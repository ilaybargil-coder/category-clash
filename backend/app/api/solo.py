"""Authenticated, in-process single-player practice sessions."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from ..auth import TokenUser, get_current_user
from ..config import settings
from ..db import SessionLocal
from ..game.db_io import make_question_provider
from ..game.validator import AnswerStatus, QuestionData, RoundValidator
from ..models import ApprovedAnswer

router = APIRouter(prefix="/api", tags=["solo"])
_SESSION_TTL = timedelta(minutes=30)
_question_provider = make_question_provider(SessionLocal)


@dataclass
class SoloSession:
    owner_user_id: int
    question: QuestionData
    validator: RoundValidator
    found_answers: list[tuple[int, str]] = field(default_factory=list)
    played_question_ids: set[int] = field(default_factory=set)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class SoloAnswerBody(BaseModel):
    text: str


_solo_sessions: dict[str, SoloSession] = {}


def _make_validator(question: QuestionData) -> RoundValidator:
    return RoundValidator(
        question.index,
        max_length=settings.max_answer_length,
        fuzzy_enabled=settings.fuzzy_matching_enabled,
        fuzzy_max_distance=settings.fuzzy_max_distance,
        fuzzy_min_length=settings.fuzzy_min_length,
    )


def _purge_expired_sessions() -> None:
    cutoff = datetime.now(timezone.utc) - _SESSION_TTL
    expired = [solo_id for solo_id, session in _solo_sessions.items() if session.created_at < cutoff]
    for solo_id in expired:
        _solo_sessions.pop(solo_id, None)


def _owned_session(solo_id: str, current: TokenUser) -> SoloSession:
    _purge_expired_sessions()
    session = _solo_sessions.get(solo_id)
    if session is None or session.owner_user_id != current.id:
        raise HTTPException(status_code=404, detail="Solo session not found")
    return session


def _question_response(solo_id: str, question: QuestionData) -> dict[str, object]:
    return {
        "solo_id": solo_id,
        "question_id": question.id,
        "question_text": question.text,
        "total_answers": len(question.index),
    }


@router.post("/solo/start")
async def start_solo(current: TokenUser = Depends(get_current_user)) -> dict[str, object]:
    _purge_expired_sessions()
    question = await _question_provider(set())
    if question is None:
        raise HTTPException(status_code=503, detail="No questions available")
    solo_id = uuid4().hex
    _solo_sessions[solo_id] = SoloSession(
        owner_user_id=current.id,
        question=question,
        validator=_make_validator(question),
        played_question_ids={question.id},
    )
    return _question_response(solo_id, question)


@router.post("/solo/{solo_id}/answer")
async def answer_solo(
    solo_id: str,
    body: SoloAnswerBody,
    current: TokenUser = Depends(get_current_user),
) -> dict[str, object]:
    session = _owned_session(solo_id, current)
    result = session.validator.check(body.text)
    if result.status == AnswerStatus.VALID and result.entry is not None:
        session.found_answers.append((result.entry.answer_id, result.entry.canonical))
    return {
        "status": result.status.value,
        "canonical": result.entry.canonical if result.entry is not None else None,
        "found_count": len(session.found_answers),
        "total_answers": len(session.question.index),
    }


@router.post("/solo/{solo_id}/reveal")
async def reveal_solo(
    solo_id: str, current: TokenUser = Depends(get_current_user)
) -> dict[str, object]:
    solo = _owned_session(solo_id, current)
    async with SessionLocal() as db_session:
        answers = (
            (
                await db_session.execute(
                    select(ApprovedAnswer)
                    .where(
                        ApprovedAnswer.question_id == solo.question.id,
                        ApprovedAnswer.is_active.is_(True),
                    )
                    .order_by(ApprovedAnswer.id)
                )
            )
            .scalars()
            .all()
        )
    found_ids = {answer_id for answer_id, _ in solo.found_answers}
    return {
        "answers": [
            {
                "canonical": answer.canonical,
                "semantic_group": answer.semantic_group,
                "found": answer.id in found_ids,
            }
            for answer in answers
        ],
        "found_count": len(solo.found_answers),
        "total_answers": len(solo.question.index),
    }


@router.post("/solo/{solo_id}/next")
async def next_solo(
    solo_id: str, current: TokenUser = Depends(get_current_user)
) -> dict[str, object]:
    solo = _owned_session(solo_id, current)
    question = await _question_provider(set(solo.played_question_ids))
    if question is None:
        raise HTTPException(status_code=409, detail="No more questions")
    solo.question = question
    solo.validator = _make_validator(question)
    solo.found_answers = []
    solo.played_question_ids.add(question.id)
    return _question_response(solo_id, question)


@router.delete("/solo/{solo_id}")
async def end_solo(
    solo_id: str, current: TokenUser = Depends(get_current_user)
) -> dict[str, bool]:
    _owned_session(solo_id, current)
    _solo_sessions.pop(solo_id, None)
    return {"ended": True}
