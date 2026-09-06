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

במצב מקומי ללא Docker השרת משתמש במסד SQLite קטן כדי שהתחלת העבודה תהיה פשוטה. בתוך Docker הוא משתמש ב-MySQL לפי דרישות האפיון.

## בדיקות

```powershell
cd server
.\.venv\Scripts\python.exe -m pytest
```

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
