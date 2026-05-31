"""Analitika javob sxemalari — ``/analytics/*`` (R9, R20.1).

``/analytics/me`` (GET) endpointi uchun javob modellari. Router
``AnalyticsService`` ustidagi yupqa HTTP qatlami: servis ``AnalyticsView``
(frozen DTO) qaytaradi, bu yerdagi modellar uni tasdiqlangan javob sxemasiga
keltiradi (``from_attributes=True``).

Natija yo'q bo'lsa muvaffaqiyatli bo'sh holat (``has_results=False``,
``overall_score=0.00``, bo'sh ro'yxatlar) qaytadi — bu xato emas (R9.7).
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class CompetencyDistributionResponse(BaseModel):
    """Kompetensiya taqsimotidagi bitta yozuv (R9.2).

    Radar / progress bar / toifa ball kartochkasi uchun ma'lumot.
    """

    model_config = ConfigDict(from_attributes=True)

    competency_id: int = Field(..., description="Kompetensiya ID")
    competency_name: str | None = Field(default=None, description="Kompetensiya nomi")
    percentage: Decimal = Field(..., description="Jamlangan foiz (0–100)")
    level: str = Field(..., description="Jamlangan foizdan aniqlangan daraja")


class GrowthPointResponse(BaseModel):
    """O'sish dinamikasidagi bitta nuqta — sana bilan belgilangan foiz (R9.1)."""

    model_config = ConfigDict(from_attributes=True)

    achieved_at: datetime = Field(..., description="Natija sanasi/vaqti")
    percentage: Decimal = Field(..., description="Shu natijaning umumiy foizi")


class CompetencyRefResponse(BaseModel):
    """Kompetensiyaga ishora (kuchli / rivojlantirilishi lozim ro'yxatlari) (R9.5, R9.6)."""

    model_config = ConfigDict(from_attributes=True)

    competency_id: int = Field(..., description="Kompetensiya ID")
    competency_name: str | None = Field(default=None, description="Kompetensiya nomi")


class AnalyticsResponse(BaseModel):
    """Foydalanuvchi analitikasining to'liq javobi (R9.1–R9.7).

    ``AnalyticsView`` (frozen DTO) dan ``model_validate`` orqali quriladi.
    """

    model_config = ConfigDict(from_attributes=True)

    overall_score: Decimal = Field(..., description="Jamlangan o'rtacha foiz (0–100)")
    distribution: list[CompetencyDistributionResponse] = Field(
        default_factory=list, description="Kompetensiya taqsimoti (radar/progress/card)"
    )
    dynamics: list[GrowthPointResponse] = Field(
        default_factory=list, description="Xronologik o'sish dinamikasi (line chart)"
    )
    growth_diff: Decimal | None = Field(
        default=None, description="Joriy vs oldingi farq; bitta natijada None (R9.4)"
    )
    strongest: list[CompetencyRefResponse] = Field(
        default_factory=list, description="Eng kuchli kompetensiya(lar)"
    )
    to_develop: list[CompetencyRefResponse] = Field(
        default_factory=list, description="Rivojlantirilishi lozim kompetensiya(lar)"
    )
    result_count: int = Field(default=0, description="Hisobga olingan natijalar soni")
    has_results: bool = Field(default=False, description="Kamida bitta natija bormi")


class SectionAnalyticsResponse(BaseModel):
    """Tashkilot/hudud kesimi bo'yicha jamlangan analitika javobi (R15.3, R15.4).

    ``/analytics/organization/{id}`` va ``/analytics/region/{id}`` endpointlari
    uchun. ``ReportService.report_by_organization``/``report_by_region``
    natijasidagi mos kesim qatori (``SectionReportRow``) dan quriladi; kesimda
    ma'lumot bo'lmasa nol qiymatli bo'sh holat qaytadi (R15.7).
    """

    model_config = ConfigDict(from_attributes=True)

    section_id: int | None = Field(default=None, description="Kesim (tashkilot/hudud) ID")
    section_name: str | None = Field(default=None, description="Kesim nomi")
    leaders_count: int = Field(default=0, description="Kesimdagi noyob rahbarlar soni")
    test_takers_count: int = Field(
        default=0, description="Kesimda test topshirgan rahbarlar soni"
    )
    average_score: Decimal = Field(..., description="Kesim o'rtacha balli (0–100)")


__all__ = [
    "CompetencyDistributionResponse",
    "GrowthPointResponse",
    "CompetencyRefResponse",
    "AnalyticsResponse",
    "SectionAnalyticsResponse",
]
