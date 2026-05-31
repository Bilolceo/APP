"""Natija (test_results) javob sxemalari (R8, R8.7, R20.3).

``/tests/results/me`` va ``/tests/results/{id}`` endpointlari (vazifa 17.2)
uchun javob modellari. Bu modellar ``ResultRepository`` qaytaradigan
``TestResult`` (va bog'liq ``CompetencyResult``) ORM yozuvlaridan
``from_attributes=True`` orqali quriladi.

- :class:`ResultSummaryResponse` — foydalanuvchi natijalari ro'yxatidagi bitta
  yozuv (R8.6); ``/tests/results/me`` ro'yxati uchun.
- :class:`ResultDetailResponse` — natija tafsiloti, kompetensiya ballari bilan
  (R8.3, R8.7); ``/tests/results/{id}`` uchun.

R8.7 — natijaning tarkibiy qismlari (umumiy ball, kompetensiya ballari, qayta
topshirish sanasi) mavjud bo'lganlari to'liq qaytariladi; ixtiyoriy maydonlar
(``expert_score``, ``next_retake_date``) ``None`` bo'lishi mumkin.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class CompetencyResultResponse(BaseModel):
    """Natija tarkibidagi bitta kompetensiya ballari (R8.3, R8.8).

    ``CompetencyResult`` ORM yozuvidan quriladi.
    """

    model_config = ConfigDict(from_attributes=True)

    competency_id: int = Field(..., description="Kompetensiya identifikatori")
    score: Decimal = Field(..., description="Yig'ilgan ball")
    max_score: Decimal = Field(..., description="Maksimal ball")
    percentage: Decimal = Field(..., description="Kompetensiya foizi (0–100)")


class ResultSummaryResponse(BaseModel):
    """Foydalanuvchi natijalari ro'yxatidagi bitta yozuv (R8.6).

    ``TestResult`` ORM yozuvidan quriladi (kompetensiya tafsilotisiz — ro'yxat
    uchun yetarli minimal ma'lumot).
    """

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Natija identifikatori")
    test_id: int = Field(..., description="Test identifikatori")
    session_id: int = Field(..., description="Sessiya identifikatori")
    total_score: Decimal = Field(..., description="Umumiy yig'ilgan ball")
    max_score: Decimal = Field(..., description="Umumiy maksimal ball")
    percentage: Decimal = Field(..., description="Umumiy foiz (0–100)")
    level: str = Field(..., description="Daraja: Past/O'rta/Yaxshi/Yuqori")
    expert_score: Decimal | None = Field(
        default=None, description="Ekspert qo'shimcha ko'rsatkichi (R13.2)"
    )
    next_retake_date: date | None = Field(
        default=None, description="Keyingi qayta topshirish sanasi (R8.4)"
    )
    created_at: datetime = Field(..., description="Yaratilgan vaqt")


class ResultDetailResponse(BaseModel):
    """Natija tafsiloti — kompetensiya ballari bilan (R8.3, R8.7).

    ``TestResult`` ORM yozuvidan (kompetensiya natijalari bilan) quriladi.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Natija identifikatori")
    user_id: int = Field(..., description="Natija egasi (foydalanuvchi) ID")
    test_id: int = Field(..., description="Test identifikatori")
    session_id: int = Field(..., description="Sessiya identifikatori")
    total_score: Decimal = Field(..., description="Umumiy yig'ilgan ball")
    max_score: Decimal = Field(..., description="Umumiy maksimal ball")
    percentage: Decimal = Field(..., description="Umumiy foiz (0–100)")
    level: str = Field(..., description="Daraja: Past/O'rta/Yaxshi/Yuqori")
    expert_score: Decimal | None = Field(
        default=None, description="Ekspert qo'shimcha ko'rsatkichi (R13.2)"
    )
    next_retake_date: date | None = Field(
        default=None, description="Keyingi qayta topshirish sanasi (R8.4)"
    )
    created_at: datetime = Field(..., description="Yaratilgan vaqt")
    competency_results: list[CompetencyResultResponse] = Field(
        default_factory=list, description="Kompetensiya bo'yicha ballar"
    )


__all__ = [
    "CompetencyResultResponse",
    "ResultSummaryResponse",
    "ResultDetailResponse",
]
