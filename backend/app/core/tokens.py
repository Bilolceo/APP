"""JWT token yordamchilari — sof kripto/da'vo (claim) qatlami.

Ushbu modul access va refresh JWT tokenlarini **yaratish**, **tekshirish** va
ular ustida bekor qilish/aylantirish (revocation/rotation) uchun zarur sof
yordamchilarni taqdim etadi. Modul ataylab **I/O dan mustaqil**: u ma'lumotlar
bazasiga murojaat qilmaydi va blacklist/`refresh_tokens` jadvallarini
o'qimaydi/yozmaydi. DB qidiruvlari servis qatlami (AuthService — vazifa 9.3) va
middleware (vazifa 16.1) zimmasida qoladi; bu yerda faqat kripto va da'vo
(claim) bilan ishlovchi, aniq nomlangan funksiyalar joylashadi.

Dizayn (design.md — "Security Design / Autentifikatsiya (JWT)"):
- **Access token (R2.1, R2.5, R17.2):** 15 daqiqa amal qiladi; da'volari
  ``sub`` (user_id), ``role``, ``jti`` (noyob identifikator) va ``exp``;
  ``HS256`` algoritmi va ``jwt_secret_key`` bilan imzolanadi. Har bir himoyalangan
  so'rovda imzo, muddat va ``jti`` blacklistda emasligi tekshiriladi.
- **Refresh token (R2.1, R2.3, R2.4, R2.6):** 30 kun amal qiladi; DB'da
  ``refresh_tokens.token_hash`` ko'rinishida saqlanadi (xom token emas). Logout
  yoki aylantirish (rotation)'da ``revoked=true``.
- **Bekor qilish (R2.4):** access token ``jti`` -> ``token_blacklist.jti``;
  refresh token -> ``revoked``.

Bekor qilish/aylantirishni qo'llab-quvvatlash uchun:
- ``generate_jti`` — har bir token uchun noyob ``jti``.
- ``hash_token`` — refresh tokenni DB'da saqlash/qidirish uchun SHA-256 xesh
  (``refresh_tokens.token_hash``); xom token hech qachon saqlanmaydi.
- ``extract_jti`` / ``extract_expiry`` — dekodlangan da'volardan ``jti`` (blacklist
  uchun) va muddat tugash vaqtini (DB'da ``expires_at`` uchun) ajratib oladi.

Vaqt belgilari UTC-aware ``datetime`` ko'rinishida ishlatiladi. Barcha yaratuvchi
funksiyalar ``now`` ni tashqaridan qabul qiladi (deterministik testlar uchun).
"""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Final

import jwt

from app.core.config import settings

# ---------------------------------------------------------------------------
# Konstantalar (config'dan standart, lekin funksiyalar parametrlangan)
# ---------------------------------------------------------------------------

#: Imzolash algoritmi (R17.2) — design'ga ko'ra ``HS256``.
JWT_ALGORITHM: Final[str] = settings.jwt_algorithm

#: Access token amal qilish muddati daqiqalarda (R2.1) — standart 15.
ACCESS_TOKEN_EXPIRE_MINUTES: Final[int] = settings.access_token_expire_minutes

#: Refresh token amal qilish muddati kunlarda (R2.1) — standart 30.
REFRESH_TOKEN_EXPIRE_DAYS: Final[int] = settings.refresh_token_expire_days

#: Da'volardagi ``type`` qiymatlari — access va refresh tokenni farqlash uchun.
ACCESS_TOKEN_TYPE: Final[str] = "access"
REFRESH_TOKEN_TYPE: Final[str] = "refresh"

# Dekodlashda majburiy bo'lishi kerak bo'lgan da'volar. Bizning tokenlarimiz
# har doim ushbu da'volarni o'z ichiga oladi; ularning yo'qligi tokenni yaroqsiz
# qiladi (begona/buzilgan token rad etiladi).
_REQUIRED_CLAIMS: Final[tuple[str, ...]] = ("exp", "sub", "jti", "type")


