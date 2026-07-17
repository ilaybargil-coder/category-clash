from app.game.validator import normalize_answer
from app.seed import QUESTIONS


def test_question_bank_is_substantially_populated():
    assert len(QUESTIONS) >= 30
    assert sum(len(question["answers"]) for question in QUESTIONS) >= 500


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
