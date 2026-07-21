"""Engine tests: turn logic, server-side timers, best-of-3 flow, races."""

import asyncio

import pytest

from app.game.engine import GameConfig, GameRoom, PowerUpStatus, RoomPhase
from app.game.validator import AnswerStatus, QuestionData, build_question_index

P1, P2 = 1, 2


def make_question(qid=1):
    index = build_question_index(
        [
            (10, "מנגו", None, []),
            (11, "אננס", None, []),
            (12, "פפאיה", None, ["פפיה"]),
            (13, "שפתון", "lipstick", []),
            (14, "אודם", "lipstick", []),
        ]
    )
    return QuestionData(id=qid, text=f"שאלה {qid}", index=index)


class EventCollector:
    def __init__(self):
        self.events = []

    async def __call__(self, event):
        self.events.append(event)

    def of_type(self, event_type):
        return [e for e in self.events if e["type"] == event_type]


def make_room(turn_seconds=0.15, preview=0.01, intermission=0.01, powerup_grace_ms=600):
    events = EventCollector()

    async def provider(exclude_ids, _player_ids):
        next_id = max(exclude_ids, default=0) + 1
        return make_question(next_id)

    config = GameConfig(
        turn_seconds=turn_seconds,
        powerup_grace_ms=powerup_grace_ms,
        preview_seconds=preview,
        intermission_seconds=intermission,
        rounds_to_win=2,
        disconnect_forfeit_seconds=0.3,
    )
    room = GameRoom("TEST1", config, provider, events)
    return room, events


async def join_both(room):
    assert await room.join(P1, "p1", "שחקן 1")
    assert await room.join(P2, "p2", "שחקן 2")


async def wait_for_phase(room, phase, timeout=2.0):
    deadline = asyncio.get_running_loop().time() + timeout
    while room.phase != phase:
        if asyncio.get_running_loop().time() > deadline:
            pytest.fail(f"phase never reached {phase}, stuck at {room.phase}")
        await asyncio.sleep(0.005)


class TestMatchSetup:
    async def test_match_starts_when_both_join(self):
        room, events = make_room()
        await join_both(room)
        assert room.phase == RoomPhase.QUESTION_PREVIEW
        assert room.round_no == 1
        assert room.turn_user_id == room.first_starter_id
        assert len(events.of_type("round_started")) == 1

    async def test_third_player_rejected(self):
        room, _ = make_room()
        await join_both(room)
        assert not await room.join(3, "p3", "שחקן 3")

    async def test_round_activates_after_preview(self):
        room, events = make_room()
        await join_both(room)
        await wait_for_phase(room, RoomPhase.ROUND_ACTIVE)
        assert len(events.of_type("round_active")) == 1


class TestTurns:
    async def test_valid_answer_passes_turn(self):
        room, events = make_room(turn_seconds=5)
        await join_both(room)
        await wait_for_phase(room, RoomPhase.ROUND_ACTIVE)
        starter = room.turn_user_id
        other = room._other(starter)

        status = await room.submit_answer(starter, "מנגו")
        assert status == AnswerStatus.VALID
        assert room.turn_user_id == other

    async def test_invalid_answer_keeps_turn(self):
        room, _ = make_room(turn_seconds=5)
        await join_both(room)
        await wait_for_phase(room, RoomPhase.ROUND_ACTIVE)
        starter = room.turn_user_id

        assert await room.submit_answer(starter, "תפוח") == AnswerStatus.INVALID
        assert room.turn_user_id == starter

    async def test_invalid_answer_does_not_reset_timer(self):
        room, _ = make_room(turn_seconds=5)
        await join_both(room)
        await wait_for_phase(room, RoomPhase.ROUND_ACTIVE)
        deadline_before = room.turn_deadline
        await room.submit_answer(room.turn_user_id, "תפוח")
        assert room.turn_deadline == deadline_before

    async def test_valid_answer_resets_timer(self):
        room, _ = make_room(turn_seconds=5)
        await join_both(room)
        await wait_for_phase(room, RoomPhase.ROUND_ACTIVE)
        deadline_before = room.turn_deadline
        await room.submit_answer(room.turn_user_id, "מנגו")
        assert room.turn_deadline > deadline_before

    async def test_duplicate_answer_keeps_turn(self):
        room, _ = make_room(turn_seconds=5)
        await join_both(room)
        await wait_for_phase(room, RoomPhase.ROUND_ACTIVE)
        starter = room.turn_user_id
        other = room._other(starter)

        await room.submit_answer(starter, "מנגו")
        assert await room.submit_answer(other, "מנגו") == AnswerStatus.DUPLICATE
        assert room.turn_user_id == other

    async def test_alias_duplicate_and_semantic_group(self):
        room, _ = make_room(turn_seconds=5)
        await join_both(room)
        await wait_for_phase(room, RoomPhase.ROUND_ACTIVE)
        starter = room.turn_user_id
        other = room._other(starter)

        assert await room.submit_answer(starter, "פפאיה") == AnswerStatus.VALID
        assert await room.submit_answer(other, "פפיה") == AnswerStatus.DUPLICATE
        assert await room.submit_answer(other, "שפתון") == AnswerStatus.VALID
        assert await room.submit_answer(starter, "אודם") == AnswerStatus.TOO_SIMILAR
        assert room.turn_user_id == starter

    async def test_not_your_turn(self):
        room, _ = make_room(turn_seconds=5)
        await join_both(room)
        await wait_for_phase(room, RoomPhase.ROUND_ACTIVE)
        other = room._other(room.turn_user_id)

        assert await room.submit_answer(other, "מנגו") == AnswerStatus.NOT_YOUR_TURN
        assert all(a.user_id != other for a in room.answers)

    async def test_answer_during_preview_rejected(self):
        room, _ = make_room(turn_seconds=5, preview=1.0)
        await join_both(room)
        assert room.phase == RoomPhase.QUESTION_PREVIEW
        status = await room.submit_answer(room.turn_user_id, "מנגו")
        assert status == AnswerStatus.NOT_YOUR_TURN


