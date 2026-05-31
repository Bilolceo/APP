"""Vazifa 21.1 — FastAPI ilova wiring integratsion testlari.

``create_app()`` orqali qurilgan ilovada quyidagilar tekshiriladi:
- ``/health`` endpointi 200 qaytaradi (R20.5);
- barcha asosiy routerlar ``/api/v1`` prefiksi ostida ulangan (R20);
- markazlashtirilgan xato boshqaruvi ulangan (noma'lum yo'l yagona tuzilgan
  xato formatida 404 beradi, R20.6/R20.7);
- OpenAPI sxemasi (``/openapi.json``) xizmat qiladi va ulangan yo'llarni
  o'z ichiga oladi (R20.5).
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app, create_app

# Ulangan routerlarning vakil (representative) yo'llari — har bir prefiks
# guruhidan kamida bittadan (R20).
REPRESENTATIVE_PATHS = (
    "/api/v1/auth/login",
    "/api/v1/auth/register",
    "/api/v1/users/me",
    "/api/v1/tests",
    "/api/v1/tests/{test_id}",
    "/api/v1/questions",
    "/api/v1/recommendations/me",
    "/api/v1/portfolio/me",
    "/api/v1/analytics/me",
    "/api/v1/admin/users",
    "/api/v1/expert/reviews",
    "/api/v1/reports/admin",
    "/api/v1/rating",
    "/api/v1/devices/token",
)


@pytest.fixture()
def client() -> TestClient:
    """``create_app()`` orqali qurilgan ilova mijozi."""
    application = create_app()
    return TestClient(application, raise_server_exceptions=False)


def _route_paths(application) -> set[str]:
    """Ilovadagi barcha route yo'llari to'plamini qaytaradi."""
    return {getattr(r, "path", None) for r in application.routes}


def test_health_endpoint_returns_200(client: TestClient) -> None:
    """/health endpointi 200 va kutilgan tanani qaytaradi (R20.5)."""
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["service"] == settings.app_name


def test_module_level_app_is_built() -> None:
    """Modul darajasidagi ``app`` instansi qurilgan va sarlavhaga ega."""
    assert app.title == settings.app_name
    # Skeletondan ancha ko'p route bo'lishi kerak (health + docs + 12 router).
    assert len(app.routes) > 30


@pytest.mark.parametrize("path", REPRESENTATIVE_PATHS)
def test_representative_routes_are_wired(client: TestClient, path: str) -> None:
    """Vakil routerlar ``/api/v1`` prefiksi ostida ro'yxatdan o'tgan (R20)."""
    assert path in _route_paths(client.app)


def test_all_router_prefixes_present(client: TestClient) -> None:
    """Barcha 12 router prefiksi ``/api/v1`` ostida mavjud (R20)."""
    paths = _route_paths(client.app)
    expected_prefixes = (
        "/api/v1/auth",
        "/api/v1/users",
        "/api/v1/tests",
        "/api/v1/questions",
        "/api/v1/recommendations",
        "/api/v1/portfolio",
        "/api/v1/analytics",
        "/api/v1/admin",
        "/api/v1/expert",
        "/api/v1/reports",
        "/api/v1/rating",
        "/api/v1/devices",
    )
    for prefix in expected_prefixes:
        assert any(p is not None and p.startswith(prefix) for p in paths), prefix


def test_openapi_served_and_contains_wired_paths(client: TestClient) -> None:
    """``/openapi.json`` xizmat qiladi va ulangan yo'llarni o'z ichiga oladi (R20.5)."""
    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    schema = resp.json()
    assert schema["info"]["title"] == settings.app_name
    openapi_paths = set(schema["paths"].keys())
    for path in REPRESENTATIVE_PATHS:
        assert path in openapi_paths, path


def test_unknown_path_returns_structured_404(client: TestClient) -> None:
    """Markazlashtirilgan handler noma'lum yo'l uchun tuzilgan 404 beradi (R20.7)."""
    resp = client.get("/api/v1/no-such-endpoint")
    assert resp.status_code == 404
    body = resp.json()
    assert "error" in body
    assert body["error"]["code"] == "not_found"


def test_exception_handlers_registered(client: TestClient) -> None:
    """Markazlashtirilgan exception handler'lar ilovaga ulangan (R20.6)."""
    # FastAPI/Starlette handler'lari ``exception_handlers`` registratsiyasida
    # bo'lishi kerak (ServiceError, RequestValidationError, HTTPException, Exception).
    assert len(client.app.exception_handlers) >= 3
