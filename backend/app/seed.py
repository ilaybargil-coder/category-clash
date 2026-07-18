"""Idempotent seed for demo users and the curated Hebrew question bank.

Run with:  python -m app.seed
"""

import asyncio

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from .auth import hash_password
from .db import SessionLocal
from .models import AnswerAlias, ApprovedAnswer, Question, User
from .question_bank import ADDITIONAL_QUESTIONS
from .question_bank_continuous import CURATED_ALIAS_ADDITIONS, CURATED_ANSWER_ADDITIONS
from .question_bank_corrections_claude import QUESTION_CORRECTIONS, apply_corrections
from .question_bank_enrichment import QUESTION_ENRICHMENTS
from .question_bank_expansion_v2 import (
    ANSWER_ALIAS_ADDITIONS_V2,
    ANSWER_GROUP_UPDATES_V2,
    QUESTION_EXPANSIONS_V2,
)
from .question_bank_expansion_v3 import (
    ANSWER_ALIAS_ADDITIONS_V3,
    ANSWER_GROUP_UPDATES_V3,
    QUESTION_EXPANSION_SOURCES_V3,
    QUESTION_EXPANSIONS_V3,
)
from .question_bank_expansion_v4 import (
    ANSWER_ALIAS_ADDITIONS_V4,
    ANSWER_GROUP_UPDATES_V4,
    QUESTION_EXPANSION_SOURCES_V4,
    QUESTION_EXPANSIONS_V4,
    QUESTION_POLICIES_V4,
)
from .question_bank_expansion_v5 import (
    CURATION_SOURCES as CURATION_SOURCES_V5,
)
from .question_bank_expansion_v5 import (
    EXPANSION_V5,
)

# The V3 governance test audits the current QUESTIONS collection through the
# V3 registries. Register later closed-set questions there without copying any
# V4 answer data; their actual review policies and sources remain owned by V4.
for v4_question_text in QUESTION_POLICIES_V4:
    ANSWER_ALIAS_ADDITIONS_V3.setdefault(v4_question_text, {})
    QUESTION_EXPANSION_SOURCES_V3.setdefault(
        v4_question_text,
        QUESTION_EXPANSION_SOURCES_V4[v4_question_text],
    )

# Keep the V3 all-question governance registry aware of later source-audited
# batches.  V5 owns the current source records for its six target categories.
for v5_question_text, v5_sources in CURATION_SOURCES_V5.items():
    ANSWER_ALIAS_ADDITIONS_V3.setdefault(v5_question_text, {})
    QUESTION_EXPANSION_SOURCES_V3.setdefault(v5_question_text, v5_sources)

DEMO_PASSWORD = "demo1234"

DEMO_USERS = [
    {"username": "dana", "display_name": "דנה"},
    {"username": "omer", "display_name": "עומר"},
]

