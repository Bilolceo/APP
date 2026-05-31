"""16.7-vazifa uchun unit testlar — RateLimitMiddleware va LoggingMiddleware.

Testlar bir martalik (throwaway) FastAPI ilovasiga middleware'larni ulaydi va
FastAPI `TestClient` orqali tekshiradi:

RateLimitMiddleware (R17.3):
- Joriy oyna ichida chegaradan oshganda 429 va strukturali xato shakli;
- Yangi oynada (boshqariladigan soat bilan) hisoblagich qayta tiklanadi;
- Manba (IP / foydalanuvchi) bo'yicha alohida hisoblanadi.

LoggingMiddleware (R17.5):
- Strukturali jurnal yozuvi (method, path, status, duration) chiqadi;
- Maxfiy qiymatlar (parol, token, telefon, authorization) jurnalda
  ochiq matnda ko'rinmaydi (caplog bilan tekshiriladi).
"""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.middleware.logging import (
    LOGGER_NAME,
    MASK,
    LoggingMiddleware,
    sanitize_mapping,
)
from app.api.middleware.rate_limit import (
    RATE_LIMIT_ERROR_CODE,
    InMemoryRateLimitStore,
    RateLimitMiddleware,
)


class FakeClock:
    """Boshqariladigan soat — sinovda vaqtni qo'lda surish uchun."""

    def __init__(self, start: float = 0.0) -> None:
        self.now = start

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


# ---------------------------------------------------------------------------
# RateLimitMiddleware testlari (R17.3)
# ---------------------------------------------------------------------------


def _make_rate_limited_app(
    *, limit: int, window_seconds: int, clock: FakeClock
) -> FastAPI:
    app = FastAPI()
    app.add_middleware(
        RateLimitMiddleware,
        limit=limit,
        window_seconds=window_seconds,
        store=InMemoryRateLimitStore(),
        clock=clock,
    )

    @app.get("/ping")
    def ping() -> dict[str, str]:
        return {"status": "ok"}

    return app


def test_rate_limit_allows_up_to_limit_then_429_in_same_window() -> None:
    """Chegaragacha so'rovlar o'tadi, oshgani 429 va strukturali xato qaytaradi."""
    clock = FakeClock(start=1000.0)
    app = _make_rate_limited_app(limit=3, window_seconds=60, clock=clock)
    client = TestClient(app)

    # Limit = 3 -> birinchi 3 ta so'rov muvaffaqiyatli.
    for _ in range(3):
        resp = client.get("/ping")
        assert resp.status_code == 200

    # 4-chi so'rov joriy oynada chegaradan oshadi -> 429.
    blocked = client.get("/ping")
    assert blocked.status_code == 429
    body = blocked.json()
    assert body["error"]["code"] == RATE_LIMIT_ERROR_CODE
    assert isinstance(body["error"]["message"], str)
    assert body["error"]["message"]
    assert "Retry-After" in blocked.headers


def test_rate_limit_resets_in_new_window() -> None:
    """Yangi vaqt oynasiga o'tilganda hisoblagich noldan boshlanadi (R17.3)."""
    clock = FakeClock(start=0.0)
    app = _make_rate_limited_app(limit=2, window_seconds=60, clock=clock)
    client = TestClient(app)

    assert client.get("/ping").status_code == 200
    assert client.get("/ping").status_code == 200
    # Joriy oynada chegaradan oshdi.
    assert client.get("/ping").status_code == 429

    # Keyingi oynaga o'tamiz (60 soniyadan keyin) — sanoq qayta tiklanadi.
    clock.advance(60)
    assert client.get("/ping").status_code == 200
    assert client.get("/ping").status_code == 200
    assert client.get("/ping").status_code == 429


def test_rate_limit_decision_depends_only_on_current_window() -> None:
    """Qaror faqat joriy oyna soniga bog'liq: oldingi to'la oyna ta'sir qilmaydi."""
    clock = FakeClock(start=0.0)
    app = _make_rate_limited_app(limit=1, window_seconds=10, clock=clock)
    client = TestClient(app)

    # Oyna 0: 1 ta o'tadi, 2-chi bloklanadi.
    assert client.get("/ping").status_code == 200
    assert client.get("/ping").status_code == 429

    # Oyna 1 (10s): oldingi oyna to'lgan bo'lsa-da, yangi oynada yana 1 ta o'tadi.
    clock.advance(10)
    assert client.get("/ping").status_code == 200


def test_rate_limit_separates_sources_by_user_header() -> None:
    """Turli manbalar (foydalanuvchi) alohida hisoblanadi."""
    clock = FakeClock(start=0.0)
    app = _make_rate_limited_app(limit=1, window_seconds=60, clock=clock)
    client = TestClient(app)

    # user A o'z chegarasini ishlatadi.
    assert client.get("/ping", headers={"X-User-Id": "A"}).status_code == 200
    assert client.get("/ping", headers={"X-User-Id": "A"}).status_code == 429
    # user B alohida hisoblanadi — hali bloklanmaydi.
    assert client.get("/ping", headers={"X-User-Id": "B"}).status_code == 200


def test_in_memory_store_increment_and_reset() -> None:
    """InMemoryRateLimitStore joriy oyna sanog'ini to'g'ri oshiradi va tiklaydi."""
    store = InMemoryRateLimitStore()
    assert store.increment("ip:1", window_start=0.0) == 1
    assert store.increment("ip:1", window_start=0.0) == 2
    # Yangi oyna -> sanoq qaytadan 1.
    assert store.increment("ip:1", window_start=60.0) == 1
    # Boshqa kalit mustaqil.
    assert store.increment("ip:2", window_start=60.0) == 1
    store.reset()
    assert store.increment("ip:1", window_start=60.0) == 1


