# Milestone A — ביקורת Phase 1 ותיקון כפילות תשובות

תאריך ביקורת: 16 ביולי 2026

## תמונת מצב

הפרויקט הוא monorepo עם Next.js/React/Tailwind בצד הלקוח ו-FastAPI/SQLAlchemy/Alembic בצד השרת. השרת הוא authoritative: `GameRoom` מנהל את ה-state machine תחת `asyncio.Lock`, טיימרים מוגנים ב-generation counter, ו-`RoomManager` מחזיק חדרים וחיבורי WebSocket בזיכרון התהליך. PostgreSQL שומר תוכן ותוצאות; Redis מותקן אך שמור ל-presence, הזמנות ו-scale-out בשלבים הבאים.

Phase 1 עובד מקצה לקצה בתצורת שרת יחיד. מגבלה מכוונת: restart מוחק חדרים פעילים ואי אפשר להפעיל כמה workers בלי להעביר מצב ו-fan-out ל-Redis.

## גורם השורש לכפילות

לפני התיקון, זהות של ניסיון לא הייתה חוזה end-to-end יציב. retry של אותה פעולת משתמש יכול היה להיכנס שוב למנוע, ו-replay או `state_sync` בצד הלקוח יכול היה להצטבר לפיד המקומי. בנוסף, לא היה מזהה פקודה ייחודי שנשמר עד שכבת ה-DB.

התיקון מפריד בין שתי זהויות:

- `client_command_id`: UUID שנוצר פעם אחת לפעולה לוגית בצד הלקוח ומשמש לכל retry.
- `submission_id`: מזהה ייחודי שהשרת יוצר לניסיון שנרשם ומופיע באירוע, ב-snapshot וב-DB.

המנוע שומר תוצאה לפי `(user_id, client_command_id)` תחת אותו lock של החדר. retry, גם concurrent, אינו יוצר אירוע, היסטוריה או כתיבת DB נוספת. ה-frontend משדר מחדש רק פקודה pending עם אותו UUID, מסיר אותה כשהגיעה תשובה, מסנן אירועים ישנים לפי `seq`, מסיר כפילויות לפי `submission_id`, ו-`state_sync` מחליף מצב במקום לצבור אותו. ב-PostgreSQL קיימים unique constraints לשני המזהים הרלוונטיים.

## שינויים קריטיים נוספים

- פקודות WebSocket עוברות ולידציה ב-Pydantic; UUID לא תקין, טקסט ארוך או סוג לא מוכר נדחים בבטחה.
- אירועי השרת משתמשים במעטפת פרוטוקול v1 עם metadata וסדר `seq` סמכותי.
- טיפוסי TypeScript נוצרים ממודלי Python, וטסט מונע drift בין הצדדים.
- broadcast ללקוחות מתבצע במקביל עם timeout ו-lock נפרד לכל socket.
- שגיאות token/room נסגרות בקודים `4401`/`4404` שהדפדפן מבין כטרמינליים; כך נמנעת לולאת reconnect אינסופית.
- מיגרציה משלימה ערכי `submission_id` ישנים, הופכת אותם ל-`NOT NULL`, ומוסיפה `client_command_id` ייחודי.
- סקריפטים ו-Run Configurations מאפשרים להפעיל את כל ה-stack מתוך PyCharm בלי Docker.

## כיסוי ואימות

הכיסוי האוטומטי כולל:

- retry רגיל ו-concurrent של אותה פקודה.
- אותה תשובה בשתי פקודות שונות.
- דחייה שנשארת דחייה גם אם ה-retry מגיע מאוחר יותר.
- אירוע, history וקריאת DB יחידים לאותה הגשה.
- snapshot עם מזהים ודדופליקציה ב-reducer.
- remount, reconnect, retry של pending command וקודי close טרמינליים ב-hook.
- WebSocket protocol, JSON/פקודה פגומים ויצירת טיפוסים משותפים.
- אינטגרציה אמיתית מול PostgreSQL שמוודאת שורה אחת בלבד.

בדיקה ידנית בוצעה בשני clients: תשובה אחת הופיעה כבועה אחת בשניהם, נשארה אחת אחרי reload, ו-double-click יצר ניסיון יחיד. השאילתה למסד החזירה שורה אחת לכל `submission_id` ו-`client_command_id`.

## פערים וחוב טכני שנותרו

- authentication הוא demo JWT וה-token נמצא כרגע ב-query של כתובת ה-WebSocket, ולכן עשוי להופיע ב-access logs.
- אין rate limiting או בדיקת Origin ל-WebSocket.
- כשל persistence נרשם והמשחק ממשיך; אין outbox/retry durable ולכן אירוע עלול לא להישמר במקרה של תקלה זמנית ב-DB.
- מצב חדרים הוא in-memory ותומך ב-backend worker יחיד בלבד.
- observability עדיין בסיסי: אין metrics, tracing, readiness עמוק או correlation IDs מלאים.
- גרסת Next.js 14 הנוכחית מופיעה עם advisories ב-`npm audit`; שדרוג major דורש בדיקת תאימות ונשמר למיילסטון הבא במקום לבצע `--force` מסוכן.
- ספריית TestClient מפיקה אזהרת deprecation אחת דרך שכבת התאימות של Starlette/httpx.

## תוכנית מומלצת ל-Milestone B

1. לחזק authentication ולהעביר credential מחוץ ל-query, עם Origin allowlist ו-rate limits.
2. לשדרג Next.js והתלויות בבקרת תאימות ולסגור את advisories.
3. להוסיף structured logging, health/readiness, metrics ו-correlation IDs.
4. להגדיר מדיניות persistence אמינה (outbox/retry) לפני scale-out.
5. להעביר presence/fan-out ומצב נדרש ל-Redis לפני הוספת worker נוסף.

Milestone B לא התחיל במסגרת מסמך זה.
