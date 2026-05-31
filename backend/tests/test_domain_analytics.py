"""5.1-vazifa: o'sish dinamikasi va farq sof funksiyalari uchun unit testlar.

Bu yerda faqat aniq misollar va chegaraviy holatlar tekshiriladi. Universal
xususiyatlar (Property 23, 24) alohida property-based testlar (5.2, 5.3
vazifalar) sifatida qo'shiladi.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app.domain.analytics import (
    AggregateResult,
    CompetencyAggregate,
    DatedResult,
    GrowthPoint,
    SectionRecord,
    aggregate_average,
    aggregate_by_section,
    aggregate_competencies,
    growth_diff,
    growth_dynamics,
)

_BASE = datetime(2024, 1, 1, tzinfo=timezone.utc)


def _r(percentage: str, days: int) -> DatedResult:
    return DatedResult(percentage=Decimal(percentage), achieved_at=_BASE + timedelta(days=days))


# --- growth_dynamics (R9.1, R15.5) ---


def test_growth_dynamics_empty_returns_empty() -> None:
    """Bo'sh kirish bo'sh ketma-ketlikni qaytaradi (R9.7)."""
    assert growth_dynamics([]) == []


def test_growth_dynamics_orders_oldest_to_newest() -> None:
    """Natijalar sana bo'yicha eng eskidan eng yangiga tartiblanadi (R9.1)."""
    results = [_r("80.00", 10), _r("50.00", 0), _r("65.00", 5)]
    dynamics = growth_dynamics(results)

    assert [p.percentage for p in dynamics] == [
        Decimal("50.00"),
        Decimal("65.00"),
        Decimal("80.00"),
    ]
    # Sanalar ham o'suvchi tartibda va har bir nuqta sana bilan belgilangan.
    assert all(isinstance(p, GrowthPoint) for p in dynamics)
    assert [p.achieved_at for p in dynamics] == sorted(p.achieved_at for p in dynamics)


def test_growth_dynamics_single_result() -> None:
    """Bitta natijada dinamika shu yagona nuqtadan iborat (R9.4)."""
    dynamics = growth_dynamics([_r("42.50", 3)])
    assert len(dynamics) == 1
    assert dynamics[0].percentage == Decimal("42.50")


# --- growth_diff (R9.3, R9.4) ---


def test_growth_diff_single_result_is_not_available() -> None:
    """Bitta natijada farq "mavjud emas" — None qaytadi (R9.4)."""
    assert growth_diff([_r("70.00", 0)]) is None


def test_growth_diff_empty_is_not_available() -> None:
    """Natija bo'lmasa farq "mavjud emas" — None qaytadi (R9.4)."""
    assert growth_diff([]) is None


def test_growth_diff_positive_when_improved() -> None:
    """O'sishda farq musbat bo'ladi (current − previous) (R9.3)."""
    assert growth_diff([_r("60.00", 0), _r("75.50", 1)]) == Decimal("15.50")


def test_growth_diff_negative_when_declined() -> None:
    """Pasayishda farq manfiy bo'ladi (R9.3)."""
    assert growth_diff([_r("75.50", 0), _r("60.00", 1)]) == Decimal("-15.50")


def test_growth_diff_zero_when_unchanged() -> None:
    """O'zgarishsiz holatda farq nol bo'ladi (R9.3)."""
    assert growth_diff([_r("80.00", 0), _r("80.00", 1)]) == Decimal("0")


def test_growth_diff_uses_two_latest_by_date_not_input_order() -> None:
    """Farq sana bo'yicha eng so'nggi ikki natijadan hisoblanadi (R9.3)."""
    # Kirish tartibi aralash; eng so'nggi (kun=2) va undan oldingi (kun=1).
    results = [_r("90.00", 2), _r("50.00", 0), _r("70.00", 1)]
    assert growth_diff(results) == Decimal("20.00")  # 90.00 − 70.00


# ======================================================================
# 5.4-vazifa: jamlangan agregatsiya funksiyalari uchun unit testlar.
#
# Aniq misollar va chegaraviy holatlar. Universal xususiyatlar (Property 25,
# 26, 27) alohida property-based testlar (5.5, 5.6, 5.7 vazifalar) sifatida
# qo'shiladi.
# ======================================================================


def _ar(user_id: int, percentage: str, competencies: dict[int, str] | None = None) -> AggregateResult:
    return AggregateResult(
        user_id=user_id,
        percentage=Decimal(percentage),
        competencies={cid: Decimal(p) for cid, p in (competencies or {}).items()},
    )


# --- aggregate_average (R15.1) ---


def test_aggregate_average_empty_returns_zero() -> None:
    """Natija yo'q bo'lsa o'rtacha 0.00 (muvaffaqiyatli bo'sh holat, R15.7)."""
    assert aggregate_average([]) == Decimal("0.00")


