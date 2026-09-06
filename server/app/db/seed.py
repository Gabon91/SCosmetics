from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.treatment import Treatment

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

