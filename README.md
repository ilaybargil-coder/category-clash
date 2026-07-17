# קרב קטגוריות 🏆

משחק טריוויה תחרותי לשני שחקנים בזמן אמת: מקבלים שאלת קטגוריה ("כתבו שמות של פירות טרופיים"), עונים בתורות, ומי שנתקע כשהטיימר מתאפס — מפסיד את הסיבוב. Best of 3.

**סטטוס:** ‏Phase 1 הושלם; Milestone B כולל בטא חינמית ו-Supabase Auth על Cloudflare Workers + Render Free + Supabase Free.

## סטאק

| שכבה | טכנולוגיה |
|---|---|
| Frontend | Next.js + TypeScript + React + Tailwind CSS |
| Backend | Python + FastAPI + SQLAlchemy (async) + Alembic |
| DB | PostgreSQL |
| Real-time | WebSockets |
| Live room state | זיכרון של תהליך Backend יחיד |

## הפעלה מקומית

דרישה מקדימה: [Docker Desktop](https://www.docker.com/products/docker-desktop/).

```bash
cd category-clash
cp .env.example .env        # אופציונלי — יש ברירות מחדל לכל דבר
docker compose up --build
```

זה מרים PostgreSQL, ‏Backend (כולל הרצת מיגרציות ו-seed אוטומטית) ו-Frontend.

- משחק: http://localhost:3000
- API: ‏http://localhost:8000/docs

### איך משחקים (סימולציה של שני שחקנים)

1. פתחו את http://localhost:3000 בחלון רגיל **ובחלון גלישה בסתר** (או שני דפדפנים).
2. בחלון אחד בחרו את **דנה**, בשני את **עומר** (משתמשי דמו, סיסמה `demo1234` — מוזנת אוטומטית).
3. בחלון הראשון לחצו "משחק חדש" — יוצג קוד חדר.
4. בחלון השני הזינו את הקוד ולחצו "הצטרפות".
5. המשחק מתחיל אוטומטית ברגע ששני השחקנים בחדר.

### הרצה מ-PyCharm (בלי Docker)

הפרויקט מגיע עם Run Configurations מוכנות (תיקיית `.idea`). ב-PyCharm: **File → Open** ובחרו את תיקיית `category-clash` (השורש, לא backend). בפינה למעלה ליד כפתור ה-Run יופיעו:

| קונפיגורציה | מה היא עושה |
|---|---|
| **START HERE - Full Stack** | מפעילה PostgreSQL, מריצה migrations ו-seed, ואז מרימה Backend ו-Frontend — זה הכפתור היומיומי |
| Prepare local services + DB | מכינה רק את התשתיות ומסד הנתונים; רצה אוטומטית לפני ה-Backend |
| Backend (uvicorn) | שרת FastAPI על 8000 עם reload |
| Frontend (npm dev) | ‏Next.js על 3000 |
| Backend tests (pytest) | כל בדיקות המנוע עם ה-runner של PyCharm |
| Seed DB | מזריע משתמשי דמו ושאלות (אידמפוטנטי) |

הקונפיגורציות מצביעות ישירות על `backend/.venv`, כך שהן עובדות גם לפני הגדרת אינטרפרטר. כדי שגם השלמות הקוד יעבדו: **Settings → Project → Python Interpreter → Add Interpreter → Existing** ובחרו `backend/.venv/bin/python`.

### הרצה בלי Docker (טרמינל)

```bash
# תשתית: PostgreSQL על 5432 (user/pass/db = game)

# Backend
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
alembic upgrade head && python -m app.seed
uvicorn app.main:app --reload

# Frontend (טרמינל נפרד)
cd frontend
npm install
npm run dev
```

## בדיקות

המדריך המחייב להוספת שאלה, aliases, תיקוני כתיב, מקורות, טסטים ופריסה נמצא
ב־[`docs/ADDING_A_QUESTION.md`](docs/ADDING_A_QUESTION.md).

בדיקות היחידה מכסות את מנוע המשחק (תורות, טיימרים, Best of 3, ניתוקים, מרוצי־זמן), idempotency של פקודות, פרוטוקול WebSocket ואת ולידציית התשובות (נרמול עברית, aliases, כפילויות, semantic groups):

```bash
cd backend
.venv/bin/python -m pytest tests/ -v
.venv/bin/ruff check app tests
.venv/bin/ruff format --check app tests
.venv/bin/mypy app
# או בתוך Docker:
docker compose run --rm backend pytest tests/ -v
```

בדיקת האינטגרציה מול PostgreSQL כבויה כברירת מחדל כדי שטסטים רגילים יישארו עצמאיים מתשתית. כשה-DB המקומי פועל:

```bash
cd backend
RUN_DB_INTEGRATION=1 .venv/bin/python -m pytest tests/test_db_integration.py -v
```

בדיקות ה-frontend (vitest) מכסות את ה-reducer של אירועי המשחק — דדופליקציה לפי `submission_id`, ‏`state_sync` שמחליף ולא צובר, וניקוי הפיד בין סיבובים:

```bash
cd frontend
npm test
npm run lint
npx tsc --noEmit
npm run build
```

אחרי שינוי במודלי פרוטוקול ה-WebSocket, מייצרים מחדש את טיפוסי ה-TypeScript:

```bash
backend/.venv/bin/python backend/scripts/generate_protocol_types.py
```

## קונפיגורציה

כל קבועי המשחק ב-[backend/app/config.py](backend/app/config.py), ניתנים לדריסה ב-env (ראו [.env.example](.env.example)):

| קבוע | ברירת מחדל | משמעות |
|---|---|---|
| `TURN_SECONDS` | 15 | זמן לכל תור |
| `PREVIEW_SECONDS` | 4 | הצגת השאלה לפני תחילת הסיבוב |
| `INTERMISSION_SECONDS` | 4 | מסך תוצאת סיבוב בין סיבובים |
| `ROUNDS_TO_WIN` | 2 | ‏Best of 3 |
| `MAX_ANSWER_LENGTH` | 60 | אורך תשובה מקסימלי |
| `WEBSOCKET_SEND_TIMEOUT_SECONDS` | 2 | timeout לכתיבה ללקוח איטי, כדי שלא יחסום broadcast |
| `DISCONNECT_FORFEIT_SECONDS` | 60 | זמן חסד לחזרה אחרי ניתוק לפני הפסד טכני |
| `INVITE_TTL_SECONDS` | 90 | (שלב 2) תוקף הזמנה למשחק |
| `SWAP_QUESTION_COST_COINS` | 50 | (שלב 3) עלות החלפת שאלה |
| `FUZZY_MATCHING_ENABLED` | true | התאמה שמרנית לשגיאת הקלדה אחת, עם הגנת עמימות |
| `UNIQUE_PREFIX_MATCHING_ENABLED` | true | השלמה רק כאשר הקידומת מצביעה על תשובה אחת בשאלה הנוכחית |
| `UNIQUE_PREFIX_MIN_LENGTH` | 3 | מספר תווים מינימלי להפעלת השלמה |
| `DEFINITE_ARTICLE_MATCHING_ENABLED` | true | קבלת ה״א הידיעה כאשר הצורה בלעדיה היא תשובה מדויקת |

לפרטי הארכיטקטורה המלאים (State Machine, סכמת DB, חלוקת PostgreSQL/Redis, מקרי קצה): [ARCHITECTURE.md](ARCHITECTURE.md). דו״ח הביקורת של Milestone A נמצא ב-[docs/PHASE1_AUDIT.md](docs/PHASE1_AUDIT.md).

## פריסת בטא חינמית

קובצי הפריסה מוכנים ב-`render.yaml`, ‏`frontend/wrangler.jsonc` ו-`frontend/open-next.config.ts`. אין secrets ב-Git; את כתובות השירותים והסודות מגדירים ב-Dashboards. לפרטים: [docs/FREE_DEPLOYMENT.md](docs/FREE_DEPLOYMENT.md).

- Backend liveness: `/health`
- Backend readiness מול PostgreSQL והגדרות authentication: `/ready`
- Render משתמש ב-`0.0.0.0:$PORT` וב-Uvicorn worker יחיד.
- ה-frontend משתמש ב-HTTPS/WSS בפרודקשן ומעיר את Render ברקע בלי לחסום את הממשק.
- גרסת הבטא החינמית מאבדת משחק פעיל אם תהליך Render מופעל מחדש.

## מפת דרכים

- **Phase 1 — ליבת המשחק** ✅ (הושלם)
- **Phase 2A — הרשמה והתחברות עם session מתמשך** ✅
- **Phase 2B — חברים, presence והזמנות עם טיימר 90 שניות**
- **Phase 3A — מאגר מורחב ו-fuzzy matching שמרני** ✅
- **Phase 3B — החלפת שאלה במטבעות ומסך סקירת תשובות שנדחו**
- **Phase 4 — ממשק Admin**
- **Phase 5 — ליטוש: אנימציות, reconnect משופר, אבטחה, ביצועים**
