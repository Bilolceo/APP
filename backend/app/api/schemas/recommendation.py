"""Tavsiya so'rov/javob sxemalari — ``/recommendations/*`` (R10, R20.1).

``/recommendations/me`` (GET) va ``/recommendations/by-result/{result_id}``
(GET) endpointlari uchun javob modeli. Router ``RecommendationService`` ustidagi
yupqa HTTP qatlami: servis ``RecommendationView`` (frozen dataclass) ro'yxatini
qaytaradi, bu yerdagi :class:`RecommendationResponse` esa uni tasdiqlangan javob
sxemasiga keltiradi (``from_attributes=True``).

Egalik (R10.6) va bo'sh holat (R10.5) servis qatlamida hal qilinadi: begona/yo'q
natija ``NotFoundError`` (404), natija yo'q bo'lsa bo'sh ro'yxat (xato emas).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class RecommendationResponse(BaseModel):
    """Natijaga bog'langan bitta tavsiyaning javob ko'rinishi (R10.2).

    ``RecommendationView`` dataclass'idan ``model_validate`` orqali quriladi.
    Maydonlar (R10.2 — kompetensiya nomi, darajasi va rivojlanish ko'rsatmasi).
    """

    model_config = ConfigDict(from_attributes=True)

    competency_id: int | None = Field(default=None, description="Kompetensiya ID")
    competency_name: str | None = Field(default=None, description="Kompetensiya nomi")
    level: str | None = Field(default=None, description="Baholangan daraja")
    text: str | None = Field(default=None, description="Tavsiya matni (snapshot)")


__all__ = ["RecommendationResponse"]
