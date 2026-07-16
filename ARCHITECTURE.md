# ארכיטקטורה — קרב קטגוריות

## עקרון־על: השרת הוא המקור היחיד לאמת

ה-frontend לעולם לא מחליט כלום: לא זמן, לא תור, לא תקינות תשובה, לא מנצח. הוא שולח פעולות (`submit_answer`) ומרנדר את המצב שהשרת משדר. הטיימר שמוצג למשתמש הוא רינדור מקומי של deadline שהשרת קבע (כולל פיצוי הפרשי שעון דרך `server_now_ms` שנשלח בכל אירוע) — אבל ההכרעה אם הזמן נגמר נעשית אך ורק בשרת.

## רכיבים

```
Browser (Next.js)
   │  REST: login, create/join room          │  WebSocket: submit_answer
   ▼                                          ▼
FastAPI ──────────────────────────────────────────────
   │   RoomManager (in-memory, per-process)
   │      └── GameRoom  ←— asyncio.Lock, generation-guarded timers
   │             ├── QuestionProvider ──→ PostgreSQL (שאלות + תשובות)
   │             └── ResultSink ────────→ PostgreSQL (היסטוריה, סטטיסטיקות)
   │
   └── Redis (שלב 2+: presence, הזמנות TTL, pub/sub)
```

### GameRoom — מנוע המשחק

- כל מוטציה של מצב עוברת דרך `asyncio.Lock` אחד לחדר ⇒ שתי תשובות שמגיעות "יחד", או תשובה שמתחרה בטיימר, מוכרעות בסדר דטרמיניסטי.
- **טיימרים עם generation guard**: כל חימוש טיימר מקדם מונה. משימת טיימר שמתעוררת בודקת שהמונה לא השתנה — אם תשובה תקינה עברה תור בינתיים, הטיימר הישן מזהה שהוא "פג תוקף" ולא עושה כלום.
- **מרוץ תשובה/טיימר**: תשובה שמגיעה אחרי שה-deadline עבר (אבל לפני שמשימת הטיימר הספיקה לרוץ) מקבלת `TIME_EXPIRED` והסיבוב מוכרע מיידית — לא ייתכן מצב שבו תשובה "מנצחת את השעון" בזכות עומס.
- המנוע נקי מ-FastAPI ומ-DB (הזרקת `QuestionProvider` ו-`ResultSink`) ⇒ כל לוגיקת המשחק נבדקת ביחידה בלי תשתית.

## State Machine

```
                    create room
                        │
              WAITING_FOR_PLAYERS ◄──── שחקן עוזב לפני שהתחיל
                        │  שני שחקנים בחדר
                        ▼
              ┌── QUESTION_PREVIEW  (PREVIEW_SECONDS להצגת השאלה)
              │         │
              │         ▼
              │   ROUND_ACTIVE ◄────┐
              │     │ │ │           │ תשובה VALID: התור עובר,
              │     │ │ └───────────┘ טיימר חדש ליריב
              │     │ │
              │     │ │ INVALID / DUPLICATE / TOO_SIMILAR:
              │     │ │ התור נשאר, הטיימר ממשיך לרדת
              │     │ │
              │     │ ▼ הטיימר הגיע ל-0 (או תשובה אחרי ה-deadline)
              │   ROUND_FINISHED — נקודה ליריב, מסך ביניים
              │     │           │
              │     │           │ יש 2 נצחונות
   סיבוב הבא  │     │           ▼
   (מחליפים   └─────┘      MATCH_FINISHED — עדכון wins/losses
    פותח)
                        
   בכל שלב פעיל: ניתוק ⇒ טיימר התור ממשיך כרגיל; אם השחקן לא חזר
   תוך DISCONNECT_FORFEIT_SECONDS ⇒ MATCH_FINISHED (FORFEIT ליריב).
   רענון דף ⇒ reconnect ⇒ state_sync מלא וממשיכים מאותה נקודה.
```

מצבי הזמנות (INVITE_PENDING / ACCEPTED / DECLINED / EXPIRED) שייכים לשלב 2 וינוהלו ב-Redis עם TTL של 90 שניות.

### פרוטוקול WebSocket

