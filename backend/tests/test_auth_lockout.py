"""Birlik (unit) testlari — login bloklash va parolni tiklash kodi sof mantig'i.

Bu testlar `app.domain.auth_lockout` sof funksiyalari uchun aniq misol va chekka
holatlarni tekshiradi (R2.7 login bloklash; R3.1, R3.4, R3.5, R3.6, R3.7 reset
kod). Property-based testlar (Property 3, 8, 9) alohida vazifalarda (8.5, 8.6,
8.7) qo'shiladi.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.domain.auth_lockout import (
    LOGIN_LOCKOUT_MINUTES,
    MAX_FAILED_LOGIN_ATTEMPTS,
    MAX_RESET_CODE_ATTEMPTS,
    RESET_CODE_TTL_MINUTES,
    ResetCodeStatus,
    check_reset_code,
    compute_reset_code_expiry,
    is_locked,
    is_new_password_acceptable,
    is_reset_code_expired,
    is_reset_code_format_valid,
    is_reset_code_invalidated,
    register_failed_attempt,
    register_failed_code_attempt,
    reset_after_success,
)

NOW = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


# ===========================================================================
# Login bloklash (R2.7)
# ===========================================================================


def test_register_failed_attempt_increments_without_lock_below_threshold() -> None:
    state = register_failed_attempt(0, NOW)
    assert state.failed_count == 1
    assert state.locked_until is None


def test_register_failed_attempt_locks_at_threshold() -> None:
    # 4 -> 5: chegaraga yetadi va 15 daqiqaga bloklanadi.
    state = register_failed_attempt(MAX_FAILED_LOGIN_ATTEMPTS - 1, NOW)
    assert state.failed_count == MAX_FAILED_LOGIN_ATTEMPTS
    assert state.locked_until == NOW + timedelta(minutes=LOGIN_LOCKOUT_MINUTES)


def test_register_failed_attempt_stays_locked_above_threshold() -> None:
    state = register_failed_attempt(MAX_FAILED_LOGIN_ATTEMPTS, NOW)
    assert state.failed_count == MAX_FAILED_LOGIN_ATTEMPTS + 1
    assert state.locked_until == NOW + timedelta(minutes=LOGIN_LOCKOUT_MINUTES)


def test_register_failed_attempt_respects_custom_threshold() -> None:
    state = register_failed_attempt(2, NOW, threshold=3, lockout_minutes=10)
    assert state.failed_count == 3
    assert state.locked_until == NOW + timedelta(minutes=10)


def test_is_locked_none_returns_false() -> None:
    assert is_locked(None, NOW) is False


def test_is_locked_true_before_expiry() -> None:
    locked_until = NOW + timedelta(minutes=15)
    assert is_locked(locked_until, NOW) is True


def test_is_locked_false_at_and_after_expiry() -> None:
    locked_until = NOW + timedelta(minutes=15)
    assert is_locked(locked_until, locked_until) is False  # chegara: ochiq
    assert is_locked(locked_until, locked_until + timedelta(seconds=1)) is False


def test_reset_after_success_clears_state() -> None:
    state = reset_after_success()
    assert state.failed_count == 0
    assert state.locked_until is None


# ===========================================================================
# Reset kod formati (R3.5)
# ===========================================================================


def test_reset_code_format_accepts_six_digits() -> None:
    assert is_reset_code_format_valid("123456") is True
    assert is_reset_code_format_valid("000000") is True


def test_reset_code_format_rejects_wrong_length() -> None:
    assert is_reset_code_format_valid("12345") is False
    assert is_reset_code_format_valid("1234567") is False


def test_reset_code_format_rejects_non_digits_and_non_str() -> None:
    assert is_reset_code_format_valid("12345a") is False
    assert is_reset_code_format_valid("12 456") is False
    assert is_reset_code_format_valid("１２３４５６") is False  # unicode raqamlar
    assert is_reset_code_format_valid(123456) is False
    assert is_reset_code_format_valid(None) is False


# ===========================================================================
# Reset kod muddati (R3.1, R3.4)
# ===========================================================================


def test_compute_reset_code_expiry_adds_ttl() -> None:
    assert compute_reset_code_expiry(NOW) == NOW + timedelta(
        minutes=RESET_CODE_TTL_MINUTES
    )


def test_is_reset_code_expired_boundary_is_inclusive_valid() -> None:
    expires_at = compute_reset_code_expiry(NOW)
    # Aynan tugash vaqtida hali yaroqli (R3.4 — "ko'p vaqt o'tgan bo'lsa").
    assert is_reset_code_expired(expires_at, expires_at) is False
    assert is_reset_code_expired(expires_at, expires_at + timedelta(seconds=1)) is True
    assert is_reset_code_expired(expires_at, NOW) is False


# ===========================================================================
# Yangi parol uzunligi (R3.3, R3.6)
# ===========================================================================


def test_is_new_password_acceptable_min_length() -> None:
    assert is_new_password_acceptable("a" * 8) is True
    assert is_new_password_acceptable("a" * 7) is False
    assert is_new_password_acceptable(12345678) is False


# ===========================================================================
# Urinishlar hisoblagichi va bekor qilish (R3.7)
# ===========================================================================


def test_register_failed_code_attempt_increments() -> None:
    assert register_failed_code_attempt(0) == 1
    assert register_failed_code_attempt(4) == 5


def test_is_reset_code_invalidated_only_above_max() -> None:
    # "5 martadan ko'p" -> faqat 6 va undan ortig'ida bekor qilinadi.
    assert is_reset_code_invalidated(MAX_RESET_CODE_ATTEMPTS) is False
    assert is_reset_code_invalidated(MAX_RESET_CODE_ATTEMPTS + 1) is True


# ===========================================================================
# check_reset_code — to'liq o'tish funksiyasi
# ===========================================================================


def test_check_reset_code_valid() -> None:
    expires_at = compute_reset_code_expiry(NOW)
    result = check_reset_code(
        entered_code="123456",
        expected_code="123456",
        expires_at=expires_at,
        now=NOW,
    )
    assert result.status is ResetCodeStatus.VALID
    assert result.is_valid is True
    assert result.attempts == 0
    assert result.invalidated is False


def test_check_reset_code_mismatch_increments_attempts() -> None:
    expires_at = compute_reset_code_expiry(NOW)
    result = check_reset_code(
        entered_code="654321",
        expected_code="123456",
        expires_at=expires_at,
        now=NOW,
        attempts=0,
    )
    assert result.status is ResetCodeStatus.MISMATCH
    assert result.attempts == 1
    assert result.invalidated is False


def test_check_reset_code_invalid_format_counts_as_attempt() -> None:
    expires_at = compute_reset_code_expiry(NOW)
    result = check_reset_code(
        entered_code="abc",
        expected_code="123456",
        expires_at=expires_at,
        now=NOW,
        attempts=2,
    )
    assert result.status is ResetCodeStatus.INVALID_FORMAT
    assert result.attempts == 3
    assert result.invalidated is False


def test_check_reset_code_expired_takes_priority_over_match() -> None:
    expires_at = compute_reset_code_expiry(NOW)
    result = check_reset_code(
        entered_code="123456",
        expected_code="123456",
        expires_at=expires_at,
        now=expires_at + timedelta(minutes=1),
    )
    assert result.status is ResetCodeStatus.EXPIRED
    assert result.invalidated is True
    # Muddati o'tish urinish sifatida sanalmaydi.
    assert result.attempts == 0


def test_check_reset_code_consumed_rejected() -> None:
    expires_at = compute_reset_code_expiry(NOW)
    result = check_reset_code(
        entered_code="123456",
        expected_code="123456",
        expires_at=expires_at,
        now=NOW,
        consumed=True,
    )
    assert result.status is ResetCodeStatus.CONSUMED
    assert result.invalidated is True


def test_check_reset_code_too_many_attempts_rejected() -> None:
    expires_at = compute_reset_code_expiry(NOW)
    result = check_reset_code(
        entered_code="123456",
        expected_code="123456",
        expires_at=expires_at,
        now=NOW,
        attempts=MAX_RESET_CODE_ATTEMPTS + 1,
    )
    assert result.status is ResetCodeStatus.TOO_MANY_ATTEMPTS
    assert result.invalidated is True


def test_check_reset_code_mismatch_invalidates_when_exceeding_max() -> None:
    expires_at = compute_reset_code_expiry(NOW)
    # attempts=5 -> mismatch -> 6 > 5 => bekor qilinadi.
    result = check_reset_code(
        entered_code="654321",
        expected_code="123456",
        expires_at=expires_at,
        now=NOW,
        attempts=MAX_RESET_CODE_ATTEMPTS,
    )
    assert result.status is ResetCodeStatus.MISMATCH
    assert result.attempts == MAX_RESET_CODE_ATTEMPTS + 1
    assert result.invalidated is True
