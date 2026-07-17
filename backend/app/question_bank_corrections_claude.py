"""Content corrections for question-bank categories 1-20 (Claude audit).

Sourced from docs/CLAUDE_QUESTION_BANK_AUDIT.md after external verification
(Hebrew Wikipedia list of Israeli cities, Olympic programme 2024/2028
coverage, botanical sources for salak). Categories 21-31 are intentionally
NOT touched here — they are owned by a separate work stream.

The data is declarative; ``apply_corrections`` produces a corrected copy of
a seed-format question list without mutating the input, so the seed can
adopt it with a single call and tests can validate it in isolation.

Correction kinds per question:
- ``rename_canonicals``: fix a wrong canonical name (history-preserving —
  seed already supports renames via the same mechanism as
  LEGACY_CANONICAL_RENAMES).
- ``remove_aliases``: drop an alias that is factually wrong for its answer.
- ``add_aliases``: attach spelling variants / common misspellings to an
  existing canonical. Includes explicit misspellings that fuzzy matching
  can never accept because they are ambiguous (e.g. "איראק" sits at edit
  distance 1 from both "עיראק" and "איראן").
- ``set_semantic_group``: mark existing answers that must block each other
  as duplicates.
- ``add``: new (canonical, aliases, semantic_group) answers.
"""

from copy import deepcopy

# The exact question texts of categories 1-20, in audit-report order.
CATEGORY_SCOPE_1_20: tuple[str, ...] = (
    "כתבו שמות של פירות טרופיים",  # 1
    "כתבו שמות של מוצרי איפור",  # 2
    "כתבו שמות של מדינות באירופה",  # 3
    "כתבו שמות של בעלי חיים שחיים בים",  # 4
    "כתבו שמות של ירקות ירוקים",  # 5
    "כתבו שמות של מותגי רכב",  # 6
    "כתבו שמות של ענפי ספורט אולימפיים",  # 7
    "כתבו שמות של כלי נגינה",  # 8
    "כתבו טעמים של גלידה",  # 9
    "כתבו שמות של ערי בירה בעולם",  # 10
    "כתבו שמות של ערים בישראל",  # 11
    "כתבו שמות של מדינות באסיה",  # 12
    "כתבו שמות של איברי גוף",  # 13
    "כתבו שמות של מקצועות",  # 14
    "כתבו שמות של כלי מטבח",  # 15
    "כתבו שמות של פריטי לבוש",  # 16
    "כתבו שמות של משקאות",  # 17
    "כתבו שמות של קינוחים",  # 18
    "כתבו שמות של פרחים",  # 19
    "כתבו שמות של כלי תחבורה",  # 20
)

Answer = tuple[str, list[str], str | None]

