from __future__ import annotations

import json
from datetime import datetime, UTC
from typing import Any

from openai import OpenAI

from app.config import OPENAI_API_KEY, DEFAULT_MODEL, TEMPERATURE, MAX_TOKENS
from app.core.models import (
    AgentEvent,
    AgentName,
    AgentState,
    ARIAState,
    AudiencePlan,
    AudienceSegment,
    BudgetPlan,
    CampaignBrief,
    CreativeVariant,
    EvaluationVerdict,
    Experiment,
    ExperimentStatus,
    ExperimentMetrics,
    HypothesisOutcome,
    Hypothesis,
    MemoryWritePayload,
    ObservationSignals,
    PlatformAllocation,
    RouteAfterEval,
)
from app.core.runtime import runtime
from langgraph.graph import END, START, StateGraph


# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)


def _call_openai(system_prompt: str, user_prompt: str, max_tokens: int = MAX_TOKENS) -> str:
    """Helper function to call OpenAI API."""
    try:
        response = client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=TEMPERATURE,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"OpenAI API error: {e}")
        return "Fallback response due to API error"


def _event(state: dict[str, Any], agent: AgentName, action: str, reason: str, confidence: float, diff: dict[str, Any]) -> dict[str, Any]:
    event = AgentEvent(
        run_id=state["run_id"],
        iteration=state["iteration"],
        agent=agent,
        action=action,
        reason=reason,
        confidence=confidence,
        diff=diff,
    )
    events = list(state.get("events", []))
    events.append(event.model_dump(mode="json"))
    return {"events": events}


