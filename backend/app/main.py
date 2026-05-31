"""FastAPI ilovasi — kirish nuqtasi va to'liq wiring (vazifa 21.1).

Bu modul barcha REST_API routerlarini (R20), markazlashtirilgan xato
boshqaruvini (R20.6, R20.7) va middleware'larni (R17.3, R17.5) yagona FastAPI
ilovasiga ulaydi. Autentifikatsiya/RBAC esa global middleware sifatida emas,
har bir endpointning ``get_current_principal`` bog'liqligi orqali qo'llanadi
(R17.6) — shu sababli bu yerda global auth middleware qo'shilmaydi.

Tuzilma:
- ``create_app()`` — application factory; ilova instansini yaratadi va sozlaydi.
- Routerlar ``settings.api_v1_prefix`` (``/api/v1``) ostida ulanadi; har bir
  router o'zining lokal prefiksini (``/auth``, ``/users``, ...) e'lon qiladi.
- Middleware tartibi (R17.3, R17.5) — pastdagi izohga qarang.
- ``/health`` salomatlik endpointi va OpenAPI hujjatlari saqlanadi (R20.5).
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.errors import register_exception_handlers
from app.api.middleware import LoggingMiddleware, RateLimitMiddleware
from app.api.routers import (
    admin_router,
    analytics_router,
    auth_router,
    devices_router,
    expert_router,
    portfolio_router,
    questions_router,
    rating_router,
    recommendations_router,
    reports_router,
    tests_router,
    users_router,
)
from app.core.config import settings

#: Ilovaga ulanadigan barcha routerlar. Har biri o'zining lokal prefiksiga
#: ega; bu yerda ular ``settings.api_v1_prefix`` ostida birlashtiriladi
#: (masalan ``/api/v1/auth/login``, ``/api/v1/tests``).
_ROUTERS = (
    auth_router,
    users_router,
    tests_router,
    questions_router,
    recommendations_router,
    portfolio_router,
    analytics_router,
    admin_router,
    expert_router,
    reports_router,
    rating_router,
    devices_router,
)


def _parse_cors_origins(raw: str) -> list[str]:
    """CORS ruxsat etilgan manbalar satrini ro'yxatga aylantiradi.

    ``settings.cors_allow_origins`` — vergul bilan ajratilgan manbalar ro'yxati
    yoki ``*`` (barchasiga ruxsat). Bo'sh joylar olib tashlanadi; ``*`` bo'lsa
    yagona ``["*"]`` qaytariladi (barcha manbalarga ruxsat).
    """
    raw = (raw or "").strip()
    if raw == "*" or raw == "":
        return ["*"]
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


def create_app() -> FastAPI:
    """FastAPI ilova instansini yaratadi va sozlaydi (application factory)."""
    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        # OpenAPI hujjatlari yoqilgan (R20.5)
        docs_url=settings.docs_url,
        redoc_url=settings.redoc_url,
        openapi_url=settings.openapi_url,
    )

    # --- Markazlashtirilgan xato boshqaruvi (R20.6, R20.7) ---
    # Servis qatlami semantik istisnolari yagona tuzilgan xato formatiga va mos
    # HTTP holat kodlariga shu yerda keltiriladi.
    register_exception_handlers(application)

    # --- Routerlar (R20) ---
    # Har bir router ``/api/v1`` prefiksi ostida ulanadi; routerning o'z lokal
    # prefiksi (``/auth``, ``/users``, ...) bunga qo'shiladi.
    for router in _ROUTERS:
        application.include_router(router, prefix=settings.api_v1_prefix)

    # --- Middleware (R17.3, R17.5) ---
    # Starlette middleware'larni ro'yxatga olishning TESKARI tartibida ishlatadi:
    # eng oxiri qo'shilgan middleware ish vaqtida eng tashqi (outermost) bo'ladi.
    # Maqsadli ish vaqti tartibi (tashqaridan ichkariga):
    #     RateLimit (eng tashqi) -> Logging -> CORS -> routerlar.
    # Auth/RBAC global middleware emas — u har bir endpointda
    # ``get_current_principal`` bog'liqligi orqali qo'llanadi (R17.6).
    #
    # Shu tartibga erishish uchun ro'yxatga olish ketma-ketligi (oldindan
    # oxirigacha): CORS -> Logging -> RateLimit (oxirgi qo'shilgan eng tashqi).

    # 1) CORS — eng ichki global middleware. Wildcard (``*``) bilan
    # ``allow_credentials=True`` brauzerlarda taqiqlanadi, shuning uchun
    # manbalar aniq ro'yxat bo'lgandagina cookie/cred ruxsat etiladi.
    cors_origins = _parse_cors_origins(settings.cors_allow_origins)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=cors_origins != ["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 2) Logging — strukturali so'rov jurnali; maxfiy maydonlarni maskalaydi (R17.5).
    application.add_middleware(LoggingMiddleware)

    # 3) RateLimit — eng tashqi; joriy oyna bo'yicha so'rovlarni cheklaydi (R17.3).
    application.add_middleware(
        RateLimitMiddleware, limit=settings.rate_limit_per_minute
    )

    @application.get("/health", tags=["system"], summary="Salomatlik tekshiruvi")
    def health_check() -> dict[str, str]:
        """Servis ishlayotganini tasdiqlovchi oddiy health-check endpointi."""
        return {
            "status": "ok",
            "service": settings.app_name,
            "version": settings.app_version,
            "environment": settings.environment,
        }

    return application


app = create_app()
