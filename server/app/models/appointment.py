from datetime import datetime
from enum import Enum

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum as SqlEnum,
    ForeignKey,
    Index,
    Integer,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.beautician import Beautician
from app.models.treatment import Treatment
from app.models.user import User


class AppointmentStatus(str, Enum):
    BOOKED = "booked"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"


class Appointment(Base):
    __tablename__ = "appointments"
    __table_args__ = (
        CheckConstraint(
            "end_time > start_time",
            name="ck_appointments_time_range",
        ),
        Index(
            "ix_appointments_beautician_start",
            "beautician_id",
            "start_time",
        ),
        Index(
            "ix_appointments_treatment_start",
            "treatment_id",
            "start_time",
        ),
        Index(
            "ix_appointments_start_status",
            "start_time",
            "status",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    customer_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        index=True,
    )
    beautician_id: Mapped[int] = mapped_column(
        ForeignKey("beauticians.id"),
    )
    treatment_id: Mapped[int] = mapped_column(
        ForeignKey("treatments.id"),
    )
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[AppointmentStatus] = mapped_column(
        SqlEnum(
            AppointmentStatus,
            name="appointment_status",
            native_enum=False,
            values_callable=lambda statuses: [
                status.value for status in statuses
            ],
        ),
        default=AppointmentStatus.BOOKED,
        server_default=AppointmentStatus.BOOKED.value,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    customer: Mapped[User] = relationship(foreign_keys=[customer_id])
    beautician: Mapped[Beautician] = relationship()
    treatment: Mapped[Treatment] = relationship()
