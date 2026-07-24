"""Curated Israeli survey questions and stateless answer matching."""

from __future__ import annotations

from functools import lru_cache
from typing import Any, Callable

from .config import settings
from .game.validator import AnswerStatus, RoundValidator, build_question_index

SURVEY_QUESTIONS: list[dict[str, Any]] = [
    {
        "id": "q1",
        "text": "מה אנשים עושים כשהטלפון על 1%?",
        "answers": [
            {
                "canonical": "מחפשים מטען או שקע",
                "aliases": [
                    "מחפשים מטען",
                    "מחפש מטען",
                    "מחפשים שקע",
                    "רצים למטען",
                    "מבקשים מטען",
                ],
                "points": 32,
            },
            {
                "canonical": "מדליקים מצב חיסכון",
                "aliases": [
                    "מפעילים מצב חיסכון",
                    "מצב חיסכון",
                    "חיסכון בסוללה",
                    "battery saver",
                ],
                "points": 22,
            },
            {
                "canonical": "מורידים את בהירות המסך",
                "aliases": [
                    "מורידים בהירות",
                    "מנמיכים בהירות",
                    "מחשיכים את המסך",
                    "מוריד בהירות",
                ],
                "points": 15,
            },
            {
                "canonical": "סוגרים אפליקציות",
                "aliases": [
                    "סוגרים את כל האפליקציות",
                    "יוצאים מאפליקציות",
                    "מכבים אפליקציות",
                ],
                "points": 11,
            },
            {
                "canonical": "שולחים הודעה אחרונה",
                "aliases": [
                    "שולחים הודעה",
                    "מודיעים שנגמרת הסוללה",
                    "נפרדים בוואטסאפ",
                ],
                "points": 8,
            },
            {
                "canonical": "נכנסים ללחץ",
                "aliases": ["נלחצים", "נכנסים לפאניקה", "מתחילים להילחץ"],
                "points": 7,
            },
            {
                "canonical": "מכבים את הטלפון",
                "aliases": ["מכבים", "סוגרים את הטלפון", "כיבוי"],
                "points": 5,
            },
        ],
    },
    {
        "id": "q2",
        "text": "מה אנשים עושים ברמזור אדום?",
        "answers": [
            {
                "canonical": "בודקים את הטלפון",
                "aliases": [
                    "מסתכלים בטלפון",
                    "בטלפון",
                    "וואטסאפ",
                    "גוללים בטלפון",
                ],
                "points": 29,
            },
            {
                "canonical": "מסתכלים על הנהגים מסביב",
                "aliases": [
                    "מסתכלים לצדדים",
                    "בוהים באנשים",
                    "מסתכלים במכוניות ליד",
                ],
                "points": 19,
            },
            {
                "canonical": "שרים עם המוזיקה",
                "aliases": ["שרים", "שומעים מוזיקה", "מזמזמים", "שרים באוטו"],
                "points": 15,
            },
            {
                "canonical": "מתעצבנים ומחכים שיתחלף",
                "aliases": ["מתעצבנים", "מחכים לירוק", "מקללים את הרמזור", "חסרי סבלנות"],
                "points": 12,
            },
            {
                "canonical": "מחטטים באף",
                "aliases": ["מחטטים", "מכניסים אצבע לאף", "מנקים את האף"],
                "points": 10,
            },
            {
                "canonical": "מסדרים שיער במראה",
                "aliases": ["מסתכלים במראה", "מסדרים שיער", "מתאפרים", "בודקים איך נראים"],
                "points": 8,
            },
            {
                "canonical": "אוכלים או שותים",
                "aliases": ["אוכלים", "שותים", "לוגמים קפה", "מנשנשים"],
                "points": 7,
            },
        ],
    },
    {
        "id": "q3",
        "text": "מה אנשים עושים לפני דייט?",
        "answers": [
            {
                "canonical": "מתקלחים",
                "aliases": ["עושים מקלחת", "נכנסים למקלחת", "מתרחצים"],
                "points": 24,
            },
            {
                "canonical": "מתלבטים מה ללבוש",
                "aliases": ["בוחרים בגדים", "מחליפים בגדים", "מודדים בגדים", "מה ללבוש"],
                "points": 21,
            },
            {
                "canonical": "מתגלחים או מסתדרים",
                "aliases": [
                    "מתגלחים",
                    "מסדרים שיער",
                    "מתאפרים",
                    "מורידים שיער",
                    "מתגנדרים",
                ],
                "points": 17,
            },
            {
                "canonical": "עושים סטוק ברשתות",
                "aliases": [
                    "עושים סטוק",
                    "בודקים אינסטגרם",
                    "מחפשים בפייסבוק",
                    "בודקים את הדייט",
                    "חוקרים אותו",
                ],
                "points": 14,
            },
            {
                "canonical": "שמים בושם",
                "aliases": ["מתבשמים", "שמים דאודורנט", "בושם"],
                "points": 10,
            },
            {
                "canonical": "מתרגלים מה להגיד",
                "aliases": ["מתכננים שיחה", "מכינים נושאי שיחה", "עושים חזרות"],
                "points": 8,
            },
            {
                "canonical": "שותים משהו בשביל האומץ",
                "aliases": ["שותים אלכוהול", "דופקים שוט", "שותים יין", "שותים להרגעה"],
                "points": 6,
            },
        ],
    },
    {
        "id": "q4",
        "text": "מה אנשים עושים כשמשעמם?",
        "answers": [
            {
                "canonical": "גוללים בטלפון",
                "aliases": [
                    "בטלפון",
                    "גוללים באינסטגרם",
                    "טיקטוק",
                    "רשתות חברתיות",
                    "משחקים בטלפון",
                ],
                "points": 28,
            },
            {
                "canonical": "רואים סדרה או סרט",
                "aliases": ["רואים טלוויזיה", "נטפליקס", "צופים בסדרה", "רואים סרט"],
                "points": 20,
            },
            {
                "canonical": "אוכלים",
                "aliases": ["מנשנשים", "פותחים את המקרר", "מחפשים אוכל", "אוכלים שטויות"],
                "points": 16,
            },
            {
                "canonical": "מאוננים",
                "aliases": ["מביאים ביד", "עושים ביד", "נוגעים בעצמם"],
                "points": 12,
            },
            {
                "canonical": "הולכים לישון",
                "aliases": ["ישנים", "תופסים תנומה", "נרדמים"],
                "points": 10,
            },
            {
                "canonical": "מציקים לחברים",
                "aliases": ["מתקשרים לחברים", "שולחים הודעות", "מחפשים עם מי לצאת"],
                "points": 8,
            },
            {
                "canonical": "מנקים או מסדרים",
                "aliases": ["מנקים", "מסדרים את הבית", "עושים כביסה"],
                "points": 6,
            },
        ],
    },
    {
        "id": "q5",
        "text": "מה אנשים עושים כשהם בלחץ?",
        "answers": [
            {
                "canonical": "כוססים ציפורניים",
                "aliases": ["אוכלים ציפורניים", "כוססים", "נושכים ציפורניים"],
                "points": 22,
            },
            {
                "canonical": "מעשנים",
                "aliases": ["יוצאים לסיגריה", "מדליקים סיגריה", "סיגריה"],
                "points": 19,
            },
            {
                "canonical": "אוכלים בלי הפסקה",
                "aliases": ["אכילה רגשית", "מנשנשים", "אוכלים", "טוחנים אוכל"],
                "points": 16,
            },
            {
                "canonical": "הולכים הלוך ושוב",
                "aliases": ["מסתובבים", "צועדים בבית", "לא יושבים בשקט", "חסרי מנוחה"],
                "points": 14,
            },
            {
                "canonical": "נושמים עמוק",
                "aliases": ["עושים נשימות", "מדיטציה", "מנסים להירגע", "נרגעים"],
                "points": 11,
            },
            {
                "canonical": "פורקים על מישהו",
                "aliases": ["צועקים", "מתעצבנים", "רבים", "מדברים עם חבר"],
                "points": 10,
            },
            {
                "canonical": "רצים לשירותים",
                "aliases": ["הולכים לשירותים", "משלשלים", "כואבת הבטן"],
                "points": 8,
            },
        ],
    },
    {
        "id": "q6",
        "text": 'דברים שישראלים עושים בחו"ל',
        "answers": [
            {
                "canonical": "מדברים עברית בקול",
                "aliases": ["צועקים בעברית", "מדברים בקול רם", "עושים רעש", "רועשים"],
                "points": 23,
            },
            {
                "canonical": "מחפשים אוכל ישראלי",
                "aliases": ["מחפשים חומוס", "אוכלים בבית חבד", "מחפשים אוכל מהבית"],
                "points": 19,
            },
            {
                "canonical": "מתמקחים על המחיר",
                "aliases": ["מתמקחים", "עושים מיקוח", "מבקשים הנחה", "מורידים מחיר"],
                "points": 16,
            },
            {
                "canonical": "מתלוננים שהכול יקר",
                "aliases": ["מתלוננים", "אומרים שיקר", "משווים מחירים לארץ", "יקר פה"],
                "points": 14,
            },
            {
                "canonical": "מצלמים הכול",
                "aliases": ["מצטלמים", "עושים סלפי", "מעלים סטורי", "מצלמים מלא"],
                "points": 11,
            },
            {
                "canonical": "מעמיסים בארוחת הבוקר",
                "aliases": [
                    "מעמיסים בבופה",
                    "לוקחים אוכל מהמלון",
                    "גונבים מהבופה",
                    "אוכלים מלא במלון",
                ],
                "points": 9,
            },
            {
                "canonical": "מעמידים פנים שהם לא ישראלים",
                "aliases": ["אומרים שהם לא מישראל", "מסתירים שהם ישראלים", "מדברים באנגלית"],
                "points": 8,
            },
        ],
    },
    {
        "id": "q7",
        "text": "תירוצים נפוצים לאיחור",
        "answers": [
            {
                "canonical": "היו פקקים",
                "aliases": ["פקקים", "נתקעתי בפקק", "הכביש היה עמוס", "עומסי תנועה"],
                "points": 27,
            },
            {
                "canonical": "השעון לא צלצל",
                "aliases": ["לא שמעתי את השעון", "נרדמתי", "קמתי מאוחר", "השעון המעורר"],
                "points": 20,
            },
            {
                "canonical": "לא מצאתי חניה",
                "aliases": ["חיפשתי חניה", "אין חניה", "בעיה בחניה", "חניה"],
                "points": 15,
            },
            {
                "canonical": "האוטובוס או הרכבת איחרו",
                "aliases": [
                    "האוטובוס איחר",
                    "הרכבת איחרה",
                    "תחבורה ציבורית",
                    "פספסתי אוטובוס",
                ],
                "points": 13,
            },
            {
                "canonical": "הילד או הכלב עיכבו אותי",
                "aliases": ["הילד עיכב", "הכלב עיכב", "הילדים", "הייתי עם הילד"],
                "points": 10,
            },
            {
                "canonical": "לא מצאתי את המפתחות",
                "aliases": ["חיפשתי מפתחות", "איבדתי את המפתחות", "המפתחות נעלמו"],
                "points": 8,
            },
            {
                "canonical": "הפגישה הקודמת התארכה",
                "aliases": ["הישיבה התארכה", "נתקעתי בעבודה", "הבוס עיכב אותי", "הייתה לי שיחה"],
                "points": 7,
            },
        ],
    },
    {
        "id": "q8",
        "text": "מה אנשים עושים בשירותים?",
        "answers": [
            {
                "canonical": "גוללים בטלפון",
                "aliases": ["בטלפון", "קוראים וואטסאפ", "אינסטגרם", "טיקטוק", "משחקים בטלפון"],
                "points": 31,
            },
            {
                "canonical": "קוראים מה שכתוב על האריזות",
                "aliases": ["קוראים תוויות", "קוראים את השמפו", "קוראים בקבוקים", "קוראים עיתון"],
                "points": 18,
            },
            {
                "canonical": "חושבים על החיים",
                "aliases": ["חושבים", "מהרהרים", "פותרים בעיות", "מתכננים דברים"],
                "points": 15,
            },
            {
                "canonical": "עושים קקי",
                "aliases": ["מחרבנים", "קקי", "מספר שתיים", "מתפנים"],
                "points": 13,
            },
            {
                "canonical": "מאוננים",
                "aliases": ["מביאים ביד", "עושים ביד", "נוגעים בעצמם"],
                "points": 10,
            },
            {
                "canonical": "שרים",
                "aliases": ["מזמזמים", "עושים הופעה", "שרים לעצמם"],
                "points": 7,
            },
            {
                "canonical": "מתחבאים מכולם",
                "aliases": ["לוקחים הפסקה", "בורחים מהילדים", "יושבים בשקט", "מתבודדים"],
                "points": 6,
            },
        ],
    },
    {
        "id": "q9",
        "text": "מה אנשים עושים כשלא מצליחים להירדם?",
        "answers": [
            {
                "canonical": "גוללים בטלפון",
                "aliases": ["בטלפון", "אינסטגרם", "טיקטוק", "קוראים בטלפון"],
                "points": 25,
            },
            {
                "canonical": "מתהפכים במיטה",
                "aliases": ["מתהפכים מצד לצד", "זזים במיטה", "מנסים להירדם", "שוכבים ערים"],
                "points": 20,
            },
            {
                "canonical": "סופרים כבשים",
                "aliases": ["סופרים", "כבשים", "ספירת כבשים"],
                "points": 15,
            },
            {
                "canonical": "רואים סדרה",
                "aliases": ["רואים טלוויזיה", "נטפליקס", "רואים סרט", "פותחים סדרה"],
                "points": 13,
            },
            {
                "canonical": "קמים לאכול",
                "aliases": ["אוכלים", "פותחים את המקרר", "מנשנשים בלילה", "נשנוש"],
                "points": 10,
            },
            {
                "canonical": "מאוננים",
                "aliases": ["מביאים ביד", "עושים ביד", "נוגעים בעצמם"],
                "points": 7,
            },
            {
                "canonical": "עושים נשימות או מדיטציה",
                "aliases": ["נושמים עמוק", "מדיטציה", "הרפיה", "עושים נשימות"],
                "points": 6,
            },
            {
                "canonical": "קמים מהמיטה",
                "aliases": ["יוצאים מהמיטה", "מסתובבים בבית", "עוברים לספה"],
                "points": 4,
            },
        ],
    },
    {
        "id": "q10",
        "text": "דברים שהכי מעצבנים בכביש",
        "answers": [
            {
                "canonical": "נהגים שחותכים",
                "aliases": ["חותכים", "נדחפים לנתיב", "עוקפים בפראות", "נהג שנדחף"],
                "points": 24,
            },
            {
                "canonical": "נהגים איטיים בנתיב השמאלי",
                "aliases": ["נוסעים לאט בשמאל", "נתקעים בשמאל", "איטי בנתיב שמאל", "לא מפנים שמאל"],
                "points": 19,
            },
            {
                "canonical": "לא מאותתים",
                "aliases": [
                    "בלי איתות",
                    "לא שמים וינקר",
                    "לא משתמשים באיתות",
                    "עוברים נתיב בלי לאותת",
                ],
                "points": 16,
            },
            {
                "canonical": "צופרים בלי סיבה",
                "aliases": ["צפירות", "צופרים", "צפירה ברמזור", "נשענים על הצופר"],
                "points": 13,
            },
            {
                "canonical": "מתעסקים בטלפון בנהיגה",
                "aliases": [
                    "בטלפון בזמן נהיגה",
                    "מסמסים בנהיגה",
                    "נוהגים עם הטלפון",
                    "וואטסאפ בנהיגה",
                ],
                "points": 11,
            },
            {
                "canonical": "נצמדים מאחור",
                "aliases": ["לא שומרים מרחק", "יושבים על הזנב", "נדבקים מאחור", "נוסעים צמוד"],
                "points": 9,
            },
            {
                "canonical": "חוסמים עם חניה גרועה",
                "aliases": ["חניה כפולה", "חוסמים את הכביש", "חונים כמו זבל", "חניה עקומה"],
                "points": 8,
            },
        ],
    },
]

