"""NotificationService va FCM abstraksiyasi uchun unit testlar (task 14.1).

`app/services/notification_service.py` (Bildirishnoma_Xizmati) va
`app/integrations/fcm.py` (FCM yuborgich abstraksiyasi) biznes-mantig'ini
in-memory SQLite engine ustida (real `UserRepository`/`DeviceTokenRepository`
bilan, FCM yuborgich uchun fake bilan) tekshiradi.

Bog'liq talablar:
- R16.1: yangi test haqida tegishli foydalanuvchilarga push.
- R16.2: qayta diagnostika sanasida rahbarga push.
- R16.3: rivojlanish rejasi muddatida foydalanuvchiga push.
- R16.4: ekspert tavsiyasi kelganda rahbarga push.
- R16.5: push o'chirilgan foydalanuvchini o'tkazib yuborish (xato emas).
- R16.6: yaroqli qurilma tokeni yo'q foydalanuvchini o'tkazib yuborish (xato emas).

Eslatma: bu yerda **sof filtr** funksiyasi (`filter_eligible_recipients`) ham
to'g'ridan-to'g'ri (I/O'siz) tekshiriladi — u Property 41 (task 14.2) uchun asos.
"""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

import app.models  # noqa: F401  (modellarni metadata'ga ro'yxatdan o'tkazadi)
from app.core.db import create_db_engine
from app.integrations.fcm import (
    FcmMessage,
    FcmSender,
    LoggingFcmSender,
    NoopFcmSender,
)
from app.models.base import Base
from app.models.user import User
from app.repositories.devices import DeviceTokenRepository
from app.repositories.reference import RoleRepository
from app.repositories.users import UserRepository
from app.services.notification_service import (
    EligibleRecipient,
    NotificationService,
    RecipientCandidate,
    filter_eligible_recipients,
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
def role_id(session: Session) -> int:
    return RoleRepository(session).create(name="Rahbar").id


class FakeFcmSender:
    """Test uchun fake FCM yuborgich — yuborilgan xabarlarni to'playdi."""

    def __init__(self, *, fail_tokens: set[str] | None = None) -> None:
        self.sent: list[FcmMessage] = []
        self._fail_tokens = fail_tokens or set()

    def send(
        self,
        token: str,
        title: str,
        body: str,
        data: dict[str, str] | None = None,
    ) -> bool:
        if token in self._fail_tokens:
            raise RuntimeError("FCM xatosi (simulyatsiya)")
        self.sent.append(
            FcmMessage(token=token, title=title, body=body, data=dict(data or {}))
        )
        return True

    @property
    def tokens(self) -> list[str]:
        return [m.token for m in self.sent]


def _make_user(
    session: Session,
    *,
    phone: str,
    role_id: int,
    notifications_enabled: bool = True,
) -> User:
    user = User(
        full_name="Rahbar",
        phone=phone,
        password_hash="h",
        role_id=role_id,
        notifications_enabled=notifications_enabled,
    )
    session.add(user)
    session.flush()
    return user


# ---------------------------------------------------------------------------
# Sof filtr (filter_eligible_recipients) — Property 41 asosi (R16.5, R16.6)
# ---------------------------------------------------------------------------


def test_filter_keeps_only_enabled_with_valid_token() -> None:
    """Faqat push yoqilgan VA yaroqli tokenli foydalanuvchilar loyiq (R16.5, R16.6)."""
    candidates = [
        RecipientCandidate(1, notifications_enabled=True, valid_tokens=("a",)),
        RecipientCandidate(2, notifications_enabled=False, valid_tokens=("b",)),
        RecipientCandidate(3, notifications_enabled=True, valid_tokens=()),
        RecipientCandidate(4, notifications_enabled=False, valid_tokens=()),
        RecipientCandidate(5, notifications_enabled=True, valid_tokens=("c", "d")),
    ]

    eligible = filter_eligible_recipients(candidates)

    assert eligible == [
        EligibleRecipient(1, ("a",)),
        EligibleRecipient(5, ("c", "d")),
    ]


def test_filter_skipping_is_not_an_error() -> None:
    """Hammasi ineligible bo'lsa, bo'sh ro'yxat (xato emas) (R16.5, R16.6)."""
    candidates = [
        RecipientCandidate(1, notifications_enabled=False, valid_tokens=("a",)),
        RecipientCandidate(2, notifications_enabled=True, valid_tokens=()),
    ]
    assert filter_eligible_recipients(candidates) == []


def test_filter_preserves_input_order() -> None:
    """Filtr kirish tartibini saqlaydi (deterministik)."""
    candidates = [
        RecipientCandidate(3, notifications_enabled=True, valid_tokens=("x",)),
        RecipientCandidate(1, notifications_enabled=True, valid_tokens=("y",)),
        RecipientCandidate(2, notifications_enabled=True, valid_tokens=("z",)),
    ]
    assert [r.user_id for r in filter_eligible_recipients(candidates)] == [3, 1, 2]


# ---------------------------------------------------------------------------
# FCM abstraksiyasi implementatsiyalari
# ---------------------------------------------------------------------------


def test_noop_sender_records_and_returns_true() -> None:
    """NoopFcmSender hech narsa yubormaydi, ammo qayd etadi va True qaytaradi."""
    sender = NoopFcmSender()
    assert isinstance(sender, FcmSender)  # Protocol muvofiqligi (runtime_checkable)
    assert sender.send("tok", "Sarlavha", "Matn", {"type": "x"}) is True
    assert sender.sent == [
        FcmMessage(token="tok", title="Sarlavha", body="Matn", data={"type": "x"})
    ]


def test_logging_sender_masks_token_and_returns_true(caplog) -> None:
    """LoggingFcmSender token qiymatini to'liq jurnalga yozmaydi (R17.5)."""
    sender = LoggingFcmSender()
    assert isinstance(sender, FcmSender)
    with caplog.at_level("INFO"):
        assert sender.send("supersecret-token-1234", "T", "B") is True
    logged = "\n".join(r.getMessage() for r in caplog.records)
    assert "supersecret-token-1234" not in logged
    assert "1234" in logged  # faqat oxirgi 4 belgi


# ---------------------------------------------------------------------------
# NotificationService — dispatch (R16.1–R16.4) + filtrlash (R16.5, R16.6)
# ---------------------------------------------------------------------------


def test_notify_new_test_sends_only_to_eligible(session: Session, role_id: int) -> None:
    """Yangi test: faqat loyiq foydalanuvchilarga yuboriladi (R16.1, R16.5, R16.6)."""
    devices = DeviceTokenRepository(session)

    eligible = _make_user(session, phone="+998900000001", role_id=role_id)
    disabled = _make_user(
        session, phone="+998900000002", role_id=role_id, notifications_enabled=False
    )
    no_token = _make_user(session, phone="+998900000003", role_id=role_id)
    session.flush()

    devices.register(user_id=eligible.id, token="ok-1", platform="android")
    devices.register(user_id=disabled.id, token="skip-disabled", platform="android")
    # no_token uchun token yo'q.
    session.commit()

    sender = FakeFcmSender()
    service = NotificationService(session, sender)

    sent = service.notify_new_test(
        test=None, recipient_user_ids=[eligible.id, disabled.id, no_token.id]
    )

    assert sent == 1
    assert sender.tokens == ["ok-1"]
    assert sender.sent[0].data["type"] == "new_test"


def test_notify_new_test_sends_to_all_valid_tokens(session: Session, role_id: int) -> None:
    """Bir foydalanuvchining bir nechta yaroqli tokeniga ham yuboriladi (R16.1)."""
    devices = DeviceTokenRepository(session)
    user = _make_user(session, phone="+998900000010", role_id=role_id)
    session.flush()
    devices.register(user_id=user.id, token="t1", platform="android")
    devices.register(user_id=user.id, token="t2", platform="ios")
    invalid = devices.register(user_id=user.id, token="t3", platform="android")
    session.commit()
    devices.invalidate("t3")
    session.commit()
    assert invalid.is_valid is False

    sender = FakeFcmSender()
    service = NotificationService(session, sender)

    sent = service.notify_new_test(test=None, recipient_user_ids=[user.id])

    assert sent == 2
    assert set(sender.tokens) == {"t1", "t2"}


def test_notify_skips_unknown_users_without_error(session: Session, role_id: int) -> None:
    """Mavjud bo'lmagan foydalanuvchi o'tkazib yuboriladi (xato emas)."""
    sender = FakeFcmSender()
    service = NotificationService(session, sender)
    # Hech qanday foydalanuvchi yaratilmagan.
    sent = service.notify_new_test(test=None, recipient_user_ids=[999, 1000])
    assert sent == 0
    assert sender.sent == []


def test_one_send_failure_does_not_stop_others(session: Session, role_id: int) -> None:
    """Bitta token yuborilmasa ham boshqalarga yuborish davom etadi (R16.1)."""
    devices = DeviceTokenRepository(session)
    u1 = _make_user(session, phone="+998900000020", role_id=role_id)
    u2 = _make_user(session, phone="+998900000021", role_id=role_id)
    session.flush()
    devices.register(user_id=u1.id, token="boom", platform="android")
    devices.register(user_id=u2.id, token="good", platform="android")
    session.commit()

    sender = FakeFcmSender(fail_tokens={"boom"})
    service = NotificationService(session, sender)

    sent = service.notify_new_test(test=None, recipient_user_ids=[u1.id, u2.id])

    # "boom" xato berdi, ammo "good" yuborildi.
    assert sent == 1
    assert sender.tokens == ["good"]


def test_notify_retake_sends_to_user_object(session: Session, role_id: int) -> None:
    """Qayta diagnostika: rahbarga (User obyekti) yuboriladi (R16.2)."""
    devices = DeviceTokenRepository(session)
    user = _make_user(session, phone="+998900000030", role_id=role_id)
    session.flush()
    devices.register(user_id=user.id, token="retake-tok", platform="android")
    session.commit()

    sender = FakeFcmSender()
    service = NotificationService(session, sender)

    sent = service.notify_retake(user)

    assert sent == 1
    assert sender.sent[0].data["type"] == "retake"
    assert sender.tokens == ["retake-tok"]


def test_notify_retake_skips_when_disabled(session: Session, role_id: int) -> None:
    """Push o'chirilgan rahbarga qayta diagnostika yuborilmaydi (R16.5)."""
    devices = DeviceTokenRepository(session)
    user = _make_user(
        session, phone="+998900000031", role_id=role_id, notifications_enabled=False
    )
    session.flush()
    devices.register(user_id=user.id, token="x", platform="android")
    session.commit()

    sender = FakeFcmSender()
    service = NotificationService(session, sender)
    assert service.notify_retake(user) == 0
    assert sender.sent == []


def test_notify_dev_plan_deadline_resolves_user_id(session: Session, role_id: int) -> None:
    """Rivojlanish rejasi muddati: plan.user_id orqali yuboriladi (R16.3)."""
    devices = DeviceTokenRepository(session)
    user = _make_user(session, phone="+998900000040", role_id=role_id)
    session.flush()
    devices.register(user_id=user.id, token="plan-tok", platform="android")
    session.commit()

    class DevPlan:
        def __init__(self, user_id: int) -> None:
            self.user_id = user_id

    sender = FakeFcmSender()
    service = NotificationService(session, sender)

    sent = service.notify_dev_plan_deadline(DevPlan(user.id))

    assert sent == 1
    assert sender.sent[0].data["type"] == "dev_plan_deadline"


def test_notify_expert_review_sends_to_leader(session: Session, role_id: int) -> None:
    """Ekspert tavsiyasi: rahbarga (id orqali) yuboriladi (R16.4)."""
    devices = DeviceTokenRepository(session)
    leader = _make_user(session, phone="+998900000050", role_id=role_id)
    session.flush()
    devices.register(user_id=leader.id, token="exp-tok", platform="android")
    session.commit()

    sender = FakeFcmSender()
    service = NotificationService(session, sender)

    sent = service.notify_expert_review(leader.id)

    assert sent == 1
    assert sender.sent[0].data["type"] == "expert_review"


def test_service_defaults_to_noop_sender(session: Session, role_id: int) -> None:
    """Yuborgich berilmasa NoopFcmSender ishlatiladi (xavfsiz standart)."""
    devices = DeviceTokenRepository(session)
    user = _make_user(session, phone="+998900000060", role_id=role_id)
    session.flush()
    devices.register(user_id=user.id, token="noop-tok", platform="android")
    session.commit()

    service = NotificationService(session)
    assert isinstance(service.sender, NoopFcmSender)
    sent = service.notify_retake(user)
    assert sent == 1
    assert service.sender.sent[0].token == "noop-tok"


def test_service_accepts_injected_repositories(session: Session, role_id: int) -> None:
    """Servis tayyor repositorylar bilan ham quriladi (framework-agnostik)."""
    users = UserRepository(session)
    devices = DeviceTokenRepository(session)
    user = _make_user(session, phone="+998900000070", role_id=role_id)
    session.flush()
    devices.register(user_id=user.id, token="inj-tok", platform="android")
    session.commit()

    sender = FakeFcmSender()
    service = NotificationService(sender=sender, users=users, devices=devices)
    assert service.notify_retake(user) == 1


def test_service_requires_session_or_repositories() -> None:
    """Sessiya ham, repositorylar ham berilmasa xato (konfiguratsiya xatosi)."""
    with pytest.raises(ValueError):
        NotificationService()
