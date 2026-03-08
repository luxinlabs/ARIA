from __future__ import annotations

import asyncio
from copy import deepcopy
import json
import re
from datetime import UTC, datetime
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request as UrlRequest, urlopen

from fastapi import APIRouter, HTTPException, Request, WebSocket, WebSocketDisconnect, status

from app.core.models import (
    ARIAState,
    AgentEvent,
    AgentName,
    AgentState,
    ApproveRequest,
    ComparisonRequest,
    ComparisonResponse,
    GoalType,
    InitRequest,
    InitResponse,
    PauseRequest,
    PerformanceResponse,
    PlatformMetrics,
    PlatformType,
    RunReportResponse,
    SendReportRequest,
    SharedMemory,
    StatusResponse,
)
from app.core.runtime import runtime
from app.orchestration.graph import run_one_cycle
from app.ws.live_feed import live_feed_manager

router = APIRouter(prefix="/aria", tags=["aria"])


@router.get("/health")
async def health_check(request: Request) -> dict[str, Any]:
    """Health check endpoint to verify API key and system status."""
    from app.config import OPENAI_API_KEY
    
    return {
        "status": "healthy",
        "openai_configured": bool(OPENAI_API_KEY),
        "openai_key_length": len(OPENAI_API_KEY) if OPENAI_API_KEY else 0,
        "initialized": await runtime.get_state(_resolve_run_id(request)) is not None,
    }


@router.get("/sessions")
async def list_sessions() -> dict[str, Any]:
    sessions = await runtime.list_sessions()
    return {"sessions": sessions}


@router.post("/sessions/{run_id}/activate")
async def activate_session(run_id: str) -> dict[str, Any]:
    state = await runtime.set_active_run(run_id)
    if state is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return {"status": "active", "run_id": state.run_id}


@router.delete("/sessions/{run_id}")
async def delete_session(run_id: str) -> dict[str, str]:
    state = await runtime.get_state(run_id)
    if state is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    await runtime.clear_state(run_id)
    return {"status": "deleted", "run_id": run_id}


@router.get("/learning/insights")
async def get_learning_insights() -> dict[str, Any]:
    """Get insights about agent learning and self-improvement."""
    from app.core.decision_framework import shared_framework
    
    # Get insights for all agents
    agent_insights = {}
    for agent_name in ["strategist", "creative", "audience", "budget", "evaluate"]:
        insights = shared_framework.get_agent_insights(agent_name)
        if insights:
            agent_insights[agent_name] = insights
    
    # Get overall framework statistics
    knowledge = shared_framework.export_knowledge()
    
    return {
        "agent_insights": agent_insights,
        "total_decisions": knowledge["total_decisions"],
        "total_outcomes": knowledge["total_outcomes"],
        "patterns_discovered": len(knowledge["learned_patterns"]),
        "learning_enabled": True,
        "framework_version": "1.0",
        "top_patterns": [
            {
                "pattern_id": p["pattern_id"],
                "success_rate": p["success_rate"],
                "sample_size": p["sample_size"],
                "confidence": p["confidence"]
            }
            for p in sorted(
                knowledge["learned_patterns"],
                key=lambda x: x["success_rate"] * x["confidence"],
                reverse=True
            )[:5]
        ]
    }


@router.get("/learning/export")
async def export_learning_knowledge() -> dict[str, Any]:
    """Export all learned knowledge for backup or analysis."""
    from app.core.decision_framework import shared_framework
    return shared_framework.export_knowledge()


def _as_agent_event(event: AgentEvent | dict[str, Any]) -> AgentEvent:
    if isinstance(event, AgentEvent):
        return event
    return AgentEvent.model_validate(event)


async def _publish_delta_events(previous_count: int, state: ARIAState) -> None:
    for event in state.events[previous_count:]:
        await runtime.emit_existing_event(_as_agent_event(event))


def _resolve_run_id(request: Request, run_id: str | None = None) -> str | None:
    if run_id:
        return run_id
    query_run_id = request.query_params.get("run_id")
    if query_run_id:
        return query_run_id
    header_run_id = request.headers.get("X-Run-Id")
    if header_run_id:
        return header_run_id
    return None


