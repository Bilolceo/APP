"""Test, sessiya va topshirish so'rov/javob sxemalari (R6, R7, R8, R20.3).

Ushbu modul ``/tests/*`` endpointlari (vazifa 17.2) uchun Pydantic **so'rov** va
**javob** modellarini belgilaydi:

- Testlar ro'yxati va tafsiloti (R6.1, R6.3) — :class:`TestSummaryResponse`,
  :class:`TestDetailResponse` (savollar + variantlar bilan). Bu modellar
  ``TestService`` qaytaradigan dataclass DTO'laridan ``from_attributes=True``
  orqali quriladi.
- Sessiyani boshlash/davom ettirish javobi (R7.1, R7.10) —
  :class:`SessionResponse` (``TestSession`` ORM yozuvidan).
- Topshirish so'rovi va natija javobi (R7.6, R8.6) —
  :class:`SubmitSessionRequest`, :class:`SubmitResultResponse`.

Konvensiya (auth/user sxemalari bilan izchil): so'rov modellari ``*Request``,
javob modellari ``*Response``; biznes validatsiyasi servis qatlamida, xatolar
markazlashtirilgan handler orqali (R20.6). Test tafsilotida javob
variantlarining to'g'riligi/balli ataylab oshkor qilinmaydi — bu ``TestService``
DTO darajasida ham hisobga olingan (faqat ``id`` va matn).
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Testlar ro'yxati / tafsiloti (R6.1, R6.3)
# ---------------------------------------------------------------------------


class TestSummaryResponse(BaseModel):
    """Testlar ro'yxatidagi bitta yozuv (R6.1).

    ``TestService.list_tests`` qaytaradigan :class:`TestSummary` dataclass'idan
    quriladi.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Test noyob identifikatori")
    title: str = Field(..., description="Test nomi")
    description: str | None = Field(default=None, description="Test tavsifi")
    category: str | None = Field(default=None, description="Toifa (yo'nalish)")
    duration_minutes: int | None = Field(
        default=None, description="Davomiyligi (daqiqalarda)"
    )


class AnswerOptionResponse(BaseModel):
    """Savolning bitta javob varianti (R6.3).

    Faqat foydalanuvchiga ko'rsatiladigan ma'lumot (id va matn); to'g'rilik/ball
    oshkor qilinmaydi.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Variant identifikatori")
    answer_text: str = Field(..., description="Variant matni")


class QuestionDetailResponse(BaseModel):
    """Test tafsilotidagi bitta savol va uning variantlari (R6.3)."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Savol identifikatori")
    question_text: str = Field(..., description="Savol matni")
    question_type: str | None = Field(
        default=None, description="Savol turi (cognitive/likert/situational)"
    )
    order_index: int | None = Field(default=None, description="Tartib raqami")
    competency_id: int | None = Field(
        default=None, description="Bog'langan kompetensiya ID (yo'q bo'lsa None)"
    )
    answers: list[AnswerOptionResponse] = Field(
        default_factory=list, description="Javob variantlari"
    )


class TestDetailResponse(BaseModel):
    """Test tafsiloti: meta-ma'lumot + savollar to'plami (R6.3).

    ``TestService.get_test`` qaytaradigan :class:`TestDetail` dataclass'idan
    quriladi.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Test identifikatori")
    title: str = Field(..., description="Test nomi")
    description: str | None = Field(default=None, description="Test tavsifi")
    category: str | None = Field(default=None, description="Toifa (yo'nalish)")
    duration_minutes: int | None = Field(
        default=None, description="Davomiyligi (daqiqalarda)"
    )
    question_count: int = Field(..., description="Savollar soni")
    questions: list[QuestionDetailResponse] = Field(
        default_factory=list, description="Savollar (belgilangan tartibda)"
    )


# ---------------------------------------------------------------------------
# Sessiyani boshlash / davom ettirish (R7.1, R7.10)
# ---------------------------------------------------------------------------


class SessionResponse(BaseModel):
    """Boshlangan yoki davom ettirilayotgan test sessiyasi (R7.1, R7.10).

    ``SessionService.start_session`` qaytaradigan ``TestSession`` ORM yozuvidan
    quriladi. Mavjud tugatilmagan sessiya bo'lsa, o'sha sessiya qaytariladi
    (idempotentlik — R7.10).
    """

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Sessiya identifikatori")
    user_id: int = Field(..., description="Sessiya egasi (foydalanuvchi) ID")
    test_id: int = Field(..., description="Test identifikatori")
    status: str = Field(..., description="Holat: in_progress / completed")
    started_at: datetime = Field(..., description="Boshlanish vaqti")
    expires_at: datetime | None = Field(
        default=None, description="Muddat tugash vaqti (davomiylik belgilangan bo'lsa)"
    )
    completed_at: datetime | None = Field(
        default=None, description="Yakunlanish vaqti (yakunlangan bo'lsa)"
    )


# ---------------------------------------------------------------------------
# Topshirish so'rovi (R7.6, R7.8)
# ---------------------------------------------------------------------------


class AnswerSubmission(BaseModel):
    """Bitta savolga berilgan javob (R7.6).

    ``question_id`` majburiy; variant tanlash (``answer_id``) yoki Likert qiymati
    (``likert_value``) dan kamida bittasi beriladi. To'liq normalizatsiya va
    baholash servis qatlamida (``SessionService``).
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {"question_id": 1, "answer_id": 4}
        }
    )

    question_id: int = Field(..., description="Savol identifikatori")
    answer_id: int | None = Field(
        default=None, description="Tanlangan variant identifikatori"
    )
    selected_answer_id: int | None = Field(
        default=None, description="Tanlangan variant (muqobil kalit)"
    )
    likert_value: int | None = Field(
        default=None, description="Likert shkalasi qiymati (1–5)"
    )


