"""Source-audited geography and science curation for batch V5.

``EXPANSION_V5`` uses the regular answer-tuple shape for both new canonicals
and aliases added to an existing canonical.  The seed merges each tuple by
canonical, so an English or alternate name cannot create a second score.
Normalization-only Hebrew spelling variants are deliberately omitted.
"""

from __future__ import annotations

# answer tuples: (canonical, aliases, semantic_group | None)
EXPANSION_V5: dict[str, list[tuple[str, list[str], str | None]]] = {
    "כתבו שמות של מדינות באסיה": [
        ("ישראל", ["Israel"], None),
        ("יפן", ["Japan"], None),
        ("סין", ["China"], None),
        ("הודו", ["India"], None),
        ("תאילנד", ["Thailand"], None),
        ("וייטנאם", ["Vietnam"], None),
        ("דרום קוריאה", ["South Korea", "Republic of Korea", "ROK"], None),
        ("צפון קוריאה", ["North Korea", "DPRK"], None),
        ("אינדונזיה", ["Indonesia"], None),
        ("פיליפינים", ["Philippines"], None),
        ("סינגפור", ["Singapore"], None),
        ("מלזיה", ["Malaysia"], None),
        ("נפאל", ["Nepal"], None),
        ("מונגוליה", ["Mongolia"], None),
        ("קזחסטן", ["Kazakhstan"], None),
        ("פקיסטן", ["Pakistan"], None),
        ("בנגלדש", ["Bangladesh"], None),
        ("סרי לנקה", ["Sri Lanka"], None),
        ("קמבודיה", ["Cambodia"], None),
        ("לאוס", ["Laos"], None),
        ("מיאנמר", ["בורמה", "Myanmar", "Burma"], None),
        ("בהוטן", ["Bhutan"], None),
        ("איראן", ["Iran"], None),
        ("עיראק", ["Iraq"], None),
        ("ערב הסעודית", ["Saudi Arabia"], None),
        ("איחוד האמירויות", ["United Arab Emirates", "UAE"], None),
        ("קטאר", ["Qatar"], None),
        ("ירדן", ["Jordan"], None),
        ("לבנון", ["Lebanon"], None),
        ("סוריה", ["Syria"], None),
        ("טורקיה", ["Turkey", "Türkiye"], None),
        ("אפגניסטן", ["Afghanistan"], None),
        ("אוזבקיסטן", ["Uzbekistan"], None),
        ("טורקמניסטן", ["Turkmenistan"], None),
        ("קירגיזסטן", ["Kyrgyzstan"], None),
        ("טג'יקיסטן", ["Tajikistan"], None),
        ("האיים המלדיביים", ["Maldives"], None),
        ("ברוניי", ["Brunei", "Brunei Darussalam"], None),
        ("מזרח טימור", ["East Timor", "Timor-Leste"], None),
        ("עומאן", ["Oman"], None),
        ("תימן", ["Yemen"], None),
        ("בחריין", ["Bahrain"], None),
        ("גאורגיה", ["Georgia"], None),
        ("ארמניה", ["Armenia"], None),
        ("אזרבייג'ן", ["Azerbaijan"], None),
        ("רוסיה", ["Russia", "Russian Federation"], None),
        ("טייוואן", ["Taiwan"], None),
        ("כווית", ["Kuwait"], None),
        ("קפריסין", ["Cyprus"], None),
        ("פלסטין", ["מדינת פלסטין", "Palestine", "State of Palestine"], None),
    ],
    "כתבו שמות של ערים בישראל": [
        ("כפר יונה", ["Kfar Yona"], None),
        ("גני תקווה", ["Ganei Tikva"], None),
        ("כפר קרע", ["Kafr Qara"], None),
        ("מע'אר", ["Maghar"], None),
    ],
}


