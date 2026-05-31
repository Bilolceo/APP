"""Autentifikatsiya so'rov/javob sxemalari (R1, R2, R3, R20.1, R20.2, R20.6).

Ushbu modul ``/auth/*`` endpointlari uchun Pydantic **so'rov** va **javob**
modellarini belgilaydi. Maqsad — so'rov tanasini tuzilgan (typed) qilish va
avtomatik OpenAPI hujjati (R20.5) hamda yagona validatsiya xatosi (R20.6) ni
ta'minlash.

Muhim dizayn qarori: **chuqur biznes validatsiyasi servis qatlamida** bajariladi
(``AuthService`` — telefon formati, parol uzunligi, rol whitelisti va h.k.,
R1.5–R1.7). Shu sababli bu yerdagi modellar ataylab **yumshoq** (maydon mavjudligi
va tiplar) bo'lib, servis xatolarini takrorlamaydi — bir xil qoidani ikki joyda
saqlash xatoga olib keladi. Bu, ayniqsa, login uchun muhim: noto'g'ri formatdagi
telefon ham "telefon yoki parol noto'g'ri" umumiy xatosini (R2.2) berishi kerak,
sxema darajasida emas.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# So'rov modellari (Request)
# ---------------------------------------------------------------------------


class RegisterRequest(BaseModel):
    """Ro'yxatdan o'tish so'rovi (R1.1).

    Majburiy maydonlar (``phone``, ``password``, ``full_name``, ``role``) hamda
    ixtiyoriy profil maydonlari. To'liq validatsiya (format/uzunlik/rol) servis
    qatlamida (R1.3, R1.5, R1.6, R1.7).
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "phone": "+998901234567",
                "password": "secret123",
                "full_name": "Ali Valiyev",
                "role": "Rahbar",
                "organization_id": 1,
                "region_id": 1,
                "position": "Direktor",
                "experience_years": 5,
            }
        }
    )

    phone: str = Field(..., description="Telefon raqami (+998, 13 belgi)")
    password: str = Field(..., description="Parol (8–64 belgi)")
    full_name: str = Field(..., description="To'liq ism (1–200 belgi)")
    role: str = Field(..., description="Rol: Rahbar, Ekspert yoki Administrator")

    # Ixtiyoriy profil maydonlari (R1.1).
    organization_id: int | None = Field(default=None, description="Tashkilot ID")
    region_id: int | None = Field(default=None, description="Hudud ID")
    position: str | None = Field(default=None, description="Lavozim")
    experience_years: int | None = Field(default=None, description="Ish staji (0–60)")
    education_level: str | None = Field(default=None, description="Ta'lim darajasi")
    qualification_courses: str | None = Field(
        default=None, description="Malaka oshirish kurslari"
    )
    certificates: str | None = Field(default=None, description="Sertifikatlar")
    org_type: str | None = Field(default=None, description="Tashkilot turi")


class LoginRequest(BaseModel):
    """Tizimga kirish so'rovi (R2.1)."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {"phone": "+998901234567", "password": "secret123"}
        }
    )

    phone: str = Field(..., description="Telefon raqami")
    password: str = Field(..., description="Parol")


class RefreshRequest(BaseModel):
    """Token yangilash so'rovi (R2.3)."""

    refresh_token: str = Field(..., description="Yangilash (refresh) tokeni")


class LogoutRequest(BaseModel):
    """Tizimdan chiqish so'rovi (R2.4).

    Access token ``Authorization`` sarlavhasidan olinadi; refresh token
    (ixtiyoriy) tanada beriladi va u ham bekor qilinadi.
    """

    refresh_token: str | None = Field(
        default=None, description="Bekor qilinadigan yangilash tokeni (ixtiyoriy)"
    )


class ForgotPasswordRequest(BaseModel):
    """Parolni tiklashni boshlash so'rovi (R3.1, R3.2)."""

    phone: str = Field(..., description="Ro'yxatdan o'tgan telefon raqami")


class ResetPasswordRequest(BaseModel):
    """Tasdiqlash kodi bilan parolni yangilash so'rovi (R3.3–R3.7)."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "phone": "+998901234567",
                "code": "123456",
                "new_password": "new-secret-123",
            }
        }
    )

    phone: str = Field(..., description="Telefon raqami")
    code: str = Field(..., description="6 raqamli tasdiqlash kodi")
    new_password: str = Field(..., description="Yangi parol (>= 8 belgi)")


# ---------------------------------------------------------------------------
# Javob modellari (Response)
# ---------------------------------------------------------------------------


class TokenPairResponse(BaseModel):
    """Login javobi — access + refresh token juftligi (R2.1)."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "access_token": "eyJ...",
                "refresh_token": "eyJ...",
                "token_type": "bearer",
                "expires_in": 900,
            }
        }
    )

    access_token: str = Field(..., description="JWT kirish tokeni (15 daqiqa)")
    refresh_token: str = Field(..., description="Yangilash tokeni (30 kun)")
    token_type: str = Field(default="bearer", description="Token turi")
    expires_in: int = Field(..., description="Access token amal muddati (soniya)")


class AccessTokenResponse(BaseModel):
    """Refresh javobi — faqat yangi access token (R2.3)."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "access_token": "eyJ...",
                "token_type": "bearer",
                "expires_in": 900,
            }
        }
    )

    access_token: str = Field(..., description="Yangi JWT kirish tokeni")
    token_type: str = Field(default="bearer", description="Token turi")
    expires_in: int = Field(..., description="Access token amal muddati (soniya)")


__all__ = [
    "RegisterRequest",
    "LoginRequest",
    "RefreshRequest",
    "LogoutRequest",
    "ForgotPasswordRequest",
    "ResetPasswordRequest",
    "TokenPairResponse",
    "AccessTokenResponse",
]
