"""3.1-vazifa: umumiy foiz va daraja sof funksiyalari uchun misol-asosli testlar.

Bu testlar `compute_percentage` va `determine_level` funksiyalarining aniq
misollar va muhim chegara holatlari bo'yicha to'g'ri ishlashini tekshiradi
(R8.1, R8.2, R8.8). Property-based testlar (Property 18, 19) alohida
vazifalarda (3.2, 3.3) yoziladi.

Eslatma: merge konfliktlaridan qochish uchun import bevosita
`app.domain.scoring` modulidan amalga oshiriladi (paket `__init__` orqali emas).
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.domain.scoring import compute_percentage, determine_level
from app.domain.types import Level


# --- compute_percentage (R8.1, R8.8) ---


@pytest.mark.parametrize(
    ("collected", "max_score", "expected"),
    [
        (Decimal("50"), Decimal("100"), Decimal("50.00")),
        (Decimal("0"), Decimal("100"), Decimal("0.00")),
        (Decimal("100"), Decimal("100"), Decimal("100.00")),
        (Decimal("1"), Decimal("3"), Decimal("33.33")),  # 33.333... -> 33.33
        (Decimal("2"), Decimal("3"), Decimal("66.67")),  # 66.666... -> 66.67
    ],
)
def test_compute_percentage_basic(collected: Decimal, max_score: Decimal, expected: Decimal) -> None:
    """Foiz formulasi va 2 kasr yaxlitlash to'g'ri ishlaydi (R8.1)."""
    assert compute_percentage(collected, max_score) == expected


def test_compute_percentage_half_up_rounding() -> None:
    """Yaxlitlash banker emas, oddiy half-up bo'ladi (x.xx5 -> yuqoriga)."""
    # 0.125 * 100 = 12.5 ... aslida foizni hosil qiluvchi misol:
    # collected=1, max=8 -> 12.5 (aniq), yaxlitlanmaydi.
    assert compute_percentage(Decimal("1"), Decimal("8")) == Decimal("12.50")
    # 0.005 chegarasi: 1/40000*100 = 0.0025 -> 0.00; 3/40000*100=0.0075 -> 0.01
    # Aniqroq half-up misol: 12.345 -> 12.35 (half-up), banker bo'lsa 12.34 bo'lardi.
    # collected=12.345, max=100 -> 12.345 -> 12.35
    assert compute_percentage(Decimal("12.345"), Decimal("100")) == Decimal("12.35")
    # 12.355 -> 12.36 (half-up)
    assert compute_percentage(Decimal("12.355"), Decimal("100")) == Decimal("12.36")


def test_compute_percentage_zero_max_returns_zero_no_division() -> None:
    """max == 0 bo'lsa nolga bo'lmasdan 0.00 qaytariladi (R8.8)."""
    assert compute_percentage(Decimal("0"), Decimal("0")) == Decimal("0.00")
    assert compute_percentage(Decimal("5"), Decimal("0")) == Decimal("0.00")


def test_compute_percentage_returns_decimal() -> None:
    """Natija turi izchil ravishda Decimal bo'ladi (types.py bilan mos)."""
    assert isinstance(compute_percentage(Decimal("1"), Decimal("2")), Decimal)
    assert isinstance(compute_percentage(Decimal("1"), Decimal("0")), Decimal)


# --- determine_level (R8.2) ---


@pytest.mark.parametrize(
    ("percentage", "expected"),
    [
        (Decimal("0"), Level.PAST),
        (Decimal("40"), Level.PAST),  # chegara: pastki oraliqqa tegishli
        (Decimal("40.01"), Level.ORTA),
        (Decimal("40.5"), Level.ORTA),  # R8.2 misoli: 40.5 -> O'rta
        (Decimal("60"), Level.ORTA),  # chegara
        (Decimal("60.01"), Level.YAXSHI),
        (Decimal("80"), Level.YAXSHI),  # chegara
        (Decimal("80.01"), Level.YUQORI),
        (Decimal("100"), Level.YUQORI),
    ],
)
def test_determine_level_intervals(percentage: Decimal, expected: Level) -> None:
    """Daraja oraliqlari uzluksiz va chegaralar pastki oraliqqa tegishli (R8.2)."""
    assert determine_level(percentage) is expected