def _deep_merge(base: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    merged = deepcopy(base)
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


async def _get_or_404(request: Request, run_id: str | None = None) -> ARIAState:
    state = await runtime.get_state(_resolve_run_id(request, run_id))
    if state is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ARIA run is not initialized")
    return state


async def _get_state_or_none(request: Request, run_id: str | None = None) -> ARIAState | None:
    return await runtime.get_state(_resolve_run_id(request, run_id))


def _safe_text(value: Any, fallback: str = "N/A") -> str:
    if value is None:
        return fallback
    text = str(value).strip()
    return text if text else fallback


def _build_cycle_report_markdown(state: ARIAState) -> str:
    company_name = _safe_text(state.memory.brand_dna.name, _safe_text(state.brand.brand_name, "Unknown Company"))
    latest_experiment = state.experiments[-1] if state.experiments else None
    latest_evaluation = state.evaluation
    production = state.memory.production_information
    audience = state.memory.target_audience

    channel_mix = ", ".join(
        getattr(ch, "value", str(ch)) for ch in state.memory.platform_context.channels
    ) or "N/A"
    generated_at = datetime.now(UTC).isoformat()
    top_hypotheses = state.hypotheses[:3]
    hypothesis_lines = "\n".join(
        f"- {item.statement} (confidence: {item.confidence:.2f})" for item in top_hypotheses
    )
    if not hypothesis_lines:
        hypothesis_lines = "- No hypotheses generated in this cycle."

    experiment_summary = "No experiment has been produced yet."
    if latest_experiment:
        experiment_summary = (
            f"ID: {latest_experiment.experiment_id}; status: {latest_experiment.status}; "
            f"ROAS: {latest_experiment.metrics.roas}; CPA: {latest_experiment.metrics.cpa}; "
            f"CTR: {latest_experiment.metrics.ctr}; CVR: {latest_experiment.metrics.cvr}"
        )

    evaluation_summary = "No evaluation output available yet."
    if latest_evaluation:
        outcome = getattr(latest_evaluation, "hypothesis_outcome", None)
        confidence = getattr(latest_evaluation, "confidence_score", None)
        route = getattr(latest_evaluation, "route", None)
        confidence_text = f"{confidence:.2f}" if isinstance(confidence, (int, float)) else "N/A"
        outcome_text = getattr(outcome, "value", str(outcome) if outcome is not None else "N/A")
        route_text = getattr(route, "value", str(route) if route is not None else "N/A")
        evaluation_summary = (
            f"Outcome: {outcome_text}; confidence: {confidence_text}; "
            f"winning element: {_safe_text(getattr(latest_evaluation, 'winning_element', None))}; "
            f"effect size: {_safe_text(getattr(latest_evaluation, 'effect_size', None))}; "
            f"route: {route_text}"
        )

    return f"""# ARIA Cycle Report

Generated at: {generated_at}
Run ID: {state.run_id}
Cycle Iteration: {state.iteration}

## Company Snapshot
- Company: {company_name}
- Website: {_safe_text(state.brand.url)}
- Goal: {state.brand.goal.value}
- Daily Budget: ${state.brand.budget_daily}
- Business Type: {state.brand.business_type.value}

## Production Information (Website-Derived)
- Product Name: {_safe_text(production.product_name)}
- Category: {_safe_text(production.product_category)}
- Offer Summary: {_safe_text(production.offer_summary)}
- Price Point: {_safe_text(production.price_point)}
- Brand URL: {_safe_text(production.brand_url, _safe_text(state.brand.url))}

## Target Audience
- Primary Segment: {_safe_text(audience.primary_segment)}
- Age Range: {_safe_text(audience.age_range)}
- Geography: {", ".join(audience.geography) if audience.geography else "N/A"}
- Key Interests: {", ".join(audience.interests) if audience.interests else "N/A"}

## Platform & Creative Setup
- Channels: {channel_mix}
- Copies per Cycle: {state.memory.generations.copies_per_cycle}
- Images Required: {state.memory.platform_context.images_required}
- Videos Required: {state.memory.platform_context.videos_required}

## Hypotheses (Top 3)
{hypothesis_lines}

## Experiment Snapshot
{experiment_summary}

## Evaluation & Learning
{evaluation_summary}

## Notes
- This report was generated after at least one completed cycle.
- Data source is run-scoped shared memory and latest cycle artifacts.
"""


def _post_openclaw_prompt(base_url: str, prompt: str) -> dict[str, Any]:
    url_base = base_url.rstrip("/")
    payload = json.dumps({"prompt": prompt}).encode("utf-8")
    candidates = [url_base, f"{url_base}/send", f"{url_base}/prompt"]
    errors: list[str] = []

    for endpoint in candidates:
        request = UrlRequest(
            endpoint,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=15) as response:
                body = response.read().decode("utf-8", errors="ignore")
                return {
                    "endpoint": endpoint,
                    "status_code": response.status,
                    "response": body,
                }
        except HTTPError as exc:
            body = exc.read().decode("utf-8", errors="ignore") if exc.fp else ""
            errors.append(f"{endpoint} -> HTTP {exc.code}: {body[:180]}")
        except URLError as exc:
            errors.append(f"{endpoint} -> URL error: {exc.reason}")
        except TimeoutError:
            errors.append(f"{endpoint} -> request timed out")

    raise RuntimeError("OpenClaw delivery failed. Tried endpoints: " + " | ".join(errors))


@router.post("/init", response_model=InitResponse)
async def init_aria(payload: InitRequest) -> InitResponse:
    from app.config import OPENAI_API_KEY
    
    if not OPENAI_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="OPENAI_API_KEY environment variable is not set. Please configure it in your deployment settings.",
        )
    
    try:
        state = await runtime.init_run(payload)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Initialization failed from strategy generation: {exc}",
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Initialization error: {str(exc)}",
        ) from exc

    return InitResponse(run_id=state.run_id, message="ARIA initialized")


