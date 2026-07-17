"""Print a review-only report of recurring rejected production answers.

Run on Render or locally with DATABASE_URL configured:

    python -m scripts.report_rejected_answers --min-count 2 --limit 100
"""

from __future__ import annotations

import argparse
import asyncio
import json

from sqlalchemy import func, select

from app.content_curator import RejectedAnswerAggregate, rank_rejected_answers
from app.db import SessionLocal
from app.game.validator import AnswerStatus
from app.models import Question, Round, SubmittedAnswer


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Rank recurring invalid answers for human review.")
    parser.add_argument("--min-count", type=int, default=2)
    parser.add_argument("--limit", type=int, default=100)
    return parser.parse_args()


async def _load_aggregates() -> list[RejectedAnswerAggregate]:
    statement = (
        select(
            Question.id.label("question_id"),
            Question.text.label("question"),
            SubmittedAnswer.normalized_text,
            func.min(SubmittedAnswer.raw_text).label("sample_raw_text"),
            func.count(SubmittedAnswer.id).label("occurrence_count"),
            func.count(func.distinct(SubmittedAnswer.user_id)).label("unique_players"),
            func.max(SubmittedAnswer.created_at).label("last_seen_at"),
        )
        .join(Round, Round.question_id == Question.id)
        .join(SubmittedAnswer, SubmittedAnswer.round_id == Round.id)
        .where(SubmittedAnswer.status == AnswerStatus.INVALID.value)
        .group_by(
            Question.id,
            Question.text,
            SubmittedAnswer.normalized_text,
        )
    )
    async with SessionLocal() as session:
        rows = (await session.execute(statement)).mappings().all()
    return [RejectedAnswerAggregate(**dict(row)) for row in rows]


async def _main() -> None:
    args = _parse_args()
    candidates = rank_rejected_answers(
        await _load_aggregates(),
        min_count=args.min_count,
        limit=args.limit,
    )
    print(
        json.dumps(
            {
                "candidate_count": len(candidates),
                "candidates": [candidate.to_dict() for candidate in candidates],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    asyncio.run(_main())
