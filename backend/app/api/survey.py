"""Stateless API for the solo Israeli survey game."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..auth import TokenUser, get_current_user
from ..survey_questions import (
    SURVEY_QUESTIONS,
    get_survey_matcher,
    get_survey_question,
)

router = APIRouter(prefix="/api/survey", tags=["survey"])


class SurveyGuessBody(BaseModel):
    text: str
    revealed: list[int]


@router.get("/questions")
async def list_survey_questions(
    _current: TokenUser = Depends(get_current_user),
) -> list[dict[str, int | str]]:
    return [
        {
            "id": question["id"],
            "text": question["text"],
            "slot_count": len(question["answers"]),
            "max_points": sum(answer["points"] for answer in question["answers"]),
        }
        for question in SURVEY_QUESTIONS
    ]


@router.post("/questions/{question_id}/guess")
async def guess_survey_answer(
    question_id: str,
    body: SurveyGuessBody,
    _current: TokenUser = Depends(get_current_user),
) -> dict[str, bool | int | str | None]:
    if get_survey_question(question_id) is None:
        raise HTTPException(status_code=404, detail="Survey question not found")

    match = get_survey_matcher(question_id)(body.text)
    if match is None:
        return {
            "matched": False,
            "slot_index": None,
            "canonical": None,
            "points": 0,
            "already_revealed": False,
        }

    slot_index = int(match["slot_index"])
    already_revealed = slot_index in set(body.revealed)
    return {
        "matched": True,
        "slot_index": slot_index,
        "canonical": match["canonical"],
        "points": 0 if already_revealed else match["points"],
        "already_revealed": already_revealed,
    }
