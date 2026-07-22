import pytest

from app.game.validator import (
    AnswerStatus,
    RoundValidator,
    build_question_index,
    normalize_answer,
    skeleton_form,
)


def make_index():
    return build_question_index(
        [
            (1, "מנגו", None, []),
            (2, "פפאיה", None, ["פפיה"]),
            (3, "מסקרה", "mascara", ["רימל", "מסקארה"]),
            (4, "שפתון", "lipstick", []),
            (5, "אודם", "lipstick", []),
            (6, "סוסון ים", None, ["סוסון-ים"]),
            (7, "ליצ'י", None, []),
            (8, "מסוק", None, []),
        ]
    )


class TestNormalization:
    def test_trims_whitespace(self):
        assert normalize_answer("  מנגו  ") == "מנגו"

    def test_collapses_inner_whitespace(self):
        assert normalize_answer("סוסון   ים") == normalize_answer("סוסון ים")

    def test_lowercases_english(self):
        assert normalize_answer("BMW") == "bmw"

    def test_hebrew_final_letters(self):
        assert normalize_answer("לוויתן") == normalize_answer("לוויתנ")

    def test_removes_punctuation_as_space(self):
        assert normalize_answer("סוסון-ים") == normalize_answer("סוסון ים")

    def test_removes_geresh(self):
        assert normalize_answer("ליצ'י") == normalize_answer("ליצי")

    def test_removes_nikud(self):
        assert normalize_answer("מַנְגּוֹ") == "מנגו"

    def test_empty_is_empty(self):
        assert normalize_answer("   ") == ""


class TestSkeletonForm:
    def test_collapses_doubled_matres(self):
        assert skeleton_form("טלוויזייה") == skeleton_form("טלויזיה")

    def test_folds_explicit_sin_but_not_unpointed_shin(self):
        assert skeleton_form(normalize_answer("שׂ")) == skeleton_form("ס")
        assert skeleton_form(normalize_answer("ש")) != skeleton_form("ס")


class TestRoundValidator:
    def test_valid_answer(self):
        v = RoundValidator(make_index())
        result = v.check("מנגו")
        assert result.status == AnswerStatus.VALID
        assert result.entry.canonical == "מנגו"

    def test_valid_with_trailing_space(self):
        v = RoundValidator(make_index())
        assert v.check("מנגו ").status == AnswerStatus.VALID

    def test_invalid_answer(self):
        v = RoundValidator(make_index())
        assert v.check("תפוח").status == AnswerStatus.INVALID

    def test_empty_answer_invalid(self):
        v = RoundValidator(make_index())
        assert v.check("   ").status == AnswerStatus.INVALID

    def test_too_long_answer_invalid(self):
        v = RoundValidator(make_index(), max_length=10)
        assert v.check("א" * 11).status == AnswerStatus.INVALID

    def test_exact_duplicate(self):
        v = RoundValidator(make_index())
        assert v.check("מנגו").status == AnswerStatus.VALID
        assert v.check("מנגו").status == AnswerStatus.DUPLICATE

    def test_alias_matches_canonical(self):
        v = RoundValidator(make_index())
        assert v.check("פפיה").status == AnswerStatus.VALID

    def test_alias_of_used_answer_is_duplicate(self):
        v = RoundValidator(make_index())
        assert v.check("מסקרה").status == AnswerStatus.VALID
        assert v.check("רימל").status == AnswerStatus.DUPLICATE

    def test_semantic_group_blocks_second_answer(self):
        v = RoundValidator(make_index())
        assert v.check("שפתון").status == AnswerStatus.VALID
        assert v.check("אודם").status == AnswerStatus.TOO_SIMILAR

    def test_hyphen_variant_is_duplicate(self):
        v = RoundValidator(make_index())
        assert v.check("סוסון ים").status == AnswerStatus.VALID
        assert v.check("סוסון-ים").status == AnswerStatus.DUPLICATE

    def test_rejected_answer_can_be_retried_correctly(self):
        v = RoundValidator(make_index())
        assert v.check("תפוח").status == AnswerStatus.INVALID
        assert v.check("מנגו").status == AnswerStatus.VALID