QUESTION_CORRECTIONS: dict[str, dict] = {
    # 1 — פירות טרופיים: הפרי הוא סאלאק ("פרי הנחש"); הצורה "סלק" קיבלה
    # בטעות שחקנים שהתכוונו לירק.
    "כתבו שמות של פירות טרופיים": {
        "rename_canonicals": {"סלק": "סאלאק"},
        "add_aliases": {
            "סאלאק": ["סלאק"],
            "קרמבולה": ["פרי כוכב", "כוכב פרי"],
            "פיטאיה": ["דרגון פרוט"],
        },
    },
    # 2 — מוצרי איפור
    "כתבו שמות של מוצרי איפור": {
        "add": [("לק", ["לק ציפורניים"], None)],
    },
    # 3 — מדינות באירופה: טרנס-יבשתית + קוסובו (מוכרת חלקית — החלטת
    # מדיניות הפיכה, מתועדת בדוח ה-audit).
    "כתבו שמות של מדינות באירופה": {
        "add": [
            ("טורקיה", [], None),
            ("קוסובו", [], None),
        ],
        "add_aliases": {"איסלנד": ["איסלאנד"]},
    },
    # 4 — בעלי חיים בים: סרטן נהרות (crayfish) חי במים מתוקים ואינו לובסטר.
    "כתבו שמות של בעלי חיים שחיים בים": {
        "remove_aliases": {"לובסטר": ["סרטן נהרות"]},
        "add": [("אלמוג", ["אלמוגים"], None)],
    },
    # 5 — ירקות ירוקים: alias גנרי מדי.
    "כתבו שמות של ירקות ירוקים": {
        "remove_aliases": {"עלי בייבי": ["בייבי"]},
    },
    # 6 — מותגי רכב: מותגי יוקרה + המותגים הסיניים הנפוצים בישראל.
    "כתבו שמות של מותגי רכב": {
        "add": [
            ("מזראטי", ["מסראטי"], None),
            ("רולס רויס", [], None),
            ("בנטלי", [], None),
            ("בוגאטי", [], None),
            ("מיני", ["מיני קופר"], None),
            ("דודג'", ["דודג"], None),
            ("אינפיניטי", [], None),
            ("בי ווי די", ["byd"], None),
            ("אם ג'י", ["mg"], None),
            ("צ'רי", ["chery"], None),
            ("ג'ילי", ["geely"], None),
        ],
    },
    # 7 — ספורט אולימפי: הענף הוא קפיצות למים (לא "צלילה"); ענפי החורף
    # חסרו לגמרי; ברייקינג הופיע בפריז 2024.
    "כתבו שמות של ענפי ספורט אולימפיים": {
        "rename_canonicals": {"צלילה": "קפיצות למים"},
        "add_aliases": {"קפיצות למים": ["צלילה", "קפיצה למים"]},
        "add": [
            ("סקי", ["סקי אלפיני"], None),
            ("סנובורד", [], None),
            ("החלקה אמנותית", [], None),
            ("החלקה מהירה", [], None),
            ("הוקי קרח", [], None),
            ("ביאתלון", [], None),
            ("קרלינג", [], None),
            ("בובסלי", ["בובסלד"], None),
            ("ברייקדאנס", ["ברייקינג"], None),
            ("שחייה אמנותית", ["שחיה אמנותית"], None),
        ],
    },
    # 8 — כלי נגינה
    "כתבו שמות של כלי נגינה": {
        "add": [
            ("עוד", ["אוד"], None),
            ("שופר", [], None),
            ("מצילתיים", ["מצילות"], None),
            ("משולש", [], None),
            ("גונג", [], None),
            ("קלימבה", [], None),
            ("בוזוקי", [], None),
            ("מלודיקה", [], None),
            ("חליל פאן", [], None),
            ("עוגב", [], None),
        ],
    },
    # 9 — טעמים של גלידה
    "כתבו טעמים של גלידה": {
        "add": [
            ("חלבה", ["חלווה"], None),
            ("יוגורט", [], None),
            ("נוטלה", [], None),
        ],
    },
    # 10 — ערי בירה: ההרחבה הגדולה; כולן בירות רשמיות מוכרות.
    "כתבו שמות של ערי בירה בעולם": {
        "add": [
            ("קייב", [], None),
            ("טהרן", ["טהראן"], None),
            ("בגדד", ["בגדאד"], None),
            ("דמשק", [], None),
            ("מינסק", [], None),
            ("ריגה", [], None),
            ("וילנה", ["וילניוס"], None),
            ("טאלין", ["טלין"], None),
            ("בלגרד", [], None),
            ("זאגרב", ["זגרב"], None),
            ("ליובליאנה", [], None),
            ("ברטיסלבה", [], None),
            ("רייקיאוויק", ["רייקיאביק"], None),
            ("לוקסמבורג", [], None),
            ("רבאט", [], None),
            ("תוניס", [], None),
            ("קטמנדו", [], None),
            ("ג'קרטה", ["גקרטה"], None),
            ("מנילה", [], None),
            ("האנוי", ["הנוי"], None),
            ("אולן בטור", ["אולאן בטור"], None),
        ],
        "add_aliases": {"בייג'ינג": ["בייג'ין"]},
    },
    # 11 — ערים בישראל: כולן במעמד עירייה רשמי. טירה וקלנסווה אומתו
    # עצמאית מול פרסומי ממשלה והלמ"ס לפני השילוב.
    "כתבו שמות של ערים בישראל": {
        "add": [
            ("קריית אתא", ["קרית אתא"], None),
            ("קריית ים", ["קרית ים"], None),
            ("קריית ביאליק", ["קרית ביאליק"], None),
            ("קריית מוצקין", ["קרית מוצקין"], None),
            ("רמת השרון", [], None),
            ("ראש העין", [], None),
            ("יהוד", ["יהוד מונוסון"], None),
            ("אלעד", [], None),
            ("ביתר עילית", [], None),
            ("מודיעין עילית", [], None),
            ("נתיבות", [], None),
            ("אופקים", [], None),
            ("בית שאן", [], None),
            ("מגדל העמק", [], None),
            ("נשר", [], None),
            ("טירת כרמל", ["טירת הכרמל"], None),
            ("אריאל", [], None),
            ("מעלות תרשיחא", ["מעלות"], None),
            ("קריית מלאכי", ["קרית מלאכי"], None),
            ("אום אל פחם", [], None),
            ("רהט", [], None),
            ("טייבה", [], None),
            ("סחנין", ["סכנין"], None),
            ("שפרעם", [], None),
            ("טמרה", [], None),
            ("כפר קאסם", ["כפר קסם"], None),
            ("באקה אל גרביה", ["באקה אל גרבייה"], None),
            ("טירה", [], None),
            ("קלנסווה", ["קלנסואה"], None),
        ],
    },
    # 12 — מדינות באסיה: רוסיה טרנס-יבשתית; "איראק" הוא כתיב שגוי נפוץ
    # של עיראק ש-fuzzy לעולם ידחה כי הוא במרחק 1 גם מאיראן — לכן alias
    # מפורש. טייוואן — החלטת מדיניות הפיכה, מתועדת בדוח.
    "כתבו שמות של מדינות באסיה": {
        "add": [
            ("רוסיה", [], None),
            ("טייוואן", ["טאיוואן"], None),
        ],
        "add_aliases": {
            "עיראק": ["איראק"],
            "וייטנאם": ["וייטנם"],
            "אזרבייג'ן": ["אזרבייגן"],
        },
    },
    # 13 — איברי גוף
    "כתבו שמות של איברי גוף": {
        "add": [
            ("עצם", ["עצמות"], None),
            ("שריר", ["שרירים"], None),
            ("גרון", [], None),
            ("גולגולת", [], None),
            ("עמוד שדרה", ["עמוד השדרה"], None),
            ("צלע", ["צלעות"], None),
            ("אגודל", [], None),
            ("בוהן", [], None),
            ("ושט", [], None),
            ("שלפוחית שתן", ["שלפוחית"], None),
            ("כיס מרה", ["מרה"], None),
            ("וריד", ["ורידים"], None),
            ("עורק", ["עורקים"], None),
        ],
    },
    # 14 — מקצועות: שיננית היא מקצוע נפרד, לא alias של רופא שיניים.
    "כתבו שמות של מקצועות": {
        "remove_aliases": {"רופא שיניים": ["שיננית"]},
        "add": [
            ("שיננית", ["שינן"], None),
            ("מלצר", ["מלצרית"], None),
            ("קופאי", ["קופאית"], None),
            ("מאבטח", ["מאבטחת"], None),
            ("אופה", [], None),
            ("קונדיטור", ["קונדיטורית"], None),
            ("קצב", [], None),
            ("דוור", [], None),
            ("מזכיר", ["מזכירה"], None),
            ("בנקאי", ["בנקאית"], None),
            ("סוכן ביטוח", ["סוכנת ביטוח"], None),
            ("מתווך", ["מתווכת"], None),
            ("פיזיותרפיסט", ["פיזיותרפיסטית"], None),
            ("דיאטן", ["דיאטנית"], None),
            ("אופטומטריסט", [], None),
            ("פסיכיאטר", ["פסיכיאטרית"], None),
            ("חייט", ["חייטת"], None),
            ("סנדלר", [], None),
        ],
    },
    # 15 — כלי מטבח
    "כתבו שמות של כלי מטבח": {
        "add": [
            ("משפך", [], None),
            ("מסחטה", ["מסחטת מיץ"], None),
            ("ווק", [], None),
            ("מגש", [], None),
            ("מלחייה", ["מלחיה"], None),
            ("סיר לחץ", [], None),
        ],
        "add_aliases": {"פומפייה": ["מגרדת"]},
    },
    # 16 — פריטי לבוש: בגד ים וביקיני חוסמים זה את זה כקבוצת משמעות.
    "כתבו שמות של פריטי לבוש": {
        "set_semantic_group": {"בגד ים": "swimwear"},
        "add": [
            ("גרביונים", [], None),
            ("ביקיני", [], "swimwear"),
            ("חלוק", ["חלוק רחצה"], None),
        ],
    },
    # 17 — משקאות: קבוצות משמעות למשפחות שוקו/קפה/שייק + חוסרים ישראליים.
    "כתבו שמות של משקאות": {
        "set_semantic_group": {"שוקו": "choco-drink", "קפה": "coffee-hot", "שייק": "milkshake"},
        "add": [
            ("קקאו", [], "choco-drink"),
            ("שוקולד חם", ["שוקו חם"], "choco-drink"),
            ("נס קפה", ["נס"], "coffee-hot"),
            ("לימונענע", ["לימון נענע"], None),
            ("ברד", [], None),
            ("מיץ פטל", ["פטל"], None),
            ("מיץ גזר", [], None),
            ("סמוזי", ["סמותי"], None),
            ("מילקשייק", [], "milkshake"),
        ],
        "add_aliases": {"משקה אנרגיה": ["מונסטר", "אקס אל"]},
    },
    # 18 — קינוחים
    "כתבו שמות של קינוחים": {
        "add": [
            ("סופגנייה", ["סופגניה", "סופגניות"], None),
            ("ג'לי", [], None),
            ("אוזני המן", ["אוזן המן"], None),
            ("פחזנייה", ["פחזניה", "פחזניות"], None),
            ("בלינצ'ס", ["בלינצס"], None),
            ("בסבוסה", [], None),
            ("טארט", [], None),
            ("עוגת שמרים", [], None),
        ],
    },
    # 19 — פרחים: "וורד" (כפל ו') קצר מכדי שה-fuzzy יתפוס — alias מפורש.
    "כתבו שמות של פרחים": {
        "add_aliases": {"ורד": ["וורד"]},
        "add": [
            ("חצב", [], None),
            ("כרכום", [], None),
            ("סביון", [], None),
        ],
    },
    # 20 — כלי תחבורה: אונייה/ספינה זהות משמעות; "רכבת קלה" הוא המונח
    # הישראלי העדכני לחשמלית.
    "כתבו שמות של כלי תחבורה": {
        "set_semantic_group": {"אונייה": "ship"},
        "add_aliases": {"חשמלית": ["רכבת קלה", "הרכבת הקלה"]},
        "add": [
            ("ספינה", [], "ship"),
            ("כרכרה", [], None),
            ("ריקשה", [], None),
            ("סגוויי", ["סגווי"], None),
            ("קרוואן", [], None),
        ],
    },
}


