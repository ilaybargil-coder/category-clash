"""Source-audited Israeli stand-up comedian expansion for batch V8.

``EXPANSION_V8`` adds verified performers and useful alternate names to the
new question whose supplied canonical core lives in :mod:`app.question_bank`.
Aliases are genuine English forms or real alternate names; normalization-only
Hebrew spelling variants are deliberately omitted.
"""

from __future__ import annotations

# answer tuples: (canonical, aliases, semantic_group | None)
EXPANSION_V8: dict[str, list[tuple[str, list[str], str | None]]] = {
    "כתבו שמות של סטנדאפיסטים ישראליים": [
        ("אדיר מילר", ["Adir Miller"], None),
        ("שחר חסון", ["Shahar Hason"], None),
        ("יוחאי ספונדי", ["יוחאי ספונדר", "Yohay Sponder"], None),
        ("אורי חזקיה", ["Uri Hizkiah"], None),
        ("יובל סמו", ["Yuval Semo"], None),
        ("נדב אבוקסיס", ["Nadav Abuksis"], None),
        ("אסי כהן", ["Assi Cohen"], None),
        ("גורי אלפי", ["Guri Alfi"], None),
        ("טל פרידמן", ["Tal Friedman"], None),
        ("מריאנו אידלמן", ["Mariano Idelman"], None),
        ("גיא הוכמן", ["Guy Hochman"], None),
        ("שלומי קוריאט", ["Shlomi Koriat"], None),
        ("יניב זייד", ["Yaniv Zaid"], None),
        ("נתי לוי", ["Nati Levi"], None),
        ("ליאור שליין", ["Lior Schleien"], None),
        ("בן צור", ["Ben Tzur"], None),
        ("ישראל קטורזה", ["Israel Katorza"], None),
        ("שלום אסייג", ["Shalom Assayag"], None),
        ("רשף לוי", ["Reshef Levi"], None),
        ("עדי אשכנזי", ["Adi Ashkenazi"], None),
        ("אורנה בנאי", ["Orna Banai"], None),
        ("רותם אבוהב", ["Rotem Abuhab"], None),
        ("קובי מימון", ["Kobi Maimon"], None),
        ("מני עוזרי", ["Meni Ozeri"], None),
        ("נאור ציון", ["Naor Zion"], None),
        ("אבי נוסבאום", ["Avi Nussbaum"], None),
        ("יונתן ברק", ["Yonatan Barak"], None),
        ("תום יער", ["Tom Ya'ar"], None),
        ("חן מזרחי", ["Hen Mizrahi"], None),
        ("בני ברוכים", ["Benny Bruchim"], None),
    ],
}


CURATION_SOURCES: dict[str, list[str]] = {
    "כתבו שמות של סטנדאפיסטים ישראליים": [
        "https://live.tickchak.co.il/standup/artists",
        "https://www.standupro.co.il/סטנדאפיסטים-שמות",
        "https://www.zappa-club.co.il/artist/stand-up/",
    ],
}