class TestTypoTolerance:
    def test_is_disabled_by_default(self):
        v = RoundValidator(make_index())
        assert v.check("מסןק").status == AnswerStatus.INVALID

    def test_accepts_neighbor_key_substitution_in_short_word(self):
        v = RoundValidator(make_index(), fuzzy_enabled=True, fuzzy_min_length=4)
        result = v.check("מסןק")
        assert result.status == AnswerStatus.VALID
        assert result.entry is not None
        assert result.entry.canonical == "מסוק"

    def test_accepts_adjacent_transposition(self):
        v = RoundValidator(make_index(), fuzzy_enabled=True, fuzzy_min_length=4)
        assert v.check("מנוג").status == AnswerStatus.VALID

    def test_rejects_non_neighbor_substitution_in_short_word(self):
        v = RoundValidator(make_index(), fuzzy_enabled=True, fuzzy_min_length=4)
        assert v.check("מסאק").status == AnswerStatus.INVALID

    def test_rejects_an_ambiguous_typo(self):
        index = build_question_index(
            [
                (1, "מנורה", None, []),
                (2, "מניעה", None, []),
            ]
        )
        v = RoundValidator(index, fuzzy_enabled=True, fuzzy_min_length=4)
        assert v.check("מנירה").status == AnswerStatus.INVALID

    def test_fuzzy_alias_of_used_answer_is_duplicate(self):
        v = RoundValidator(make_index(), fuzzy_enabled=True, fuzzy_min_length=4)
        assert v.check("מסוק").status == AnswerStatus.VALID
        assert v.check("מסןק").status == AnswerStatus.DUPLICATE

    def test_accepts_dolphin_substitution(self):
        index = build_question_index([(1, "דולפין", None, [])])
        result = RoundValidator(index, fuzzy_enabled=True).check("דולפיו")
        assert result.status == AnswerStatus.VALID
        assert result.entry is not None
        assert result.entry.canonical == "דולפין"

    def test_accepts_two_keyboard_neighbor_edits_at_scaled_long_length(self):
        index = build_question_index([(1, "דולפינים", None, [])])
        validator = RoundValidator(index, fuzzy_enabled=True)
        assert validator.check("שולצינים").status == AnswerStatus.VALID

    def test_rejects_two_edits_below_scaled_length(self):
        index = build_question_index([(1, "דולפין", None, [])])
        validator = RoundValidator(index, fuzzy_enabled=True)
        assert validator.check("דולביא").status == AnswerStatus.INVALID

    def test_unrelated_word_stays_invalid_with_forgiving_layers(self):
        index = build_question_index([(1, "דולפין", None, [])])
        validator = RoundValidator(
            index,
            fuzzy_enabled=True,
            hebrew_skeleton_enabled=True,
        )
        assert validator.check("בננה").status == AnswerStatus.INVALID


class TestHebrewSkeletonTolerance:
    def test_accepts_single_vav_full_spelling_variant(self):
        index = build_question_index([(1, "טלוויזיה", None, [])])
        validator = RoundValidator(index, hebrew_skeleton_enabled=True)
        assert validator.check("טלויזיה").status == AnswerStatus.VALID

    def test_accepts_kaf_kuf_spelling_variant(self):
        index = build_question_index([(1, "קונצרט", None, [])])
        validator = RoundValidator(index, hebrew_skeleton_enabled=True)
        assert validator.check("כונצרט").status == AnswerStatus.VALID

    def test_accepts_tet_tav_spelling_variant(self):
        index = build_question_index([(1, "טורקיה", None, [])])
        validator = RoundValidator(index, hebrew_skeleton_enabled=True)
        assert validator.check("תורקיה").status == AnswerStatus.VALID

    def test_accepts_doubled_vav_variant(self):
        index = build_question_index([(1, "וורד", None, [])])
        validator = RoundValidator(index, hebrew_skeleton_enabled=True)
        assert validator.check("ורד").status == AnswerStatus.VALID

    def test_rejects_ambiguous_skeleton(self):
        index = build_question_index(
            [
                (1, "אבטיח", None, []),
                (2, "עבטיח", None, []),
            ]
        )
        validator = RoundValidator(index, hebrew_skeleton_enabled=True)
        assert validator.check("הבטיח").status == AnswerStatus.INVALID

    def test_exact_answer_wins_despite_skeleton_collision(self):
        index = build_question_index(
            [
                (1, "אבטיח", None, []),
                (2, "עבטיח", None, []),
            ]
        )
        result = RoundValidator(index, hebrew_skeleton_enabled=True).check("אבטיח")
        assert result.status == AnswerStatus.VALID
        assert result.entry is not None
        assert result.entry.answer_id == 1

    def test_skeleton_match_preserves_duplicate_logic(self):
        index = build_question_index([(1, "קונצרט", None, [])])
        validator = RoundValidator(index, hebrew_skeleton_enabled=True)
        assert validator.check("קונצרט").status == AnswerStatus.VALID
        assert validator.check("כונצרט").status == AnswerStatus.DUPLICATE

    def test_skeleton_match_preserves_semantic_group_logic(self):
        index = build_question_index(
            [
                (1, "קונצרט", "music", []),
                (2, "טורקיה", "music", []),
            ]
        )
        validator = RoundValidator(index, hebrew_skeleton_enabled=True)
        assert validator.check("קונצרט").status == AnswerStatus.VALID
        assert validator.check("תורקיה").status == AnswerStatus.TOO_SIMILAR


