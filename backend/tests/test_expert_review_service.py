"""ExpertReviewService uchun unit testlar (task 13.5, R13.1–R13.6).

`app/services/expert_review_service.py` — Ekspert_Moduli servisining biznes
mantig'ini in-memory SQLite engine ustida (mock'siz, real repositorylar va ORM
modellari bilan, bildirishnoma uchun stub bilan) tekshiradi.

Eslatma: servis `app/services/__init__.py` ga eksport qilinmaydi (parallel
vazifalar bilan ziddiyatni oldini olish uchun), shu sababli to'g'ridan-to'g'ri
modulidan import qilinadi.

Bog'liq talablar:
- R13.1: har bir mezon 1–5 butun son shkalasida baholashga ruxsat.
- R13.2: o'rtacha (1.00–5.00) hisoblanadi va rahbar natijasiga qo'shiladi.
- R13.3: yaroqsiz qiymat -> hech narsa saqlanmaydi, ValidationError.
- R13.4: to'ldirilmagan mezon -> hech narsa saqlanmaydi, ValidationError.
- R13.5: biriktirilmagan rahbar -> hech narsa saqlanmaydi, 403.
- R13.6: muvaffaqiyatli baholashda rahbarga bildirishnoma.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

import app.models  # noqa: F401  (modellarni metadata'ga ro'yxatdan o'tkazadi)
from app.core.db import create_db_engine
from app.models.base import Base
from app.models.content import Test
from app.models.expert import ExpertReview
from app.models.reference import Organization, Role
from app.models.result import TestResult
from app.models.session import TestSession
from app.models.user import User
from app.services.errors import ValidationError
from app.services.expert_review_service import (
    ExpertReviewOutcome,
    ExpertReviewService,
    PermissionDeniedError,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def engine():
    """Sxema yaratilgan in-memory SQLite engine."""
    eng = create_db_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(eng)
    try:
        yield eng
    finally:
        Base.metadata.drop_all(eng)
        eng.dispose()


@pytest.fixture()
def session(engine):
    """Test uchun bitta sessiya."""
    with Session(engine) as sess:
        yield sess


@pytest.fixture()
def roles(session: Session) -> dict[str, Role]:
    """Rahbar va Ekspert rollari."""
    leader_role = Role(name="Rahbar")
    expert_role = Role(name="Ekspert")
    session.add_all([leader_role, expert_role])
    session.flush()
    return {"Rahbar": leader_role, "Ekspert": expert_role}


@pytest.fixture()
def organization(session: Session) -> Organization:
    """Namunaviy tashkilot (biriktirilganlik shu orqali aniqlanadi)."""
    org = Organization(name="MTT-1")
    session.add(org)
    session.flush()
    return org


def _make_user(
    session: Session,
    *,
    phone: str,
    role: Role,
    organization_id: int | None = None,
) -> User:
    user = User(
        full_name="Foydalanuvchi",
        phone=phone,
        password_hash="h",
        role_id=role.id,
        organization_id=organization_id,
    )
    session.add(user)
    session.flush()
    return user


def _make_result_for(
    session: Session,
    *,
    leader: User,
    created_at: datetime | None = None,
    percentage: Decimal = Decimal("50.00"),
) -> TestResult:
    """Rahbar uchun yakunlangan sessiya + natija yaratadi (expert_score=NULL)."""
    test = Test(title="Diagnostika", category="kompetensiya", duration_minutes=30)
    session.add(test)
    session.flush()
    now = datetime.now(timezone.utc)
    ts = TestSession(
        user_id=leader.id,
        test_id=test.id,
        status="completed",
        started_at=now,
        expires_at=now + timedelta(minutes=30),
        completed_at=now,
    )
    session.add(ts)
    session.flush()
    result = TestResult(
        user_id=leader.id,
        test_id=test.id,
        session_id=ts.id,
        total_score=Decimal("10.00"),
        max_score=Decimal("20.00"),
        percentage=percentage,
        level="O'rta",
    )
    if created_at is not None:
        result.created_at = created_at
    session.add(result)
    session.flush()
    return result


class StubNotifier:
    """Bildirishnoma servisi o'rniga stub — chaqiruvlarni qayd etadi (R13.6)."""

    def __init__(self, *, raise_error: bool = False) -> None:
        self.calls: list[int] = []
        self._raise_error = raise_error

    def notify_expert_review(self, leader) -> int:  # noqa: ANN001 - test stub
        self.calls.append(leader)
        if self._raise_error:
            raise RuntimeError("bildirishnoma xatosi (simulyatsiya)")
        return 1


