from datetime import time
from decimal import Decimal
from secrets import token_urlsafe

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.beautician import Beautician, BeauticianWorkingHours
from app.models.package import Package
from app.models.site import Equipment, SiteContent, TeamMember
from app.models.treatment import Treatment
from app.models.user import User, UserRole

SEED_TREATMENTS = (
    {
        "name": "טיפול זוהר לפנים",
        "category": "טיפולי פנים",
        "description": "ניקוי עמוק, הזנה ולחות למראה רענן ואחיד.",
        "duration_minutes": 60,
        "price": Decimal("420.00"),
        "accent": "sage",
    },
    {
        "name": "אנטי אייג׳ינג מתקדם",
        "category": "אנטי אייג׳ינג",
        "description": "פרוטוקול מותאם לחידוש העור, מיצוק ושיפור המרקם.",
        "duration_minutes": 75,
        "price": Decimal("590.00"),
        "accent": "sand",
    },
    {
        "name": "הסרת שיער בלייזר",
        "category": "טיפולי לייזר",
        "description": "טיפול ממוקד בטכנולוגיה מתקדמת ובתוכנית אישית.",
        "duration_minutes": 45,
        "price": Decimal("280.00"),
        "accent": "rose",
    },
)


def seed_treatments(session: Session) -> None:
    if session.scalar(select(Treatment.id).limit(1)) is not None:
        return

    session.add_all(Treatment(**treatment) for treatment in SEED_TREATMENTS)
    session.commit()


def seed_booking_demo(session: Session) -> None:
    if session.scalar(select(Beautician.id).limit(1)) is not None:
        return

    treatments = list(
        session.scalars(
            select(Treatment)
            .where(Treatment.active.is_(True))
            .order_by(Treatment.id)
        ).all()
    )
    if not treatments:
        return

    sigal_user = User(
        first_name="סיגל",
        last_name="לוי",
        email="sigal@scosmetics.local",
        phone="050-0000001",
        password_hash=hash_password(token_urlsafe(32)),
        role=UserRole.BEAUTICIAN,
    )
    demo_user = User(
        first_name="מטפלת",
        last_name="לדוגמה",
        email="therapist1@scosmetics.local",
        phone="050-0000002",
        password_hash=hash_password(token_urlsafe(32)),
        role=UserRole.BEAUTICIAN,
    )

    workdays = (6, 0, 1, 2, 3)
    sigal = Beautician(
        user=sigal_user,
        bio="מייסדת מכון היופי S.Cosmetics וקוסמטיקאית פרה-רפואית.",
        treatments=treatments,
        working_hours=[
            BeauticianWorkingHours(
                weekday=weekday,
                start_time=time(9, 0),
                end_time=time(17, 0),
            )
            for weekday in workdays
        ],
    )
    demo_beautician = Beautician(
        user=demo_user,
        bio="מטפלת לדוגמה בסביבת הפיתוח.",
        treatments=[
            treatment
            for treatment in treatments
            if treatment.category in {"טיפולי פנים", "טיפולי לייזר"}
        ],
        working_hours=[
            BeauticianWorkingHours(
                weekday=weekday,
                start_time=time(10, 0),
                end_time=time(18, 0),
            )
            for weekday in workdays
        ],
    )

    session.add_all([sigal, demo_beautician])
    session.commit()


def seed_packages(session: Session) -> None:
    if session.scalar(select(Package.id).limit(1)) is not None:
        return

    treatments = {
        treatment.name: treatment
        for treatment in session.scalars(select(Treatment)).all()
    }
    laser = treatments.get("הסרת שיער בלייזר")
    facial = treatments.get("טיפול זוהר לפנים")
    packages = []
    if laser is not None:
        packages.append(
            Package(
                name="סדרת לייזר — 10 טיפולים",
                price=Decimal("2500.00"),
                sessions=10,
                validity_days=365,
                treatments=[laser],
            )
        )
    if facial is not None:
        packages.append(
            Package(
                name="סדרת טיפולי פנים — 5 טיפולים",
                price=Decimal("1800.00"),
                sessions=5,
                validity_days=180,
                treatments=[facial],
            )
        )
    session.add_all(packages)
    session.commit()