# ---------------------------------------------------------------------------
# Xatoliklar — aniq, oshkor sabab bilan (R2.5, R2.6, R17.2)
# ---------------------------------------------------------------------------


class TokenError(Exception):
    """JWT tokenni dekodlash/tekshirishdagi umumiy xato (bazaviy sinf)."""


class ExpiredTokenError(TokenError):
    """Token imzosi to'g'ri, lekin amal qilish muddati o'tgan (R2.5, R2.6)."""


class InvalidTokenError(TokenError):
    """Token imzosi yaroqsiz, buzilgan, majburiy da'vosi yo'q yoki turi noto'g'ri."""


# ---------------------------------------------------------------------------
# Natija tuzilmasi
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class IssuedToken:
    """Yangi chiqarilgan (issued) JWT token va u bilan bog'liq metama'lumot.

    Servis qatlami ushbu qiymatlardan tokenni qaytarish hamda DB'da saqlash
    uchun foydalanadi — qayta dekodlashga hojat qolmaydi:
    - ``token``: imzolangan, kodlangan JWT satri (mijozga qaytariladi).
    - ``jti``: tokenning noyob identifikatori (access uchun ``token_blacklist.jti``;
      refresh aylantirishni kuzatish uchun).
    - ``expires_at``: tokenning amal qilish tugash vaqti (UTC-aware) — DB'dagi
      ``expires_at`` ustunlariga mos (``refresh_tokens``/``token_blacklist``).
    """

    token: str
    jti: str
    expires_at: datetime


# ---------------------------------------------------------------------------
# Yordamchi (pure) funksiyalar — jti, vaqt, xesh
# ---------------------------------------------------------------------------


def generate_jti() -> str:
    """Token uchun noyob identifikator (``jti``) yaratadi.

    UUID4'ning 32 belgili hex ko'rinishi qaytariladi; bu ``token_blacklist.jti``
    (``VARCHAR(64)``) ustuniga bemalol sig'adi va amalda to'qnashuvsiz.

    Returns:
        32 belgili hex satr (masalan ``"3f1c…"``).
    """
    return uuid.uuid4().hex


def _utcnow() -> datetime:
    """Joriy UTC-aware vaqtni qaytaradi (ichki yordamchi)."""
    return datetime.now(timezone.utc)


def access_token_expiry(
    now: datetime | None = None,
    *,
    minutes: int = ACCESS_TOKEN_EXPIRE_MINUTES,
) -> datetime:
    """Access token amal qilish tugash vaqtini hisoblaydi (R2.1).

    Args:
        now: hisoblash boshlang'ich nuqtasi (UTC-aware). ``None`` bo'lsa joriy
            UTC vaqt olinadi.
        minutes: amal qilish muddati daqiqalarda (standart — config 15 daqiqa).

    Returns:
        ``now + minutes`` (UTC-aware ``datetime``).
    """
    base = now if now is not None else _utcnow()
    return base + timedelta(minutes=minutes)


def refresh_token_expiry(
    now: datetime | None = None,
    *,
    days: int = REFRESH_TOKEN_EXPIRE_DAYS,
) -> datetime:
    """Refresh token amal qilish tugash vaqtini hisoblaydi (R2.1).

    Args:
        now: hisoblash boshlang'ich nuqtasi (UTC-aware). ``None`` bo'lsa joriy
            UTC vaqt olinadi.
        days: amal qilish muddati kunlarda (standart — config 30 kun).

    Returns:
        ``now + days`` (UTC-aware ``datetime``).
    """
    base = now if now is not None else _utcnow()
    return base + timedelta(days=days)


