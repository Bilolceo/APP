"""ReportService uchun unit testlar (task 12.4, R15.1–R15.7).

`app/services/report_service.py` — Hisobot_Moduli servisining biznes mantig'ini
in-memory SQLite engine ustida (mock'siz, real repositorylar va ORM modellari
bilan) tekshiradi.

Bog'liq talablar:
- R15.1: rahbarlar soni, test topshirganlar soni, o'rtacha ball, eng past/yuqori
  kompetensiyalar.
- R15.2: kompetensiya kesimida jamlangan foiz; teng qiymatda barchasi.
- R15.3: hudud kesimi jamlanmasi.
- R15.4: tashkilot kesimi jamlanmasi.
- R15.5: individual xronologik dinamika.
- R15.6: ekspert faqat biriktirilgan tashkilotlar bilan cheklanadi.
- R15.7: natija yo'q bo'lsa nol qiymatli/bo'sh muvaffaqiyatli holat.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

import app.models  # noqa: F401  (modellarni metadata'ga ro'yxatdan o'tkazadi)
from app.core.db import create_db_engine
from app.models.base import Base
from app.models.content import Test
from app.models.reference import Competency, Organization, Region, Role
from app.models.result import CompetencyResult, TestResult
from app.models.session import TestSession
from app.models.user import User
from app.services.report_service import (
    AdminReport,
    IndividualDynamics,
    ReportService,
    SectionReport,
)


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
    """Rahbar/Ekspert/Administrator rollari."""
    leader = Role(name="Rahbar")
    expert = Role(name="Ekspert")
    admin = Role(name="Administrator")
    session.add_all([leader, expert, admin])
    session.flush()
    return {"Rahbar": leader, "Ekspert": expert, "Administrator": admin}


@pytest.fixture()
def test_obj(session: Session) -> Test:
    """Namunaviy test."""
    t = Test(title="Diagnostika", category="kompetensiya", duration_minutes=30)
    session.add(t)
    session.flush()
    return t


@pytest.fixture()
def competencies(session: Session) -> list[Competency]:
    """Ikkita kompetensiya."""
    c1 = Competency(name="Boshqaruv")
    c2 = Competency(name="Pedagogik")
    session.add_all([c1, c2])
    session.flush()
    return [c1, c2]


def _make_leader(
    session: Session,
    roles: dict[str, Role],
    *,
    phone: str,
    region_id: int | None = None,
    organization_id: int | None = None,
) -> User:
    user = User(
        full_name=f"Rahbar {phone}",
        phone=phone,
        password_hash="hashed",
        role_id=roles["Rahbar"].id,
        region_id=region_id,
        organization_id=organization_id,
    )
    session.add(user)
    session.flush()
    return user


def _make_result(
    session: Session,
    *,
    user_id: int,
    test_id: int,
    percentage: Decimal,
    competency_rows: list[tuple[int, Decimal]] | None = None,
    created_at: datetime | None = None,
) -> TestResult:
    """Yakunlangan sessiya + natija + kompetensiya natijalarini yaratadi."""
    now = datetime.now(timezone.utc)
    ts = TestSession(
        user_id=user_id,
        test_id=test_id,
        status="completed",
        started_at=now,
        expires_at=now + timedelta(minutes=30),
        completed_at=now,
    )
    session.add(ts)
    session.flush()
    result = TestResult(
        user_id=user_id,
        test_id=test_id,
        session_id=ts.id,
        total_score=Decimal("10.00"),
        max_score=Decimal("20.00"),
        percentage=percentage,
        level="O'rta",
    )
    if created_at is not None:
        result.created_at = created_at
    for competency_id, pct in competency_rows or []:
        result.competency_results.append(
            CompetencyResult(
                competency_id=competency_id,
                score=Decimal("5.00"),
                max_score=Decimal("10.00"),
                percentage=pct,
            )
        )
    session.add(result)
    session.flush()
    return result


# ---------------------------------------------------------------------------
# admin_report (R15.1, R15.2, R15.7)
# ---------------------------------------------------------------------------


def test_admin_report_counts_and_average(
    session: Session,
    roles: dict[str, Role],
    test_obj: Test,
    competencies: list[Competency],
) -> None:
    """Rahbarlar soni, test topshirganlar soni va o'rtacha ball (R15.1)."""
    c1, c2 = competencies
    leader1 = _make_leader(session, roles, phone="+998900000001")
    leader2 = _make_leader(session, roles, phone="+998900000002")
    # leader3 — test topshirmagan rahbar (rahbarlar soniga kiradi, takerga emas).
    _make_leader(session, roles, phone="+998900000003")
    # Ekspert ham bor — rahbar emas, hisobga olinmasligi kerak.
    session.add(
        User(
            full_name="Ekspert",
            phone="+998900000009",
            password_hash="hashed",
            role_id=roles["Ekspert"].id,
        )
    )
    session.flush()

    _make_result(
        session,
        user_id=leader1.id,
        test_id=test_obj.id,
        percentage=Decimal("40.00"),
        competency_rows=[(c1.id, Decimal("40.00")), (c2.id, Decimal("80.00"))],
    )
    _make_result(
        session,
        user_id=leader2.id,
        test_id=test_obj.id,
        percentage=Decimal("60.00"),
        competency_rows=[(c1.id, Decimal("20.00")), (c2.id, Decimal("60.00"))],
    )
    session.commit()

    report = ReportService(session).admin_report()
    assert isinstance(report, AdminReport)
    assert report.leaders_count == 3
    assert report.test_takers_count == 2
    # (40 + 60) / 2 = 50.00
    assert report.average_score == Decimal("50.00")


