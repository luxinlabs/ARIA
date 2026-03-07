from __future__ import annotations

from copy import deepcopy
from typing import Any

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, status

from app.core.models import (
    ARIAState,
    AgentState,
    AgentEvent,
    AgentName,
    ApproveRequest,
    GoalType,
    InitRequest,
    InitResponse,
    PauseRequest,
    PerformanceResponse,
    SharedMemory,
    StatusResponse,
)
from app.core.runtime import runtime
from app.orchestration.graph import run_one_cycle
from app.ws.live_feed import live_feed_manager

router = APIRouter(prefix="/aria", tags=["aria"])


def _as_agent_event(event: AgentEvent | dict[str, Any]) -> AgentEvent:
    if isinstance(event, AgentEvent):
        return event
    return AgentEvent.model_validate(event)


async def _publish_delta_events(previous_count: int, state: ARIAState) -> None:
    for event in state.events[previous_count:]:
        await runtime.emit_existing_event(_as_agent_event(event))


def _deep_merge(base: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    merged = deepcopy(base)
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


async def _get_or_404() -> ARIAState:
    state = await runtime.get_state()
    if state is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ARIA run is not initialized")
    return state


async def _get_state_or_none() -> ARIAState | None:
    return await runtime.get_state()


@router.post("/init", response_model=InitResponse)
async def init_aria(payload: InitRequest) -> InitResponse:
    try:
        state = await runtime.init_run(payload)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Initialization failed from strategy generation: {exc}",
        ) from exc

    return InitResponse(run_id=state.run_id, message="ARIA initialized")


@router.get("/status", response_model=StatusResponse)
async def aria_status() -> StatusResponse:
    state = await _get_state_or_none()
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
async def aria_memory() -> dict[str, Any]:
    state = await _get_state_or_none()
    if state is None:
        return {}
    return state.memory.model_dump(mode="json")


@router.get("/strategy")
async def aria_strategy_snapshot() -> dict[str, Any]:
    """Return a focused strategy payload after initialization."""
    state = await _get_or_404()
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
async def patch_memory(payload: dict[str, Any]) -> dict[str, Any]:
    state = await _get_or_404()

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
async def aria_hypotheses() -> list[dict[str, Any]]:
    state = await _get_state_or_none()
    if state is None:
        return []
    return [h.model_dump(mode="json") for h in state.hypotheses]


@router.post("/approve/{hypothesis_id}")
async def approve_hypothesis(hypothesis_id: str, payload: ApproveRequest) -> dict[str, Any]:
    state = await _get_or_404()
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
async def aria_experiments() -> list[dict[str, Any]]:
    state = await _get_state_or_none()
    if state is None:
        return []
    return [e.model_dump(mode="json") for e in state.experiments]


@router.get("/eval/{exp_id}")
async def aria_eval(exp_id: str) -> dict[str, Any]:
    state = await _get_or_404()
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
async def aria_performance() -> PerformanceResponse:
    state = await _get_state_or_none()
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
async def aria_pause(payload: PauseRequest) -> dict[str, str]:
    state = await _get_or_404()
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


@router.get("/learnings")
async def aria_learnings() -> dict[str, Any]:
    state = await _get_or_404()
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
async def aria_step() -> dict[str, Any]:
    state = await _get_or_404()
    if state.paused:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Run paused: {state.pause_reason}")

    before_count = len(state.events)
    updated = await run_one_cycle(state)
    await runtime.set_state(updated)
    await _publish_delta_events(before_count, updated)

    return {
        "run_id": updated.run_id,
        "iteration": updated.iteration,
        "hypotheses": [h.model_dump(mode="json") for h in updated.hypotheses],
        "evaluation": updated.evaluation.model_dump(mode="json") if updated.evaluation else None,
    }


@router.websocket("/live")
async def aria_live(websocket: WebSocket) -> None:
    await live_feed_manager.connect(websocket)
    try:
        state = await runtime.get_state()
        if state and state.events:
            await live_feed_manager.send_many(websocket, [event.model_dump(mode="json") for event in state.events[-50:]])

        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await live_feed_manager.disconnect(websocket)
    except Exception:
        await live_feed_manager.disconnect(websocket)