def _valid_scores() -> dict[str, int]:
    """Oltita mezon bo'yicha yaroqli baholar (o'rtacha = 3.50)."""
    return {
        "management_culture": 5,
        "teamwork": 4,
        "pedagogical_process": 3,
        "innovation": 2,
        "documentation": 4,
        "strategic_planning": 3,
    }


@pytest.fixture()
def assigned_pair(
    session: Session, roles: dict[str, Role], organization: Organization
) -> tuple[User, User]:
    """Bir tashkilotga tegishli (biriktirilgan) ekspert + rahbar."""
    expert = _make_user(
        session,
        phone="+998900000001",
        role=roles["Ekspert"],
        organization_id=organization.id,
    )
    leader = _make_user(
        session,
        phone="+998900000002",
        role=roles["Rahbar"],
        organization_id=organization.id,
    )
    session.commit()
    return expert, leader


# ---------------------------------------------------------------------------
# Muvaffaqiyatli baholash (R13.1, R13.2, R13.6)
# ---------------------------------------------------------------------------


def test_submit_review_persists_and_computes_average(
    session: Session, assigned_pair: tuple[User, User]
) -> None:
    """Yaroqli baholash saqlanadi va o'rtacha to'g'ri hisoblanadi (R13.1, R13.2)."""
    expert, leader = assigned_pair
    notifier = StubNotifier()
    service = ExpertReviewService(session, notifications=notifier)

    outcome = service.submit_review(expert.id, leader.id, _valid_scores())

    assert isinstance(outcome, ExpertReviewOutcome)
    # (5+4+3+2+4+3)/6 = 21/6 = 3.50.
    assert outcome.average_score == Decimal("3.50")

    stored = session.get(ExpertReview, outcome.review_id)
    assert stored is not None
    assert stored.expert_id == expert.id
    assert stored.leader_id == leader.id
    assert stored.management_culture == 5
    assert stored.strategic_planning == 3
    assert stored.average_score == Decimal("3.50")


def test_submit_review_applies_expert_score_to_latest_result(
    session: Session, assigned_pair: tuple[User, User]
) -> None:
    """Ekspert bahosi rahbarning eng so'nggi natijasiga qo'shiladi (R13.2)."""
    expert, leader = assigned_pair
    old = _make_result_for(
        session, leader=leader, created_at=datetime(2023, 1, 1, tzinfo=timezone.utc)
    )
    latest = _make_result_for(
        session, leader=leader, created_at=datetime(2024, 1, 1, tzinfo=timezone.utc)
    )
    session.commit()

    service = ExpertReviewService(session, notifications=StubNotifier())
    outcome = service.submit_review(expert.id, leader.id, _valid_scores())

    assert outcome.expert_score_applied is True
    session.refresh(latest)
    session.refresh(old)
    # Faqat eng so'nggi natijaga qo'shiladi.
    assert latest.expert_score == Decimal("3.50")
    assert old.expert_score is None


def test_submit_review_triggers_notification(
    session: Session, assigned_pair: tuple[User, User]
) -> None:
    """Muvaffaqiyatli baholashda rahbarga bildirishnoma yuboriladi (R13.6)."""
    expert, leader = assigned_pair
    notifier = StubNotifier()
    service = ExpertReviewService(session, notifications=notifier)

    service.submit_review(expert.id, leader.id, _valid_scores())

    assert notifier.calls == [leader.id]


def test_submit_review_without_result_still_saves(
    session: Session, assigned_pair: tuple[User, User]
) -> None:
    """Rahbarda natija bo'lmasa ham sharh saqlanadi, ball qo'shilmaydi (R13.1)."""
    expert, leader = assigned_pair
    notifier = StubNotifier()
    service = ExpertReviewService(session, notifications=notifier)

    outcome = service.submit_review(expert.id, leader.id, _valid_scores())

    assert outcome.expert_score_applied is False
    assert session.get(ExpertReview, outcome.review_id) is not None
    # Bildirishnoma baribir yuboriladi.
    assert notifier.calls == [leader.id]


def test_submit_review_works_without_notifier(
    session: Session, assigned_pair: tuple[User, User]
) -> None:
    """Bildirishnoma servisi berilmasa ham baholash muvaffaqiyatli (R13.6 seam)."""
    expert, leader = assigned_pair
    service = ExpertReviewService(session)  # notifier yo'q

    outcome = service.submit_review(expert.id, leader.id, _valid_scores())

    assert session.get(ExpertReview, outcome.review_id) is not None


