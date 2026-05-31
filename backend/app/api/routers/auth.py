"""Autentifikatsiya routeri — ``/auth/*`` (R1, R2, R3, R20.1, R20.2).

Ushbu router ``AuthService`` ustidagi yupqa (thin) HTTP qatlami: u so'rovni
tuzilgan Pydantic modeli sifatida qabul qiladi, servis metodini chaqiradi va
javobni tasdiqlangan javob modeliga keltiradi. **Biznes validatsiyasi va xatolar
servis qatlamida** hal qilinadi; router servis istisnolarini ushlamaydi va
markazlashtirilgan exception handler (``app.api.errors``) ularni yagona tuzilgan
HTTP javobiga keltiradi (R20.6).

Endpointlar (design.md — "API Design / Autentifikatsiya"):

==============================  ====  =====================================
Yo'l                            Usul  Tavsif
==============================  ====  =====================================
``/auth/register``              POST  ro'yxatdan o'tish; 201 (R1)
``/auth/login``                 POST  TokenPair; 200 / 401 / 429 (R2.1)
``/auth/refresh``               POST  yangi access token; 200 / 401 (R2.3)
``/auth/logout``                POST  tokenlarni bekor qiladi; 200 (R2.4)
``/auth/forgot-password``       POST  reset kod; umumiy 200 (R3.1, R3.2)
``/auth/reset-password``        POST  parolni yangilaydi; 200 / 400 (R3.3)
==============================  ====  =====================================

Lokal prefiks ``/auth``; ``main.py`` uni ``/api/v1`` ostiga ulaydi (vazifa 18.1).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.api.deps import bearer_scheme, get_db
from app.api.schemas import (
    AccessTokenResponse,
    ForgotPasswordRequest,
    LoginRequest,
    LogoutRequest,
    MessageResponse,
    ProfileResponse,
    RefreshRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenPairResponse,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=ProfileResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ro'yxatdan o'tish",
)
def register(
    payload: RegisterRequest,
    db: Session = Depends(get_db),
) -> ProfileResponse:
    """Yangi hisob yaratadi (R1.1–R1.7).

    Validatsiya (telefon formati, parol uzunligi, rol, takroriy telefon) servis
    qatlamida; yaroqsiz so'rov ``ValidationError``/``ConflictError`` ko'taradi va
    markazlashtirilgan handler uni 400/409 ga keltiradi (R1.2, R1.3, R20.6).
    """
    service = AuthService(db)
    user = service.register(payload.model_dump())
    return ProfileResponse.model_validate(user)


@router.post(
    "/login",
    response_model=TokenPairResponse,
    summary="Tizimga kirish",
)
def login(
    payload: LoginRequest,
    db: Session = Depends(get_db),
) -> TokenPairResponse:
    """Telefon va parol bilan kirib token juftligini qaytaradi (R2.1).

    Noto'g'ri ma'lumot yoki bloklangan hisob ``AuthError`` ko'taradi (401);
    xato xabari qaysi maydon noto'g'ri ekanini oshkor qilmaydi (R2.2, R2.7).
    """
    service = AuthService(db)
    tokens = service.login(payload.phone, payload.password)
    return TokenPairResponse(**tokens)


@router.post(
    "/refresh",
    response_model=AccessTokenResponse,
    summary="Token yangilash",
)
def refresh(
    payload: RefreshRequest,
    db: Session = Depends(get_db),
) -> AccessTokenResponse:
    """Yaroqli refresh token asosida yangi access token beradi (R2.3, R2.6).

    Bekor qilingan/muddati o'tgan/yaroqsiz refresh token ``AuthError`` (401).
    """
    service = AuthService(db)
    tokens = service.refresh(payload.refresh_token)
    return AccessTokenResponse(**tokens)


@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Tizimdan chiqish",
)
def logout(
    payload: LogoutRequest,
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> MessageResponse:
    """Joriy access (va berilgan bo'lsa refresh) tokenni bekor qiladi (R2.4).

    Access token ``Authorization: Bearer`` sarlavhasidan olinadi. Amal bardoshli:
    servis yaroqsiz access token bo'lsa ham refresh tokenni bekor qilishga
    harakat qiladi (R2.4).
    """
    access_token = credentials.credentials if credentials else ""
    service = AuthService(db)
    service.logout(access_token, payload.refresh_token)
    return MessageResponse(message="Tizimdan muvaffaqiyatli chiqildi")


@router.post(
    "/forgot-password",
    response_model=MessageResponse,
    summary="Parolni tiklashni boshlash",
)
def forgot_password(
    payload: ForgotPasswordRequest,
    db: Session = Depends(get_db),
) -> MessageResponse:
    """Parolni tiklash kodini yuboradi; har doim umumiy javob qaytaradi (R3.1, R3.2).

    Hisob mavjudligini oshkor qilmaslik uchun javob mavjud/mavjud emas holatlarda
    bir xil bo'ladi (R3.2).
    """
    service = AuthService(db)
    result = service.request_password_reset(payload.phone)
    return MessageResponse(**result)


@router.post(
    "/reset-password",
    response_model=MessageResponse,
    summary="Parolni yangilash",
)
def reset_password(
    payload: ResetPasswordRequest,
    db: Session = Depends(get_db),
) -> MessageResponse:
    """Tasdiqlash kodi bilan parolni yangilaydi (R3.3–R3.7).

    Yaroqsiz/muddati o'tgan kod yoki kuchsiz parol ``ValidationError`` (400).
    """
    service = AuthService(db)
    result = service.confirm_password_reset(
        payload.phone, payload.code, payload.new_password
    )
    return MessageResponse(**result)


__all__ = ["router"]
