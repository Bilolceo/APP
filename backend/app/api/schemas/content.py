"""Kontent (savol) so'rov/javob sxemalari — ``/questions/*`` (R14, R20.1, R20.6).

Ushbu modul administrator kontent boshqaruvi (savollar CRUD) endpointlari uchun
Pydantic **so'rov** va **javob** modellarini belgilaydi. Routerlar
``AdminService`` ustidagi yupqa HTTP qatlami bo'lib, biznes validatsiyasi (matn
1–1000, ball 0.01–1000, kamida 2 variant, mavjud kompetensiya — R14.3, R14.7)
servis qatlamida hal qilinadi; bu yerdagi modellar ataylab **yumshoq** (maydon
mavjudligi va tiplar) bo'lib, servis qoidalarini takrorlamaydi.

Konvensiyalar (17.1 bilan izchil):
- So'rov modellari ``*Request``, javob modellari ``*Response`` deb nomlanadi.
- Javoblar ORM obyektlaridan ``ConfigDict(from_attributes=True)`` orqali quriladi.
- Qisman yangilash (PATCH) uchun faqat yuborilgan maydonlar uzatiladi
  (``exclude_unset``), shunda servis validatsiyasi faqat shu maydonlarga
  qo'llanadi.
"""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# So'rov modellari (Request)
# ---------------------------------------------------------------------------


class AnswerOptionRequest(BaseModel):
    """Savol javob varianti (R14.3 — kamida 2 ta variant talab qilinadi).

    ``answer_text`` majburiy; ``is_correct`` va ``score`` ixtiyoriy. To'liq
    validatsiya (bo'sh matn, tiplar) ``AdminService`` da.
    """

    answer_text: str = Field(..., description="Javob varianti matni")
    is_correct: bool = Field(default=False, description="To'g'ri variantmi")
    score: Decimal | None = Field(default=None, description="Variant balli (ixtiyoriy)")


class QuestionCreateRequest(BaseModel):
    """Savol yaratish so'rovi (R14.3, R14.7).

    Majburiy maydonlar: ``test_id``, ``question_text``, ``score``,
    ``competency_id`` hamda kamida 2 ta ``answers``. Validatsiya servis
    qatlamida; mavjud bo'lmagan kompetensiya 404, yaroqsiz qiymat 400 beradi.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "test_id": 1,
                "question_text": "Jamoani qanday boshqarasiz?",
                "score": 5,
                "competency_id": 2,
                "question_type": "likert",
                "order_index": 0,
                "answers": [
                    {"answer_text": "Variant A", "is_correct": False},
                    {"answer_text": "Variant B", "is_correct": True},
                ],
            }
        }
    )

    test_id: int = Field(..., description="Savol tegishli test ID")
    question_text: str = Field(..., description="Savol matni (1–1000 belgi)")
    score: Decimal = Field(..., description="Savol balli (0.01–1000)")
    competency_id: int = Field(..., description="Bog'lanadigan kompetensiya ID")
    answers: list[AnswerOptionRequest] = Field(
        ..., description="Javob variantlari (kamida 2 ta)"
    )
    question_type: str | None = Field(
        default=None, description="Savol turi (cognitive/likert/situational)"
    )
    order_index: int | None = Field(default=None, description="Belgilangan tartib indeksi")


class QuestionUpdateRequest(BaseModel):
    """Savolni qisman yangilash so'rovi (R14.3, R14.6).

    Barcha maydonlar ixtiyoriy: faqat yuborilganlari yangilanadi
    (``exclude_unset``). ``answers`` yuborilsa, mavjud variantlar yangilari bilan
    to'liq almashtiriladi (kamida 2 ta).
    """

    question_text: str | None = Field(default=None, description="Savol matni (1–1000)")
    score: Decimal | None = Field(default=None, description="Savol balli (0.01–1000)")
    competency_id: int | None = Field(default=None, description="Kompetensiya ID")
    answers: list[AnswerOptionRequest] | None = Field(
        default=None, description="Javob variantlari (kamida 2 ta)"
    )
    question_type: str | None = Field(default=None, description="Savol turi")
    order_index: int | None = Field(default=None, description="Tartib indeksi")


# ---------------------------------------------------------------------------
# Javob modellari (Response)
# ---------------------------------------------------------------------------


class AnswerResponse(BaseModel):
    """Savol javob varianti javobi (R14.3)."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Variant ID")
    answer_text: str = Field(..., description="Variant matni")
    is_correct: bool = Field(..., description="To'g'ri variantmi")
    score: Decimal | None = Field(default=None, description="Variant balli")


class QuestionResponse(BaseModel):
    """Savol javobi — variantlari bilan (R14.3).

    ``Question`` ORM yozuvidan ``model_validate`` orqali quriladi; ``answers``
    bog'lanish (relationship) orqali olinadi.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Savol ID")
    test_id: int = Field(..., description="Test ID")
    competency_id: int | None = Field(default=None, description="Kompetensiya ID")
    question_text: str = Field(..., description="Savol matni")
    question_type: str | None = Field(default=None, description="Savol turi")
    score: Decimal = Field(..., description="Savol balli")
    order_index: int | None = Field(default=None, description="Tartib indeksi")
    answers: list[AnswerResponse] = Field(
        default_factory=list, description="Javob variantlari"
    )


__all__ = [
    "AnswerOptionRequest",
    "QuestionCreateRequest",
    "QuestionUpdateRequest",
    "AnswerResponse",
    "QuestionResponse",
]
