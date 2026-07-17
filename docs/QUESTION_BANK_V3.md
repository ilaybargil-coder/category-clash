# מאגר שאלות V3 — כללי איכות והתאמה

הגרסה הזו עברה על כל 31 השאלות ומרחיבה את המאגר ל־2,216 תשובות
קנוניות, 1,451 aliases ו־3,601 צורות exact מנורמלות. מעבר לצורות
השמורות, המנוע תומך בהשלמה ייחודית ובטעות הקלדה אחת לא־עמומה, ולכן
מספר דרכי הקלט שהמשחק מסוגל להבין גדול משמעותית ממספר השורות במסד.

## סדר ההכרעה

1. התאמה מדויקת ל־canonical או alias.
2. הסרת ה״א הידיעה ובדיקת exact נוספת.
3. השלמת קידומת רק אם כל ההתאמות בשאלה מובילות לאותה תשובה.
4. Damerau–Levenshtein במרחק 1 בלבד, עם הגנת עמימות וכללי מקלדת
   מחמירים למילים קצרות.
5. דחייה — המנוע אינו מנחש בין שתי תשובות שונות.

דוגמאות שנבדקות ברגרסיה:

- `כונן`, `כןנן` ו־`הכונן` מתקבלים בציוד מחשב.
- `כבל h` מושלם ל־`כבל HDMI`, אך `כבל` עצמו נשאר תשובה עצמאית.
- `מחשבת` מושלם ל־`מחשבת ישראל`.
- `דוקו`, `פלפל`, `סולמות`, `אליאס`, `רמי` ו־`מסןק` מתקבלים.

## כללי תוכן

- קטגוריות סגורות אינן מנופחות במספר תשובות מומצאות. לדוגמה, רשימת
  מדינות נשארת מוגבלת לישויות שהוגדרו במדיניות הקטגוריה.
- שם עממי, קיצור, תעתיק או שגיאה נפוצה נשמרים כ־alias של תשובה אחת.
- וריאציות שהן אותה תשובה מקבלות `semantic_group`, כדי שלא יעניקו
  שתי נקודות באותו סיבוב.
- כל כתיבה עוברת audit שמונע normalized collision בין שתי תשובות.
- ה־seed אידמפוטנטי: הרצה חוזרת מוסיפה רק תוכן חסר ואינה מכפילה אותו.

## מקורות מרכזיים

- [משרד החינוך — תחומי דעת](https://pop.education.gov.il/tchumey_daat/)
- [IOC — ענפי אולימפיאדת החורף](https://support.olympics.com/hc/en-gb/articles/43002667811219-What-sports-are-in-the-Olympic-Winter-Games-Milano-Cortina-2026)
- [UN M49 — אזורים ומדינות](https://unstats.un.org/unsd/methodology/m49/)
- [משרד הפנים/השלטון המקומי — רשויות מקומיות](https://www.gov.il/he/Departments/DynamicCollectors/switching-apartments)
- [FDA — קטגוריות מוצרי איפור](https://www.fda.gov/cosmetics/registration-listing-cosmetic-product-facilities-and-products/cosmetic-product-categories-and-codes)
- [NOAA — מיני בעלי חיים ימיים](https://www.fisheries.noaa.gov/find-species)
- [Cleveland Clinic — איברים ומערכות גוף](https://my.clevelandclinic.org/health/articles/organs-in-the-body)
- [O*NET — מאגר מקצועות](https://www.onetonline.org/)
- [FCI — גזעי כלבים](https://www.fci.be/en/Nomenclature/educationGroupe.aspx)
- [אתר הצפרות הישראלי](https://birds.org.il/)
- [Intel — רכיבי מחשב](https://www.intel.com/content/www/us/en/gaming/resources/how-to-build-a-gaming-pc.html)
- [NASA — מערכת השמש](https://science.nasa.gov/solar-system/)

רשימת המקורות המלאה לכל 31 השאלות נשמרת ב־
`backend/app/question_bank_expansion_v3.py` ונבדקת בטסט שמוודא שאין
שאלה ללא מקור ביקורת.
