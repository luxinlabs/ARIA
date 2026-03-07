from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes_aria import router as aria_router
from app.core.runtime import runtime
from app.ws.live_feed import live_feed_manager


async def _event_broadcaster(stop_event: asyncio.Event) -> None:
    while not stop_event.is_set():
        payload = await runtime.event_queue.get()
        await live_feed_manager.broadcast(payload)


@asynccontextmanager
async def lifespan(_: FastAPI):
    stop_event = asyncio.Event()
    broadcaster_task = asyncio.create_task(_event_broadcaster(stop_event))
    try:
        yield
    finally:
        stop_event.set()
        broadcaster_task.cancel()
        with suppress(asyncio.CancelledError):
            await broadcaster_task


app = FastAPI(title="ARIA Backend", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(aria_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