# answer tuples: (canonical, [aliases], semantic_group | None)
QUESTIONS: list[dict] = [
    {
        "text": "כתבו שמות של פירות טרופיים",
        "answers": [
            ("מנגו", [], None),
            ("אננס", [], None),
            ("פפאיה", ["פפיה"], None),
            ("קוקוס", ["אגוז קוקוס"], None),
            ("בננה", ["בננות"], None),
            ("גויאבה", ["גויבה"], None),
            ("ליצ'י", ["ליצי"], None),
            ("פסיפלורה", ["שעונית"], None),
            ("קיווי", ["קיוי"], None),
            ("פיטאיה", ["פרי הדרקון", "פיטאייה"], None),
            ("קרמבולה", [], None),
        ],
    },
    {
        "text": "כתבו שמות של מוצרי איפור",
        "answers": [
            ("מסקרה", ["רימל", "מסקארה", "מסקרה שחורה"], "mascara"),
            ("שפתון", [], "lipstick"),
            ("אודם", [], "lipstick"),
            ("מייקאפ", ["פאונדיישן", "מייק אפ"], "foundation"),
            ("פודרה", [], None),
            ("סומק", ["בלאש"], "blush"),
            ("צללית", ["צלליות", "צללית עיניים"], None),
            ("אייליינר", ["איילינר", "עיפרון עיניים"], None),
            ("קונסילר", [], None),
            ("ברונזר", [], None),
            ("ליפגלוס", ["גלוס"], None),
        ],
    },
    {
        "text": "כתבו שמות של בעלי חיים שחיים בים",
        "answers": [
            ("דולפין", ["דולפינים"], None),
            ("כריש", ["כרישים"], None),
            ("לוויתן", ["לויתן"], None),
            ("תמנון", ["אוקטופוס"], None),
            ("מדוזה", ["מדוזות"], None),
            ("סוסון ים", ["סוסון-ים"], None),
            ("צב ים", [], None),
            ("דיונון", [], None),
            ("כוכב ים", [], None),
            ("שרימפס", ["חסילון"], "shrimp"),
        ],
    },
    {
        "text": "כתבו שמות של ירקות ירוקים",
        "answers": [
            ("מלפפון", ["מלפפונים"], None),
            ("חסה", [], None),
            ("ברוקולי", [], None),
            ("קישוא", ["זוקיני"], "zucchini"),
            ("תרד", [], None),
            ("סלרי", [], None),
            ("כרוב", ["כרוב ירוק"], None),
            ("אפונה", [], None),
            ("שעועית ירוקה", [], None),
            ("ארטישוק", [], None),
        ],
    },
    {
        "text": "כתבו שמות של מותגי רכב",
        "answers": [
            ("טויוטה", [], None),
            ("מאזדה", ["מזדה"], None),
            ("יונדאי", ["יונדיי"], None),
            ("קיה", [], None),
            ("פורד", [], None),
            ("מרצדס", ["מרצדס בנץ"], None),
            ("במוו", ["ב.מ.וו", "bmw", "בי אם דבליו"], None),
            ("סקודה", [], None),
            ("סובארו", [], None),
            ("הונדה", [], None),
            ("פולקסווגן", ["פולקסוואגן"], None),
        ],
    },
    {
        "text": "כתבו שמות של ענפי ספורט אולימפיים",
        "answers": [
            ("שחייה", ["שחיה"], None),
            ("אתלטיקה", ["אתלטיקה קלה"], None),
            ("התעמלות", ["ג'ימנסטיקה"], "gymnastics"),
            ("ג'ודו", ["גודו"], None),
            ("כדורסל", [], None),
            ("כדורגל", [], None),
            ("טניס", [], None),
            ("רכיבת אופניים", ["אופניים"], None),
            ("חתירה", [], None),
            ("סיף", [], None),
        ],
    },
    {
        "text": "כתבו שמות של כלי נגינה",
        "answers": [
            ("גיטרה", ["גיטרה חשמלית", "גיטרה אקוסטית"], "guitar"),
            ("פסנתר", ["פסנתר כנף"], None),
            ("תופים", ["מערכת תופים", "תוף"], None),
            ("חליל", ["חליל צד"], None),
            ("חלילית", [], None),
            ("כינור", [], None),
            ("חצוצרה", [], None),
            ("סקסופון", [], None),
            ("צ'לו", ["צלו"], None),
            ("נבל", [], None),
            ("אקורדיון", [], None),
        ],
    },
    {
        "text": "כתבו טעמים של גלידה",
        "answers": [
            ("וניל", ["ווניל"], None),
            ("שוקולד", [], None),
            ("תות", ["תות שדה"], None),
            ("פיסטוק", [], None),
            ("מנגו", [], None),
            ("לימון", [], None),
            ("קרמל", ["קרמל מלוח"], None),
            ("עוגיות", ["קוקיס"], "cookies"),
            ("בננה", [], None),
            ("מוקה", [], None),
        ],
    },
    {
        "text": "כתבו שמות של ערי בירה בעולם",
        "answers": [
            ("פריז", ["פריס"], None),
            ("לונדון", [], None),
            ("רומא", [], None),
            ("מדריד", [], None),
            ("ברלין", [], None),
            ("אתונה", [], None),
            ("ליסבון", [], None),
            ("וינה", [], None),
            ("ירושלים", [], None),
            ("אוסלו", [], None),
            ("מוסקבה", [], None),
            ("טוקיו", [], None),
        ],
    },
]

EUROPE_QUESTION_TEXT = "כתבו שמות של מדינות באירופה"
EUROPE_COUNTRY_CANONICALS = {
    canonical
    for question in ADDITIONAL_QUESTIONS
    if question["text"] == EUROPE_QUESTION_TEXT
    for canonical, _aliases, _group in question["answers"]
}
EUROPE_ALLOWED_CANONICALS = EUROPE_COUNTRY_CANONICALS | {"טורקיה", "קוסובו"}

QUESTIONS.extend(ADDITIONAL_QUESTIONS)

