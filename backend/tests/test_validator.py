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
