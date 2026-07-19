"""Tests for the categories 1-20 content corrections (Claude audit)."""

from app.game.validator import (
    AnswerStatus,
    RoundValidator,
    build_question_index,
    normalize_answer,
)
from app.question_bank_corrections_claude import (
    CATEGORY_SCOPE_1_20,
    QUESTION_CORRECTIONS,
    apply_corrections,
)
from app.seed import (
    DEACTIVATED_QUESTION_TEXTS,
    QUESTIONS,
    QUESTIONS_BEFORE_CLAUDE_CORRECTIONS,
)

CORRECTED = QUESTIONS
CORRECTED_BY_TEXT = {question["text"]: question for question in CORRECTED}
ORIGINAL_BY_TEXT = {question["text"]: question for question in QUESTIONS_BEFORE_CLAUDE_CORRECTIONS}


def forms_of(question_text: str) -> dict[str, str]:
    """normalized form -> canonical, for a corrected question."""
    result: dict[str, str] = {}
    for canonical, aliases, _group in CORRECTED_BY_TEXT[question_text]["answers"]:
        for form in (canonical, *aliases):
            result.setdefault(normalize_answer(form), canonical)
    return result


def index_of(question_text: str):
    return build_question_index(
        [
            (answer_id, canonical, group, aliases)
            for answer_id, (canonical, aliases, group) in enumerate(
                CORRECTED_BY_TEXT[question_text]["answers"]
            )
        ]
    )


class TestScope:
    def test_all_corrections_target_existing_questions(self):
        existing = {question["text"] for question in QUESTIONS}
        for text in QUESTION_CORRECTIONS:
            assert text in existing or text in DEACTIVATED_QUESTION_TEXTS, text

    def test_corrections_stay_within_categories_1_to_20(self):
        assert set(QUESTION_CORRECTIONS) <= set(CATEGORY_SCOPE_1_20)

    def test_categories_21_to_31_are_untouched(self):
        for question in QUESTIONS:
            if question["text"] in CATEGORY_SCOPE_1_20:
                continue
            assert CORRECTED_BY_TEXT[question["text"]]["answers"] == question["answers"], question[
                "text"
            ]

    def test_apply_is_pure_and_idempotent(self):
        snapshot = [list(question["answers"]) for question in QUESTIONS_BEFORE_CLAUDE_CORRECTIONS]
        apply_corrections(QUESTIONS_BEFORE_CLAUDE_CORRECTIONS)
        assert snapshot == [
            list(question["answers"]) for question in QUESTIONS_BEFORE_CLAUDE_CORRECTIONS
        ]
        assert apply_corrections(CORRECTED) == CORRECTED


class TestIntegrityAfterCorrections:
    def test_no_normalized_form_points_to_two_answers(self):
        for question in CORRECTED:
            seen: dict[str, str] = {}
            for canonical, aliases, _group in question["answers"]:
                for form in (canonical, *aliases):
                    normalized = normalize_answer(form)
                    assert normalized, (question["text"], form)
                    previous = seen.get(normalized)
                    assert previous in (None, canonical), (
                        question["text"],
                        form,
                        previous,
                        canonical,
                    )
                    seen[normalized] = canonical

    def test_canonicals_are_unique_per_question(self):
        for question in CORRECTED:
            canonicals = [answer[0] for answer in question["answers"]]
            assert len(canonicals) == len(set(canonicals)), question["text"]

    def test_no_alias_equals_its_canonical(self):
        for question in CORRECTED:
            for canonical, aliases, _group in question["answers"]:
                assert canonical not in aliases, (question["text"], canonical)


class TestWrongAnswerFixes:
    def test_salak_no_longer_reachable_as_beet(self):
        forms = forms_of("כתבו שמות של פירות טרופיים")
        assert normalize_answer("סלק") not in forms
        assert forms[normalize_answer("סאלאק")] == "סאלאק"
        assert forms[normalize_answer("פרי הנחש")] == "סאלאק"
        assert forms[normalize_answer("סלאק")] == "סאלאק"

    def test_crayfish_alias_removed_from_lobster(self):
        forms = forms_of("כתבו שמות של בעלי חיים שחיים בים")
        assert normalize_answer("סרטן נהרות") not in forms
        assert normalize_answer("לובסטר") in forms

    def test_hygienist_is_own_profession(self):
        forms = forms_of("כתבו שמות של מקצועות")
        assert forms[normalize_answer("שיננית")] == "שיננית"
        assert forms[normalize_answer("רופא שיניים")] == "רופא שיניים"

    def test_olympic_diving_renamed(self):
        forms = forms_of("כתבו שמות של ענפי ספורט אולימפיים")
        assert forms[normalize_answer("קפיצות למים")] == "קפיצות למים"
        # "צלילה" נשארת כ-alias סלחני של הענף האמיתי.
        assert forms[normalize_answer("צלילה")] == "קפיצות למים"

    def test_generic_baby_alias_removed(self):
        forms = forms_of("כתבו שמות של ירקות ירוקים")
        assert normalize_answer("בייבי") not in forms
        assert normalize_answer("עלי בייבי") in forms


