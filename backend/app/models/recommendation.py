"""Tavsiya jadvallari: recommendations, result_recommendations (R10).

design.md — "recommendations (R10)" va
"result_recommendations (R10) — tanlangan tavsiyani natijaga bog'lash".
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, BigIntType

if TYPE_CHECKING:
    from app.models.reference import Competency
    from app.models.result import TestResult


class Recommendation(Base):
    """Kompetensiya + daraja bo'yicha tavsiya matni (R10.1, R10.4).

    ``competency_id`` NULL + umumiy daraja = standart (default) tavsiya (R10.4).
    """

    __tablename__ = "recommendations"

    id: Mapped[int] = mapped_column(BigIntType, primary_key=True)
    competency_id: Mapped[int | None] = mapped_column(
        ForeignKey("competencies.id"), nullable=True
    )
    level: Mapped[str | None] = mapped_column(String(10), nullable=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)

    competency: Mapped["Competency | None"] = relationship(
        back_populates="recommendations"
    )
    result_recommendations: Mapped[list["ResultRecommendation"]] = relationship(
        back_populates="recommendation"
    )


class ResultRecommendation(Base):
    """Natijaga bog'langan tanlangan tavsiya (R10.1).

    ``text_snapshot`` tavsiya keyin o'zgarsa ham tarixiy matnni saqlaydi.
    """

    __tablename__ = "result_recommendations"

    id: Mapped[int] = mapped_column(BigIntType, primary_key=True)
    result_id: Mapped[int] = mapped_column(
        ForeignKey("test_results.id"), nullable=False
    )
    competency_id: Mapped[int | None] = mapped_column(
        ForeignKey("competencies.id"), nullable=True
    )
    level: Mapped[str | None] = mapped_column(String(10), nullable=True)
    recommendation_id: Mapped[int | None] = mapped_column(
        ForeignKey("recommendations.id"), nullable=True
    )
    text_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)

    result: Mapped["TestResult"] = relationship(
        back_populates="result_recommendations"
    )
    competency: Mapped["Competency | None"] = relationship()
    recommendation: Mapped["Recommendation | None"] = relationship(
        back_populates="result_recommendations"
    )


__all__ = ["Recommendation", "ResultRecommendation"]
