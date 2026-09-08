from datetime import time
from decimal import Decimal
from secrets import token_urlsafe

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.beautician import Beautician, BeauticianWorkingHours
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
