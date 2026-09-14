from datetime import time
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    ForeignKey,
    Integer,
    Table,
    Text,
    Time,
    UniqueConstraint,
    text,
    true,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.treatment import Treatment
    from app.models.user import User


beautician_treatments = Table(
    "beautician_treatments",
    Base.metadata,
    Column(
        "beautician_id",
        ForeignKey("beauticians.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "treatment_id",
        ForeignKey("treatments.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class Beautician(Base):
    __tablename__ = "beauticians"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        index=True,
    )
    bio: Mapped[str] = mapped_column(
        Text,
        default="",
        server_default=text("('')"),
    )
    active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default=true(),
        index=True,
    )

    user: Mapped["User"] = relationship()
    treatments: Mapped[list["Treatment"]] = relationship(
        secondary=beautician_treatments,
    )
    working_hours: Mapped[list["BeauticianWorkingHours"]] = relationship(
        back_populates="beautician",
        cascade="all, delete-orphan",
    )


class BeauticianWorkingHours(Base):
    __tablename__ = "beautician_working_hours"
    __table_args__ = (
        CheckConstraint(
            "weekday >= 0 AND weekday <= 6",
            name="ck_beautician_working_hours_weekday",
        ),
        CheckConstraint(
            "start_time < end_time",
            name="ck_beautician_working_hours_time_range",
        ),
        UniqueConstraint(
            "beautician_id",
            "weekday",
            "start_time",
            "end_time",
            name="uq_beautician_working_hours_shift",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    beautician_id: Mapped[int] = mapped_column(
        ForeignKey("beauticians.id", ondelete="CASCADE"),
        index=True,
    )
    weekday: Mapped[int] = mapped_column(Integer)
    start_time: Mapped[time] = mapped_column(Time)
    end_time: Mapped[time] = mapped_column(Time)
    active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default=true(),
    )

    beautician: Mapped[Beautician] = relationship(
        back_populates="working_hours",
    )
