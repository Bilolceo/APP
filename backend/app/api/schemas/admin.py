"""Admin (kontent boshqaruvi) so'rov/javob sxemalari (R14, R20.4).

``/admin/*`` endpointlari uchun Pydantic **so'rov** va **javob** modellari.
Konvensiyalar 17.1 (auth/profil) sxemalari bilan bir xil:

- So'rov modellari ``*Request``, javob modellari ``*Response``.
- ORM obyektidan javob qurish uchun ``ConfigDict(from_attributes=True)``.
- Chuqur biznes validatsiyasi **servis qatlamida** (``AdminService``): nom
  1–200, toifa whitelisti, davomiyligi 1–600 va h.k. (R14.2). Shu sababli bu
  yerdagi so'rov modellari ataylab yumshoq (maydon mavjudligi/tiplar) bo'lib,
  servis qoidalarini takrorlamaydi (yagona haqiqat manbai — servis).

Eslatma (RBAC): admin-only ruxsat (R14.5) router qatlamida ``require_admin``
bog'liqligi orqali ta'minlanadi; sxemalar ruxsatni tekshirmaydi.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Javob modellari (Response) — foydalanuvchi / natija ro'yxatlari (R14.1, R20.4)
# ---------------------------------------------------------------------------


class AdminUserResponse(BaseModel):
    """Admin foydalanuvchi ro'yxati elementi (R14.1, R20.4).

    Administrator barcha foydalanuvchilar profiliga kira oladi (R4.3); bu model
    ro'yxat ko'rinishi uchun asosiy maydonlarni beradi. ``role`` — rol nomi
    (``roles.name``), router ``User.role`` munosabatidan to'ldiradi.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Foydalanuvchi ID")
    full_name: str = Field(..., description="To'liq ism")
    phone: str = Field(..., description="Telefon raqami")
    role: str | None = Field(default=None, description="Rol nomi")
    organization_id: int | None = Field(default=None, description="Tashkilot ID")
    region_id: int | None = Field(default=None, description="Hudud ID")
    position: str | None = Field(default=None, description="Lavozim")


class AdminResultResponse(BaseModel):
    """Admin natija ro'yxati elementi (R14.1, R20.4).

    ``TestResult`` ORM obyektidan ``model_validate`` orqali quriladi.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Natija ID")
    user_id: int = Field(..., description="Foydalanuvchi ID")
    test_id: int = Field(..., description="Test ID")
    total_score: Decimal = Field(..., description="Yig'ilgan ball")
    max_score: Decimal = Field(..., description="Maksimal ball")
    percentage: Decimal = Field(..., description="Umumiy foiz (0–100)")
    level: str = Field(..., description="Daraja (Past/O'rta/Yaxshi/Yuqori)")
    expert_score: Decimal | None = Field(
        default=None, description="Ekspert qo'shimcha ko'rsatkichi"
    )
    next_retake_date: date | None = Field(
        default=None, description="Keyingi qayta topshirish sanasi"
    )
    created_at: datetime | None = Field(default=None, description="Yaratilgan sana")


# ---------------------------------------------------------------------------
# Test CRUD so'rov/javob modellari (R14.2, R14.4)
# ---------------------------------------------------------------------------


class TestCreateRequest(BaseModel):
    """Yangi test yaratish so'rovi (R14.2).

    To'liq validatsiya (nom 1–200, toifa whitelisti, davomiyligi 1–600)
    ``AdminService.create_test`` da (R14.2, R14.6).
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "Kognitiv diagnostika",
                "category": "kognitiv",
                "duration_minutes": 30,
                "description": "Bilim darajasini baholash",
                "is_active": True,
            }
        }
    )

    title: str = Field(..., description="Test nomi (1–200 belgi)")
    category: str = Field(
        ..., description="Toifa: kognitiv/kompetensiya/reflexiv/situatsion"
    )
    duration_minutes: int = Field(..., description="Davomiyligi (1–600 daqiqa)")
    description: str | None = Field(default=None, description="Tavsif (ixtiyoriy)")
    is_active: bool = Field(default=True, description="Faolligi")


class TestUpdateRequest(BaseModel):
    """Mavjud testni qisman yangilash so'rovi (R14.2, R14.4, R14.6).

    Barcha maydonlar ixtiyoriy: faqat yuborilganlar yangilanadi
    (``exclude_unset``). Yaroqsiz qiymat servisda 400 beradi (R14.6).
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {"title": "Yangilangan nom", "is_active": False}
        }
    )

    title: str | None = Field(default=None, description="Test nomi (1–200 belgi)")
    category: str | None = Field(default=None, description="Toifa")
    duration_minutes: int | None = Field(
        default=None, description="Davomiyligi (1–600 daqiqa)"
    )
    description: str | None = Field(default=None, description="Tavsif")
    is_active: bool | None = Field(default=None, description="Faolligi")


class TestResponse(BaseModel):
    """Test javobi (R14.2, R14.4).

    ``Test`` ORM obyektidan ``model_validate`` orqali quriladi.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Test ID")
    title: str = Field(..., description="Test nomi")
    category: str | None = Field(default=None, description="Toifa")
    duration_minutes: int | None = Field(default=None, description="Davomiyligi (daqiqa)")
    description: str | None = Field(default=None, description="Tavsif")
    is_active: bool = Field(..., description="Faolligi")


__all__ = [
    "AdminUserResponse",
    "AdminResultResponse",
    "TestCreateRequest",
    "TestUpdateRequest",
    "TestResponse",
]
