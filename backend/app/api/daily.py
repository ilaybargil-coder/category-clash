"""Authenticated daily challenge built on the solo answer validator."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..auth import TokenUser, get_current_user
from ..config import settings
from ..db import get_session
from ..game.validator import AnswerStatus, QuestionData, RoundValidator, build_question_index
from ..models import ApprovedAnswer, DailyChallenge, DailyResult, Question, User

router = APIRouter(prefix="/api/daily", tags=["daily"])
_SESSION_TTL = timedelta(minutes=30)
_LEADERBOARD_LIMIT = 20
_ISRAEL_TZ = ZoneInfo("Asia/Jerusalem")


@dataclass
class DailySession:
    owner_user_id: int
    challenge_date: date
    question: QuestionData
    validator: RoundValidator
    found_answers: list[tuple[int, str]] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class DailyAnswerBody(BaseModel):
    text: str = Field(min_length=1, max_length=200)


class DailyResultOut(BaseModel):
    id: int
    date: date
    question_id: int
    score: int
    created_at: datetime
    share_text: str


class DailyTodayOut(BaseModel):
    date: date
    question_id: int
    question_text: str
    total_answers: int
    result: DailyResultOut | None


class DailyStartOut(BaseModel):
    date: date
    question_id: int
    question_text: str
    total_answers: int
    found_count: int
    found_answers: list[str]


class DailyAnswerOut(BaseModel):
    status: str
    canonical: str | None
    found_count: int
    total_answers: int


class DailyLeaderboardEntry(BaseModel):
    rank: int
    user_id: int
    username: str
    display_name: str
    score: int
    created_at: datetime


class DailyLeaderboardOut(BaseModel):
    date: date
    entries: list[DailyLeaderboardEntry]


_daily_sessions: dict[tuple[int, date], DailySession] = {}


def _local_today() -> date:
    return datetime.now(_ISRAEL_TZ).date()


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
    expired = [key for key, daily in _daily_sessions.items() if daily.created_at < cutoff]
    for key in expired:
        _daily_sessions.pop(key, None)


async def get_daily_question(session: AsyncSession, challenge_date: date) -> QuestionData | None:
    """Return the pinned active question selected for an Israel-local calendar date."""

    pin = (
        await session.execute(select(DailyChallenge).where(DailyChallenge.date == challenge_date))
    ).scalar_one_or_none()
    if pin is not None:
        question = (
            await session.execute(
                select(Question)
                .where(Question.id == pin.question_id)
                .options(selectinload(Question.answers).selectinload(ApprovedAnswer.aliases))
            )
        ).scalar_one_or_none()
        if question is not None and question.is_active:
            active_answers = [answer for answer in question.answers if answer.is_active]
            if active_answers:
                index = build_question_index(
                    [
                        (
                            answer.id,
                            answer.canonical,
                            answer.semantic_group,
                            [alias.alias for alias in answer.aliases],
                        )
                        for answer in active_answers
                    ]
                )
                return QuestionData(id=question.id, text=question.text, index=index)

    question_ids = list(
        (
            await session.execute(
                select(Question.id)
                .where(
                    Question.is_active.is_(True),
                    Question.answers.any(ApprovedAnswer.is_active.is_(True)),
                )
                .order_by(Question.id)
            )
        )
        .scalars()
        .all()
    )
    if not question_ids:
        return None

    digest = hashlib.sha256(challenge_date.isoformat().encode("ascii")).digest()
    question_id = question_ids[int.from_bytes(digest, "big") % len(question_ids)]

    if pin is None:
        session.add(DailyChallenge(date=challenge_date, question_id=question_id))
        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()
            concurrent_pin = (
                await session.execute(
                    select(DailyChallenge).where(DailyChallenge.date == challenge_date)
                )
            ).scalar_one()
            question_id = concurrent_pin.question_id
    else:
        pin.question_id = question_id
        await session.commit()

    question = (
        await session.execute(
            select(Question)
            .where(Question.id == question_id)
            .options(selectinload(Question.answers).selectinload(ApprovedAnswer.aliases))
        )
    ).scalar_one()
    active_answers = [answer for answer in question.answers if answer.is_active]
    index = build_question_index(
        [
            (
                answer.id,
                answer.canonical,
                answer.semantic_group,
                [alias.alias for alias in answer.aliases],
            )
            for answer in active_answers
        ]
    )
    return QuestionData(id=question.id, text=question.text, index=index)


async def _find_result(
    session: AsyncSession, user_id: int, challenge_date: date
) -> DailyResult | None:
    return (
        await session.execute(
            select(DailyResult).where(
                DailyResult.user_id == user_id,
                DailyResult.date == challenge_date,
            )
        )
    ).scalar_one_or_none()


def _result_out(result: DailyResult) -> DailyResultOut:
    return DailyResultOut(
        id=result.id,
        date=result.date,
        question_id=result.question_id,
        score=result.score,
        created_at=result.created_at,
        share_text=f"עניתי {result.score} תשובות היום",
    )


def _start_out(daily: DailySession) -> DailyStartOut:
    return DailyStartOut(
        date=daily.challenge_date,
        question_id=daily.question.id,
        question_text=daily.question.text,
        total_answers=len(daily.question.index),
        found_count=len(daily.found_answers),
        found_answers=[canonical for _, canonical in daily.found_answers],
    )


def _owned_session(current: TokenUser, challenge_date: date) -> DailySession:
    _purge_expired_sessions()
    daily = _daily_sessions.get((current.id, challenge_date))
    if daily is None:
        raise HTTPException(status_code=409, detail="Daily challenge not started")
    return daily


@router.get("/today", response_model=DailyTodayOut)
async def daily_today(
    current: TokenUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> DailyTodayOut:
    challenge_date = _local_today()
    question = await get_daily_question(session, challenge_date)
    if question is None:
        raise HTTPException(status_code=503, detail="No questions available")
    result = await _find_result(session, current.id, challenge_date)
    return DailyTodayOut(
        date=challenge_date,
        question_id=question.id,
        question_text=question.text,
        total_answers=len(question.index),
        result=_result_out(result) if result is not None else None,
    )


@router.post("/start", response_model=DailyStartOut)
async def start_daily(
    current: TokenUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> DailyStartOut:
    challenge_date = _local_today()
    if await _find_result(session, current.id, challenge_date) is not None:
        raise HTTPException(status_code=409, detail="Daily challenge already completed")

    _purge_expired_sessions()
    key = (current.id, challenge_date)
    existing = _daily_sessions.get(key)
    if existing is not None:
        return _start_out(existing)

    question = await get_daily_question(session, challenge_date)
    if question is None:
        raise HTTPException(status_code=503, detail="No questions available")
    daily = DailySession(
        owner_user_id=current.id,
        challenge_date=challenge_date,
        question=question,
        validator=_make_validator(question),
    )
    _daily_sessions[key] = daily
    return _start_out(daily)


@router.post("/answer", response_model=DailyAnswerOut)
async def answer_daily(
    body: DailyAnswerBody,
    current: TokenUser = Depends(get_current_user),
) -> DailyAnswerOut:
    daily = _owned_session(current, _local_today())
    result = daily.validator.check(body.text)
    if result.status == AnswerStatus.VALID and result.entry is not None:
        daily.found_answers.append((result.entry.answer_id, result.entry.canonical))
    return DailyAnswerOut(
        status=result.status.value,
        canonical=result.entry.canonical if result.entry is not None else None,
        found_count=len(daily.found_answers),
        total_answers=len(daily.question.index),
    )


@router.post("/finish", response_model=DailyResultOut)
async def finish_daily(
    current: TokenUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> DailyResultOut:
    challenge_date = _local_today()
    existing = await _find_result(session, current.id, challenge_date)
    if existing is not None:
        _daily_sessions.pop((current.id, challenge_date), None)
        return _result_out(existing)

    daily = _owned_session(current, challenge_date)
    candidate = DailyResult(
        user_id=current.id,
        date=challenge_date,
        question_id=daily.question.id,
        score=len(daily.found_answers),
    )
    result = candidate
    try:
        async with session.begin_nested():
            session.add(candidate)
            await session.flush()
    except IntegrityError:
        concurrent_result = await _find_result(session, current.id, challenge_date)
        if concurrent_result is None:
            raise
        result = concurrent_result
    await session.commit()
    _daily_sessions.pop((current.id, challenge_date), None)
    return _result_out(result)


@router.get("/leaderboard", response_model=DailyLeaderboardOut)
async def daily_leaderboard(
    _current: TokenUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> DailyLeaderboardOut:
    challenge_date = _local_today()
    rows = (
        await session.execute(
            select(DailyResult, User)
            .join(User, User.id == DailyResult.user_id)
            .where(DailyResult.date == challenge_date)
            .order_by(
                DailyResult.score.desc(),
                DailyResult.created_at.asc(),
                DailyResult.id.asc(),
            )
            .limit(_LEADERBOARD_LIMIT)
        )
    ).all()
    return DailyLeaderboardOut(
        date=challenge_date,
        entries=[
            DailyLeaderboardEntry(
                rank=rank,
                user_id=result.user_id,
                username=user.username,
                display_name=user.display_name,
                score=result.score,
                created_at=result.created_at,
            )
            for rank, (result, user) in enumerate(rows, start=1)
        ],
    )
