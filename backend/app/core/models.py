from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class BusinessType(str, Enum):
    B2B = "B2B"
    B2C = "B2C"


class GoalType(str, Enum):
    PURCHASES = "purchases"
    LEADS = "leads"
    AWARENESS = "awareness"
    INSTALLS = "installs"


class AgentName(str, Enum):
    OBSERVE = "observe"
    STRATEGIST = "strategist"
    CREATIVE = "creative"
    AUDIENCE = "audience"
    BUDGET = "budget"
    EXECUTE = "execute"
    EVALUATE = "evaluate"
    LEARN = "learn"
    NOTIFY = "notify"


class AgentStatus(str, Enum):
    IDLE = "idle"
    THINKING = "thinking"
    RUNNING = "running"
    WAITING = "waiting"


class HypothesisOutcome(str, Enum):
    CONFIRMED = "CONFIRMED"
    REJECTED = "REJECTED"
    INCONCLUSIVE = "INCONCLUSIVE"


class ExperimentStatus(str, Enum):
    DRAFT = "draft"
    RUNNING = "running"
    COMPLETED = "completed"
    KILLED = "killed"


class RouteAfterEval(str, Enum):
    KILL_AND_RERUN = "kill_and_rerun"
    SCALE_WINNER = "scale_winner"
    INCONCLUSIVE = "inconclusive"
    COMPLETE = "complete"


