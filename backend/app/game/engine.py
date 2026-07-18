"""Authoritative game engine.

A GameRoom owns the full state of one match. Every mutation happens under an
asyncio.Lock, so two answers (or an answer racing the timer) are always
resolved in a single, deterministic order. Timers are generation-guarded:
arming a new timer bumps the generation, so a stale sleeping task wakes up,
sees a mismatched generation and does nothing.

The engine has no FastAPI / DB imports — questions arrive via an injected
async provider and results leave via an injected sink, which keeps the whole
state machine unit-testable without infrastructure.
"""

from __future__ import annotations

import asyncio
import logging
import random
import time
import uuid
from dataclasses import dataclass
from enum import Enum
from typing import Awaitable, Callable, Optional

from ..protocol import make_server_event
from .validator import AnswerStatus, QuestionData, RoundValidator

logger = logging.getLogger(__name__)

Broadcaster = Callable[[dict], Awaitable[None]]
QuestionProvider = Callable[[set[int]], Awaitable[Optional[QuestionData]]]


class RoomPhase(str, Enum):
    WAITING_FOR_PLAYERS = "WAITING_FOR_PLAYERS"
    QUESTION_PREVIEW = "QUESTION_PREVIEW"
    ROUND_ACTIVE = "ROUND_ACTIVE"
    ROUND_FINISHED = "ROUND_FINISHED"
    MATCH_FINISHED = "MATCH_FINISHED"
    ABANDONED = "ABANDONED"


class MatchEndReason(str, Enum):
    SCORE = "SCORE"
    FORFEIT = "FORFEIT"


class PowerUpStatus(str, Enum):
    USED = "USED"
    ALREADY_USED = "ALREADY_USED"
    NOT_AVAILABLE = "NOT_AVAILABLE"


@dataclass
class GameConfig:
    turn_seconds: float = 15.0
    preview_seconds: float = 4.0
    intermission_seconds: float = 4.0
    rounds_to_win: int = 2
    max_answer_length: int = 60
    disconnect_forfeit_seconds: float = 60.0
    fuzzy_matching_enabled: bool = False
    fuzzy_max_distance: int = 2
    fuzzy_min_length: int = 4
    fuzzy_two_edit_min_length: int = 7
    hebrew_skeleton_matching_enabled: bool = False
    unique_prefix_matching_enabled: bool = True
    unique_prefix_min_length: int = 3
    definite_article_matching_enabled: bool = True


@dataclass
class Player:
    user_id: int
    username: str
    display_name: str
    connected: bool = True


@dataclass
class AnswerRecord:
    submission_id: str
    client_command_id: str | None
    user_id: int
    raw_text: str
    status: AnswerStatus
    canonical: str | None
    at_ms: int


class ResultSink:
    """Persistence hooks. The engine never fails because persistence failed."""

    async def on_match_start(self, code: str, p1_id: int, p2_id: int) -> None: ...
    async def on_round_start(
        self, code: str, round_no: int, question_id: int, starter_id: int
    ) -> None: ...
    async def on_question_swap(self, code: str, round_no: int, question_id: int) -> None: ...
    async def on_answer(
        self,
        code: str,
        round_no: int,
        submission_id: str,
        client_command_id: str | None,
        user_id: int,
        raw_text: str,
        normalized: str,
        status: str,
        matched_answer_id: int | None,
    ) -> None: ...
    async def on_round_end(self, code: str, round_no: int, winner_id: int, reason: str) -> None: ...
    async def on_match_end(
        self, code: str, winner_id: int, score: dict[int, int], reason: str
    ) -> None: ...


def now_ms() -> int:
    return int(time.time() * 1000)