@router.get("/status", response_model=StatusResponse)
async def aria_status(request: Request) -> StatusResponse:
    state = await _get_state_or_none(request)
    if state is None:
        return StatusResponse(
            run_id="uninitialized",
            iteration=0,
            paused=False,
            goal=GoalType.PURCHASES,
            budget_daily=0.0,
            agent_states={name: AgentState() for name in AgentName},
        )

    return StatusResponse(
        run_id=state.run_id,
        iteration=state.iteration,
        paused=state.paused,
        goal=state.brand.goal,
        budget_daily=state.brand.budget_daily,
        agent_states=state.agent_states,
    )


@router.get("/memory")
async def aria_memory(request: Request) -> dict[str, Any]:
    state = await _get_state_or_none(request)
    if state is None:
        return {}
    return state.memory.model_dump(mode="json")


@router.get("/strategy")
async def aria_strategy_snapshot(request: Request) -> dict[str, Any]:
    """Return a focused strategy payload after initialization."""
    state = await _get_or_404(request)
    memory = state.memory

    return {
        "production_information": memory.production_information.model_dump(mode="json"),
        "platform": {
            "channels": memory.platform_context.channels,
            "images_required": memory.platform_context.images_required,
            "videos_required": memory.platform_context.videos_required,
        },
        "target_audience": memory.target_audience.model_dump(mode="json"),
        "generations": {
            "copies_per_cycle": memory.generations.copies_per_cycle,
            "max_generations": memory.generations.max_generations,
            "active_generation": memory.generations.active_generation,
        },
        "performance_history": {
            "platform_user_click_history": [
                {
                    "platform": row.platform,
                    "user_clicks": row.user_clicks,
                    "integrations_from_sites": row.integrations_from_sites,
                    "paid_conversions": row.paid_conversions,
                    "conversion_rate": row.conversion_rate,
                }
                for row in memory.performance_history.platform_user_click_history
            ],
            "overall_conversion_rate": memory.performance_history.overall_conversion_rate,
        },
    }


@router.patch("/memory")
async def patch_memory(request: Request, payload: dict[str, Any]) -> dict[str, Any]:
    state = await _get_or_404(request)

    current = state.memory.model_dump(mode="python")
    merged = _deep_merge(current, payload)

    try:
        updated_memory = SharedMemory.model_validate(merged)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid memory patch: {exc}",
        ) from exc

    updated_state = state.model_copy(update={"memory": updated_memory})
    await runtime.set_state(updated_state)

    event = AgentEvent(
        run_id=updated_state.run_id,
        iteration=updated_state.iteration,
        agent=AgentName.LEARN,
        action="memory_patch",
        reason="Shared memory updated via PATCH /aria/memory",
        confidence=1.0,
        diff={"updated_keys": list(payload.keys())},
    )
    await runtime.publish_event(event)

    return updated_state.memory.model_dump(mode="json")


@router.get("/hypotheses")
async def aria_hypotheses(request: Request) -> list[dict[str, Any]]:
    state = await _get_state_or_none(request)
    if state is None:
        return []
    return [h.model_dump(mode="json") for h in state.hypotheses]