class SubmitSessionRequest(BaseModel):
    """Test sessiyasini topshirish so'rovi (R7.6).

    ``session_id`` — topshirilayotgan sessiya; ``answers`` — javoblar ro'yxati.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "session_id": 1024,
                "answers": [
                    {"question_id": 1, "answer_id": 4},
                    {"question_id": 2, "likert_value": 5},
                ],
            }
        }
    )

    session_id: int = Field(..., description="Topshirilayotgan sessiya ID")
    answers: list[AnswerSubmission] = Field(
        default_factory=list, description="Javoblar ro'yxati"
    )


# ---------------------------------------------------------------------------
# Topshirish natijasi (R8.1–R8.4)
# ---------------------------------------------------------------------------


class CompetencyScoreResponse(BaseModel):
    """Topshirish natijasidagi bitta kompetensiya foizi (R8.3)."""

    model_config = ConfigDict(from_attributes=True)

    competency_id: int = Field(..., description="Kompetensiya identifikatori")
    percentage: Decimal = Field(..., description="Kompetensiya foizi (0–100)")


class SubmitResultResponse(BaseModel):
    """Topshirishdan keyingi hisoblangan natija (R8.1, R8.2, R8.4).

    ``SessionService.submit_session`` qaytaradigan :class:`SubmissionOutcome`
    (natija ID + sof domen :class:`ScoreResult`) hamda saqlangan natijaning
    qayta topshirish sanasidan (R8.4) quriladi.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "result_id": 555,
                "total_score": 78.00,
                "max_score": 100.00,
                "percentage": 78.00,
                "level": "Yaxshi",
                "competencies": [{"competency_id": 3, "percentage": 85.00}],
                "strongest": [3],
                "weakest": [7],
                "next_retake_date": "2025-09-01",
            }
        }
    )

    result_id: int = Field(..., description="Saqlangan natija identifikatori")
    total_score: Decimal = Field(..., description="Umumiy yig'ilgan ball")
    max_score: Decimal = Field(..., description="Umumiy maksimal ball")
    percentage: Decimal = Field(..., description="Umumiy foiz (0–100)")
    level: str = Field(..., description="Daraja: Past/O'rta/Yaxshi/Yuqori")
    competencies: list[CompetencyScoreResponse] = Field(
        default_factory=list, description="Kompetensiya bo'yicha foizlar"
    )
    strongest: list[int] = Field(
        default_factory=list, description="Eng kuchli kompetensiya(lar) ID"
    )
    weakest: list[int] = Field(
        default_factory=list, description="Eng zaif kompetensiya(lar) ID"
    )
    next_retake_date: date | None = Field(
        default=None, description="Keyingi qayta topshirish sanasi (R8.4)"
    )


__all__ = [
    "TestSummaryResponse",
    "AnswerOptionResponse",
    "QuestionDetailResponse",
    "TestDetailResponse",
    "SessionResponse",
    "AnswerSubmission",
    "SubmitSessionRequest",
    "CompetencyScoreResponse",
    "SubmitResultResponse",
]
