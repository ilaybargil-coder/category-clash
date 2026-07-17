"""Pure ranking helpers for the human-reviewed content curator workflow."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Iterable


@dataclass(frozen=True)
class RejectedAnswerAggregate:
    question_id: int
    question: str
    normalized_text: str
    sample_raw_text: str
    occurrence_count: int
    unique_players: int
    last_seen_at: datetime | None


@dataclass(frozen=True)
class CuratorCandidate:
    question_id: int
    question: str
    normalized_text: str
    sample_raw_text: str
    occurrence_count: int
    unique_players: int
    last_seen_at: datetime | None
    priority: str
    proposed_action: str = "REVIEW_REQUIRED"

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["last_seen_at"] = (
            self.last_seen_at.isoformat() if self.last_seen_at is not None else None
        )
        return payload


def _priority(occurrence_count: int, unique_players: int) -> str:
    if occurrence_count >= 5 and unique_players >= 2:
        return "HIGH"
    if occurrence_count >= 3 or unique_players >= 2:
        return "MEDIUM"
    return "LOW"


def rank_rejected_answers(
    rows: Iterable[RejectedAnswerAggregate],
    *,
    min_count: int = 2,
    limit: int = 100,
) -> list[CuratorCandidate]:
    """Rank recurring invalid answers without deciding whether they are valid.

    The function deliberately emits only ``REVIEW_REQUIRED`` candidates. A
    person must still classify each row as a canonical answer, alias, semantic
    duplicate, invalid answer, or ambiguous case.
    """

    if min_count < 1:
        raise ValueError("min_count must be at least 1")
    if limit < 1:
        raise ValueError("limit must be at least 1")

    candidates = [
        CuratorCandidate(
            question_id=row.question_id,
            question=row.question,
            normalized_text=row.normalized_text,
            sample_raw_text=row.sample_raw_text,
            occurrence_count=row.occurrence_count,
            unique_players=row.unique_players,
            last_seen_at=row.last_seen_at,
            priority=_priority(row.occurrence_count, row.unique_players),
        )
        for row in rows
        if row.normalized_text and row.occurrence_count >= min_count
    ]
    candidates.sort(
        key=lambda item: (
            -item.occurrence_count,
            -item.unique_players,
            item.question,
            item.normalized_text,
        )
    )
    return candidates[:limit]
