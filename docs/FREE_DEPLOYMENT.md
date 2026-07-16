# Free beta deployment

היעד המאושר ל-Milestone B:

- Cloudflare Workers Free — Next.js/OpenNext frontend.
- Render Free Web Service — FastAPI/Uvicorn, instance יחיד ו-worker יחיד.
- Supabase Free — PostgreSQL.

אין Redis, ‏Upstash או Durable Objects. מצב חדר חי נשמר בזיכרון של תהליך Render ולכן restart או spin-down מפילים משחק פעיל. ה-frontend מציג מסך התעוררות ומבצע polling ל-`/health`; בזמן חיבור פעיל הוא שולח heartbeat דרך ה-WebSocket.

## Secrets

אין לשמור ערכים אמיתיים בקבצי Git. מגדירים אותם רק ב-Dashboard של השירות המתאים:

- Render: `DATABASE_URL`, ‏`JWT_SECRET`, ‏`AUTH_MODE`, ‏`SUPABASE_URL`,
  ‏`SUPABASE_PUBLISHABLE_KEY`, ‏`CORS_ORIGINS`, ‏`WEBSOCKET_ORIGINS`.
- Cloudflare build variables: `NEXT_PUBLIC_API_URL`, ‏`NEXT_PUBLIC_WS_URL`,
  ‏`NEXT_PUBLIC_AUTH_MODE`, ‏`NEXT_PUBLIC_SUPABASE_URL`,
  ‏`NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY`.

ה-`publishable key` של Supabase מיועד לשימוש בדפדפן ואינו secret. אסור להכניס
ל-frontend את `service_role`, ‏secret key, סיסמת מסד הנתונים או `DATABASE_URL`.

`DATABASE_URL` צריך להיות Supabase Session Pooler על פורט 5432. הקוד מקבל URL שמתחיל ב-`postgresql://` וממיר אותו אוטומטית ל-`postgresql+asyncpg://`. אין להשתמש ב-Transaction Pooler על פורט 6543 עם הגדרות ה-runtime הנוכחיות.

Migration `0004` מפעיל RLS ללא policies ומסיר הרשאות Data API מהתפקידים `anon` ו-`authenticated`. ה-backend ממשיך לעבוד דרך החיבור הישיר כבעל הסכמה, אך הדפדפן אינו יכול לעקוף אותו ולגשת לטבלאות דרך Supabase Data API. Migration `0005` מוסיף ל-`users` את `auth_user_id`, שמקשר את פרופיל המשחק למשתמש ב-Supabase Auth בלי לשנות את מזהי המשתמשים של מנוע המשחק.

## Supabase Auth

בבטא משתמשים ב-Email + Password של Supabase Auth. ה-session נשמר ומתרענן
אוטומטית בדפדפן, ולכן אין צורך לבחור משתמש מחדש בכל כניסה לאתר. FastAPI מקבל
את access token, מאמת אותו מול Supabase, ואז טוען את פרופיל המשחק הפנימי.

הגדרות Supabase הנדרשות:

1. ב-Authentication → Providers משאירים Email פעיל.
2. לבטא סגורה ללא SMTP פרטי מומלץ לבטל זמנית Confirm email. אם הוא נשאר פעיל,
   המשתמש חייב ללחוץ על הקישור במייל לפני הכניסה, ומגבלת המיילים המובנית נמוכה.
3. ב-Authentication → URL Configuration מגדירים Site URL לכתובת Cloudflare.
4. מעתיקים מ-Project Settings → API את Project URL ואת ה-publishable key בלבד.

ערכי production ב-Render:

```text
AUTH_MODE=supabase
SUPABASE_URL=https://<project-ref>.supabase.co
SUPABASE_PUBLISHABLE_KEY=<sb_publishable_...>
```

ערכי build ב-Cloudflare:

```text
NEXT_PUBLIC_AUTH_MODE=supabase
NEXT_PUBLIC_SUPABASE_URL=https://<project-ref>.supabase.co
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=<sb_publishable_...>
```

לפיתוח מקומי נשארים עם `AUTH_MODE=demo` ו-`NEXT_PUBLIC_AUTH_MODE=demo`, כך
שהרצת Full Stack ב-PyCharm ממשיכה לעבוד עם דנה ועומר ללא תלות באינטרנט.

## Render startup

`render.yaml` מגדיר `plan: free`, ‏root directory של `backend`, health check ב-`/health` וסקריפט הפעלה יחיד. בכל cold start הסקריפט מריץ:

1. `alembic upgrade head`
2. seed idempotent
3. Uvicorn על `0.0.0.0:$PORT`, עם `--workers 1`

ה-seed מוסיף רק משתמשי דמו ושאלות חסרים. unique constraints וטסט אינטגרציה שמריץ אותו פעמיים מונעים הכפלה.

## URLs

לאחר יצירת Render:

```text
NEXT_PUBLIC_API_URL=https://<render-service>.onrender.com
NEXT_PUBLIC_WS_URL=wss://<render-service>.onrender.com
```

לאחר יצירת Cloudflare:

```text
CORS_ORIGINS=https://<cloudflare-worker>.workers.dev
WEBSOCKET_ORIGINS=https://<cloudflare-worker>.workers.dev
WEBSOCKET_ALLOW_MISSING_ORIGIN=false
```

## סדר מעבר בטוח מ-demo להרשמה אמיתית

1. דוחפים את הקוד וממתינים ש-Render יריץ את migration `0005` כאשר האתר עדיין ב-demo.
2. מגדירים Supabase Auth ואת משתני Render, ואז מבצעים deploy מחדש ובודקים `/ready`.
3. מגדירים את משתני Cloudflare ובונים מחדש את ה-frontend.
4. נרשמים עם חשבון בדיקה, מרעננים את הדף, מתנתקים ומתחברים מחדש.
5. פותחים שני דפדפנים עם שני חשבונות ובודקים משחק מלא דרך קוד חדר.
