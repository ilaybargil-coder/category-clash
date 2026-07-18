"""Regression and governance tests for the source-audited V4 curation."""

from app.game.validator import AnswerStatus, RoundValidator, build_question_index, normalize_answer
from app.question_bank_expansion_v4 import (
    ANSWER_ALIAS_ADDITIONS_V4,
    ANSWER_GROUP_UPDATES_V4,
    QUESTION_EXPANSION_SOURCES_V4,
    QUESTION_EXPANSIONS_V4,
    QUESTION_POLICIES_V4,
)
from app.seed import QUESTIONS

BY_QUESTION = {question["text"]: question for question in QUESTIONS}
NEW_QUESTION_TEXTS = {
    "כתבו שמות של אותיות באלף-בית העברי",
    "כתבו שמות של מדינות בארצות הברית",
    "כתבו שמות של מדינות באפריקה",
}


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


def assert_resolves(question_text: str, submitted: str, canonical: str):
    result = RoundValidator(index_for(question_text)).check(submitted)
    assert result.status == AnswerStatus.VALID
    assert result.entry is not None
    assert result.entry.canonical == canonical


def test_v4_questions_and_touched_categories_have_sources():
    curated_questions = (
        set(QUESTION_EXPANSIONS_V4) | set(ANSWER_ALIAS_ADDITIONS_V4) | set(ANSWER_GROUP_UPDATES_V4)
    )
    assert curated_questions == set(QUESTION_EXPANSION_SOURCES_V4)
    assert NEW_QUESTION_TEXTS <= set(BY_QUESTION)
    assert NEW_QUESTION_TEXTS == set(QUESTION_POLICIES_V4)
    assert all(
        len(QUESTION_EXPANSION_SOURCES_V4[question_text]) >= 2
        for question_text in NEW_QUESTION_TEXTS
    )


def test_new_question_policies_define_required_boundaries():
    required_fields = {
        "includes",
        "excludes",
        "granularity",
        "time_and_place",
        "brands",
        "language",
    }
    for policy in QUESTION_POLICIES_V4.values():
        assert set(policy) == required_fields
        assert isinstance(policy["excludes"], list)
        assert len(policy["excludes"]) >= 3


def test_new_closed_sets_are_complete_and_playable():
    assert len(BY_QUESTION["כתבו שמות של אותיות באלף-בית העברי"]["answers"]) == 22
    assert len(BY_QUESTION["כתבו שמות של מדינות בארצות הברית"]["answers"]) == 50
    assert len(BY_QUESTION["כתבו שמות של מדינות באפריקה"]["answers"]) == 54
    assert all(len(exact_forms(question_text)) >= 50 for question_text in NEW_QUESTION_TEXTS)


def test_hebrew_letter_canonicals_symbols_and_transliterations_are_accepted():
    question = "כתבו שמות של אותיות באלף-בית העברי"
    assert_resolves(question, "אלף", "אלף")
    assert_resolves(question, "א", "אלף")
    assert_resolves(question, "Aleph", "אלף")
    assert_resolves(question, "ך", "כף")


def test_us_state_canonicals_english_names_and_postal_codes_are_accepted():
    question = "כתבו שמות של מדינות בארצות הברית"
    assert_resolves(question, "קליפורניה", "קליפורניה")
    assert_resolves(question, "California", "קליפורניה")
    assert_resolves(question, "CA", "קליפורניה")
    assert_resolves(question, "West Virginia", "וירג'יניה המערבית")


def test_african_country_canonicals_and_real_alternate_names_are_accepted():
    question = "כתבו שמות של מדינות באפריקה"
    assert_resolves(question, "קניה", "קניה")
    assert_resolves(question, "Kenya", "קניה")
    assert_resolves(question, "Swaziland", "אסוואטיני")
    assert_resolves(question, "DRC", "הרפובליקה הדמוקרטית של קונגו")


def test_existing_categories_receive_canonicals_and_non_inferred_aliases():
    assert_resolves("כתבו שמות של מדינות באסיה", "כווית", "כווית")
    assert_resolves("כתבו שמות של מדינות באסיה", "Cyprus", "קפריסין")
    assert_resolves("כתבו שמות של ערי בירה בעולם", "Ouagadougou", "ואגאדוגו")
    assert_resolves("כתבו שמות של גרמי שמיים במערכת השמש", "Jupiter", "צדק")


def test_no_v4_form_collides_between_answers():
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