DEFAULT_SITE_CONTENT = {
    "hero_eyebrow": "מדע, דיוק וטיפוח שנפגשים במקום אחד",
    "hero_title_first": "להרגיש טוב בעור שלך,",
    "hero_title_second": " בכל שלב בדרך.",
    "hero_description": "קליניקה לקוסמטיקה פרה-רפואית המתמחה בטיפולי פנים, אנטי אייג׳ינג ולייזר — עם אבחון אישי, טכנולוגיה מתקדמת וליווי מקצועי.",
    "about_title": "יופי בריא מתחיל בהבנה עמוקה של העור.",
    "about_body": "ב־S Cosmetics אנחנו משלבות ניסיון מקצועי, מכשור מתקדם וחומרים פעילים כדי ליצור תוכנית טיפול מדויקת — בלי קיצורי דרך ובלי הבטחות גנריות.",
    "equipment_title": "טכנולוגיה שמותאמת לטיפול שלך.",
    "equipment_intro": "אנחנו בוחרות את המכשור לפי מטרת הטיפול וצרכי העור, עם תשומת לב לפרטים הקטנים.",
    "materials_title": "חומרים שנבחרים בקפידה.",
    "materials_body": "התאמת תכשירים וחומרים מקצועיים מתבצעת לאחר אבחון אישי ובהתאם לסוג העור ולמטרות הטיפול.",
    "contact_title": "בואי נכיר את העור שלך.",
    "contact_body": "בחרי את הטיפול והיום שמתאימים לך — ונמצא יחד שעה פנויה.",
    "opening_hours": "א׳–ה׳, 09:00–17:00",
}


def seed_site_content(session: Session) -> None:
    existing = set(session.scalars(select(SiteContent.key)).all())
    missing = [SiteContent(key=key, value=value) for key, value in DEFAULT_SITE_CONTENT.items() if key not in existing]
    if missing:
        session.add_all(missing)
        session.commit()


def seed_equipment(session: Session) -> None:
    if session.scalar(select(Equipment.id).limit(1)) is not None:
        return
    laser = session.scalar(select(Treatment).where(Treatment.name == "הסרת שיער בלייזר"))
    if laser is None:
        return
    session.add(Equipment(
        name="מכשיר לייזר להסרת שיער",
        manufacturer="",
        description="טכנולוגיה להסרת שיער במסגרת תוכנית טיפול אישית המותאמת ללקוחה.",
        image_url="/images/Hair_Removal_Soprano.png",
        treatments=[laser],
    ))
    session.commit()


SEED_TEAM_MEMBERS = (
    {
        "name": "סיגל לוי", "title": "מייסדת מכון היופי S.Cosmetics",
        "description": "סיגל הקימה את המכון מתוך אהבה לעולם הטיפוח והאסתטיקה ומתוך אמונה שטיפול מקצועי מתחיל בהקשבה. היא משלבת יחס אישי, ניסיון והתאמה לצרכים הייחודיים של כל מטופלת.",
        "image_url": "/images/Sigal_Levi.png", "featured": True, "display_order": 0,
    },
    {
        "name": "מטפלת1", "title": "קוסמטיקאית פרה-רפואית",
        "description": "קוסמטיקאית מקצועית המתמחה בהתאמת טיפולי פנים לצורכי העור, תוך הקפדה על עבודה עדינה, אבחון אישי וליווי לאורך התהליך.",
        "image_url": "/images/logo-scosmetics.png", "display_order": 1,
    },
    {
        "name": "מטפלת2", "title": "מומחית להזרקות ועיצוב שפתיים",
        "description": "מטפלת בתחום האסתטיקה המתמקדת בתכנון אישי וביצירת מראה מאוזן וטבעי, מתוך הקשבה לרצונות המטופלת ושמירה על תהליך מקצועי ומדויק.",
        "image_url": "/images/logo-scosmetics.png", "display_order": 2,
    },
    {
        "name": "מטפלת3", "title": "קוסמטיקאית פרה-רפואית",
        "description": "קוסמטיקאית בעלת גישה אישית ואהבה לעולם הטיפוח, המשלבת ידע מקצועי עם התאמת שגרת טיפול שמטרתה לשמור על עור בריא ומטופח.",
        "image_url": "/images/logo-scosmetics.png", "display_order": 3,
    },
    {
        "name": "מטפלת4", "title": "מומחית להזרקות ועיצוב שפתיים",
        "description": "מטפלת אסתטית המתמחה בהתאמת טיפולים למבנה הפנים, עם תשומת לב לפרטים, תקשורת פתוחה ושאיפה לתוצאה עדינה והרמונית.",
        "image_url": "/images/logo-scosmetics.png", "display_order": 4,
    },
)


def seed_team(session: Session) -> None:
    if session.scalar(select(TeamMember.id).limit(1)) is not None:
        return
    session.add_all(TeamMember(**member) for member in SEED_TEAM_MEMBERS)
    session.commit()
