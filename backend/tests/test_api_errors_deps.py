"""Vazifa 16.1 testlari — markazlashtirilgan xato boshqaruvi va auth bog'liqligi.

Ushbu testlar bir martalik (throwaway) FastAPI ilovasi ustida ishlaydi:
- ``register_exception_handlers`` ulanadi va har bir istisno tipini ko'taradigan
  route'lar holat kodi + yagona tuzilgan tana (``{"error": {...}}``) qaytarishini
  tasdiqlaydi (R20.6, R20.7).
- ``get_current_principal`` bog'liqligi yaroqli/muddati o'tgan/blacklistdagi/
  yo'q/yaroqsiz token holatlarida to'g'ri ishlashini tasdiqlaydi (R2.5, R17.2).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.api.deps import Principal, get_current_principal, get_db
from app.api.errors import register_exception_handlers
from app.core.tokens import create_access_token, create_refresh_token
from app.services.errors import (
    AuthError,
    ConflictError,
    NotFoundError,
    ServiceError,
    ValidationError,
)

# ---------------------------------------------------------------------------
# Yordamchilar: soxta (fake) DB sessiyasi va ilova quruvchi
# ---------------------------------------------------------------------------


class _FakeSession:
    """``TokenRepository.is_jti_blacklisted`` uchun minimal soxta sessiya.

    ``is_jti_blacklisted`` faqat ``session.get(TokenBlacklist, jti)`` ni
    chaqiradi; shu sababli ``get`` blacklistdagi ``jti`` lar uchun truthy,
    aks holda ``None`` qaytaradi.
    """

    def __init__(self, blacklisted_jtis: set[str] | None = None) -> None:
        self._blacklisted = blacklisted_jtis or set()

    def get(self, _model: object, primary_key: object) -> object | None:
        return object() if primary_key in self._blacklisted else None

    def close(self) -> None:  # noqa: D401 - hech narsa qilmaydi
        pass


class _Body(BaseModel):
    name: str


def _build_app(blacklisted: set[str] | None = None) -> FastAPI:
    """Handler'lar va har bir istisno tipini ko'taradigan route'lar bilan ilova."""
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/raise/validation")
    def _validation() -> None:
        raise ValidationError("Telefon raqami noto'g'ri", field="phone")

    @app.get("/raise/auth")
    def _auth() -> None:
        raise AuthError("Yaroqsiz token")

    @app.get("/raise/forbidden")
    def _forbidden() -> None:
        raise ServiceError("Ruxsat yo'q", code="forbidden")

    @app.get("/raise/notfound")
    def _notfound() -> None:
        raise NotFoundError("Topilmadi")

    @app.get("/raise/conflict")
    def _conflict() -> None:
        raise ConflictError("Takroriy telefon")

    @app.get("/raise/ratelimit")
    def _ratelimit() -> None:
        raise ServiceError("Juda ko'p so'rov", code="rate_limit_exceeded")

    @app.get("/raise/generic")
    def _generic() -> None:
        raise ServiceError("Umumiy xato")

    @app.get("/raise/unhandled")
    def _unhandled() -> None:
        raise RuntimeError("kutilmagan")

    @app.post("/echo")
    def _echo(body: _Body) -> dict[str, str]:
        return {"name": body.name}

    @app.get("/protected")
    def _protected(principal: Principal = Depends(get_current_principal)) -> dict:
        return {"user_id": principal.user_id, "role": principal.role, "jti": principal.jti}

    # Auth bog'liqligi DB sessiyasini soxta sessiya bilan almashtiramiz.
    def _override_db():
        session = _FakeSession(blacklisted)
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = _override_db
    return app