@router.post("/approve/{hypothesis_id}")
async def approve_hypothesis(request: Request, hypothesis_id: str, payload: ApproveRequest) -> dict[str, Any]:
    state = await _get_or_404(request)
    decision = "approved" if payload.approved else "rejected"

    event = AgentEvent(
        run_id=state.run_id,
        iteration=state.iteration,
        agent=AgentName.STRATEGIST,
        action="human_override",
        reason=f"Hypothesis {hypothesis_id} {decision} by operator",
        confidence=1.0,
        diff={"hypothesis_id": hypothesis_id, "decision": decision, "note": payload.note},
    )
    await runtime.publish_event(event)
    return {"hypothesis_id": hypothesis_id, "decision": decision, "note": payload.note}


@router.get("/experiments")
async def aria_experiments(request: Request) -> list[dict[str, Any]]:
    state = await _get_state_or_none(request)
    if state is None:
        return []
    return [e.model_dump(mode="json") for e in state.experiments]


@router.get("/eval/{exp_id}")
async def aria_eval(request: Request, exp_id: str) -> dict[str, Any]:
    state = await _get_or_404(request)
    if state.evaluation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No evaluation available")

    experiment = next((exp for exp in state.experiments if exp.experiment_id == exp_id), None)
    if experiment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experiment not found")

    return {
        "experiment": experiment.model_dump(mode="json"),
        "evaluation": state.evaluation.model_dump(mode="json"),
    }


@router.get("/performance", response_model=PerformanceResponse)
async def aria_performance(request: Request) -> PerformanceResponse:
    state = await _get_state_or_none(request)
    if state is None:
        return PerformanceResponse(
            unified_roas=0.0,
            meta_roas=0.0,
            google_roas=0.0,
            cpa=0.0,
            ctr=0.0,
            cvr=0.0,
        )

    latest_exp = state.experiments[-1] if state.experiments else None
    if latest_exp:
        metrics = latest_exp.metrics
        meta_roas = state.signals.meta.get("roas", metrics.roas)
        google_roas = state.signals.google.get("roas", metrics.roas)
        unified_roas = round((meta_roas + google_roas) / 2, 2)
        return PerformanceResponse(
            unified_roas=unified_roas,
            meta_roas=meta_roas,
            google_roas=google_roas,
            cpa=metrics.cpa,
            ctr=metrics.ctr,
            cvr=metrics.cvr,
        )

    meta_roas = state.signals.meta.get("roas", 0.0)
    google_roas = state.signals.google.get("roas", 0.0)
    return PerformanceResponse(
        unified_roas=round((meta_roas + google_roas) / 2, 2),
        meta_roas=meta_roas,
        google_roas=google_roas,
        cpa=0.0,
        ctr=0.0,
        cvr=0.0,
    )


@router.post("/pause")
async def aria_pause(request: Request, payload: PauseRequest) -> dict[str, str]:
    state = await _get_or_404(request)
    updated = state.model_copy(update={"paused": True, "pause_reason": payload.reason})
    await runtime.set_state(updated)

    event = AgentEvent(
        run_id=updated.run_id,
        iteration=updated.iteration,
        agent=AgentName.NOTIFY,
        action="pause",
        reason="Emergency stop requested",
        confidence=1.0,
        diff={"reason": payload.reason},
    )
    await runtime.publish_event(event)
    return {"status": "paused", "reason": payload.reason}


@router.post("/reset")
async def aria_reset(request: Request) -> dict[str, str]:
    run_id = _resolve_run_id(request)
    await runtime.clear_state(run_id)
    return {"status": "cleared"}


@router.get("/learnings")
async def aria_learnings(request: Request) -> dict[str, Any]:
    state = await _get_or_404(request)
    lessons = [
        {
            "pattern": item.learning,
            "confidence": item.confidence,
            "conditions": item.conditions,
        }
        for item in state.memory.experiment_log[-10:]
    ]
    summary = (
        f"ARIA has learned {len(state.memory.experiment_log)} total patterns. "
        f"Current winning angle: {state.memory.strategy_memory.current_winning_angle or 'N/A'}."
    )
    return {"summary": summary, "recent_learnings": lessons}


