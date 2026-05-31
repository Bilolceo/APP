"""Hisobot routeri — ``/reports/*`` (R15, R20.4).

Admin va ekspert uchun jamlangan hisobotlar. Router ``ReportService`` ustidagi
yupqa (thin) HTTP qatlami: servis metodini chaqiradi va natijani (frozen
dataclass) tasdiqlangan javob modeliga keltiradi.

RBAC qarori (hujjatlash — R4, R15.6): hisobotlar **jamlangan ko'rsatkichlar**
bo'lgani uchun ``require_expert`` bilan himoyalanadi — ya'ni **Ekspert yoki
Administrator** kira oladi; Rahbar 403 oladi (R4.5). So'rovchi ekspert bo'lsa,
router ``expert_id=principal.user_id`` ni servisga uzatadi, shunda hisobot faqat
shu ekspertga biriktirilgan rahbarlar bilan cheklanadi (R15.6); Administrator
uchun doira cheklanmaydi (``None`` — barcha rahbarlar, R4.3).

Bo'sh holat (R15.7): natija/kesim ma'lumoti bo'lmasa, xato emas, balki nol
qiymatli/bo'sh muvaffaqiyatli javob qaytadi (servis ta'minlaydi).

Endpointlar (design.md — "API Design / Hisobot"):

==================================  =====  ==================================
Yo'l                                Usul   Tavsif
==================================  =====  ==================================
``/reports/admin``                  GET    umumiy hisobot (R15.1, R15.2)
``/reports/by-region``              GET    hudud kesimi (R15.3)
``/reports/by-organization``        GET    tashkilot kesimi (R15.4)
``/reports/dynamics/{leader_id}``   GET    individual dinamika (R15.5)
==================================  =====  ==================================

Lokal prefiks ``/reports``; ``main.py`` uni ``/api/v1`` ostiga ulaydi (18.1).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import Principal, get_db
from app.api.middleware.rbac import (
    ROLE_ADMIN,
    ensure_expert_can_access_leader,
    require_expert,
)
from app.api.schemas import (
    AdminReportResponse,
    IndividualDynamicsResponse,
    SectionReportResponse,
)
from app.services.report_service import ReportService

router = APIRouter(
    prefix="/reports",
    tags=["reports"],
    # Rol darajasi: Ekspert yoki Administrator (R4.2, R4.3). Rahbar 403 (R4.5).
    dependencies=[Depends(require_expert)],
)


def _expert_scope(principal: Principal) -> int | None:
    """Ekspert doirasini aniqlaydi (R15.6).

    Administrator uchun doira cheklanmaydi (``None`` — barcha rahbarlar, R4.3);
    Ekspert uchun esa o'z identifikatori qaytariladi, shunda hisobot faqat
    biriktirilgan rahbarlar bilan cheklanadi (R15.6).
    """
    if principal.role == ROLE_ADMIN:
        return None
    return principal.user_id


@router.get(
    "/admin",
    response_model=AdminReportResponse,
    summary="Umumiy hisobot (admin/ekspert)",
)
def admin_report(
    principal: Principal = Depends(require_expert),
    db: Session = Depends(get_db),
) -> AdminReportResponse:
    """Umumiy jamlangan hisobotni qaytaradi (R15.1, R15.2).

    Ekspert uchun doira biriktirilgan rahbarlar bilan cheklanadi (R15.6); natija
    yo'q bo'lsa nol qiymatli/bo'sh holat (R15.7).
    """
    service = ReportService(db)
    report = service.admin_report(expert_id=_expert_scope(principal))
    return AdminReportResponse.model_validate(report)


@router.get(
    "/by-region",
    response_model=SectionReportResponse,
    summary="Hudud kesimi hisoboti",
)
def report_by_region(
    principal: Principal = Depends(require_expert),
    db: Session = Depends(get_db),
) -> SectionReportResponse:
    """Hudud kesimi bo'yicha hisobotni qaytaradi (R15.3).

    Ekspert uchun doira biriktirilgan rahbarlar bilan cheklanadi (R15.6).
    """
    service = ReportService(db)
    report = service.report_by_region(expert_id=_expert_scope(principal))
    return SectionReportResponse.model_validate(report)


@router.get(
    "/by-organization",
    response_model=SectionReportResponse,
    summary="Tashkilot kesimi hisoboti",
)
def report_by_organization(
    principal: Principal = Depends(require_expert),
    db: Session = Depends(get_db),
) -> SectionReportResponse:
    """Tashkilot kesimi bo'yicha hisobotni qaytaradi (R15.4).

    Ekspert uchun doira biriktirilgan rahbarlar bilan cheklanadi (R15.6).
    """
    service = ReportService(db)
    report = service.report_by_organization(expert_id=_expert_scope(principal))
    return SectionReportResponse.model_validate(report)


@router.get(
    "/dynamics/{leader_id}",
    response_model=IndividualDynamicsResponse,
    summary="Individual dinamika (RBAC)",
)
def individual_dynamics(
    leader_id: int,
    principal: Principal = Depends(require_expert),
    db: Session = Depends(get_db),
) -> IndividualDynamicsResponse:
    """Tanlangan rahbar natijalarining xronologik dinamikasi (R15.5).

    Egalik/biriktirilganlik: Administrator istalgan rahbarga kira oladi (R4.3);
    Ekspert faqat o'ziga biriktirilgan rahbarga kira oladi, aks holda 403
    (``ensure_expert_can_access_leader`` — R4.2, R15.6). Natija yo'q bo'lsa bo'sh
    ``points`` (R15.7).
    """
    ensure_expert_can_access_leader(principal, leader_id, db)
    service = ReportService(db)
    dynamics = service.individual_dynamics(leader_id)
    return IndividualDynamicsResponse.model_validate(dynamics)


__all__ = ["router"]
