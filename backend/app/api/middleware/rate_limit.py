"""RateLimitMiddleware — joriy vaqt oynasi bo'yicha so'rovlarni cheklash (R17.3).

Bir manbadan (mijoz IP yoki autentifikatsiyalangan foydalanuvchi) joriy vaqt
oynasida kelgan so'rovlar soni ruxsat etilgan chegaradan oshsa, middleware
so'rovni `429` bilan rad etadi va strukturali xato shaklini qaytaradi:

    {"error": {"code": "rate_limit_exceeded", "message": "..."}}

Muhim xususiyat (R17.3): cheklov **faqat joriy vaqt oynasidagi** so'rovlar
soni asosida qabul qilinadi. Bu yerda fixed-window (qat'iy oyna) hisoblagich
ishlatiladi: vaqt o'qi `window_seconds` uzunlikdagi oynalarga bo'linadi va har
bir oyna mustaqil hisoblanadi. Yangi oyna boshlanganda hisoblagich noldan
boshlanadi — oldingi oyna qaroriga ta'sir qilmaydi.

Saqlash (`RateLimitStore`) abstraksiyasi orqali MVP'da in-memory `dict`
ishlatiladi, kelajakda esa Redis kabi backend bilan almashtirilishi mumkin.
Limit, oyna uzunligi va vaqt (clock) sinov uchun injeksiya qilinadi.
"""

from __future__ import annotations

import math
import threading
import time
from abc import ABC, abstractmethod
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.config import get_settings

#: Strukturali xato shakli uchun mashina o'qiy oladigan kod (R17.3).
RATE_LIMIT_ERROR_CODE = "rate_limit_exceeded"


class RateLimitStore(ABC):
    """Rate-limit hisoblagichlari uchun abstrakt saqlash backendi.

    Implementatsiyalar bitta `increment` amalini taqdim etadi: berilgan manba
    kaliti uchun joriy oynadagi so'rovlar sonini bittaga oshiradi va yangilangan
    sonni qaytaradi. Backend `source -> (window_start, count)` holatini saqlaydi
    va yangi oynaga o'tilganda hisoblagichni qayta tiklaydi. Bu interfeys
    in-memory yoki Redis kabi backendlar bilan bir xil bo'ladi.
    """

    @abstractmethod
    def increment(self, key: str, window_start: float) -> int:
        """`key` uchun `window_start` oynasidagi sanagichni oshirib qaytaradi.

        Agar saqlangan oyna `window_start` bilan mos kelmasa (yangi oyna), sanoq
        `1` dan boshlanadi; aks holda oldingi qiymatga `1` qo'shiladi.
        """

    def reset(self) -> None:
        """Barcha hisoblagichlarni tozalaydi (asosan sinov uchun)."""


class InMemoryRateLimitStore(RateLimitStore):
    """Jarayon ichidagi (in-memory) rate-limit saqlovchisi.

    `dict[source] = (window_start, count)` ko'rinishida saqlaydi. MVP uchun
    yetarli; ko'p-instansli joylashtirishda Redis backendi bilan almashtiriladi.
    Bir nechta worker thread'dan xavfsiz foydalanish uchun qulf (lock) bilan
    himoyalangan.
    """

    def __init__(self) -> None:
        self._data: dict[str, tuple[float, int]] = {}
        self._lock = threading.Lock()

    def increment(self, key: str, window_start: float) -> int:
        with self._lock:
            entry = self._data.get(key)
            if entry is None or entry[0] != window_start:
                count = 1
            else:
                count = entry[1] + 1
            self._data[key] = (window_start, count)
            return count

    def reset(self) -> None:
        with self._lock:
            self._data.clear()


def default_identify_source(request: Request) -> str:
    """So'rov manbasini aniqlaydi: autentifikatsiyalangan foydalanuvchi yoki IP.

    Ustuvorlik tartibi:
    1. `request.state.user_id` (auth middleware o'rnatgan bo'lsa).
    2. `request.state.user.id`.
    3. `X-User-Id` sarlavhasi (auth qatlami o'rnatgan bo'lsa).
    4. Mijoz IP manzili (`request.client.host`).
    """
    user_id = getattr(request.state, "user_id", None)
    if user_id is None:
        user = getattr(request.state, "user", None)
        if user is not None:
            user_id = getattr(user, "id", None)
    if user_id is not None:
        return f"user:{user_id}"

    header_uid = request.headers.get("x-user-id")
    if header_uid:
        return f"user:{header_uid}"

    client = request.client
    if client is not None and client.host:
        return f"ip:{client.host}"
    return "ip:unknown"


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Joriy oyna bo'yicha so'rovlarni cheklovchi middleware (R17.3).

    Parametrlar (barchasi sinov uchun injeksiya qilinadi):
    - `limit`: oyna ichida ruxsat etilgan maksimal so'rovlar soni. Berilmasa
      `settings.rate_limit_per_minute` ishlatiladi.
    - `window_seconds`: oyna uzunligi soniyalarda (standart `60`).
    - `store`: `RateLimitStore` implementatsiyasi (standart in-memory).
    - `clock`: joriy vaqtni soniyalarda qaytaruvchi chaqiriluvchi (standart
      `time.monotonic`) — sinovda boshqariladigan soat berish mumkin.
    - `identify_source`: so'rovdan manba kalitini hosil qiluvchi funksiya.
    """

    def __init__(
        self,
        app: Callable,
        *,
        limit: int | None = None,
        window_seconds: int = 60,
        store: RateLimitStore | None = None,
        clock: Callable[[], float] = time.monotonic,
        identify_source: Callable[[Request], str] = default_identify_source,
    ) -> None:
        super().__init__(app)
        if window_seconds <= 0:
            raise ValueError("window_seconds 0 dan katta bo'lishi kerak")
        self.limit = limit if limit is not None else get_settings().rate_limit_per_minute
        self.window_seconds = window_seconds
        self.store = store if store is not None else InMemoryRateLimitStore()
        self.clock = clock
        self.identify_source = identify_source

    def _window_start(self, now: float) -> float:
        """`now` soniyalari uchun joriy oynaning boshlanish nuqtasini hisoblaydi."""
        return math.floor(now / self.window_seconds) * self.window_seconds

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        now = float(self.clock())
        window_start = self._window_start(now)
        key = self.identify_source(request)
        count = self.store.increment(key, window_start)

        if count > self.limit:
            retry_after = max(0, int(math.ceil(window_start + self.window_seconds - now)))
            return JSONResponse(
                status_code=429,
                headers={"Retry-After": str(retry_after)},
                content={
                    "error": {
                        "code": RATE_LIMIT_ERROR_CODE,
                        "message": (
                            "So'rovlar soni ruxsat etilgan chegaradan oshdi. "
                            "Iltimos, birozdan so'ng qayta urinib ko'ring."
                        ),
                    }
                },
            )

        return await call_next(request)