def test_admin_report_lowest_and_highest_competencies(
    session: Session,
    roles: dict[str, Role],
    test_obj: Test,
    competencies: list[Competency],
) -> None:
    """Eng past/yuqori jamlangan kompetensiyalar nom bilan qaytadi (R15.2)."""
    c1, c2 = competencies
    leader1 = _make_leader(session, roles, phone="+998900000001")
    leader2 = _make_leader(session, roles, phone="+998900000002")
    # c1 o'rtacha: (40 + 20) / 2 = 30; c2 o'rtacha: (80 + 60) / 2 = 70.
    _make_result(
        session,
        user_id=leader1.id,
        test_id=test_obj.id,
        percentage=Decimal("60.00"),
        competency_rows=[(c1.id, Decimal("40.00")), (c2.id, Decimal("80.00"))],
    )
    _make_result(
        session,
        user_id=leader2.id,
        test_id=test_obj.id,
        percentage=Decimal("40.00"),
        competency_rows=[(c1.id, Decimal("20.00")), (c2.id, Decimal("60.00"))],
    )
    session.commit()

    report = ReportService(session).admin_report()
    assert [e.competency_id for e in report.lowest_competencies] == [c1.id]
    assert report.lowest_competencies[0].competency_name == "Boshqaruv"
    assert report.lowest_competencies[0].aggregate_percentage == Decimal("30.00")
    assert [e.competency_id for e in report.highest_competencies] == [c2.id]
    assert report.highest_competencies[0].aggregate_percentage == Decimal("70.00")


def test_admin_report_tie_returns_all(
    session: Session,
    roles: dict[str, Role],
    test_obj: Test,
    competencies: list[Competency],
) -> None:
    """Teng jamlangan foizda barcha kompetensiyalar past ham, yuqori ham (R15.2)."""
    c1, c2 = competencies
    leader = _make_leader(session, roles, phone="+998900000001")
    _make_result(
        session,
        user_id=leader.id,
        test_id=test_obj.id,
        percentage=Decimal("50.00"),
        competency_rows=[(c1.id, Decimal("50.00")), (c2.id, Decimal("50.00"))],
    )
    session.commit()

    report = ReportService(session).admin_report()
    assert {e.competency_id for e in report.lowest_competencies} == {c1.id, c2.id}
    assert {e.competency_id for e in report.highest_competencies} == {c1.id, c2.id}


def test_admin_report_empty_is_zero_state(
    session: Session, roles: dict[str, Role]
) -> None:
    """Natija yo'q bo'lsa nol qiymatli/bo'sh muvaffaqiyatli holat (R15.7)."""
    _make_leader(session, roles, phone="+998900000001")
    session.commit()

    report = ReportService(session).admin_report()
    assert report.leaders_count == 1
    assert report.test_takers_count == 0
    assert report.average_score == Decimal("0.00")
    assert report.lowest_competencies == ()
    assert report.highest_competencies == ()


# ---------------------------------------------------------------------------
# report_by_region / report_by_organization (R15.3, R15.4)
# ---------------------------------------------------------------------------