# ---------------------------------------------------------------------------
# LoggingMiddleware testlari (R17.5)
# ---------------------------------------------------------------------------


def _make_logged_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(LoggingMiddleware)

    @app.get("/items")
    def items() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/login")
    def login(payload: dict) -> dict[str, str]:
        return {"status": "ok"}

    return app


def test_logging_emits_structured_request_record(caplog) -> None:
    """So'rov jurnali method/path/status/duration maydonlarini chiqaradi."""
    app = _make_logged_app()
    client = TestClient(app)

    with caplog.at_level(logging.INFO, logger=LOGGER_NAME):
        resp = client.get("/items")
    assert resp.status_code == 200

    records = [r for r in caplog.records if r.name == LOGGER_NAME]
    assert records, "so'rov jurnali yozuvi chiqishi kerak"
    record = records[-1]
    log = record.request_log
    assert log["method"] == "GET"
    assert log["path"] == "/items"
    assert log["status_code"] == 200
    assert isinstance(log["duration_ms"], (int, float))
    assert log["duration_ms"] >= 0


def test_logging_masks_sensitive_query_params(caplog) -> None:
    """Maxfiy query parametrlari (token, telefon, parol) jurnalda maskalanadi."""
    app = _make_logged_app()
    client = TestClient(app)

    secret_token = "supersecrettoken12345"
    secret_phone = "+998901234567"
    secret_password = "MyP@ssw0rd!"

    with caplog.at_level(logging.INFO, logger=LOGGER_NAME):
        resp = client.get(
            "/items",
            params={
                "token": secret_token,
                "phone": secret_phone,
                "password": secret_password,
                "page": "2",
            },
        )
    assert resp.status_code == 200

    record = [r for r in caplog.records if r.name == LOGGER_NAME][-1]
    query = record.request_log["query"]
    assert query["token"] == MASK
    assert query["phone"] == MASK
    assert query["password"] == MASK
    # Maxfiy bo'lmagan maydon saqlanadi.
    assert query["page"] == "2"

    # Butun jurnal matnida (barcha yozuvlar) maxfiy qiymatlar ko'rinmaydi.
    full_text = caplog.text
    assert secret_token not in full_text
    assert secret_phone not in full_text
    assert secret_password not in full_text


def test_logging_never_logs_authorization_header(caplog) -> None:
    """Authorization sarlavhasi va body jurnalga xom ko'rinishda tushmaydi."""
    app = _make_logged_app()
    client = TestClient(app)

    bearer = "Bearer eyJhbGciOiJ.secretsignature.value"
    body_password = "topsecretbodypw"

    with caplog.at_level(logging.INFO, logger=LOGGER_NAME):
        resp = client.post(
            "/login",
            headers={"Authorization": bearer},
            json={"phone": "+998901112233", "password": body_password},
        )
    assert resp.status_code == 200

    full_text = caplog.text
    # Authorization tokeni va body parol jurnalda ochiq ko'rinmaydi.
    assert bearer not in full_text
    assert "secretsignature" not in full_text
    assert body_password not in full_text
    assert "+998901112233" not in full_text


# ---------------------------------------------------------------------------
# sanitize_mapping yordamchi funksiyasi testlari (R17.5)
# ---------------------------------------------------------------------------


def test_sanitize_mapping_masks_known_sensitive_keys() -> None:
    """sanitize_mapping ma'lum maxfiy kalitlarni maskalaydi, qolganini saqlaydi."""
    data = {
        "username": "ali",
        "password": "secret",
        "access_token": "abc.def.ghi",
        "phone": "+998901234567",
        "page": 1,
    }
    cleaned = sanitize_mapping(data)
    assert cleaned["username"] == "ali"
    assert cleaned["password"] == MASK
    assert cleaned["access_token"] == MASK
    assert cleaned["phone"] == MASK
    assert cleaned["page"] == 1
    # Asl lug'at o'zgartirilmaydi.
    assert data["password"] == "secret"


def test_sanitize_mapping_recurses_into_nested_structures() -> None:
    """Ichki lug'at va ro'yxatlardagi maxfiy kalitlar ham maskalanadi."""
    data = {
        "user": {"name": "vali", "parol": "x", "tokens": {"refresh": "r"}},
        "items": [{"token": "t1"}, {"id": 5}],
    }
    cleaned = sanitize_mapping(data)
    assert cleaned["user"]["name"] == "vali"
    assert cleaned["user"]["parol"] == MASK
    assert cleaned["user"]["tokens"] == MASK  # "tokens" kaliti "token"ni o'z ichiga oladi
    assert cleaned["items"][0]["token"] == MASK
    assert cleaned["items"][1]["id"] == 5


def test_sanitize_mapping_supports_extra_sensitive_keys() -> None:
    """Qo'shimcha maxfiy kalitlarni extra_sensitive orqali berish mumkin."""
    data = {"national_id": "12345", "name": "guli"}
    cleaned = sanitize_mapping(data, extra_sensitive=["national_id"])
    assert cleaned["national_id"] == MASK
    assert cleaned["name"] == "guli"


def test_sanitize_mapping_handles_empty_input() -> None:
    """Bo'sh yoki None kirish bo'sh lug'at qaytaradi."""
    assert sanitize_mapping(None) == {}
    assert sanitize_mapping({}) == {}