class BrandDNA(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = ""
    voice: str = ""
    values: list[str] = Field(default_factory=list)
    non_negotiables: list[str] = Field(default_factory=list)
    usp: str = ""
    business_type: BusinessType = BusinessType.B2C


class BrandInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    url: HttpUrl
    goal: GoalType
    budget_daily: float = Field(gt=0)
    business_type: BusinessType
    brand_name: str = ""


class MarketMap(BaseModel):
    model_config = ConfigDict(extra="forbid")

    competitors: list[str] = Field(default_factory=list)
    their_angles: list[str] = Field(default_factory=list)
    saturated_messages: list[str] = Field(default_factory=list)
    open_gaps: list[str] = Field(default_factory=list)


class AudienceTruth(BaseModel):
    model_config = ConfigDict(extra="forbid")

    segments: list[str] = Field(default_factory=list)
    belief_states: list[str] = Field(default_factory=list)
    proven_triggers: list[str] = Field(default_factory=list)
    proven_objections: list[str] = Field(default_factory=list)
    b2b_intent_signals: list[str] = Field(default_factory=list)


class ProductionInformation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    product_name: str = ""
    product_category: str = ""
    offer_summary: str = ""
    price_point: str = ""
    brand_url: HttpUrl | None = None


class PlatformContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    channels: list[Literal["webads", "images", "videos"]] = Field(
        default_factory=lambda: ["webads", "images", "videos"]
    )
    images_required: int = Field(default=5, ge=0)
    videos_required: int = Field(default=2, ge=0)


class TargetAudienceProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    primary_segment: str = ""
    age_range: str = ""
    geography: list[str] = Field(default_factory=list)
    interests: list[str] = Field(default_factory=list)
    belief_state: str = ""
    key_objections: list[str] = Field(default_factory=list)


class GenerationSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    copies_per_cycle: int = Field(default=5, ge=1)
    max_generations: int = Field(default=3, ge=1)
    active_generation: int = Field(default=1, ge=1)


class ExperimentLogEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    experiment_id: str
    date: datetime = Field(default_factory=lambda: datetime.now(UTC))
    hypothesis: str
    result: HypothesisOutcome
    confidence: float = Field(ge=0.0, le=1.0)
    learning: str
    conditions: dict[str, Any] = Field(default_factory=dict)


class StrategyMemory(BaseModel):
    model_config = ConfigDict(extra="forbid")

    iteration: int = 0
    current_winning_angle: str = ""
    retired_angles: list[str] = Field(default_factory=list)
    performance_trajectory: list[float] = Field(default_factory=list)
    next_hypotheses_ranked: list[str] = Field(default_factory=list)


class PlatformPerformanceRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    platform: str
    user_clicks: int = Field(default=0, ge=0)
    integrations_from_sites: list[str] = Field(default_factory=list)
    paid_conversions: int = Field(default=0, ge=0)
    conversion_rate: float = Field(default=0.0, ge=0.0, le=1.0)


class PerformanceHistory(BaseModel):
    model_config = ConfigDict(extra="forbid")

    by_channel: dict[str, dict[str, float]] = Field(default_factory=dict)
    by_creative_type: dict[str, dict[str, float]] = Field(default_factory=dict)
    by_audience_segment: dict[str, dict[str, float]] = Field(default_factory=dict)
    by_time_of_day: dict[str, dict[str, float]] = Field(default_factory=dict)
    by_season: dict[str, dict[str, float]] = Field(default_factory=dict)
    platform_user_click_history: list[PlatformPerformanceRecord] = Field(default_factory=list)
    cross_site_integrations: list[str] = Field(default_factory=list)
    overall_conversion_rate: float = Field(default=0.0, ge=0.0, le=1.0)


class SharedMemory(BaseModel):
    model_config = ConfigDict(extra="forbid")

    brand_dna: BrandDNA = Field(default_factory=BrandDNA)
    production_information: ProductionInformation = Field(default_factory=ProductionInformation)
    platform_context: PlatformContext = Field(default_factory=PlatformContext)
    target_audience: TargetAudienceProfile = Field(default_factory=TargetAudienceProfile)
    generations: GenerationSettings = Field(default_factory=GenerationSettings)
    market_map: MarketMap = Field(default_factory=MarketMap)
    audience_truth: AudienceTruth = Field(default_factory=AudienceTruth)
    experiment_log: list[ExperimentLogEntry] = Field(default_factory=list)
    strategy_memory: StrategyMemory = Field(default_factory=StrategyMemory)
    performance_history: PerformanceHistory = Field(default_factory=PerformanceHistory)


class ObservationSignals(BaseModel):
    model_config = ConfigDict(extra="forbid")

    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    meta: dict[str, float] = Field(default_factory=dict)
    google: dict[str, float] = Field(default_factory=dict)
    competitor_signals: dict[str, Any] = Field(default_factory=dict)
    market_trends: dict[str, Any] = Field(default_factory=dict)
    audience_behavior: dict[str, Any] = Field(default_factory=dict)


class Hypothesis(BaseModel):
    model_config = ConfigDict(extra="forbid")

    hypothesis_id: str = Field(default_factory=lambda: f"hyp_{uuid4().hex[:8]}")
    statement: str
    rationale: str
    confidence: float = Field(ge=0.0, le=1.0)
    success_metric: str = "roas"
    target_lift_percent: float = 0.0
    priority: int = Field(ge=1, le=10, default=5)


class CampaignBrief(BaseModel):
    model_config = ConfigDict(extra="forbid")

    objective: GoalType
    angle: str
    channel_mix: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)


class CreativeVariant(BaseModel):
    model_config = ConfigDict(extra="forbid")

    variant_id: str = Field(default_factory=lambda: f"cr_{uuid4().hex[:8]}")
    hook: str
    body: str
    cta: str
    format: Literal["image", "video", "carousel", "search"] = "image"
    source_hypothesis_id: str


class AudienceSegment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    segment_id: str = Field(default_factory=lambda: f"seg_{uuid4().hex[:8]}")
    name: str
    business_type: BusinessType
    belief_state: str
    purchase_trigger: str
    objection: str
    message_angle: str
    targeting_layers: list[str] = Field(default_factory=list)


class AudiencePlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    segments: list[AudienceSegment] = Field(default_factory=list)
    overlap_risk_percent: float = Field(default=0.0, ge=0.0, le=100.0)
    recommendations: list[str] = Field(default_factory=list)


