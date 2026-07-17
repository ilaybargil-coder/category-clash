from scripts.audit_question_bank import audit_question_bank


def test_deterministic_question_bank_audit_has_no_blocking_errors():
    report = audit_question_bank()

    assert report["duplicate_questions"] == []
    assert report["totals"]["duplicate_canonicals"] == 0
    assert report["totals"]["normalized_collisions"] == 0
    assert report["totals"]["canonical_answers"] >= 1_400


def test_every_question_has_a_meaningful_number_of_exact_forms():
    report = audit_question_bank()

    assert all(question["accepted_exact_forms"] >= 20 for question in report["questions"])
