"""Regression and governance tests for the full 31-question V3 audit."""

from app.game.validator import AnswerStatus, RoundValidator, build_question_index, normalize_answer
from app.question_bank_expansion_v3 import (
    ANSWER_ALIAS_ADDITIONS_V3,
    QUESTION_EXPANSION_SOURCES_V3,
    QUESTION_EXPANSIONS_V3,
)
from app.seed import DEACTIVATED_QUESTION_TEXTS, QUESTIONS

BY_QUESTION = {question["text"]: question for question in QUESTIONS}


def index_for(question_text: str):
    answers = BY_QUESTION[question_text]["answers"]
    return build_question_index(
        [
            (answer_id, canonical, group, aliases)
            for answer_id, (canonical, aliases, group) in enumerate(answers, start=1)
        ]
    )


def exact_forms(question_text: str) -> set[str]:
    return {
        normalize_answer(form)
        for canonical, aliases, _group in BY_QUESTION[question_text]["answers"]
        for form in (canonical, *aliases)
    }


def test_every_question_was_reviewed_and_has_sources():
    question_names = set(BY_QUESTION)
    reviewed = set(QUESTION_EXPANSIONS_V3) | set(ANSWER_ALIAS_ADDITIONS_V3)
    assert question_names <= reviewed
    active_source_names = set(QUESTION_EXPANSION_SOURCES_V3) - set(DEACTIVATED_QUESTION_TEXTS)
    assert question_names == active_source_names
    assert all(QUESTION_EXPANSION_SOURCES_V3[name] for name in question_names)


def test_bank_has_large_high_quality_coverage():
    canonical_count = sum(len(question["answers"]) for question in QUESTIONS)
    alias_count = sum(
        len(aliases)
        for question in QUESTIONS
        for _canonical, aliases, _group in question["answers"]
    )
    accepted_exact_count = sum(len(exact_forms(question["text"])) for question in QUESTIONS)

    assert canonical_count >= 2_200
    assert alias_count >= 1_400
    assert accepted_exact_count >= 3_500
    assert all(len(exact_forms(question["text"])) >= 50 for question in QUESTIONS)


def test_no_v3_form_collides_between_answers():
    for question in QUESTIONS:
        seen: dict[str, str] = {}
        for canonical, aliases, _group in question["answers"]:
            for form in (canonical, *aliases):
                normalized = normalize_answer(form)
                previous = seen.get(normalized)
                assert previous in (None, canonical), (
                    question["text"],
                    form,
                    previous,
                    canonical,
                )
                seen[normalized] = canonical


def test_computer_drive_and_realistic_typos_are_accepted():
    validator = RoundValidator(
        index_for("כתבו שמות של רכיבי מחשב וציוד היקפי"),
        fuzzy_enabled=True,
    )
    result = validator.check("כןנן")
    assert result.status == AnswerStatus.VALID
    assert result.entry is not None
    assert result.entry.canonical == "כונן"


def test_computer_prefix_completion_is_question_scoped():
    validator = RoundValidator(index_for("כתבו שמות של רכיבי מחשב וציוד היקפי"))
    result = validator.check("כבל h")
    assert result.status == AnswerStatus.VALID
    assert result.entry is not None
    assert result.entry.canonical == "כבל HDMI"


def test_school_subject_completion_and_common_aliases():
    validator = RoundValidator(index_for("כתבו שמות של מקצועות לימוד בבית הספר"))
    result = validator.check("מחשבת")
    assert result.status == AnswerStatus.VALID
    assert result.entry is not None
    assert result.entry.canonical == "מחשבת ישראל"

    second = RoundValidator(index_for("כתבו שמות של מקצועות לימוד בבית הספר"))
    assert second.check("לשון").status == AnswerStatus.VALID


def test_existing_playtest_examples_stay_accepted():
    cases = {
        "כתבו שמות של ירקות ירוקים": ["פלפל"],
        "כתבו שמות של ז'אנרים בקולנוע": ["דוקו"],
        "כתבו שמות של משחקי קופסה וקלפים": ["סולמות", "אליאס", "רמי"],
        "כתבו שמות של כלי תחבורה": ["מסןק"],
    }
    for question_text, answers in cases.items():
        for answer in answers:
            validator = RoundValidator(index_for(question_text), fuzzy_enabled=True)
            assert validator.check(answer).status == AnswerStatus.VALID, (question_text, answer)