def apply_corrections(questions: list[dict]) -> list[dict]:
    """Return a deep-copied question list with all corrections applied.

    Pure and idempotent: renames run first, then alias removals, group
    updates, alias additions and finally new answers. Aliases equal to
    their (possibly renamed) canonical are dropped; already-present
    aliases and answers are not duplicated.
    """
    corrected = deepcopy(questions)
    for question in corrected:
        correction = QUESTION_CORRECTIONS.get(question["text"])
        if correction is None:
            continue

        renames = correction.get("rename_canonicals", {})
        removals = correction.get("remove_aliases", {})
        groups = correction.get("set_semantic_group", {})
        alias_additions = correction.get("add_aliases", {})

        rebuilt: list[Answer] = []
        for canonical, aliases, group in question["answers"]:
            canonical = renames.get(canonical, canonical)
            aliases = [a for a in aliases if a not in removals.get(canonical, [])]
            for alias in alias_additions.get(canonical, []):
                if alias not in aliases:
                    aliases.append(alias)
            aliases = [a for a in aliases if a != canonical]
            group = groups.get(canonical, group)
            rebuilt.append((canonical, aliases, group))

        existing_canonicals = {answer[0] for answer in rebuilt}
        for canonical, aliases, group in correction.get("add", []):
            if canonical not in existing_canonicals:
                rebuilt.append((canonical, list(aliases), group))
                existing_canonicals.add(canonical)

        question["answers"] = rebuilt
    return corrected