def test_aggregate_average_arithmetic_mean_rounded_half_up() -> None:
    """O'rtacha arifmetik o'rtachaga teng, 2 kasr xonasi, half-up (R15.1)."""
    # (50 + 75 + 100) / 3 = 75.00
    results = [_ar(1, "50.00"), _ar(2, "75.00"), _ar(3, "100.00")]
    assert aggregate_average(results) == Decimal("75.00")
    # (33.33 + 33.34) / 2 = 33.335 -> 33.34 (half-up)
    assert aggregate_average([_ar(1, "33.33"), _ar(2, "33.34")]) == Decimal("33.34")


def test_aggregate_average_within_bounds() -> None:
    """O'rtacha 0–100 oralig'ida bo'ladi (R15.1)."""
    avg = aggregate_average([_ar(1, "0.00"), _ar(2, "100.00")])
    assert Decimal("0") <= avg <= Decimal("100")
    assert avg == Decimal("50.00")


# --- aggregate_competencies (R15.2) ---


def test_aggregate_competencies_empty_returns_empty() -> None:
    """Natija yo'q bo'lsa bo'sh jamlanma va bo'sh ro'yxatlar (R15.7)."""
    extremes = aggregate_competencies([])
    assert extremes.aggregates == ()
    assert extremes.lowest == ()
    assert extremes.highest == ()


def test_aggregate_competencies_means_and_extremes() -> None:
    """Har bir kompetensiya o'rtachasi va eng past/yuqori to'g'ri (R15.2)."""
    results = [
        _ar(1, "70.00", {10: "40.00", 20: "80.00", 30: "60.00"}),
        _ar(2, "70.00", {10: "60.00", 20: "90.00", 30: "60.00"}),
    ]
    extremes = aggregate_competencies(results)
    # Jamlanma kompetensiya id bo'yicha o'suvchi tartibda.
    assert extremes.aggregates == (
        CompetencyAggregate(10, Decimal("50.00")),  # (40+60)/2
        CompetencyAggregate(20, Decimal("85.00")),  # (80+90)/2
        CompetencyAggregate(30, Decimal("60.00")),  # (60+60)/2
    )
    assert extremes.lowest == (10,)
    assert extremes.highest == (20,)


def test_aggregate_competencies_ties_return_all() -> None:
    """Teng jamlangan foizda barcha kompetensiyalar qaytariladi (R15.2)."""
    results = [
        _ar(1, "50.00", {10: "30.00", 20: "30.00", 30: "90.00", 40: "90.00"}),
    ]
    extremes = aggregate_competencies(results)
    assert extremes.lowest == (10, 20)
    assert extremes.highest == (30, 40)


def test_aggregate_competencies_single_competency_is_both_extremes() -> None:
    """Yagona kompetensiya ham eng past, ham eng yuqori (R15.2)."""
    extremes = aggregate_competencies([_ar(1, "50.00", {10: "50.00"})])
    assert extremes.lowest == (10,)
    assert extremes.highest == (10,)


# --- aggregate_by_section (R15.3, R15.4) ---


def test_aggregate_by_section_empty_returns_empty_dict() -> None:
    """Yozuv yo'q bo'lsa bo'sh lug'at (R15.7)."""
    assert aggregate_by_section([], "region") == {}


def test_aggregate_by_section_counts_and_average_by_field_name() -> None:
    """Kesim bo'yicha rahbarlar/topshirganlar soni va o'rtacha (R15.3)."""
    records = [
        SectionRecord(user_id=1, percentage=Decimal("60.00"), region="Toshkent"),
        SectionRecord(user_id=2, percentage=Decimal("80.00"), region="Toshkent"),
        SectionRecord(user_id=3, percentage=None, region="Toshkent"),  # topshirmagan
        SectionRecord(user_id=4, percentage=Decimal("50.00"), region="Samarqand"),
    ]
    summary = aggregate_by_section(records, "region")

    assert summary["Toshkent"].leaders_count == 3
    assert summary["Toshkent"].test_takers_count == 2
    assert summary["Toshkent"].average_score == Decimal("70.00")  # (60+80)/2

    assert summary["Samarqand"].leaders_count == 1
    assert summary["Samarqand"].test_takers_count == 1
    assert summary["Samarqand"].average_score == Decimal("50.00")


def test_aggregate_by_section_no_test_takers_average_zero() -> None:
    """Topshirgan rahbar bo'lmagan kesimda o'rtacha 0.00 (R15.7)."""
    records = [SectionRecord(user_id=1, percentage=None, organization="A")]
    summary = aggregate_by_section(records, "organization")
    assert summary["A"].leaders_count == 1
    assert summary["A"].test_takers_count == 0
    assert summary["A"].average_score == Decimal("0.00")


def test_aggregate_by_section_accepts_callable_key() -> None:
    """Kesim kaliti chaqiriladigan funksiya sifatida ham berilishi mumkin."""
    records = [
        SectionRecord(user_id=1, percentage=Decimal("40.00"), organization="Org-1"),
        SectionRecord(user_id=2, percentage=Decimal("60.00"), organization="Org-1"),
    ]
    summary = aggregate_by_section(records, lambda r: r.organization)
    assert summary["Org-1"].leaders_count == 2
    assert summary["Org-1"].average_score == Decimal("50.00")