שרת → לקוח: `state_sync` (בכל התחברות), `player_joined/left/disconnected/reconnected`, `round_started`, `round_active`, `answer_result`, `turn_changed` (מוטמע בתוך `answer_result`), `turn_timeout`, `round_finished`, `match_finished`, `action_rejected`.
לקוח → שרת: `submit_answer {text, client_command_id}`, `ping`.

`client_command_id` הוא UUID שהלקוח יוצר פעם אחת לפעולה לוגית. שליחה חוזרת אחרי double-click, reconnect או retry משתמשת באותו UUID, והשרת מחזיר את התוצאה שכבר חושבה בלי אירוע או כתיבת DB נוספים.

כל הודעת שרת משתמשת במעטפת גרסה 1 ונושאת `event_id`, ‏`event_type`, ‏`protocol_version`, ‏`server_timestamp`, ‏`server_now_ms`, ‏`match_id`, ‏`seq` ו-`payload`. בתקופת המעבר שדות האירוע נמצאים גם ברמה העליונה כדי לשמור תאימות. `seq` עולה הוא סדר האירועים הסמכותי; ה-reducer מתעלם מאירועים ישנים ו-`state_sync` מחליף את המצב המקומי.

המודלים בצד השרת מוגדרים ב-`backend/app/protocol.py`. טיפוסי TypeScript נוצרים מהם אל `frontend/src/lib/protocol.generated.ts` באמצעות `backend/scripts/generate_protocol_types.py`, ובדיקה אוטומטית נכשלת אם הקובץ שנוצר אינו מעודכן.

## סכמת בסיס הנתונים (PostgreSQL)

```
users              questions             approved_answers        answer_aliases
─────              ─────────             ────────────────        ──────────────
id                 id                    id                      id
username (uniq)    text (uniq)           question_id ─► questions id ─► approved_answers
display_name       is_active             canonical               alias
password_hash      created_at            semantic_group
coins                                    notes
wins                                     is_active
losses
created_at

matches                       rounds                      submitted_answers
───────                       ──────                      ─────────────────
id                            id                          id
code                          match_id ─► matches         round_id ─► rounds
player1_id ─► users           round_no                    user_id ─► users
player2_id ─► users           question_id ─► questions    raw_text
winner_id ─► users            starter_user_id             normalized_text
score_p1 / score_p2           winner_user_id              status (VALID/INVALID/…)
status                        end_reason                  matched_answer_id
                                                          submission_id (uniq, not null)
                                                          client_command_id (uniq, legacy nullable)
created_at / finished_at      created_at                  created_at
```

`submitted_answers` שומרת **כל** ניסיון, כולל דחויים — זה המזין של מסך "תשובות שנדחו" ב-Admin (שלב 4) ושל כריית תשובות חדשות למאגר.

שלב 2 יוסיף: `friendships`, `friend_requests` (ההזמנות למשחק עצמן חיות ב-Redis בלבד כי הן בנות 90 שניות).

## מה ב-PostgreSQL ומה ב-Redis

| נתון | היכן | למה |
|---|---|---|
| משתמשים, שאלות, תשובות מאושרות, aliases | PostgreSQL | נתוני אמת קבועים |
| היסטוריית משחקים, סיבובים, כל תשובה שהוגשה | PostgreSQL | נדרש לתמיד (סטטיסטיקות, Admin) |
| מצב חדר חי (תור, טיימר, ניקוד ביניים) | **זיכרון התהליך** (Phase 1) | מהירות ופשטות; שרת יחיד |
| presence (מי מחובר) | Redis (שלב 2) | נתון נדיף עם TTL טבעי |
| הזמנות למשחק (90 שניות) | Redis (שלב 2) | TTL מובנה, אין טעם ב-DB |
| pub/sub בין שרתים | Redis (בעת scale-out) | כששני שחקנים מחוברים לשרתים שונים |

**החלטה מפורשת:** ב-Phase 1 מצב החדרים חי בזיכרון של תהליך backend יחיד ולא ב-Redis. זה שומר את המנוע פשוט, מהיר ואטומי (lock אחד). המחיר: הפעלה מחדש של השרת מפילה משחקים חיים, ואי אפשר להריץ כמה instances. שתי המגבלות מקובלות ל-MVP ומטופלות בשלב 5 (serialization של מצב חדר ל-Redis).