for question in QUESTIONS:
    # Europe now owns its complete 44-state core plus two documented legacy
    # policy extensions in question_bank.py.  The old enrichment also included
    # constituent countries and Cyprus outside that policy.
    if question["text"] != EUROPE_QUESTION_TEXT:
        question["answers"].extend(QUESTION_ENRICHMENTS.get(question["text"], []))
    question["answers"].extend(QUESTION_EXPANSIONS_V2.get(question["text"], []))

    group_updates = ANSWER_GROUP_UPDATES_V2.get(question["text"], {})
    if group_updates:
        question["answers"] = [
            (canonical, aliases, group_updates.get(canonical, group))
            for canonical, aliases, group in question["answers"]
        ]

    answers_by_canonical = {
        canonical: aliases for canonical, aliases, _group in question["answers"]
    }
    for canonical, aliases in ANSWER_ALIAS_ADDITIONS_V2.get(question["text"], {}).items():
        target = answers_by_canonical.get(canonical)
        if target is None:
            raise ValueError(
                f"Alias expansion targets missing answer {canonical!r} "
                f"in question {question['text']!r}"
            )
        for alias in aliases:
            if alias != canonical and alias not in target:
                target.append(alias)

    existing_canonicals = {canonical for canonical, _aliases, _group in question["answers"]}
    for canonical, aliases, group in QUESTION_EXPANSIONS_V3.get(question["text"], []):
        if canonical not in existing_canonicals:
            question["answers"].append((canonical, list(aliases), group))
            existing_canonicals.add(canonical)

QUESTIONS_BEFORE_CLAUDE_CORRECTIONS = QUESTIONS
QUESTIONS = apply_corrections(QUESTIONS_BEFORE_CLAUDE_CORRECTIONS)

for question in QUESTIONS:
    if question["text"] == EUROPE_QUESTION_TEXT:
        question["answers"] = [
            answer for answer in question["answers"] if answer[0] in EUROPE_ALLOWED_CANONICALS
        ]

for question in QUESTIONS:
    group_updates_v3 = ANSWER_GROUP_UPDATES_V3.get(question["text"], {})
    if group_updates_v3:
        question["answers"] = [
            (canonical, aliases, group_updates_v3.get(canonical, group))
            for canonical, aliases, group in question["answers"]
        ]

    answers_by_canonical_v3 = {
        canonical: aliases for canonical, aliases, _group in question["answers"]
    }
    for canonical, aliases in ANSWER_ALIAS_ADDITIONS_V3.get(question["text"], {}).items():
        target = answers_by_canonical_v3.get(canonical)
        if target is None:
            raise ValueError(
                f"V3 alias expansion targets missing answer {canonical!r} "
                f"in question {question['text']!r}"
            )
        for alias in aliases:
            if alias != canonical and alias not in target:
                target.append(alias)

    existing_canonicals = {canonical for canonical, _aliases, _group in question["answers"]}
    for canonical, aliases, group in QUESTION_EXPANSIONS_V4.get(question["text"], []):
        if canonical not in existing_canonicals:
            question["answers"].append((canonical, list(aliases), group))
            existing_canonicals.add(canonical)

    group_updates_v4 = ANSWER_GROUP_UPDATES_V4.get(question["text"], {})
    if group_updates_v4:
        question["answers"] = [
            (canonical, aliases, group_updates_v4.get(canonical, group))
            for canonical, aliases, group in question["answers"]
        ]

    answers_by_canonical_v4 = {
        canonical: aliases for canonical, aliases, _group in question["answers"]
    }
    for canonical, aliases in ANSWER_ALIAS_ADDITIONS_V4.get(question["text"], {}).items():
        target = answers_by_canonical_v4.get(canonical)
        if target is None:
            raise ValueError(
                f"V4 alias expansion targets missing answer {canonical!r} "
                f"in question {question['text']!r}"
            )
        for alias in aliases:
            if alias != canonical and alias not in target:
                target.append(alias)

    answers_by_canonical_v5 = {
        canonical: aliases for canonical, aliases, _group in question["answers"]
    }
    for canonical, aliases, group in EXPANSION_V5.get(question["text"], []):
        target = answers_by_canonical_v5.get(canonical)
        if target is None:
            copied_aliases = list(aliases)
            question["answers"].append((canonical, copied_aliases, group))
            answers_by_canonical_v5[canonical] = copied_aliases
            continue
        for alias in aliases:
            if alias != canonical and alias not in target:
                target.append(alias)

    existing_canonicals = {canonical for canonical, _aliases, _group in question["answers"]}
    for canonical, aliases, group in CURATED_ANSWER_ADDITIONS.get(question["text"], []):
        if canonical not in existing_canonicals:
            question["answers"].append((canonical, list(aliases), group))
            existing_canonicals.add(canonical)

    answers_by_canonical = {
        canonical: aliases for canonical, aliases, _group in question["answers"]
    }
    for canonical, aliases in CURATED_ALIAS_ADDITIONS.get(question["text"], {}).items():
        target = answers_by_canonical.get(canonical)
        if target is None:
            raise ValueError(
                f"Continuous alias expansion targets missing answer {canonical!r} "
                f"in question {question['text']!r}"
            )
        for alias in aliases:
            if alias != canonical and alias not in target:
                target.append(alias)


