"""Repository qatlami uchun integratsion unit testlari (task 2.3).

Bu testlar yangi repository klasslarining (sessions, results, portfolio, expert,
recommendations, tokens, devices, reference) CRUD round-trip ishlashini in-memory
SQLite engine ustida tekshiradi (`Base.metadata.create_all`). I/O'siz, tez va
real funksiyani (mock'siz) tekshiradi.

Repository konvensiyasi: `add()`/`create()` `flush` qiladi, `commit` qilmaydi —
shu sababli testlar har bir blok oxirida `session.commit()` ni o'zi bajaradi
(tranzaksiya chegarasi chaqiruvchida).

Bog'liq talablar: 8.6 (natija saqlash), 11.1 (portfolio ro'yxati), 12.1 (reyting
uchun natijalar), 15.5 (xronologik dinamika), R2/R3 (tokenlar), R16 (qurilma
tokenlari), R13 (ekspert).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

import app.models  # noqa: F401  (modellarni metadata'ga ro'yxatdan o'tkazadi)
from app.core.db import create_db_engine
from app.models.base import Base
from app.repositories import (
    CompetencyRepository,
    DeviceTokenRepository,
    ExpertReviewRepository,
    OrganizationRepository,
    PortfolioRepository,
    RecommendationRepository,
    RegionRepository,
    ResultRepository,
    RoleRepository,
    SessionRepository,
    TokenRepository,
)
from app.models.content import Test
from app.models.recommendation import Recommendation
from app.models.user import User


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
    """Test uchun bitta sessiya (tranzaksiya chegarasi test ichida)."""
    with Session(engine) as sess:
        yield sess


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _make_role(session: Session, name: str = "Rahbar"):
    return RoleRepository(session).create(name=name)


def _make_user(
    session: Session,
    *,
    phone: str,
    role_id: int,
    organization_id: int | None = None,
):
    user = User(
        full_name="Test User",
        phone=phone,
        password_hash="h",
        role_id=role_id,
        organization_id=organization_id,
    )
    session.add(user)
    session.flush()
    return user


def _make_test(session: Session, *, title: str = "Test") -> Test:
    test = Test(title=title, category="kognitiv", duration_minutes=30)
    session.add(test)
    session.flush()
    return test


# ---------------------------------------------------------------------------
# Reference repositorylar
# ---------------------------------------------------------------------------


def test_role_repository_get_by_name_round_trip(session: Session) -> None:
    """Rol yaratiladi va nom bo'yicha topiladi (R1.7)."""
    repo = RoleRepository(session)
    created = repo.create(name="Administrator")
    session.commit()

    assert repo.get_by_name("Administrator").id == created.id
    assert repo.get_by_id(created.id).name == "Administrator"
    assert repo.get_by_name("Nomavjud") is None


def test_region_and_organization_repositories(session: Session) -> None:
    """Hudud va tashkilot yaratiladi; tashkilot hudud bo'yicha topiladi (R15.4)."""
    region = RegionRepository(session).create(name="Toshkent")
    org_repo = OrganizationRepository(session)
    org = org_repo.create(name="MTT-1", region_id=region.id, org_type="davlat")
    session.commit()

    assert org_repo.get_by_id(org.id).name == "MTT-1"
    assert org_repo.get_by_name("MTT-1").id == org.id
    listed = org_repo.list_for_region(region.id)
    assert [o.id for o in listed] == [org.id]


def test_competency_repository_round_trip(session: Session) -> None:
    """Kompetensiya yaratiladi va ID/nom bo'yicha topiladi (R14.1)."""
    repo = CompetencyRepository(session)
    comp = repo.create(name="Boshqaruv", description="desc")
    session.commit()

    assert repo.get_by_id(comp.id).name == "Boshqaruv"
    assert repo.get_by_name("Boshqaruv").id == comp.id


# ---------------------------------------------------------------------------
# SessionRepository
# ---------------------------------------------------------------------------