class TestTimer:
    async def test_timeout_gives_round_to_opponent(self):
        room, events = make_room(turn_seconds=0.1, intermission=5)
        await join_both(room)
        await wait_for_phase(room, RoomPhase.ROUND_ACTIVE)
        starter = room.turn_user_id
        opponent = room._other(starter)

        await wait_for_phase(room, RoomPhase.ROUND_FINISHED)
        assert room.score[opponent] == 1
        assert room.score[starter] == 0
        finished = events.of_type("round_finished")[0]
        assert finished["winner_user_id"] == opponent
        assert finished["reason"] == "TIMEOUT"

    async def test_answer_after_deadline_is_time_expired_without_powerup_grace(self):
        room, _ = make_room(turn_seconds=5)
        await join_both(room)
        await wait_for_phase(room, RoomPhase.ROUND_ACTIVE)
        starter = room.turn_user_id
        opponent = room._other(starter)

        # Simulate the race: the deadline passed but the timer task has not
        # fired yet, and an answer arrives.
        room.turn_deadline = asyncio.get_running_loop().time() - 0.01
        status = await room.submit_answer(starter, "מנגו")
        assert status == AnswerStatus.TIME_EXPIRED
        assert room.phase == RoomPhase.ROUND_ACTIVE
        assert room.score[opponent] == 0
        assert not room.answers

    async def test_answer_after_powerup_grace_finalizes_timeout(self):
        room, _ = make_room(turn_seconds=5)
        await join_both(room)
        await wait_for_phase(room, RoomPhase.ROUND_ACTIVE)
        starter = room.turn_user_id
        opponent = room._other(starter)

        room.turn_deadline = asyncio.get_running_loop().time() - 0.61
        status = await room.submit_answer(starter, "מנגו")
        assert status == AnswerStatus.TIME_EXPIRED
        assert room.phase in (RoomPhase.ROUND_FINISHED, RoomPhase.QUESTION_PREVIEW)
        assert room.score[opponent] == 1

    async def test_valid_answer_prevents_pending_timeout(self):
        room, events = make_room(turn_seconds=0.15, intermission=5)
        await join_both(room)
        await wait_for_phase(room, RoomPhase.ROUND_ACTIVE)
        starter = room.turn_user_id

        await room.submit_answer(starter, "מנגו")
        await asyncio.sleep(0.05)
        assert room.phase == RoomPhase.ROUND_ACTIVE
        # The opponent's fresh timer eventually fires — not the stale one —
        # so the round ends exactly once, with the starter as winner.
        await wait_for_phase(room, RoomPhase.ROUND_FINISHED)
        finished = events.of_type("round_finished")
        assert len(finished) == 1
        assert finished[0]["winner_user_id"] == starter
        assert sum(room.score.values()) == 1


