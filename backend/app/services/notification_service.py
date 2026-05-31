"""Bildirishnoma_Xizmati — NotificationService (R16).

Push bildirishnomalarni biznes-mantiq darajasida boshqaradi. Servis
**framework'dan mustaqil**: konstruktorga SQLAlchemy ``Session`` (yoki tayyor
repositorylar) hamda FCM yuborgich abstraksiyasi (``FcmSender``) in'ektsiya
qilinadi; FastAPI/HTTP haqida hech narsa bilmaydi.

Mas'uliyat (design.md — "Push Notification Dizayni"):
- Hodisa (yangi test / qayta topshirish / reja muddati / ekspert tavsiyasi) ro'y
  berganda tegishli foydalanuvchilarni aniqlaydi (R16.1–R16.4).
- Qabul qiluvchilarni **filtrlaydi**: faqat ``notifications_enabled=true`` VA
  kamida bitta yaroqli (``is_valid=true``) qurilma tokeniga ega foydalanuvchilar
  bildirishnoma oladi; push o'chirilgan yoki yaroqli tokeni bo'lmagan
  foydalanuvchilar **o'tkazib yuboriladi** — bu xato hisoblanmaydi va boshqa
  qabul qiluvchilarga yuborishni to'xtatmaydi (R16.5, R16.6).
- Har bir yaroqli token uchun ``FcmSender.send(...)`` ni chaqiradi (R16.1–R16.4).

Filtrlash mantig'i sof (pure) funksiya sifatida ajratilgan
(``filter_eligible_recipients``) — bu I/O'siz va Property 41 (task 14.2) bilan
to'g'ridan-to'g'ri testlanadi.

Bog'liq talablar: R16.1, R16.2, R16.3, R16.4, R16.5, R16.6.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from app.integrations.fcm import FcmSender, NoopFcmSender
from app.repositories.devices import DeviceTokenRepository
from app.repositories.users import UserRepository

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Standart bildirishnoma matnlari (R16.1–R16.4)
# ---------------------------------------------------------------------------

_NEW_TEST_TITLE = "Yangi diagnostika testi"
_NEW_TEST_BODY = "Tizimga yangi test qo'shildi. Uni topshirishingiz mumkin."

_RETAKE_TITLE = "Qayta diagnostika vaqti"
_RETAKE_BODY = "Qayta diagnostika qilish sanasi yetib keldi."

_DEADLINE_TITLE = "Rivojlanish rejasi muddati"
_DEADLINE_BODY = "Rivojlanish rejangiz muddati tugashiga 3 kun qoldi."

_EXPERT_REVIEW_TITLE = "Ekspert tavsiyasi"
_EXPERT_REVIEW_BODY = "Sizga ekspert tomonidan baho va tavsiya berildi."


# ---------------------------------------------------------------------------
# Sof (pure) filtr mantig'i — Property 41 (task 14.2) shu yerni testlaydi
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RecipientCandidate:
    """Bildirishnoma uchun nomzod foydalanuvchi (transient, I/O'siz).

    Maydonlar:
    - ``user_id``: foydalanuvchi identifikatori.
    - ``notifications_enabled``: push yoqilganmi (R16.5).
    - ``valid_tokens``: foydalanuvchining **yaroqli** qurilma tokenlari
      (``is_valid=true``); bo'sh bo'lsa yaroqli token yo'q (R16.6).
    """

    user_id: int
    notifications_enabled: bool
    valid_tokens: tuple[str, ...] = ()


@dataclass(frozen=True)
class EligibleRecipient:
    """Bildirishnoma olishga loyiq foydalanuvchi (filtrdan o'tgan).

    ``tokens`` — yuborish kerak bo'lgan yaroqli tokenlar (kamida bitta).
    """

    user_id: int
    tokens: tuple[str, ...]


def filter_eligible_recipients(
    candidates: Iterable[RecipientCandidate],
) -> list[EligibleRecipient]:
    """Bildirishnoma olishga loyiq qabul qiluvchilarni qaytaradi (R16.5, R16.6).

    Qabul qiluvchi **faqat** quyidagi ikkala shart bajarilsa loyiq hisoblanadi:
    - ``notifications_enabled`` is ``True`` (push yoqilgan) — aks holda o'tkazib
      yuboriladi (R16.5);
    - kamida bitta yaroqli qurilma tokeni mavjud — aks holda o'tkazib yuboriladi
      (R16.6).

    O'tkazib yuborish **xato emas**: shunchaki natijaga kiritilmaydi. Kirish
    tartibi saqlanadi (deterministik).

    Args:
        candidates: nomzod foydalanuvchilar.

    Returns:
        Loyiq qabul qiluvchilar ro'yxati (har birida kamida bitta token).
    """
    eligible: list[EligibleRecipient] = []
    for candidate in candidates:
        if not candidate.notifications_enabled:
            # R16.5 — push o'chirilgan: o'tkazib yuborish (xato emas).
            continue
        if not candidate.valid_tokens:
            # R16.6 — yaroqli token yo'q: o'tkazib yuborish (xato emas).
            continue
        eligible.append(
            EligibleRecipient(
                user_id=candidate.user_id,
                tokens=tuple(candidate.valid_tokens),
            )
        )
    return eligible


# ---------------------------------------------------------------------------
# Servis
# ---------------------------------------------------------------------------


def _coerce_user_id(obj: Any) -> int | None:
    """Foydalanuvchi/reja/identifikatordan ``user_id`` ni ajratib oladi.

    Qabul qilinadi:
    - ``int`` — to'g'ridan-to'g'ri identifikator;
    - ``user_id`` atributiga ega obyekt (masalan, rivojlanish rejasi);
    - ``id`` atributiga ega obyekt (masalan, ``User``).

    Aniqlab bo'lmasa ``None`` qaytaradi (chaqiruvchi o'tkazib yuboradi).
    """
    if isinstance(obj, bool):  # ``bool`` — ``int`` quyi klassi; rad etamiz.
        return None
    if isinstance(obj, int):
        return obj
    for attr in ("user_id", "id"):
        value = getattr(obj, attr, None)
        if isinstance(value, int) and not isinstance(value, bool):
            return value
    return None


class NotificationService:
    """Push bildirishnoma servisi (R16).

    Args:
        session: faol SQLAlchemy ``Session`` (repositorylar bevosita berilmasa
            shu sessiyadan quriladi).
        sender: FCM yuborgich abstraksiyasi (``FcmSender``). ``None`` bo'lsa
            xavfsiz ``NoopFcmSender`` ishlatiladi (hech narsa yubormaydi).
        users: (ixtiyoriy) tayyor ``UserRepository`` — testlar uchun.
        devices: (ixtiyoriy) tayyor ``DeviceTokenRepository`` — testlar uchun.
    """

    def __init__(
        self,
        session: Session | None = None,
        sender: FcmSender | None = None,
        *,
        users: UserRepository | None = None,
        devices: DeviceTokenRepository | None = None,
    ) -> None:
        if users is None or devices is None:
            if session is None:
                raise ValueError(
                    "NotificationService uchun 'session' yoki tayyor "
                    "repositorylar ('users' va 'devices') kerak"
                )
        self.session = session
        self.users = users or UserRepository(session)  # type: ignore[arg-type]
        self.devices = devices or DeviceTokenRepository(session)  # type: ignore[arg-type]
        self.sender: FcmSender = sender or NoopFcmSender()

    # ------------------------------------------------------------------
    # Dispatch metodlari (R16.1–R16.4)
    # ------------------------------------------------------------------

    def notify_new_test(
        self, test: Any, recipient_user_ids: Sequence[int]
    ) -> int:
        """Yangi test haqida tegishli foydalanuvchilarga push yuboradi (R16.1).

        Args:
            test: yangi test (``id``/``title`` atributlari ixtiyoriy ravishda
                o'qiladi).
            recipient_user_ids: tegishli foydalanuvchi identifikatorlari.

        Returns:
            Yuborilgan xabarlar soni (token darajasida).
        """
        data = {"type": "new_test"}
        test_id = _coerce_user_id(test)
        if test_id is not None:
            data["test_id"] = str(test_id)
        title = getattr(test, "title", None) or _NEW_TEST_TITLE
        return self._dispatch(recipient_user_ids, title, _NEW_TEST_BODY, data)

    def notify_retake(self, user: Any) -> int:
        """Rahbarga qayta diagnostika haqida push yuboradi (R16.2).

        Args:
            user: rahbar (``User`` yoki identifikator).

        Returns:
            Yuborilgan xabarlar soni.
        """
        return self._dispatch_single(
            user, _RETAKE_TITLE, _RETAKE_BODY, {"type": "retake"}
        )

    def notify_dev_plan_deadline(self, plan: Any) -> int:
        """Rivojlanish rejasi muddati haqida push yuboradi (R16.3).

        Args:
            plan: rivojlanish rejasi (``user_id`` atributiga ega) yoki
                foydalanuvchi/identifikator.

        Returns:
            Yuborilgan xabarlar soni.
        """
        return self._dispatch_single(
            plan, _DEADLINE_TITLE, _DEADLINE_BODY, {"type": "dev_plan_deadline"}
        )

    def notify_expert_review(self, leader: Any) -> int:
        """Rahbarga ekspert tavsiyasi kelgani haqida push yuboradi (R16.4, R13.6).

        Args:
            leader: baholangan rahbar (``User`` yoki identifikator).

        Returns:
            Yuborilgan xabarlar soni.
        """
        return self._dispatch_single(
            leader, _EXPERT_REVIEW_TITLE, _EXPERT_REVIEW_BODY, {"type": "expert_review"}
        )

    # ------------------------------------------------------------------
    # Ichki yordamchilar
    # ------------------------------------------------------------------

    def _dispatch_single(
        self, target: Any, title: str, body: str, data: dict[str, str]
    ) -> int:
        """Bitta maqsadli foydalanuvchiga yuborish (identifikatorni aniqlaydi)."""
        user_id = _coerce_user_id(target)
        if user_id is None:
            # Identifikatorni aniqlab bo'lmadi — o'tkazib yuborish (xato emas).
            return 0
        return self._dispatch([user_id], title, body, data)

    def _resolve_recipients(
        self, user_ids: Sequence[int]
    ) -> list[EligibleRecipient]:
        """Foydalanuvchi identifikatorlaridan loyiq qabul qiluvchilarni quradi.

        Repositorylar orqali ``notifications_enabled`` va yaroqli tokenlarni
        o'qiydi, so'ng sof ``filter_eligible_recipients`` ni qo'llaydi (R16.5,
        R16.6). Noma'lum (mavjud bo'lmagan) foydalanuvchilar o'tkazib yuboriladi.
        """
        # Takroriy identifikatorlarni olib tashlash, tartibni saqlash.
        unique_ids: list[int] = list(
            dict.fromkeys(
                uid for uid in (_coerce_user_id(u) for u in user_ids) if uid is not None
            )
        )
        if not unique_ids:
            return []

        # Yaroqli tokenlarni bitta so'rovda olib, foydalanuvchi bo'yicha guruhlash.
        tokens_by_user: dict[int, list[str]] = defaultdict(list)
        for device in self.devices.list_valid_for_users(unique_ids):
            tokens_by_user[device.user_id].append(device.token)

        candidates: list[RecipientCandidate] = []
        for uid in unique_ids:
            user = self.users.get_by_id(uid)
            if user is None:
                continue  # noma'lum foydalanuvchi — o'tkazib yuborish (xato emas)
            candidates.append(
                RecipientCandidate(
                    user_id=uid,
                    notifications_enabled=bool(user.notifications_enabled),
                    valid_tokens=tuple(tokens_by_user.get(uid, ())),
                )
            )
        return filter_eligible_recipients(candidates)

    def _dispatch(
        self,
        user_ids: Sequence[int],
        title: str,
        body: str,
        data: dict[str, str] | None = None,
    ) -> int:
        """Loyiq qabul qiluvchilarning har bir tokeniga yuboradi (R16.1–R16.4).

        Ineligible foydalanuvchilar filtr orqali allaqachon chetlatilgan (R16.5,
        R16.6). Bitta yuborish xato bersa ham (tashqi xizmat nosozligi), boshqa
        qabul qiluvchilarga yuborish to'xtamaydi.

        Returns:
            Muvaffaqiyatli yuborilgan xabarlar soni.
        """
        recipients = self._resolve_recipients(user_ids)
        payload = dict(data or {})
        sent_count = 0
        for recipient in recipients:
            for token in recipient.tokens:
                try:
                    accepted = self.sender.send(token, title, body, payload)
                except Exception:  # noqa: BLE001 - tashqi xizmat nosozligi izolyatsiyasi
                    # Bitta yuborish xatosi boshqalarni to'xtatmaydi (R16.1–R16.4).
                    logger.warning(
                        "FCM yuborish muvaffaqiyatsiz (user_id=%s) — davom etiladi",
                        recipient.user_id,
                    )
                    continue
                if accepted:
                    sent_count += 1
        return sent_count


__all__ = [
    "NotificationService",
    "RecipientCandidate",
    "EligibleRecipient",
    "filter_eligible_recipients",
]