class GameRoom:
    def __init__(
        self,
        code: str,
        config: GameConfig,
        question_provider: QuestionProvider,
        broadcaster: Broadcaster,
        sink: ResultSink | None = None,
    ) -> None:
        self.code = code
        self.config = config
        self._provider = question_provider
        self._broadcast_fn = broadcaster
        self._sink = sink or ResultSink()

        self.lock = asyncio.Lock()
        self.phase = RoomPhase.WAITING_FOR_PLAYERS
        self.players: dict[int, Player] = {}
        self.order: list[int] = []
        self.score: dict[int, int] = {}

        self.round_no = 0
        self.question: QuestionData | None = None
        self.used_question_ids: set[int] = set()
        self.validator: RoundValidator | None = None
        self.answers: list[AnswerRecord] = []

        self.turn_user_id: int | None = None
        self.round_starter_id: int | None = None
        self.first_starter_id: int | None = None
        self.turn_deadline: float | None = None  # event-loop monotonic time
        self.last_round_result: dict | None = None
        self.match_winner_id: int | None = None
        self.match_end_reason: MatchEndReason | None = None

        self._seq = 0
        self._timer_gen = 0
        self._preview_gen = 0
        self._forfeit_gens: dict[int, int] = {}
        self._tasks: set[asyncio.Task] = set()
        # Idempotency: (user_id, client_command_id) -> status of the processed
        # submission, so a client retry / double-click never creates a second
        # record or a second event.
        self._processed_commands: dict[tuple[int, str], AnswerStatus] = {}
        self.powerups_used: dict[int, set[str]] = {}
        self._processed_powerups: dict[tuple[int, str], PowerUpStatus] = {}

    # ---------------------------------------------------------------- utils

    def _spawn(self, coro) -> None:
        task = asyncio.create_task(coro)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    def cancel_background_tasks(self) -> None:
        for task in list(self._tasks):
            task.cancel()
        self._tasks.clear()

    def _other(self, user_id: int) -> int:
        return self.order[1] if self.order[0] == user_id else self.order[0]

    def _score_payload(self) -> list[dict]:
        return [{"user_id": uid, "points": self.score.get(uid, 0)} for uid in self.order]

    def _players_payload(self) -> list[dict]:
        return [
            {
                "user_id": p.user_id,
                "username": p.username,
                "display_name": p.display_name,
                "connected": p.connected,
            }
            for p in (self.players[uid] for uid in self.order)
        ]

    def _deadline_epoch_ms(self) -> int | None:
        if self.turn_deadline is None or self.phase != RoomPhase.ROUND_ACTIVE:
            return None
        remaining = max(0.0, self.turn_deadline - asyncio.get_running_loop().time())
        return now_ms() + int(remaining * 1000)

    async def _emit(self, event_type: str, **data) -> None:
        self._seq += 1
        event = make_server_event(event_type, seq=self._seq, match_id=self.code, **data)
        try:
            await self._broadcast_fn(event)
        except Exception:
            logger.exception("broadcast failed for room %s", self.code)

    async def _sink_safe(self, coro: Awaitable[None]) -> None:
        try:
            await coro
        except Exception:
            logger.exception("result sink failed for room %s", self.code)

    # ------------------------------------------------------------- snapshot

    def snapshot(self, for_user_id: int) -> dict:
        """Full state for (re)connecting clients."""
        return make_server_event(
            "state_sync",
            seq=self._seq,
            match_id=self.code,
            you=for_user_id,
            code=self.code,
            phase=self.phase.value,
            players=self._players_payload(),
            score=self._score_payload(),
            round_no=self.round_no,
            rounds_to_win=self.config.rounds_to_win,
            question=(
                {"id": self.question.id, "text": self.question.text} if self.question else None
            ),
            turn_user_id=self.turn_user_id,
            turn_seconds=self.config.turn_seconds,
            deadline_epoch_ms=self._deadline_epoch_ms(),
            answers=[
                {
                    "submission_id": a.submission_id,
                    "client_command_id": a.client_command_id,
                    "user_id": a.user_id,
                    "raw_text": a.raw_text,
                    "status": a.status.value,
                    "canonical": a.canonical,
                    "at_ms": a.at_ms,
                }
                for a in self.answers
            ],
            last_round_result=self.last_round_result,
            match_winner_id=self.match_winner_id,
            match_end_reason=(self.match_end_reason.value if self.match_end_reason else None),
            powerups={
                str(uid): {
                    "swap_question": "swap_question" not in self.powerups_used.get(uid, set()),
                    "extend_time": "extend_time" not in self.powerups_used.get(uid, set()),
                    "joker": "joker" not in self.powerups_used.get(uid, set()),
                }
                for uid in self.order
            },
        )

    # ------------------------------------------------------------ join/leave

    async def join(self, user_id: int, username: str, display_name: str) -> bool:
        """Add a player, or reconnect an existing one. False = room is full."""
        async with self.lock:
            existing = self.players.get(user_id)
            if existing is not None:
                existing.connected = True
                # Invalidate any pending forfeit countdown for this player.
                self._forfeit_gens[user_id] = self._forfeit_gens.get(user_id, 0) + 1
                await self._emit(
                    "player_reconnected", user_id=user_id, players=self._players_payload()
                )
                return True

            if len(self.players) >= 2 or self.phase != RoomPhase.WAITING_FOR_PLAYERS:
                return False

            self.players[user_id] = Player(user_id, username, display_name)
            self.order.append(user_id)
            self.score[user_id] = 0
            self.powerups_used[user_id] = set()
            await self._emit("player_joined", players=self._players_payload())

            if len(self.players) == 2:
                await self._start_match_locked()
            return True

    async def disconnect(self, user_id: int) -> None:
        async with self.lock:
            player = self.players.get(user_id)
            if player is None or not player.connected:
                return
            player.connected = False

            if self.phase == RoomPhase.WAITING_FOR_PLAYERS:
                # Match never started — free the slot entirely.
                del self.players[user_id]
                self.order.remove(user_id)
                self.score.pop(user_id, None)
                await self._emit("player_left", user_id=user_id, players=self._players_payload())
                return

            await self._emit(
                "player_disconnected",
                user_id=user_id,
                players=self._players_payload(),
                forfeit_seconds=self.config.disconnect_forfeit_seconds,
            )
            if self.phase in (RoomPhase.MATCH_FINISHED, RoomPhase.ABANDONED):
                return
            self._forfeit_gens[user_id] = self._forfeit_gens.get(user_id, 0) + 1
            self._spawn(self._forfeit_watch(user_id, self._forfeit_gens[user_id]))

    async def _forfeit_watch(self, user_id: int, gen: int) -> None:
        await asyncio.sleep(self.config.disconnect_forfeit_seconds)
        async with self.lock:
            if self._forfeit_gens.get(user_id) != gen:
                return  # player reconnected (or a newer countdown superseded us)
            player = self.players.get(user_id)
            if player is None or player.connected:
                return
            if self.phase in (RoomPhase.MATCH_FINISHED, RoomPhase.ABANDONED):
                return
            self._timer_gen += 1  # kill any live turn timer
            await self._finish_match_locked(
                winner_id=self._other(user_id), reason=MatchEndReason.FORFEIT
            )

    # ------------------------------------------------------------ match flow

    async def _start_match_locked(self) -> None:
        self.first_starter_id = random.choice(self.order)
        await self._sink_safe(self._sink.on_match_start(self.code, self.order[0], self.order[1]))
        await self._start_round_locked()

    async def _start_round_locked(self) -> None:
        question = await self._provider(set(self.used_question_ids))
        if question is None:
            logger.error("room %s: no questions available, abandoning", self.code)
            self.phase = RoomPhase.ABANDONED
            await self._emit("room_error", code="NO_QUESTIONS")
            return

        self.round_no += 1
        self.used_question_ids.add(question.id)
        self.question = question
        self.validator = RoundValidator(
            question.index,
            max_length=self.config.max_answer_length,
            fuzzy_enabled=self.config.fuzzy_matching_enabled,
            fuzzy_max_distance=self.config.fuzzy_max_distance,
            fuzzy_min_length=self.config.fuzzy_min_length,
            fuzzy_two_edit_min_length=self.config.fuzzy_two_edit_min_length,
            hebrew_skeleton_enabled=self.config.hebrew_skeleton_matching_enabled,
            unique_prefix_enabled=self.config.unique_prefix_matching_enabled,
            unique_prefix_min_length=self.config.unique_prefix_min_length,
            definite_article_enabled=self.config.definite_article_matching_enabled,
        )
        self.answers = []
        self.last_round_result = None

        if self.round_starter_id is None:
            starter = self.first_starter_id
        else:
            starter = self._other(self.round_starter_id)
        if starter is None:
            raise RuntimeError("round cannot start without a starter")
        self.round_starter_id = starter
        self.turn_user_id = starter
        self.phase = RoomPhase.QUESTION_PREVIEW

        await self._sink_safe(
            self._sink.on_round_start(self.code, self.round_no, question.id, starter)
        )
        await self._emit(
            "round_started",
            round_no=self.round_no,
            question={"id": question.id, "text": question.text},
            starter_user_id=starter,
            preview_seconds=self.config.preview_seconds,
            score=self._score_payload(),
        )
        self._preview_gen += 1
        self._spawn(self._preview_then_activate(self.round_no, self._preview_gen))

    async def _preview_then_activate(self, round_no: int, preview_gen: int) -> None:
        await asyncio.sleep(self.config.preview_seconds)
        async with self.lock:
            if (
                self.phase != RoomPhase.QUESTION_PREVIEW
                or self.round_no != round_no
                or self._preview_gen != preview_gen
            ):
                return
            self.phase = RoomPhase.ROUND_ACTIVE
            self._arm_timer_locked()
            await self._emit(
                "round_active",
                round_no=self.round_no,
                turn_user_id=self.turn_user_id,
                turn_seconds=self.config.turn_seconds,
                deadline_epoch_ms=self._deadline_epoch_ms(),
            )

    def _arm_timer_locked(self) -> None:
        self._timer_gen += 1
        self.turn_deadline = asyncio.get_running_loop().time() + self.config.turn_seconds
        self._spawn(self._watch_timer(self._timer_gen, self.turn_deadline))

    async def _watch_timer(self, gen: int, deadline: float) -> None:
        loop = asyncio.get_running_loop()
        await asyncio.sleep(max(0.0, deadline - loop.time()))
        async with self.lock:
            if gen != self._timer_gen or self.phase != RoomPhase.ROUND_ACTIVE:
                return  # timer was superseded by a valid answer / round end
            timed_out_user = self.turn_user_id
            if timed_out_user is None:
                return
            await self._emit("turn_timeout", user_id=timed_out_user)
            await self._end_round_locked(winner_id=self._other(timed_out_user), reason="TIMEOUT")

    async def _end_round_locked(self, winner_id: int, reason: str) -> None:
        self._timer_gen += 1
        self.turn_deadline = None
        self.phase = RoomPhase.ROUND_FINISHED
        self.score[winner_id] = self.score.get(winner_id, 0) + 1
        self.last_round_result = {
            "round_no": self.round_no,
            "winner_user_id": winner_id,
            "loser_user_id": self._other(winner_id),
            "reason": reason,
            "score": self._score_payload(),
        }
        await self._sink_safe(self._sink.on_round_end(self.code, self.round_no, winner_id, reason))
        await self._emit(
            "round_finished",
            **self.last_round_result,
            intermission_seconds=self.config.intermission_seconds,
        )
        if self.score[winner_id] >= self.config.rounds_to_win:
            await self._finish_match_locked(winner_id, MatchEndReason.SCORE)
        else:
            self._spawn(self._intermission_then_next(self.round_no))

    async def _intermission_then_next(self, round_no: int) -> None:
        await asyncio.sleep(self.config.intermission_seconds)
        async with self.lock:
            if self.phase != RoomPhase.ROUND_FINISHED or self.round_no != round_no:
                return
            await self._start_round_locked()

    async def _finish_match_locked(self, winner_id: int, reason: MatchEndReason) -> None:
        self.phase = RoomPhase.MATCH_FINISHED
        self.match_winner_id = winner_id
        self.match_end_reason = reason
        await self._sink_safe(
            self._sink.on_match_end(self.code, winner_id, dict(self.score), reason.value)
        )
        await self._emit(
            "match_finished",
            winner_user_id=winner_id,
            reason=reason.value,
            score=self._score_payload(),
        )

    # --------------------------------------------------------------- answers

    async def submit_answer(
        self,
        user_id: int,
        text: str,
        client_command_id: str | None = None,
    ) -> AnswerStatus:
        """Returns the status; protocol-level rejections (NOT_YOUR_TURN etc.)
        are NOT broadcast — the caller acks them to the sender only."""
        async with self.lock:
            # A retry of an already-processed submission (double-click, client
            # resend) returns the original verdict without any new record,
            # event or DB write.
            command_key = (user_id, client_command_id) if client_command_id is not None else None
            if command_key is not None:
                cached = self._processed_commands.get(command_key)
                if cached is not None:
                    return cached

            if self.phase in (RoomPhase.ROUND_FINISHED, RoomPhase.MATCH_FINISHED):
                status = AnswerStatus.ROUND_FINISHED
                if command_key is not None:
                    self._processed_commands[command_key] = status
                return status
            if self.phase != RoomPhase.ROUND_ACTIVE:
                status = AnswerStatus.NOT_YOUR_TURN
                if command_key is not None:
                    self._processed_commands[command_key] = status
                return status
            if user_id != self.turn_user_id:
                status = AnswerStatus.NOT_YOUR_TURN
                if command_key is not None:
                    self._processed_commands[command_key] = status
                return status

            loop_now = asyncio.get_running_loop().time()
            if self.turn_deadline is not None and loop_now > self.turn_deadline:
                # The answer lost the race against the clock. Resolve the
                # timeout right here instead of waiting for the timer task.
                timed_out_user = self.turn_user_id
                await self._emit("turn_timeout", user_id=timed_out_user)
                await self._end_round_locked(
                    winner_id=self._other(timed_out_user), reason="TIMEOUT"
                )
                status = AnswerStatus.TIME_EXPIRED
                if command_key is not None:
                    self._processed_commands[command_key] = status
                return status

            if self.validator is None:
                raise RuntimeError("active round is missing its answer validator")
            result = self.validator.check(text)
            record = AnswerRecord(
                submission_id=uuid.uuid4().hex,
                client_command_id=client_command_id,
                user_id=user_id,
                raw_text=(text or "").strip()[: self.config.max_answer_length],
                status=result.status,
                canonical=result.entry.canonical if result.entry else None,
                at_ms=now_ms(),
            )
            self.answers.append(record)
            if command_key is not None:
                self._processed_commands[command_key] = result.status
            await self._sink_safe(
                self._sink.on_answer(
                    self.code,
                    self.round_no,
                    record.submission_id,
                    record.client_command_id,
                    user_id,
                    record.raw_text,
                    result.normalized,
                    result.status.value,
                    result.entry.answer_id if result.entry else None,
                )
            )

            if result.status == AnswerStatus.VALID:
                # Turn passes to the opponent with a fresh timer.
                self.turn_user_id = self._other(user_id)
                self._arm_timer_locked()

            await self._emit(
                "answer_result",
                submission_id=record.submission_id,
                user_id=user_id,
                raw_text=record.raw_text,
                status=result.status.value,
                canonical=record.canonical,
                client_command_id=client_command_id,
                at_ms=record.at_ms,
                turn_user_id=self.turn_user_id,
                deadline_epoch_ms=self._deadline_epoch_ms(),
            )
            return result.status

    # ------------------------------------------------------------ power-ups

    def _powerup_result(self, user_id: int, name: str, command_id: str) -> PowerUpStatus | None:
        cached = self._processed_powerups.get((user_id, command_id))
        if cached is not None:
            return cached
        if name in self.powerups_used.get(user_id, set()):
            return PowerUpStatus.ALREADY_USED
        return None

    async def use_powerup(self, user_id: int, name: str, client_command_id: str) -> PowerUpStatus:
        async with self.lock:
            cached = self._powerup_result(user_id, name, client_command_id)
            if cached is not None:
                return cached

            available = (
                user_id in self.players
                and self.phase == RoomPhase.ROUND_ACTIVE
                and self.turn_user_id == user_id
            )
            if name == "swap_question":
                available = (
                    user_id in self.players
                    and self.phase in (RoomPhase.QUESTION_PREVIEW, RoomPhase.ROUND_ACTIVE)
                    and not self.answers
                )
            if not available:
                status = PowerUpStatus.NOT_AVAILABLE
                self._processed_powerups[(user_id, client_command_id)] = status
                return status

            if name == "swap_question":
                question = await self._provider(set(self.used_question_ids))
                if question is None:
                    status = PowerUpStatus.NOT_AVAILABLE
                    self._processed_powerups[(user_id, client_command_id)] = status
                    return status
                self._timer_gen += 1
                self.turn_deadline = None
                self.used_question_ids.add(question.id)
                self.question = question
                self.validator = RoundValidator(
                    question.index,
                    max_length=self.config.max_answer_length,
                    fuzzy_enabled=self.config.fuzzy_matching_enabled,
                    fuzzy_max_distance=self.config.fuzzy_max_distance,
                    fuzzy_min_length=self.config.fuzzy_min_length,
                    fuzzy_two_edit_min_length=self.config.fuzzy_two_edit_min_length,
                    hebrew_skeleton_enabled=self.config.hebrew_skeleton_matching_enabled,
                    unique_prefix_enabled=self.config.unique_prefix_matching_enabled,
                    unique_prefix_min_length=self.config.unique_prefix_min_length,
                    definite_article_enabled=self.config.definite_article_matching_enabled,
                )
                self.phase = RoomPhase.QUESTION_PREVIEW
                await self._sink_safe(
                    self._sink.on_question_swap(self.code, self.round_no, question.id)
                )
                self._preview_gen += 1
                self._spawn(self._preview_then_activate(self.round_no, self._preview_gen))
            elif name == "extend_time":
                if self.turn_deadline is None:
                    return PowerUpStatus.NOT_AVAILABLE
                self._timer_gen += 1
                self.turn_deadline += self.config.turn_seconds
                self._spawn(self._watch_timer(self._timer_gen, self.turn_deadline))
            elif name == "joker":
                self.turn_user_id = self._other(user_id)
                self._arm_timer_locked()
            else:
                return PowerUpStatus.NOT_AVAILABLE

            self.powerups_used[user_id].add(name)
            status = PowerUpStatus.USED
            self._processed_powerups[(user_id, client_command_id)] = status
            assert self.question is not None
            await self._emit(
                "powerup_used",
                user_id=user_id,
                powerup=name,
                question={"id": self.question.id, "text": self.question.text},
                phase=self.phase.value,
                turn_user_id=self.turn_user_id,
                deadline_epoch_ms=self._deadline_epoch_ms(),
                powerups={
                    str(uid): {
                        "swap_question": "swap_question" not in self.powerups_used.get(uid, set()),
                        "extend_time": "extend_time" not in self.powerups_used.get(uid, set()),
                        "joker": "joker" not in self.powerups_used.get(uid, set()),
                    }
                    for uid in self.order
                },
                client_command_id=client_command_id,
            )
            return status

    # --------------------------------------------------------------- helpers

    @property
    def is_empty(self) -> bool:
        return not any(p.connected for p in self.players.values())

    @property
    def is_over(self) -> bool:
        return self.phase in (RoomPhase.MATCH_FINISHED, RoomPhase.ABANDONED)

    @property
    def event_sequence(self) -> int:
        return self._seq
