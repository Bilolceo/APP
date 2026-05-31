"""Markazlashtirilgan xato boshqaruvi va yagona tuzilgan xato formati (R20.6, R20.7).

Ushbu modul REST_API qatlami uchun **markazlashtirilgan** FastAPI exception
handler'larini taqdim etadi. Servis qatlami framework'dan mustaqil semantik
istisnolarni (``app.services.errors``) ko'taradi; bu yerda ular yagona tuzilgan
xato formatiga va mos HTTP holat kodlariga keltiriladi.

Dizayn (design.md — "API Design / Standart xato formati", "Error Handling"):

Barcha xatolar quyidagi tuzilgan sxemada qaytadi (R20.6)::

    {
      "error": {
        "code": "validation_error",
        "message": "Telefon raqami formati noto'g'ri",
        "details": [
          { "field": "phone", "reason": "must start with +998 and be 13 chars" }
        ]
      }
    }

HTTP holat kodlari (design.md — "HTTP status kodlari" / "Xato toifalari"):

==========================  ===========  ============================================
Manba                       HTTP holat   Izoh
==========================  ===========  ============================================
``code == "forbidden"``     403          RBAC/egalik buzilishi (R4.5, R11.6, R13.5)
``AuthError``               401          yaroqsiz/muddati o'tgan token, login (R2.5)
``NotFoundError``           404          resurs yo'q (R6.4, R7.9, R10.6, R11.7)
``ConflictError``           409          takroriy telefon (R1.2), takroriy topshirish
``ValidationError``         400          yaroqsiz maydon (R1, R5, R14, R20.6)
``code == "rate_limit_…"``  429          rate limit (R17.3)
generic ``ServiceError``    400          boshqa biznes-qoida xatosi
``RequestValidationError``  400          so'rov sxemasi/maydon xatosi (R20.6)
noma'lum yo'l               404          (R20.7)
qo'llab-quvvatlanmas usul   405          (R20.7)
kutilmagan xato             500          maxfiy tafsilotsiz (ServerError)
==========================  ===========  ============================================

Tamoyillar (design.md — "Error Handling / Tamoyillar"):
- Xato xabarlari ichki tafsilotlarni (stack trace, SQL) oshkor qilmaydi.
- Yaroqsiz so'rovlar resurs holatini o'zgartirmaydi (servis qatlami zimmasida).

Asosiy kirish nuqtasi — :func:`register_exception_handlers`.
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.services.errors import (
    AuthError,
    ConflictError,
    NotFoundError,
    ServiceError,
    ValidationError,
)

__all__ = [
    "build_error_response",
    "register_exception_handlers",
    "status_for_service_error",
]


# ---------------------------------------------------------------------------
# Holat kodi xaritalari (design.md — "HTTP status kodlari")
# ---------------------------------------------------------------------------

#: Servis xato ``code`` -> HTTP holat. ``forbidden``/``rate_limit_exceeded``
#: kodlari generic ``ServiceError`` ustida belgilanadigan mahalliy tiplar
#: (``PermissionDeniedError`` — PortfolioService/ExpertReviewService/RBAC,
#: rate-limit middleware) tomonidan ishlatiladi; ular alohida istisno tipiga
#: ega bo'lmagani uchun ``code`` orqali aniqlanadi (R4.5, R17.3).
_SERVICE_CODE_STATUS: dict[str, int] = {
    "validation_error": 400,
    "authentication_error": 401,
    "forbidden": 403,
    "not_found": 404,
    "conflict": 409,
    "rate_limit_exceeded": 429,
}

#: Servis istisno **tipi** -> HTTP holat. Bu birlamchi xaritalash: servislar
#: (masalan ``AuthService``) bir xil tip uchun turli ``code`` qiymatlaridan
#: foydalanishi mumkin (``invalid_credentials``, ``account_locked``,
#: ``phone_already_registered`` va h.k.), shuning uchun holat avval tip bo'yicha
#: aniqlanadi (``AuthError`` -> 401, ``ConflictError`` -> 409, ``NotFoundError``
#: -> 404, ``ValidationError`` -> 400). Bu errors.py docstring'idagi shartnomaga
#: (design.md HTTP status jadvali) muvofiqdir.
_SERVICE_TYPE_STATUS: tuple[tuple[type[ServiceError], int], ...] = (
    (ValidationError, 400),
    (AuthError, 401),
    (NotFoundError, 404),
    (ConflictError, 409),
)

#: Generic ServiceError (masalan ``code == "service_error"``) -> 400.
_DEFAULT_SERVICE_STATUS = 400

#: HTTP holat -> standart mashina-o'qiy kod (noma'lum yo'l/usul va boshqalar).
_HTTP_STATUS_CODE_NAME: dict[int, str] = {
    400: "bad_request",
    401: "authentication_error",
    403: "forbidden",
    404: "not_found",
    405: "method_not_allowed",
    409: "conflict",
    429: "rate_limit_exceeded",
    500: "internal_error",
}


def status_for_service_error(exc: ServiceError) -> int:
    """Servis istisnosini mos HTTP holat kodiga keltiradi.

    Xaritalash ikki bosqichli:

    1. **Maxsus kodlar** (``forbidden``, ``rate_limit_exceeded``) — bu kodlar
       alohida istisno tipiga ega emas (generic ``ServiceError`` ustida
       belgilanadi), shuning uchun avval ``code`` bo'yicha aniqlanadi (R4.5,
       R17.3).
    2. **Istisno tipi** — qolgan barcha holatlar istisno tipi bo'yicha
       aniqlanadi (``AuthError`` -> 401, ``ConflictError`` -> 409,
       ``NotFoundError`` -> 404, ``ValidationError`` -> 400). Bu servis bir tip
       uchun turli ``code`` qiymatlaridan foydalanganda ham (``AuthError`` ning
       ``invalid_credentials``/``account_locked`` kabi) to'g'ri holatni beradi.

    Hech biriga mos kelmasa generic 400 qaytariladi.

    Args:
        exc: servis qatlami istisnosi.

    Returns:
        HTTP holat kodi (int).
    """
    # 1-bosqich: tipga bog'lanmagan maxsus kodlar (forbidden/rate_limit).
    if exc.code in ("forbidden", "rate_limit_exceeded"):
        return _SERVICE_CODE_STATUS[exc.code]
    # 2-bosqich: istisno tipi bo'yicha (eng aniq moslikdan umumiyga).
    for exc_type, status_code in _SERVICE_TYPE_STATUS:
        if isinstance(exc, exc_type):
            return status_code
    # 3-bosqich: kod bo'yicha so'nggi urinish, aks holda generic 400.
    return _SERVICE_CODE_STATUS.get(exc.code, _DEFAULT_SERVICE_STATUS)


# ---------------------------------------------------------------------------
# Tuzilgan xato javobi quruvchi
# ---------------------------------------------------------------------------


def build_error_response(
    *,
    status_code: int,
    code: str,
    message: str,
    details: list[dict[str, Any]] | None = None,
) -> JSONResponse:
    """Yagona tuzilgan xato sxemasiga ega ``JSONResponse`` quradi (R20.6).

    Args:
        status_code: HTTP holat kodi.
        code: barqaror, mashina-o'qiy xato kodi (masalan ``"validation_error"``).
        message: foydalanuvchiga ko'rsatish mumkin bo'lgan (ichki tafsilotsiz) xabar.
        details: ``{"field": ..., "reason": ...}`` ko'rinishidagi yozuvlar ro'yxati.

    Returns:
        ``{"error": {"code", "message", "details"}}`` tanasiga ega javob.
    """
    body: dict[str, Any] = {
        "error": {
            "code": code,
            "message": message,
            "details": details or [],
        }
    }
    return JSONResponse(status_code=status_code, content=body)


def _service_error_details(exc: ServiceError) -> list[dict[str, Any]]:
    """Servis istisnosidan ``{"field", "reason"}`` yozuvlari ro'yxatini quradi.

    - ``field`` belgilangan bo'lsa, sababi sifatida xabar ishlatiladi (R1.3, R20.6).
    - ``details`` lug'atidagi qo'shimcha kontekst ham yozuvga aylantiriladi.
    """
    details: list[dict[str, Any]] = []
    if exc.field:
        details.append({"field": exc.field, "reason": exc.message})
    for key, value in exc.details.items():
        details.append({"field": key, "reason": value})
    return details


# ---------------------------------------------------------------------------
# Exception handler'lar
# ---------------------------------------------------------------------------


async def _service_error_handler(
    _request: Request, exc: ServiceError
) -> JSONResponse:
    """Barcha servis qatlami istisnolarini tuzilgan xatoga keltiradi.

    ``ServiceError`` quyi sinflari (``ValidationError``, ``AuthError``,
    ``NotFoundError``, ``ConflictError``) hamda servislardagi mahalliy
    ``PermissionDeniedError`` (``code == "forbidden"``) shu yerda qamrab olinadi.
    """
    status_code = status_for_service_error(exc)
    return build_error_response(
        status_code=status_code,
        code=exc.code,
        message=exc.message,
        details=_service_error_details(exc),
    )


async def _request_validation_handler(
    _request: Request, exc: RequestValidationError
) -> JSONResponse:
    """FastAPI/Pydantic so'rov validatsiyasi xatosini 400 ga keltiradi (R20.6).

    Har bir Pydantic xatosi ``{"field", "reason"}`` yozuviga aylantiriladi;
    ``field`` — xato joylashuvi (``loc``) nuqta bilan birlashtirilgan ko'rinishi
    (``body`` prefiksi tashlab yuboriladi).
    """
    details: list[dict[str, Any]] = []
    for error in exc.errors():
        loc = error.get("loc", ())
        # ``body``/``query``/``path`` prefiksini tashlab, qolgan yo'lni birlashtiramiz.
        parts = [str(part) for part in loc if part not in ("body", "query", "path")]
        field = ".".join(parts) if parts else (str(loc[0]) if loc else None)
        details.append({"field": field, "reason": error.get("msg", "invalid")})
    return build_error_response(
        status_code=400,
        code="validation_error",
        message="So'rov ma'lumotlari yaroqsiz",
        details=details,
    )


async def _http_exception_handler(
    _request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    """Starlette/FastAPI ``HTTPException`` ni tuzilgan xatoga keltiradi (R20.7).

    Noma'lum yo'l (404) va qo'llab-quvvatlanmaydigan usul (405) ham shu yo'l
    bilan yagona formatga keltiriladi.
    """
    code = _HTTP_STATUS_CODE_NAME.get(exc.status_code, "http_error")
    detail = exc.detail if isinstance(exc.detail, str) else "Xatolik yuz berdi"
    return build_error_response(
        status_code=exc.status_code,
        code=code,
        message=detail,
    )


async def _unhandled_exception_handler(
    _request: Request, _exc: Exception
) -> JSONResponse:
    """Kutilmagan xatoni maxfiy tafsilotsiz 500 ga keltiradi (ServerError).

    Ichki tafsilotlar (stack trace, SQL) oshkor qilinmaydi (design — Tamoyillar).
    """
    return build_error_response(
        status_code=500,
        code="internal_error",
        message="Ichki server xatosi",
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Markazlashtirilgan exception handler'larni FastAPI ilovasiga ulaydi.

    Ulanadigan handler'lar:
    - ``ServiceError`` (va barcha quyi sinflari) -> tuzilgan xato + mos holat kodi.
    - ``RequestValidationError`` -> 400 (maydon tafsilotlari bilan, R20.6).
    - ``StarletteHTTPException`` -> tuzilgan xato (404/405 va boshqalar, R20.7).
    - ``Exception`` -> 500 (maxfiy tafsilotsiz ServerError).

    Args:
        app: handler'lar ulanadigan FastAPI ilovasi.
    """
    app.add_exception_handler(ServiceError, _service_error_handler)
    app.add_exception_handler(RequestValidationError, _request_validation_handler)
    app.add_exception_handler(StarletteHTTPException, _http_exception_handler)
    app.add_exception_handler(Exception, _unhandled_exception_handler)
