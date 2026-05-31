"""FCM (Firebase Cloud Messaging) yuborgich abstraksiyasi (R16).

Push bildirishnomalar yon ta'sirli tashqi xizmat (FCM) orqali yuboriladi.
Bildirishnoma_Xizmati (``NotificationService``) bu modul belgilagan **interfeys**
(``FcmSender``) ustida ishlaydi va konkret implementatsiyani **in'ektsiya** qiladi.
Bu tufayli:

- biznes-mantiq tarmoq/FCM SDK chaqiruvlaridan mustaqil bo'ladi
  (framework-agnostik, testlash oson);
- testlarda yuborgich fake/mock bilan almashtiriladi (Property 41 va dispatch
  integratsion testi — task 14.2/14.3);
- haqiqiy FCM integratsiyasi keyinchalik ``FcmSender`` ni amalga oshiruvchi yangi
  klass sifatida qo'shiladi (masalan, ``FirebaseFcmSender``), qolgan kod
  o'zgarmaydi.

Dizayn (design.md — "Push Notification Dizayni"): har bir yaroqli token uchun
``send(...)`` chaqiriladi; qabul qiluvchilarni filtrlash (notifications_enabled
va yaroqli token) ``NotificationService`` zimmasida (R16.5, R16.6).

Bog'liq talablar: R16.1, R16.2, R16.3, R16.4 (yuborish), R16.5, R16.6 (o'tkazib
yuborish — bu yerda emas, servisda).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FcmMessage:
    """Bitta qurilma tokeniga yuboriladigan push xabari (transient).

    Maydonlar:
    - ``token``: maqsadli qurilma tokeni (yaroqli, ``is_valid=true``).
    - ``title``: bildirishnoma sarlavhasi.
    - ``body``: bildirishnoma matni.
    - ``data``: (ixtiyoriy) qo'shimcha kalit-qiymat yuk (deep-link, hodisa turi
      va h.k.). Qiymatlar FCM `data` payload konvensiyasiga mos ravishda satr
      bo'ladi.
    """

    token: str
    title: str
    body: str
    data: dict[str, str] = field(default_factory=dict)


@runtime_checkable
class FcmSender(Protocol):
    """Push yuborgich interfeysi (abstraksiya) — mock qilinadi (R16).

    Implementatsiyalar bitta qurilma tokeniga bitta xabar yuboradi. Interfeys
    ataylab minimal va yon ta'sir-izolyatsiyalangan: filtrlash, takrorlash yoki
    navbatlash mantig'i yuqori qatlamda (``NotificationService``) joylashadi.
    """

    def send(
        self,
        token: str,
        title: str,
        body: str,
        data: dict[str, str] | None = None,
    ) -> bool:
        """Berilgan tokenga push xabarini yuboradi.

        Args:
            token: maqsadli qurilma tokeni.
            title: bildirishnoma sarlavhasi.
            body: bildirishnoma matni.
            data: (ixtiyoriy) qo'shimcha satr kalit-qiymat yuk.

        Returns:
            Yuborish (mantiqan) qabul qilingan bo'lsa ``True``.
        """
        ...


class NoopFcmSender:
    """Hech narsa yubormaydigan xavfsiz standart yuborgich (R16).

    FCM hali sozlanmagan muhitlarda (yoki testlarda) standart sifatida
    ishlatiladi: ``send(...)`` har doim muvaffaqiyatli (``True``) hisoblanadi,
    ammo tashqi chaqiruv bajarilmaydi. Yuborilgan xabarlar ``sent`` ro'yxatida
    saqlanadi — bu sodda tekshiruvlar uchun qulay.
    """

    def __init__(self) -> None:
        #: Yuborishga uzatilgan xabarlar (kuzatuv/test uchun).
        self.sent: list[FcmMessage] = []

    def send(
        self,
        token: str,
        title: str,
        body: str,
        data: dict[str, str] | None = None,
    ) -> bool:
        """Xabarni ``sent`` ga qayd etadi va muvaffaqiyatli deb qaytaradi."""
        self.sent.append(
            FcmMessage(token=token, title=title, body=body, data=dict(data or {}))
        )
        return True


class LoggingFcmSender:
    """Jurnalga yozuvchi yupqa "real-stub" yuborgich (R16).

    Haqiqiy FCM SDK ulanmasdan turib, dispatch oqimini kuzatish uchun foydali.
    Maxfiy ma'lumot (token qiymati) **to'liq** jurnalga yozilmaydi (R17.5) —
    faqat qisqartirilgan ko'rinish chiqariladi.
    """

    def __init__(self, log: logging.Logger | None = None) -> None:
        self._log = log or logger

    @staticmethod
    def _mask(token: str) -> str:
        """Token qiymatini jurnal uchun qisqartiradi (R17.5)."""
        if len(token) <= 4:
            return "***"
        return f"***{token[-4:]}"

    def send(
        self,
        token: str,
        title: str,
        body: str,
        data: dict[str, str] | None = None,
    ) -> bool:
        """Yuborishni jurnalga yozadi (token maskalangan holda)."""
        self._log.info(
            "FCM push: token=%s title=%s data_keys=%s",
            self._mask(token),
            title,
            sorted((data or {}).keys()),
        )
        return True


__all__ = [
    "FcmMessage",
    "FcmSender",
    "NoopFcmSender",
    "LoggingFcmSender",
]