class TestPowerUps:
    async def test_extend_time_arriving_within_grace_after_deadline_is_honored(self):
        room, _ = make_room(turn_seconds=0.05, powerup_grace_ms=600)
        await join_both(room)
        await wait_for_phase(room, RoomPhase.ROUND_ACTIVE)
        player = room.turn_user_id
        original_deadline = room.turn_deadline
        await asyncio.sleep(0.06)

        status = await room.use_powerup(player, "extend_time", "extend-in-grace")

        assert status == PowerUpStatus.USED
        assert room.phase == RoomPhase.ROUND_ACTIVE
        assert room.turn_deadline == original_deadline + room.config.turn_seconds

    async def test_extend_time_after_grace_is_rejected(self):
        room, _ = make_room(turn_seconds=5, powerup_grace_ms=600)
        await join_both(room)
        await wait_for_phase(room, RoomPhase.ROUND_ACTIVE)
        player = room.turn_user_id
        room.turn_deadline = asyncio.get_running_loop().time() - 0.61

        status = await room.use_powerup(player, "extend_time", "extend-too-late")

        assert status == PowerUpStatus.NOT_AVAILABLE
        assert "extend_time" not in room.powerups_used[player]

    async def test_extend_time_once_per_player(self):
        room, _ = make_room(turn_seconds=5)
        await join_both(room)
        await wait_for_phase(room, RoomPhase.ROUND_ACTIVE)
        player = room.turn_user_id
        before = room.turn_deadline
        assert await room.use_powerup(player, "extend_time", "extend-1") == PowerUpStatus.USED
        assert room.turn_deadline >= before + 4.9
        assert (
            await room.use_powerup(player, "extend_time", "extend-2") == PowerUpStatus.ALREADY_USED
        )

    async def test_joker_passes_turn_once_per_player(self):
        room, _ = make_room(turn_seconds=5)
        await join_both(room)
        await wait_for_phase(room, RoomPhase.ROUND_ACTIVE)
        player = room.turn_user_id
        opponent = room._other(player)
        assert await room.use_powerup(player, "joker", "joker-1") == PowerUpStatus.USED
        assert room.turn_user_id == opponent
        await room.submit_answer(opponent, "מנגו")
        assert room.turn_user_id == player
        assert await room.use_powerup(player, "joker", "joker-2") == PowerUpStatus.ALREADY_USED

    async def test_swap_replaces_question_and_restarts_preview(self):
        room, _ = make_room(turn_seconds=5, preview=5)
        await join_both(room)
        player = room.turn_user_id
        old_question_id = room.question.id
        assert await room.use_powerup(player, "swap_question", "swap-1") == PowerUpStatus.USED
        assert room.question.id != old_question_id
        assert room.phase == RoomPhase.QUESTION_PREVIEW
        assert (
            await room.use_powerup(player, "swap_question", "swap-2") == PowerUpStatus.ALREADY_USED
        )

    async def test_powerup_command_is_idempotent(self):
        room, events = make_room(turn_seconds=5)
        await join_both(room)
        await wait_for_phase(room, RoomPhase.ROUND_ACTIVE)
        player = room.turn_user_id
        first = await room.use_powerup(player, "extend_time", "same-command")
        deadline = room.turn_deadline
        second = await room.use_powerup(player, "extend_time", "same-command")
        assert first == second == PowerUpStatus.USED
        assert room.turn_deadline == deadline
        assert len(events.of_type("powerup_used")) == 1


class TestBestOfThree:
    async def test_full_match_by_timeouts(self):
        room, events = make_room(turn_seconds=0.08, preview=0.01, intermission=0.01)
        await join_both(room)
        first_starter = room.first_starter_id
        other = room._other(first_starter)

        # Round 1: first_starter times out -> other scores.
        # Round 2: other starts (alternation) and times out -> 1:1.
        # Round 3: first_starter starts and times out -> other wins 2:1.
        await wait_for_phase(room, RoomPhase.MATCH_FINISHED, timeout=5)

        assert room.match_winner_id == other
        assert room.score[other] == 2
        assert room.score[first_starter] == 1
        assert len(events.of_type("match_finished")) == 1

        starters = [e["starter_user_id"] for e in events.of_type("round_started")]
        assert starters == [first_starter, other, first_starter]

        questions = [e["question"]["id"] for e in events.of_type("round_started")]
        assert len(set(questions)) == 3, "each round must get a fresh question"

    async def test_answers_after_match_finished_rejected(self):
        room, _ = make_room(turn_seconds=0.05, preview=0.01, intermission=0.01)
        await join_both(room)
        await wait_for_phase(room, RoomPhase.MATCH_FINISHED, timeout=5)
        status = await room.submit_answer(P1, "מנגו")
        assert status == AnswerStatus.ROUND_FINISHED


