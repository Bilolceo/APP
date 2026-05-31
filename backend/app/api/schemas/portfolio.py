"""Portfolio javob sxemalari — ``/portfolio/*`` (R11, R20.1).

``/portfolio/me`` (GET) va ``POST /portfolio/upload`` endpointlari uchun javob
modeli. Yuklash so'rovi ``multipart/form-data`` (``UploadFile`` + ``title`` form
maydoni) bo'lgani uchun alohida so'rov modeli yo'q — router ``UploadFile`` va
``Form`` parametrlarini bevosita qabul qiladi.

Router ``PortfolioService`` ustidagi yupqa HTTP qatlami: servis
``PortfolioItem`` (frozen dataclass) qaytaradi, bu yerdagi
:class:`PortfolioItemResponse` esa uni tasdiqlangan javob sxemasiga keltiradi
(``from_attributes=True``). Validatsiya (tur/hajm/nom) va egalik (R11.6) servis
qatlamida.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PortfolioItemResponse(BaseModel):
    """Portfolio yozuvi javobi (R11.1, R11.2).

    ``PortfolioItem`` dataclass'idan ``model_validate`` orqali quriladi.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Portfolio yozuvi ID")
    title: str = Field(..., description="Yozuv nomi")
    file_url: str | None = Field(default=None, description="Fayl havolasi")
    file_type: str | None = Field(default=None, description="Fayl turi (pdf/png/...)")
    size_bytes: int | None = Field(default=None, description="Fayl hajmi (bayt)")
    created_at: datetime | None = Field(default=None, description="Yaratilgan sana")


__all__ = ["PortfolioItemResponse"]
