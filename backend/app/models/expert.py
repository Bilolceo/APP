"""`expert_reviews` jadvali (R13) — ekspert tomonidan 6 mezon bo'yicha baholash.

design.md — "expert_reviews (R13)" jadval ta'rifiga aniq mos keladi.
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Numeric,
    SmallInteger,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, BigIntType, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User


class ExpertReview(TimestampMixin, Base):
    """Ekspert sharhi — har bir mezon 1–5, o'rtacha 1.00–5.00 (R13.1, R13.2)."""

    __tablename__ = "expert_reviews"
    __table_args__ = (
        # har bir mezon 1..5 butun son (R13.1, R13.3)
        CheckConstraint(
            "management_culture >= 1 AND management_culture <= 5",
            name="management_culture_range",
        ),
        CheckConstraint(
            "teamwork >= 1 AND teamwork <= 5",
            name="teamwork_range",
        ),
        CheckConstraint(
            "pedagogical_process >= 1 AND pedagogical_process <= 5",
            name="pedagogical_process_range",
        ),
        CheckConstraint(
            "innovation >= 1 AND innovation <= 5",
            name="innovation_range",
        ),
        CheckConstraint(
            "documentation >= 1 AND documentation <= 5",
            name="documentation_range",
        ),
        CheckConstraint(
            "strategic_planning >= 1 AND strategic_planning <= 5",
            name="strategic_planning_range",
        ),
    )

    id: Mapped[int] = mapped_column(BigIntType, primary_key=True)
    expert_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    leader_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    # 6 mezon (R13.1)
    management_culture: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    teamwork: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    pedagogical_process: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    innovation: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    documentation: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    strategic_planning: Mapped[int] = mapped_column(SmallInteger, nullable=False)

    # o'rtacha 1.00–5.00 (R13.2)
    average_score: Mapped[Decimal] = mapped_column(Numeric(3, 2), nullable=False)

    expert: Mapped["User"] = relationship(
        back_populates="reviews_given",
        foreign_keys=[expert_id],
    )
    leader: Mapped["User"] = relationship(
        back_populates="reviews_received",
        foreign_keys=[leader_id],
    )


__all__ = ["ExpertReview"]
