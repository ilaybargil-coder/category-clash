from app.game.validator import normalize_answer
from app.seed import QUESTIONS


def test_question_bank_is_substantially_populated():
    assert len(QUESTIONS) >= 30
    assert sum(len(question["answers"]) for question in QUESTIONS) >= 1_200
    assert all(len(question["answers"]) >= 20 for question in QUESTIONS)


def test_common_playtest_answers_are_accepted_forms():
    by_question = {question["text"]: question for question in QUESTIONS}

    def forms(question_text: str) -> set[str]:
        return {
            normalize_answer(form)
            for canonical, aliases, _group in by_question[question_text]["answers"]
            for form in (canonical, *aliases)
        }

    board_games = forms("כתבו שמות של משחקי קופסה וקלפים")
    assert normalize_answer("סולמות ונחשים") in board_games
    assert normalize_answer("אליאס") in board_games
    assert normalize_answer("רמי") in board_games

    green_vegetables = forms("כתבו שמות של ירקות ירוקים")
    assert normalize_answer("פלפל") in green_vegetables
    assert normalize_answer("פלפל ירוק") in green_vegetables

    school_subjects = forms("כתבו שמות של מקצועות לימוד בבית הספר")
    assert normalize_answer("מחשבת ישראל") in school_subjects
    assert normalize_answer("מדעי החברה") in school_subjects
    assert normalize_answer("צרפתית") in school_subjects
    assert normalize_answer("ספרדית") in school_subjects

    computer_equipment = forms("כתבו שמות של רכיבי מחשב וציוד היקפי")
    assert normalize_answer("כבל") in computer_equipment

    film_genres = forms("כתבו שמות של ז'אנרים בקולנוע")
    assert normalize_answer("דוקו") in film_genres


def test_questions_and_canonical_answers_are_unique():
    question_texts: set[str] = set()
    for question in QUESTIONS:
        assert question["text"] not in question_texts
        question_texts.add(question["text"])

        canonicals = [answer[0] for answer in question["answers"]]
        assert len(canonicals) == len(set(canonicals)), question["text"]


def test_normalized_forms_never_point_to_different_answers():
    for question in QUESTIONS:
        forms: dict[str, str] = {}
        for canonical, aliases, _group in question["answers"]:
            for form in (canonical, *aliases):
                normalized = normalize_answer(form)
                assert normalized
                assert len(form) <= 120
                previous = forms.get(normalized)
                assert previous in (None, canonical), (
                    question["text"],
                    form,
                    previous,
                    canonical,
                )
                forms[normalized] = canonical