def test_session_repository_create_and_get_active(session: Session) -> None:
    """Sessiya yaratiladi; faqat in_progress sessiya `get_active` da topiladi (R7.1, R7.10)."""
    role = _make_role(session)
    user = _make_user(session, phone="+998900000001", role_id=role.id)
    test = _make_test(session)
    repo = SessionRepository(session)

    started = _now()
    sess = repo.create(
        user_id=user.id,
        test_id=test.id,
        started_at=started,
        expires_at=started + timedelta(minutes=30),
    )
    session.commit()

    active = repo.get_active(user.id, test.id)
    assert active is not None and active.id == sess.id
    assert repo.get_by_id(sess.id).status == "in_progress"


def test_session_complete_clears_active(session: Session) -> None:
    """Sessiya yakunlangach `get_active` uni qaytarmaydi (R7.5, R7.6)."""
    role = _make_role(session)
    user = _make_user(session, phone="+998900000002", role_id=role.id)
    test = _make_test(session)
    repo = SessionRepository(session)

    sess = repo.create(user_id=user.id, test_id=test.id, started_at=_now())
    session.commit()

    repo.complete(sess, completed_at=_now())
    session.commit()

    assert sess.status == "completed"
    assert repo.get_active(user.id, test.id) is None


def test_session_upsert_answer_is_idempotent(session: Session) -> None:
    """Bir savol uchun javob upsert qilinadi — takror saqlashda yangilanadi (R7.5)."""
    role = _make_role(session)
    user = _make_user(session, phone="+998900000003", role_id=role.id)
    test = _make_test(session)
    repo = SessionRepository(session)
    sess = repo.create(user_id=user.id, test_id=test.id, started_at=_now())
    session.flush()

    # Question yaratish (FK uchun).
    from app.models.content import Question

    q = Question(
        test_id=test.id, question_text="Savol?", score=Decimal("1.00")
    )
    session.add(q)
    session.flush()

    first = repo.upsert_answer(
        session_id=sess.id, question_id=q.id, likert_value=3, answered=True
    )
    second = repo.upsert_answer(
        session_id=sess.id, question_id=q.id, likert_value=5, answered=True
    )
    session.commit()

    answers = repo.list_answers(sess.id)
    assert len(answers) == 1
    assert first.id == second.id
    assert answers[0].likert_value == 5


def test_session_add_answers_bulk(session: Session) -> None:
    """Bir nechta javob bir vaqtda qo'shiladi (R7.5)."""
    from app.models.content import Question
    from app.models.session import SessionAnswer

    role = _make_role(session)
    user = _make_user(session, phone="+998900000004", role_id=role.id)
    test = _make_test(session)
    repo = SessionRepository(session)
    sess = repo.create(user_id=user.id, test_id=test.id, started_at=_now())
    q1 = Question(test_id=test.id, question_text="Q1", score=Decimal("1.00"))
    q2 = Question(test_id=test.id, question_text="Q2", score=Decimal("1.00"))
    session.add_all([q1, q2])
    session.flush()

    repo.add_answers(
        [
            SessionAnswer(session_id=sess.id, question_id=q1.id, answered=True),
            SessionAnswer(session_id=sess.id, question_id=q2.id, answered=False),
        ]
    )
    session.commit()

    assert len(repo.list_answers(sess.id)) == 2


# ---------------------------------------------------------------------------
# ResultRepository
# ---------------------------------------------------------------------------


def _make_completed_session(session: Session, user_id: int, test_id: int):
    repo = SessionRepository(session)
    sess = repo.create(user_id=user_id, test_id=test_id, started_at=_now())
    repo.complete(sess, completed_at=_now())
    return sess


