"""Ekspert baholash so'rov/javob sxemalari (R13, R20.4).

``/expert/*`` endpointlari uchun Pydantic modellar. 6 mezon bo'yicha 1–5 baho
qabul qilinadi; chuqur validatsiya (har biri 1–5 butun, olti mezon to'liq) sof
domen funksiyasi orqali **servis qatlamida** (``ExpertReviewService`` ->
``app.domain.expert.validate_expert_scores``) hal qilinadi (R13.1, R13.3, R13.4).

So'rov modeli mezonlarni ataylab ``int`` sifatida e'lon qiladi, ammo oraliq
(1–5) va to'liqlik tekshiruvini sxema darajasida cheklamaydi — bu qoidani ikki
joyda saqlamaslik uchun (yagona haqiqat manbai — domen). Shu tarzda yaroqsiz
baho ham servisning izchil ``validation_error`` (400) javobini beradi.
"""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class ExpertReviewRequest(BaseModel):
    """Ekspert baholash so'rovi — 6 mezon (R13.1).

    Mezon nomlari ``app.domain.expert.EXPERT_CRITERIA`` va ``expert_reviews``
    jadvali maydonlariga aniq mos keladi. ``expert_id`` so'rovda yo'q: u
    autentifikatsiyalangan principaldan (``principal.user_id``) olinadi (R13.5).
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "leader_id": 2,
                "management_culture": 4,
                "teamwork": 5,
                "pedagogical_process": 3,
                "innovation": 4,
                "documentation": 5,
                "strategic_planning": 4,
            }
        }
    )

    leader_id: int = Field(..., description="Baholanayotgan rahbar ID")
    management_culture: int = Field(..., description="Boshqaruv madaniyati (1–5)")
    teamwork: int = Field(..., description="Jamoaviy ishlash (1–5)")
    pedagogical_process: int = Field(
        ..., description="Pedagogik jarayonlarni tashkil etish (1–5)"
    )
    innovation: int = Field(..., description="Innovatsion yondashuv (1–5)")
    documentation: int = Field(..., description="Hujjatlar bilan ishlash (1–5)")
    strategic_planning: int = Field(..., description="Strategik rejalashtirish (1–5)")


class ExpertReviewResponse(BaseModel):
    """Ekspert baholash javobi (R13.2).

    ``ExpertReviewService.submit_review`` qaytaradigan ``ExpertReviewOutcome``
    dataclass'idan ``model_validate`` orqali quriladi.
    """

    model_config = ConfigDict(from_attributes=True)

    review_id: int = Field(..., description="Saqlangan sharh ID")
    average_score: Decimal = Field(..., description="Ekspert o'rtacha bahosi (1.00–5.00)")
    expert_score_applied: bool = Field(
        ...,
        description="Ekspert bahosi rahbarning so'nggi natijasiga qo'shildimi",
    )


class ExpertLeaderResponse(BaseModel):
    """Ekspertga biriktirilgan rahbar ro'yxati elementi (R13.5).

    ``User`` ORM obyektidan ``model_validate`` orqali quriladi.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Rahbar ID")
    full_name: str = Field(..., description="To'liq ism")
    organization_id: int | None = Field(default=None, description="Tashkilot ID")
    region_id: int | None = Field(default=None, description="Hudud ID")
    position: str | None = Field(default=None, description="Lavozim")


__all__ = [
    "ExpertReviewRequest",
    "ExpertReviewResponse",
    "ExpertLeaderResponse",
]
