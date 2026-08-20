from __future__ import annotations

import asyncio
from collections import defaultdict

from fastapi import WebSocket


class ConnectionHub:
    def __init__(self) -> None:
        self._connections: dict[int, list[WebSocket]] = defaultdict(list)
        self._loop: asyncio.AbstractEventLoop | None = None

    def set_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    async def connect(self, user_id: int, ws: WebSocket) -> None:
        await ws.accept()
        self._connections[user_id].append(ws)

    def disconnect(self, user_id: int, ws: WebSocket) -> None:
        conns = self._connections.get(user_id, [])
        if ws in conns:
            conns.remove(ws)

    def send_to_user(self, user_id: int, payload: dict) -> None:
        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(self._broadcast(user_id, payload), self._loop)
            return
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._broadcast(user_id, payload))
        except RuntimeError:
            pass

    async def _broadcast(self, user_id: int, payload: dict) -> None:
        dead: list[WebSocket] = []
        for ws in list(self._connections.get(user_id, [])):
            try:
                await ws.send_json(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(user_id, ws)


hub = ConnectionHub()
