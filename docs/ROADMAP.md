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

- [x] זמינות קוסמטיקאיות לפי טיפול ושעות עבודה.
- [x] חישוב Slots במרווחים של 15 דקות לפי משך טיפול.
- [x] Redis Lock אטומי עם TTL לפי מטפלת וטיפול ביום המבוקש.
- [x] יצירת תור ב-Transaction עם נעילת שורות ב-MySQL ומניעת Double Booking.
- [x] בדיקות אוטומטיות לבקשות מקבילות ולטיפול ב-Lock שפג.
- [x] בדיקת אינטגרציה ומקביליות מול MySQL מקומי ו-Redis אמיתי ב-Docker.

## שלב 4 — חבילות, אזור אישי ו-Waitlist

- [x] Orders, Packages ו-UserPackages, עם רכישת הדגמה ללא סליקה.
- [x] הורדת יתרה פעם אחת בלבד עם השלמת טיפול מורשית.
- [x] תורים, חבילות, הזמנות ורשימת המתנה באזור האישי.
- [x] הצטרפות לרשימת המתנה והצעת חלון שהתפנה לאחר ביטול תור.

הצעת רשימת המתנה נשמרת ל-15 דקות באזור האישי. טרם נשלחת הודעה חיצונית
והמערכת אינה מעבירה אוטומטית הצעה שפגה ללקוחה הבאה.

## שלב 5 — CMS ותשתית מסירה

- [ ] CRUD מלא לתוכן, צוות, טיפולים ומכשור.
- [ ] Dashboard ודוחות CSV.
- [ ] Alembic migrations ו-seed מלא.
- [ ] Rate limiting, הרחבת cache ו-invalidation.
- [ ] לפחות 10 בדיקות ו-GitHub Actions.