SurveyMatcher = Callable[[str], dict[str, int | str] | None]

_QUESTIONS_BY_ID = {question["id"]: question for question in SURVEY_QUESTIONS}


def get_survey_question(question_id: str) -> dict[str, Any] | None:
    """Return a survey question by its stable public identifier."""

    return _QUESTIONS_BY_ID.get(question_id)


@lru_cache
def get_survey_matcher(question_id: str) -> SurveyMatcher:
    """Build a stateless matcher backed by the regular round validator."""

    question = get_survey_question(question_id)
    if question is None:
        raise KeyError(question_id)

    answers = question["answers"]
    index = build_question_index(
        [
            (slot_index, answer["canonical"], None, answer["aliases"])
            for slot_index, answer in enumerate(answers)
        ]
    )

    def match(guess: str) -> dict[str, int | str] | None:
        validator = RoundValidator(
            index,
            max_length=settings.max_answer_length,
            fuzzy_enabled=settings.fuzzy_matching_enabled,
            fuzzy_max_distance=settings.fuzzy_max_distance,
            fuzzy_min_length=settings.fuzzy_min_length,
        )
        result = validator.check(guess)
        if result.status != AnswerStatus.VALID or result.entry is None:
            return None
        slot_index = result.entry.answer_id
        answer = answers[slot_index]
        return {
            "slot_index": slot_index,
            "canonical": answer["canonical"],
            "points": answer["points"],
        }

    return match
