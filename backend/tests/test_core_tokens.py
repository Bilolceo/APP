"""Birlik (unit) testlari — JWT token yordamchilari (``app.core.tokens``).

Bu testlar access/refresh token yaratish, dekodlash/tekshirish va bekor
qilish/aylantirish yordamchilari uchun aniq misol va chekka holatlarni
tekshiradi (R2.1, R2.3, R2.4, R2.5, R2.6, R17.2). Property-based test
(Property 4 — refresh tokenning yaroqliligi) alohida vazifada (9.2) qo'shiladi.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt
import pytest

from app.core.config import settings
from app.core.tokens import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    ACCESS_TOKEN_TYPE,
    REFRESH_TOKEN_EXPIRE_DAYS,
    REFRESH_TOKEN_TYPE,
    ExpiredTokenError,
    InvalidTokenError,
    create_access_token,
    create_refresh_token,
    decode_token,
    extract_expiry,
    extract_jti,
    extract_role,
    extract_subject,
    generate_jti,
    hash_token,
)

# Joriy (real) vaqt — tokenlar dekodlashda muddat (``exp``) tekshiruvi haqiqiy
# soatga nisbatan amalga oshadi, shuning uchun yangi yaratilgan token yaroqli
# bo'lishi uchun ``now`` joriy vaqtga yaqin bo'lishi shart. ``microsecond=0`` —
# JWT ``exp`` ni butun soniyaga (integer Unix timestamp) yaxlitlaydi, shuning
# uchun ``extract_expiry`` bilan aniq tenglik uchun mikrosekundlar nolga
# tushiriladi.
NOW = datetime.now(timezone.utc).replace(microsecond=0)


# ===========================================================================
# Access token yaratish va da'volar (R2.1, R17.2)
# ===========================================================================


def test_access_token_has_expected_claims_and_expiry() -> None:
    issued = create_access_token(user_id=42, role="Rahbar", now=NOW)
    claims = decode_token(issued.token, expected_type=ACCESS_TOKEN_TYPE)

    assert claims["sub"] == "42"
    assert claims["role"] == "Rahbar"
    assert claims["jti"] == issued.jti
    assert claims["type"] == ACCESS_TOKEN_TYPE
    # 15 daqiqalik muddat (R2.1).
    assert issued.expires_at == NOW + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    assert extract_expiry(claims) == issued.expires_at


def test_access_token_is_signed_with_hs256_secret() -> None:
    issued = create_access_token(user_id=1, role="Administrator", now=NOW)
    header = jwt.get_unverified_header(issued.token)
    assert header["alg"] == "HS256"
    # Noto'g'ri sir bilan tekshiruv yaroqsiz bo'ladi.
    with pytest.raises(InvalidTokenError):
        decode_token(issued.token, secret_key="boshqa-sir")


def test_each_token_gets_unique_jti() -> None:
    a = create_access_token(user_id=1, role="Ekspert", now=NOW)
    b = create_access_token(user_id=1, role="Ekspert", now=NOW)
    assert a.jti != b.jti


# ===========================================================================
# Refresh token (R2.1, R2.3, R2.6)
# ===========================================================================


def test_refresh_token_has_30_day_expiry_and_type() -> None:
    issued = create_refresh_token(user_id=7, now=NOW)
    claims = decode_token(issued.token, expected_type=REFRESH_TOKEN_TYPE)

    assert claims["sub"] == "7"
    assert claims["type"] == REFRESH_TOKEN_TYPE
    assert "role" not in claims
    assert issued.expires_at == NOW + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)


def test_token_type_mismatch_is_rejected() -> None:
    # Refresh kutilgan joyga access token kelsa -> rad etiladi (va aksincha).
    access = create_access_token(user_id=1, role="Rahbar", now=NOW)
    with pytest.raises(InvalidTokenError):
        decode_token(access.token, expected_type=REFRESH_TOKEN_TYPE)

    refresh = create_refresh_token(user_id=1, now=NOW)
    with pytest.raises(InvalidTokenError):
        decode_token(refresh.token, expected_type=ACCESS_TOKEN_TYPE)


# ===========================================================================
# Muddat va yaroqsizlik (R2.5, R2.6)
# ===========================================================================


def test_expired_token_raises_expired_error() -> None:
    past = NOW - timedelta(days=40)
    issued = create_access_token(user_id=1, role="Rahbar", now=past)
    with pytest.raises(ExpiredTokenError):
        decode_token(issued.token)


def test_tampered_token_raises_invalid_error() -> None:
    issued = create_access_token(user_id=1, role="Rahbar", now=NOW)
    tampered = issued.token[:-2] + ("aa" if issued.token[-2:] != "aa" else "bb")
    with pytest.raises(InvalidTokenError):
        decode_token(tampered)


def test_token_missing_required_claim_is_invalid() -> None:
    # ``jti`` siz qo'lda yasalgan token majburiy da'vo yo'qligi sabab rad etiladi.
    payload = {"sub": "1", "type": ACCESS_TOKEN_TYPE, "exp": NOW + timedelta(minutes=5)}
    raw = jwt.encode(payload, settings.jwt_secret_key, algorithm="HS256")
    with pytest.raises(InvalidTokenError):
        decode_token(raw)


# ===========================================================================
# Bekor qilish/aylantirish yordamchilari (R2.3, R2.4, R2.6)
# ===========================================================================


def test_hash_token_is_deterministic_and_differs_per_token() -> None:
    a = create_refresh_token(user_id=1, now=NOW)
    b = create_refresh_token(user_id=1, now=NOW)
    assert hash_token(a.token) == hash_token(a.token)  # deterministik
    assert hash_token(a.token) != hash_token(b.token)  # turli token -> turli xesh
    assert len(hash_token(a.token)) == 64  # SHA-256 hex


def test_hash_token_rejects_non_string() -> None:
    with pytest.raises(TypeError):
        hash_token(123)  # type: ignore[arg-type]


def test_extractors_return_claim_values() -> None:
    issued = create_access_token(user_id=99, role="Ekspert", now=NOW)
    claims = decode_token(issued.token)
    assert extract_jti(claims) == issued.jti
    assert extract_subject(claims) == "99"
    assert extract_role(claims) == "Ekspert"
    assert extract_expiry(claims) == issued.expires_at


def test_extract_role_none_for_refresh_token() -> None:
    issued = create_refresh_token(user_id=1, now=NOW)
    claims = decode_token(issued.token)
    assert extract_role(claims) is None


def test_generate_jti_is_unique() -> None:
    assert generate_jti() != generate_jti()
