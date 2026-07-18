"""Regression and governance tests for the source-audited V7 expansion."""

import pytest

from app.game.validator import AnswerStatus, RoundValidator, build_question_index, normalize_answer
from app.question_bank_expansion_v7 import CURATION_SOURCES, EXPANSION_V7
from app.seed import QUESTIONS

BY_QUESTION = {question["text"]: question for question in QUESTIONS}
EXPECTED_MINIMUM_COUNTS = {
    "כתבו שמות של זמרים וזמרות ישראלים": 105,
    "כתבו שמות של מאכלים ישראליים": 100,
    "כתבו שמות של מותגי חטיפים ושוקולד": 100,
    "כתבו שמות של גיבורי על": 101,
    "כתבו שמות של דמויות מצוירות מפורסמות": 105,
    "כתבו שמות של סרטים של דיסני ופיקסאר": 90,
    "כתבו שמות של משחקי מחשב ווידאו": 110,
    "כתבו שמות של סוגי ממתקים": 82,
    "כתבו שמות של חיות משק וחווה": 67,
    "כתבו דברים שמוצאים במטבח": 110,
    "כתבו שמות של ירקות ירוקים": 63,
    "כתבו שמות של פירות טרופיים": 55,
    "כתבו שמות של מוצרי איפור": 63,
    "כתבו שמות של פרחים": 90,
    "כתבו שמות של בעלי חיים שחיים בים": 91,
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


def test_v7_targets_are_live_and_have_multiple_sources():
    assert set(EXPANSION_V7) == set(CURATION_SOURCES) == set(EXPECTED_MINIMUM_COUNTS)
    assert set(EXPANSION_V7) <= set(BY_QUESTION)
    assert all(len(sources) >= 2 for sources in CURATION_SOURCES.values())


def test_v7_adds_substantial_density_without_padding_closed_sets():
    assert sum(len(additions) for additions in EXPANSION_V7.values()) >= 500
    for question_text, minimum in EXPECTED_MINIMUM_COUNTS.items():
        assert len(BY_QUESTION[question_text]["answers"]) >= minimum


@pytest.mark.parametrize(
    ("question_text", "submitted", "canonical"),
    [
        ("כתבו שמות של זמרים וזמרות ישראלים", "רביד פלוטניק", "רביד פלוטניק"),
        ("כתבו שמות של זמרים וזמרות ישראלים", "נצ'י נצ'", "רביד פלוטניק"),
        ("כתבו שמות של מאכלים ישראליים", "גונדי", "גונדי"),
        ("כתבו שמות של מאכלים ישראליים", "Gondi", "גונדי"),
        ("כתבו שמות של מותגי חטיפים ושוקולד", "טאקיס", "טאקיס"),
        ("כתבו שמות של מותגי חטיפים ושוקולד", "Takis", "טאקיס"),
        ("כתבו שמות של גיבורי על", "מיסטר פנטסטיק", "מיסטר פנטסטיק"),
        ("כתבו שמות של גיבורי על", "ריד ריצ'רדס", "מיסטר פנטסטיק"),
        ("כתבו שמות של דמויות מצוירות מפורסמות", "שום שן", "שום שן"),
        ("כתבו שמות של דמויות מצוירות מפורסמות", "Toothless", "שום שן"),
        ("כתבו שמות של סרטים של דיסני ופיקסאר", "צעצוע של סיפור 5", "צעצוע של סיפור 5"),
        ("כתבו שמות של סרטים של דיסני ופיקסאר", "Toy Story 5", "צעצוע של סיפור 5"),
        ("כתבו שמות של משחקי מחשב ווידאו", "סטארדיו ואלי", "סטארדיו ואלי"),
        ("כתבו שמות של משחקי מחשב ווידאו", "Stardew Valley", "סטארדיו ואלי"),
        ("כתבו שמות של סוגי ממתקים", "בריטל בוטנים", "בריטל בוטנים"),
        ("כתבו שמות של סוגי ממתקים", "Peanut brittle", "בריטל בוטנים"),
        ("כתבו שמות של חיות משק וחווה", "תולעת משי", "תולעת משי"),
        ("כתבו שמות של חיות משק וחווה", "Silkworm", "תולעת משי"),
        ("כתבו דברים שמוצאים במטבח", "בלנדר מוט", "בלנדר מוט"),
        ("כתבו דברים שמוצאים במטבח", "Immersion blender", "בלנדר מוט"),
        ("כתבו שמות של ירקות ירוקים", "רפיני", "רפיני"),
        ("כתבו שמות של ירקות ירוקים", "Broccoli rabe", "רפיני"),
        ("כתבו שמות של פירות טרופיים", "תפוח קשיו", "תפוח קשיו"),
        ("כתבו שמות של פירות טרופיים", "Cashew apple", "תפוח קשיו"),
        ("כתבו שמות של מוצרי איפור", "סומק נוזלי", "סומק נוזלי"),
        ("כתבו שמות של מוצרי איפור", "Liquid blush", "סומק נוזלי"),
        ("כתבו שמות של פרחים", "נימפאה", "נימפאה"),
        ("כתבו שמות של פרחים", "Water lily", "נימפאה"),
        ("כתבו שמות של בעלי חיים שחיים בים", "סבידה", "סבידה"),
        ("כתבו שמות של בעלי חיים שחיים בים", "Cuttlefish", "סבידה"),
    ],
)
def test_v7_canonicals_and_real_alternate_names_are_accepted(
    question_text: str,
    submitted: str,
    canonical: str,
):
    assert_resolves(question_text, submitted, canonical)


def test_v7_unique_prefix_completion_remains_unambiguous():
    result = RoundValidator(index_for("כתבו שמות של משחקי מחשב ווידאו")).check("דיסקו אלי")
    assert result.status == AnswerStatus.VALID
    assert result.entry is not None
    assert result.entry.canonical == "דיסקו אליסיום"


def test_v7_variants_share_points_when_they_are_the_same_product_family():
    validator = RoundValidator(index_for("כתבו שמות של מוצרי איפור"))
    assert validator.check("מייקאפ").status == AnswerStatus.VALID
    assert validator.check("מייקאפ נוזלי").status == AnswerStatus.TOO_SIMILAR


def test_v7_alias_recipe_omits_normalization_only_duplicates():
    for question_text, additions in EXPANSION_V7.items():
        for canonical, aliases, _group in additions:
            forms = [normalize_answer(form) for form in (canonical, *aliases)]
            assert len(forms) == len(set(forms)), (question_text, canonical, aliases)


def test_no_v7_target_form_collides_between_answers():
    for question_text in EXPANSION_V7:
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
