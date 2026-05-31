"""LoggingMiddleware — strukturali so'rov jurnali va jurnal gigiyenasi (R17.5).

Har bir so'rov uchun strukturali jurnal yozuvi hosil qiladi: HTTP usuli, yo'l,
javob holati (status) va davomiyligi (millisekundlarda). Maxfiy maydonlar
(parol, token, telefon, `authorization` sarlavhasi) hech qachon ochiq matnda
jurnalga tushmasligi uchun maskalanadi yoki o'tkazib yuboriladi.

R17.5: Backend_Xizmati maxfiy ma'lumotlarni (parol, token, telefon raqami kabi)
jurnal yozuvlariga yozmaydi. Bu yerda **deny-list** (maxfiy kalitlar nomi) va
**allow-list** (faqat ruxsat etilgan metadata maydonlari jurnalga tushadi)
yondashuvi birgalikda ishlatiladi:
- So'rov tanasi (body) hech qachon xom ko'rinishda jurnalga yozilmaydi.
- Strukturali kontekst lug'ati maxfiy kalitlar bo'yicha rekursiv tozalanadi.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Callable, Iterable

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

#: Jurnalga yozish uchun ishlatiladigan logger nomi.
LOGGER_NAME = "app.request"

logger = logging.getLogger(LOGGER_NAME)

#: Maxfiy hisoblanuvchi kalit nomlari (deny-list). Kalit nomida ushbu
#: bo'laklardan biri uchrasa (katta-kichik harfdan qat'i nazar), qiymat
#: maskalanadi. R17.5: parol, token, telefon, authorization va shunga o'xshash.
SENSITIVE_KEY_PARTS: tuple[str, ...] = (
    "password",
    "passwd",
    "pwd",
    "parol",
    "token",
    "secret",
    "authorization",
    "auth",
    "api_key",
    "apikey",
    "phone",
    "telefon",
    "code_hash",
    "password_hash",
    "refresh",
    "access_token",
    "set-cookie",
    "cookie",
)

#: Maskalangan qiymat o'rniga qo'yiladigan belgi.
MASK = "***"


def _is_sensitive_key(key: str) -> bool:
    """Kalit nomi maxfiy maydonlar deny-listiga mos kelishini tekshiradi."""
    lowered = key.lower()
    return any(part in lowered for part in SENSITIVE_KEY_PARTS)


def sanitize_value(key: str, value: Any) -> Any:
    """Bitta (kalit, qiymat) juftligini tozalaydi.

    Agar kalit maxfiy bo'lsa, qiymat `MASK` bilan almashtiriladi. Aks holda,
    qiymat ichidagi ichki tuzilmalar (dict/list) rekursiv tozalanadi.
    """
    if _is_sensitive_key(key):
        return MASK
    return _sanitize(value)


def _sanitize(value: Any) -> Any:
    """Ixtiyoriy qiymatni rekursiv tozalaydi (dict/list ichidagi maxfiy kalitlar)."""
    if isinstance(value, dict):
        return {k: sanitize_value(str(k), v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_sanitize(item) for item in value]
    return value


def sanitize_mapping(
    data: dict[str, Any] | None,
    *,
    extra_sensitive: Iterable[str] | None = None,
) -> dict[str, Any]:
    """Lug'atni maxfiy kalitlardan tozalaydi (maskalaydi).

    Rekursiv ishlaydi: ichki lug'at va ro'yxatlar ham tozalanadi. `extra_sensitive`
    orqali qo'shimcha maxfiy kalit nomlarini berish mumkin (masalan, ma'lum bir
    endpoint maydoni). Asl lug'at o'zgartirilmaydi — yangi lug'at qaytariladi.
    """
    if not data:
        return {}
    extra = tuple(s.lower() for s in (extra_sensitive or ()))

    def is_sensitive(key: str) -> bool:
        lowered = key.lower()
        if _is_sensitive_key(key):
            return True
        return any(part in lowered for part in extra)

    result: dict[str, Any] = {}
    for key, value in data.items():
        if is_sensitive(str(key)):
            result[key] = MASK
        else:
            result[key] = _sanitize(value)
    return result


class LoggingMiddleware(BaseHTTPMiddleware):
    """Strukturali so'rov jurnalini yozuvchi middleware (R17.5).

    Har bir so'rov yakunlanganda quyidagi maydonlarni jurnalga yozadi:
    `method`, `path`, `status_code`, `duration_ms`. So'rov tanasi (body) hech
    qachon jurnalga tushmaydi va maxfiy sarlavhalar (`authorization`, `cookie`)
    hamda so'rov parametrlari maskalanadi.

    Parametrlar:
    - `logger`: ishlatiladigan logger (standart modul loggeri) — sinov uchun
      injeksiya qilinadi.
    - `clock`: davomiylikni o'lchash uchun monotonik soat (standart
      `time.perf_counter`).
    - `log_query_params`: `True` bo'lsa, so'rov query parametrlari tozalangan
      holda jurnalga qo'shiladi (standart `True`).
    """

    def __init__(
        self,
        app: Callable,
        *,
        logger: logging.Logger = logger,
        clock: Callable[[], float] = time.perf_counter,
        log_query_params: bool = True,
    ) -> None:
        super().__init__(app)
        self.logger = logger
        self.clock = clock
        self.log_query_params = log_query_params

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        start = self.clock()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            duration_ms = round((self.clock() - start) * 1000, 3)
            self._emit(request, status_code, duration_ms)

    def _emit(self, request: Request, status_code: int, duration_ms: float) -> None:
        """Tozalangan strukturali jurnal yozuvini chiqaradi."""
        record: dict[str, Any] = {
            "method": request.method,
            "path": request.url.path,
            "status_code": status_code,
            "duration_ms": duration_ms,
        }
        if self.log_query_params:
            query = dict(request.query_params)
            if query:
                record["query"] = sanitize_mapping(query)

        # So'rov tanasi (body) hech qachon jurnalga yozilmaydi (R17.5).
        # Maxfiy maydonlar `record`da maskalangan; `extra` orqali strukturali
        # uzatamiz, lekin xabar matnida ham faqat tozalangan qiymatlar bo'ladi.
        self.logger.info(
            "request method=%s path=%s status=%s duration_ms=%s",
            record["method"],
            record["path"],
            record["status_code"],
            record["duration_ms"],
            extra={"request_log": record},
        )