class TestExplicitMisspellingAliases:
    def test_iraq_common_misspelling_resolves_to_iraq_not_iran(self):
        # "איראק" נמצא במרחק עריכה 1 גם מעיראק וגם מאיראן, ולכן fuzzy
        # לבדו חייב לדחות אותו כעמום. ה-alias המפורש מכריע נכון.
        index = index_of("כתבו שמות של מדינות באסיה")
        entry = index.lookup(normalize_answer("איראק"))
        assert entry is not None
        assert entry.canonical == "עיראק"

    def test_double_vav_rose(self):
        forms = forms_of("כתבו שמות של פרחים")
        assert forms[normalize_answer("וורד")] == "ורד"

    def test_light_rail_alias_for_tram(self):
        forms = forms_of("כתבו שמות של כלי תחבורה")
        assert forms[normalize_answer("רכבת קלה")] == "חשמלית"
        assert forms[normalize_answer("הרכבת הקלה")] == "חשמלית"


class TestSemanticGroups:
    def _validator(self, question_text: str) -> RoundValidator:
        return RoundValidator(index_of(question_text))

    def test_swimsuit_and_bikini_block_each_other(self):
        validator = self._validator("כתבו שמות של פריטי לבוש")
        assert validator.check("בגד ים").status == AnswerStatus.VALID
        assert validator.check("ביקיני").status == AnswerStatus.TOO_SIMILAR

    def test_choco_drinks_block_each_other(self):
        validator = self._validator("כתבו שמות של משקאות")
        assert validator.check("שוקו").status == AnswerStatus.VALID
        assert validator.check("קקאו").status == AnswerStatus.TOO_SIMILAR
        assert validator.check("שוקולד חם").status == AnswerStatus.TOO_SIMILAR

    def test_coffee_variants_block_but_espresso_is_distinct(self):
        validator = self._validator("כתבו שמות של משקאות")
        assert validator.check("קפה").status == AnswerStatus.VALID
        assert validator.check("נס קפה").status == AnswerStatus.TOO_SIMILAR
        assert validator.check("אספרסו").status == AnswerStatus.VALID

    def test_ship_and_boat_names_block_each_other(self):
        validator = self._validator("כתבו שמות של כלי תחבורה")
        assert validator.check("אונייה").status == AnswerStatus.VALID
        assert validator.check("ספינה").status == AnswerStatus.TOO_SIMILAR


class TestAdditions:
    def test_winter_olympic_sports_are_accepted(self):
        forms = forms_of("כתבו שמות של ענפי ספורט אולימפיים")
        for sport in (
            "סקי",
            "סנובורד",
            "החלקה אמנותית",
            "הוקי קרח",
            "ביאתלון",
            "קרלינג",
            "ברייקדאנס",
        ):
            assert normalize_answer(sport) in forms, sport

    def test_verified_israeli_cities_are_accepted(self):
        forms = forms_of("כתבו שמות של ערים בישראל")
        for city in (
            "קריית אתא",
            "קרית אתא",
            "רמת השרון",
            "נתיבות",
            "אום אל פחם",
            "רהט",
            "סחנין",
            "סכנין",
            "שפרעם",
            "טמרה",
            "כפר קאסם",
            "ראש העין",
            "ביתר עילית",
        ):
            assert normalize_answer(city) in forms, city

    def test_additionally_verified_cities_are_added(self):
        forms = forms_of("כתבו שמות של ערים בישראל")
        assert forms[normalize_answer("קלנסווה")] == "קלנסווה"
        assert forms[normalize_answer("קלנסואה")] == "קלנסווה"
        assert forms[normalize_answer("טירה")] == "טירה"
        assert forms.get(normalize_answer("טירת כרמל")) == "טירת כרמל"

    def test_missing_capitals_are_accepted(self):
        forms = forms_of("כתבו שמות של ערי בירה בעולם")
        for capital in ("קייב", "טהרן", "בגדד", "דמשק", "רייקיאוויק", "קטמנדו", "אולן בטור"):
            assert normalize_answer(capital) in forms, capital

    def test_body_parts_additions(self):
        forms = forms_of("כתבו שמות של איברי גוף")
        for part in ("עצם", "שריר", "גולגולת", "עמוד שדרה", "ושט"):
            assert normalize_answer(part) in forms, part

    def test_transcontinental_countries_valid_on_both_continents(self):
        europe = forms_of("כתבו שמות של מדינות באירופה")
        asia = forms_of("כתבו שמות של מדינות באסיה")
        assert normalize_answer("טורקיה") in europe
        assert normalize_answer("טורקיה") in asia
        assert normalize_answer("רוסיה") in europe
        assert normalize_answer("רוסיה") in asia

    def test_israeli_desserts_added(self):
        forms = forms_of("כתבו שמות של קינוחים")
        for dessert in ("סופגנייה", "סופגניה", "אוזני המן", "ג'לי"):
            assert normalize_answer(dessert) in forms, dessert

    def test_additions_do_not_shadow_existing_answers(self):
        """Every added canonical is genuinely new for its question."""
        for text, correction in QUESTION_CORRECTIONS.items():
            if text in DEACTIVATED_QUESTION_TEXTS:
                continue
            original_forms = {
                normalize_answer(form)
                for canonical, aliases, _g in ORIGINAL_BY_TEXT[text]["answers"]
                for form in (canonical, *aliases)
            }
            renamed_away = {
                normalize_answer(old) for old in correction.get("rename_canonicals", {})
            }
            removed = {
                normalize_answer(alias)
                for aliases in correction.get("remove_aliases", {}).values()
                for alias in aliases
            }
            available = original_forms - renamed_away - removed
            for canonical, _aliases, _g in correction.get("add", []):
                assert normalize_answer(canonical) not in available, (text, canonical)
