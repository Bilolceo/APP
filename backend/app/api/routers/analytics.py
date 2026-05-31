"""Analitika routeri — ``/analytics/*`` (R9, R15, R20.4).

Shaxsiy analitika hamda tashkilot/hudud kesimi bo'yicha jamlangan analitika
endpointlari. Router servislar ustidagi yupqa HTTP qatlami:

- ``/analytics/me`` — ``AnalyticsService.get_my_analytics`` (R9.1–R9.7);
  autentifikatsiyalangan har qanday foydalanuvchi o'z analitikasini oladi.
- ``/analytics/organization/{id}`` va ``/analytics/region/{id}`` — jamlangan
  (kesim) analitika ``ReportService`` orqali (R15.3, R15.4).

RBAC qarori (hujjatlash — R4, R15.6): kesim (tashkilot/hudud) analitikasi
**jamlangan ko'rsatkichlar** bo'lgani uchun u Hisobot_Moduli (R15) doirasiga
kiradi. MVP'da bu endpointlar ``require_expert`` bilan himoyalanadi — ya'ni
**Ekspert yoki Administrator** kira oladi (Rahbar kira olmaydi -> 403). Ekspert
so'rovda ``expert_id`` doirasi uzatiladi, shunda hisobot faqat shu ekspertga
biriktirilgan rahbarlar bilan cheklanadi (R15.6); Administrator uchun doira
cheklanmaydi (R4.3). Bu tanlov ``ReportService`` ning ``expert_id`` parametri va
RBAC ``require_expert`` guardiga to'g'ridan-to'g'ri mos keladi.

Bo'sh holat (R9.7, R15.7): natija yoki kesim ma'lumoti bo'lmasa, xato emas,
balki nol qiymatli/bo'sh muvaffaqiyatli javob qaytadi.

Endpointlar (design.md — "API Design / Analitika"):

=====================================  =====  =================================
Yo'l                                   Usul   Tavsif
=====================================  =====  =================================
``/analytics/me``                      GET    shaxsiy analitika (R9.1–R9.7)
``/analytics/organization/{id}``       GET    tashkilot kesimi (RBAC; R15.4)
``/analytics/region/{id}``             GET    hudud kesimi (RBAC; R15.3)
=====================================  =====  =================================

Lokal prefiks ``/analytics``; ``main.py`` uni ``/api/v1`` ostiga ulaydi (18.1).
"""

from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import Principal, get_current_principal, get_db
from app.api.middleware.rbac import ROLE_ADMIN, require_expert
from app.api.schemas import AnalyticsResponse, SectionAnalyticsResponse
from app.services.analytics_service import AnalyticsService
from app.services.report_service import ReportService, SectionReport, SectionReportRow

router = APIRouter(prefix="/analytics", tags=["analytics"])

#: Bo'sh kesim holati uchun nol o'rtacha (R15.7) — domen bilan izchil.
_ZERO_PERCENT = Decimal("0.00")


@router.get(
    "/me",
    response_model=AnalyticsResponse,
    summary="Shaxsiy analitika",
)
def get_my_analytics(
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> AnalyticsResponse:
    """Joriy foydalanuvchining analitikasini qaytaradi (R9.1–R9.7).

    Natija yo'q bo'lsa muvaffaqiyatli bo'sh holat (``has_results=False``,
    ``overall_score=0.00``) qaytadi — bu xato emas (R9.7).
    """
    service = AnalyticsService(db)
    view = service.get_my_analytics(principal.user_id)
    return AnalyticsResponse.model_validate(view)


def _expert_scope(principal: Principal) -> int | None:
    """Ekspert doirasini aniqlaydi (R15.6).

    Administrator uchun doira cheklanmaydi (``None`` — barcha rahbarlar, R4.3);
    Ekspert uchun esa o'z identifikatori qaytariladi, shunda hisobot faqat
    biriktirilgan rahbarlar bilan cheklanadi (R15.6).
    """
    if principal.role == ROLE_ADMIN:
        return None
    return principal.user_id


def _row_for_section(
    report: SectionReport, section_id: int
) -> SectionReportRow | None:
    """Hisobotdan berilgan kesim qatorini topadi (yoki ``None``)."""
    for row in report.rows:
        if row.section_id == section_id:
            return row
    return None


def _to_section_response(
    section_id: int, row: SectionReportRow | None
) -> SectionAnalyticsResponse:
    """Kesim qatorini javobga aylantiradi; qator yo'q bo'lsa bo'sh holat (R15.7)."""
    if row is None:
        return SectionAnalyticsResponse(
            section_id=section_id,
            section_name=None,
            leaders_count=0,
            test_takers_count=0,
            average_score=_ZERO_PERCENT,
        )
    return SectionAnalyticsResponse.model_validate(row)


@router.get(
    "/organization/{organization_id}",
    response_model=SectionAnalyticsResponse,
    summary="Tashkilot kesimi analitikasi (RBAC)",
)
def get_organization_analytics(
    organization_id: int,
    principal: Principal = Depends(require_expert),
    db: Session = Depends(get_db),
) -> SectionAnalyticsResponse:
    """Tashkilot kesimi bo'yicha jamlangan analitikani qaytaradi (R15.4).

    Faqat Ekspert yoki Administrator kira oladi (``require_expert``); Rahbar 403
    oladi (R4.5). Ekspert uchun doira biriktirilgan rahbarlar bilan cheklanadi
    (R15.6). Kesimda ma'lumot bo'lmasa nol qiymatli bo'sh holat (R15.7).
    """
    service = ReportService(db)
    report = service.report_by_organization(expert_id=_expert_scope(principal))
    return _to_section_response(
        organization_id, _row_for_section(report, organization_id)
    )


@router.get(
    "/region/{region_id}",
    response_model=SectionAnalyticsResponse,
    summary="Hudud kesimi analitikasi (RBAC)",
)
def get_region_analytics(
    region_id: int,
    principal: Principal = Depends(require_expert),
    db: Session = Depends(get_db),
) -> SectionAnalyticsResponse:
    """Hudud kesimi bo'yicha jamlangan analitikani qaytaradi (R15.3).

    Faqat Ekspert yoki Administrator kira oladi (``require_expert``); Rahbar 403
    oladi (R4.5). Ekspert uchun doira biriktirilgan rahbarlar bilan cheklanadi
    (R15.6). Kesimda ma'lumot bo'lmasa nol qiymatli bo'sh holat (R15.7).
    """
    service = ReportService(db)
    report = service.report_by_region(expert_id=_expert_scope(principal))
    return _to_section_response(region_id, _row_for_section(report, region_id))


__all__ = ["router"]
