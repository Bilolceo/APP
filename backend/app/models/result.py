"""Natija jadvallari: test_results, competency_results (R8).

design.md — "test_results (R8)" va "competency_results (R8)".
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    Date,
    ForeignKey,
    Numeric,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, BigIntType, TimestampMixin

if TYPE_CHECKING:
    from app.models.content import Test
    from app.models.reference import Competency
    from app.models.recommendation import ResultRecommendation
    from app.models.session import TestSession
    from app.models.user import User


class TestResult(TimestampMixin, Base):
    """Test natijasi — sessiyaga 1:1 bog'lanadi (idempotentlik, R7.7)."""

    # pytest bu ORM modelini test klassi sifatida yig'ishga urinmasligi uchun.
    __test__ = False

    __tablename__ = "test_results"
    __table_args__ = (
        # umumiy foiz 0..100 (R8.1)
        CheckConstraint(
            "percentage >= 0 AND percentage <= 100",
            name="percentage_range",
        ),
    )

    id: Mapped[int] = mapped_column(BigIntType, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    test_id: Mapped[int] = mapped_column(ForeignKey("tests.id"), nullable=False)
    # idempotentlik: sessiyaga 1:1 (R7.7)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("test_sessions.id"), nullable=False, unique=True
    )

    total_score: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    max_score: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    # (R8.1)
    percentage: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    # Past/O'rta/Yaxshi/Yuqori (R8.2)
    level: Mapped[str] = mapped_column(String(10), nullable=False)
    # ekspert qo'shimcha ko'rsatkichi (R13.2)
    expert_score: Mapped[Decimal | None] = mapped_column(
        Numeric(3, 2), nullable=True
    )
    # qayta topshirish sanasi (R8.4)
    next_retake_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    user: Mapped["User"] = relationship(back_populates="test_results")
    test: Mapped["Test"] = relationship(back_populates="results")
    session: Mapped["TestSession"] = relationship(back_populates="result")
    competency_results: Mapped[list["CompetencyResult"]] = relationship(
        back_populates="result"
    )
    result_recommendations: Mapped[list["ResultRecommendation"]] = relationship(
        back_populates="result"
    )


class CompetencyResult(Base):
    """Natija tarkibidagi kompetensiya bo'yicha ball (R8.3, R8.8)."""

    __tablename__ = "competency_results"
    __table_args__ = (
        # kompetensiya foizi 0..100 (R8.8)
        CheckConstraint(
            "percentage >= 0 AND percentage <= 100",
            name="percentage_range",
        ),
    )

    id: Mapped[int] = mapped_column(BigIntType, primary_key=True)
    result_id: Mapped[int] = mapped_column(
        ForeignKey("test_results.id"), nullable=False
    )
    competency_id: Mapped[int] = mapped_column(
        ForeignKey("competencies.id"), nullable=False
    )
    score: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    max_score: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    percentage: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)

    result: Mapped["TestResult"] = relationship(
        back_populates="competency_results"
    )
    competency: Mapped["Competency"] = relationship(
        back_populates="competency_results"
    )


__all__ = ["TestResult", "CompetencyResult"]
