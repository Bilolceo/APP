"""6.1-vazifa: ekspert o'rtacha bahosi va mezon validatsiyasi (sof funksiyalar).

Bu yerda faqat misol (example-based) birlik testlari yoziladi. Property-based
testlar (Property 36, 37) alohida vazifalarda (6.2, 6.3) qo'shiladi.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.domain.expert import (
    CRITERIA_COUNT,
    EXPERT_CRITERIA,
    ExpertScoreValidationError,
    compute_expert_average,
    validate_expert_scores,
)


def _scores(*values: int) -> dict[str, int]:
    """Oltita mezonni berilgan qiymatlar bilan to'ldiruvchi yordamchi."""
    assert len(values) == CRITERIA_COUNT
    return dict(zip(EXPERT_CRITERIA, values))


# --- compute_expert_average (R13.2) ---


def test_average_all_max_is_five() -> None:
    """Barcha mezon 5 bo'lsa, o'rtacha 5.00."""
    assert compute_expert_average(_scores(5, 5, 5, 5, 5, 5)) == Decimal("5.00")


def test_average_all_min_is_one() -> None:
    """Barcha mezon 1 bo'lsa, o'rtacha 1.00."""
    assert compute_expert_average(_scores(1, 1, 1, 1, 1, 1)) == Decimal("1.00")


def test_average_is_sum_over_six() -> None:
    """O'rtacha = yig'indi / 6 (3+4+5+2+1+3 = 18 -> 3.00)."""
    assert compute_expert_average(_scores(3, 4, 5, 2, 1, 3)) == Decimal("3.00")


def test_average_rounds_half_up_to_two_places() -> None:
    """Yaxlitlash 2 kasr xonasiga half-up (1+1+1+1+1+2 = 7/6 = 1.1666... -> 1.17)."""
    assert compute_expert_average(_scores(1, 1, 1, 1, 1, 2)) == Decimal("1.17")


def test_average_two_decimal_places_repeating() -> None:
    """5+5+5+5+5+4 = 29/6 = 4.8333... -> 4.83 (half-up)."""
    assert compute_expert_average(_scores(5, 5, 5, 5, 5, 4)) == Decimal("4.83")


def test_average_in_one_to_five_range() -> None:
    """Natija 1.00–5.00 oralig'ida bo'ladi."""
    avg = compute_expert_average(_scores(2, 3, 4, 5, 1, 2))
    assert Decimal("1.00") <= avg <= Decimal("5.00")


def test_average_rejects_invalid_scores() -> None:
    """Yaroqsiz qiymat bo'lsa o'rtacha hisoblanmaydi, istisno ko'tariladi (R13.3)."""
    with pytest.raises(ExpertScoreValidationError):
        compute_expert_average(_scores(0, 5, 5, 5, 5, 5))


# --- validate_expert_scores (R13.1, R13.3, R13.4) ---


def test_validate_accepts_all_valid() -> None:
    """Oltita yaroqli mezon bo'lsa, xatolar yo'q."""
    assert validate_expert_scores(_scores(1, 2, 3, 4, 5, 3)) == []


def test_validate_rejects_below_range() -> None:
    """1 dan kichik qiymat rad etiladi (R13.3)."""
    errors = validate_expert_scores(_scores(0, 2, 3, 4, 5, 3))
    assert len(errors) == 1
    assert "management_culture" in errors[0]


def test_validate_rejects_above_range() -> None:
    """5 dan katta qiymat rad etiladi (R13.3)."""
    errors = validate_expert_scores(_scores(1, 2, 3, 4, 5, 6))
    assert len(errors) == 1
    assert "strategic_planning" in errors[0]


def test_validate_rejects_non_integer() -> None:
    """Butun son bo'lmagan (float) qiymat rad etiladi (R13.3)."""
    scores = _scores(1, 2, 3, 4, 5, 3)
    scores["teamwork"] = 3.5  # type: ignore[assignment]
    errors = validate_expert_scores(scores)
    assert any("teamwork" in e for e in errors)


def test_validate_rejects_bool_as_non_integer() -> None:
    """bool (int quyi sinfi) butun son sifatida qabul qilinmaydi (R13.3)."""
    scores = _scores(1, 2, 3, 4, 5, 3)
    scores["innovation"] = True  # type: ignore[assignment]
    errors = validate_expert_scores(scores)
    assert any("innovation" in e for e in errors)


def test_validate_rejects_missing_criterion() -> None:
    """To'ldirilmagan mezon rad etiladi (R13.4)."""
    scores = _scores(1, 2, 3, 4, 5, 3)
    del scores["documentation"]
    errors = validate_expert_scores(scores)
    assert any("documentation" in e and "to'ldirilmagan" in e for e in errors)


def test_validate_reports_all_missing() -> None:
    """Bo'sh kirish — oltita mezon ham to'ldirilmagan deb belgilanadi (R13.4)."""
    errors = validate_expert_scores({})
    assert len(errors) == CRITERIA_COUNT


def test_validate_raises_type_error_for_non_mapping() -> None:
    """Moslama bo'lmagan kirish shartnoma buzilishi sifatida TypeError beradi."""
    with pytest.raises(TypeError):
        validate_expert_scores([1, 2, 3, 4, 5, 6])  # type: ignore[arg-type]


def test_validation_error_carries_errors_list() -> None:
    """ExpertScoreValidationError xatolar ro'yxatini saqlaydi."""
    err = ExpertScoreValidationError(["x mezoni yaroqsiz"])
    assert err.errors == ["x mezoni yaroqsiz"]