def test_result_create_with_competencies_round_trip(session: Session) -> None:
    """Natija kompetensiya natijalari bilan saqlanadi va o'qiladi (R8.6, R8.3)."""
    role = _make_role(session)
    user = _make_user(session, phone="+998900000010", role_id=role.id)
    test = _make_test(session)
    comp = CompetencyRepository(session).create(name="Innovatsiya")
    sess = _make_completed_session(session, user.id, test.id)
    session.flush()

    repo = ResultRepository(session)
    result = repo.create_with_competencies(
        user_id=user.id,
        test_id=test.id,
        session_id=sess.id,
        total_score=Decimal("8.00"),
        max_score=Decimal("10.00"),
        percentage=Decimal("80.00"),
        level="Yuqori",
        competency_rows=[
            {
                "competency_id": comp.id,
                "score": Decimal("8.00"),
                "max_score": Decimal("10.00"),
                "percentage": Decimal("80.00"),
            }
        ],
    )
    session.commit()

    loaded = repo.get_by_id(result.id)
    assert loaded.percentage == Decimal("80.00")
    assert len(loaded.competency_results) == 1
    assert loaded.competency_results[0].competency_id == comp.id
    assert repo.get_by_session(sess.id).id == result.id
    assert len(repo.list_competency_results(result.id)) == 1


def test_result_list_for_user_is_chronological(session: Session) -> None:
    """Natijalar xronologik (created_at, id) tartibda qaytadi (R9.1, R15.5)."""
    role = _make_role(session)
    user = _make_user(session, phone="+998900000011", role_id=role.id)
    test = _make_test(session)
    repo = ResultRepository(session)

    ids = []
    base = datetime(2024, 1, 1, tzinfo=timezone.utc)
    for i in range(3):
        sess = _make_completed_session(session, user.id, test.id)
        session.flush()
        res = repo.create_with_competencies(
            user_id=user.id,
            test_id=test.id,
            session_id=sess.id,
            total_score=Decimal("5.00"),
            max_score=Decimal("10.00"),
            percentage=Decimal("50.00"),
            level="O'rta",
        )
        # created_at ni aniq tartibda belgilash (SQLite server_default bir xil
        # bo'lishi mumkin — deterministik tekshiruv uchun).
        res.created_at = base + timedelta(days=i)
        session.flush()
        ids.append(res.id)
    session.commit()

    listed = repo.list_for_user(user.id)
    assert [r.id for r in listed] == ids
    latest = repo.latest_for_user(user.id)
    assert latest.id == ids[-1]


def test_result_get_for_user_enforces_ownership(session: Session) -> None:
    """Boshqa foydalanuvchi natijasi `get_for_user` da `None` qaytadi (R10.6, R4.1)."""
    role = _make_role(session)
    owner = _make_user(session, phone="+998900000012", role_id=role.id)
    other = _make_user(session, phone="+998900000013", role_id=role.id)
    test = _make_test(session)
    sess = _make_completed_session(session, owner.id, test.id)
    session.flush()

    repo = ResultRepository(session)
    result = repo.create_with_competencies(
        user_id=owner.id,
        test_id=test.id,
        session_id=sess.id,
        total_score=Decimal("9.00"),
        max_score=Decimal("10.00"),
        percentage=Decimal("90.00"),
        level="Yuqori",
    )
    session.commit()

    assert repo.get_for_user(owner.id, result.id).id == result.id
    assert repo.get_for_user(other.id, result.id) is None


def test_result_list_all_with_user(session: Session) -> None:
    """Barcha natijalar foydalanuvchi bilan yuklanadi (R12.1, R15.3)."""
    role = _make_role(session)
    region = RegionRepository(session).create(name="Region")
    org = OrganizationRepository(session).create(name="Org", region_id=region.id)
    user = _make_user(
        session, phone="+998900000014", role_id=role.id, organization_id=org.id
    )
    test = _make_test(session)
    sess = _make_completed_session(session, user.id, test.id)
    session.flush()

    repo = ResultRepository(session)
    repo.create_with_competencies(
        user_id=user.id,
        test_id=test.id,
        session_id=sess.id,
        total_score=Decimal("7.00"),
        max_score=Decimal("10.00"),
        percentage=Decimal("70.00"),
        level="Yaxshi",
    )
    session.commit()

    rows = repo.list_all_with_user()
    assert len(rows) == 1
    assert rows[0].user.organization_id == org.id


# ---------------------------------------------------------------------------
# PortfolioRepository
# ---------------------------------------------------------------------------


