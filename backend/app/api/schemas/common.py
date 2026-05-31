"""Umumiy (domenlararo) javob sxemalari (R20.1, R20.6).

Bu yerda bir nechta router bo'ylab qayta ishlatiladigan kichik javob modellari
joylashadi. Hozircha — oddiy xabar javobi (masalan logout, parolni tiklash
oqimlarida).
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class MessageResponse(BaseModel):
    """Oddiy matnli muvaffaqiyat javobi (R3.2, R2.4).

    Servis qatlami ``{"message": ...}`` lug'atini qaytaradi (masalan
    :meth:`AuthService.request_password_reset`); ushbu model uni tasdiqlangan
    javob sxemasiga keltiradi.
    """

    message: str = Field(..., description="Foydalanuvchiga ko'rsatiladigan xabar")


__all__ = ["MessageResponse"]
