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
from .question_bank_expansion_v6 import (
    CURATION_SOURCES as CURATION_SOURCES_V6,
)
from .question_bank_expansion_v6 import (
    EXPANSION_V6,
)
from .question_bank_expansion_v7 import (
    CURATION_SOURCES as CURATION_SOURCES_V7,
)
from .question_bank_expansion_v7 import (
    EXPANSION_V7,
)
from .question_bank_expansion_v8 import (
    CURATION_SOURCES as CURATION_SOURCES_V8,
)
from .question_bank_expansion_v8 import (
    EXPANSION_V8,
)
from .question_bank_expansion_v9 import (
    CURATION_SOURCES as CURATION_SOURCES_V9,
)
from .question_bank_expansion_v9 import (
    EXPANSION_V9,
)
from .question_bank_expansion_v10 import NEW_QUESTIONS_V10

DEACTIVATED_QUESTION_TEXTS = [
    "כתבו שמות של אותיות באלף-בית העברי",
    "כתבו שמות של בירות בעולם",
    "כתבו שמות של כלי מטבח",
    "כתבו שמות של יסודות כימיים",
]

# The V3 governance test audits the current QUESTIONS collection through the
# V3 registries. Register later closed-set questions there without copying any
# V4 answer data; their actual review policies and sources remain owned by V4.
for v4_question_text in QUESTION_POLICIES_V4:
    if v4_question_text in DEACTIVATED_QUESTION_TEXTS:
        continue
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

# V6 owns the source records for its ten new fun categories while the V3
# governance registry continues to cover every question in the live bank.
for v6_question_text, v6_sources in CURATION_SOURCES_V6.items():
    ANSWER_ALIAS_ADDITIONS_V3.setdefault(v6_question_text, {})
    QUESTION_EXPANSION_SOURCES_V3.setdefault(v6_question_text, v6_sources)

# V7 deepens existing open categories and refreshes their source records while
# preserving the V3 registry as the single all-question governance inventory.
for v7_question_text, v7_sources in CURATION_SOURCES_V7.items():
    ANSWER_ALIAS_ADDITIONS_V3.setdefault(v7_question_text, {})
    QUESTION_EXPANSION_SOURCES_V3.setdefault(v7_question_text, v7_sources)

# V8 adds the Israeli stand-up category and keeps the V3 governance registry
# aware of its independently curated source records.
for v8_question_text, v8_sources in CURATION_SOURCES_V8.items():
    ANSWER_ALIAS_ADDITIONS_V3.setdefault(v8_question_text, {})
    QUESTION_EXPANSION_SOURCES_V3.setdefault(v8_question_text, v8_sources)

# V9 adds eight pop-culture categories and keeps the V3 governance registry
# aware of their independently curated source records.
for v9_question_text, v9_sources in CURATION_SOURCES_V9.items():
    ANSWER_ALIAS_ADDITIONS_V3.setdefault(v9_question_text, {})
    QUESTION_EXPANSION_SOURCES_V3.setdefault(v9_question_text, v9_sources)

DEMO_PASSWORD = "demo1234"

DEMO_USERS = []

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
QUESTIONS.extend(NEW_QUESTIONS_V10)

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

    answers_by_canonical_v6 = {
        canonical: aliases for canonical, aliases, _group in question["answers"]
    }
    for canonical, aliases, group in EXPANSION_V6.get(question["text"], []):
        target = answers_by_canonical_v6.get(canonical)
        if target is None:
            copied_aliases = list(aliases)
            question["answers"].append((canonical, copied_aliases, group))
            answers_by_canonical_v6[canonical] = copied_aliases
            continue
        for alias in aliases:
            if alias != canonical and alias not in target:
                target.append(alias)

    answers_by_canonical_v7 = {
        canonical: aliases for canonical, aliases, _group in question["answers"]
    }
    for canonical, aliases, group in EXPANSION_V7.get(question["text"], []):
        target = answers_by_canonical_v7.get(canonical)
        if target is None:
            copied_aliases = list(aliases)
            question["answers"].append((canonical, copied_aliases, group))
            answers_by_canonical_v7[canonical] = copied_aliases
            continue
        for alias in aliases:
            if alias != canonical and alias not in target:
                target.append(alias)

    answers_by_canonical_v8 = {
        canonical: aliases for canonical, aliases, _group in question["answers"]
    }
    for canonical, aliases, group in EXPANSION_V8.get(question["text"], []):
        target = answers_by_canonical_v8.get(canonical)
        if target is None:
            copied_aliases = list(aliases)
            question["answers"].append((canonical, copied_aliases, group))
            answers_by_canonical_v8[canonical] = copied_aliases
            continue
        for alias in aliases:
            if alias != canonical and alias not in target:
                target.append(alias)

    answers_by_canonical_v9 = {
        canonical: aliases for canonical, aliases, _group in question["answers"]
    }
    for canonical, aliases, group in EXPANSION_V9.get(question["text"], []):
        target = answers_by_canonical_v9.get(canonical)
        if target is None:
            copied_aliases = list(aliases)
            question["answers"].append((canonical, copied_aliases, group))
            answers_by_canonical_v9[canonical] = copied_aliases
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