def test_notification_failure_does_not_break_saved_review(
    session: Session, assigned_pair: tuple[User, User]
) -> None:
    """Bildirishnoma xatosi allaqachon saqlangan sharhni buzmaydi (R13.6)."""
    expert, leader = assigned_pair
    notifier = StubNotifier(raise_error=True)
    service = ExpertReviewService(session, notifications=notifier)

    # Bildirishnoma ichida xato bo'lsa ham submit_review xato ko'tarmaydi.
    outcome = service.submit_review(expert.id, leader.id, _valid_scores())

    assert session.get(ExpertReview, outcome.review_id) is not None
    assert notifier.calls == [leader.id]


# ---------------------------------------------------------------------------
# Validatsiya — hech narsa saqlanmaydi (R13.3, R13.4)
# ---------------------------------------------------------------------------


def test_submit_review_rejects_out_of_range_score(
    session: Session, assigned_pair: tuple[User, User]
) -> None:
    """1–5 oralig'idan tashqari qiymat rad etiladi, hech narsa saqlanmaydi (R13.3)."""
    expert, leader = assigned_pair
    notifier = StubNotifier()
    service = ExpertReviewService(session, notifications=notifier)

    scores = _valid_scores()
    scores["innovation"] = 7  # 1–5 dan tashqarida

    with pytest.raises(ValidationError):
        service.submit_review(expert.id, leader.id, scores)

    assert session.scalars(select(ExpertReview)).first() is None
    assert notifier.calls == []


def test_submit_review_rejects_non_integer_score(
    session: Session, assigned_pair: tuple[User, User]
) -> None:
    """Butun bo'lmagan qiymat (float) rad etiladi (R13.3)."""
    expert, leader = assigned_pair
    service = ExpertReviewService(session, notifications=StubNotifier())

    scores = _valid_scores()
    scores["teamwork"] = 3.5  # type: ignore[assignment]

    with pytest.raises(ValidationError):
        service.submit_review(expert.id, leader.id, scores)

    assert session.scalars(select(ExpertReview)).first() is None


def test_submit_review_rejects_missing_criterion(
    session: Session, assigned_pair: tuple[User, User]
) -> None:
    """To'ldirilmagan mezon rad etiladi, hech narsa saqlanmaydi (R13.4)."""
    expert, leader = assigned_pair
    service = ExpertReviewService(session, notifications=StubNotifier())

    scores = _valid_scores()
    del scores["documentation"]  # mezon yetishmaydi

    with pytest.raises(ValidationError):
        service.submit_review(expert.id, leader.id, scores)

    assert session.scalars(select(ExpertReview)).first() is None


# ---------------------------------------------------------------------------
# Biriktirilganlik (R13.5)
# ---------------------------------------------------------------------------


def test_submit_review_rejects_unassigned_expert(
    session: Session, roles: dict[str, Role]
) -> None:
    """Biriktirilmagan ekspert -> 403, hech narsa saqlanmaydi (R13.5)."""
    org1 = Organization(name="MTT-A")
    org2 = Organization(name="MTT-B")
    session.add_all([org1, org2])
    session.flush()
    expert = _make_user(
        session, phone="+998900000010", role=roles["Ekspert"], organization_id=org1.id
    )
    leader = _make_user(
        session, phone="+998900000011", role=roles["Rahbar"], organization_id=org2.id
    )
    session.commit()

    notifier = StubNotifier()
    service = ExpertReviewService(session, notifications=notifier)

    with pytest.raises(PermissionDeniedError):
        service.submit_review(expert.id, leader.id, _valid_scores())

    assert session.scalars(select(ExpertReview)).first() is None
    assert notifier.calls == []


def test_permission_denied_error_code_is_forbidden(
    session: Session, roles: dict[str, Role]
) -> None:
    """PermissionDeniedError.code == 'forbidden' (router 403 ga keltiradi)."""
    expert = _make_user(session, phone="+998900000020", role=roles["Ekspert"])
    leader = _make_user(session, phone="+998900000021", role=roles["Rahbar"])
    session.commit()

    service = ExpertReviewService(session)
    with pytest.raises(PermissionDeniedError) as exc_info:
        service.submit_review(expert.id, leader.id, _valid_scores())

    assert exc_info.value.code == "forbidden"


def test_submit_review_no_organization_is_not_assigned(
    session: Session, roles: dict[str, Role]
) -> None:
    """Tashkilot biriktirilmagan (NULL) bo'lsa biriktirilganlik yo'q (R13.5)."""
    # Ikkalasi ham organization_id=None — bir xil NULL "tashkilot" emas.
    expert = _make_user(session, phone="+998900000030", role=roles["Ekspert"])
    leader = _make_user(session, phone="+998900000031", role=roles["Rahbar"])
    session.commit()

    service = ExpertReviewService(session)
    with pytest.raises(PermissionDeniedError):
        service.submit_review(expert.id, leader.id, _valid_scores())
