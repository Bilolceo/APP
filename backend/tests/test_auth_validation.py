"""Birlik (unit) testlari — autentifikatsiya validatsiyasi va parol xeshlash.

Bu testlar `app.domain.auth_validation` sof validatorlari (R1.3, R1.5, R1.6,
R1.7) hamda `app.core.security` parol xeshlash funksiyalari (R1.4, R17.1)
uchun aniq misol va chekka holatlarni tekshiradi. Property-based testlar
(Property 1, 2) alohida vazifalarda (8.2, 8.3) qo'shiladi.
"""

from __future__ import annotations

from app.core.security import hash_password, verify_password
from app.domain.auth_validation import (
    validate_password,
    validate_phone,
    validate_required,
    validate_role,
)


# --- validate_phone (R1.6) ---


def test_validate_phone_accepts_valid_number() -> None:
    assert validate_phone("+998901234567") is True


def test_validate_phone_rejects_wrong_prefix() -> None:
    assert validate_phone("+997901234567") is False


def test_validate_phone_rejects_wrong_length() -> None:
    assert validate_phone("+99890123456") is False  # 12 belgi
    assert validate_phone("+9989012345678") is False  # 14 belgi


def test_validate_phone_rejects_non_string() -> None:
    assert validate_phone(None) is False
    assert validate_phone(998901234567) is False


# --- validate_password (R1.5) ---


def test_validate_password_accepts_boundaries() -> None:
    assert validate_password("a" * 8) is True
    assert validate_password("a" * 64) is True


def test_validate_password_rejects_out_of_range() -> None:
    assert validate_password("a" * 7) is False
    assert validate_password("a" * 65) is False


def test_validate_password_rejects_non_string() -> None:
    assert validate_password(None) is False
    assert validate_password(12345678) is False


# --- validate_role (R1.7) ---


def test_validate_role_accepts_whitelisted() -> None:
    assert validate_role("Rahbar") is True
    assert validate_role("Ekspert") is True
    assert validate_role("Administrator") is True


def test_validate_role_rejects_unknown_or_miscased() -> None:
    assert validate_role("admin") is False
    assert validate_role("rahbar") is False
    assert validate_role("") is False
    assert validate_role(None) is False


# --- validate_required (R1.3) ---


def test_validate_required_rejects_missing_and_blank() -> None:
    assert validate_required(None) is False
    assert validate_required("") is False
    assert validate_required("   ") is False
    assert validate_required("\t\n ") is False


def test_validate_required_accepts_non_blank() -> None:
    assert validate_required("Ism") is True
    assert validate_required("  x  ") is True
    assert validate_required(0) is True  # satr emas, mavjud deb qabul qilinadi


# --- hash_password / verify_password (R1.4, R17.1) ---


def test_hash_password_does_not_store_plaintext() -> None:
    password = "S3cretPass!"
    hashed = hash_password(password)
    assert hashed != password
    assert password not in hashed


def test_hash_password_uses_random_salt() -> None:
    password = "S3cretPass!"
    assert hash_password(password) != hash_password(password)


def test_verify_password_round_trip() -> None:
    password = "S3cretPass!"
    hashed = hash_password(password)
    assert verify_password(password, hashed) is True
    assert verify_password("wrong-password", hashed) is False


def test_verify_password_handles_invalid_hash() -> None:
    assert verify_password("anything", "not-a-valid-hash") is False
    assert verify_password("anything", "") is False
