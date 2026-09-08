# מפת דרכים — SCosmetics

## שלב 1 — חתך אנכי ציבורי

- [x] שלד `client`, `admin`, `server`.
- [x] דף בית RTL.
- [x] API בריאות וקטלוג טיפולים.
- [x] SQLAlchemy, נתוני seed ו-Redis cache.
- [x] Docker Compose ל-Server, MySQL ו-Redis.

## שלב 2 — Authentication ו-RBAC

- [x] מודל משתמשים ותפקידי `Customer`, `Beautician`, `Admin`.
- [x] רישום משתמשת ו-hashing לסיסמה.
- [x] התחברות באמצעות אימייל וסיסמה.
- [x] Access Token ו-Refresh Token.
- [x] Protected Routes והרשאות בצד השרת.
- [x] בדיקות גישה לכל Role.

## שלב 3 — Booking ו-Concurrency

- [ ] זמינות קוסמטיקאיות ומכשור.
- [ ] חישוב Slots לפי משך טיפול.
- [ ] Redis Lock אטומי עם TTL.
- [ ] Transaction ב-MySQL ומניעת Double Booking.
- [ ] בדיקות מקביליות ושחרור Lock שפג.

## שלב 4 — חבילות, אזור אישי ו-Waitlist

- [ ] Orders, Packages ו-UserPackages.
- [ ] הורדת יתרה פעם אחת בלבד עם השלמת טיפול.
- [ ] תורים וחבילות באזור האישי.
- [ ] הצטרפות לרשימת המתנה וטיפול בביטול.

## שלב 5 — CMS ותשתית מסירה

- [ ] CRUD מלא לתוכן, צוות, טיפולים ומכשור.
- [ ] Dashboard ודוחות CSV.
- [ ] Alembic migrations ו-seed מלא.
- [ ] Rate limiting, הרחבת cache ו-invalidation.
- [ ] לפחות 10 בדיקות ו-GitHub Actions.
