"""Regression and quality-gate tests for the standalone V10 question batch."""

from app.game.validator import normalize_answer
from app.question_bank_expansion_v10 import NEW_QUESTIONS_V10
from app.seed import QUESTIONS
from scripts.audit_question_bank import audit_question_bank

EXPECTED_QUESTION_TEXTS = {
    "כתבו מילים בסלנג ישראלי",
    "כתבו דברים שיש במקרר",
    "כתבו דברים שלוקחים לים",
    "כתבו שמות של תוכניות ריאליטי",
    'כתבו שמות של דמויות מהתנ"ך',
    "כתבו שמות של דמויות מהארי פוטר",
    "כתבו שמות של זמרים בינלאומיים",
    "כתבו שמות של אוכל רחוב בעולם",
    "כתבו שמות של דמויות מהמיתולוגיה היוונית",
    "כתבו שמות של נהרות בעולם",
    "כתבו שמות של שפות מדוברות בעולם",
    "כתבו שמות של סוגי גבינות",
}


def test_all_v10_questions_are_loaded_into_the_assembled_bank():
    assembled_texts = {question["text"] for question in QUESTIONS}

    assert {question["text"] for question in NEW_QUESTIONS_V10} == (EXPECTED_QUESTION_TEXTS)
    assert EXPECTED_QUESTION_TEXTS <= assembled_texts


def test_each_v10_question_has_at_least_fifty_accepted_forms():
    for question in NEW_QUESTIONS_V10:
        accepted_forms = sum(
            1 + len(aliases) for _canonical, aliases, _group in question["answers"]
        )

        assert accepted_forms >= 50, question["text"]


def test_v10_questions_have_unique_canonicals_and_no_normalized_collisions():
    for question in NEW_QUESTIONS_V10:
        canonicals = [canonical for canonical, _aliases, _group in question["answers"]]
        assert len(canonicals) == len(set(canonicals)), question["text"]

        owners_by_form: dict[str, str] = {}
        for canonical, aliases, _group in question["answers"]:
            for form in (canonical, *aliases):
                normalized = normalize_answer(form)
                previous_owner = owners_by_form.get(normalized)
                assert previous_owner in (None, canonical), (
                    question["text"],
                    form,
                    canonical,
                    previous_owner,
                )
                owners_by_form[normalized] = canonical


def test_v10_preserves_the_question_bank_audit_quality_gate():
    report = audit_question_bank()

    assert report["duplicate_questions"] == []
    assert report["totals"]["duplicate_canonicals"] == 0
    assert report["totals"]["normalized_collisions"] == 0