# --- compute_competency_scores (R8.3, R8.5, R8.8) ---


from app.domain.scoring import build_result, compute_competency_scores
from app.domain.types import AnsweredQuestion


def _aq(question_id: int, awarded: str, maximum: str, competency_id: int | None) -> AnsweredQuestion:
    return AnsweredQuestion(
        question_id=question_id,
        awarded_score=Decimal(awarded),
        max_score=Decimal(maximum),
        competency_id=competency_id,
    )


def test_competency_scores_groups_by_competency() -> None:
    """Har bir kompetensiya foizi faqat o'z savollaridan hisoblanadi (R8.3)."""
    answered = [
        _aq(1, "5", "10", competency_id=1),
        _aq(2, "5", "10", competency_id=1),  # comp 1: 10/20 -> 50.00
        _aq(3, "9", "10", competency_id=2),  # comp 2: 9/10  -> 90.00
    ]
    results = compute_competency_scores(answered)
    by_id = {c.competency_id: c for c in results}
    assert by_id[1].percentage == Decimal("50.00")
    assert by_id[2].percentage == Decimal("90.00")
    assert by_id[1].score == Decimal("10")
    assert by_id[1].max_score == Decimal("20")


def test_competency_scores_excludes_unlinked_questions() -> None:
    """competency_id is None bo'lgan savollar kompetensiya foizidan chetda (R8.5)."""
    answered = [
        _aq(1, "5", "10", competency_id=1),
        _aq(2, "10", "10", competency_id=None),  # bog'lanmagan
    ]
    results = compute_competency_scores(answered)
    assert [c.competency_id for c in results] == [1]
    assert results[0].percentage == Decimal("50.00")


def test_competency_scores_zero_max_returns_zero() -> None:
    """Kompetensiya maksimal balli 0 bo'lsa, foiz 0.00 (R8.8)."""
    answered = [_aq(1, "0", "0", competency_id=1)]
    results = compute_competency_scores(answered)
    assert results[0].percentage == Decimal("0.00")


# --- build_result (R8.4, R8.5, R8.8, R9.5, R9.6) ---


def test_build_result_overall_includes_unlinked_questions() -> None:
    """Umumiy ball bog'lanmagan savolni ham hisobga oladi (R8.5)."""
    answered = [
        _aq(1, "5", "10", competency_id=1),
        _aq(2, "5", "10", competency_id=None),
    ]
    result = build_result(answered)
    assert result.total_score == Decimal("10")
    assert result.max_score == Decimal("20")
    assert result.percentage == Decimal("50.00")
    assert result.level is Level.ORTA
    # faqat bog'langan kompetensiya natijada
    assert [c.competency_id for c in result.competencies] == [1]


def test_build_result_strongest_weakest_single() -> None:
    """Eng yuqori/past kompetensiyalar to'g'ri aniqlanadi (R8.4)."""
    answered = [
        _aq(1, "9", "10", competency_id=1),  # 90.00 strongest
        _aq(2, "5", "10", competency_id=2),  # 50.00
        _aq(3, "1", "10", competency_id=3),  # 10.00 weakest
    ]
    result = build_result(answered)
    assert result.strongest == [1]
    assert result.weakest == [3]


def test_build_result_strongest_weakest_ties_return_all() -> None:
    """Teng qiymatda barcha teng kompetensiyalar qaytariladi (R9.5, R9.6)."""
    answered = [
        _aq(1, "9", "10", competency_id=1),  # 90.00
        _aq(2, "9", "10", competency_id=2),  # 90.00 (teng yuqori)
        _aq(3, "1", "10", competency_id=3),  # 10.00
        _aq(4, "1", "10", competency_id=4),  # 10.00 (teng past)
    ]
    result = build_result(answered)
    assert result.strongest == [1, 2]
    assert result.weakest == [3, 4]


def test_build_result_empty_answers() -> None:
    """Bo'sh kirish: 0 ball, 0.00 foiz, bo'sh kuchli/zaif ro'yxatlar (R8.8)."""
    result = build_result([])
    assert result.total_score == Decimal("0")
    assert result.max_score == Decimal("0")
    assert result.percentage == Decimal("0.00")
    assert result.level is Level.PAST
    assert result.competencies == []
    assert result.strongest == []
    assert result.weakest == []
