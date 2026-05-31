"""Ekspert baholash routeri — ``/expert/*`` (R13, R20.4).

Ekspert tomonidan biriktirilgan rahbarni baholash va biriktirilgan rahbarlar
ro'yxati. Router ``ExpertReviewService`` ustidagi yupqa (thin) HTTP qatlami:
so'rovni tuzilgan Pydantic modeli sifatida qabul qiladi, ``expert_id`` ni
**so'rovdan emas, autentifikatsiyalangan principaldan** oladi
(``principal.user_id``) va servis metodini chaqiradi (R13.5).

Rol darajasi: ``require_expert`` (Ekspert yoki Administrator) — Rahbar 403 oladi
(R4.5). Resurs darajasidagi **biriktirilganlik** (ekspert rahbarga biriktirilganmi)
``ExpertReviewService.submit_review`` ichida tekshiriladi: biriktirilmagan bo'lsa
servis ``PermissionDeniedError`` (``code="forbidden"``) ko'taradi, markazlashtirilgan
handler uni 403 ga keltiradi (R13.5). Yaroqsiz/to'liqsiz baho ``ValidationError``
(400) beradi (R13.3, R13.4).

GET /expert/leaders — biriktirilgan rahbarlar (MVP implementatsiyasi)
--------------------------------------------------------------------
Tizimda alohida ``expert_assignments`` jadvali yo'q; biriktirilganlik MVP da
**bir xil tashkilot** asosida aniqlanadi (``ExpertReviewRepository.is_expert_assigned``
bilan izchil — qarang ``app.repositories.expert``). Shu sababli bu endpoint
ekspert bilan **bir tashkilotdagi** Rahbar rolidagi foydalanuvchilarni qaytaradi.
Administrator chaqirsa, tashkilot doirasi yo'q (Administrator barcha rahbarlarga
kira oladi, R4.3), shuning uchun barcha Rahbarlar qaytadi. Kelajakda alohida
``expert_assignments`` jadvali qo'shilsa, bu mantiq shu jadvalga ko'chiriladi —
endpoint shartnomasi o'zgarmaydi.

Endpointlar (design.md — "API Design / Ekspert"):

=======================  ======  =========================================
Yo'l                     Usul    Tavsif
=======================  ======  =========================================
``/expert/reviews``      POST    6 mezon bo'yicha baholash; 201 (R13)
``/expert/leaders``      GET     biriktirilgan rahbarlar ro'yxati (R13.5)
=======================  ======  =========================================

Lokal prefiks ``/expert``; ``main.py`` uni ``/api/v1`` ostiga ulaydi (18.1).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import Principal, get_db
from app.api.middleware.rbac import ROLE_ADMIN, ROLE_LEADER, require_expert
from app.api.schemas import (
    ExpertLeaderResponse,
    ExpertReviewRequest,
    ExpertReviewResponse,
)
from app.domain.expert import EXPERT_CRITERIA
from app.repositories.users import UserRepository
from app.services.expert_review_service import ExpertReviewService

router = APIRouter(
    prefix="/expert",
    tags=["expert"],
    # Rol darajasi: Ekspert yoki Administrator (R4.2). Resurs darajasidagi
    # biriktirilganlik servis ichida tekshiriladi (R13.5).
    dependencies=[Depends(require_expert)],
)


@router.post(
    "/reviews",
    response_model=ExpertReviewResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ekspert baholash",
)
def submit_review(
    payload: ExpertReviewRequest,
    principal: Principal = Depends(require_expert),
    db: Session = Depends(get_db),
) -> ExpertReviewResponse:
    """6 mezon bo'yicha rahbarni baholaydi (R13.1–R13.6).

    ``expert_id`` autentifikatsiyalangan principaldan olinadi (R13.5). Servis:
    mezonlarni validatsiya qiladi (yaroqsiz -> 400, R13.3/R13.4), biriktirilganlikni
    tekshiradi (biriktirilmagan -> 403, R13.5), sharhni saqlaydi va o'rtacha
    bahoni rahbarning so'nggi natijasiga qo'shadi (R13.2). ``ExpertReviewService``
    o'zi ``commit`` qiladi va bildirishnoma yuboradi (R13.6).
    """
    scores = {criterion: getattr(payload, criterion) for criterion in EXPERT_CRITERIA}
    service = ExpertReviewService(db)
    outcome = service.submit_review(principal.user_id, payload.leader_id, scores)
    return ExpertReviewResponse.model_validate(outcome)


@router.get(
    "/leaders",
    response_model=list[ExpertLeaderResponse],
    summary="Biriktirilgan rahbarlar ro'yxati",
)
def list_assigned_leaders(
    principal: Principal = Depends(require_expert),
    db: Session = Depends(get_db),
) -> list[ExpertLeaderResponse]:
    """Ekspertga biriktirilgan rahbarlarni qaytaradi (R13.5 — MVP).

    Biriktirilganlik bir xil tashkilot asosida (modul docstring'iga qarang).
    Administrator chaqirsa barcha Rahbarlar qaytadi (R4.3). Tashkiloti
    biriktirilmagan (NULL) ekspert uchun bo'sh ro'yxat qaytadi.
    """
    users = UserRepository(db).list_all()
    leaders = [
        u
        for u in users
        if u.role is not None and u.role.name == ROLE_LEADER
    ]
    if principal.role != ROLE_ADMIN:
        # Ekspert doirasi: bir xil (NULL bo'lmagan) tashkilotdagi rahbarlar.
        expert = UserRepository(db).get_by_id(principal.user_id)
        expert_org = expert.organization_id if expert is not None else None
        if expert_org is None:
            return []
        leaders = [
            leader
            for leader in leaders
            if leader.organization_id == expert_org
        ]
    return [ExpertLeaderResponse.model_validate(leader) for leader in leaders]


__all__ = ["router"]