def test_report_by_region_aggregates_per_section(
    session: Session, roles: dict[str, Role], test_obj: Test
) -> None:
    """Hudud kesimida rahbarlar/topshirganlar soni va o'rtacha ball (R15.3)."""
    r1 = Region(name="Toshkent")
    r2 = Region(name="Samarqand")
    session.add_all([r1, r2])
    session.flush()

    # r1: 2 rahbar, ikkalasi ham topshirgan (40, 60 -> o'rtacha 50).
    l1 = _make_leader(session, roles, phone="+998900000001", region_id=r1.id)
    l2 = _make_leader(session, roles, phone="+998900000002", region_id=r1.id)
    # r2: 1 rahbar, topshirmagan.
    _make_leader(session, roles, phone="+998900000003", region_id=r2.id)

    _make_result(
        session, user_id=l1.id, test_id=test_obj.id, percentage=Decimal("40.00")
    )
    _make_result(
        session, user_id=l2.id, test_id=test_obj.id, percentage=Decimal("60.00")
    )
    session.commit()

    report = ReportService(session).report_by_region()
    assert isinstance(report, SectionReport)
    by_id = {row.section_id: row for row in report.rows}

    assert by_id[r1.id].section_name == "Toshkent"
    assert by_id[r1.id].leaders_count == 2
    assert by_id[r1.id].test_takers_count == 2
    assert by_id[r1.id].average_score == Decimal("50.00")

    assert by_id[r2.id].leaders_count == 1
    assert by_id[r2.id].test_takers_count == 0
    assert by_id[r2.id].average_score == Decimal("0.00")


def test_report_by_region_uses_latest_result_per_leader(
    session: Session, roles: dict[str, Role], test_obj: Test
) -> None:
    """Kesim o'rtachasi rahbar boshiga — eng so'nggi natija ishlatiladi (R15.3)."""
    r1 = Region(name="Toshkent")
    session.add(r1)
    session.flush()
    leader = _make_leader(session, roles, phone="+998900000001", region_id=r1.id)

    old = datetime(2023, 1, 1, tzinfo=timezone.utc)
    new = datetime(2024, 1, 1, tzinfo=timezone.utc)
    _make_result(
        session,
        user_id=leader.id,
        test_id=test_obj.id,
        percentage=Decimal("20.00"),
        created_at=old,
    )
    _make_result(
        session,
        user_id=leader.id,
        test_id=test_obj.id,
        percentage=Decimal("80.00"),
        created_at=new,
    )
    session.commit()

    report = ReportService(session).report_by_region()
    by_id = {row.section_id: row for row in report.rows}
    # Bitta rahbar: leaders=1, takers=1, o'rtacha = eng so'nggi (80.00).
    assert by_id[r1.id].leaders_count == 1
    assert by_id[r1.id].test_takers_count == 1
    assert by_id[r1.id].average_score == Decimal("80.00")


def test_report_by_organization_aggregates_per_section(
    session: Session, roles: dict[str, Role], test_obj: Test
) -> None:
    """Tashkilot kesimida jamlanma (R15.4)."""
    o1 = Organization(name="MTT-1")
    o2 = Organization(name="MTT-2")
    session.add_all([o1, o2])
    session.flush()

    l1 = _make_leader(
        session, roles, phone="+998900000001", organization_id=o1.id
    )
    l2 = _make_leader(
        session, roles, phone="+998900000002", organization_id=o2.id
    )
    _make_result(
        session, user_id=l1.id, test_id=test_obj.id, percentage=Decimal("70.00")
    )
    _make_result(
        session, user_id=l2.id, test_id=test_obj.id, percentage=Decimal("30.00")
    )
    session.commit()

    report = ReportService(session).report_by_organization()
    by_id = {row.section_id: row for row in report.rows}
    assert by_id[o1.id].section_name == "MTT-1"
    assert by_id[o1.id].average_score == Decimal("70.00")
    assert by_id[o2.id].average_score == Decimal("30.00")


def test_report_by_region_empty_is_empty_rows(
    session: Session, roles: dict[str, Role]
) -> None:
    """Hech qanday rahbar bo'lmasa bo'sh rows (R15.7)."""
    report = ReportService(session).report_by_region()
    assert report.rows == ()


# ---------------------------------------------------------------------------
# individual_dynamics (R15.5, R15.7)
# ---------------------------------------------------------------------------