@router.post("/step")
async def aria_step(request: Request) -> dict[str, Any]:
    state = await _get_or_404(request)
    if state.paused:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Run paused: {state.pause_reason}")

    # Emit start event
    start_event = AgentEvent(
        run_id=state.run_id,
        iteration=state.iteration,
        agent=AgentName.OBSERVE,
        action="running",
        reason="Starting agent cycle execution",
        confidence=1.0,
        diff={"cycle_started": True}
    )
    await runtime.publish_event(start_event)

    before_count = len(state.events)
    updated = await run_one_cycle(state)
    await runtime.set_state(updated)
    await _publish_delta_events(before_count, updated)

    # Emit completion event
    complete_event = AgentEvent(
        run_id=updated.run_id,
        iteration=updated.iteration,
        agent=AgentName.LEARN,
        action="idle",
        reason="Agent cycle completed",
        confidence=1.0,
        diff={"cycle_completed": True}
    )
    await runtime.publish_event(complete_event)

    return {
        "run_id": updated.run_id,
        "iteration": updated.iteration,
        "hypotheses": [h.model_dump(mode="json") for h in updated.hypotheses],
        "evaluation": updated.evaluation.model_dump(mode="json") if updated.evaluation else None,
    }


@router.get("/report", response_model=RunReportResponse)
async def aria_report(request: Request) -> RunReportResponse:
    state = await _get_or_404(request)
    if state.iteration < 1:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Run report is available only after at least 1 completed cycle.",
        )

    company_name = _safe_text(state.memory.brand_dna.name, _safe_text(state.brand.brand_name, "company"))
    slug = re.sub(r"[^a-z0-9]+", "-", company_name.lower()).strip("-") or "company"
    report_markdown = _build_cycle_report_markdown(state)
    generated_at = datetime.now(UTC)

    return RunReportResponse(
        run_id=state.run_id,
        iteration=state.iteration,
        file_name=f"aria-report-{slug}-{state.run_id}-iter-{state.iteration}.md",
        company_name=company_name,
        generated_at=generated_at,
        report_markdown=report_markdown,
    )


@router.post("/report/send")
async def aria_report_send(request: Request, payload: SendReportRequest) -> dict[str, Any]:
    state = await _get_or_404(request)
    if state.iteration < 1:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot send report before at least 1 completed cycle.",
        )

    report_markdown = _build_cycle_report_markdown(state)
    prompt = f"{payload.prompt_prefix}\n\n{report_markdown}"
    try:
        delivery = await runtime_loop_safe_openclaw_send(str(payload.openclaw_url), prompt)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    event = AgentEvent(
        run_id=state.run_id,
        iteration=state.iteration,
        agent=AgentName.NOTIFY,
        action="report_sent",
        reason="Cycle report delivered to OpenClaw for Slack notification",
        confidence=1.0,
        diff={"endpoint": delivery["endpoint"], "status_code": delivery["status_code"]},
    )
    await runtime.publish_event(event)

    return {
        "status": "sent",
        "run_id": state.run_id,
        "iteration": state.iteration,
        "openclaw_endpoint": delivery["endpoint"],
        "openclaw_status": delivery["status_code"],
    }


async def runtime_loop_safe_openclaw_send(base_url: str, prompt: str) -> dict[str, Any]:
    return await asyncio.to_thread(_post_openclaw_prompt, base_url, prompt)


@router.post("/compare/save")
async def save_comparison_decision(http_request: Request, request: ComparisonRequest) -> dict[str, Any]:
    """Save human platform allocation decision to shared memory."""
    state = await _get_or_404(http_request)
    
    # Validate allocations sum to 100%
    total_pct = sum(alloc.percentage for alloc in request.allocations)
    if abs(total_pct - 100.0) > 0.01:
        raise HTTPException(status_code=400, detail=f"Allocations must sum to 100%, got {total_pct}%")
    
    # Create human input decision record
    from app.core.models import HumanInputDecision
    
    decision = HumanInputDecision(
        decision_type="platform_allocation",
        data={
            "total_budget": request.total_budget,
            "goal": request.goal.value,
            "allocations": [
                {
                    "platform": alloc.platform.value,
                    "percentage": alloc.percentage,
                    "budget": request.total_budget * alloc.percentage / 100
                }
                for alloc in request.allocations
            ]
        },
        rationale=f"Manual platform allocation via comparison tool: {', '.join([f'{a.platform.value} {a.percentage:.1f}%' for a in request.allocations])}",
        source="human_input"
    )
    
    # Add to strategy memory
    updated_memory = state.memory.model_copy(deep=True)
    updated_memory.strategy_memory.human_decisions.append(decision)
    
    # Update state
    updated_state = state.model_copy(update={"memory": updated_memory})
    await runtime.set_state(updated_state)
    
    # Publish event
    event = AgentEvent(
        run_id=state.run_id,
        iteration=state.iteration,
        agent=AgentName.STRATEGIST,
        action="human_override",
        reason=f"Human set platform allocation: {', '.join([f'{a.platform.value} {a.percentage:.1f}%' for a in request.allocations])}",
        confidence=1.0,
        diff={"source": "human_input", "decision_type": "platform_allocation"}
    )
    await runtime.publish_event(event)
    
    return {
        "status": "saved",
        "decision_id": len(updated_memory.strategy_memory.human_decisions),
        "message": "Platform allocation saved to shared memory as human input"
    }