class TestSafeCompletion:
    def test_accepts_unique_multiword_prefix(self):
        index = build_question_index(
            [
                (1, "מחשבת ישראל", None, []),
                (2, "מדעי החברה", None, []),
            ]
        )
        result = RoundValidator(index).check("מחשבת")
        assert result.status == AnswerStatus.VALID
        assert result.entry is not None
        assert result.entry.canonical == "מחשבת ישראל"

    def test_rejects_prefix_shared_by_different_answers(self):
        index = build_question_index(
            [
                (1, "כבל HDMI", "cables", []),
                (2, "כבל USB", "cables", []),
            ]
        )
        assert RoundValidator(index).check("כבל").status == AnswerStatus.INVALID

    def test_exact_answer_wins_even_when_it_prefixes_other_answers(self):
        index = build_question_index(
            [
                (1, "כבל", "cables", []),
                (2, "כבל HDMI", "cables", []),
                (3, "כבל USB", "cables", []),
            ]
        )
        result = RoundValidator(index).check("כבל")
        assert result.status == AnswerStatus.VALID
        assert result.entry is not None
        assert result.entry.canonical == "כבל"

    def test_does_not_complete_two_character_fragment(self):
        assert RoundValidator(make_index()).check("מנ").status == AnswerStatus.INVALID

    def test_can_be_disabled(self):
        validator = RoundValidator(make_index(), unique_prefix_enabled=False)
        assert validator.check("פפי").status == AnswerStatus.INVALID

    def test_accepts_definite_article_for_exact_answer(self):
        result = RoundValidator(make_index()).check("המסוק")
        assert result.status == AnswerStatus.VALID
        assert result.entry is not None
        assert result.entry.canonical == "מסוק"

    def test_exact_form_starting_with_hebrew_he_wins(self):
        index = build_question_index(
            [
                (1, "הולנד", None, []),
                (2, "ולנד", None, []),
            ]
        )
        result = RoundValidator(index).check("הולנד")
        assert result.entry is not None
        assert result.entry.canonical == "הולנד"


@pytest.mark.parametrize(
    ("left", "right"),
    [
        pytest.param("מלך", "מלכ", id="final-kaf"),
        pytest.param("תום", "תומ", id="final-mem"),
        pytest.param("ישן", "ישנ", id="final-nun"),
        pytest.param("אלף", "אלפ", id="final-pe"),
        pytest.param("ארץ", "ארצ", id="final-tsadi"),
        pytest.param("מַנְגּוֹ", "מנגו", id="niqqud"),
        pytest.param("ליצ׳י", "ליצי", id="geresh"),
        pytest.param("צה״ל", "צהל", id="gershayim"),
        pytest.param("סוסון־ים", "סוסון ים", id="maqaf"),
        pytest.param("  ניו\tיורק\n", "ניו יורק", id="unicode-whitespace"),
        pytest.param("ＢＭＷ", "bmw", id="fullwidth-latin"),
        pytest.param("אייפון ١٥", "אייפון 15", id="arabic-indic-digits"),
        pytest.param("תפוּשׂ", "תפוס", id="explicit-sin"),
    ],
)
def test_normalization_equivalent_surface_forms(left: str, right: str):
    assert normalize_answer(left) == normalize_answer(right)


def _surface_validator(*canonicals: str) -> RoundValidator:
    return RoundValidator(
        build_question_index(
            [
                (answer_id, canonical, None, [])
                for answer_id, canonical in enumerate(canonicals, start=1)
            ]
        ),
        fuzzy_enabled=True,
        hebrew_skeleton_enabled=True,
        unique_prefix_enabled=False,
    )


