"""Test/savol/javob repository (R6, R14).

`tests`, `questions`, `answers` jadvallari ustida ma'lumotlarga kirish.
Diagnostika_Moduli (TestService) faol testlar ro'yxati va test tafsilotlarini
(savollar belgilangan tartibda) shu repository orqali oladi.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.content import Answer, Question, Test
from app.repositories.base import BaseRepository


class TestRepository(BaseRepository[Test]):
    """`tests` jadvali uchun repository."""

    model = Test

    def get_by_id(self, test_id: int) -> Test | None:
        """ID bo'yicha testni qaytaradi (faol/nofaolligidan qat'i nazar)."""
        return self.session.get(Test, test_id)

    def list_active(self) -> list[Test]:
        """Faqat faol (``is_active=true``) testlarni qaytaradi (R6.1, R6.5)."""
        stmt = (
            select(Test)
            .where(Test.is_active.is_(True))
            .order_by(Test.id)
        )
        return list(self.session.scalars(stmt).all())

    def get_with_questions(self, test_id: int) -> Test | None:
        """Test va uning savollarini ``order_index`` bo'yicha tartibda yuklaydi (R6.3).

        Savollar bilan bog'liq javob variantlari ham birga (eager) yuklanadi.
        """
        stmt = (
            select(Test)
            .where(Test.id == test_id)
            .options(
                selectinload(Test.questions).selectinload(Question.answers)
            )
        )
        return self.session.scalar(stmt)

    def create(
        self,
        *,
        title: str,
        category: str | None = None,
        description: str | None = None,
        duration_minutes: int | None = None,
        is_active: bool = True,
    ) -> Test:
        """Yangi test yaratadi (R14.2)."""
        test = Test(
            title=title,
            category=category,
            description=description,
            duration_minutes=duration_minutes,
            is_active=is_active,
        )
        return self.add(test)

    def set_active(self, test: Test, *, is_active: bool) -> Test:
        """Testni faol/nofaol holatga o'tkazadi (R14.4)."""
        test.is_active = is_active
        self.session.flush()
        return test


class QuestionRepository(BaseRepository[Question]):
    """`questions` jadvali uchun repository (R6.3, R14.3)."""

    model = Question

    def get_by_id(self, question_id: int) -> Question | None:
        """ID bo'yicha savolni qaytaradi."""
        return self.session.get(Question, question_id)

    def list_for_test(self, test_id: int) -> list[Question]:
        """Test savollarini ``order_index`` bo'yicha qaytaradi (R6.3)."""
        stmt = (
            select(Question)
            .where(Question.test_id == test_id)
            .order_by(Question.order_index, Question.id)
        )
        return list(self.session.scalars(stmt).all())

    def create(
        self,
        *,
        test_id: int,
        question_text: str,
        score: object,
        competency_id: int | None = None,
        question_type: str | None = None,
        order_index: int | None = None,
    ) -> Question:
        """Yangi savol yaratadi (R14.3)."""
        question = Question(
            test_id=test_id,
            question_text=question_text,
            score=score,
            competency_id=competency_id,
            question_type=question_type,
            order_index=order_index,
        )
        return self.add(question)

    def is_competency_used(self, competency_id: int) -> bool:
        """Kompetensiya biror savol tomonidan ishlatilayotganini tekshiradi (R14.8).

        Referensial yaxlitlik: ishlatilayotgan kompetensiyani o'chirish rad
        etiladi.
        """
        stmt = select(Question.id).where(
            Question.competency_id == competency_id
        ).limit(1)
        return self.session.scalar(stmt) is not None


class AnswerRepository(BaseRepository[Answer]):
    """`answers` jadvali uchun repository (R6, R14.3)."""

    model = Answer

    def get_by_id(self, answer_id: int) -> Answer | None:
        """ID bo'yicha javob variantini qaytaradi."""
        return self.session.get(Answer, answer_id)

    def list_for_question(self, question_id: int) -> list[Answer]:
        """Savolning barcha javob variantlarini qaytaradi (R14.3 — ≥2 variant)."""
        stmt = (
            select(Answer)
            .where(Answer.question_id == question_id)
            .order_by(Answer.id)
        )
        return list(self.session.scalars(stmt).all())

    def create(
        self,
        *,
        question_id: int,
        answer_text: str,
        is_correct: bool = False,
        score: object | None = None,
    ) -> Answer:
        """Yangi javob varianti yaratadi."""
        answer = Answer(
            question_id=question_id,
            answer_text=answer_text,
            is_correct=is_correct,
            score=score,
        )
        return self.add(answer)


__all__ = ["TestRepository", "QuestionRepository", "AnswerRepository"]
