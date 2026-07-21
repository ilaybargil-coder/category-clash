from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import distinct, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import TokenUser, get_current_user
from ..config import settings
from ..db import get_session
from ..game.validator import normalize_answer
from ..models import AnswerAlias, AnswerReport, ApprovedAnswer, Question

router = APIRouter(prefix="/api")


class CreateAnswerReport(BaseModel):
    question_id: int = Field(gt=0)
    raw_text: str = Field(min_length=1, max_length=200)


class AnswerReportOut(BaseModel):
    id: int
    question_id: int
    raw_text: str
    normalized: str
    reporter_user_id: int
    created_at: datetime
    status: str


class PendingAnswerReportGroup(BaseModel):
    question_id: int
    question_text: str
    normalized: str
    sample_raw_text: str
    occurrence_count: int
    distinct_reporter_count: int
    newest_created_at: datetime


class ApprovedAnswerOut(BaseModel):
    id: int
    canonical: str


class AnswerReportContext(BaseModel):
    question_id: int
    question_text: str
    answers: list[ApprovedAnswerOut]


class ApproveAnswerReport(BaseModel):
    question_id: int = Field(gt=0)
    normalized: str = Field(min_length=1, max_length=200)
    mode: Literal["new_answer", "alias"]
    canonical: str = Field(min_length=1, max_length=120)
    target_answer_id: int | None = Field(default=None, gt=0)


class ReviewAnswerReport(BaseModel):
    question_id: int = Field(gt=0)
    normalized: str = Field(min_length=1, max_length=200)


class ReviewResult(BaseModel):
    status: Literal["approved", "rejected"]
    updated_reports: int


def answer_report_out(report: AnswerReport) -> AnswerReportOut:
    return AnswerReportOut(
        id=report.id,
        question_id=report.question_id,
        raw_text=report.raw_text,
        normalized=report.normalized,
        reporter_user_id=report.reporter_user_id,
        created_at=report.created_at,
        status=report.status,
    )


async def find_answer_report(
    session: AsyncSession,
    question_id: int,
    normalized: str,
    reporter_user_id: int,
) -> AnswerReport | None:
    return (
        await session.execute(
            select(AnswerReport).where(
                AnswerReport.question_id == question_id,
                AnswerReport.normalized == normalized,
                AnswerReport.reporter_user_id == reporter_user_id,
            )
        )
    ).scalar_one_or_none()


async def require_admin(current: TokenUser = Depends(get_current_user)) -> TokenUser:
    admin_usernames = {
        username.strip() for username in settings.admin_usernames.split(",") if username.strip()
    }
    if current.username not in admin_usernames:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current


