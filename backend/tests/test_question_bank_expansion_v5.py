"""Regression and governance tests for the source-audited V5 curation."""

from app.game.validator import AnswerStatus, RoundValidator, build_question_index, normalize_answer
from app.question_bank_expansion_v5 import (
    CURATION_SOURCES,
    EXPANSION_V5,
    QUESTION_POLICIES_V5,
)
from app.seed import QUESTIONS

BY_QUESTION = {question["text"]: question for question in QUESTIONS}
TARGET_QUESTION_TEXTS = {
    "כתבו שמות של מדינות באסיה",
    "כתבו שמות של מדינות באירופה",
    "כתבו שמות של מדינות באפריקה",
    "כתבו שמות של ערים בישראל",
    "כתבו שמות של יסודות כימיים",
    "כתבו שמות של בירות בעולם",
}
DEEPENED_QUESTION_TEXTS = {
    "כתבו שמות של מדינות באסיה",
    "כתבו שמות של ערים בישראל",
}


def index_for(question_text: str):
    answers = BY_QUESTION[question_text]["answers"]
    return build_question_index(
        [
            (answer_id, canonical, group, aliases)
            for answer_id, (canonical, aliases, group) in enumerate(answers, start=1)
        ]
    )


def assert_resolves(question_text: str, submitted: str, canonical: str):
    result = RoundValidator(index_for(question_text)).check(submitted)
    assert result.status == AnswerStatus.VALID
    assert result.entry is not None
    assert result.entry.canonical == canonical


def test_v5_targets_have_policies_and_multiple_sources():
    assert TARGET_QUESTION_TEXTS <= set(BY_QUESTION)
    assert TARGET_QUESTION_TEXTS == set(CURATION_SOURCES)
    assert TARGET_QUESTION_TEXTS == set(QUESTION_POLICIES_V5)
    assert set(EXPANSION_V5) == DEEPENED_QUESTION_TEXTS
    assert all(len(sources) >= 2 for sources in CURATION_SOURCES.values())


def test_v5_policies_define_required_boundaries():
    required_fields = {
        "includes",
        "excludes",
        "granularity",
        "time_and_place",
        "brands",
        "language",
    }
    for policy in QUESTION_POLICIES_V5.values():
        assert set(policy) == required_fields
        assert isinstance(policy["excludes"], list)
        assert len(policy["excludes"]) >= 3


def test_closed_sets_and_requested_depth_are_present():
    assert len(BY_QUESTION["כתבו שמות של מדינות באסיה"]["answers"]) == 50
    assert len(BY_QUESTION["כתבו שמות של מדינות באירופה"]["answers"]) == 46
    assert len(BY_QUESTION["כתבו שמות של מדינות באפריקה"]["answers"]) == 54
    assert len(BY_QUESTION["כתבו שמות של ערים בישראל"]["answers"]) == 82
    assert len(BY_QUESTION["כתבו שמות של יסודות כימיים"]["answers"]) >= 40
    assert len(BY_QUESTION["כתבו שמות של בירות בעולם"]["answers"]) >= 50


def test_asian_country_canonicals_and_real_alternate_names_are_accepted():
    question = "כתבו שמות של מדינות באסיה"
    assert_resolves(question, "פלסטין", "פלסטין")
    assert_resolves(question, "State of Palestine", "פלסטין")
    assert_resolves(question, "Burma", "מיאנמר")
    assert_resolves(question, "Turkey", "טורקיה")


def test_new_israeli_cities_and_english_names_are_accepted():
    question = "כתבו שמות של ערים בישראל"
    assert_resolves(question, "כפר יונה", "כפר יונה")
    assert_resolves(question, "Ganei Tikva", "גני תקווה")
    assert_resolves(question, "Kafr Qara", "כפר קרע")
    assert_resolves(question, "Maghar", "מע'אר")


def test_european_country_canonicals_and_alternate_names_are_accepted():
    question = "כתבו שמות של מדינות באירופה"
    assert_resolves(question, "Deutschland", "גרמניה")
    assert_resolves(question, "נדרלנד", "הולנד")
    assert_resolves(question, "Netherlands", "הולנד")
    assert_resolves(question, "United Kingdom", "בריטניה")


def test_african_country_set_remains_complete_and_playable():
    question = "כתבו שמות של מדינות באפריקה"
    assert_resolves(question, "זימבבואה", "זימבבואה")
    assert_resolves(question, "Cabo Verde", "כף ורדה")
    assert_resolves(question, "Swaziland", "אסוואטיני")


def test_chemical_element_names_symbols_and_real_alternates_are_accepted():
    question = "כתבו שמות של יסודות כימיים"
    assert_resolves(question, "ברזל", "ברזל")
    assert_resolves(question, "Fe", "ברזל")
    assert_resolves(question, "Silicon", "צורן")
    assert_resolves(question, "וולפרם", "טונגסטן")


def test_world_capital_canonicals_and_english_names_are_accepted():
    question = "כתבו שמות של בירות בעולם"
    assert_resolves(question, "בייג'ינג", "בייג'ינג")
    assert_resolves(question, "Beijing", "בייג'ינג")
    assert_resolves(question, "Washington, D.C.", "וושינגטון")
    assert_resolves(question, "Addis Ababa", "אדיס אבבה")


def test_no_v5_target_form_collides_between_answers():
    for question_text in TARGET_QUESTION_TEXTS:
        seen: dict[str, str] = {}
        for canonical, aliases, _group in BY_QUESTION[question_text]["answers"]:
            for form in (canonical, *aliases):
                normalized = normalize_answer(form)
                previous = seen.get(normalized)
                assert previous in (None, canonical), (
                    question_text,
                    form,
                    previous,
                    canonical,
                )
                seen[normalized] = canonical
