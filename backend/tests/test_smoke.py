"""Skelet (smoke) testlari — loyiha skeletoni to'g'ri sozlanganini tekshiradi.

Bu testlar 1.1-vazifa doirasida faqat skeleton/konfiguratsiyani tekshiradi:
- FastAPI ilovasi import bo'ladi va health-check ishlaydi;
- OpenAPI hujjatlari (R20.5) yoqilgan;
- Hypothesis profili kamida 100 iteratsiya bilan ishlaydi.
"""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from app.core.config import settings as app_settings
from app.main import app


def test_app_imports_and_has_title() -> None:
    """Ilova instansi yaratiladi va sarlavhaga ega."""
    assert app.title == app_settings.app_name


def test_openapi_schema_enabled() -> None:
    """OpenAPI sxemasi mavjud va asosiy maydonlarga ega (R20.5)."""
    schema = app.openapi()
    assert schema["info"]["title"] == app_settings.app_name
    assert "paths" in schema
    assert app.openapi_url == "/openapi.json"
    assert app.docs_url == "/docs"


def test_health_endpoint_registered() -> None:
    """/health endpointi ro'yxatdan o'tgan."""
    routes = {getattr(r, "path", None) for r in app.routes}
    assert "/health" in routes


def test_token_lifetimes_match_requirements() -> None:
    """Token muddatlari R2.1 ga mos: access 15 daqiqa, refresh 30 kun."""
    assert app_settings.access_token_expire_minutes == 15
    assert app_settings.refresh_token_expire_days == 30


def test_hypothesis_profile_runs_at_least_100_examples() -> None:
    """Faol Hypothesis profili kamida 100 iteratsiyaga sozlangan."""
    assert settings().max_examples >= 100


# Hypothesis ishlashini tasdiqlovchi minimal property testi.
@settings(max_examples=100)
@given(st.integers(), st.integers())
def test_integer_addition_is_commutative(a: int, b: int) -> None:
    """Sanity: butun sonlar qo'shilishi kommutativ (Hypothesis ishlayotganini tekshiradi)."""
    assert a + b == b + a