class PlatformAllocation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    platform: Literal["meta", "google"]
    budget: float = Field(ge=0.0)
    rationale: str


class BudgetPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total_budget: float = Field(ge=0.0)
    allocations: list[PlatformAllocation] = Field(default_factory=list)
    pacing_action: str = "hold"
    guardrails_applied: list[str] = Field(default_factory=list)


class ExperimentMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    impressions: int = Field(default=0, ge=0)
    clicks: int = Field(default=0, ge=0)
    spend: float = Field(default=0.0, ge=0.0)
    conversions: int = Field(default=0, ge=0)
    roas: float = Field(default=0.0, ge=0.0)
    cpa: float = Field(default=0.0, ge=0.0)
    ctr: float = Field(default=0.0, ge=0.0)
    cvr: float = Field(default=0.0, ge=0.0)


class Experiment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    experiment_id: str = Field(default_factory=lambda: f"exp_{uuid4().hex[:8]}")
    hypothesis_id: str
    status: ExperimentStatus = ExperimentStatus.DRAFT
    channels: list[str] = Field(default_factory=list)
    start_time: datetime | None = None
    end_time: datetime | None = None
    success_metric: str = "roas"
    metrics: ExperimentMetrics = Field(default_factory=ExperimentMetrics)


class MemoryWritePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pattern: str
    conditions: dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(ge=0.0, le=1.0)
    n_experiments: int = Field(default=1, ge=1)


class EvaluationVerdict(BaseModel):
    model_config = ConfigDict(extra="forbid")

    hypothesis_outcome: HypothesisOutcome
    confidence_score: float = Field(ge=0.0, le=1.0)
    winning_element: str
    effect_size: str
    statistical_significance: bool
    sample_size_adequate: bool
    brief_to_creative: str
    brief_to_audience: str
    brief_to_budget: str
    brief_to_strategist: str
    write_to_memory: MemoryWritePayload
    route: RouteAfterEval = RouteAfterEval.COMPLETE


class AgentEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: str = Field(default_factory=lambda: f"evt_{uuid4().hex[:8]}")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    run_id: str
    iteration: int
    agent: AgentName
    action: str
    reason: str
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    diff: dict[str, Any] = Field(default_factory=dict)


class AgentState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: AgentStatus = AgentStatus.IDLE
    last_update: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ARIAState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str = Field(default_factory=lambda: f"run_{uuid4().hex[:8]}")
    iteration: int = 0
    brand: BrandInput
    memory: SharedMemory = Field(default_factory=SharedMemory)
    signals: ObservationSignals = Field(default_factory=ObservationSignals)
    hypotheses: list[Hypothesis] = Field(default_factory=list)
    campaign_brief: CampaignBrief | None = None
    creative_variants: list[CreativeVariant] = Field(default_factory=list)
    audience_plan: AudiencePlan = Field(default_factory=AudiencePlan)
    budget_plan: BudgetPlan = Field(default_factory=lambda: BudgetPlan(total_budget=0.0))
    experiments: list[Experiment] = Field(default_factory=list)
    evaluation: EvaluationVerdict | None = None
    events: list[AgentEvent] = Field(default_factory=list)
    paused: bool = False
    pause_reason: str = ""
    agent_states: dict[AgentName, AgentState] = Field(
        default_factory=lambda: {name: AgentState() for name in AgentName}
    )


class InitRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    url: HttpUrl
    goal: GoalType
    budget_daily: float = Field(gt=0)
    business_type: BusinessType
    brand_name: str = ""


class InitResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    message: str


class ApproveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    approved: bool
    note: str = ""


class PauseRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str = Field(min_length=3)


class StatusResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    iteration: int
    paused: bool
    goal: GoalType
    budget_daily: float
    agent_states: dict[AgentName, AgentState]


class PerformanceResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    unified_roas: float
    meta_roas: float
    google_roas: float
    cpa: float
    ctr: float
    cvr: float
