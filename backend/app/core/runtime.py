from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from typing import Any

from openai import OpenAI

from app.config import DEFAULT_MODEL, OPENAI_API_KEY
from app.core.models import (
    ARIAState,
    AgentEvent,
    AgentName,
    AgentState,
    AgentStatus,
    BrandDNA,
    BrandInput,
    InitRequest,
    SharedMemory,
)


class InMemoryRuntime:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._state: ARIAState | None = None
        self._event_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._openai = OpenAI(api_key=OPENAI_API_KEY)

    @property
    def event_queue(self) -> asyncio.Queue[dict[str, Any]]:
        return self._event_queue

    async def _generate_strategy_seed(self, request: InitRequest) -> dict[str, Any]:
        system_prompt = (
            "You are a staff marketing and strategy lead. "
            "Given a brand URL and business goal, produce a practical initialization strategy payload "
            "for ad operations. Return strict JSON only."
        )
        user_prompt = f"""
Generate initialization JSON for this brand:
- brand_name: {request.brand_name}
- brand_url: {request.url}
- goal: {request.goal.value}
- budget_daily: {request.budget_daily}
- business_type: {request.business_type.value}

Required JSON schema:
{{
  "production_information": {{
    "product_name": string,
    "product_category": string,
    "offer_summary": string,
    "price_point": string,
    "brand_url": string
  }},
  "platform": {{
    "channels": ["webads", "images", "videos"],
    "images_required": int,
    "videos_required": int
  }},
  "target_audience": {{
    "primary_segment": string,
    "age_range": string,
    "geography": string[],
    "interests": string[],
    "belief_state": string,
    "key_objections": string[]
  }},
  "generations": {{
    "copies_per_cycle": int,
    "max_generations": int,
    "active_generation": int
  }},
  "performance_history": {{
    "platform_user_click_history": [
      {{
        "platform": "meta" | "google",
        "user_clicks": int,
        "integrations_from_sites": string[],
        "paid_conversions": int,
        "conversion_rate": float
      }}
    ],
    "cross_site_integrations": string[],
    "overall_conversion_rate": float
  }}
}}

Rules:
- Fill all string fields with non-empty, realistic values derived from the brand context.
- conversions/user_clicks should be coherent with conversion_rate (0.0 to 1.0).
- max_generations >= active_generation >= 1.
- copies_per_cycle >= 1.
- images_required/videos_required >= 0.
- Return JSON only, no markdown.
"""

        def _call_openai() -> str:
            response = self._openai.chat.completions.create(
                model=DEFAULT_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,
                max_tokens=1200,
            )
            return (response.choices[0].message.content or "").strip()

        raw = await asyncio.to_thread(_call_openai)
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise RuntimeError("OpenAI initialization payload was not valid JSON") from exc

        required_keys = {
            "production_information",
            "platform",
            "target_audience",
            "generations",
            "performance_history",
        }
        if not required_keys.issubset(payload.keys()):
            missing = sorted(required_keys - set(payload.keys()))
            raise RuntimeError(f"OpenAI initialization payload missing keys: {missing}")

        return payload

    async def init_run(self, request: InitRequest) -> ARIAState:
        init_event: AgentEvent | None = None
        strategy_seed = await self._generate_strategy_seed(request)

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
                production_information=strategy_seed["production_information"],
                platform_context=strategy_seed["platform"],
                target_audience=strategy_seed["target_audience"],
                generations=strategy_seed["generations"],
                performance_history=strategy_seed["performance_history"],
            )
            self._state = ARIAState(
                brand=brand,
                memory=memory,
                budget_plan={"total_budget": request.budget_daily},
                agent_states={name: AgentState(status=AgentStatus.IDLE) for name in AgentName},
            )
            init_event = AgentEvent(
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

        # Publish after releasing lock to avoid deadlock in publish_event.
        await self.publish_event(init_event)

        async with self._lock:
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