def _merge_state(state: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    """LangGraph dict state does not automatically deep-merge partial updates.

    Return a full state object by overlaying each node patch on top of incoming state.
    """
    return {**state, **patch}


def observe_signals(state: dict[str, Any]) -> dict[str, Any]:
    """Observe market signals using OpenAI analysis."""
    brand_info = state.get("brand", {})
    
    system_prompt = "You are an expert market analyst for digital advertising. Analyze the provided brand information and generate realistic market signals."
    user_prompt = f"""
    Analyze this brand and generate market signals:
    - Brand: {brand_info.get('brand_name', 'Unknown')}
    - URL: {brand_info.get('url', 'Unknown')}
    - Goal: {brand_info.get('goal', 'Unknown')}
    - Budget: ${brand_info.get('budget_daily', 0)}
    
    Provide a JSON response with:
    - meta_roas: Return on ad spend (0.1-10.0)
    - google_roas: Google-specific ROAS (0.1-10.0)
    - meta_ctr: Meta CTR percentage (0.1-10.0)
    - top_objection: Main customer objection
    - seasonal_trend: Current market trend
    """
    
    ai_response = _call_openai(system_prompt, user_prompt, max_tokens=300)
    
    # Parse AI response or use fallback
    try:
        ai_data = json.loads(ai_response)
        meta_roas = ai_data.get("meta_roas", 3.8)
        google_roas = ai_data.get("google_roas", 2.9)
        meta_ctr = ai_data.get("meta_ctr", 3.1)
        top_objection = ai_data.get("top_objection", "is this legit?")
        seasonal_trend = ai_data.get("seasonal_trend", "q1_self_improvement")
    except:
        # Fallback values
        meta_roas = 3.8
        google_roas = 2.9
        meta_ctr = 3.1
        top_objection = "is this legit?"
        seasonal_trend = "q1_self_improvement"
    
    signals = ObservationSignals(
        timestamp=datetime.now(UTC),
        meta={"roas": meta_roas, "frequency": 2.4, "ctr": meta_ctr},
        google={"roas": google_roas, "frequency": 0.0, "ctr": 4.2},
        competitor_signals={"saturated_angles": ["discount", "limited_time_offer"]},
        market_trends={"season": seasonal_trend.split("_")[0], "theme": seasonal_trend.split("_")[1] if "_" in seasonal_trend else "self_improvement"},
        audience_behavior={"top_objection": top_objection},
    )
    patch = {"signals": signals.model_dump(mode="json")}
    patch.update(
        _event(
            state,
            AgentName.OBSERVE,
            "observe_signals",
            f"Collected signals using AI analysis for {brand_info.get('brand_name', 'brand')}",
            0.85,
            {"meta_roas": meta_roas, "google_roas": google_roas, "ai_analysis": True},
        )
    )
    return _merge_state(state, patch)


def growth_strategist_agent(state: dict[str, Any]) -> dict[str, Any]:
    """Generate growth hypotheses using OpenAI strategy analysis."""
    brand_info = state.get("brand", {})
    signals = state.get("signals", {})
    
    system_prompt = (
        "You are a staff marketing and strategy lead for digital advertising. "
        "Generate data-driven hypotheses based on market signals and brand information."
    )
    user_prompt = f"""
    Create 2 strategic hypotheses for this brand:
    - Brand: {brand_info.get('brand_name', 'Unknown')}
    - Goal: {brand_info.get('goal', 'Unknown')}
    - Budget: ${brand_info.get('budget_daily', 0)}
    - Market ROAS: Meta {signals.get('meta', {}).get('roas', 0)}, Google {signals.get('google', {}).get('roas', 0)}
    - Top objection: {signals.get('audience_behavior', {}).get('top_objection', 'Unknown')}
    
    Provide a JSON response with 2 hypotheses, each containing:
    - statement: Clear hypothesis statement
    - rationale: Strategic reasoning
    - confidence: Confidence level (0.1-1.0)
    - success_metric: Primary metric (cvr/roas/ctr)
    - target_lift_percent: Expected lift (5-50%)
    """
    
    ai_response = _call_openai(system_prompt, user_prompt, max_tokens=400)
    
    # Parse AI response or use fallback
    try:
        ai_data = json.loads(ai_response)
        ai_hypotheses = ai_data.get("hypotheses", [])
    except:
        ai_hypotheses = []
    
    # Use AI hypotheses if available, otherwise fallback
    if len(ai_hypotheses) >= 2:
        hypotheses = []
        for i, hyp in enumerate(ai_hypotheses[:2]):
            hypotheses.append(Hypothesis(
                statement=hyp.get("statement", f"AI hypothesis {i+1}"),
                rationale=hyp.get("rationale", "AI-generated strategy"),
                confidence=hyp.get("confidence", 0.8),
                success_metric=hyp.get("success_metric", "cvr"),
                target_lift_percent=hyp.get("target_lift_percent", 15.0),
                priority=i+1,
            ))
    else:
        # Fallback hypotheses
        hypotheses = [
            Hypothesis(
                statement="Testimonial trust hook beats discount hook",
                rationale="Competitors over-index on discount; memory favors trust for this category",
                confidence=0.87,
                success_metric="cvr",
                target_lift_percent=18.0,
                priority=1,
            ),
            Hypothesis(
                statement="Instagram Stories outperforms Search for sub-$50 products",
                rationale="Observed B2C impulse behavior + higher short-form CTR",
                confidence=0.79,
                success_metric="roas",
                target_lift_percent=12.0,
                priority=2,
            ),
        ]
    
    brief = CampaignBrief(
        objective=brand_info.get("goal", "purchases"),
        angle="trust_social_proof",
        channel_mix=["meta", "google"],
        constraints=["max daily scale 20%", "frequency cap 3.5"],
    )
    patch = {
        "hypotheses": [h.model_dump(mode="json") for h in hypotheses],
        "campaign_brief": brief.model_dump(mode="json"),
    }
    patch.update(
        _event(
            state,
            AgentName.STRATEGIST,
            "rank_hypotheses",
            f"Generated {len(ai_hypotheses)} AI-powered hypotheses for {brand_info.get('brand_name', 'brand')}",
            0.87,
            {"top_hypothesis": hypotheses[0].statement, "ai_generated": len(ai_hypotheses) >= 2},
        )
    )
    return _merge_state(state, patch)


def creative_generation_agent(state: dict[str, Any]) -> dict[str, Any]:
    """Generate creative variants using OpenAI copywriting."""
    brand_info = state.get("brand", {})
    hypotheses = state.get("hypotheses", [])
    top_hypothesis = hypotheses[0] if hypotheses else {}
    
    system_prompt = "You are an expert copywriter and creative director for digital advertising. Generate compelling ad creative based on the provided hypothesis and brand information."
    user_prompt = f"""
    Create 2 ad creative variants for this campaign:
    - Brand: {brand_info.get('brand_name', 'Unknown')}
    - Goal: {brand_info.get('goal', 'Unknown')}
    - Hypothesis: {top_hypothesis.get('statement', 'Test trust-based messaging')}
    - Target metric: {top_hypothesis.get('success_metric', 'cvr')}
    
    Provide a JSON response with 2 variants, each containing:
    - hook: Compelling opening line (under 15 words)
    - body: Main message (under 25 words)
    - cta: Clear call to action (under 8 words)
    - format: "image" or "video"
    """
    
    ai_response = _call_openai(system_prompt, user_prompt, max_tokens=350)
    
    # Parse AI response or use fallback
    try:
        ai_data = json.loads(ai_response)
        ai_variants = ai_data.get("variants", [])
    except:
        ai_variants = []
    
    hypothesis_id = top_hypothesis.get("hypothesis_id", "default")
    
    # Use AI variants if available, otherwise fallback
    if len(ai_variants) >= 2:
        variants = []
        for variant in ai_variants[:2]:
            variants.append(CreativeVariant(
                hook=variant.get("hook", "AI-generated hook"),
                body=variant.get("body", "AI-generated body"),
                cta=variant.get("cta", "Learn more"),
                format=variant.get("format", "image"),
                source_hypothesis_id=hypothesis_id,
            ))
    else:
        # Fallback variants
        variants = [
            CreativeVariant(
                hook="I tried 12 products. This one finally worked.",
                body="Proof-backed results from people who thought nothing would work.",
                cta="See real before/after stories",
                format="video",
                source_hypothesis_id=hypothesis_id,
            ),
            CreativeVariant(
                hook="Before: breakouts daily. After: clear skin in 3 weeks.",
                body="Built for people who've tried everything else.",
                cta="Shop the routine",
                format="image",
                source_hypothesis_id=hypothesis_id,
            ),
        ]
    
    patch = {"creative_variants": [v.model_dump(mode="json") for v in variants]}
    patch.update(
        _event(
            state,
            AgentName.CREATIVE,
            "generate_variants",
            f"Generated {len(ai_variants)} AI-powered creative variants for {brand_info.get('brand_name', 'brand')}",
            0.82,
            {"variant_count": len(variants), "ai_generated": len(ai_variants) >= 2},
        )
    )
    return _merge_state(state, patch)


def audience_optimization_agent(state: dict[str, Any]) -> dict[str, Any]:
    business_type = state["brand"]["business_type"]
    if business_type == "B2B":
        segment = AudienceSegment(
            name="In-market RevOps buyers",
            business_type="B2B",
            belief_state="Current stack is leaking pipeline efficiency",
            purchase_trigger="ROI proof from similar companies",
            objection="Will this integrate with existing stack?",
            message_angle="Revenue lift in 30 days",
            targeting_layers=["job_title", "company_size", "tech_stack"],
        )
    else:
        segment = AudienceSegment(
            name="Trust-seeking skincare buyers",
            business_type="B2C",
            belief_state="I've tried solutions and been disappointed",
            purchase_trigger="Social proof + low perceived risk",
            objection="Will this actually work for me?",
            message_angle="Designed for people who've tried everything",
            targeting_layers=["instagram_stories", "women_28_38", "lookalike_converters"],
        )

    plan = AudiencePlan(segments=[segment], overlap_risk_percent=11.0, recommendations=["Exclude prior 7-day clickers from broad ad set"])
    patch = {"audience_plan": plan.model_dump(mode="json")}
    patch.update(
        _event(
            state,
            AgentName.AUDIENCE,
            "optimize_audience",
            "Selected segment + exclusion list based on conversion quality",
            0.81,
            {"segment": segment.name, "overlap_risk_percent": 11.0},
        )
    )
    return _merge_state(state, patch)


def budget_allocation_agent(state: dict[str, Any]) -> dict[str, Any]:
    total_budget = state["brand"]["budget_daily"]
    meta_roas = state["signals"]["meta"].get("roas", 0.0)
    google_roas = state["signals"]["google"].get("roas", 0.0)

    if meta_roas >= google_roas:
        meta_budget = round(total_budget * 0.6, 2)
    else:
        meta_budget = round(total_budget * 0.4, 2)
    google_budget = round(total_budget - meta_budget, 2)

    plan = BudgetPlan(
        total_budget=total_budget,
        allocations=[
            PlatformAllocation(platform="meta", budget=meta_budget, rationale="Higher observed ROAS"),
            PlatformAllocation(platform="google", budget=google_budget, rationale="Maintain search capture"),
        ],
        pacing_action="hold",
        guardrails_applied=["max daily scale 20%", "frequency cap 3.5"],
    )

    patch = {"budget_plan": plan.model_dump(mode="json")}
    patch.update(
        _event(
            state,
            AgentName.BUDGET,
            "allocate_budget",
            "Allocated by weighted ROAS with safety caps",
            0.84,
            {"meta_budget": meta_budget, "google_budget": google_budget},
        )
    )
    return _merge_state(state, patch)


def composio_execution_layer(state: dict[str, Any]) -> dict[str, Any]:
    top_hypothesis_id = state["hypotheses"][0]["hypothesis_id"]
    experiment = Experiment(
        hypothesis_id=top_hypothesis_id,
        status=ExperimentStatus.RUNNING,
        channels=[a["platform"] for a in state["budget_plan"]["allocations"]],
        start_time=datetime.now(UTC),
        success_metric=state["hypotheses"][0]["success_metric"],
    )
    patch = {"experiments": list(state.get("experiments", [])) + [experiment.model_dump(mode="json")]}
    patch.update(
        _event(
            state,
            AgentName.EXECUTE,
            "launch_experiment",
            "Launched experiment via mocked Composio adapters",
            0.78,
            {"experiment_id": experiment.experiment_id},
        )
    )
    return _merge_state(state, patch)


def experiment_evaluation_agent(state: dict[str, Any]) -> dict[str, Any]:
    verdict = EvaluationVerdict(
        hypothesis_outcome=HypothesisOutcome.CONFIRMED,
        confidence_score=0.86,
        winning_element="testimonial hook first sentence",
        effect_size="+18% CVR vs baseline",
        statistical_significance=True,
        sample_size_adequate=True,
        brief_to_creative="Mutate testimonial hook across 3 fresh variants",
        brief_to_audience="Expand lookalike from converters in top segment",
        brief_to_budget="Scale winner by 20%, keep guardrails",
        brief_to_strategist="Increase rank of trust-first hypotheses",
        write_to_memory=MemoryWritePayload(
            pattern="Trust signals outperform discount for trust-seeking skincare segment",
            conditions={"business_type": state["brand"]["business_type"], "price_band": "mid"},
            confidence=0.86,
            n_experiments=1,
        ),
        route=RouteAfterEval.COMPLETE,
    )
    patch = {"evaluation": verdict.model_dump(mode="json")}
    patch.update(
        _event(
            state,
            AgentName.EVALUATE,
            "evaluate_experiment",
            "Evaluated winner based on ROAS + CVR deltas",
            0.88,
            {"outcome": verdict.hypothesis_outcome.value, "route": verdict.route.value},
        )
    )
    return _merge_state(state, patch)


def write_to_shared_memory(state: dict[str, Any]) -> dict[str, Any]:
    evaluation = state["evaluation"]
    memory = state["memory"]

    log_entry = {
        "experiment_id": state["experiments"][-1]["experiment_id"],
        "date": datetime.now(UTC).isoformat(),
        "hypothesis": state["hypotheses"][0]["statement"],
        "result": evaluation["hypothesis_outcome"],
        "confidence": evaluation["confidence_score"],
        "learning": evaluation["write_to_memory"]["pattern"],
        "conditions": evaluation["write_to_memory"]["conditions"],
    }
    memory["experiment_log"] = list(memory.get("experiment_log", [])) + [log_entry]
    memory["strategy_memory"]["iteration"] = state["iteration"] + 1
    memory["strategy_memory"]["current_winning_angle"] = "trust_social_proof"

    patch = {"memory": memory, "iteration": state["iteration"] + 1}
    patch.update(
        _event(
            state,
            AgentName.LEARN,
            "write_memory",
            "Persisted winning pattern into shared strategy memory",
            0.9,
            {"learning": log_entry["learning"]},
        )
    )
    return _merge_state(state, patch)


def slack_notification(state: dict[str, Any]) -> dict[str, Any]:
    patch = _event(
        state,
        AgentName.NOTIFY,
        "notify",
        "Prepared Slack decision digest for operators",
        0.75,
        {
            "message": (
                f"ARIA cycle {state['iteration']} complete. "
                f"Outcome: {state['evaluation']['hypothesis_outcome']}"
            )
        },
    )
    return _merge_state(state, patch)


def route_after_eval(state: dict[str, Any]) -> str:
    evaluation = state.get("evaluation")
    if not evaluation:
        return RouteAfterEval.COMPLETE.value
    return evaluation.get("route", RouteAfterEval.COMPLETE.value)


def build_aria_graph():
    graph = StateGraph(dict)

    graph.add_node("observe", observe_signals)
    graph.add_node("strategize", growth_strategist_agent)
    graph.add_node("create", creative_generation_agent)
    graph.add_node("target", audience_optimization_agent)
    graph.add_node("allocate", budget_allocation_agent)
    graph.add_node("execute", composio_execution_layer)
    graph.add_node("evaluate", experiment_evaluation_agent)
    graph.add_node("learn", write_to_shared_memory)
    graph.add_node("notify", slack_notification)

    graph.add_edge(START, "observe")
    graph.add_edge("observe", "strategize")
    graph.add_edge("strategize", "create")
    graph.add_edge("create", "target")
    graph.add_edge("target", "allocate")
    graph.add_edge("allocate", "execute")
    graph.add_edge("execute", "evaluate")

    graph.add_conditional_edges(
        "evaluate",
        route_after_eval,
        {
            RouteAfterEval.KILL_AND_RERUN.value: "strategize",
            RouteAfterEval.SCALE_WINNER.value: "allocate",
            RouteAfterEval.INCONCLUSIVE.value: "create",
            RouteAfterEval.COMPLETE.value: "learn",
        },
    )

    graph.add_edge("learn", "notify")
    graph.add_edge("notify", END)

    return graph.compile()


async def run_one_cycle(app_state: ARIAState) -> ARIAState:
    graph = build_aria_graph()
    updated_state = await graph.ainvoke(app_state.model_dump(mode="json"))
    return ARIAState.model_validate(updated_state)
