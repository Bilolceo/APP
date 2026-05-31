"""Ekspert sharhi repository (R13).

`expert_reviews` jadvali ustida ma'lumotlarga kirish. Ekspert_Moduli rahbarni
6 mezon bo'yicha baholaydi va biriktirilganlikni tekshiradi.

Biriktirilganlik (assignment) haqida eslatma
--------------------------------------------
design.md ning ER diagrammasida ``expert_assignments`` munosabati ko'rsatilgan,
ammo MVP sxemasida (task 2.1 modellari) alohida ``expert_assignments`` jadvali
mavjud emas. Shu sababli biriktirilganlik MVP da **bir xil tashkilot** (shared
organization) asosida aniqlanadi: ekspert va rahbar bir tashkilotga tegishli
bo'lsa, ekspert shu rahbarni baholashga biriktirilgan hisoblanadi (R4.2, R13.5).
Kelajakda alohida ``expert_assignments`` jadvali qo'shilsa, `is_expert_assigned`
shu jadvalga asoslanib qayta yoziladi — interfeys o'zgarmaydi.

Konvensiyalar `base.py` bilan bir xil.
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.expert import ExpertReview
from app.models.user import User
from app.repositories.base import BaseRepository


class ExpertReviewRepository(BaseRepository[ExpertReview]):
    """`expert_reviews` uchun repository (R13)."""

    model = ExpertReview

    def get_by_id(self, review_id: int) -> ExpertReview | None:
        """ID bo'yicha ekspert sharhini qaytaradi."""
        return self.session.get(ExpertReview, review_id)

    def list_for_leader(self, leader_id: int) -> list[ExpertReview]:
        """Rahbar bo'yicha barcha ekspert sharhlarini qaytaradi (R13)."""
        stmt = (
            select(ExpertReview)
            .where(ExpertReview.leader_id == leader_id)
            .order_by(ExpertReview.created_at.desc(), ExpertReview.id.desc())
        )
        return list(self.session.scalars(stmt).all())

    def list_by_expert(self, expert_id: int) -> list[ExpertReview]:
        """Ekspert bergan barcha sharhlarni qaytaradi."""
        stmt = (
            select(ExpertReview)
            .where(ExpertReview.expert_id == expert_id)
            .order_by(ExpertReview.created_at.desc(), ExpertReview.id.desc())
        )
        return list(self.session.scalars(stmt).all())

    def create(
        self,
        *,
        expert_id: int,
        leader_id: int,
        management_culture: int,
        teamwork: int,
        pedagogical_process: int,
        innovation: int,
        documentation: int,
        strategic_planning: int,
        average_score: Decimal,
    ) -> ExpertReview:
        """Yangi ekspert sharhini yaratadi (R13.1, R13.2).

        6 mezon validatsiyasi va o'rtacha hisoblash domen/servis qatlamida
        bajariladi; bu metod faqat hisoblangan qiymatlarni persist qiladi.
        """
        review = ExpertReview(
            expert_id=expert_id,
            leader_id=leader_id,
            management_culture=management_culture,
            teamwork=teamwork,
            pedagogical_process=pedagogical_process,
            innovation=innovation,
            documentation=documentation,
            strategic_planning=strategic_planning,
            average_score=average_score,
        )
        return self.add(review)

    def is_expert_assigned(self, expert_id: int, leader_id: int) -> bool:
        """Ekspert berilgan rahbarga biriktirilganligini tekshiradi (R4.2, R13.5).

        MVP qoidasi: ekspert va rahbar bir xil (NULL bo'lmagan) tashkilotga
        tegishli bo'lsa biriktirilgan hisoblanadi. Tashkilot biriktirilmagan
        (NULL) bo'lsa biriktirilganlik yo'q deb qaraladi.

        Eslatma: alohida ``expert_assignments`` jadvali qo'shilganda bu mantiq
        shu jadvalga ko'chiriladi (yuqoridagi modul-darajali eslatmaga qarang).
        """
        expert = self.session.get(User, expert_id)
        leader = self.session.get(User, leader_id)
        if expert is None or leader is None:
            return False
        if expert.organization_id is None or leader.organization_id is None:
            return False
        return expert.organization_id == leader.organization_id


__all__ = ["ExpertReviewRepository"]