def test_portfolio_create_list_desc_and_delete(session: Session) -> None:
    """Portfolio yaratiladi, sana bo'yicha kamayuvchi tartibda ro'yxat, o'chiriladi (R11.1, R11.5)."""
    role = _make_role(session)
    user = _make_user(session, phone="+998900000020", role_id=role.id)
    repo = PortfolioRepository(session)

    base = datetime(2024, 5, 1, tzinfo=timezone.utc)
    created_ids = []
    for i in range(3):
        p = repo.create(
            user_id=user.id,
            title=f"Sertifikat {i}",
            storage_key=f"key-{i}",
            file_url=f"http://x/key-{i}",
            file_type="pdf",
            size_bytes=1024,
        )
        p.created_at = base + timedelta(days=i)
        session.flush()
        created_ids.append(p.id)
    session.commit()

    listed = repo.list_for_user(user.id)
    # Eng yangi birinchi (kamayuvchi).
    assert [p.id for p in listed] == list(reversed(created_ids))
    assert listed[0].file.storage_key == "key-2"

    # O'chirish: portfolio + fayl qatori olib tashlanadi.
    target = repo.get_for_user(user.id, created_ids[0])
    assert target is not None
    file_id = target.file_id
    repo.delete(target)
    session.commit()

    from app.models.portfolio import File

    assert repo.get_by_id(created_ids[0]) is None
    assert session.get(File, file_id) is None


def test_portfolio_get_for_user_ownership(session: Session) -> None:
    """Begona portfolio `get_for_user` da `None` qaytadi (R11.6)."""
    role = _make_role(session)
    owner = _make_user(session, phone="+998900000021", role_id=role.id)
    other = _make_user(session, phone="+998900000022", role_id=role.id)
    repo = PortfolioRepository(session)
    p = repo.create(user_id=owner.id, title="T", storage_key="k")
    session.commit()

    assert repo.get_for_user(owner.id, p.id).id == p.id
    assert repo.get_for_user(other.id, p.id) is None


def test_portfolio_empty_list(session: Session) -> None:
    """Yozuv bo'lmasa bo'sh ro'yxat (R11.1)."""
    role = _make_role(session)
    user = _make_user(session, phone="+998900000023", role_id=role.id)
    session.commit()
    assert PortfolioRepository(session).list_for_user(user.id) == []


# ---------------------------------------------------------------------------
# ExpertReviewRepository
# ---------------------------------------------------------------------------


def test_expert_review_create_and_assignment_by_org(session: Session) -> None:
    """Ekspert sharhi yaratiladi; biriktirilganlik tashkilot bo'yicha aniqlanadi (R13.1, R4.2)."""
    expert_role = _make_role(session, name="Ekspert")
    leader_role = _make_role(session, name="Rahbar")
    org = OrganizationRepository(session).create(name="MTT-X")
    other_org = OrganizationRepository(session).create(name="MTT-Y")

    expert = _make_user(
        session, phone="+998900000030", role_id=expert_role.id, organization_id=org.id
    )
    leader_same = _make_user(
        session, phone="+998900000031", role_id=leader_role.id, organization_id=org.id
    )
    leader_other = _make_user(
        session,
        phone="+998900000032",
        role_id=leader_role.id,
        organization_id=other_org.id,
    )
    session.flush()

    repo = ExpertReviewRepository(session)
    review = repo.create(
        expert_id=expert.id,
        leader_id=leader_same.id,
        management_culture=5,
        teamwork=4,
        pedagogical_process=4,
        innovation=3,
        documentation=5,
        strategic_planning=4,
        average_score=Decimal("4.17"),
    )
    session.commit()

    assert repo.get_by_id(review.id).average_score == Decimal("4.17")
    assert [r.id for r in repo.list_for_leader(leader_same.id)] == [review.id]
    assert [r.id for r in repo.list_by_expert(expert.id)] == [review.id]

    # Biriktirilganlik: bir xil tashkilot -> True, boshqa tashkilot -> False.
    assert repo.is_expert_assigned(expert.id, leader_same.id) is True
    assert repo.is_expert_assigned(expert.id, leader_other.id) is False


