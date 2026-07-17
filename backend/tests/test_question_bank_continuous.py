"""Regression tests for human-reviewed continuous curation batches."""

from app.game.validator import AnswerStatus, RoundValidator, build_question_index
from app.question_bank_continuous import CURATED_ANSWER_ADDITIONS, CURATION_SOURCES
from app.seed import QUESTIONS


def _validator(question_text: str, *, fuzzy_enabled: bool = True) -> RoundValidator:
    question = next(question for question in QUESTIONS if question["text"] == question_text)
    return RoundValidator(
        build_question_index(
            [
                (answer_id, canonical, group, aliases)
                for answer_id, (canonical, aliases, group) in enumerate(
                    question["answers"], start=1
                )
            ]
        ),
        fuzzy_enabled=fuzzy_enabled,
    )


def test_every_continuously_curated_question_has_sources():
    assert set(CURATED_ANSWER_ADDITIONS) <= set(CURATION_SOURCES)
    assert all(CURATION_SOURCES[question] for question in CURATED_ANSWER_ADDITIONS)


def test_mille_feuille_spellings_are_accepted():
    for submitted in ("מילפיי", "מילפה", "מיל פיי", "קרמשניט"):
        result = _validator("כתבו שמות של קינוחים").check(submitted)
        assert result.status == AnswerStatus.VALID
        assert result.entry is not None
        assert result.entry.canonical == "מילפיי"


def test_croissant_and_common_misspellings_are_accepted():
    for submitted in ("קרואסון", "קוראסון", "קרוסון"):
        result = _validator("כתבו שמות של קינוחים").check(submitted)
        assert result.status == AnswerStatus.VALID
        assert result.entry is not None
        assert result.entry.canonical == "קרואסון"


def test_unique_prefix_completion_stays_question_scoped():
    result = _validator("כתבו שמות של קינוחים", fuzzy_enabled=False).check("מילפ")
    assert result.status == AnswerStatus.VALID
    assert result.entry is not None
    assert result.entry.canonical == "מילפיי"
