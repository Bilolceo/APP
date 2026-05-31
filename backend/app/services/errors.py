"""Servis qatlami xatoliklari — framework'dan mustaqil (R20.6, Error Handling).

Ushbu modul biznes-mantiq (servis) qatlami ko'taradigan **framework-agnostik**
istisnolarni (exception) belgilaydi. Servislar (AuthService va boshqalar) FastAPI
yoki HTTP haqida hech narsa bilmaydi: ular faqat ushbu semantik xatoliklarni
ko'taradi. REST_API qatlami (keyingi vazifa 16.1/17.1) ushbu istisnolarni
markazlashtirilgan exception handler orqali yagona tuzilgan xato formatiga
(code/message/details) hamda mos HTTP holat kodlariga keltiradi.

design.md — "Error Handling / Xato toifalari va javoblar" jadvaliga muvofiq
moslik:

| Servis istisnosi    | HTTP holat | Misol manba                                  |
|---------------------|-----------|-----------------------------------------------|
| ``ValidationError`` | 400       | yaroqsiz maydon (R1, R5, R14, R20.6)          |
| ``AuthError``       | 401       | yaroqsiz/muddati o'tgan token, login (R2)     |
| ``NotFoundError``   | 404       | test/sessiya/natija/yo'l yo'q (R6.4, R7.9...) |
| ``ConflictError``   | 409       | takroriy telefon (R1.2), takroriy topshirish  |

Tamoyillar (design.md — "Error Handling / Tamoyillar"):
- Xatolar ichki tafsilotlarni (stack trace, SQL) oshkor qilmaydi.
- Login va parolni tiklash xatolari hisob mavjudligini bildirmaydi (R2.2, R3.2)
  — buni AuthService umumiy ("generic") xabarlar bilan ta'minlaydi.
"""

from __future__ import annotations

from typing import Any


class ServiceError(Exception):
    """Barcha servis qatlami xatoliklari uchun bazaviy sinf.

    Maydonlar:
    - ``message``: foydalanuvchiga ko'rsatish mumkin bo'lgan (ichki tafsilotsiz)
      xabar.
    - ``code``: barqaror mashina-o'qiy oladigan xato kodi (router uni xato
      javobining ``code`` maydoniga joylaydi).
    - ``field``: (ixtiyoriy) qaysi kirish maydoni xato ekanini ko'rsatadi
      (R1.3, R20.6) — masalan ``"phone"``.
    - ``details``: (ixtiyoriy) qo'shimcha tuzilgan kontekst.
    """

    #: Standart xato kodi (quyi sinflar qayta belgilaydi).
    code: str = "service_error"

    def __init__(
        self,
        message: str,
        *,
        code: str | None = None,
        field: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        if code is not None:
            self.code = code
        self.field = field
        self.details: dict[str, Any] = details or {}

    def __repr__(self) -> str:  # pragma: no cover - faqat nosozliklarni tuzatish uchun
        return (
            f"{type(self).__name__}(code={self.code!r}, message={self.message!r}, "
            f"field={self.field!r})"
        )


class ValidationError(ServiceError):
    """Kirish validatsiyasi muvaffaqiyatsiz — HTTP 400 (R1, R5, R14, R20.6).

    Qaysi maydon yaroqsizligini ``field`` orqali ko'rsatadi (R1.3).
    """

    code = "validation_error"

    def __init__(
        self,
        message: str,
        *,
        field: str | None = None,
        code: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message,
            code=code or "validation_error",
            field=field,
            details=details,
        )


class AuthError(ServiceError):
    """Autentifikatsiya muvaffaqiyatsiz — HTTP 401 (R2.2, R2.5, R2.6, R3.4).

    Login va parolni tiklash uchun xabarlar ataylab **umumiy** bo'ladi va qaysi
    maydon (telefon yoki parol) noto'g'ri ekanini hamda hisob mavjudligini
    oshkor qilmaydi (R2.2, R3.2).
    """

    code = "authentication_error"


class NotFoundError(ServiceError):
    """So'ralgan resurs topilmadi — HTTP 404 (R6.4, R7.9, R10.6, R11.7)."""

    code = "not_found"


class ConflictError(ServiceError):
    """Resurs holati bilan ziddiyat — HTTP 409 (R1.2 takroriy telefon, R7.7)."""

    code = "conflict"


__all__ = [
    "ServiceError",
    "ValidationError",
    "AuthError",
    "NotFoundError",
    "ConflictError",
]