def test_expert_assignment_false_when_org_missing(session: Session) -> None:
    """Tashkilot biriktirilmagan (NULL) bo'lsa biriktirilganlik yo'q (R13.5)."""
    expert_role = _make_role(session, name="Ekspert")
    leader_role = _make_role(session, name="Rahbar")
    expert = _make_user(session, phone="+998900000033", role_id=expert_role.id)
    leader = _make_user(session, phone="+998900000034", role_id=leader_role.id)
    session.commit()

    repo = ExpertReviewRepository(session)
    assert repo.is_expert_assigned(expert.id, leader.id) is False
    assert repo.is_expert_assigned(9999, leader.id) is False


# ---------------------------------------------------------------------------
# RecommendationRepository
# ---------------------------------------------------------------------------


def test_recommendation_find_by_and_fallback(session: Session) -> None:
    """Aniq tavsiya va umumiy standart tavsiya topiladi (R10.1, R10.4)."""
    comp = CompetencyRepository(session).create(name="Strategik")
    repo = RecommendationRepository(session)
    specific = Recommendation(
        competency_id=comp.id, level="Past", text="Aniq tavsiya"
    )
    fallback = Recommendation(competency_id=None, level=None, text="Umumiy")
    fallback_leveled = Recommendation(
        competency_id=None, level="Past", text="Umumiy past"
    )
    session.add_all([specific, fallback, fallback_leveled])
    session.commit()

    assert repo.find_by(comp.id, "Past").id == specific.id
    assert repo.find_by(comp.id, "Yuqori") is None
    # Darajaga mos standart afzal.
    assert repo.get_general_fallback("Past").id == fallback_leveled.id
    # Darajasi yo'q standartga qaytish.
    assert repo.get_general_fallback("Yuqori").id == fallback.id
    assert len(repo.list_all()) == 3


def test_recommendation_attach_and_get_for_result(session: Session) -> None:
    """Tavsiya natijaga bog'lanadi va o'qiladi; so'nggi natija topiladi (R10.1, R10.2)."""
    role = _make_role(session)
    user = _make_user(session, phone="+998900000040", role_id=role.id)
    test = _make_test(session)
    comp = CompetencyRepository(session).create(name="Kommunikatsiya")
    sess = _make_completed_session(session, user.id, test.id)
    session.flush()

    result = ResultRepository(session).create_with_competencies(
        user_id=user.id,
        test_id=test.id,
        session_id=sess.id,
        total_score=Decimal("3.00"),
        max_score=Decimal("10.00"),
        percentage=Decimal("30.00"),
        level="Past",
    )
    session.flush()

    repo = RecommendationRepository(session)
    link = repo.attach_to_result(
        result_id=result.id,
        competency_id=comp.id,
        level="Past",
        text_snapshot="Rivojlantiring",
    )
    session.commit()

    links = repo.get_for_result(result.id)
    assert [l.id for l in links] == [link.id]
    assert links[0].text_snapshot == "Rivojlantiring"
    assert repo.latest_result_for_user(user.id).id == result.id


# ---------------------------------------------------------------------------
# TokenRepository
# ---------------------------------------------------------------------------


def test_token_refresh_store_get_revoke(session: Session) -> None:
    """Refresh token saqlanadi, xesh bo'yicha topiladi va bekor qilinadi (R2.3, R2.6)."""
    role = _make_role(session)
    user = _make_user(session, phone="+998900000050", role_id=role.id)
    repo = TokenRepository(session)
    exp = _now() + timedelta(days=30)

    token = repo.store_refresh(
        user_id=user.id, token_hash="hash-1", expires_at=exp
    )
    session.commit()

    found = repo.get_refresh_by_hash("hash-1")
    assert found.id == token.id and found.revoked is False
    repo.revoke_refresh(found)
    session.commit()
    assert repo.get_refresh_by_hash("hash-1").revoked is True


