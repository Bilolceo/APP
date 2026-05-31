"""Sessiya repository (R7).

`test_sessions` va `session_answers` jadvallari ustida ma'lumotlarga kirish.
Diagnostika_Moduli (SessionService) sessiya hayot siklini (boshlash, javoblarni
saqlash, yakunlash) shu repository orqali boshqaradi.

Konvensiyalar `base.py` bilan bir xil: konstruktorda `Session`, SQLAlchemy 2.x
`select()` uslubi, `add()` `flush` qiladi (commit emas) — tranzaksiya chegarasi
chaqiruvchida (servis / `get_session`).
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.session import SessionAnswer, TestSession
from app.repositories.base import BaseRepository


class SessionRepository(BaseRepository[TestSession]):
    """`test_sessions` va `session_answers` uchun repository (R7)."""

    model = TestSession

    def get_by_id(self, session_id: int) -> TestSession | None:
        """ID bo'yicha sessiyani qaytaradi (yoki ``None``)."""
        return self.session.get(TestSession, session_id)

    def get_active(self, user_id: int, test_id: int) -> TestSession | None:
        """Foydalanuvchining berilgan test bo'yicha tugatilmagan sessiyasi (R7.1, R7.10).

        ``status='in_progress'`` bo'lgan sessiya qaytariladi; bunday sessiya
        yo'q bo'lsa ``None``. Qisman noyob indeks (R7.10) bir vaqtda faqat bitta
        bunday sessiya mavjudligini kafolatlaydi.
        """
        stmt = (
            select(TestSession)
            .where(
                TestSession.user_id == user_id,
                TestSession.test_id == test_id,
                TestSession.status == "in_progress",
            )
            .order_by(TestSession.id.desc())
            .limit(1)
        )
        return self.session.scalar(stmt)

    def create(
        self,
        *,
        user_id: int,
        test_id: int,
        started_at: datetime,
        expires_at: datetime | None = None,
        status: str = "in_progress",
    ) -> TestSession:
        """Yangi sessiya yaratadi (R7.1)."""
        session_obj = TestSession(
            user_id=user_id,
            test_id=test_id,
            status=status,
            started_at=started_at,
            expires_at=expires_at,
        )
        return self.add(session_obj)

    def complete(
        self, session_obj: TestSession, *, completed_at: datetime
    ) -> TestSession:
        """Sessiyani ``completed`` holatiga o'tkazadi (R7.5, R7.6)."""
        session_obj.status = "completed"
        session_obj.completed_at = completed_at
        self.session.flush()
        return session_obj

    def list_answers(self, session_id: int) -> list[SessionAnswer]:
        """Sessiyaga tegishli barcha javoblarni qaytaradi (R7.5)."""
        stmt = (
            select(SessionAnswer)
            .where(SessionAnswer.session_id == session_id)
            .order_by(SessionAnswer.id)
        )
        return list(self.session.scalars(stmt).all())

    def get_answer(
        self, session_id: int, question_id: int
    ) -> SessionAnswer | None:
        """Sessiya + savol bo'yicha mavjud javobni qaytaradi (upsert uchun)."""
        stmt = select(SessionAnswer).where(
            SessionAnswer.session_id == session_id,
            SessionAnswer.question_id == question_id,
        )
        return self.session.scalar(stmt)

    def upsert_answer(
        self,
        *,
        session_id: int,
        question_id: int,
        selected_answer_id: int | None = None,
        likert_value: int | None = None,
        answered: bool = True,
    ) -> SessionAnswer:
        """Sessiya javobini yaratadi yoki mavjudini yangilaydi (R7.5).

        Bir savol uchun bitta javob yozuvi saqlanadi; takroriy saqlashda
        oldingi yozuv yangilanadi.
        """
        existing = self.get_answer(session_id, question_id)
        if existing is not None:
            existing.selected_answer_id = selected_answer_id
            existing.likert_value = likert_value
            existing.answered = answered
            self.session.flush()
            return existing
        answer = SessionAnswer(
            session_id=session_id,
            question_id=question_id,
            selected_answer_id=selected_answer_id,
            likert_value=likert_value,
            answered=answered,
        )
        return self.add(answer)

    def add_answers(
        self, answers: list[SessionAnswer]
    ) -> list[SessionAnswer]:
        """Bir nechta javob yozuvini qo'shadi va `flush` qiladi (R7.5)."""
        self.session.add_all(answers)
        self.session.flush()
        return answers


__all__ = ["SessionRepository"]
