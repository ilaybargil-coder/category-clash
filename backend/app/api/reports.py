from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import TokenUser, get_current_user
from ..db import get_session
from ..game.validator import normalize_answer
from ..models import AnswerReport, Question

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
