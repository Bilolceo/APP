"""OpenAPI qoplam smoke testi (task 17.5, Property 46).

Maqsad: `create_app()` dagi barcha `/api/v1/*` endpointlar OpenAPI hujjatida
yo'l + HTTP usul + javob sxemasi bilan borligini tekshirish.
"""

from __future__ import annotations

from collections.abc import Iterable

from fastapi.routing import APIRoute

from app.main import create_app

_DOC_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE"}


def _iter_api_routes(routes: Iterable[object]) -> Iterable[APIRoute]:
    """Faqat hujjatlashtiriladigan `/api/v1` APIRoute'larni qaytaradi."""
    for route in routes:
        if not isinstance(route, APIRoute):
            continue
        if not route.path.startswith("/api/v1"):
            continue
        yield route


def test_openapi_covers_all_api_routes_with_method_and_schema() -> None:
    """Har bir `/api/v1` route OpenAPI'da method/path/schema bilan mavjud bo'ladi."""
    app = create_app()
    schema = app.openapi()
    openapi_paths: dict[str, dict] = schema.get("paths", {})

    missing: list[str] = []
    without_response_schema: list[str] = []

    for route in _iter_api_routes(app.routes):
        path_item = openapi_paths.get(route.path)
        if path_item is None:
            missing.append(f"{route.path} (path)")
            continue

        for method in sorted(route.methods & _DOC_METHODS):
            operation = path_item.get(method.lower())
            if operation is None:
                missing.append(f"{method} {route.path}")
                continue

            responses = operation.get("responses", {})
            has_schema = False
            for response in responses.values():
                content = (response or {}).get("content") or {}
                for media in content.values():
                    if "schema" in media:
                        has_schema = True
                        break
                if has_schema:
                    break

            if not has_schema:
                without_response_schema.append(f"{method} {route.path}")

    assert not missing, f"OpenAPI'da yo'q endpoint(lar): {', '.join(missing)}"
    assert not without_response_schema, (
        "Response schema yo'q endpoint(lar): "
        + ", ".join(without_response_schema)
    )
