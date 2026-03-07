from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from langgraph.graph import END, START, StateGraph

from app.core.models import (
    ARIAState,
    AgentEvent,
    AgentName,
    AudiencePlan,
    AudienceSegment,
    BudgetPlan,
    CampaignBrief,
    CreativeVariant,
    EvaluationVerdict,
    Experiment,
    ExperimentStatus,
    Hypothesis,
    HypothesisOutcome,
    MemoryWritePayload,
    ObservationSignals,
    PlatformAllocation,
    RouteAfterEval,
)


def _event(
    state: dict[str, Any],
    agent: AgentName,
    action: str,
    reason: str,
    confidence: float,
    diff: dict[str, Any],
) -> dict[str, Any]:
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


def observe_signals(state: dict[str, Any]) -> dict[str, Any]:
    signals = ObservationSignals(
        timestamp=datetime.now(UTC),
        meta={"roas": 3.8, "frequency": 2.4, "ctr": 3.1},
        google={"roas": 2.9, "frequency": 0.0, "ctr": 4.2},
        competitor_signals={"saturated_angles": ["discount", "limited_time_offer"]},
        market_trends={"season": "q1", "theme": "self_improvement"},
        audience_behavior={"top_objection": "is this legit?"},
    )
    patch = {"signals": signals.model_dump(mode="json")}
    patch.update(
        _event(
            state,
            AgentName.OBSERVE,
            "observe_signals",
            "Collected platform + market + audience signals",
            0.85,
            {"meta_roas": 3.8, "google_roas": 2.9},
        )
    )
    return patch


def growth_strategist_agent(state: dict[str, Any]) -> dict[str, Any]:
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
        objective=state["brand"]["goal"],
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
            "Ranked hypotheses using competitor gaps + strategy memory",
            0.87,
            {"top_hypothesis": hypotheses[0].statement},
        )
    )
    return patch


def creative_generation_agent(state: dict[str, Any]) -> dict[str, Any]:
    hypothesis_id = state["hypotheses"][0]["hypothesis_id"]
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
            "Generated variant set from top trust hypothesis",
            0.82,
            {"variant_count": len(variants)},
        )
    )
    return patch


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
            "build_audience_plan",
            "Built audience model with belief state + trigger + objection",
            0.84,
            {"segment": segment.name, "overlap_risk_percent": 11.0},
        )
    )
    return patch


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
            "Allocated portfolio budget across channels",
            0.8,
            {"meta_budget": meta_budget, "google_budget": google_budget},
        )
    )
    return patch


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
            "Created execution payloads for ad platform adapters",
            0.78,
            {"experiment_id": experiment.experiment_id},
        )
    )
    return patch


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
            "Assigned verdict and generated downstream briefs",
            0.86,
            {"outcome": verdict.hypothesis_outcome.value, "route": verdict.route.value},
        )
    )
    return patch


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
            "Persisted structured learning into shared memory",
            0.9,
            {"learning": log_entry["learning"]},
        )
    )
    return patch


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
    return patch


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
    graph.add_edge("strategize", "target")
    graph.add_edge("create", "allocate")
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
