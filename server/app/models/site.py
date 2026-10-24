from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Table, Text, false, true
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class SiteContent(Base):
    __tablename__ = "site_content"

    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    value: Mapped[str] = mapped_column(Text)


equipment_treatments = Table(
    "equipment_treatments",
    Base.metadata,
    Column("equipment_id", ForeignKey("equipment.id", ondelete="CASCADE"), primary_key=True),
    Column("treatment_id", ForeignKey("treatments.id", ondelete="CASCADE"), primary_key=True),
)


class Equipment(Base):
    __tablename__ = "equipment"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    manufacturer: Mapped[str] = mapped_column(String(120), default="")
    description: Mapped[str] = mapped_column(Text)
    image_url: Mapped[str] = mapped_column(String(500), default="")
    active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())
    treatments = relationship("Treatment", secondary=equipment_treatments)


class TeamMember(Base):
    """Public-facing biography; booking permissions remain on Beautician."""

    __tablename__ = "team_members"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    title: Mapped[str] = mapped_column(String(160))
    description: Mapped[str] = mapped_column(Text)
    image_url: Mapped[str] = mapped_column(String(500), default="")
    featured: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    display_order: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())