@pytest.mark.parametrize(
    ("canonical", "submitted"),
    [
        pytest.param("סוסון ים", "סוסוןים", id="removed-space"),
        pytest.param("קוקה קולה", "קוקה-קולה", id="ascii-hyphen"),
        pytest.param("iPhone 15", "IPHONE-15", id="latin-brand-digit"),
        pytest.param("BMW X5", "ｂｍｗ־ｘ٥", id="mixed-width-brand"),
        pytest.param("PlayStation 5", "playstation5", id="latin-brand-compact"),
        pytest.param("מסוק", "המסוק", id="definite-article"),
        pytest.param("תפוחים", "ותפוחים", id="conjunction-prefix"),
        pytest.param("תפוחים", "בתפוחים", id="bet-prefix"),
        pytest.param("תפוחים", "כתפוחים", id="kaf-prefix"),
        pytest.param("תפוחים", "לתפוחים", id="lamed-prefix"),
        pytest.param("תפוחים", "מתפוחים", id="mem-prefix"),
        pytest.param("תפוחים", "שתפוחים", id="shin-prefix"),
        pytest.param("תפוחים", "והתפוחים", id="stacked-conjunction-article"),
        pytest.param("טלוויזיה", "טלויזייה", id="double-vav-and-yod"),
        pytest.param("וורד", "ורד", id="double-vav"),
        pytest.param("קונצרט", "כונצרט", id="kaf-kuf"),
        pytest.param("טורקיה", "תורקיה", id="tet-tav"),
        pytest.param("עיראק", "איראק", id="guttural-vowel-carrier"),
        pytest.param("וניל", "בניל", id="bet-vav"),
        pytest.param("וולוו", "בולבו", id="bet-double-vav-brand"),
        pytest.param("תפוס", "תפוּשׂ", id="samekh-explicit-sin"),
        pytest.param("מסוק", "מסןק", id="hebrew-neighbor-key"),
        pytest.param("מנגו", "מנוג", id="adjacent-transposition"),
        pytest.param("מנגו", "מנגגו", id="accidental-double-letter"),
        pytest.param("דולפינים", "שולצינים", id="two-bounded-neighbor-typos"),
        pytest.param("adidas", "adidqs", id="latin-neighbor-key"),
    ],
)
def test_surface_recall_battery(canonical: str, submitted: str):
    result = _surface_validator(canonical).check(submitted)
    assert result.status == AnswerStatus.VALID
    assert result.entry is not None
    assert result.entry.canonical == canonical


@pytest.mark.parametrize(
    ("canonical", "submitted"),
    [
        pytest.param("כלב", "כלוב", id="explicit-near-word-regression"),
        pytest.param("כלב", "חלב", id="het-is-not-kaf"),
        pytest.param("אור", "עור", id="short-guttural-real-words"),
        pytest.param("מאיר", "מעיר", id="four-letter-guttural-real-words"),
        pytest.param("פתה", "פטה", id="short-tet-tav-risk"),
        pytest.param("לילה", "כלילה", id="short-kaf-prefix-risk"),
        pytest.param("בתאי", "שבתאי", id="short-shin-prefix-risk"),
        pytest.param("דינה", "מדינה", id="short-mem-prefix-risk"),
        pytest.param("כלב", "כבל", id="short-real-word-transposition"),
        pytest.param("מסוק", "מסאק", id="non-neighbor-substitution"),
        pytest.param("דולפין", "דולביא", id="two-edits-below-threshold"),
        pytest.param("iphone15", "iphone16", id="different-model-number"),
        pytest.param("adidas", "adidos", id="non-neighbor-latin-substitution"),
        pytest.param("סוס", "שוש", id="unpointed-shin-is-not-sin"),
        pytest.param("לב", "לו", id="short-bet-vav-real-words"),
        pytest.param("מנגו", "בננה", id="unrelated-fruit"),
        pytest.param("קם", "מתעורר", id="semantic-synonym-is-not-surface-match"),
    ],
)
def test_surface_precision_battery(canonical: str, submitted: str):
    assert _surface_validator(canonical).check(submitted).status == AnswerStatus.INVALID


def test_normalized_form_collision_is_rejected():
    validator = _surface_validator("ליצ'י", "ליצי")
    assert validator.check("ליצ׳י").status == AnswerStatus.INVALID


def test_compact_form_collision_is_rejected():
    validator = _surface_validator("אב גד", "א בגד")
    assert validator.check("אבגד").status == AnswerStatus.INVALID


def test_prefix_expansions_that_point_to_two_answers_are_rejected():
    validator = _surface_validator("תפוחים", "התפוחים")
    assert validator.check("והתפוחים").status == AnswerStatus.INVALID


def test_hebrew_prefix_matching_can_be_disabled():
    validator = RoundValidator(make_index(), hebrew_prefixes_enabled=False)
    assert validator.check("המסוק").status == AnswerStatus.INVALID
