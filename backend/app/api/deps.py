"""Umumiy FastAPI bog'liqliklari (dependencies) — DB sessiyasi va autentifikatsiya.

Ushbu modul routerlar (vazifa 17.x) qayta ishlatadigan ikkita asosiy
bog'liqlikni taqdim etadi:

- :func:`get_db` — har bir so'rov uchun SQLAlchemy ``Session`` ochadi va so'rov
  yakunida yopadi.
- :func:`get_current_principal` — ``Authorization: Bearer <token>`` sarlavhasidan
  access tokenni ajratib oladi, imzo/muddat/turini tekshiradi, ``jti`` ni
  blacklist orqali rad etadi va kichik :class:`Principal` qiymatini qaytaradi
  (R2.5, R17.2).

Dizayn qarori (design.md — "Security Design"): autentifikatsiya **blanket
middleware** emas, balki **bog'liqlik** (dependency) sifatida amalga oshiriladi.
Bu ochiq endpointlar (``/auth/login``, ``/auth/register`` va boshqalar) ni
himoyalanganlardan ajratishni va RBAC (vazifa 16.5) ni shu ``Principal`` ustiga
qurishni osonlashtiradi.

Yaroqsiz holatlar (token yo'q / muddati o'tgan / imzo yaroqsiz / blacklistda)
``AuthError`` ko'taradi; markazlashtirilgan handler (``app.api.errors``) uni
401 ga keltiradi (R2.5).
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.core.tokens import (
    ACCESS_TOKEN_TYPE,
    ExpiredTokenError,
    InvalidTokenError,
    TokenError,
    decode_token,
    extract_jti,
    extract_role,
    extract_subject,
)
from app.repositories.tokens import TokenRepository
from app.services.errors import AuthError

__all__ = [
    "Principal",
    "get_db",
    "get_current_principal",
    "bearer_scheme",
]


# ---------------------------------------------------------------------------
# DB sessiyasi bog'liqligi
# ---------------------------------------------------------------------------


def get_db() -> Iterator[Session]:
    """So'rov doirasidagi SQLAlchemy ``Session`` ni beradi (yield) va yopadi.

    FastAPI ``yield`` li bog'liqliklarni qo'llab-quvvatlaydi: so'rov boshlanishida
    sessiya ochiladi, so'rov yakunida (xato bo'lsa ham) ``finally`` blokida
    yopiladi. Tranzaksiya chegarasi (commit/rollback) servis qatlami yoki router
    zimmasida — bu yerda faqat sessiya hayot sikli boshqariladi.

    Yields:
        Faol ``Session``.
    """
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Autentifikatsiya bog'liqligi
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Principal:
    """Autentifikatsiyalangan so'rovchining minimal identifikatori.

    Maydonlar:
    - ``user_id``: foydalanuvchi identifikatori (``sub`` da'vosidan, ``int``).
    - ``role``: foydalanuvchi roli (``role`` da'vosi) — RBAC (vazifa 16.5) uchun.
    - ``jti``: access tokenning noyob identifikatori (blacklist/logout uchun).
    """

    user_id: int
    role: str
    jti: str


#: HTTP Bearer sxemasi. ``auto_error=False`` — sarlavha yo'q bo'lsa FastAPI
#: o'zining 403 ini ko'tarmaydi; biz o'rniga ``AuthError`` (401) ko'taramiz (R2.5).
bearer_scheme = HTTPBearer(auto_error=False)


def get_current_principal(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> Principal:
    """Joriy so'rov uchun autentifikatsiyalangan :class:`Principal` ni qaytaradi.

    Bosqichlar (R2.5, R17.2):
    1. ``Authorization: Bearer <token>`` sarlavhasi mavjudligini tekshiradi.
    2. Tokenni access token sifatida dekodlaydi (imzo, muddat, ``type``).
    3. ``jti`` blacklistda emasligini ``TokenRepository`` orqali tekshiradi.
    4. ``Principal(user_id, role, jti)`` ni quradi va qaytaradi.

    Args:
        request: joriy so'rov (kelajakda kontekst uchun; hozir ishlatilmaydi).
        credentials: Bearer sxemasidan ajratilgan ma'lumot (yoki ``None``).
        db: DB sessiyasi (blacklist tekshiruvi uchun).

    Returns:
        Autentifikatsiyalangan ``Principal``.

    Raises:
        AuthError: token yo'q / muddati o'tgan / imzo yaroqsiz / turi noto'g'ri /
            ``jti`` blacklistda / da'volari yaroqsiz (hammasi -> 401, R2.5).
    """
    # 1. Bearer sarlavhasi mavjudligini tekshirish (R2.5).
    if credentials is None or not credentials.credentials:
        raise AuthError("Autentifikatsiya talab qilinadi")

    token = credentials.credentials

    # 2. Tokenni access token sifatida dekodlash va tekshirish (R2.5, R17.2).
    try:
        claims = decode_token(token, expected_type=ACCESS_TOKEN_TYPE)
    except ExpiredTokenError as exc:
        raise AuthError("Token muddati o'tgan") from exc
    except (InvalidTokenError, TokenError) as exc:
        raise AuthError("Token yaroqsiz") from exc

    # 3. Majburiy da'volarni ajratib olish (jti/sub/role) (R17.2).
    try:
        jti = extract_jti(claims)
        subject = extract_subject(claims)
    except InvalidTokenError as exc:
        raise AuthError("Token yaroqsiz") from exc

    role = extract_role(claims)
    if role is None:
        # Access tokenda rol bo'lishi shart; bo'lmasa yaroqsiz hisoblanadi.
        raise AuthError("Token yaroqsiz")

    try:
        user_id = int(subject)
    except (TypeError, ValueError) as exc:
        raise AuthError("Token yaroqsiz") from exc

    # 4. Bekor qilingan (blacklist) tokenni rad etish (R2.4, R2.5).
    tokens = TokenRepository(db)
    if tokens.is_jti_blacklisted(jti):
        raise AuthError("Token bekor qilingan")

    return Principal(user_id=user_id, role=role, jti=jti)
