from datetime import date
from decimal import Decimal
from enum import Enum

from sqlalchemy import Boolean, CheckConstraint, Column, Date, Enum as SqlEnum
from sqlalchemy import ForeignKey, Integer, Numeric, String, Table, true
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


package_treatments = Table(
    "package_treatments",
    Base.metadata,
    Column("package_id", ForeignKey("packages.id", ondelete="CASCADE"), primary_key=True),
    Column("treatment_id", ForeignKey("treatments.id", ondelete="CASCADE"), primary_key=True),
)


class UserPackageStatus(str, Enum):
    ACTIVE = "active"
    EXHAUSTED = "exhausted"


class Package(Base):
    __tablename__ = "packages"
    __table_args__ = (
        CheckConstraint("sessions > 0", name="ck_packages_sessions_positive"),
        CheckConstraint("validity_days > 0", name="ck_packages_validity_positive"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    sessions: Mapped[int] = mapped_column(Integer)
    validity_days: Mapped[int] = mapped_column(Integer)
    active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())
    treatments = relationship("Treatment", secondary=package_treatments)


class UserPackage(Base):
    __tablename__ = "user_packages"
    __table_args__ = (
        CheckConstraint(
            "total_sessions > 0 AND used_sessions >= 0 AND remaining_sessions >= 0",
            name="ck_user_packages_nonnegative_balance",
        ),
        CheckConstraint(
            "used_sessions + remaining_sessions = total_sessions",
            name="ck_user_packages_balance_matches_total",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    package_id: Mapped[int] = mapped_column(ForeignKey("packages.id"))
    total_sessions: Mapped[int] = mapped_column(Integer)
    used_sessions: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    remaining_sessions: Mapped[int] = mapped_column(Integer)
    expiration_date: Mapped[date] = mapped_column(Date)
    status: Mapped[UserPackageStatus] = mapped_column(
        SqlEnum(
            UserPackageStatus,
            native_enum=False,
            values_callable=lambda statuses: [status.value for status in statuses],
        ),
        default=UserPackageStatus.ACTIVE,
        server_default=UserPackageStatus.ACTIVE.value,
    )

    package: Mapped[Package] = relationship()