# TestClient kutilgan xato javoblarida istisno ko'tarmasligi uchun.
def _client(app: FastAPI) -> TestClient:
    return TestClient(app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# Xato boshqaruvi testlari (R20.6, R20.7)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("path", "expected_status", "expected_code"),
    [
        ("/raise/validation", 400, "validation_error"),
        ("/raise/auth", 401, "authentication_error"),
        ("/raise/forbidden", 403, "forbidden"),
        ("/raise/notfound", 404, "not_found"),
        ("/raise/conflict", 409, "conflict"),
        ("/raise/ratelimit", 429, "rate_limit_exceeded"),
        ("/raise/generic", 400, "service_error"),
        ("/raise/unhandled", 500, "internal_error"),
    ],
)
def test_service_errors_map_to_status_and_structured_body(
    path: str, expected_status: int, expected_code: str
) -> None:
    """Har bir istisno tipi mos holat kodi va tuzilgan tanaga keltiriladi."""
    client = _client(_build_app())
    response = client.get(path)
    assert response.status_code == expected_status
    body = response.json()
    assert set(body.keys()) == {"error"}
    error = body["error"]
    assert error["code"] == expected_code
    assert isinstance(error["message"], str) and error["message"]
    assert isinstance(error["details"], list)


def test_validation_error_includes_field_details() -> None:
    """ValidationError ``field`` ni ``details`` ga {field, reason} sifatida qo'yadi (R20.6)."""
    client = _client(_build_app())
    response = client.get("/raise/validation")
    assert response.status_code == 400
    details = response.json()["error"]["details"]
    assert {"field": "phone", "reason": "Telefon raqami noto'g'ri"} in details


def test_request_validation_error_returns_400_with_field() -> None:
    """FastAPI so'rov validatsiyasi xatosi 400 va maydon tafsilotini qaytaradi (R20.6)."""
    client = _client(_build_app())
    # Majburiy ``name`` maydoni yo'q -> RequestValidationError.
    response = client.post("/echo", json={})
    assert response.status_code == 400
    body = response.json()["error"]
    assert body["code"] == "validation_error"
    fields = {d["field"] for d in body["details"]}
    assert "name" in fields


def test_unknown_path_returns_structured_404() -> None:
    """Noma'lum yo'l yagona formatdagi 404 qaytaradi (R20.7)."""
    client = _client(_build_app())
    response = client.get("/no/such/path")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_unsupported_method_returns_structured_405() -> None:
    """Qo'llab-quvvatlanmaydigan usul yagona formatdagi 405 qaytaradi (R20.7)."""
    client = _client(_build_app())
    # ``/echo`` faqat POST; DELETE -> 405.
    response = client.delete("/echo")
    assert response.status_code == 405
    assert response.json()["error"]["code"] == "method_not_allowed"


# ---------------------------------------------------------------------------
# Auth bog'liqligi testlari (R2.5, R17.2)
# ---------------------------------------------------------------------------


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_valid_token_returns_principal() -> None:
    """Yaroqli access token Principal (user_id/role/jti) ni beradi."""
    client = _client(_build_app())
    issued = create_access_token(user_id=42, role="Rahbar")
    response = client.get("/protected", headers=_auth_header(issued.token))
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == 42
    assert data["role"] == "Rahbar"
    assert data["jti"] == issued.jti


def test_missing_token_returns_401() -> None:
    """Token yo'q -> 401 (R2.5)."""
    client = _client(_build_app())
    response = client.get("/protected")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "authentication_error"


def test_expired_token_returns_401() -> None:
    """Muddati o'tgan token -> 401 (R2.5)."""
    client = _client(_build_app())
    past = datetime.now(timezone.utc) - timedelta(hours=1)
    issued = create_access_token(user_id=1, role="Rahbar", now=past)
    response = client.get("/protected", headers=_auth_header(issued.token))
    assert response.status_code == 401


def test_invalid_token_returns_401() -> None:
    """Buzilgan/yaroqsiz token -> 401 (R2.5)."""
    client = _client(_build_app())
    response = client.get("/protected", headers=_auth_header("not.a.valid.token"))
    assert response.status_code == 401


def test_wrong_type_token_returns_401() -> None:
    """Refresh token access kutilgan joyga kelsa -> 401 (R17.2)."""
    client = _client(_build_app())
    issued = create_refresh_token(user_id=1)
    response = client.get("/protected", headers=_auth_header(issued.token))
    assert response.status_code == 401


def test_blacklisted_token_returns_401() -> None:
    """Bekor qilingan (blacklistdagi) jti -> 401 (R2.4, R2.5)."""
    issued = create_access_token(user_id=7, role="Administrator")
    client = _client(_build_app(blacklisted={issued.jti}))
    response = client.get("/protected", headers=_auth_header(issued.token))
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "authentication_error"
