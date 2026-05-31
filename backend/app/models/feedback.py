"""`feedbacks` jadvali — 360 daraja teskari aloqa (post-MVP, R18.1).

design.md — "Kengaytirilish uchun jadvallar (R18 — post-MVP tayyorgarlik)":
``feedbacks(id, target_user_id FK, source_type VARCHAR(20), source_user_id FK NULL,
payload JSONB, created_at)``. ``source_type`` ∈ {self, staff, expert, parent,
superior}. ``payload JSONB`` turli baholash sxemalarini sxemani o'zgartirmasdan
saqlashga imkon beradi.

Eslatma: ``JSONB`` PostgreSQL-spetsifik tur; boshqa backendlarda (sinov, SQLite)
umumiy ``JSON`` ga moslashuvi uchun ``JSONB(...).with_variant(JSON, "sqlite")``
ishlatiladi.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import CheckConstraint, ForeignKey, String
from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, BigIntType, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User

# PostgreSQL'da JSONB, boshqa backendlarda (sinov) umumiy JSON.
JSONType = JSONB().with_variant(JSON(), "sqlite")


class Feedback(TimestampMixin, Base):
    """Umumlashtirilgan 360 daraja teskari aloqa modeli (R18.1)."""

    __tablename__ = "feedbacks"
    __table_args__ = (
        CheckConstraint(
            "source_type IN ('self', 'staff', 'expert', 'parent', 'superior')",
            name="source_type_valid",
        ),
    )

    id: Mapped[int] = mapped_column(BigIntType, primary_key=True)
    target_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )
    source_type: Mapped[str] = mapped_column(String(20), nullable=False)
    source_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    payload: Mapped[dict[str, Any] | None] = mapped_column(
        JSONType, nullable=True
    )

    target_user: Mapped["User"] = relationship(
        back_populates="feedbacks_received",
        foreign_keys=[target_user_id],
    )
    source_user: Mapped["User | None"] = relationship(
        foreign_keys=[source_user_id],
    )


__all__ = ["Feedback"]
