"""Reyting javob sxemalari (R12, R20.4).

``GET /rating`` endpointi uchun Pydantic **javob** modellari. Reyting domen
yadrosi (``app.domain.rating.build_anonymized_rating``) anonim natija
(``AnonymizedRating``) qaytaradi; bu modullar uni ``model_validate`` orqali
javob sxemasiga keltiradi (``from_attributes=True``).

Anonimlik (R12.4): yozuvlar faqat ``region``, ``org_type``, ``position``,
``percentage`` (saralash ko'rsatkichi) va ``rank`` ni oshkor qiladi; to'liq ism,
telefon raqami yoki boshqa identifikatsiyalovchi maydonlar BU YERDA MAVJUD EMAS.
So'rovchining o'z yozuvi ``is_requester`` bayrog'i bilan ajratiladi (R12.4).
Natijasi bo'lmagan foydalanuvchilar ``out_of_ranking`` da (rank berilmasdan,
R12.5).

Domen ``region``/``org_type``/``position`` maydonlari ``Hashable`` tipida
(odatda ID yoki matn). Router ushbu qiymatlarni inson o'qiy oladigan nomlarga
keltirib uzatadi (hudud/tashkilot nomi); shuning uchun bu yerda ular ``str``
sifatida e'lon qilinadi (qiymatlar matn ko'rinishida beriladi).
"""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class RatingEntryResponse(BaseModel):
    """Reytingdagi bitta anonim yozuv (R12.1, R12.4).

    Faqat anonim maydonlar oshkor qilinadi; ``is_requester`` so'rovchining o'z
    yozuvini ajratadi (R12.4).
    """

    model_config = ConfigDict(from_attributes=True)

    rank: int = Field(..., description="Reyting o'rni (1 dan boshlanadi)")
    percentage: Decimal = Field(..., description="Saralash ko'rsatkichi — umumiy foiz")
    region: str | None = Field(default=None, description="Hudud")
    org_type: str | None = Field(default=None, description="Tashkilot turi")
    position: str | None = Field(default=None, description="Lavozim")
    is_requester: bool = Field(
        default=False, description="So'rovchining o'z yozuvimi"
    )


class OutOfRankingEntryResponse(BaseModel):
    """Reytingdan tashqaridagi yozuv — yakunlangan natijasi yo'q (R12.5)."""

    model_config = ConfigDict(from_attributes=True)

    region: str | None = Field(default=None, description="Hudud")
    org_type: str | None = Field(default=None, description="Tashkilot turi")
    position: str | None = Field(default=None, description="Lavozim")
    is_requester: bool = Field(
        default=False, description="So'rovchining o'z (reytingsiz) yozuvimi"
    )


class RatingResponse(BaseModel):
    """To'liq anonim reyting taqdimoti (R12.1–R12.5).

    ``scope`` — so'ralgan kesim (overall/region/organization/competency);
    ``ranked`` — tartiblangan anonim yozuvlar; ``out_of_ranking`` — natijasi
    bo'lmagan (reytingsiz) yozuvlar.
    """

    scope: str = Field(..., description="Reyting kesimi")
    ranked: list[RatingEntryResponse] = Field(
        default_factory=list, description="Tartiblangan anonim yozuvlar"
    )
    out_of_ranking: list[OutOfRankingEntryResponse] = Field(
        default_factory=list, description="Reytingdan tashqaridagi yozuvlar"
    )


__all__ = [
    "RatingEntryResponse",
    "OutOfRankingEntryResponse",
    "RatingResponse",
]
