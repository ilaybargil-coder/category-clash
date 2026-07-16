"""One submission == one record, one event, one DB write — under retries too."""

import asyncio

from test_engine import join_both, make_room, wait_for_phase

from app.game.engine import ResultSink, RoomPhase
from app.game.validator import AnswerStatus


class RecordingSink(ResultSink):
    """Counts persistence calls — stands in for DB writes."""

    def __init__(self):
        self.answer_calls: list[dict] = []

    async def on_answer(
        self,
        code,
        round_no,
        submission_id,
        client_command_id,
        user_id,
        raw_text,
        normalized,
        status,
        matched_answer_id,
    ):
        self.answer_calls.append(
            {
                "submission_id": submission_id,
                "user_id": user_id,
                "client_command_id": client_command_id,
                "raw_text": raw_text,
                "status": status,
            }
        )


def make_room_with_sink(**kwargs):
    room, events = make_room(**kwargs)
    sink = RecordingSink()
    room._sink = sink
    return room, events, sink


class TestSingleSubmission:
    async def test_one_submission_one_event_one_record_one_db_write(self):
        room, events, sink = make_room_with_sink(turn_seconds=5)
        await join_both(room)
        await wait_for_phase(room, RoomPhase.ROUND_ACTIVE)
        starter = room.turn_user_id

        await room.submit_answer(starter, "מנגו", client_command_id="cmd-1")

        results = events.of_type("answer_result")
        assert len(results) == 1, "exactly one broadcast event per submission"
        assert len(room.answers) == 1, "exactly one history record"
        assert len(sink.answer_calls) == 1, "exactly one DB write"

        # The same submission_id ties the event, history and DB row together.
        sid = results[0]["submission_id"]
        assert sid and sid == room.answers[0].submission_id
        assert sid == sink.answer_calls[0]["submission_id"]
        assert sink.answer_calls[0]["client_command_id"] == "cmd-1"
        assert results[0]["event_id"]
        assert results[0]["protocol_version"] == 1

    async def test_submission_ids_are_unique(self):
        room, events, _ = make_room_with_sink(turn_seconds=5)
        await join_both(room)
        await wait_for_phase(room, RoomPhase.ROUND_ACTIVE)
        starter = room.turn_user_id
        other = room._other(starter)

        await room.submit_answer(starter, "תפוח", client_command_id="cmd-1")
        await room.submit_answer(starter, "מנגו", client_command_id="cmd-2")
        await room.submit_answer(other, "אננס", client_command_id="cmd-3")

        ids = [e["submission_id"] for e in events.of_type("answer_result")]
        assert len(ids) == 3
        assert len(set(ids)) == 3

    async def test_snapshot_answers_carry_submission_ids(self):
        room, _, _ = make_room_with_sink(turn_seconds=5)
        await join_both(room)
        await wait_for_phase(room, RoomPhase.ROUND_ACTIVE)
        starter = room.turn_user_id
        await room.submit_answer(starter, "מנגו", client_command_id="cmd-1")

        snap = room.snapshot(starter)
        assert len(snap["answers"]) == 1
        assert snap["answers"][0]["submission_id"] == room.answers[0].submission_id
        assert snap["answers"][0]["client_command_id"] == "cmd-1"


class TestClientRetries:
    async def test_double_click_same_command_id_is_idempotent(self):
        """A retry of an already-processed command returns the original
        verdict and creates no new record, event or DB write."""
        room, events, sink = make_room_with_sink(turn_seconds=5)
        await join_both(room)
        await wait_for_phase(room, RoomPhase.ROUND_ACTIVE)
        starter = room.turn_user_id
        other = room._other(starter)

        first = await room.submit_answer(starter, "מנגו", client_command_id="cmd-7")
        second = await room.submit_answer(starter, "מנגו", client_command_id="cmd-7")

        assert first == AnswerStatus.VALID
        assert second == AnswerStatus.VALID, "retry gets the ORIGINAL verdict"
        assert len(events.of_type("answer_result")) == 1
        assert len(room.answers) == 1
        assert len(sink.answer_calls) == 1
        assert room.turn_user_id == other, "turn passed exactly once"

    async def test_concurrent_double_click_is_idempotent(self):
        room, events, sink = make_room_with_sink(turn_seconds=5)
        await join_both(room)
        await wait_for_phase(room, RoomPhase.ROUND_ACTIVE)
        starter = room.turn_user_id

        results = await asyncio.gather(
            room.submit_answer(starter, "מנגו", client_command_id="cmd-3"),
            room.submit_answer(starter, "מנגו", client_command_id="cmd-3"),
        )
        assert list(results) == [AnswerStatus.VALID, AnswerStatus.VALID]
        assert len(events.of_type("answer_result")) == 1
        assert len(sink.answer_calls) == 1

    async def test_retry_of_invalid_answer_does_not_duplicate(self):
        room, events, sink = make_room_with_sink(turn_seconds=5)
        await join_both(room)
        await wait_for_phase(room, RoomPhase.ROUND_ACTIVE)
        starter = room.turn_user_id

        first = await room.submit_answer(starter, "תפוח", client_command_id="cmd-1")
        second = await room.submit_answer(starter, "תפוח", client_command_id="cmd-1")

        assert first == second == AnswerStatus.INVALID
        assert len(events.of_type("answer_result")) == 1
        assert len(sink.answer_calls) == 1

    async def test_different_command_id_same_text_is_a_new_attempt(self):
        """Typing the same word again on purpose IS a new attempt (DUPLICATE),
        not a swallowed retry."""
        room, events, _ = make_room_with_sink(turn_seconds=5)
        await join_both(room)
        await wait_for_phase(room, RoomPhase.ROUND_ACTIVE)
        starter = room.turn_user_id
        other = room._other(starter)

        assert (
            await room.submit_answer(starter, "מנגו", client_command_id="cmd-1")
            == AnswerStatus.VALID
        )
        # A different id is a different intent, so it is judged by the game.
        # processed as a real attempt and judged DUPLICATE by game rules:
        status = await room.submit_answer(other, "מנגו", client_command_id="cmd-2")
        assert status == AnswerStatus.DUPLICATE
        results = events.of_type("answer_result")
        assert len(results) == 2
        assert results[1]["status"] == "DUPLICATE"

    async def test_rejected_command_cannot_be_applied_later(self):
        room, events, sink = make_room_with_sink(turn_seconds=5, preview=1)
        await join_both(room)
        starter = room.turn_user_id

        first = await room.submit_answer(starter, "מנגו", client_command_id="early-command")
        room.phase = RoomPhase.ROUND_ACTIVE
        second = await room.submit_answer(starter, "מנגו", client_command_id="early-command")

        assert first == second == AnswerStatus.NOT_YOUR_TURN
        assert events.of_type("answer_result") == []
        assert sink.answer_calls == []
