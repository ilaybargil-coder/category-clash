"""In-process room registry + WebSocket fan-out.

Free-beta note: live room state is held in one backend process. No external
cache or distributed room-state service is configured in Milestone B.
"""

from __future__ import annotations

import asyncio
import logging
import secrets
from collections import defaultdict

from fastapi import WebSocket

from ..config import settings
from ..db import SessionLocal
from .db_io import DbResultSink, make_question_provider
from .engine import GameConfig, GameRoom

logger = logging.getLogger(__name__)

# No ambiguous chars (0/O, 1/I/L) — codes get typed by hand.
_CODE_ALPHABET = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"


def game_config_from_settings() -> GameConfig:
    return GameConfig(
        turn_seconds=settings.turn_seconds,
        preview_seconds=settings.preview_seconds,
        intermission_seconds=settings.intermission_seconds,
        rounds_to_win=settings.rounds_to_win,
        max_answer_length=settings.max_answer_length,
        disconnect_forfeit_seconds=settings.disconnect_forfeit_seconds,
        fuzzy_matching_enabled=settings.fuzzy_matching_enabled,
        fuzzy_max_distance=settings.fuzzy_max_distance,
        fuzzy_min_length=settings.fuzzy_min_length,
    )


class RoomManager:
    def __init__(self) -> None:
        self.rooms: dict[str, GameRoom] = {}
        self._sockets: dict[str, set[WebSocket]] = defaultdict(set)
        self._send_locks: dict[WebSocket, asyncio.Lock] = {}

    def _new_code(self) -> str:
        while True:
            code = "".join(secrets.choice(_CODE_ALPHABET) for _ in range(5))
            if code not in self.rooms:
                return code

    def create_room(self) -> GameRoom:
        code = self._new_code()

        async def broadcast(event: dict) -> None:
            await self.broadcast(code, event)

        room = GameRoom(
            code=code,
            config=game_config_from_settings(),
            question_provider=make_question_provider(SessionLocal),
            broadcaster=broadcast,
            sink=DbResultSink(SessionLocal),
        )
        self.rooms[code] = room
        return room

    def get(self, code: str) -> GameRoom | None:
        return self.rooms.get(code.upper())

    async def broadcast(self, code: str, event: dict) -> None:
        sockets = list(self._sockets.get(code, ()))
        if sockets:
            await asyncio.gather(
                *(self.send(ws, event) for ws in sockets),
                return_exceptions=True,
            )

    async def send(self, ws: WebSocket, event: dict) -> None:
        lock = self._send_locks.setdefault(ws, asyncio.Lock())
        try:
            async with lock:
                await asyncio.wait_for(
                    ws.send_json(event),
                    timeout=settings.websocket_send_timeout_seconds,
                )
        except Exception:
            logger.warning("WebSocket send failed", exc_info=True)
            raise

    def register(self, code: str, ws: WebSocket) -> None:
        self._sockets[code].add(ws)
        self._send_locks.setdefault(ws, asyncio.Lock())

    def sockets_for(self, code: str) -> set[WebSocket]:
        return self._sockets.get(code, set())

    def unregister(self, code: str, ws: WebSocket) -> None:
        self._sockets[code].discard(ws)
        self._send_locks.pop(ws, None)

    def remove_if_unused(self, code: str) -> None:
        room = self.rooms.get(code)
        if room and room.is_empty and (room.is_over or not self._sockets[code]):
            if room.is_over or room.phase.value == "WAITING_FOR_PLAYERS":
                room.cancel_background_tasks()
                self.rooms.pop(code, None)
                self._sockets.pop(code, None)


room_manager = RoomManager()