@router.post("/reports", response_model=AnswerReportOut)
async def create_answer_report(
    body: CreateAnswerReport,
    current: TokenUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    try:
        if await session.get(Question, body.question_id) is None:
            raise HTTPException(status_code=404, detail="Question not found")

        normalized = normalize_answer(body.raw_text)
        report = await find_answer_report(session, body.question_id, normalized, current.id)
        if report is None:
            candidate = AnswerReport(
                question_id=body.question_id,
                raw_text=body.raw_text,
                normalized=normalized,
                reporter_user_id=current.id,
            )
            try:
                async with session.begin_nested():
                    session.add(candidate)
                    await session.flush()
                report = candidate
            except IntegrityError:
                report = await find_answer_report(session, body.question_id, normalized, current.id)
                if report is None:
                    raise
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    return answer_report_out(report)


@router.get("/reports", response_model=list[AnswerReportOut])
async def list_pending_answer_reports(
    current: TokenUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    reports = (
        (
            await session.execute(
                select(AnswerReport)
                .where(AnswerReport.status == "pending")
                .order_by(AnswerReport.created_at.desc(), AnswerReport.id.desc())
            )
        )
        .scalars()
        .all()
    )
    return [answer_report_out(report) for report in reports]


@router.get("/reports/pending", response_model=list[PendingAnswerReportGroup])
async def list_pending_answer_report_groups(
    _admin: TokenUser = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    occurrence_count = func.count(AnswerReport.id)
    newest_created_at = func.max(AnswerReport.created_at)
    rows = (
        await session.execute(
            select(
                AnswerReport.question_id,
                Question.text.label("question_text"),
                AnswerReport.normalized,
                func.max(AnswerReport.raw_text).label("sample_raw_text"),
                occurrence_count.label("occurrence_count"),
                func.count(distinct(AnswerReport.reporter_user_id)).label(
                    "distinct_reporter_count"
                ),
                newest_created_at.label("newest_created_at"),
            )
            .join(Question, Question.id == AnswerReport.question_id)
            .where(AnswerReport.status == "pending")
            .group_by(AnswerReport.question_id, Question.text, AnswerReport.normalized)
            .order_by(
                occurrence_count.desc(),
                newest_created_at.desc(),
                AnswerReport.question_id,
                AnswerReport.normalized,
            )
        )
    ).mappings()
    return [PendingAnswerReportGroup.model_validate(row) for row in rows]


@router.get("/reports/context/{question_id}", response_model=AnswerReportContext)
async def get_answer_report_context(
    question_id: int,
    _admin: TokenUser = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    question = await session.get(Question, question_id)
    if question is None:
        raise HTTPException(status_code=404, detail="Question not found")
    answers = (
        (
            await session.execute(
                select(ApprovedAnswer)
                .where(
                    ApprovedAnswer.question_id == question_id,
                    ApprovedAnswer.is_active.is_(True),
                )
                .order_by(ApprovedAnswer.canonical, ApprovedAnswer.id)
            )
        )
        .scalars()
        .all()
    )
    return AnswerReportContext(
        question_id=question.id,
        question_text=question.text,
        answers=[ApprovedAnswerOut(id=answer.id, canonical=answer.canonical) for answer in answers],
    )


@router.post("/reports/approve", response_model=ReviewResult)
async def approve_answer_report(
    body: ApproveAnswerReport,
    _admin: TokenUser = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    canonical = body.canonical.strip()
    if not canonical:
        raise HTTPException(status_code=422, detail="Canonical answer is required")
    if await session.get(Question, body.question_id) is None:
        raise HTTPException(status_code=404, detail="Question not found")

    if body.mode == "new_answer":
        answer: ApprovedAnswer | AnswerAlias = ApprovedAnswer(
            question_id=body.question_id,
            canonical=canonical,
            is_active=True,
        )
    else:
        if body.target_answer_id is None:
            raise HTTPException(status_code=422, detail="Target answer is required for an alias")
        target = await session.get(ApprovedAnswer, body.target_answer_id)
        if target is None or target.question_id != body.question_id or not target.is_active:
            raise HTTPException(status_code=404, detail="Active target answer not found")
        answer = AnswerAlias(approved_answer_id=target.id, alias=canonical)

    try:
        session.add(answer)
        await session.flush()
        result = await session.execute(
            update(AnswerReport)
            .where(
                AnswerReport.question_id == body.question_id,
                AnswerReport.normalized == body.normalized,
                AnswerReport.status == "pending",
            )
            .values(status="approved")
        )
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(status_code=409, detail="Answer or alias already exists") from exc
    return ReviewResult(status="approved", updated_reports=result.rowcount)


@router.post("/reports/reject", response_model=ReviewResult)
async def reject_answer_report(
    body: ReviewAnswerReport,
    _admin: TokenUser = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        update(AnswerReport)
        .where(
            AnswerReport.question_id == body.question_id,
            AnswerReport.normalized == body.normalized,
            AnswerReport.status == "pending",
        )
        .values(status="rejected")
    )
    await session.commit()
    return ReviewResult(status="rejected", updated_reports=result.rowcount)
