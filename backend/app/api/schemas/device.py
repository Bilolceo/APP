"""Qurilma tokeni (push) so'rov/javob sxemalari (R16, R20.4).

``/devices/token`` endpointlari (POST register / DELETE invalidate) uchun
Pydantic modellar. Token har doim autentifikatsiyalangan principalga bog'lanadi
(``principal.user_id``) — router ``user_id`` ni so'rovdan emas, tokendan oladi
(R16.1).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class DeviceTokenRegisterRequest(BaseModel):
    """Qurilma tokenini ro'yxatdan o'tkazish so'rovi (R16.1)."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {"token": "fcm-device-token-abc123", "platform": "android"}
        }
    )

    token: str = Field(..., description="FCM qurilma tokeni")
    platform: str | None = Field(
        default=None, description="Platforma (masalan 'android')"
    )


class DeviceTokenInvalidateRequest(BaseModel):
    """Qurilma tokenini bekor qilish (yaroqsiz qilish) so'rovi (R16.6)."""

    model_config = ConfigDict(
        json_schema_extra={"example": {"token": "fcm-device-token-abc123"}}
    )

    token: str = Field(..., description="Bekor qilinadigan FCM qurilma tokeni")


class DeviceTokenResponse(BaseModel):
    """Qurilma tokeni javobi (R16.1).

    ``DeviceToken`` ORM obyektidan ``model_validate`` orqali quriladi.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Qurilma tokeni yozuvi ID")
    user_id: int = Field(..., description="Egasi (foydalanuvchi) ID")
    platform: str | None = Field(default=None, description="Platforma")
    is_valid: bool = Field(..., description="Token yaroqliligi")


__all__ = [
    "DeviceTokenRegisterRequest",
    "DeviceTokenInvalidateRequest",
    "DeviceTokenResponse",
]