@router.post("/compare", response_model=ComparisonResponse)
async def compare_platforms(http_request: Request, request: ComparisonRequest) -> ComparisonResponse:
    """OpenAI-powered platform comparison and budget allocation analysis."""
    from openai import OpenAI
    from app.config import OPENAI_API_KEY
    import json

    state = await runtime.get_state(_resolve_run_id(http_request))
    if not state:
        raise HTTPException(status_code=400, detail="ARIA not initialized. Call POST /aria/init first.")

    # Validate allocations sum to 100%
    total_pct = sum(alloc.percentage for alloc in request.allocations)
    if abs(total_pct - 100.0) > 0.01:
        raise HTTPException(status_code=400, detail=f"Allocations must sum to 100%, got {total_pct}%")

    client = OpenAI(api_key=OPENAI_API_KEY)

    context = {
        "brand_name": state.memory.brand_dna.name,
        "business_type": state.memory.brand_dna.business_type.value,
        "goal": request.goal.value,
        "total_budget": request.total_budget,
        "allocations": [{"platform": a.platform.value, "percentage": a.percentage, "budget": request.total_budget * a.percentage / 100} for a in request.allocations],
        "target_audience": state.memory.target_audience.model_dump() if state.memory.target_audience else {},
        "product_info": state.memory.production_information.model_dump() if state.memory.production_information else {},
    }

    prompt = f"""You are a digital advertising strategist analyzing platform performance for {context['brand_name']}.

Brand Context:
- Business Type: {context['business_type']}
- Campaign Goal: {context['goal']}
- Total Budget: ${context['total_budget']}/day
- Target Audience: {json.dumps(context['target_audience'], indent=2)}
- Product: {json.dumps(context['product_info'], indent=2)}

Proposed Budget Allocation:
{json.dumps(context['allocations'], indent=2)}

Analyze each platform (Google, Meta, TikTok) and provide:
1. Estimated reach, CPA, CTR, CVR for each platform
2. Audience fit score (0-1) based on demographics/interests
3. Creative format score (0-1) based on ad format compatibility
4. Competitive intensity (low/medium/high)
5. Platform-specific recommendation
6. Overall recommendation for this allocation
7. Risk assessment
8. 3-5 optimization tips

Return valid JSON matching this schema:
{{
  "platform_metrics": [
    {{
      "platform": "google|meta|tiktok",
      "estimated_reach": <int>,
      "estimated_cpa": <float>,
      "estimated_ctr": <float>,
      "estimated_cvr": <float>,
      "audience_fit_score": <0-1>,
      "creative_format_score": <0-1>,
      "competitive_intensity": "low|medium|high",
      "recommendation": "<string>"
    }}
  ],
  "overall_recommendation": "<string>",
  "risk_assessment": "<string>",
  "optimization_tips": ["<tip1>", "<tip2>", ...]
}}"""

    try:
        completion = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an expert digital advertising strategist. Return only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.7,
        )

        result = json.loads(completion.choices[0].message.content)
        
        return ComparisonResponse(
            total_budget=request.total_budget,
            platform_metrics=[PlatformMetrics(**m) for m in result["platform_metrics"]],
            overall_recommendation=result["overall_recommendation"],
            risk_assessment=result["risk_assessment"],
            optimization_tips=result["optimization_tips"],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OpenAI analysis failed: {str(e)}")


@router.websocket("/live")
async def aria_live(websocket: WebSocket) -> None:
    await live_feed_manager.connect(websocket)
    try:
        run_id = websocket.query_params.get("run_id") or websocket.headers.get("x-run-id")
        state = await runtime.get_state(run_id)
        if state and state.events:
            await live_feed_manager.send_many(websocket, [event.model_dump(mode="json") for event in state.events[-50:]])

        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await live_feed_manager.disconnect(websocket)
    except Exception:
        await live_feed_manager.disconnect(websocket)
