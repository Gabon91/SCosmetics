from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Treatment(Base):
    __tablename__ = "treatments"
    __table_args__ = (
        CheckConstraint(
            "duration_minutes > 0 AND duration_minutes % 15 = 0",
            name="ck_treatments_duration_15_minute_increment",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), index=True)
    category: Mapped[str] = mapped_column(String(80), index=True)
    description: Mapped[str] = mapped_column(Text)
    duration_minutes: Mapped[int] = mapped_column(Integer)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    accent: Mapped[str] = mapped_column(String(20), default="sage")
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