def test_token_revoke_all_for_user(session: Session) -> None:
    """Foydalanuvchining barcha faol refresh tokenlari bekor qilinadi (R2.4)."""
    role = _make_role(session)
    user = _make_user(session, phone="+998900000051", role_id=role.id)
    repo = TokenRepository(session)
    exp = _now() + timedelta(days=30)
    repo.store_refresh(user_id=user.id, token_hash="h1", expires_at=exp)
    repo.store_refresh(user_id=user.id, token_hash="h2", expires_at=exp)
    session.commit()

    count = repo.revoke_all_for_user(user.id)
    session.commit()
    assert count == 2
    assert repo.get_refresh_by_hash("h1").revoked is True
    assert repo.get_refresh_by_hash("h2").revoked is True


def test_token_blacklist_jti_idempotent(session: Session) -> None:
    """Access token jti blacklistga qo'shiladi; takror qo'shish idempotent (R2.4, R2.5)."""
    repo = TokenRepository(session)
    exp = _now() + timedelta(minutes=15)
    repo.blacklist_jti("jti-1", exp)
    repo.blacklist_jti("jti-1", exp)  # idempotent
    session.commit()

    assert repo.is_jti_blacklisted("jti-1") is True
    assert repo.is_jti_blacklisted("jti-yoq") is False


def test_token_reset_code_lifecycle(session: Session) -> None:
    """Reset kod yaratiladi, urinishlar oshadi, sarflanadi (R3.4, R3.6, R3.7)."""
    role = _make_role(session)
    user = _make_user(session, phone="+998900000052", role_id=role.id)
    repo = TokenRepository(session)
    exp = _now() + timedelta(minutes=15)

    code = repo.create_reset_code(
        user_id=user.id, code_hash="code-hash", expires_at=exp
    )
    session.commit()

    active = repo.get_active_reset_code(user.id)
    assert active.id == code.id
    assert repo.increment_reset_attempts(active) == 1
    assert repo.increment_reset_attempts(active) == 2
    session.commit()

    repo.consume_reset_code(active)
    session.commit()
    # Sarflangan kod endi faol emas.
    assert repo.get_active_reset_code(user.id) is None


# ---------------------------------------------------------------------------
# DeviceTokenRepository
# ---------------------------------------------------------------------------


def test_device_register_invalidate_and_list_valid(session: Session) -> None:
    """Qurilma tokeni ro'yxatga olinadi, yaroqsiz qilinadi, yaroqlilar ro'yxati (R16.5, R16.6)."""
    role = _make_role(session)
    u1 = _make_user(session, phone="+998900000060", role_id=role.id)
    u2 = _make_user(session, phone="+998900000061", role_id=role.id)
    repo = DeviceTokenRepository(session)

    repo.register(user_id=u1.id, token="tok-1", platform="android")
    repo.register(user_id=u2.id, token="tok-2", platform="ios")
    invalid = repo.register(user_id=u2.id, token="tok-3", platform="android")
    session.commit()

    repo.invalidate("tok-3")
    session.commit()
    assert invalid.is_valid is False

    valid = repo.list_valid_for_users([u1.id, u2.id])
    tokens = {d.token for d in valid}
    assert tokens == {"tok-1", "tok-2"}
    # Bo'sh ro'yxat -> bo'sh natija.
    assert repo.list_valid_for_users([]) == []


def test_device_register_is_idempotent_for_same_token(session: Session) -> None:
    """Bir xil token qayta ro'yxatga olinsa yangilanadi (yangi yozuv emas) (R16.1)."""
    role = _make_role(session)
    user = _make_user(session, phone="+998900000062", role_id=role.id)
    repo = DeviceTokenRepository(session)

    first = repo.register(user_id=user.id, token="dup", platform="android")
    # Avval yaroqsiz qilamiz, keyin qayta ro'yxat — yaroqli bo'lib qaytadi.
    repo.invalidate("dup")
    second = repo.register(user_id=user.id, token="dup", platform="ios")
    session.commit()

    assert first.id == second.id
    assert second.is_valid is True
    assert second.platform == "ios"
    assert len(repo.list_valid_for_users([user.id])) == 1