TARGETED_QUESTION_ENRICHMENTS: dict[str, list[tuple[str, list[str], str | None]]] = {
    "כתבו שמות של איברי גוף": [
        ("פין", ["בולבול", "זין", "זרג", "שמוליק"], None),
        ("אשך", ["ביצה", "ביצים"], None),
        ("פי הטבעת", ["חור תחת", "חור של התחת"], None),
        ("נרתיק", ["ואגינה"], None),
        ("גבה", ["גבות"], None),
        ("ריס", ["ריסים"], None),
        ("עפעף", ["עפעפיים"], None),
        ("שפה", ["שפתיים"], None),
        ("נחיר", ["נחיריים"], None),
        ("לסת", ["לסתות"], None),
        ("חניכיים", ["חניכיים בפה"], None),
        ("שד", ["שדיים", "ציצי", "ציצים", "ציציות"], None),
        ("פטמה", ["פטמות"], None),
        ("טבור", ["פופיק"], None),
        ("בית שחי", ["בית השחי"], None),
        ("זרוע", ["זרועות"], None),
        ("אמה", ["אמות"], None),
        ("מפשעה", ["מפשעות"], None),
        ("ישבן", ["תחת", "טוסיק", "עכוז"], None),
        ("פות", ["כוס", "וולווה"], None),
        ("דגדגן", ["קליטוריס"], None),
        ("עורלה", [], None),
        ("כיס האשכים", ["שק האשכים"], None),
        ("שופכה", ["אורתרה"], None),
        ("שופכן", ["אורטר"], None),
        ("צינור הזרע", ["צינור זרע"], None),
        ("צוואר הרחם", ["צוואר רחם", "סרוויקס"], None),
        ("חצוצרה", ["חצוצרות הרחם"], None),
        ("שליה", ["פלצנטה"], None),
        ("בלוטת רוק", ["בלוטות הרוק"], None),
        ("תריסריון", ["דואודנום"], None),
        ("אבי העורקים", ["אאורטה"], None),
        ("עצם החזה", ["סטרנום"], None),
        ("עצם הזנב", ["עוקץ", "קוקסיקס"], None),
        ("שוק", ["שוקיים"], None),
        ("שוקה", ["טיביה"], None),
        ("גיד אכילס", ["אכילס"], None),
    ],
    "כתבו מילים בסלנג ישראלי": [
        ("על הכיפאק", ["עלא כיפאק"], None),
        ("חלאס", ["חלס"], None),
        ("יאמאס", [], None),
        ("אחושילינג", ["אחושרמוטה", "אחושקשוקה"], None),
        ("בואנה", ["בונה"], None),
        ("אשכרה", [], None),
        ("יעני", [], None),
        ("עאלק", ["אלק"], None),
        ("חארטה", ["חרטא"], None),
        ("חרטא ברטא", [], None),
        ("קומבינה", ["קומבינות"], None),
        ("מאכער", ["מאכר"], None),
        ("בלגן", ["בלאגן"], None),
        ("פשלה", ["פאשלה"], None),
        ("דאחקה", ["דחקה"], None),
        ("צחוקים", [], None),
        ("חפלה", ["חאפלה"], None),
        ("שכונה", ["איזו שכונה"], None),
        ("מסטול", ["מסטולה"], None),
        ("סאחי", ["סחי", "סאחית"], None),
        ("ערס", ["ערסית"], None),
        ("פרחה", [], None),
        ("צ'חצ'ח", ["צחצח"], None),
        ("ג'חש", ["גחש"], None),
        ("חנון", ["חנונית"], None),
        ("קוטר", ["קוטרית"], None),
        ("נודניק", ["נודניקית"], None),
        ("פראייר", ["פרייר", "פראיירית"], None),
        ("לוזר", ["לוזרית"], None),
        ("פסיכי", ["פסיכית"], None),
        ("מפגר", ["מפגרת"], None),
        ("קרוע", ["קרועה"], None),
        ("דלוק", ["דלוקה"], None),
        ("חרמן", ["חרמנית"], None),
        ("מדליק", ["מדליקה"], None),
        ("חתיך", ["חתיכה"], None),
        ("כוסית", ["כוסון"], None),
        ("שרמוטה", ["שרמוט"], None),
        ("זונה", [], None),
        ("כלבה", [], None),
        ("מניאק", ["מנייק"], None),
        ("בן זונה", ["בנזונה"], None),
        ("בת זונה", ["בתזונה"], None),
        ("חרא", [], None),
        ("זבל", [], None),
        ("סעמק", ["סאמק"], None),
        ("כוסאומו", ["כוס אמק", "כוס אמו"], None),
        ("פאק", ["פאקינג"], None),
        ("שיט", [], None),
        ("אפס", [], None),
        ("דביל", ["דבילית"], None),
        ("אידיוט", ["אידיוטית"], None),
        ("סתום", ["סתומה"], None),
        ("ממזר", ["ממזרה"], None),
        ("מלך", ["מלכה"], None),
        ("נסיך", ["נסיכה"], None),
        ("חיים שלי", [], None),
        ("ברו", ["אח יקר"], None),
        ("וייב", ["וייבים"], None),
        ("קראש", ["הקראש"], None),
        ("איזה סרט", ["סרט רע"], None),
        ("ראש גדול", [], None),
        ("ראש קטן", [], None),
        ("אכל אותה", ["אכלה אותה"], None),
        ("הלך עליו", ["הלך עליה"], None),
        ("אין מצב", [], None),
        ("מה נסגר", [], None),
        ("סבבה אגוזים", [], None),
        ("כיף", ["כיפי"], None),
        ("ביסים", [], None),
        ("חמוד", ["חמודה"], None),
        ("נאסה", [], None),
        ("בוסתן", [], None),
        ("חופש", [], None),
        ("חמאס", [], None),
        ("קזח", [], None),
        ("מוצלח", ["מוצלחת"], None),
        ("אינטלקטואל", ["אינטלקטואלית"], None),
        ("ברנש", [], None),
        ("בחור", ["בחורה"], None),
    ],
    "כתבו שמות של סדרות טלוויזיה": [
        ("חברים", ["פרנדס"], None),
        ("משחקי הכס", ["גיים אוף ת'רונס", "גיים אוף דה ת'רונס"], None),
        ("שובר שורות", ["ברייקינג בד"], None),
        ("הסופרנוס", ["סופרנוס"], None),
        ("אבודים", ["Lost", "לוסט"], None),
        ("נמלטים", ["Prison Break", "פריזן ברייק"], None),
        ("אימה אמריקאית", ["American Horror Story", "אמריקן הורור סטורי"], None),
        ("סיפורה של שפחה", ["The Handmaid's Tale", "הנדמיידס טייל"], None),
        ("אוזרק", ["Ozark", "אוזארק"], None),
        ("מיינדהאנטר", ["Mindhunter", "מינדהאנטר"], None),
        ("האנטומיה של גריי", ["Grey's Anatomy", "גרייס אנטומי"], None),
        ("סקנדל", ["Scandal"], None),
        ("הכתר", ["The Crown"], None),
        ("מראה שחורה", ["Black Mirror"], None),
        ("נרקוס", ["Narcos"], None),
        ("המתים המהלכים", ["The Walking Dead"], None),
        ("ויקינגים", ["Vikings"], None),
        ("צ'רנוביל", ["Chernobyl"], None),
        ("יורשים", ["Succession"], None),
        ("הלוטוס הלבן", ["The White Lotus"], None),
        ("הדוב", ["The Bear"], None),
        ("אופוריה", ["Euphoria"], None),
        ("ברידג'רטון", ["Bridgerton"], None),
        ("בלש אמיתי", ["True Detective"], None),
        ("הסמויה", ["The Wire"], None),
        ("הבנים", ["The Boys"], None),
        ("המנדלוריאן", ["The Mandalorian", "מנדלוריאן"], None),
        ("האחרונים מבינינו", ["The Last of Us", "לאסט אוף אס"], None),
        ("כנופיית ברמינגהם", ["Peaky Blinders", "פיקי בליינדרס"], None),
        ("חליפות", ["Suits", "סוטס"], None),
        ("הומלנד", ["Homeland"], None),
        ("24", ["Twenty Four"], None),
        ("האוס", ["House", "House MD"], None),
        ("המפץ הגדול", ["The Big Bang Theory"], None),
        ("איך פגשתי את אמא", ["How I Met Your Mother"], None),
        ("משפחה מודרנית", ["Modern Family"], None),
        ("סאות' פארק", ["South Park"], None),
        ("איש משפחה", ["Family Guy"], None),
        ("ארקיין", ["Arcane"], None),
        ("וונסדיי", ["Wednesday"], None),
        ("את", ["You"], None),
        ("פארגו", ["Fargo"], None),
        ("בייטס מוטל", ["Bates Motel", "ביטס מוטל"], None),
        ("פאודה", ["פאוד'ה"], None),
        ("עבודה ערבית", ["העבודה הערבית", "Arab Labor"], None),
        ("שתי אמהות", [], None),
        ("משפחה", [], None),
        ("יוניט 8200", ["Unit 8200", "יחידה 8200"], None),
        ("הבורים", [], None),
        ("היקרה", [], None),
        ("מנאייכ", ["מנאיק", "Manayek"], None),
        ("שעת נעילה", ["Valley of Tears"], None),
        ("עלומים", ["Unknowns"], None),
        ("שבאבניקים", ["Shababnikim"], None),
        ("כפולים", ["False Flag"], None),
        ("בני ערובה", ["Hostages"], None),
        ("עספור", ["Asfur"], None),
        ("הבורר", ["The Arbitrator"], None),
        ("פלפלים צהובים", ["Yellow Peppers"], None),
        ("בטיפול", ["In Treatment"], None),
        ("כבודו", ["Your Honor"], None),
        ("סרוגים", ["Srugim"], None),
        ("שנות השמונים", ["שנות ה-80", "The Eighties"], None),
        ("היהודים באים", ["The Jews Are Coming"], None),
    ],
    "כתבו שמות של שחקני כדורגל מפורסמים": [
        ("ליאונל מסי", ["מסי", "ליאו מסי"], None),
        ("כריסטיאנו רונאלדו", ["כריסטיאנו"], None),
        ("קיליאן אמבפה", ["מבאפה", "אמבפה", "קיליאן מבאפה"], None),
        ("ארלינג הולאנד", ["הלאנד", "ארלינג הלאנד"], None),
        ("ניימאר", ["נימאר"], None),
        ("לוקה מודריץ'", ["מודריץ", "מודריץ'"], None),
        ("כרים בנזמה", ["בנזמה"], None),
        ("דייוויד בקהאם", ["בקהם", "בקהאם"], None),
        ("תיירי הנרי", ["אנרי"], None),
        ("ויין רוני", ["Wayne Rooney", "רוני"], None),
        ("קאקה", ["Kaká", "Kaka"], None),
        ("אלשנדרה פאטו", ["Alexandre Pato", "פאטו"], None),
        ("ריבאלדו", ["Rivaldo", "ריבלדו"], None),
        ("רוברטו קרלוס", ["Roberto Carlos"], None),
        ("קאפו", ["Cafu"], None),
        ("רומאריו", ["Romário", "Romario"], None),
        ("זיקו", ["Zico"], None),
        ("סוקרטס", ["Sócrates", "Socrates"], None),
        ("גארינצ'ה", ["Garrincha", "גרינצ'ה"], None),
        ("אאוזביו", ["Eusébio", "Eusebio"], None),
        ("מישל פלאטיני", ["Michel Platini", "פלאטיני"], None),
        ("אלפרדו די סטפנו", ["Alfredo Di Stéfano", "די סטפנו"], None),
        ("ג'ורג' בסט", ["George Best"], None),
        ("בובי צ'רלטון", ["Bobby Charlton"], None),
        ("לב יאשין", ["Lev Yashin", "יאשין"], None),
        ("רוברטו באג'ו", ["Roberto Baggio", "באג'ו"], None),
        ("פרנקו בארזי", ["Franco Baresi", "בארזי"], None),
        ("אלסנדרו דל פיירו", ["Alessandro Del Piero", "דל פיירו"], None),
        ("פרנצ'סקו טוטי", ["Francesco Totti", "טוטי"], None),
        ("אנדראה פירלו", ["Andrea Pirlo", "פירלו"], None),
        ("פאביו קנבארו", ["Fabio Cannavaro", "קנבארו"], None),
        ("איקר קסיאס", ["Iker Casillas", "קסיאס"], None),
        ("סרחיו ראמוס", ["Sergio Ramos", "ראמוס"], None),
        ("קרלס פויול", ["Carles Puyol", "פויול"], None),
        ("סרחיו בוסקטס", ["Sergio Busquets", "בוסקטס"], None),
        ("דויד וייה", ["David Villa", "וייה"], None),
        ("פרננדו טורס", ["Fernando Torres", "טורס"], None),
        ("לואיס פיגו", ["Luís Figo", "פיגו"], None),
        ("מנואל נוייר", ["Manuel Neuer", "נוייר"], None),
        ("פיליפ לאם", ["Philipp Lahm", "לאם"], None),
        ("מירוסלב קלוזה", ["Miroslav Klose", "קלוזה"], None),
        ("תומאס מולר", ["Thomas Müller", "מולר"], None),
        ("אריין רובן", ["Arjen Robben", "רובן"], None),
        ("רובין ואן פרסי", ["Robin van Persie", "ואן פרסי"], None),
        ("דניס ברגקאמפ", ["Dennis Bergkamp", "ברגקאמפ"], None),
        ("אלן שירר", ["Alan Shearer", "שירר"], None),
        ("גארי ליניקר", ["Gary Lineker", "לינקר"], None),
        ("סטיבן ג'רארד", ["Steven Gerrard", "ג'רארד"], None),
        ("פרנק למפארד", ["Frank Lampard", "למפארד"], None),
        ("אריק קאנטונה", ["Eric Cantona", "קאנטונה"], None),
        ("דידייה דרוגבה", ["Didier Drogba", "דרוגבה"], None),
        ("סמואל אטו", ["Samuel Eto'o", "אטו"], None),
        ("לואיס סוארס", ["Luis Suárez", "סוארס"], None),
        ("זלאטן איברהימוביץ'", ["Zlatan Ibrahimović", "זלאטן"], None),
        ("סרחיו אגוארו", ["Sergio Agüero", "אגוארו", "קון אגוארו"], None),
        ("קווין דה בריינה", ["Kevin De Bruyne", "דה בריינה"], None),
        ("וירג'יל ואן דייק", ["Virgil van Dijk", "ואן דייק"], None),
        ("הארי קיין", ["Harry Kane", "קיין"], None),
        ("ג'וד בלינגהאם", ["Jude Bellingham", "בלינגהאם"], None),
        ("ויניסיוס ג'וניור", ["Vinícius Júnior", "ויניסיוס"], None),
        ("לאמין ימאל", ["Lamine Yamal", "ימאל"], None),
        ("אלי אוחנה", ["Eli Ohana"], None),
        ("מרדכי שפיגלר", ["Mordechai Spiegler", "מוטל'ה שפיגלר"], None),
        ("חיים רביבו", ["Haim Revivo", "רביבו"], None),
        ("אייל ברקוביץ'", ["Eyal Berkovic", "ברקוביץ"], None),
        ("אלון מזרחי", ["Alon Mizrahi", "האווירון"], None),
        ("ביברס נאתכו", ["Bibras Natcho", "נאתכו"], None),
        ("מנור סולומון", ["Manor Solomon"], None),
        ("אוסקר גלוך", ["Oscar Gloukh", "גלוך"], None),
        ("דניאל פרץ", ["Daniel Peretz"], None),
        ("מיגל עמוס", [], None),
        ("ג'ובי", ["גובי"], None),
        ("מוסא", [], None),
        ("מנחם", [], None),
        ("עידו שורש", [], None),
        ("גל אלבז", [], None),
        ("אבנר כהן", [], None),
    ],
    "כתבו שמות של קבוצות כדורגל": [
        ("ביתר ירושלים", ['בית"ר ירושלים', "בית״ר ירושלים"], None),
        ("הפועל חיפה", ["Hapoel Haifa FC"], None),
        ("מכבי נתניה", ["Maccabi Netanya FC"], None),
        ("עירוני קריית שמונה", ["קריית שמונה", "Ironi Kiryat Shmona"], None),
        ("הפועל כפר סבא", ["Hapoel Kfar Saba"], None),
        ("מועדון ספורט אשדוד", ["מ.ס. אשדוד", "אשדוד", "FC Ashdod"], None),
        ("בני סכנין", ["Bnei Sakhnin"], None),
        ("הפועל עפולה", ["Hapoel Afula"], None),
        ("הפועל ירושלים", ["Hapoel Jerusalem FC"], None),
        ("מכבי פתח תקווה", ["Maccabi Petah Tikva"], None),
        ("הפועל פתח תקווה", ["Hapoel Petah Tikva"], None),
        ("בני יהודה", ["Bnei Yehuda"], None),
        ("הפועל חדרה", ["Hapoel Hadera"], None),
        ("הפועל רעננה", ["Hapoel Ra'anana"], None),
        ("עירוני טבריה", ["Ironi Tiberias"], None),
        ("רומא", ["AS Roma"], None),
        ("לאציו", ["SS Lazio"], None),
        ("פיורנטינה", ["Fiorentina", "ACF Fiorentina"], None),
        ("אטאלנטה", ["Atalanta BC"], None),
        ("סביליה", ["Sevilla FC"], None),
        ("ולנסיה", ["Valencia CF"], None),
        ("ויאריאל", ["Villarreal CF"], None),
        ("אתלטיק בילבאו", ["Athletic Bilbao", "Athletic Club"], None),
        ("ריאל סוסיאדד", ["Real Sociedad"], None),
        ("באייר לברקוזן", ["Bayer Leverkusen"], None),
        ("ר.ב. לייפציג", ["RB Leipzig", "לייפציג"], None),
        ("שאלקה 04", ["Schalke 04", "שאלקה"], None),
        ("פורטו", ["FC Porto"], None),
        ("ספורטינג ליסבון", ["Sporting CP", "ספורטינג"], None),
        ("פיינורד", ["Feyenoord"], None),
        ("פ.ס.וו איינדהובן", ["PSV Eindhoven", "PSV"], None),
        ("סלטיק", ["Celtic FC"], None),
        ("ריינג'רס", ["Rangers FC"], None),
        ("אולימפיק מרסיי", ["Olympique de Marseille", "מרסיי"], None),
        ("אולימפיק ליון", ["Olympique Lyonnais", "ליון"], None),
        ("מונקו", ["AS Monaco"], None),
        ("גלאטסראיי", ["Galatasaray"], None),
        ("פנרבחצ'ה", ["Fenerbahçe", "Fenerbahce"], None),
        ("בוקה ג'וניורס", ["Boca Juniors", "בוקה"], None),
        ("ריבר פלייט", ["River Plate", "ריבר"], None),
        ("פלמנגו", ["Flamengo"], None),
        ("סנטוס", ["Santos FC"], None),
        ("קורינתיאנס", ["Corinthians"], None),
        ("פלמיירס", ["Palmeiras"], None),
        ("סאו פאולו", ["São Paulo FC", "Sao Paulo"], None),
        ("אינטר מיאמי", ["Inter Miami CF", "Inter Miami"], None),
        ("אל הילאל", ["Al Hilal"], None),
        ("אל נאסר", ["Al Nassr"], None),
    ],
    "כתבו שמות של רשתות מזון מהיר": [
        ("דומינוס", ["דומינוס פיצה"], None),
        ("פופאי'ס", ["פופייז"], None),
        ("בורגראנץ'", ["בורגר ראנץ'", "בורגר ראנץ"], None),
        ("פייב גאיז", ["פייב גייס"], None),
        ("בי בי בי", ["BBB", "בי.בי.בי"], None),
        ("פפר'ס", ["Peppers", "פפרס"], None),
        ("קינג ג'ורג'", ["King George", "קינג ג'ורג"], None),
        ("שווארמה ברס", ["שוורמה ברס", "שווארמה-ברס"], None),
        ("הומוסיה", ["Hummusiya"], None),
        ("גוטה", ["Gota"], None),
        ("ופל", ["Waffle"], None),
        ("קרואסון פה", ["Croissant פה"], None),
        ("מוזס", ["Moses"], None),
        ("אגאדיר", ["Agadir"], None),
        ("בורגר סאלון", ["Burger Saloon"], None),
        ("ויטרינה", ["Vitrina"], None),
        ("סודוך", ["Suduch"], None),
        ("ניו דלי", ["New Deli"], None),
        ("פיצה עגבניה", ["Pizza Agvania", "פיצה עגבנייה"], None),
        ("פיצה שמש", ["Pizza Shemesh"], None),
        ("חומוס אליהו", ["Hummus Eliyahu"], None),
        ("שווארמה שמש", ["Shawarma Shemesh"], None),
        ("בנדורה", ["Bandora"], None),
        ("ג'פניקה", ["Japanika", "גפניקה"], None),
        ("ריבר", ["River"], None),
        ("ג'ירף", ["Giraffe", "גירף"], None),
        ("ארומה", ["Aroma Espresso Bar", "Aroma"], None),
        ("וינגסטופ", ["Wingstop"], None),
        ("פנדה אקספרס", ["Panda Express"], None),
        ("ג'וליבי", ["Jollibee", "גוליבי"], None),
        ("ננדוס", ["Nando's", "Nandos"], None),
        ("ווטאבורגר", ["Whataburger"], None),
        ("וייט קאסל", ["White Castle"], None),
        ("קולברס", ["Culver's", "Culvers"], None),
        ("צ'רץ'ס צ'יקן", ["Church's Chicken", "Church's Texas Chicken"], None),
        ("ג'רזי מייקס", ["Jersey Mike's", "Jersey Mikes"], None),
        ("סינבון", ["Cinnabon"], None),
        ("קריספי קרים", ["Krispy Kreme"], None),
        ("טים הורטונס", ["Tim Hortons"], None),
        ("פרט א מנז'ה", ["Pret A Manger", "Pret"], None),
        ("סבארו", ["Sbarro"], None),
        ("באסקין רובינס", ["Baskin-Robbins", "Baskin Robbins"], None),
    ],
    "כתבו שמות של אפליקציות ורשתות חברתיות": [
        ("טאמבלר", ["Tumblr", "טמבלר"], None),
        ("וייבר", ["Viber"], None),
        ("ביריל", ["BeReal", "בי ריל"], None),
        ("מסטודון", ["Mastodon"], None),
        ("בלוסקיי", ["Bluesky", "BlueSky"], None),
        ("קלאבהאוס", ["Clubhouse", "קלאב האוס"], None),
        ("וויצ'אט", ["WeChat", "Weixin"], None),
        ("ליין", ["LINE"], None),
        ("קאקאו טוק", ["KakaoTalk", "Kakao Talk"], None),
        ("מסנג'ר", ["Messenger", "Facebook Messenger"], None),
        ("סקייפ", ["Skype"], None),
        ("מיקרוסופט טימס", ["Microsoft Teams", "Teams", "טימס"], None),
        ("ג'ימייל", ["Gmail", "גימייל"], None),
        ("גוגל דרייב", ["Google Drive", "דרייב"], None),
        ("דרופבוקס", ["Dropbox"], None),
        ("וואן דרייב", ["OneDrive", "Microsoft OneDrive"], None),
        ("נושן", ["Notion"], None),
        ("טרלו", ["Trello"], None),
        ("סלאק", ["Slack"], None),
        ("נטפליקס", ["Netflix"], None),
        ("דיסני פלוס", ["Disney+", "Disney Plus"], None),
        ("הולו", ["Hulu"], None),
        ("אמזון פריים וידאו", ["Amazon Prime Video", "Prime Video"], None),
        ("אפל מיוזיק", ["Apple Music"], None),
        ("סאונדקלאוד", ["SoundCloud", "Sound Cloud"], None),
        ("שזאם", ["Shazam"], None),
        ("איביי", ["eBay"], None),
        ("אמזון", ["Amazon"], None),
        ("אלי אקספרס", ["AliExpress", "Ali Express"], None),
        ("שיין", ["SHEIN", "Shein"], None),
        ("טמו", ["Temu"], None),
        ("אטסי", ["Etsy"], None),
        ("גריינדר", ["Grindr", "גרינדר"], None),
        ("באמבל", ["Bumble"], None),
        ("הינג'", ["Hinge", "הינג"], None),
        ("אוקיי קיופיד", ["OkCupid", "OK Cupid"], None),
        ("ביט", ["bit", "ביטו"], None),
        ("פייבוקס", ["PayBox", "פיי בוקס"], None),
        ("יד2", ["Yad2", "יד שתיים"], None),
        ("מדלן", ["Madlan"], None),
        ("וולט", ["Wolt"], None),
        ("תן ביס", ["10bis", "Ten Bis"], None),
        ("אובר", ["Uber"], None),
        ("ליפט", ["Lyft"], None),
        ("איירבנב", ["Airbnb", "אייר בי אנד בי"], None),
        ("משחק", ["Game app"], None),
        ("אוטו", ["Auto app"], None),
    ],
    "כתבו שמות של מותגי אופנה וספורט": [
        ("ניו באלאנס", ["ניו בלאנס"], None),
        ("אייץ' אנד אם", ["H and M"], None),
        ("מיזונו", ["Mizuno"], None),
        ("טימברלנד", ["Timberland"], None),
        ("יו ג'י ג'י", ["UGG", "אג"], None),
        ("קרוקס", ["Crocs"], None),
        ("ורסאצ'ה", ["Versace", "ורסצ'ה"], None),
        ("קלווין קליין", ["Calvin Klein", "CK"], None),
        ("לקוסט", ["Lacoste"], None),
        ("הוגו בוס", ["Hugo Boss", "Boss"], None),
        ("מנגו", ["Mango"], None),
        ("יוניקלו", ["Uniqlo"], None),
        ("ברשקה", ["Bershka"], None),
        ("פול אנד בר", ["Pull&Bear", "Pull and Bear"], None),
        ("סטרדיווריוס", ["Stradivarius"], None),
        ("מאסימו דוטי", ["Massimo Dutti"], None),
        ("גאפ", ["GAP", "Gap"], None),
        ("בננה ריפבליק", ["Banana Republic"], None),
        ("אולד נייבי", ["Old Navy"], None),
        ("אברקרומבי אנד פיץ'", ["Abercrombie & Fitch", "Abercrombie"], None),
        ("אמריקן איגל", ["American Eagle"], None),
        ("צ'מפיון", ["Champion", "צמפיון"], None),
        ("סקצ'רס", ["Skechers", "סקצרס"], None),
        ("סלומון", ["Salomon"], None),
        ("הוקה", ["Hoka", "Hoka One One"], None),
        ("און ראנינג", ["On Running", "On"], None),
        ("ג'ורדן", ["Jordan", "Air Jordan"], None),
        ("אמברו", ["Umbro"], None),
        ("קאפה", ["Kappa"], None),
        ("פטגוניה", ["Patagonia"], None),
        ("ארקטריקס", ["Arc'teryx", "Arcteryx"], None),
        ("מונקלר", ["Moncler"], None),
        ("בלנסיאגה", ["Balenciaga"], None),
        ("ברברי", ["Burberry"], None),
        ("ז'יבנשי", ["Givenchy", "ג'יבנשי"], None),
        ("סן לורן", ["Saint Laurent", "YSL", "איב סן לורן"], None),
        ("ולנטינו", ["Valentino"], None),
        ("פנדי", ["Fendi"], None),
        ("דולצ'ה וגבאנה", ["Dolce & Gabbana", "D&G"], None),
        ("בוטגה ונטה", ["Bottega Veneta"], None),
        ("מייקל קורס", ["Michael Kors"], None),
        ("ויקטוריה'ס סיקרט", ["Victoria's Secret", "ויקטוריה סיקרט"], None),
        ("רנואר", ["Renuar"], None),
        ("קסטרו", ["Castro"], None),
        ("פוקס", ["Fox", "FOX"], None),
        ("גולף", ["Golf", "Golf & Co", "גולף ושות'"], None),
        ("דלתא", ["Delta", "Delta Galil"], None),
        ("הודיס", ["Hoodies"], None),
        ("טוונטי פור סבן", ["Twentyfourseven", "Twenty Four Seven"], None),
        ("תמנון", ["Tamnoon"], None),
        ("HOG", ["הוג"], None),
        ("קפיטל", ["Capital"], None),
        ("פירמה", ["Firma"], None),
        ("בוש-פיילות", ["בוש פיילות"], None),
    ],
    "כתבו שמות של סרטי אקשן מפורסמים": [
        ("מת לחיות", ["דיי הארד", "דַי הארד"], None),
        ("שליחות קטלנית 2", ["טרמינטור 2"], None),
        ("מקס הזועם: כביש הזעם", ["מד מקס פיורי רוד"], None),
        ("משימה בלתי אפשרית", ["מיז'ן אימפוסיבל", "מיזיון אימפוסיבל"], None),
        ("אהבה בשחקים", ["טופ גאן"], None),
        ("שליחות קטלנית", ["The Terminator", "Terminator", "טרמינטור"], None),
        ("מקס הזועם", ["Mad Max", "מד מקס"], None),
        ("מהיר ועצבני", ["The Fast and the Furious", "Fast & Furious", "פאסט אנד פיוריאוס"], None),
        ("רובוטריקים", ["Transformers", "טרנספורמרס"], None),
        ("הנוקמים", ["The Avengers", "Avengers", "אבנג'רס"], None),
        ("איש הפלדה", ["Man of Steel", "מן אוף סטיל"], None),
        ("באטמן", ["Batman"], None),
        ("ספיידרמן", ["Spider-Man", "Spider Man"], None),
        ("הפנתר השחור", ["Black Panther", "בלאק פאנתר"], None),
        ("שומרי הגלקסיה", ["Guardians of the Galaxy", "גארדיאנס אוף דה גלקסי"], None),
        ("דוקטור סטריינג'", ["Doctor Strange", "דר סטריינג'"], None),
        ("תור", ["Thor"], None),
        ("איירון מן", ["Iron Man"], None),
        ("צלף אמריקאי", ["American Sniper", "אמריקן סנייפר"], None),
        ("דנקרק", ["Dunkirk", "דאנקירק"], None),
        ("מקסימום ריסק", ["Maximum Risk"], None),
        ("ראש על צוואר", [], None),
        ("אינדיאנה ג'ונס והמקדש הארור", ["Indiana Jones and the Temple of Doom"], None),
        ("גולדפינגר", ["Goldfinger"], None),
        ("דוקטור נו", ["Dr. No", "Doctor No"], None),
        ("מרוסיה באהבה", ["From Russia with Love"], None),
        ("כדור הרעם", ["Thunderball"], None),
        ("בשירות הוד מלכותה", ["On Her Majesty's Secret Service"], None),
        ("המרגלת שאהבה אותי", ["The Spy Who Loved Me"], None),
        ("גולדן איי", ["GoldenEye", "Golden Eye"], None),
        ("סקייפול", ["Skyfall"], None),
        ("לא זמן למות", ["No Time to Die"], None),
        ("פארק היורה", ["Jurassic Park", "ג'ורסיק פארק"], None),
        ("טיטאניק", ["Titanic"], None),
        ("בלייד ראנר", ["Blade Runner"], None),
        ("אויב המדינה", ["Enemy of the State"], None),
        ("קון אייר", ["Con Air"], None),
        ("אייר פורס 1", ["Air Force One"], None),
        ("הנמלט", ["The Fugitive"], None),
        ("המומיה", ["The Mummy"], None),
        ("שודדי הקאריביים", ["Pirates of the Caribbean"], None),
        ("בלאק הוק דאון", ["Black Hawk Down"], None),
        ("300", ["300 Spartans"], None),
        ("קינגסמן", ["Kingsman", "Kingsman: The Secret Service"], None),
        ("אטומיק בלונד", ["Atomic Blonde"], None),
        ("אקוולייזר", ["The Equalizer", "Equalizer"], None),
        ("אקסטרקשן", ["Extraction"], None),
        ("בייבי דרייבר", ["Baby Driver"], None),
        ("שוטר מבוורלי הילס", ["Beverly Hills Cop"], None),
        ("בחורים רעים", ["Bad Boys"], None),
        ("הפשיטה", ["The Raid", "The Raid: Redemption"], None),
        ("הרכבת לבוסאן", ["Train to Busan"], None),
        ("עולם היורה", ["Jurassic World"], None),
    ],
    "כתבו שמות של חברות טכנולוגיה": [
        ("אנבידיה", ["Nvidia"], None),
        ("איי אמ די", ["Advanced Micro Devices Inc"], None),
        ("אס איי פי", ["SAP SE"], None),
        ("וויקס", ["WIX"], None),
        ("אל ג'י", ["LG", "LG Electronics"], None),
        ("נטפליקס", ["Netflix"], None),
        ("טסלה", ["Tesla", "Tesla Inc."], None),
        ("זום", ["Zoom", "Zoom Video Communications"], None),
        ("סלאק", ["Slack", "Slack Technologies"], None),
        ("שופיפיי", ["Shopify"], None),
        ("איירבנב", ["Airbnb"], None),
        ("אובר", ["Uber", "Uber Technologies"], None),
        ("ליפט", ["Lyft"], None),
        ("דורדאש", ["DoorDash", "Door Dash"], None),
        ("ספייס אקס", ["SpaceX", "Space X"], None),
        ("פלנטיר", ["Palantir", "Palantir Technologies", "פאלאנטיר"], None),
        ("מלאנוקס", ["Mellanox", "Mellanox Technologies"], None),
        ("פרסונטיקס", ["Personetics", "פרסוניקס"], None),
        ("סייברארק", ["CyberArk", "Cyber Ark"], None),
        ("אמדוקס", ["Amdocs"], None),
        ("אלביט מערכות", ["Elbit Systems", "אלביט"], None),
        ("רפאל", ["Rafael Advanced Defense Systems", "רפאל מערכות לחימה"], None),
        ("תדיראן", ["Tadiran"], None),
        ("אלעד מערכות", ["Elad Systems", "אלעד"], None),
        ("קוואלקום", ["Qualcomm"], None),
        ("ברודקום", ["Broadcom"], None),
        ("טי אס אם סי", ["TSMC", "Taiwan Semiconductor Manufacturing Company"], None),
        ("לנובו", ["Lenovo"], None),
        ("וואווי", ["Huawei", "הוואווי"], None),
        ("שיאומי", ["Xiaomi"], None),
        ("נינטנדו", ["Nintendo"], None),
        ("בייטדאנס", ["ByteDance", "Byte Dance"], None),
        ("טנסנט", ["Tencent"], None),
        ("עליבאבא", ["Alibaba", "Alibaba Group"], None),
        ("פייפאל", ["PayPal", "Pay Pal"], None),
        ("סטרייפ", ["Stripe"], None),
        ("ספוטיפיי", ["Spotify"], None),
        ("אופן איי איי", ["OpenAI", "Open AI"], None),
        ("אנתרופיק", ["Anthropic"], None),
        ("קלאודפלייר", ["Cloudflare", "CloudFlare"], None),
        ("אטלסיאן", ["Atlassian"], None),
        ("סרוויס נאו", ["ServiceNow", "Service Now"], None),
        ("סנופלייק", ["Snowflake"], None),
        ("דאטאדוג", ["Datadog", "DataDog"], None),
        ("מונגו די בי", ["MongoDB", "Mongo DB"], None),
        ("גיטהאב", ["GitHub", "Git Hub"], None),
        ("גיטלאב", ["GitLab", "Git Lab"], None),
        ("רד האט", ["Red Hat"], None),
        ("וי אם וור", ["VMware", "VM Ware"], None),
        ("דרופבוקס", ["Dropbox"], None),
        ("טוויליו", ["Twilio"], None),
        ("אוק्टा", ["Okta"], None),
        ("פאלו אלטו נטוורקס", ["Palo Alto Networks"], None),
        ("פורטינט", ["Fortinet"], None),
        ("סנטינל וואן", ["SentinelOne", "Sentinel One"], None),
    ],
}

targeted_questions = {
    question["text"]: question
    for question in QUESTIONS
    if question["text"] in TARGETED_QUESTION_ENRICHMENTS
}
if targeted_questions.keys() != TARGETED_QUESTION_ENRICHMENTS.keys():
    missing = TARGETED_QUESTION_ENRICHMENTS.keys() - targeted_questions.keys()
    raise ValueError(f"Targeted enrichment questions are missing: {sorted(missing)!r}")

for question_text, additions in TARGETED_QUESTION_ENRICHMENTS.items():
    answers_by_canonical = {
        canonical: aliases
        for canonical, aliases, _group in targeted_questions[question_text]["answers"]
    }
    for canonical, aliases, group in additions:
        target = answers_by_canonical.get(canonical)
        if target is None:
            copied_aliases = list(aliases)
            targeted_questions[question_text]["answers"].append((canonical, copied_aliases, group))
            answers_by_canonical[canonical] = copied_aliases
            continue
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
        for question_text in DEACTIVATED_QUESTION_TEXTS:
            question = existing_questions.get(question_text)
            if question is not None:
                question.is_active = False

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