def hash_token(token: str) -> str:
    """Tokenni DB'da saqlash/qidirish uchun SHA-256 xeshiga o'tkazadi (R2.3, R2.6).

    Refresh token DB'da xom holda emas, balki ``refresh_tokens.token_hash``
    ko'rinishida saqlanadi. Servis qatlami yangilash (refresh) so'rovida kelgan
    xom tokenni shu funksiya bilan xeshlab, saqlangan xesh bilan solishtiradi.
    Xeshlash deterministik bo'lgani uchun bir xil token har doim bir xil xesh
    beradi (qidiruv kaliti sifatida ishlatish mumkin).

    Args:
        token: xeshlanadigan xom JWT satri.

    Returns:
        64 belgili hex SHA-256 digest.

    Raises:
        TypeError: ``token`` satr (``str``) bo'lmasa.
    """
    if not isinstance(token, str):
        raise TypeError("token must be a string")
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Token yaratish (R2.1, R17.2)
# ---------------------------------------------------------------------------


def create_access_token(
    *,
    user_id: int | str,
    role: str,
    jti: str | None = None,
    now: datetime | None = None,
    expires_minutes: int = ACCESS_TOKEN_EXPIRE_MINUTES,
    secret_key: str | None = None,
    algorithm: str = JWT_ALGORITHM,
) -> IssuedToken:
    """15 daqiqalik access JWT tokenini yaratadi (R2.1, R17.2).

    Token da'volari: ``sub`` (user_id, satr ko'rinishida), ``role``, ``jti``,
    ``exp`` (muddat), shuningdek ``iat`` (chiqarilgan vaqt) va ``type``
    (``"access"``). Token ``HS256`` (yoki berilgan ``algorithm``) bilan
    ``jwt_secret_key`` yordamida imzolanadi.

    Args:
        user_id: foydalanuvchi identifikatori. JWT ``sub`` standartiga muvofiq
            satrga aylantiriladi (chaqiruvchi qayta ``int()`` qila oladi).
        role: foydalanuvchi roli (Rahbar/Ekspert/Administrator).
        jti: token uchun noyob identifikator. ``None`` bo'lsa avtomatik yaratiladi.
        now: chiqarilish vaqti (UTC-aware). ``None`` bo'lsa joriy UTC vaqt.
        expires_minutes: amal qilish muddati daqiqalarda (standart 15).
        secret_key: imzolash siri. ``None`` bo'lsa config'dagi ``jwt_secret_key``.
        algorithm: imzolash algoritmi (standart ``HS256``).

    Returns:
        ``IssuedToken`` — kodlangan token, ``jti`` va ``expires_at``.
    """
    issued_at = now if now is not None else _utcnow()
    expires_at = access_token_expiry(issued_at, minutes=expires_minutes)
    token_jti = jti if jti is not None else generate_jti()
    key = secret_key if secret_key is not None else settings.jwt_secret_key

    payload: dict[str, Any] = {
        "sub": str(user_id),
        "role": role,
        "jti": token_jti,
        "type": ACCESS_TOKEN_TYPE,
        "iat": issued_at,
        "exp": expires_at,
    }
    token = jwt.encode(payload, key, algorithm=algorithm)
    return IssuedToken(token=token, jti=token_jti, expires_at=expires_at)


