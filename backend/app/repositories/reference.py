"""Ma'lumotnoma (reference) repositorylari.

`roles`, `regions`, `organizations`, `competencies` jadvallari ustida oddiy
ma'lumotlarga kirish. Bu jadvallar asosan o'qish uchun (lookup) ishlatiladi;
Admin_Moduli kompetensiyalarni CRUD qiladi.

Eslatma: ishlatilayotgan kompetensiyani o'chirishni rad etish (R14.8) — biznes
qoidasi servis qatlamida `QuestionRepository.is_competency_used` orqali
tekshiriladi; bu yerda **enforce qilinmaydi** (repository yupqa qoladi).

Konvensiyalar `base.py` bilan bir xil.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.reference import Competency, Organization, Region, Role
from app.repositories.base import BaseRepository


class RoleRepository(BaseRepository[Role]):
    """`roles` uchun repository (R1.7)."""

    model = Role

    def get_by_id(self, role_id: int) -> Role | None:
        """ID bo'yicha rolni qaytaradi."""
        return self.session.get(Role, role_id)

    def get_by_name(self, name: str) -> Role | None:
        """Nom bo'yicha rolni qaytaradi (Rahbar/Ekspert/Administrator — R1.7)."""
        stmt = select(Role).where(Role.name == name)
        return self.session.scalar(stmt)

    def create(self, *, name: str) -> Role:
        """Yangi rol yaratadi."""
        return self.add(Role(name=name))


class RegionRepository(BaseRepository[Region]):
    """`regions` uchun repository."""

    model = Region

    def get_by_id(self, region_id: int) -> Region | None:
        """ID bo'yicha hududni qaytaradi."""
        return self.session.get(Region, region_id)

    def get_by_name(self, name: str) -> Region | None:
        """Nom bo'yicha hududni qaytaradi."""
        stmt = select(Region).where(Region.name == name)
        return self.session.scalar(stmt)

    def create(self, *, name: str) -> Region:
        """Yangi hudud yaratadi."""
        return self.add(Region(name=name))


class OrganizationRepository(BaseRepository[Organization]):
    """`organizations` uchun repository."""

    model = Organization

    def get_by_id(self, organization_id: int) -> Organization | None:
        """ID bo'yicha tashkilotni qaytaradi."""
        return self.session.get(Organization, organization_id)

    def get_by_name(self, name: str) -> Organization | None:
        """Nom bo'yicha tashkilotni qaytaradi."""
        stmt = select(Organization).where(Organization.name == name)
        return self.session.scalar(stmt)

    def list_for_region(self, region_id: int) -> list[Organization]:
        """Hudud bo'yicha tashkilotlarni qaytaradi (hisobot kesimi — R15.4)."""
        stmt = (
            select(Organization)
            .where(Organization.region_id == region_id)
            .order_by(Organization.id)
        )
        return list(self.session.scalars(stmt).all())

    def create(
        self,
        *,
        name: str,
        region_id: int | None = None,
        org_type: str | None = None,
    ) -> Organization:
        """Yangi tashkilot yaratadi."""
        return self.add(
            Organization(name=name, region_id=region_id, org_type=org_type)
        )


class CompetencyRepository(BaseRepository[Competency]):
    """`competencies` uchun repository (R8, R14)."""

    model = Competency

    def get_by_id(self, competency_id: int) -> Competency | None:
        """ID bo'yicha kompetensiyani qaytaradi."""
        return self.session.get(Competency, competency_id)

    def get_by_name(self, name: str) -> Competency | None:
        """Nom bo'yicha kompetensiyani qaytaradi."""
        stmt = select(Competency).where(Competency.name == name)
        return self.session.scalar(stmt)

    def create(
        self, *, name: str, description: str | None = None
    ) -> Competency:
        """Yangi kompetensiya yaratadi (R14.1)."""
        return self.add(Competency(name=name, description=description))


__all__ = [
    "RoleRepository",
    "RegionRepository",
    "OrganizationRepository",
    "CompetencyRepository",
]
