"""Qurilma tokeni (push) routeri — ``/devices/token`` (R16, R20.4).

Push bildirishnomalar uchun qurilma tokenini ro'yxatdan o'tkazish va bekor
qilish. Router ``DeviceTokenRepository`` ustidagi yupqa (thin) HTTP qatlami:
token har doim **autentifikatsiyalangan principalga** bog'lanadi
(``principal.user_id``) — ``user_id`` so'rovdan emas, tokendan olinadi (R16.1),
shu tarzda foydalanuvchi faqat o'z qurilmasini ro'yxatga oladi.

Kirish: autentifikatsiyalangan har qanday foydalanuvchi (``get_current_principal``).

Endpointlar (design.md — "API Design / Qurilma tokeni"):

=========================  =======  =====================================
Yo'l                       Usul     Tavsif
=========================  =======  =====================================
``/devices/token``         POST     tokenni ro'yxatga olish; 201 (R16.1)
``/devices/token``         DELETE   tokenni bekor qilish (R16.6)
=========================  =======  =====================================

Lokal prefiks ``/devices``; ``main.py`` uni ``/api/v1`` ostiga ulaydi (18.1).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import Principal, get_current_principal, get_db
from app.api.schemas import (
    DeviceTokenInvalidateRequest,
    DeviceTokenRegisterRequest,
    DeviceTokenResponse,
    MessageResponse,
)
from app.repositories.devices import DeviceTokenRepository

router = APIRouter(prefix="/devices", tags=["devices"])


@router.post(
    "/token",
    response_model=DeviceTokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Qurilma tokenini ro'yxatga olish",
)
def register_device_token(
    payload: DeviceTokenRegisterRequest,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> DeviceTokenResponse:
    """Qurilma tokenini joriy foydalanuvchiga bog'lab ro'yxatga oladi (R16.1).

    Idempotent: bir xil token allaqachon mavjud bo'lsa, egasiga/platformaga
    yangilanadi va yaroqli (``is_valid=true``) holatga keltiriladi (repozitoriy
    ``register``). Token har doim ``principal.user_id`` ga bog'lanadi.
    """
    devices = DeviceTokenRepository(db)
    device = devices.register(
        user_id=principal.user_id,
        token=payload.token,
        platform=payload.platform,
    )
    db.commit()
    db.refresh(device)
    return DeviceTokenResponse.model_validate(device)


@router.delete(
    "/token",
    response_model=MessageResponse,
    summary="Qurilma tokenini bekor qilish",
)
def invalidate_device_token(
    payload: DeviceTokenInvalidateRequest,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> MessageResponse:
    """Qurilma tokenini yaroqsiz deb belgilaydi — ``is_valid=false`` (R16.6).

    Bardoshli (idempotent): token topilmasa ham xato bermaydi — bildirishnoma
    filtrida yaroqsiz/yo'q token baribir o'tkazib yuboriladi (R16.6). Token
    so'rovchiga tegishli bo'lmasa ham yaroqsiz qilinadi (faqat shu token
    o'chiriladi; egasi o'zgartirilmaydi).
    """
    devices = DeviceTokenRepository(db)
    devices.invalidate(payload.token)
    db.commit()
    return MessageResponse(message="Qurilma tokeni bekor qilindi")


__all__ = ["router"]
