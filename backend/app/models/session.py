"""Sessiya jadvallari: test_sessions, session_answers (R7).

design.md — "test_sessions (R7) — sessiya hayot sikli" va "session_answers (R7)".

Eslatma: ``UNIQUE (user_id, test_id) WHERE status='in_progress'`` qisman noyob
indeks bu yerda PostgreSQL ``postgresql_where`` orqali e'lon qilinadi (R7.10).
SQLite kabi backendlarda (sinov) qisman indeks ham qo'llab-quvvatlanadi.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    SmallInteger,
    String,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, BigIntType

if TYPE_CHECKING:
    from app.models.content import Answer, Question, Test
    from app.models.result import TestResult
    from app.models.user import User


class TestSession(Base):
    """Test sessiyasi hayot sikli (R7.1, R7.5, R7.10)."""

    # pytest bu ORM modelini test klassi sifatida yig'ishga urinmasligi uchun.
    __test__ = False

    __tablename__ = "test_sessions"
    __table_args__ = (
        # Bir foydalanuvchi bitta test uchun bir vaqtda faqat bitta tugatilmagan
        # sessiyaga ega bo'lishi mumkin (R7.10).
        Index(
            "uq_test_sessions_active_user_test",
            "user_id",
            "test_id",
            unique=True,
            postgresql_where=text("status = 'in_progress'"),
            sqlite_where=text("status = 'in_progress'"),
        ),
    )

    id: Mapped[int] = mapped_column(BigIntType, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    test_id: Mapped[int] = mapped_column(ForeignKey("tests.id"), nullable=False)
    # in_progress / completed
    status: Mapped[str] = mapped_column(String(12), nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    # started_at + duration (R7.5)
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    user: Mapped["User"] = relationship(back_populates="test_sessions")
    test: Mapped["Test"] = relationship(back_populates="sessions")
    answers: Mapped[list["SessionAnswer"]] = relationship(
        back_populates="session"
    )
    result: Mapped["TestResult | None"] = relationship(back_populates="session")


class SessionAnswer(Base):
    """Sessiya doirasida savolga berilgan javob (R7.5).

    Javobsiz savollar ``answered=false`` bilan saqlanadi.
    """

    __tablename__ = "session_answers"

    id: Mapped[int] = mapped_column(BigIntType, primary_key=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("test_sessions.id"), nullable=False
    )
    question_id: Mapped[int] = mapped_column(
        ForeignKey("questions.id"), nullable=False
    )
    selected_answer_id: Mapped[int | None] = mapped_column(
        ForeignKey("answers.id"), nullable=True
    )
    likert_value: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    answered: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )

    session: Mapped["TestSession"] = relationship(back_populates="answers")
    question: Mapped["Question"] = relationship(back_populates="session_answers")
    selected_answer: Mapped["Answer | None"] = relationship(
        back_populates="selected_in"
    )


__all__ = ["TestSession", "SessionAnswer"]
