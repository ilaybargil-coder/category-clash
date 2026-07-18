"""Regression tests for the source-audited V8 stand-up expansion."""

import pytest

from app.game.validator import AnswerStatus, RoundValidator, build_question_index
from app.question_bank_expansion_v8 import CURATION_SOURCES, EXPANSION_V8
from app.seed import QUESTIONS

COMEDIANS_QUESTION_TEXT = "כתבו שמות של סטנדאפיסטים ישראליים"
LETTERS_QUESTION_TEXT = "כתבו שמות של אותיות באלף-בית העברי"
BY_QUESTION = {question["text"]: question for question in QUESTIONS}


def comedian_validator() -> RoundValidator:
    answers = BY_QUESTION[COMEDIANS_QUESTION_TEXT]["answers"]
    return RoundValidator(
        build_question_index(
            [
                (answer_id, canonical, group, aliases)
                for answer_id, (canonical, aliases, group) in enumerate(answers, start=1)
            ]
        )
    )


def test_comedians_question_is_present_with_verified_density_and_sources():
    assert COMEDIANS_QUESTION_TEXT in BY_QUESTION
    assert len(BY_QUESTION[COMEDIANS_QUESTION_TEXT]["answers"]) == 30
    assert set(EXPANSION_V8) == set(CURATION_SOURCES) == {COMEDIANS_QUESTION_TEXT}
    assert len(CURATION_SOURCES[COMEDIANS_QUESTION_TEXT]) >= 2


@pytest.mark.parametrize(
    ("submitted", "canonical"),
    [
        ("אדיר מילר", "אדיר מילר"),
        ("יוחאי ספונדר", "יוחאי ספונדי"),
        ("ישראל קטורזה", "ישראל קטורזה"),
        ("Adi Ashkenazi", "עדי אשכנזי"),
        ("Meni Ozeri", "מני עוזרי"),
        ("Tom Ya'ar", "תום יער"),
    ],
)
def test_comedian_canonicals_and_real_alternate_names_are_accepted(
    submitted: str,
    canonical: str,
):
    result = comedian_validator().check(submitted)
    assert result.status == AnswerStatus.VALID
    assert result.entry is not None
    assert result.entry.canonical == canonical


def test_letters_question_is_not_in_assembled_code_questions():
    assert LETTERS_QUESTION_TEXT not in BY_QUESTION
