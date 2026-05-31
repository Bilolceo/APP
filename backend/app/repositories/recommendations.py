"""Tavsiya repository (R10).

`recommendations` va `result_recommendations` jadvallari ustida ma'lumotlarga
kirish. Tavsiya_Moduli kompetensiya+daraja bo'yicha tavsiya tanlaydi va uni
natijaga bog'laydi. Tanlash mantig'i (aniq moslik yoki umumiy standart) domen
qatlamida; bu repository faqat so'rov/persistensiya bilan shug'ullanadi.

Konvensiyalar `base.py` bilan bir xil.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.recommendation import Recommendation, ResultRecommendation
from app.models.result import TestResult
from app.repositories.base import BaseRepository


class RecommendationRepository(BaseRepository[Recommendation]):
    """`recommendations` + `result_recommendations` uchun repository (R10)."""

    model = Recommendation

    def get_by_id(self, recommendation_id: int) -> Recommendation | None:
        """ID bo'yicha tavsiyani qaytaradi."""
        return self.session.get(Recommendation, recommendation_id)

    def list_all(self) -> list[Recommendation]:
        """Barcha tavsiyalarni qaytaradi (tanlash domen qatlamida)."""
        stmt = select(Recommendation).order_by(Recommendation.id)
        return list(self.session.scalars(stmt).all())

    def find_by(
        self, competency_id: int, level: str
    ) -> Recommendation | None:
        """Kompetensiya + daraja bo'yicha aniq tavsiyani qaytaradi (R10.1, R10.4)."""
        stmt = (
            select(Recommendation)
            .where(
                Recommendation.competency_id == competency_id,
                Recommendation.level == level,
            )
            .order_by(Recommendation.id)
            .limit(1)
        )
        return self.session.scalar(stmt)

    def get_general_fallback(
        self, level: str | None = None
    ) -> Recommendation | None:
        """Umumiy standart tavsiyani qaytaradi (R10.4).

        ``competency_id IS NULL`` bo'lgan tavsiya standart hisoblanadi. ``level``
        berilsa avval shu darajaga mos standart qidiriladi, topilmasa darajadan
        qat'i nazar birinchi standart tavsiya qaytariladi.
        """
        if level is not None:
            stmt = (
                select(Recommendation)
                .where(
                    Recommendation.competency_id.is_(None),
                    Recommendation.level == level,
                )
                .order_by(Recommendation.id)
                .limit(1)
            )
            matched = self.session.scalar(stmt)
            if matched is not None:
                return matched
        stmt = (
            select(Recommendation)
            .where(Recommendation.competency_id.is_(None))
            .order_by(Recommendation.id)
            .limit(1)
        )
        return self.session.scalar(stmt)

    def attach_to_result(
        self,
        *,
        result_id: int,
        competency_id: int | None = None,
        level: str | None = None,
        recommendation_id: int | None = None,
        text_snapshot: str | None = None,
    ) -> ResultRecommendation:
        """Tanlangan tavsiyani natijaga bog'laydi (R10.1).

        ``text_snapshot`` tavsiya matnini o'sha vaqtdagi holatda saqlaydi —
        tavsiya keyin o'zgarsa ham natija tarixiy matnni saqlab qoladi.
        """
        link = ResultRecommendation(
            result_id=result_id,
            competency_id=competency_id,
            level=level,
            recommendation_id=recommendation_id,
            text_snapshot=text_snapshot,
        )
        return self.add(link)

    def get_for_result(self, result_id: int) -> list[ResultRecommendation]:
        """Natijaga bog'langan tavsiyalarni qaytaradi (R10.2, R10.3)."""
        stmt = (
            select(ResultRecommendation)
            .where(ResultRecommendation.result_id == result_id)
            .order_by(ResultRecommendation.id)
        )
        return list(self.session.scalars(stmt).all())

    def latest_result_for_user(self, user_id: int) -> TestResult | None:
        """Foydalanuvchining eng so'nggi natijasini qaytaradi (R10.2).

        ``get_my_recommendations`` so'nggi natija tavsiyalarini ko'rsatish uchun
        ishlatadi.
        """
        stmt = (
            select(TestResult)
            .where(TestResult.user_id == user_id)
            .order_by(TestResult.created_at.desc(), TestResult.id.desc())
            .limit(1)
        )
        return self.session.scalar(stmt)


__all__ = ["RecommendationRepository"]
