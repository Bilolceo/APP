"""Foydalanuvchi / profil routeri — ``/users/*`` (R5, R4, R20.1).

Profil ko'rish va tahrirlash hamda boshqa foydalanuvchi profilini RBAC bilan
o'qish. Router ``ProfileService`` ustidagi yupqa HTTP qatlami: autentifikatsiya
``get_current_principal`` bog'liqligi orqali, egalik tekshiruvi esa
``ensure_self_or_admin`` yordamchisi orqali (R4.1, R4.3) amalga oshiriladi.

Endpointlar (design.md — "API Design / Foydalanuvchi / Profil"):

=====================  ======  ======================================
Yo'l                   Usul    Tavsif
=====================  ======  ======================================
``/users/me``          GET     o'z profili (R5.1)
``/users/me``          PATCH   profilni yangilash; telefon o'zgarmas (R5.2–R5.4)
``/users/{id}``        GET     RBAC bo'yicha boshqa profil (R4)
=====================  ======  ======================================

Lokal prefiks ``/users``; ``main.py`` uni ``/api/v1`` ostiga ulaydi (vazifa 18.1).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import Principal, get_current_principal, get_db
from app.api.middleware.rbac import ensure_self_or_admin
from app.api.schemas import ProfileResponse, ProfileUpdateRequest
from app.services.profile_service import ProfileService

router = APIRouter(prefix="/users", tags=["users"])


@router.get(
    "/me",
    response_model=ProfileResponse,
    summary="Joriy profil",
)
def get_my_profile(
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> ProfileResponse:
    """Joriy foydalanuvchining to'liq profilini qaytaradi (R5.1)."""
    service = ProfileService(db)
    profile = service.get_profile(principal.user_id)
    return ProfileResponse.model_validate(profile)


@router.patch(
    "/me",
    response_model=ProfileResponse,
    summary="Profilni yangilash",
)
def update_my_profile(
    payload: ProfileUpdateRequest,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> ProfileResponse:
    """Tahrirlanadigan profil maydonlarini yangilaydi (R5.2, R5.3, R5.4).

    Faqat **yuborilgan** maydonlar patch sifatida uzatiladi (``exclude_unset``),
    shunda validatsiya faqat o'sha maydonlarga qo'llanadi. Telefonni o'zgartirishga
    urinish servis qatlamida rad etiladi (R5.4); yaroqsiz qiymat 400 beradi (R5.3).
    """
    patch = payload.model_dump(exclude_unset=True)
    service = ProfileService(db)
    profile = service.update_profile(principal.user_id, patch)
    return ProfileResponse.model_validate(profile)


@router.get(
    "/{user_id}",
    response_model=ProfileResponse,
    summary="Foydalanuvchi profili (RBAC)",
)
def get_user_profile(
    user_id: int,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> ProfileResponse:
    """Berilgan foydalanuvchi profilini RBAC bo'yicha qaytaradi (R4.1, R4.3).

    Rahbar faqat o'z profiliga, Administrator esa istalgan profilga kira oladi;
    aks holda ``ensure_self_or_admin`` 403 ko'taradi (R4.5). Mavjud bo'lmagan
    foydalanuvchi servisda ``NotFoundError`` (404) beradi.
    """
    ensure_self_or_admin(principal, user_id)
    service = ProfileService(db)
    profile = service.get_profile(user_id)
    return ProfileResponse.model_validate(profile)


__all__ = ["router"]
