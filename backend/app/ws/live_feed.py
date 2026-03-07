from __future__ import annotations

import asyncio
from collections.abc import Iterable

from fastapi import WebSocket


class LiveFeedManager:
    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections.add(websocket)

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._connections.discard(websocket)

    async def send_many(self, websocket: WebSocket, payloads: Iterable[dict]) -> None:
        for payload in payloads:
            await websocket.send_json(payload)

    async def broadcast(self, payload: dict) -> None:
        async with self._lock:
            recipients = list(self._connections)

        stale: list[WebSocket] = []
        for conn in recipients:
            try:
                await conn.send_json(payload)
            except Exception:
                stale.append(conn)

        if stale:
            async with self._lock:
                for conn in stale:
                    self._connections.discard(conn)


live_feed_manager = LiveFeedManager()
