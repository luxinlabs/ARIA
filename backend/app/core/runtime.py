from __future__ import annotations

import asyncio
import json
import re
from contextlib import suppress
from datetime import UTC, datetime
from html import unescape
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

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
        self._states: dict[str, ARIAState] = {}
        self._active_run_id: str | None = None
        self._event_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._openai = OpenAI(api_key=OPENAI_API_KEY)

    @property
    def event_queue(self) -> asyncio.Queue[dict[str, Any]]:
        return self._event_queue

    def _extract_website_context(self, html: str, url: str) -> dict[str, Any]:
        title_match = re.search(r"<title[^>]*>(.*?)</title>", html, flags=re.IGNORECASE | re.DOTALL)
        meta_desc_match = re.search(
            r'<meta[^>]+name=["\']description["\'][^>]+content=["\'](.*?)["\']',
            html,
            flags=re.IGNORECASE | re.DOTALL,
        )
        h1_match = re.search(r"<h1[^>]*>(.*?)</h1>", html, flags=re.IGNORECASE | re.DOTALL)

        text_content = re.sub(r"<script[\s\S]*?</script>", " ", html, flags=re.IGNORECASE)
        text_content = re.sub(r"<style[\s\S]*?</style>", " ", text_content, flags=re.IGNORECASE)
        text_content = re.sub(r"<[^>]+>", " ", text_content)
        text_content = unescape(re.sub(r"\s+", " ", text_content)).strip()

        return {
            "url": url,
            "title": unescape(title_match.group(1)).strip() if title_match else "",
            "meta_description": unescape(meta_desc_match.group(1)).strip() if meta_desc_match else "",
            "h1": unescape(h1_match.group(1)).strip() if h1_match else "",
            "text_excerpt": text_content[:4000],
        }

    def _fetch_website_context(self, url: str) -> dict[str, Any]:
        request = Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; ARIABot/1.0; +https://aria.local)",
                "Accept": "text/html,application/xhtml+xml",
            },
        )
        try:
            with urlopen(request, timeout=15) as response:
                content_type = response.headers.get("Content-Type", "")
                if "text/html" not in content_type:
                    raise RuntimeError(f"Website did not return HTML content (content-type: {content_type})")
                html = response.read().decode("utf-8", errors="ignore")
        except (HTTPError, URLError, TimeoutError) as exc:
            raise RuntimeError(f"Failed to fetch website content from {url}: {exc}") from exc

        context = self._extract_website_context(html, url)
        if not context["text_excerpt"]:
            raise RuntimeError(f"Website content from {url} is empty or unreadable")
        return context

    async def _generate_strategy_seed(self, request: InitRequest) -> dict[str, Any]:
        website_context = await asyncio.to_thread(self._fetch_website_context, str(request.url))

        system_prompt = (
            "You are a staff marketing and strategy lead. "
            "Given real website content and business goal, produce a practical initialization strategy payload "
            "for ad operations. Return strict JSON only."
        )
        user_prompt = f"""
Generate initialization JSON for this brand:
- brand_name: {request.brand_name}
- brand_url: {request.url}
- goal: {request.goal.value}
- budget_daily: {request.budget_daily}
- business_type: {request.business_type.value}

Website evidence (must use this, do not invent demo placeholders):
- page_title: {website_context['title']}
- meta_description: {website_context['meta_description']}
- h1: {website_context['h1']}
- text_excerpt: {website_context['text_excerpt']}

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
- Fill all string fields with non-empty, realistic values derived from the provided website evidence.
- Production information must be grounded in website evidence above; do not use generic demo/fallback product data.
- Set production_information.brand_url to the exact brand_url above.
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

        production_information = payload.get("production_information", {})
        required_production_fields = ("product_name", "product_category", "offer_summary", "price_point")
        missing_production_fields = [
            field for field in required_production_fields if not str(production_information.get(field, "")).strip()
        ]
        if missing_production_fields:
            raise RuntimeError(f"Website-derived production information missing fields: {missing_production_fields}")
        production_information["brand_url"] = str(request.url)

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
            new_state = ARIAState(
                brand=brand,
                memory=memory,
                budget_plan={"total_budget": request.budget_daily},
                agent_states={name: AgentState(status=AgentStatus.IDLE) for name in AgentName},
            )
            self._states[new_state.run_id] = new_state
            self._active_run_id = new_state.run_id
            init_event = AgentEvent(
                run_id=new_state.run_id,
                iteration=new_state.iteration,
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
            return self._states[init_event.run_id]

    async def list_sessions(self) -> list[dict[str, Any]]:
        async with self._lock:
            sessions = []
            for run_id, state in self._states.items():
                sessions.append(
                    {
                        "run_id": run_id,
                        "iteration": state.iteration,
                        "goal": state.brand.goal.value,
                        "budget_daily": state.brand.budget_daily,
                        "brand_name": state.brand.brand_name,
                        "paused": state.paused,
                        "is_active": run_id == self._active_run_id,
                        "updated_at": state.agent_states[AgentName.OBSERVE].last_update.isoformat(),
                    }
                )
            sessions.sort(key=lambda item: item["updated_at"], reverse=True)
            return sessions

    async def get_state(self, run_id: str | None = None) -> ARIAState | None:
        async with self._lock:
            target_id = run_id or self._active_run_id
            if not target_id:
                return None
            return self._states.get(target_id)

    async def set_active_run(self, run_id: str) -> ARIAState | None:
        async with self._lock:
            state = self._states.get(run_id)
            if state is None:
                return None
            self._active_run_id = run_id
            return state

    async def set_state(self, state: ARIAState, run_id: str | None = None) -> None:
        async with self._lock:
            target_id = run_id or state.run_id
            self._states[target_id] = state
            if self._active_run_id is None:
                self._active_run_id = target_id

    async def clear_state(self, run_id: str | None = None) -> None:
        async with self._lock:
            target_id = run_id or self._active_run_id
            if target_id:
                self._states.pop(target_id, None)
                if self._active_run_id == target_id:
                    self._active_run_id = next(iter(self._states), None)
            if self._states:
                return
            while True:
                with suppress(asyncio.QueueEmpty):
                    self._event_queue.get_nowait()
                    continue
                break

    async def patch_state(self, run_id: str | None = None, **kwargs: Any) -> ARIAState | None:
        async with self._lock:
            target_id = run_id or self._active_run_id
            if target_id is None:
                return None
            state = self._states.get(target_id)
            if state is None:
                return None
            patched = state.model_copy(update=kwargs)
            self._states[target_id] = patched
            return patched

    async def publish_event(self, event: AgentEvent) -> None:
        await self._event_queue.put(event.model_dump(mode="json"))
        async with self._lock:
            state = self._states.get(event.run_id)
            if state is None:
                return
            state.events.append(event)
            if event.agent in state.agent_states:
                state.agent_states[event.agent] = AgentState(
                    status=AgentStatus.RUNNING,
                    last_update=datetime.now(UTC),
                )

    async def emit_existing_event(self, event: AgentEvent) -> None:
        """Queue an event for websocket broadcast without mutating in-memory state."""
        await self._event_queue.put(event.model_dump(mode="json"))


runtime = InMemoryRuntime()
