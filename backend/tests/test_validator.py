from app.game.validator import (
    AnswerStatus,
    RoundValidator,
    build_question_index,
    normalize_answer,
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
