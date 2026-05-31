"""Vazifa 16.5 testlari — RBACGuard (rolga asoslangan kirish nazorati, R4, R17.6).

Testlar bir martalik (throwaway) FastAPI ilovasiga RBAC bog'liqliklarini va
egalik/biriktirilganlik yordamchilarini ulaydi va FastAPI `TestClient` orqali
tekshiradi:

Rol darajasi guardlari (R4.4, R4.5):
- `require_roles`/`require_admin`/`require_expert`/`require_leader` — ruxsat
  etilgan rol(lar)da 200, aks holda 403 (`code="forbidden"`).

Egalik/biriktirilganlik yordamchilari:
- `ensure_self_or_admin` — egasi yoki admin -> 200; begona Rahbar -> 403
  (R4.1, R4.3, R17.6).
- `ensure_expert_can_access_leader` — biriktirilgan ekspert/admin -> 200;
  biriktirilmagan ekspert yoki begona rol -> 403 (R4.2, R4.3).

Autentifikatsiya `get_current_principal` ni override qilish orqali soxtalashtiriladi
(token oqimi vazifa 16.1 testlarida alohida qoplangan).
"""

from __future__ import annotations

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.api.deps import Principal, get_current_principal, get_db
from app.api.errors import register_exception_handlers
from app.api.middleware.rbac import (
    ROLE_ADMIN,
    ROLE_EXPERT,
    ROLE_LEADER,
    ensure_expert_can_access_leader,
    ensure_self_or_admin,
    require_admin,
    require_expert,
    require_leader,
    require_roles,
)

# ---------------------------------------------------------------------------
# Yordamchilar: soxta (fake) DB sessiyasi (biriktirilganlik uchun)
# ---------------------------------------------------------------------------


class _FakeUser:
    """`is_expert_assigned` faqat ``organization_id`` ga qaraydi."""

    def __init__(self, organization_id: int | None) -> None:
        self.organization_id = organization_id


class _FakeSession:
    """``ExpertReviewRepository.is_expert_assigned`` uchun minimal soxta sessiya.

    `is_expert_assigned` ``session.get(User, expert_id)`` va
    ``session.get(User, leader_id)`` ni chaqiradi va ``organization_id`` larni
    taqqoslaydi. Bu yerda ``users`` lug'ati id -> tashkilot id ni belgilaydi.
    """

    def __init__(self, users: dict[int, int | None]) -> None:
        self._users = users

    def get(self, _model: object, primary_key: int) -> _FakeUser | None:
        if primary_key in self._users:
            return _FakeUser(self._users[primary_key])
        return None

    def close(self) -> None:  # noqa: D401 - hech narsa qilmaydi
        pass


def _override_principal(principal: Principal):
    """`get_current_principal` ni belgilangan principal bilan almashtiradi."""

    def _dep() -> Principal:
        return principal

    return _dep


