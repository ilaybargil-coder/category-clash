"""Human-reviewed additions produced by the continuous curator workflow.

This module is intentionally declarative. Recurring agents may propose edits to
it in a draft pull request, but production is updated only after tests and a
human-reviewed merge. Answer resolution remains scoped to the current question.
"""

from __future__ import annotations

CURATED_ANSWER_ADDITIONS: dict[str, list[tuple[str, list[str], str | None]]] = {
    "כתבו שמות של קינוחים": [
        (
            "מילפיי",
            [
                "מיל פיי",
                "מיל-פיי",
                "מילפה",
                "נפוליאון",
                "עוגת נפוליאון",
                "קרמשניט",
            ],
            None,
        ),
        ("קרואסון", ["קוראסון", "קרוסון", "קרואסונים", "croissant"], None),
        ("פנה קוטה", ["פנקוטה", "פנה-קוטה", "panna cotta"], None),
        ("קרם קרמל", ["פלאן", "פלן", "flan"], None),
        ("טארט טאטן", ["טאטן", "טארט טאטן תפוחים"], "pie"),
        ("פסטל דה נאטה", ["פסטל נאטה", "טארט פורטוגזי"], None),
        ("קנולי", ["קנולו", "קאנולי", "cannoli"], None),
        ("ספוליאטלה", ["ספולייטלה", "sfogliatella"], None),
        ("קיורטוש", ["קורטוש", "עוגת ארובה", "צ'ימני קייק"], None),
        ("קרונאט", ["קרונאטס", "cronut"], None),
        ("קאפקייק", ["קאפקייקס", "קאפ קייק", "cupcake"], "cake"),
        ("מאפין", ["מאפינס", "מופין", "muffin"], "cake"),
        ("דניש", ["מאפה דני", "danish"], None),
        (
            "שבלול קינמון",
            ["סינבון", "רול קינמון", "סינמון רול", "cinnamon roll"],
            None,
        ),
        ("עוגת אופרה", ["אופרה"], "cake"),
        ("עוגת היער השחור", ["יער שחור", "בלאק פורסט"], "cake"),
        ("רד ולווט", ["עוגת רד ולווט", "עוגת קטיפה אדומה"], "cake"),
        ("עוגת סאקר", ["סאכר טורטה", "זאכר טורטה", "Sachertorte"], "cake"),
        ("עוגת גבינה באסקית", ["צ'יזקייק באסקי"], "cheesecake"),
        ("עוגת גבינה פירורים", ["עוגת פירורים"], "cheesecake"),
        ("עוגת שיש", [], "cake"),
        ("עוגת מוס", [], "cake"),
        ("עוגת קרפים", ["קרפ קייק"], "cake"),
        ("עוגת קוקוס", [], "cake"),
        ("עוגת לימון", [], "cake"),
        ("טארטלט", ["מיני טארט"], "pie"),
        ("פאי דלעת", [], "pie"),
        ("פאי אוכמניות", [], "pie"),
        ("פאי דובדבנים", [], "pie"),
        ("קובלר", ["קובלר פירות"], None),
        ("קרם קטלאן", ["קרמה קטלאנה", "crema catalana"], None),
        ("זביונה", ["סבאיונה", "זבאיונה", "zabaglione"], None),
        ("קרפ סוזט", ["קרפ סוזט תפוזים"], None),
        ("אפוגטו", ["אפוגאטו", "affogato"], None),
        ("גרניטה", ["granita"], None),
        ("טפיוקה", ["פודינג טפיוקה"], None),
        ("פודינג צ'יה", ["צ'יה פודינג"], None),
        (
            "אורז בחלב",
            ["אורז עם חלב", "ריז בחלב", "סוטלאץ'", "סוטלאץ"],
            None,
        ),
        ("לילות ביירות", ["ליאלי לבנאן", "לילות לבנון"], None),
        ("קטאייף", ["קטאיף", "אטאייף", "עטאייף"], None),
        ("עוואמה", ["לוקמת אל קאדי", "לוקיימאת"], "fried-syrup-dessert"),
        ("זלביה", ["זלבי"], "fried-syrup-dessert"),
        ("לוקומדס", ["סופגניות יווניות"], "fried-syrup-dessert"),
        ("גולאב ג'מון", ["גולב ג'מון", "gulab jamun"], "fried-syrup-dessert"),
        ("ג'לבי", ["ג'לאבי", "jalebi"], "fried-syrup-dessert"),
        ("קולפי", ["גלידה הודית", "kulfi"], None),
        ("ראס מלאי", ["רסמלאי", "ראסמלאי", "ras malai"], None),
        ("בריגדיירו", ["בריגדירו", "brigadeiro"], None),
        ("לוקום", ["רחת לוקום", "רחת", "טורקיש דילייט"], None),
        ("פודינג לחם", ["לחם פודינג", "bread pudding"], None),
        ("סטיקי טופי פודינג", ["פודינג טופי דביק"], None),
        ("קייק פופ", ["קייק פופס", "cake pop"], "cake"),
        ("וופי פאי", ["whoopie pie"], None),
        ("סמורס", ["סמורז", "s'mores"], None),
        ("בננה ספליט", ["banana split"], None),
        ("סנדיי", ["סאנדיי", "גלידת סנדיי", "sundae"], None),
        ("מרציפן", ["מרצפן"], None),
    ],
}


CURATED_ALIAS_ADDITIONS: dict[str, dict[str, list[str]]] = {
    "כתבו שמות של קינוחים": {
        "אקלר": ["אקלייר", "אקלרים", "eclair"],
        "מקרון": ["מקרונים", "macaron"],
        "טירמיסו": ["טירמיזו", "tiramisu"],
        "קרם ברולה": ["קרם ברוליי", "קרם ברולה צרפתי"],
        "פרופיטרול": ["פרופיטרולים", "profiterole"],
        "פבלובה": ["פבלובה אישית"],
        "שטרודל": ["שטרודל תפוחים", "אפפל שטרודל"],
        "רוגלך": ["רוגעלך", "רוגלך שוקולד"],
        "בקלאווה": ["בקלווה", "בקלוואה"],
        "כנאפה": ["קנאפה", "כנאפי"],
    },
}


CURATION_SOURCES: dict[str, list[str]] = {
    "כתבו שמות של קינוחים": [
        "https://www.britannica.com/topic/pastry",
        "https://en.wikipedia.org/wiki/List_of_desserts",
        "https://en.wikipedia.org/wiki/List_of_pastries",
    ],
}