## מנגנון בדיקת תשובות

נרמול (סדר פעולות): NFKC → lowercase → הסרת ניקוד → קיפול אותיות סופיות (ך→כ …) → הסרת גרש/גרשיים/מירכאות (כך ש"ליצ'י"="ליצי") → פיסוק אחר הופך לרווח (כך ש"סוסון-ים"="סוסון ים") → כיווץ רווחים → trim.

התאמה: המילון של כל שאלה נטען פעם אחת בתחילת סיבוב (canonical + כל alias ⇒ אותו answer_id). ואז:

1. הצורה המנורמלת לא במילון ⇒ `INVALID`
2. answer_id כבר שומש בסיבוב ⇒ `DUPLICATE` (כולל alias אחר של אותה תשובה)
3. ה-semantic_group כבר שומש ⇒ `TOO_SIMILAR` (תשובה אחרת עם אותה משמעות)
4. אחרת ⇒ `VALID`

אין קריאת LLM בזמן אמת. Fuzzy matching (Levenshtein עם threshold זהיר, רק למילים ארוכות) מוכן כקונפיג ל-שלב 3 — כבוי כברירת מחדל כי עדיף לדחות תשובה גבולית מלקבל שגויה.

## מקרי קצה מטופלים (מעבר לרשימה שלך)

- **שני סוקטים לאותו משתמש** (שני טאבים): השחקן נחשב מנותק רק כשהסוקט האחרון שלו נסגר.
- **טיימר ישן שמתעורר אחרי מעבר תור**: generation guard — נבדק בטסט ייעודי.
- **double-submit מהיר**: כל פעולה לוגית מקבלת `client_command_id` מסוג UUID בצד הלקוח, וכל ניסיון שנשמר מקבל `submission_id` ייחודי מהשרת. השרת שומר cache של `(user_id, client_command_id)` — retry של אותה פעולה (double-click, שליחה חוזרת או reconnect) מחזיר את אותו verdict בלי רשומה, אירוע או כתיבת DB נוספים. גם דחייה זמנית נשמרת, ולכן retry מאוחר לא יכול להפוך בטעות להגשה חדשה. נבדק בטסטים כולל מרוץ concurrent.
- **אירוע שמגיע פעמיים ללקוח** (סוקט כפול, replay אחרי reconnect): ה-reducer בצד הלקוח מזהה `submission_id` שכבר הוצג ולא מוסיף בועה שנייה; `state_sync` תמיד מחליף את המצב ולא מצטבר. ל-`submitted_answers` יש unique constraint על `submission_id` — גם ברמת ה-DB לא ייתכנו שתי רשומות לאותה הגשה.
- **נגמרו השאלות במאגר**: החדר עובר ל-ABANDONED עם אירוע שגיאה (במקום קריסה).
- **קוד חדר מנחש**: אלפבית ללא תווים דו-משמעיים (בלי 0/O, 1/I/L), ‏5 תווים.
- **הודעת JSON שבורה / סוג לא מוכר**: נענית ב-error מבלי להפיל את החיבור.
- **חדר לא קיים או token לא תקין**: ה-WebSocket מתקבל ואז נסגר בקוד טרמינלי (`4404`/`4401`), כך שהדפדפן לא מפרש את המצב כתקלה זמנית ולא נכנס ללולאת reconnect.
- **לקוח איטי/תקוע**: כל כתיבה ל-WebSocket מוגבלת בזמן ונשלחת במקביל לשאר הלקוחות, כך שסוקט אחד לא חוסם את החדר כולו.
- **כשל בכתיבת DB באמצע משחק**: ה-ResultSink עטוף — המשחק ממשיך גם אם הפרסיסטנס נכשל (נרשם ללוג).

## מקרי קצה מודעים־ולא־מטופלים (בכוונה, ל-Phase 1)

- restart של השרת מוחק משחקים חיים (ראו החלטת Redis למעלה).
- אין rate-limiting על הגשות (שלב 5 — אבטחה).
- refresh token אמיתי (כרגע JWT קצר בלבד; שלב 2).
- שחקן ששלח תשובה מילי־שניות לפני הדדליין אבל הרשת איחרה — נדחה. אפשר בעתיד "חסד רשת" של ~200ms כקונפיג.
