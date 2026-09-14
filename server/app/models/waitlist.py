from datetime import date, datetime
from enum import Enum

from sqlalchemy import Date, DateTime, Enum as SqlEnum, ForeignKey, Integer, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class WaitlistStatus(str, Enum):
    WAITING = "waiting"
    OFFERED = "offered"
    FULFILLED = "fulfilled"
    CANCELLED = "cancelled"


class WaitlistEntry(Base):
    __tablename__ = "waitlist"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    treatment_id: Mapped[int] = mapped_column(ForeignKey("treatments.id"), index=True)
    preferred_date: Mapped[date] = mapped_column(Date, index=True)
    beautician_id: Mapped[int | None] = mapped_column(ForeignKey("beauticians.id"))
    status: Mapped[WaitlistStatus] = mapped_column(
        SqlEnum(
            WaitlistStatus,
            native_enum=False,
            values_callable=lambda statuses: [status.value for status in statuses],
        ),
        default=WaitlistStatus.WAITING,
        server_default=WaitlistStatus.WAITING.value,
    )
    offered_start_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    offered_end_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    offer_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
