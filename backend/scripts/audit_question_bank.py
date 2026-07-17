"""Deterministic quality audit for the version-controlled question bank.

This command performs no network or database writes. It is intended to be the
mandatory safety layer underneath human or AI-assisted content curation.

Run from ``backend`` with::

    python -m scripts.audit_question_bank
    python -m scripts.audit_question_bank --json
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import asdict, dataclass

from app.game.validator import normalize_answer
from app.seed import QUESTIONS


@dataclass(frozen=True)
class QuestionAudit:
    question: str
    canonical_answers: int
    aliases: int
    accepted_exact_forms: int
    semantic_groups: int
    singleton_semantic_groups: list[str]
    duplicate_canonicals: list[str]
    normalized_collisions: list[str]


def audit_question_bank() -> dict[str, object]:
    question_names: set[str] = set()
    duplicate_questions: list[str] = []
    audits: list[QuestionAudit] = []

    for question in QUESTIONS:
        question_text = question["text"]
        if question_text in question_names:
            duplicate_questions.append(question_text)
        question_names.add(question_text)

        forms: dict[str, str] = {}
        collisions: list[str] = []
        groups: Counter[str] = Counter()
        canonical_counts: Counter[str] = Counter()
        alias_count = 0

        for canonical, aliases, semantic_group in question["answers"]:
            canonical_counts[canonical] += 1
            if semantic_group:
                groups[semantic_group] += 1
            alias_count += len(aliases)

            for form in (canonical, *aliases):
                normalized = normalize_answer(form)
                if not normalized:
                    collisions.append(f"empty form for {canonical!r}")
                    continue
                previous = forms.get(normalized)
                if previous is not None and previous != canonical:
                    collisions.append(f"{form!r} -> {canonical!r} conflicts with {previous!r}")
                else:
                    forms[normalized] = canonical

        audits.append(
            QuestionAudit(
                question=question_text,
                canonical_answers=len(question["answers"]),
                aliases=alias_count,
                accepted_exact_forms=len(forms),
                semantic_groups=len(groups),
                singleton_semantic_groups=sorted(
                    group for group, count in groups.items() if count == 1
                ),
                duplicate_canonicals=sorted(
                    canonical for canonical, count in canonical_counts.items() if count > 1
                ),
                normalized_collisions=sorted(collisions),
            )
        )

    return {
        "totals": {
            "questions": len(audits),
            "canonical_answers": sum(item.canonical_answers for item in audits),
            "aliases": sum(item.aliases for item in audits),
            "accepted_exact_forms": sum(item.accepted_exact_forms for item in audits),
            "normalized_collisions": sum(len(item.normalized_collisions) for item in audits),
            "duplicate_canonicals": sum(len(item.duplicate_canonicals) for item in audits),
        },
        "duplicate_questions": sorted(duplicate_questions),
        "questions": [asdict(item) for item in audits],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true", help="emit JSON")
    args = parser.parse_args()
    report = audit_question_bank()

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        totals = report["totals"]
        print(
            "Question bank: "
            f"{totals['questions']} questions, "
            f"{totals['canonical_answers']} canonical answers, "
            f"{totals['aliases']} aliases, "
            f"{totals['accepted_exact_forms']} accepted exact forms"
        )
        for item in report["questions"]:
            warnings = []
            if item["normalized_collisions"]:
                warnings.append(f"{len(item['normalized_collisions'])} normalized collisions")
            if item["duplicate_canonicals"]:
                warnings.append(f"{len(item['duplicate_canonicals'])} duplicate canonicals")
            if item["singleton_semantic_groups"]:
                warnings.append(f"{len(item['singleton_semantic_groups'])} singleton groups")
            suffix = f" WARNING: {', '.join(warnings)}" if warnings else ""
            print(
                f"- {item['question']}: {item['canonical_answers']} canonical, "
                f"{item['aliases']} aliases{suffix}"
            )

    has_errors = (
        bool(report["duplicate_questions"])
        or bool(report["totals"]["normalized_collisions"])
        or bool(report["totals"]["duplicate_canonicals"])
    )
    return 1 if has_errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
