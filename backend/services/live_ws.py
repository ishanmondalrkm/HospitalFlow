"""WebSocket fan-out for Phase 8E live HospitalFlow updates."""
from __future__ import annotations

import asyncio
from typing import Any

from fastapi import WebSocket
from fastapi.encoders import jsonable_encoder


class LiveConnectionManager:
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

    async def broadcast(self, event: dict[str, Any]) -> None:
        payload = jsonable_encoder(event)
        async with self._lock:
            connections = list(self._connections)
        if not connections:
            return

        async def send_one(websocket: WebSocket) -> None:
            try:
                await websocket.send_json(payload)
            except Exception:
                await self.disconnect(websocket)

        await asyncio.gather(*(send_one(ws) for ws in connections), return_exceptions=True)

    @property
    def connection_count(self) -> int:
        return len(self._connections)


manager = LiveConnectionManager()
