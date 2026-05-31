"""Profil (foydalanuvchi) so'rov/javob sxemalari (R5, R20.1, R20.6).

``/users/me`` (GET/PATCH) va ``/users/{id}`` endpointlari uchun modellar.

- :class:`ProfileResponse` — ``ProfileService.get_profile`` qaytaradigan
  :class:`~app.services.profile_service.Profile` dataclass'idan quriladi
  (``from_attributes=True``). To'liq profil maydonlari qaytariladi (R5.1).
- :class:`ProfileUpdateRequest` — tahrirlanadigan maydonlar (R5.2). ``phone``
  ham qabul qilinadi, ammo u o'zgarmas hisob identifikatori bo'lgani uchun, agar
  yuborilsa, servis qatlami uni aniq xato bilan rad etadi (R5.4) — shu tarzda
  "telefonni o'zgartirib bo'lmaydi" xatosi to'g'ri qaytariladi. Faqat
  foydalanuvchi yuborgan maydonlar patch sifatida uzatiladi (``exclude_unset``),
  shunda servis validatsiyasi (ish staji 0–60, matn ≤200) faqat berilgan
  maydonlarga qo'llanadi (R5.3).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ProfileUpdateRequest(BaseModel):
    """Profilni yangilash so'rovi — tahrirlanadigan maydonlar (R5.2, R5.4).

    Barcha maydonlar ixtiyoriy: foydalanuvchi faqat o'zgartirmoqchi bo'lganlarini
    yuboradi (qisman yangilash). ``phone`` ham qabul qilinadi, ammo u o'zgarmas
    hisob identifikatori — agar yuborilsa, servis qatlami uni aniq xato bilan
    rad etadi (R5.4). Qiymat cheklovlari (ish staji 0–60, matn ≤200) servis
    qatlamida tekshiriladi (R5.3).
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "full_name": "Ali Valiyev",
                "position": "Bosh direktor",
                "experience_years": 7,
                "education_level": "Oliy",
            }
        }
    )

    full_name: str | None = Field(default=None, description="To'liq ism (1–200 belgi)")
    organization_id: int | None = Field(default=None, description="Ish joyi (tashkilot) ID")
    region_id: int | None = Field(default=None, description="Hudud ID")
    position: str | None = Field(default=None, description="Lavozim (≤200 belgi)")
    experience_years: int | None = Field(default=None, description="Ish staji (0–60)")
    education_level: str | None = Field(default=None, description="Ta'lim darajasi (≤200)")
    qualification_courses: str | None = Field(
        default=None, description="Malaka oshirish kurslari (≤200)"
    )
    certificates: str | None = Field(default=None, description="Sertifikatlar (≤200)")
    org_type: str | None = Field(default=None, description="Tashkilot turi (≤200)")
    notifications_enabled: bool | None = Field(
        default=None,
        description="Push bildirishnomalarni yoqish/o'chirish (true/false)",
    )
    phone: str | None = Field(
        default=None,
        description="O'zgarmas hisob identifikatori — yuborilsa rad etiladi (R5.4)",
    )


class ProfileResponse(BaseModel):
    """To'liq profil javobi (R5.1).

    ``ProfileService`` qaytaradigan :class:`Profile` dataclass'idan
    ``model_validate`` orqali quriladi.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Foydalanuvchi ID")
    full_name: str = Field(..., description="To'liq ism")
    phone: str = Field(..., description="Telefon raqami (o'zgarmas)")
    organization_id: int | None = Field(default=None, description="Ish joyi (tashkilot) ID")
    region_id: int | None = Field(default=None, description="Hudud ID")
    position: str | None = Field(default=None, description="Lavozim")
    experience_years: int | None = Field(default=None, description="Ish staji")
    education_level: str | None = Field(default=None, description="Ta'lim darajasi")
    qualification_courses: str | None = Field(
        default=None, description="Malaka oshirish kurslari"
    )
    certificates: str | None = Field(default=None, description="Sertifikatlar")
    org_type: str | None = Field(default=None, description="Tashkilot turi")
    notifications_enabled: bool = Field(
        ..., description="Push bildirishnomalari yoqilganligi"
    )


__all__ = ["ProfileUpdateRequest", "ProfileResponse"]
