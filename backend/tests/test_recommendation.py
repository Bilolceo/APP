"""6.4-vazifa: tavsiya tanlash sof mantig'i (`select_recommendations`) testlari.

Bu testlar misol asosida (example-based) tanlash mantig'ini tekshiradi:
- aniq (kompetensiya, daraja) mosligi (R10.1),
- aniq moslik bo'lmaganda umumiy standart tavsiyaga tushish (R10.4),
- totallik: har bir baholangan kompetensiya uchun har doim tavsiya qaytadi.

Property-based test (totallik) alohida 6.5-vazifada qo'shiladi.
"""

from __future__ import annotations

import pytest

from app.domain.recommendation import (
    EvaluatedCompetency,
    Recommendation,
    SelectedRecommendation,
    select_recommendations,
)
from app.domain.types import Level


# --- Aniq moslik (R10.1) ---


def test_exact_match_is_selected() -> None:
    """Aniq (kompetensiya, daraja) mos tavsiya tanlanadi (R10.1)."""
    recs = [
        Recommendation(competency_id=1, level=Level.PAST, text="K1-Past", id=10),
        Recommendation(competency_id=1, level=Level.YUQORI, text="K1-Yuqori", id=11),
        Recommendation(competency_id=None, level=Level.PAST, text="Standart-Past", id=99),
    ]
    evaluated = [EvaluatedCompetency(competency_id=1, level=Level.YUQORI)]

    result = select_recommendations(evaluated, recs)

    assert result == [
        SelectedRecommendation(
            competency_id=1,
            level=Level.YUQORI,
            recommendation_id=11,
            text="K1-Yuqori",
            is_standard=False,
        )
    ]


def test_exact_match_preferred_over_general_for_same_level() -> None:
    """Aniq moslik bir xil darajadagi umumiy standartdan ustun turadi."""
    recs = [
        Recommendation(competency_id=None, level=Level.ORTA, text="Standart-O'rta", id=99),
        Recommendation(competency_id=2, level=Level.ORTA, text="K2-O'rta", id=20),
    ]
    evaluated = [EvaluatedCompetency(competency_id=2, level=Level.ORTA)]

    [selected] = select_recommendations(evaluated, recs)

    assert selected.recommendation_id == 20
    assert selected.is_standard is False


# --- Umumiy standart zaxira (R10.4) ---


def test_falls_back_to_general_for_level_when_no_exact_match() -> None:
    """Aniq moslik yo'q -> o'sha darajadagi umumiy standart tavsiya (R10.4)."""
    recs = [
        Recommendation(competency_id=1, level=Level.PAST, text="K1-Past", id=10),
        Recommendation(competency_id=None, level=Level.YAXSHI, text="Standart-Yaxshi", id=98),
    ]
    # 5-kompetensiya uchun aniq moslik yo'q.
    evaluated = [EvaluatedCompetency(competency_id=5, level=Level.YAXSHI)]

    [selected] = select_recommendations(evaluated, recs)

    assert selected.recommendation_id == 98
    assert selected.is_standard is True
    assert selected.text == "Standart-Yaxshi"


def test_falls_back_to_any_general_when_level_specific_missing() -> None:
    """Darajaga mos umumiy standart yo'q bo'lsa, istalgan umumiy standart olinadi."""
    recs = [
        Recommendation(competency_id=None, level=Level.PAST, text="Standart-Past", id=90),
    ]
    # Yuqori daraja uchun aniq ham, darajaga mos standart ham yo'q.
    evaluated = [EvaluatedCompetency(competency_id=7, level=Level.YUQORI)]

    [selected] = select_recommendations(evaluated, recs)

    assert selected.recommendation_id == 90
    assert selected.is_standard is True


# --- Totallik (R10.1, R10.4) ---


def test_every_competency_gets_a_recommendation() -> None:
    """Har bir baholangan kompetensiya uchun aynan bitta tavsiya qaytariladi."""
    recs = [
        Recommendation(competency_id=1, level=Level.PAST, text="K1-Past", id=10),
        Recommendation(competency_id=None, level=Level.ORTA, text="Standart-O'rta", id=99),
        Recommendation(competency_id=None, level=Level.YUQORI, text="Standart-Yuqori", id=100),
    ]
    evaluated = [
        EvaluatedCompetency(competency_id=1, level=Level.PAST),   # aniq
        EvaluatedCompetency(competency_id=2, level=Level.ORTA),   # standart (daraja)
        EvaluatedCompetency(competency_id=3, level=Level.YUQORI), # standart (daraja)
    ]

    result = select_recommendations(evaluated, recs)

    assert len(result) == len(evaluated)
    # Chiqish tartibi kirish tartibini saqlaydi.
    assert [s.competency_id for s in result] == [1, 2, 3]
    assert [s.is_standard for s in result] == [False, True, True]


def test_empty_evaluated_returns_empty_list() -> None:
    """Baholangan kompetensiya bo'lmasa, bo'sh ro'yxat qaytadi (xato emas)."""
    recs = [Recommendation(competency_id=None, level=Level.PAST, text="S", id=1)]
    assert select_recommendations([], recs) == []


def test_order_independent_for_unordered_recommendation_input() -> None:
    """Tavsiyalar to'plami (set) tartibsiz bo'lsa ham natija deterministik."""
    recs = {
        Recommendation(competency_id=None, level=Level.PAST, text="Standart-Past", id=99),
        Recommendation(competency_id=1, level=Level.PAST, text="K1-Past", id=10),
    }
    evaluated = [EvaluatedCompetency(competency_id=1, level=Level.PAST)]

    [selected] = select_recommendations(evaluated, recs)

    assert selected.recommendation_id == 10
    assert selected.is_standard is False


# --- Totallik buzilishi (xato holati) ---


def test_raises_when_no_general_fallback_and_no_exact_match() -> None:
    """Umumiy standart tavsiya yo'q va aniq moslik topilmasa, ValueError."""
    recs = [
        Recommendation(competency_id=1, level=Level.PAST, text="K1-Past", id=10),
    ]
    evaluated = [EvaluatedCompetency(competency_id=2, level=Level.YUQORI)]

    with pytest.raises(ValueError):
        select_recommendations(evaluated, recs)