def _client(app: FastAPI) -> TestClient:
    return TestClient(app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# Ilova quruvchi: RBAC bilan himoyalangan route'lar
# ---------------------------------------------------------------------------


def _build_app(
    *,
    principal: Principal,
    users: dict[int, int | None] | None = None,
) -> FastAPI:
    app = FastAPI()
    register_exception_handlers(app)

    # 1-bosqich: rol darajasi guardlari.
    @app.get("/admin-only", dependencies=[Depends(require_admin)])
    def _admin_only() -> dict[str, str]:
        return {"ok": "admin"}

    @app.get("/expert-area", dependencies=[Depends(require_expert)])
    def _expert_area() -> dict[str, str]:
        return {"ok": "expert"}

    @app.get("/leader-area", dependencies=[Depends(require_leader)])
    def _leader_area() -> dict[str, str]:
        return {"ok": "leader"}

    @app.get("/reports")
    def _reports(
        who: Principal = Depends(require_roles(ROLE_ADMIN, ROLE_EXPERT)),
    ) -> dict[str, str]:
        return {"ok": who.role}

    # 2-bosqich: egalik / biriktirilganlik yordamchilari (router ichida).
    @app.get("/users/{user_id}/profile")
    def _profile(
        user_id: int,
        who: Principal = Depends(get_current_principal),
    ) -> dict[str, int]:
        ensure_self_or_admin(who, user_id)
        return {"user_id": user_id}

    @app.get("/leaders/{leader_id}/results")
    def _leader_results(
        leader_id: int,
        who: Principal = Depends(get_current_principal),
        db=Depends(get_db),
    ) -> dict[str, int]:
        ensure_expert_can_access_leader(who, leader_id, db)
        return {"leader_id": leader_id}

    app.dependency_overrides[get_current_principal] = _override_principal(principal)

    def _override_db():
        session = _FakeSession(users or {})
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = _override_db
    return app


def _principal(user_id: int, role: str) -> Principal:
    return Principal(user_id=user_id, role=role, jti="test-jti")


# ---------------------------------------------------------------------------
# Rol darajasi: require_admin (R4.3, R4.5)
# ---------------------------------------------------------------------------


def test_require_admin_allows_administrator() -> None:
    app = _build_app(principal=_principal(1, ROLE_ADMIN))
    resp = _client(app).get("/admin-only")
    assert resp.status_code == 200
    assert resp.json() == {"ok": "admin"}


def test_require_admin_forbids_leader() -> None:
    app = _build_app(principal=_principal(1, ROLE_LEADER))
    resp = _client(app).get("/admin-only")
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "forbidden"


def test_require_admin_forbids_expert() -> None:
    app = _build_app(principal=_principal(1, ROLE_EXPERT))
    resp = _client(app).get("/admin-only")
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "forbidden"


# ---------------------------------------------------------------------------
# Rol darajasi: require_expert / require_leader / require_roles
# ---------------------------------------------------------------------------


def test_require_expert_allows_expert_and_admin() -> None:
    for role in (ROLE_EXPERT, ROLE_ADMIN):
        app = _build_app(principal=_principal(1, role))
        assert _client(app).get("/expert-area").status_code == 200


def test_require_expert_forbids_leader() -> None:
    app = _build_app(principal=_principal(1, ROLE_LEADER))
    assert _client(app).get("/expert-area").status_code == 403


def test_require_leader_allows_leader_and_admin() -> None:
    for role in (ROLE_LEADER, ROLE_ADMIN):
        app = _build_app(principal=_principal(1, role))
        assert _client(app).get("/leader-area").status_code == 200


def test_require_leader_forbids_expert() -> None:
    app = _build_app(principal=_principal(1, ROLE_EXPERT))
    assert _client(app).get("/leader-area").status_code == 403


def test_require_roles_multi_allows_listed_roles() -> None:
    for role in (ROLE_ADMIN, ROLE_EXPERT):
        app = _build_app(principal=_principal(1, role))
        resp = _client(app).get("/reports")
        assert resp.status_code == 200
        assert resp.json() == {"ok": role}


def test_require_roles_multi_forbids_unlisted_role() -> None:
    app = _build_app(principal=_principal(1, ROLE_LEADER))
    assert _client(app).get("/reports").status_code == 403


# ---------------------------------------------------------------------------
# Egalik: ensure_self_or_admin (R4.1, R4.3, R17.6)
# ---------------------------------------------------------------------------


def test_self_access_allowed_for_owner() -> None:
    app = _build_app(principal=_principal(7, ROLE_LEADER))
    resp = _client(app).get("/users/7/profile")
    assert resp.status_code == 200
    assert resp.json() == {"user_id": 7}


def test_other_user_forbidden_for_leader() -> None:
    app = _build_app(principal=_principal(7, ROLE_LEADER))
    resp = _client(app).get("/users/8/profile")
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "forbidden"


def test_admin_can_access_any_user_profile() -> None:
    app = _build_app(principal=_principal(1, ROLE_ADMIN))
    resp = _client(app).get("/users/999/profile")
    assert resp.status_code == 200
    assert resp.json() == {"user_id": 999}


# ---------------------------------------------------------------------------
# Biriktirilganlik: ensure_expert_can_access_leader (R4.2, R4.3)
# ---------------------------------------------------------------------------


def test_expert_can_access_assigned_leader() -> None:
    # Ekspert (id=2) va rahbar (id=5) bir xil tashkilotda -> biriktirilgan.
    app = _build_app(
        principal=_principal(2, ROLE_EXPERT),
        users={2: 100, 5: 100},
    )
    resp = _client(app).get("/leaders/5/results")
    assert resp.status_code == 200
    assert resp.json() == {"leader_id": 5}


def test_expert_cannot_access_unassigned_leader() -> None:
    # Ekspert (id=2) va rahbar (id=5) turli tashkilotlarda -> biriktirilmagan.
    app = _build_app(
        principal=_principal(2, ROLE_EXPERT),
        users={2: 100, 5: 200},
    )
    resp = _client(app).get("/leaders/5/results")
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "forbidden"


def test_admin_can_access_any_leader_results() -> None:
    # Admin uchun biriktirilganlik tekshirilmaydi (users bo'sh bo'lsa ham).
    app = _build_app(principal=_principal(1, ROLE_ADMIN), users={})
    resp = _client(app).get("/leaders/5/results")
    assert resp.status_code == 200
    assert resp.json() == {"leader_id": 5}


def test_leader_cannot_access_other_leader_results() -> None:
    # Rahbar roli ekspert doirasidagi natijalarga kira olmaydi (R4.2).
    app = _build_app(
        principal=_principal(9, ROLE_LEADER),
        users={9: 100, 5: 100},
    )
    resp = _client(app).get("/leaders/5/results")
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "forbidden"
