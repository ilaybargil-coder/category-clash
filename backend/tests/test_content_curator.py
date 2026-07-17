from datetime import UTC, datetime

import pytest

from app.content_curator import RejectedAnswerAggregate, rank_rejected_answers


def _row(
    normalized_text: str,
    occurrence_count: int,
    unique_players: int,
    *,
    question_id: int = 1,
) -> RejectedAnswerAggregate:
    return RejectedAnswerAggregate(
        question_id=question_id,
        question="כתבו שמות של רכיבי מחשב וציוד היקפי",
        normalized_text=normalized_text,
        sample_raw_text=normalized_text,
        occurrence_count=occurrence_count,
        unique_players=unique_players,
        last_seen_at=datetime(2026, 7, 17, tzinfo=UTC),
    )


def test_recurring_rejections_are_ranked_without_auto_approval():
    candidates = rank_rejected_answers(
        [
            _row("כבל", 8, 4),
            _row("מתאם", 3, 1),
            _row("טעות חד פעמית", 1, 1),
        ],
        min_count=2,
    )

    assert [candidate.normalized_text for candidate in candidates] == ["כבל", "מתאם"]
    assert candidates[0].priority == "HIGH"
    assert candidates[1].priority == "MEDIUM"
    assert {candidate.proposed_action for candidate in candidates} == {"REVIEW_REQUIRED"}


def test_candidate_json_is_serializable_and_contains_no_user_identity():
    candidate = rank_rejected_answers([_row("דוקו", 5, 3)])[0]

    payload = candidate.to_dict()

    assert payload["last_seen_at"] == "2026-07-17T00:00:00+00:00"
    assert "user_id" not in payload


@pytest.mark.parametrize("min_count,limit", [(0, 10), (1, 0)])
def test_invalid_report_limits_are_rejected(min_count: int, limit: int):
    with pytest.raises(ValueError):
        rank_rejected_answers([], min_count=min_count, limit=limit)