# Boundary policies follow docs/ADDING_A_QUESTION.md.  The closed continental
# sets use UN M49; the existing Asia question also retains its already-curated
# transcontinental/de-facto entries.
QUESTION_POLICIES_V5: dict[str, dict[str, str | list[str]]] = {
    "כתבו שמות של מדינות באסיה": {
        "includes": (
            "Current sovereign states assigned to Asia by UN M49, plus the existing "
            "transcontinental and de-facto country entries in this question."
        ),
        "excludes": ["הונג קונג", "מקאו", "גרינלנד"],
        "granularity": "Countries score once; territories, cities, and regions do not score.",
        "time_and_place": "Current geography and names.",
        "brands": "Not applicable.",
        "language": "Hebrew and English country names plus established alternate names.",
    },
    "כתבו שמות של מדינות באירופה": {
        "includes": (
            "The 44 sovereign states in the UN M49 Europe regions, plus the existing "
            "transcontinental Turkey and partially recognized Kosovo policy entries."
        ),
        "excludes": ["קפריסין", "אנגליה", "סקוטלנד", "ויילס"],
        "granularity": (
            "Sovereign and explicitly retained transcontinental/partially recognized states; "
            "constituent countries and territories do not score."
        ),
        "time_and_place": "Current UN M49 European geography plus the documented legacy extensions.",
        "brands": "Not applicable.",
        "language": "Hebrew and English names plus established local or former short names.",
    },
    "כתבו שמות של מדינות באפריקה": {
        "includes": "The 54 UN member states assigned to Africa by UN M49.",
        "excludes": ["סהרה המערבית", "ראוניון", "מיוט"],
        "granularity": "Sovereign UN member states only; dependencies do not score.",
        "time_and_place": "Current UN membership and M49 geography.",
        "brands": "Not applicable.",
        "language": "Hebrew and English names plus established former or formal names.",
    },
    "כתבו שמות של ערים בישראל": {
        "includes": "Localities whose current municipal status is city municipality (עירייה).",
        "excludes": ["זכרון יעקב", "גן יבנה", "מבשרת ציון"],
        "granularity": "A municipality scores once under its current municipal name.",
        "time_and_place": "Current Israeli municipal classification.",
        "brands": "Not applicable.",
        "language": "Hebrew names and established former names; English names where useful.",
    },
    "כתבו שמות של יסודות כימיים": {
        "includes": "Chemical elements with established Hebrew names in the curated list.",
        "excludes": ["מים", "מלח", "פלדה"],
        "granularity": "Each chemical element scores once; symbols and English names are aliases.",
        "time_and_place": "Current IUPAC element names and symbols.",
        "brands": "Not applicable.",
        "language": "Established Hebrew names, IUPAC English names, and chemical symbols.",
    },
    "כתבו שמות של בירות בעולם": {
        "includes": "Current national capital cities in the curated major-capitals list.",
        "excludes": ["ניו יורק", "סידני", "איסטנבול"],
        "granularity": "Each capital city scores once; alternate spellings are aliases.",
        "time_and_place": "Current national capitals.",
        "brands": "Not applicable.",
        "language": "Hebrew city names and established English names.",
    },
}


CURATION_SOURCES: dict[str, list[str]] = {
    "כתבו שמות של מדינות באסיה": [
        "https://unstats.un.org/unsd/methodology/m49/overview/",
        "https://www.un.org/about-us/member-states",
        "https://www.cbs.gov.il/he/cbsNewBrand/Pages/מילונים-Code-lists-Classifications.aspx",
    ],
    "כתבו שמות של מדינות באירופה": [
        "https://unstats.un.org/unsd/methodology/m49/overview/",
        "https://ungegn.un.org/dashboard/countries/index",
        "https://www.cbs.gov.il/he/cbsNewBrand/Pages/מילונים-Code-lists-Classifications.aspx",
    ],
    "כתבו שמות של מדינות באפריקה": [
        "https://unstats.un.org/unsd/methodology/m49/overview/",
        "https://www.un.org/about-us/member-states",
        "https://www.cbs.gov.il/he/cbsNewBrand/Pages/מילונים-Code-lists-Classifications.aspx",
    ],
    "כתבו שמות של ערים בישראל": [
        "https://www.cbs.gov.il/he/cbsNewBrand/Pages/מילונים-Code-lists-Classifications.aspx",
        "https://www.gov.il/BlobFolder/guide/local-goverment-criticism/he/home_main_local-government_local-goverment-criticism_bluebook-2023.pdf",
    ],
    "כתבו שמות של יסודות כימיים": [
        "https://iupac.org/what-we-do/periodic-table-of-elements/",
        "https://terms.hebrew-academy.org.il/Millonim/ShowMillon?KodMillon=311",
        "https://pop.education.gov.il/tchumey_daat/mada-tehnologia/chativat-beynayim/noseem_nilmadim/mivne-homer/",
    ],
    "כתבו שמות של בירות בעולם": [
        "https://ungegn.un.org/dashboard/cities/index",
        "https://www.britannica.com/topic/list-of-countries-capitals-and-currencies-2067022",
    ],
}
