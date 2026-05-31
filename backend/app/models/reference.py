"""Ma'lumotnoma (reference) jadvallari: roles, regions, organizations, competencies.

design.md — "Asosiy jadvallar":
- roles(id, name)
- regions(id, name)
- organizations(id, name, region_id FK, org_type)
- competencies(id, name, description)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, BigIntType

if TYPE_CHECKING:
    from app.models.content import Question
    from app.models.recommendation import Recommendation
    from app.models.result import CompetencyResult
    from app.models.user import User


class Role(Base):
    """Foydalanuvchi roli: Rahbar / Ekspert / Administrator (R1.7)."""

    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(BigIntType, primary_key=True)
    name: Mapped[str] = mapped_column(String(40), nullable=False, unique=True)

    users: Mapped[list["User"]] = relationship(back_populates="role")


class Region(Base):
    """Hudud (viloyat/tuman) ma'lumotnomasi."""

    __tablename__ = "regions"

    id: Mapped[int] = mapped_column(BigIntType, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)

    users: Mapped[list["User"]] = relationship(back_populates="region")
    organizations: Mapped[list["Organization"]] = relationship(
        back_populates="region"
    )


class Organization(Base):
    """Tashkilot (MTT) ma'lumotnomasi."""

    __tablename__ = "organizations"

    id: Mapped[int] = mapped_column(BigIntType, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    region_id: Mapped[int | None] = mapped_column(
        ForeignKey("regions.id"), nullable=True
    )
    org_type: Mapped[str | None] = mapped_column(String(200), nullable=True)

    region: Mapped["Region | None"] = relationship(back_populates="organizations")
    users: Mapped[list["User"]] = relationship(back_populates="organization")


class Competency(Base):
    """Baholanadigan kompetensiya yo'nalishi (R8, R14)."""

    __tablename__ = "competencies"

    id: Mapped[int] = mapped_column(BigIntType, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    questions: Mapped[list["Question"]] = relationship(back_populates="competency")
    competency_results: Mapped[list["CompetencyResult"]] = relationship(
        back_populates="competency"
    )
    recommendations: Mapped[list["Recommendation"]] = relationship(
        back_populates="competency"
    )


__all__ = ["Role", "Region", "Organization", "Competency"]
