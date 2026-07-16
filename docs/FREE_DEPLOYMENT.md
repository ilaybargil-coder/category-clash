# Free beta deployment

היעד המאושר ל-Milestone B:

- Cloudflare Workers Free — Next.js/OpenNext frontend.
- Render Free Web Service — FastAPI/Uvicorn, instance יחיד ו-worker יחיד.
- Supabase Free — PostgreSQL.

אין Redis, ‏Upstash או Durable Objects. מצב חדר חי נשמר בזיכרון של תהליך Render ולכן restart או spin-down מפילים משחק פעיל. ה-frontend מציג מסך התעוררות ומבצע polling ל-`/health`; בזמן חיבור פעיל הוא שולח heartbeat דרך ה-WebSocket.

## Secrets

אין לשמור ערכים אמיתיים בקבצי Git. מגדירים אותם רק ב-Dashboard של השירות המתאים:

- Render: `DATABASE_URL`, ‏`JWT_SECRET`, ‏`CORS_ORIGINS`, ‏`WEBSOCKET_ORIGINS`.
- Cloudflare build variables: `NEXT_PUBLIC_API_URL`, ‏`NEXT_PUBLIC_WS_URL`.

`DATABASE_URL` צריך להיות Supabase Session Pooler על פורט 5432. הקוד מקבל URL שמתחיל ב-`postgresql://` וממיר אותו אוטומטית ל-`postgresql+asyncpg://`. אין להשתמש ב-Transaction Pooler על פורט 6543 עם הגדרות ה-runtime הנוכחיות.

Migration `0004` מפעיל RLS ללא policies ומסיר הרשאות Data API מהתפקידים `anon` ו-`authenticated`. ה-backend ממשיך לעבוד דרך החיבור הישיר כבעל הסכמה, אך הדפדפן אינו יכול לעקוף אותו ולגשת לטבלאות דרך Supabase Data API.

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

רשימת ההקמה המפורטת נמסרת בצ'קפוינט של Milestone B לאחר שכל הבדיקות עוברות.