def create_refresh_token(
    *,
    user_id: int | str,
    jti: str | None = None,
    now: datetime | None = None,
    expires_days: int = REFRESH_TOKEN_EXPIRE_DAYS,
    secret_key: str | None = None,
    algorithm: str = JWT_ALGORITHM,
) -> IssuedToken:
    """30 kunlik refresh JWT tokenini yaratadi (R2.1).

    Token da'volari: ``sub`` (user_id), ``jti``, ``exp``, ``iat`` va ``type``
    (``"refresh"``). Refresh token DB'da xom holda saqlanmaydi — servis qatlami
    ``hash_token`` orqali uning xeshini ``refresh_tokens.token_hash`` ga yozadi
    va ``expires_at`` ni shu yerdagi ``expires_at`` qiymatidan oladi.

    Args:
        user_id: foydalanuvchi identifikatori (satrga aylantiriladi).
        jti: noyob identifikator. ``None`` bo'lsa avtomatik yaratiladi.
        now: chiqarilish vaqti (UTC-aware). ``None`` bo'lsa joriy UTC vaqt.
        expires_days: amal qilish muddati kunlarda (standart 30).
        secret_key: imzolash siri. ``None`` bo'lsa config'dagi ``jwt_secret_key``.
        algorithm: imzolash algoritmi (standart ``HS256``).

    Returns:
        ``IssuedToken`` — kodlangan token, ``jti`` va ``expires_at``.
    """
    issued_at = now if now is not None else _utcnow()
    expires_at = refresh_token_expiry(issued_at, days=expires_days)
    token_jti = jti if jti is not None else generate_jti()
    key = secret_key if secret_key is not None else settings.jwt_secret_key

    payload: dict[str, Any] = {
        "sub": str(user_id),
        "jti": token_jti,
        "type": REFRESH_TOKEN_TYPE,
        "iat": issued_at,
        "exp": expires_at,
    }
    token = jwt.encode(payload, key, algorithm=algorithm)
    return IssuedToken(token=token, jti=token_jti, expires_at=expires_at)


# ---------------------------------------------------------------------------
# Token dekodlash / tekshirish (R2.5, R2.6, R17.2)
# ---------------------------------------------------------------------------


def decode_token(
    token: str,
    *,
    expected_type: str | None = None,
    verify_exp: bool = True,
    secret_key: str | None = None,
    algorithm: str = JWT_ALGORITHM,
) -> dict[str, Any]:
    """JWT tokenni dekodlaydi, imzo va muddatini tekshiradi (R2.5, R17.2).

    Imzo ``jwt_secret_key`` va ``HS256`` bilan tekshiriladi. ``verify_exp=True``
    bo'lganda muddat ham tekshiriladi. Majburiy da'volar (``exp``, ``sub``,
    ``jti``, ``type``) mavjud bo'lishi shart — aks holda token yaroqsiz.

    Args:
        token: dekodlanadigan kodlangan JWT satri.
        expected_type: kutilgan token turi (``"access"`` yoki ``"refresh"``).
            Berilsa va ``type`` da'vosi mos kelmasa, ``InvalidTokenError``
            ko'tariladi (masalan, refresh token kutilgan joyga access token
            kelsa).
        verify_exp: muddatni tekshirish (standart ``True``).
        secret_key: imzo siri. ``None`` bo'lsa config'dagi ``jwt_secret_key``.
        algorithm: imzo algoritmi (standart ``HS256``).

    Returns:
        Tokenning da'volari (claims) lug'ati.

    Raises:
        ExpiredTokenError: token imzosi to'g'ri, lekin muddati o'tgan (R2.5, R2.6).
        InvalidTokenError: imzo yaroqsiz, token buzilgan, majburiy da'vo yo'q
            yoki ``type`` kutilganga mos emas (R2.5, R17.2).
    """
    key = secret_key if secret_key is not None else settings.jwt_secret_key
    try:
        claims: dict[str, Any] = jwt.decode(
            token,
            key,
            algorithms=[algorithm],
            options={
                "verify_exp": verify_exp,
                "require": list(_REQUIRED_CLAIMS),
            },
        )
    except jwt.ExpiredSignatureError as exc:
        # Muddat o'tgan — imzo to'g'ri bo'lsa-da, token endi yaroqsiz (R2.5, R2.6).
        raise ExpiredTokenError("token muddati o'tgan") from exc
    except jwt.InvalidTokenError as exc:
        # Imzo yaroqsiz, buzilgan yoki majburiy da'vo yo'q (R2.5, R17.2).
        raise InvalidTokenError("token yaroqsiz") from exc

    if expected_type is not None and claims.get("type") != expected_type:
        raise InvalidTokenError(
            f"kutilgan token turi '{expected_type}', lekin '{claims.get('type')}'"
        )

    return claims


