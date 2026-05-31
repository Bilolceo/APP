"""Natija repository (R8, R9, R12, R15).

`test_results` va `competency_results` jadvallari ustida ma'lumotlarga kirish.
Baholash_Moduli natijani saqlaydi (R8.6); Analitika_/Hisobot_/Reyting_Moduli
analitika va hisobot uchun natijalarni shu repository orqali oladi.

Konvensiyalar `base.py` bilan bir xil: konstruktorda `Session`, SQLAlchemy 2.x
`select()` uslubi, `add()` `flush` qiladi (commit emas).
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.result import CompetencyResult, TestResult
from app.repositories.base import BaseRepository


class ResultRepository(BaseRepository[TestResult]):
    """`test_results` + `competency_results` uchun repository (R8.6)."""

    model = TestResult

    def get_by_id(self, result_id: int) -> TestResult | None:
        """ID bo'yicha natijani (kompetensiya natijalari bilan) qaytaradi."""
        stmt = (
            select(TestResult)
            .where(TestResult.id == result_id)
            .options(selectinload(TestResult.competency_results))
        )
        return self.session.scalar(stmt)

    def get_by_session(self, session_id: int) -> TestResult | None:
        """Sessiya bo'yicha natijani qaytaradi — idempotentlik tekshiruvi (R7.7)."""
        stmt = select(TestResult).where(TestResult.session_id == session_id)
        return self.session.scalar(stmt)

    def get_for_user(self, user_id: int, result_id: int) -> TestResult | None:
        """Natijani egalik tekshiruvi bilan qaytaradi (R10.6, R4.1).

        Natija mavjud bo'lsa-yu, lekin so'rovchiga tegishli bo'lmasa ``None``
        qaytariladi (egalik servis qatlamida 403/404 ga aylantiriladi).
        """
        stmt = (
            select(TestResult)
            .where(
                TestResult.id == result_id,
                TestResult.user_id == user_id,
            )
            .options(selectinload(TestResult.competency_results))
        )
        return self.session.scalar(stmt)

    def list_for_user(self, user_id: int) -> list[TestResult]:
        """Foydalanuvchining barcha natijalarini xronologik tartibda qaytaradi (R9.1, R15.5).

        ``created_at`` bo'yicha o'suvchi (eng eskidan eng yangiga) — o'sish
        dinamikasi shu tartibga tayanadi.
        """
        stmt = (
            select(TestResult)
            .where(TestResult.user_id == user_id)
            .options(selectinload(TestResult.competency_results))
            .order_by(TestResult.created_at, TestResult.id)
        )
        return list(self.session.scalars(stmt).all())

    def latest_for_user(self, user_id: int) -> TestResult | None:
        """Foydalanuvchining eng so'nggi natijasini qaytaradi (R10.2)."""
        stmt = (
            select(TestResult)
            .where(TestResult.user_id == user_id)
            .options(selectinload(TestResult.competency_results))
            .order_by(TestResult.created_at.desc(), TestResult.id.desc())
            .limit(1)
        )
        return self.session.scalar(stmt)

    def list_all_with_user(self) -> list[TestResult]:
        """Barcha natijalarni foydalanuvchi (va kesim maydonlari) bilan yuklaydi.

        Hisobot/reyting agregatsiyasi (R15.3, R15.4, R12.1) uchun: hudud,
        tashkilot, lavozim kabi kesim maydonlari ``user`` orqali olinadi.
        """
        stmt = (
            select(TestResult)
            .options(
                selectinload(TestResult.user),
                selectinload(TestResult.competency_results),
            )
            .order_by(TestResult.created_at, TestResult.id)
        )
        return list(self.session.scalars(stmt).all())

    def create_with_competencies(
        self,
        *,
        user_id: int,
        test_id: int,
        session_id: int,
        total_score: Decimal,
        max_score: Decimal,
        percentage: Decimal,
        level: str,
        competency_rows: list[dict[str, object]] | None = None,
        expert_score: Decimal | None = None,
        next_retake_date: date | None = None,
    ) -> TestResult:
        """Natijani kompetensiya natijalari bilan birga yaratadi (R8.3, R8.6).

        Args:
            competency_rows: har biri ``competency_id``, ``score``, ``max_score``,
                ``percentage`` kalitlarini o'z ichiga olgan lug'atlar ro'yxati.

        Natija va bog'liq kompetensiya natijalari bitta `flush` da ID oladi;
        tranzaksiya chegarasi (commit) chaqiruvchida.
        """
        result = TestResult(
            user_id=user_id,
            test_id=test_id,
            session_id=session_id,
            total_score=total_score,
            max_score=max_score,
            percentage=percentage,
            level=level,
            expert_score=expert_score,
            next_retake_date=next_retake_date,
        )
        for row in competency_rows or []:
            result.competency_results.append(
                CompetencyResult(
                    competency_id=row["competency_id"],
                    score=row["score"],
                    max_score=row["max_score"],
                    percentage=row["percentage"],
                )
            )
        return self.add(result)

    def list_competency_results(self, result_id: int) -> list[CompetencyResult]:
        """Natija tarkibidagi kompetensiya ballarini qaytaradi (R8.3, R8.8)."""
        stmt = (
            select(CompetencyResult)
            .where(CompetencyResult.result_id == result_id)
            .order_by(CompetencyResult.id)
        )
        return list(self.session.scalars(stmt).all())


__all__ = ["ResultRepository"]