LEGACY_CANONICAL_RENAMES: dict[str, dict[str, str]] = {
    "כתבו שמות של משחקי קופסה וקלפים": {
        "סולמות וחבלים": "סולמות ונחשים",
    },
}
for question_text, correction in QUESTION_CORRECTIONS.items():
    LEGACY_CANONICAL_RENAMES.setdefault(question_text, {}).update(
        correction.get("rename_canonicals", {})
    )

LEGACY_ALIAS_REMOVALS: dict[str, dict[str, list[str]]] = {
    question_text: correction["remove_aliases"]
    for question_text, correction in QUESTION_CORRECTIONS.items()
    if correction.get("remove_aliases")
}

LEGACY_CANONICAL_DEACTIVATIONS: dict[str, set[str]] = {
    EUROPE_QUESTION_TEXT: {
        "אנגליה",
        "סקוטלנד",
        "ויילס",
        "קפריסין",
    },
}


async def seed() -> None:
    async with SessionLocal() as session:
        existing_users = (await session.execute(select(User.username))).scalars().all()
        for demo in DEMO_USERS:
            if demo["username"] not in existing_users:
                session.add(
                    User(
                        username=demo["username"],
                        display_name=demo["display_name"],
                        password_hash=hash_password(DEMO_PASSWORD),
                        coins=100,
                    )
                )

        existing_questions = {
            question.text: question
            for question in (
                (
                    await session.execute(
                        select(Question).options(
                            selectinload(Question.answers).selectinload(ApprovedAnswer.aliases)
                        )
                    )
                )
                .scalars()
                .unique()
                .all()
            )
        }
        for q in QUESTIONS:
            question = existing_questions.get(q["text"])
            if question is None:
                question = Question(text=q["text"])
                session.add(question)
                existing_questions[q["text"]] = question

            answers_by_canonical = {answer.canonical: answer for answer in question.answers}
            for canonical in LEGACY_CANONICAL_DEACTIVATIONS.get(q["text"], set()):
                legacy_answer = answers_by_canonical.get(canonical)
                if legacy_answer is not None:
                    legacy_answer.is_active = False

            for old_canonical, new_canonical in LEGACY_CANONICAL_RENAMES.get(q["text"], {}).items():
                legacy_answer = answers_by_canonical.get(old_canonical)
                if legacy_answer is not None and new_canonical not in answers_by_canonical:
                    legacy_answer.canonical = new_canonical
                    answers_by_canonical.pop(old_canonical)
                    answers_by_canonical[new_canonical] = legacy_answer
                elif legacy_answer is not None:
                    legacy_answer.is_active = False

            for canonical, aliases_to_remove in LEGACY_ALIAS_REMOVALS.get(q["text"], {}).items():
                answer = answers_by_canonical.get(canonical)
                if answer is not None:
                    answer.aliases = [
                        alias for alias in answer.aliases if alias.alias not in aliases_to_remove
                    ]

            for canonical, aliases, group in q["answers"]:
                answer = answers_by_canonical.get(canonical)
                if answer is None:
                    answer = ApprovedAnswer(
                        canonical=canonical,
                        semantic_group=group,
                    )
                    question.answers.append(answer)
                    answers_by_canonical[canonical] = answer
                elif group is not None:
                    answer.semantic_group = group

                existing_aliases = {item.alias for item in answer.aliases}
                for alias in aliases:
                    if alias not in existing_aliases and alias != canonical:
                        answer.aliases.append(AnswerAlias(alias=alias))
                        existing_aliases.add(alias)

        await session.commit()
    print("Seed complete.")


if __name__ == "__main__":
    asyncio.run(seed())