# ---------------------------------------------------------------------------
# Da'vo (claim) ajratuvchilar — bekor qilish/aylantirish uchun (R2.3, R2.4, R2.6)
# ---------------------------------------------------------------------------


def extract_jti(claims: dict[str, Any]) -> str:
    """Dekodlangan da'volardan ``jti`` ni ajratib oladi (R2.4).

    Middleware/servis access tokenni dekodlagach, uning ``jti`` sini
    ``token_blacklist`` da bor-yo'qligini tekshirish (yoki logout'da blacklistga
    qo'shish) uchun foydalanadi.

    Args:
        claims: ``decode_token`` qaytargan da'volar lug'ati.

    Returns:
        Token ``jti`` qiymati.

    Raises:
        InvalidTokenError: ``jti`` da'vosi mavjud bo'lmasa.
    """
    jti = claims.get("jti")
    if not isinstance(jti, str) or not jti:
        raise InvalidTokenError("jti da'vosi yo'q")
    return jti


def extract_subject(claims: dict[str, Any]) -> str:
    """Dekodlangan da'volardan ``sub`` (user_id) ni satr sifatida qaytaradi.

    Args:
        claims: ``decode_token`` qaytargan da'volar lug'ati.

    Returns:
        ``sub`` qiymati (satr). Chaqiruvchi kerak bo'lsa ``int()`` qila oladi.

    Raises:
        InvalidTokenError: ``sub`` da'vosi mavjud bo'lmasa.
    """
    sub = claims.get("sub")
    if not isinstance(sub, str) or not sub:
        raise InvalidTokenError("sub da'vosi yo'q")
    return sub


def extract_role(claims: dict[str, Any]) -> str | None:
    """Dekodlangan da'volardan ``role`` ni qaytaradi (mavjud bo'lsa).

    Refresh tokenda ``role`` bo'lmaydi, shuning uchun ``None`` qaytishi mumkin.

    Args:
        claims: ``decode_token`` qaytargan da'volar lug'ati.

    Returns:
        ``role`` qiymati yoki ``None``.
    """
    role = claims.get("role")
    return role if isinstance(role, str) else None


def extract_expiry(claims: dict[str, Any]) -> datetime:
    """Dekodlangan da'volardan muddat tugash vaqtini (``exp``) qaytaradi.

    Servis qatlami buni ``token_blacklist.expires_at`` (yoki refresh uchun
    ``refresh_tokens.expires_at``) ustuniga yozish uchun ishlatadi — shunda
    bekor qilingan yozuvlar muddati tugagach tozalanishi mumkin.

    Args:
        claims: ``decode_token`` qaytargan da'volar lug'ati.

    Returns:
        ``exp`` ga mos UTC-aware ``datetime``.

    Raises:
        InvalidTokenError: ``exp`` da'vosi mavjud bo'lmasa yoki noto'g'ri turda.
    """
    exp = claims.get("exp")
    if not isinstance(exp, (int, float)):
        raise InvalidTokenError("exp da'vosi yo'q yoki noto'g'ri")
    return datetime.fromtimestamp(exp, tz=timezone.utc)


__all__ = [
    # Konstantalar
    "JWT_ALGORITHM",
    "ACCESS_TOKEN_EXPIRE_MINUTES",
    "REFRESH_TOKEN_EXPIRE_DAYS",
    "ACCESS_TOKEN_TYPE",
    "REFRESH_TOKEN_TYPE",
    # Xatoliklar
    "TokenError",
    "ExpiredTokenError",
    "InvalidTokenError",
    # Natija tuzilmasi
    "IssuedToken",
    # Yordamchi (pure) funksiyalar
    "generate_jti",
    "access_token_expiry",
    "refresh_token_expiry",
    "hash_token",
    # Yaratish
    "create_access_token",
    "create_refresh_token",
    # Dekodlash / tekshirish
    "decode_token",
    # Da'vo ajratuvchilar
    "extract_jti",
    "extract_subject",
    "extract_role",
    "extract_expiry",
]