def test_individual_dynamics_chronological(
    session: Session, roles: dict[str, Role], test_obj: Test
) -> None:
    """Rahbar natijalari xronologik (eng eskidan eng yangiga) qaytadi (R15.5)."""
    leader = _make_leader(session, roles, phone="+998900000001")
    t1 = datetime(2023, 1, 1, tzinfo=timezone.utc)
    t2 = datetime(2023, 6, 1, tzinfo=timezone.utc)
    t3 = datetime(2024, 1, 1, tzinfo=timezone.utc)
    # Tartibsiz kiritamiz; chiqishda saralangan bo'lishi kerak.
    _make_result(
        session,
        user_id=leader.id,
        test_id=test_obj.id,
        percentage=Decimal("60.00"),
        created_at=t2,
    )
    _make_result(
        session,
        user_id=leader.id,
        test_id=test_obj.id,
        percentage=Decimal("40.00"),
        created_at=t1,
    )
    _make_result(
        session,
        user_id=leader.id,
        test_id=test_obj.id,
        percentage=Decimal("80.00"),
        created_at=t3,
    )
    session.commit()

    dynamics = ReportService(session).individual_dynamics(leader.id)
    assert isinstance(dynamics, IndividualDynamics)
    # SQLite tzinfo'ni saqlamaydi; sana qiymatlarini tz-agnostik solishtiramiz.
    achieved = [p.achieved_at.replace(tzinfo=None) for p in dynamics.points]
    assert achieved == [t1.replace(tzinfo=None), t2.replace(tzinfo=None), t3.replace(tzinfo=None)]
    # Foizlar tartibi xronologik dinamikani tasdiqlaydi (eng eskidan eng yangiga).
    assert [p.percentage for p in dynamics.points] == [
        Decimal("40.00"),
        Decimal("60.00"),
        Decimal("80.00"),
    ]


def test_individual_dynamics_empty_is_empty_points(
    session: Session, roles: dict[str, Role]
) -> None:
    """Natija yo'q rahbar -> bo'sh points (R15.7)."""
    leader = _make_leader(session, roles, phone="+998900000001")
    session.commit()

    dynamics = ReportService(session).individual_dynamics(leader.id)
    assert dynamics.points == ()


# ---------------------------------------------------------------------------
# Ekspert doirasi (R15.6)
# ---------------------------------------------------------------------------


def test_expert_scoping_restricts_to_assigned_organization(
    session: Session,
    roles: dict[str, Role],
    test_obj: Test,
    competencies: list[Competency],
) -> None:
    """Ekspert hisoboti faqat biriktirilgan tashkilot rahbarlarini qamraydi (R15.6)."""
    c1, _ = competencies
    org_a = Organization(name="MTT-A")
    org_b = Organization(name="MTT-B")
    session.add_all([org_a, org_b])
    session.flush()

    # Ekspert org_a ga tegishli (shared organization qoidasi).
    expert = User(
        full_name="Ekspert",
        phone="+998900000099",
        password_hash="hashed",
        role_id=roles["Ekspert"].id,
        organization_id=org_a.id,
    )
    session.add(expert)
    session.flush()

    leader_a = _make_leader(
        session, roles, phone="+998900000001", organization_id=org_a.id
    )
    leader_b = _make_leader(
        session, roles, phone="+998900000002", organization_id=org_b.id
    )
    _make_result(
        session,
        user_id=leader_a.id,
        test_id=test_obj.id,
        percentage=Decimal("40.00"),
        competency_rows=[(c1.id, Decimal("40.00"))],
    )
    _make_result(
        session,
        user_id=leader_b.id,
        test_id=test_obj.id,
        percentage=Decimal("90.00"),
        competency_rows=[(c1.id, Decimal("90.00"))],
    )
    session.commit()

    svc = ReportService(session)

    # Doirasiz (admin): ikkala rahbar ham hisobga olinadi.
    full = svc.admin_report()
    assert full.leaders_count == 2
    assert full.test_takers_count == 2
    assert full.average_score == Decimal("65.00")

    # Ekspert doirasi: faqat org_a (leader_a).
    scoped = svc.admin_report(expert_id=expert.id)
    assert scoped.leaders_count == 1
    assert scoped.test_takers_count == 1
    assert scoped.average_score == Decimal("40.00")
    assert scoped.lowest_competencies[0].aggregate_percentage == Decimal("40.00")

    # Kesim hisoboti ham faqat org_a ni qamraydi.
    section = svc.report_by_organization(expert_id=expert.id)
    assert {row.section_id for row in section.rows} == {org_a.id}
