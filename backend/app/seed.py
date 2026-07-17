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
        "text": "כתבו שמות של מדינות באירופה",
        "answers": [
            ("צרפת", [], None),
            ("גרמניה", [], None),
            ("איטליה", [], None),
            ("ספרד", [], None),
            ("יוון", [], None),
            ("פורטוגל", [], None),
            ("הולנד", [], None),
            ("בלגיה", [], None),
            ("שוויץ", ["שווייץ"], None),
            ("אנגליה", [], "uk"),
            ("בריטניה", ["הממלכה המאוחדת"], "uk"),
            ("פולין", [], None),
            ("אוסטריה", [], None),
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

QUESTIONS.extend(ADDITIONAL_QUESTIONS)


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
                            selectinload(Question.answers).selectinload(
                                ApprovedAnswer.aliases
                            )
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

            answers_by_canonical = {
                answer.canonical: answer for answer in question.answers
            }
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
