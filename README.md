# SCosmetics

מערכת Full Stack לניהול מכון קוסמטיקה פרה-רפואית. הפרויקט מחולק לשלוש אפליקציות עצמאיות בהתאם לאפיון הקורס:

- `client` — אתר הלקוחות הציבורי והאזור האישי (Next.js).
- `admin` — ממשק המנהלת והקוסמטיקאיות (Next.js).
- `server` — REST API, לוגיקה עסקית ונתונים (FastAPI).

## מה כבר עובד

- דף בית עברי, רספונסיבי ובכיוון RTL.
- קטלוג טיפולים הנטען מ-FastAPI, עם נתוני fallback כאשר השרת כבוי.
- API ראשוני: `GET /health` ו-`GET /api/v1/treatments`.
- שמירת טיפולים ב-SQLAlchemy וזריעת נתוני הדגמה אוטומטית.
- Redis cache קצר לקטלוג; המערכת ממשיכה לעבוד גם אם Redis אינו זמין.
- רישום לקוחה עם ולידציה ושמירת password hash באמצעות Argon2.
- התחברות מאובטחת עם JWT Access Token וחידוש באמצעות Refresh Token.
- נתיב משתמש מוגן ותשתית הרשאות לפי Customer, Beautician ו-Admin.
- צפייה בזמינות מטפלות במרווחי 15 דקות לפי משך הטיפול ושעות העבודה.
- יצירת תור ללקוחה מחוברת: בדיקת הסמכה, שעות עבודה והתנגשויות, עם Redis Lock ו-Transaction במסד הנתונים.
- שלד CMS ראשוני עם KPI ותורי היום.
- Docker Compose עבור FastAPI, MySQL ו-Redis.
- בדיקות API בסיסיות עם pytest.

## הפעלה מהירה לפיתוח

פתחו שלושה חלונות Terminal משורש הפרויקט.

### 1. Backend

```powershell
cd server
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

Alembic מנהל את גרסאות מבנה מסד הנתונים. מריצים `upgrade head` לאחר משיכת
שינויים הכוללים migration חדש ולפני הפעלת השרת.

Swagger יהיה זמין בכתובת `http://localhost:8000/docs`.

### 2. אתר הלקוחות

```powershell
cd client
npm run dev
```

האתר יהיה זמין בכתובת `http://localhost:3000`.

### 3. ממשק הניהול

```powershell
cd admin
npm run dev
```

ממשק הניהול יהיה זמין בכתובת `http://localhost:3001`.

## הפעלה עם MySQL ו-Redis

העתיקו את `.env.example` לקובץ `.env`, החליפו את הסיסמאות, ואז הריצו:

```powershell
docker compose up --build
```

אם התקנת Docker המקומית אינה מזהה את פקודת המשנה `compose`, השתמשו בפקודה המקבילה:

```powershell
docker-compose up --build
```

במצב מקומי ללא הגדרת `DATABASE_URL` השרת משתמש במסד SQLite קטן כדי שהתחלת העבודה תהיה פשוטה. בתוך Docker הוא משתמש ב-MySQL לפי דרישות האפיון. אפשר גם להריץ MySQL מקומי ו-Redis ב-Docker כאשר `server/.env` מצביע לשניהם.

`GET /api/v1/appointments/availability` מציג שעות פנויות למשתמש מחובר.
`POST /api/v1/appointments` יוצר תור ללקוחה מחוברת ומחזיר `201`. הבקשה כוללת
`treatment_id`, `beautician_id` ו-`start_time` עם אזור זמן (לדוגמה
`2026-09-14T09:00:00+03:00`). שעה תפוסה מחזירה `409`. יצירת תור דורשת Redis
פעיל; אם הוא אינו זמין, השרת מחזיר `503` ואינו שומר תור. בדיקות היחידה
משתמשות בנעילה מדומה ואינן דורשות Docker.

## בדיקות

```powershell
cd server
.\.venv\Scripts\python.exe -m pytest
```

בדיקת מקביליות מול MySQL ו-Redis אמיתיים אינה חלק מ-`pytest` הרגיל. הפעילו
את שני השירותים ואת שרת ה-API בפורט `8004`, ודאו שקובץ `server/.env` מצביע
אליהם, ואז הריצו מתוך `server`:

```powershell
.\.venv\Scripts\python.exe -m scripts.check_concurrent_booking
```

הסקריפט יוצר לקוחה זמנית, מאתר שעה שבה שתי מטפלות פנויות לאותו טיפול,
ושולח שתי בקשות הזמנה יחד. התוצאה התקינה היא `201` ו-`409`, עם תור אחד בלבד
ב-MySQL. בסיום הוא מוחק רק את הלקוחה והתור שיצר. הוא מסרב לרוץ מול שרת או
מסד נתונים מרוחקים.

```powershell
cd client
npm run lint
npm run build
```

```powershell
cd admin
npm run lint
npm run build
```

פירוט אבני הדרך נמצא ב-[docs/ROADMAP.md](docs/ROADMAP.md).
