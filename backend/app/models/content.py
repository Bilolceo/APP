"""Test kontenti jadvallari: tests, questions, answers (R6, R14).

design.md — "tests (R6, R14)", "questions (R6, R14)", "answers (R6, R14)".
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, BigIntType, TimestampMixin

if TYPE_CHECKING:
    from app.models.reference import Competency
    from app.models.result import TestResult
    from app.models.session import SessionAnswer, TestSession


class Test(TimestampMixin, Base):
    """Diagnostika testi (R6.1, R14.2)."""

    # pytest bu ORM modelini test klassi sifatida yig'ishga urinmasligi uchun.
    __test__ = False

    __tablename__ = "tests"
    __table_args__ = (
        # toifa: kognitiv/kompetensiya/reflexiv/situatsion (R6.2)
        CheckConstraint(
            "category IN ('kognitiv', 'kompetensiya', 'reflexiv', 'situatsion')",
            name="category_valid",
        ),
        # davomiyligi 1..600 daqiqa (R14.2)
        CheckConstraint(
            "duration_minutes >= 1 AND duration_minutes <= 600",
            name="duration_minutes_range",
        ),
    )

    id: Mapped[int] = mapped_column(BigIntType, primary_key=True)
    # 1–200 belgi (R14.2)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str | None] = mapped_column(String(40), nullable=True)
    duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # faol testlar (R6.1)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )

    questions: Mapped[list["Question"]] = relationship(
        back_populates="test",
        order_by="Question.order_index",
    )
    sessions: Mapped[list["TestSession"]] = relationship(back_populates="test")
    results: Mapped[list["TestResult"]] = relationship(back_populates="test")


class Question(TimestampMixin, Base):
    """Test savoli (R6.3, R14.3)."""

    __tablename__ = "questions"
    __table_args__ = (
        # savol balli 0.01..1000 musbat (R14.3)
        CheckConstraint(
            "score >= 0.01 AND score <= 1000",
            name="score_range",
        ),
    )

    id: Mapped[int] = mapped_column(BigIntType, primary_key=True)
    test_id: Mapped[int] = mapped_column(ForeignKey("tests.id"), nullable=False)
    # NULL = bog'lanmagan (R8.5)
    competency_id: Mapped[int | None] = mapped_column(
        ForeignKey("competencies.id"), nullable=True
    )
    # 1–1000 belgi (R14.3)
    question_text: Mapped[str] = mapped_column(String(1000), nullable=False)
    # cognitive/likert/situational
    question_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    score: Mapped[Decimal] = mapped_column(Numeric(7, 2), nullable=False)
    # belgilangan tartib (R6.3)
    order_index: Mapped[int | None] = mapped_column(Integer, nullable=True)

    test: Mapped["Test"] = relationship(back_populates="questions")
    competency: Mapped["Competency | None"] = relationship(
        back_populates="questions"
    )
    answers: Mapped[list["Answer"]] = relationship(back_populates="question")
    session_answers: Mapped[list["SessionAnswer"]] = relationship(
        back_populates="question"
    )


class Answer(Base):
    """Savol javob varianti — kamida 2 ta (R14.3)."""

    __tablename__ = "answers"

    id: Mapped[int] = mapped_column(BigIntType, primary_key=True)
    question_id: Mapped[int] = mapped_column(
        ForeignKey("questions.id"), nullable=False
    )
    answer_text: Mapped[str] = mapped_column(Text, nullable=False)
    is_correct: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    score: Mapped[Decimal | None] = mapped_column(Numeric(7, 2), nullable=True)

    question: Mapped["Question"] = relationship(back_populates="answers")
    selected_in: Mapped[list["SessionAnswer"]] = relationship(
        back_populates="selected_answer"
    )


__all__ = ["Test", "Question", "Answer"]
