"""Regression and governance tests for the source-audited V9 categories."""

import pytest

from app.game.validator import AnswerStatus, RoundValidator, build_question_index
from app.question_bank_expansion_v9 import CURATION_SOURCES, EXPANSION_V9
from app.seed import QUESTIONS

EXPECTED_QUESTION_TEXTS = {
    "כתבו שמות של סדרות טלוויזיה",
    "כתבו שמות של שחקני כדורגל מפורסמים",
    "כתבו שמות של קבוצות כדורגל",
    "כתבו שמות של רשתות מזון מהיר",
    "כתבו שמות של אפליקציות ורשתות חברתיות",
    "כתבו שמות של מותגי אופנה וספורט",
    "כתבו שמות של סרטי אקשן מפורסמים",
    "כתבו שמות של חברות טכנולוגיה",
}
BY_QUESTION = {question["text"]: question for question in QUESTIONS}


def validator_for(question_text: str) -> RoundValidator:
    answers = BY_QUESTION[question_text]["answers"]
    return RoundValidator(
        build_question_index(
            [
                (answer_id, canonical, group, aliases)
                for answer_id, (canonical, aliases, group) in enumerate(answers, start=1)
            ]
        )
    )


def test_every_v9_question_has_at_least_two_sources():
    assert set(EXPANSION_V9) == set(CURATION_SOURCES) == EXPECTED_QUESTION_TEXTS
    assert all(len(sources) >= 2 for sources in CURATION_SOURCES.values())
    assert all(
        all(source.startswith("https://") for source in sources)
        for sources in CURATION_SOURCES.values()
    )


def test_v9_aliases_are_loaded_into_the_assembled_bank():
    for question_text, additions in EXPANSION_V9.items():
        assembled = {
            canonical: aliases
            for canonical, aliases, _group in BY_QUESTION[question_text]["answers"]
        }
        for canonical, aliases, _group in additions:
            assert canonical in assembled
            assert set(aliases) <= set(assembled[canonical])


def test_question_text_identifiers_are_unique():
    question_texts = [question["text"] for question in QUESTIONS]
    assert len(question_texts) == len(set(question_texts))


def test_v9_questions_have_non_empty_generous_answer_sets():
    assert EXPECTED_QUESTION_TEXTS <= set(BY_QUESTION)
    for question_text in EXPECTED_QUESTION_TEXTS:
        answers = BY_QUESTION[question_text]["answers"]
        assert answers
        assert len(answers) >= 15
        assert all(canonical.strip() for canonical, _aliases, _group in answers)


@pytest.mark.parametrize(
    ("question_text", "submitted", "canonical"),
    [
        ("כתבו שמות של סדרות טלוויזיה", "Shtisel", "שטיסל"),
        ("כתבו שמות של שחקני כדורגל מפורסמים", "R9", "רונאלדו"),
        ("כתבו שמות של קבוצות כדורגל", "PSG", "פריז סן ז'רמן"),
        ("כתבו שמות של רשתות מזון מהיר", "Burgeranch", "בורגראנץ'"),
        ("כתבו שמות של אפליקציות ורשתות חברתיות", "Twitter", "אקס"),
        ("כתבו שמות של מותגי אופנה וספורט", "The North Face", "דה נורת' פייס"),
        ("כתבו שמות של סרטי אקשן מפורסמים", "Top Gun", "אהבה בשחקים"),
        ("כתבו שמות של חברות טכנולוגיה", "Mobileye", "מובילאיי"),
    ],
)
def test_v9_real_alternate_names_resolve(
    question_text: str,
    submitted: str,
    canonical: str,
):
    result = validator_for(question_text).check(submitted)
    assert result.status == AnswerStatus.VALID
    assert result.entry is not None
    assert result.entry.canonical == canonical
