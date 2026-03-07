from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any

from app.core.models import (
    ARIAState,
    AgentEvent,
    AgentName,
    AgentState,
    AgentStatus,
    BrandDNA,
    BrandInput,
    InitRequest,
    PerformanceHistory,
    PlatformPerformanceRecord,
    SharedMemory,
)


class InMemoryRuntime:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._state: ARIAState | None = None
        self._event_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()

    @property
    def event_queue(self) -> asyncio.Queue[dict[str, Any]]:
        return self._event_queue

    async def init_run(self, request: InitRequest) -> ARIAState:
        async with self._lock:
            brand = BrandInput(
                url=request.url,
                goal=request.goal,
                budget_daily=request.budget_daily,
                business_type=request.business_type,
                brand_name=request.brand_name,
            )
            memory = SharedMemory(
                brand_dna=BrandDNA(name=request.brand_name, business_type=request.business_type),
                production_information={
                    "product_name": request.brand_name,
                    "product_category": "",
                    "offer_summary": "",
                    "price_point": "",
                    "brand_url": request.url,
                },
                target_audience={
                    "primary_segment": "",
                    "age_range": "",
                    "geography": [],
                    "interests": [],
                    "belief_state": "",
                    "key_objections": [],
                },
                generations={
                    "copies_per_cycle": 5,
                    "max_generations": 3,
                    "active_generation": 1,
                },
                performance_history=PerformanceHistory(
                    platform_user_click_history=[
                        PlatformPerformanceRecord(
                            platform="meta",
                            user_clicks=0,
                            integrations_from_sites=["meta_ads"],
                            paid_conversions=0,
                            conversion_rate=0.0,
                        ),
                        PlatformPerformanceRecord(
                            platform="google",
                            user_clicks=0,
                            integrations_from_sites=["google_ads"],
                            paid_conversions=0,
                            conversion_rate=0.0,
                        ),
                    ],
                    cross_site_integrations=["meta_ads", "google_ads"],
                    overall_conversion_rate=0.0,
                ),
            )
            self._state = ARIAState(
                brand=brand,
                memory=memory,
                budget_plan={"total_budget": request.budget_daily},
                agent_states={name: AgentState(status=AgentStatus.IDLE) for name in AgentName},
            )
            await self.publish_event(
                AgentEvent(
                    run_id=self._state.run_id,
                    iteration=self._state.iteration,
                    agent=AgentName.OBSERVE,
                    action="init",
                    reason="ARIA run initialized",
                    confidence=1.0,
                    diff={
                        "goal": request.goal.value,
                        "budget_daily": request.budget_daily,
                        "url": str(request.url),
                    },
                )
            )
            return self._state

    async def get_state(self) -> ARIAState | None:
        async with self._lock:
            return self._state

    async def set_state(self, state: ARIAState) -> None:
        async with self._lock:
            self._state = state

    async def patch_state(self, **kwargs: Any) -> ARIAState | None:
        async with self._lock:
            if self._state is None:
                return None
            patched = self._state.model_copy(update=kwargs)
            self._state = patched
            return self._state

    async def publish_event(self, event: AgentEvent) -> None:
        await self._event_queue.put(event.model_dump(mode="json"))
        async with self._lock:
            if self._state is None:
                return
            self._state.events.append(event)
            if event.agent in self._state.agent_states:
                self._state.agent_states[event.agent] = AgentState(
                    status=AgentStatus.RUNNING,
                    last_update=datetime.now(UTC),
                )

    async def emit_existing_event(self, event: AgentEvent) -> None:
        """Queue an event for websocket broadcast without mutating in-memory state."""
        await self._event_queue.put(event.model_dump(mode="json"))


runtime = InMemoryRuntime()