class TestRematch:
    async def test_single_request_waits(self):
        room, events = make_room(turn_seconds=0.05, preview=0.01, intermission=0.01)
        await join_both(room)
        await wait_for_phase(room, RoomPhase.MATCH_FINISHED, timeout=5)

        assert await room.request_rematch(P1)
        assert room.phase == RoomPhase.MATCH_FINISHED
        assert room.rematch_requests == {P1}
        assert room.snapshot(P1)["rematch"] == {"requesting_user_ids": [P1]}
        assert events.of_type("rematch_updated")[-1]["rematch"] == {"requesting_user_ids": [P1]}

    async def test_both_requests_start_fresh_match(self):
        room, events = make_room(turn_seconds=0.05, preview=0.01, intermission=0.01)
        await join_both(room)
        await wait_for_phase(room, RoomPhase.MATCH_FINISHED, timeout=5)
        previous_question_id = room.question.id
        previous_round_started_count = len(events.of_type("round_started"))
        room.powerups_used[P1].add("joker")

        assert await room.request_rematch(P1)
        assert await room.request_rematch(P2)

        assert room.phase == RoomPhase.QUESTION_PREVIEW
        assert room.round_no == 1
        assert room.question.id != previous_question_id
        assert room.score == {P1: 0, P2: 0}
        assert room.match_winner_id is None
        assert room.match_end_reason is None
        assert room.rematch_requests == set()
        assert room.powerups_used == {P1: set(), P2: set()}
        assert len(events.of_type("round_started")) == previous_round_started_count + 1
        assert events.of_type("round_started")[-1]["rematch"] == {"requesting_user_ids": []}

    async def test_disconnect_clears_request(self):
        room, events = make_room(turn_seconds=0.05, preview=0.01, intermission=0.01)
        await join_both(room)
        await wait_for_phase(room, RoomPhase.MATCH_FINISHED, timeout=5)
        assert await room.request_rematch(P1)

        await room.disconnect(P1)

        assert room.phase == RoomPhase.MATCH_FINISHED
        assert room.rematch_requests == set()
        assert room.snapshot(P2)["rematch"] == {"requesting_user_ids": []}
        assert events.of_type("rematch_updated")[-1]["rematch"] == {"requesting_user_ids": []}


class TestDisconnects:
    async def test_forfeit_after_disconnect(self):
        room, events = make_room(turn_seconds=10)
        await join_both(room)
        await wait_for_phase(room, RoomPhase.ROUND_ACTIVE)

        await room.disconnect(P1)
        await wait_for_phase(room, RoomPhase.MATCH_FINISHED, timeout=2)
        assert room.match_winner_id == P2
        assert events.of_type("match_finished")[0]["reason"] == "FORFEIT"

    async def test_reconnect_cancels_forfeit(self):
        room, _ = make_room(turn_seconds=10)
        await join_both(room)
        await wait_for_phase(room, RoomPhase.ROUND_ACTIVE)

        await room.disconnect(P1)
        await asyncio.sleep(0.1)
        assert await room.join(P1, "p1", "שחקן 1")  # reconnect
        await asyncio.sleep(0.4)  # well past forfeit window
        assert room.phase == RoomPhase.ROUND_ACTIVE

    async def test_snapshot_after_reconnect_contains_history(self):
        room, _ = make_room(turn_seconds=10)
        await join_both(room)
        await wait_for_phase(room, RoomPhase.ROUND_ACTIVE)
        starter = room.turn_user_id
        await room.submit_answer(starter, "תפוח")
        await room.submit_answer(starter, "מנגו")

        await room.disconnect(starter)
        await room.join(starter, "p", "שחקן")
        snap = room.snapshot(starter)
        assert snap["phase"] == RoomPhase.ROUND_ACTIVE.value
        assert [a["status"] for a in snap["answers"]] == ["INVALID", "VALID"]
        assert snap["deadline_epoch_ms"] is not None


class TestConcurrency:
    async def test_two_rapid_answers_processed_serially(self):
        room, _ = make_room(turn_seconds=5)
        await join_both(room)
        await wait_for_phase(room, RoomPhase.ROUND_ACTIVE)
        starter = room.turn_user_id

        # Same player fires two answers "at once" (double-click / double enter).
        results = await asyncio.gather(
            room.submit_answer(starter, "מנגו"),
            room.submit_answer(starter, "אננס"),
        )
        # First is VALID; second must be rejected because the turn already
        # passed — it must NOT count for the opponent.
        assert results[0] == AnswerStatus.VALID
        assert results[1] == AnswerStatus.NOT_YOUR_TURN
