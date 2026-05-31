"""Hisobot (admin/ekspert) javob sxemalari (R15, R20.4).

``/reports/*`` endpointlari uchun Pydantic **javob** modellari. Ular
``ReportService`` qaytaradigan frozen dataclasslardan (``AdminReport``,
``SectionReport``, ``IndividualDynamics``) ``model_validate`` orqali quriladi
(``from_attributes=True``).

Hisobotlar faqat o'qish uchun (so'rov tanasi yo'q): ekspert doirasini cheklash
``?expert_id`` emas, balki **principal** orqali amalga oshiriladi — router
so'rovchi ekspert bo'lsa ``expert_id=principal.user_id`` ni servisga uzatadi
(R15.6). Shu sababli bu modulda so'rov modeli yo'q.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class CompetencyExtremeResponse(BaseModel):
    """Eng past/yuqori jamlangan kompetensiya (R15.2)."""

    model_config = ConfigDict(from_attributes=True)

    competency_id: int = Field(..., description="Kompetensiya ID")
    competency_name: str | None = Field(default=None, description="Kompetensiya nomi")
    aggregate_percentage: Decimal = Field(
        ..., description="Jamlangan foiz (0–100, 2 kasr)"
    )


class AdminReportResponse(BaseModel):
    """Administrator umumiy hisoboti (R15.1, R15.2)."""

    model_config = ConfigDict(from_attributes=True)

    leaders_count: int = Field(..., description="Rahbarlar soni")
    test_takers_count: int = Field(..., description="Test topshirganlar soni")
    average_score: Decimal = Field(..., description="O'rtacha ball (0–100, 2 kasr)")
    lowest_competencies: list[CompetencyExtremeResponse] = Field(
        default_factory=list, description="Eng past jamlangan kompetensiya(lar)"
    )
    highest_competencies: list[CompetencyExtremeResponse] = Field(
        default_factory=list, description="Eng yuqori jamlangan kompetensiya(lar)"
    )


class SectionReportRowResponse(BaseModel):
    """Kesim (hudud/tashkilot) bo'yicha jamlanma qatori (R15.3, R15.4)."""

    model_config = ConfigDict(from_attributes=True)

    section_id: int | None = Field(default=None, description="Kesim ID (hudud/tashkilot)")
    section_name: str | None = Field(default=None, description="Kesim nomi")
    leaders_count: int = Field(..., description="Kesimdagi rahbarlar soni")
    test_takers_count: int = Field(..., description="Kesimda test topshirganlar soni")
    average_score: Decimal = Field(..., description="Kesim o'rtacha balli (2 kasr)")


class SectionReportResponse(BaseModel):
    """Kesim bo'yicha hisobot (R15.3, R15.4)."""

    model_config = ConfigDict(from_attributes=True)

    rows: list[SectionReportRowResponse] = Field(
        default_factory=list, description="Kesim qatorlari"
    )


class DynamicsPointResponse(BaseModel):
    """Individual dinamikadagi bitta nuqta — sana + foiz (R15.5)."""

    model_config = ConfigDict(from_attributes=True)

    achieved_at: datetime = Field(..., description="Natijaga erishilgan sana")
    percentage: Decimal = Field(..., description="Umumiy foiz (0–100)")


class IndividualDynamicsResponse(BaseModel):
    """Bitta rahbarning xronologik o'sish dinamikasi (R15.5)."""

    model_config = ConfigDict(from_attributes=True)

    leader_id: int = Field(..., description="Rahbar ID")
    points: list[DynamicsPointResponse] = Field(
        default_factory=list, description="Xronologik (o'suvchi) nuqtalar"
    )


__all__ = [
    "CompetencyExtremeResponse",
    "AdminReportResponse",
    "SectionReportRowResponse",
    "SectionReportResponse",
    "DynamicsPointResponse",
    "IndividualDynamicsResponse",
]
