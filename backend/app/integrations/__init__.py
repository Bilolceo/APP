"""Tashqi xizmatlar bilan integratsiya abstraksiyalari (FCM va boshqalar).

Ushbu paket yon ta'sirli tashqi xizmatlarni (masalan, push provayderi FCM)
ilova mantig'idan ajratib turadi. Integratsiyalar **interfeys** (abstraksiya)
sifatida belgilanadi va servis qatlamiga **in'ektsiya** qilinadi; bu ularni
testlarda mock/fake bilan almashtirishga imkon beradi va biznes-mantiqни
tarmoq chaqiruvlaridan mustaqil saqlaydi.

Eksport:
- ``FcmSender`` — push yuborgich interfeysi (abstraksiya).
- ``NoopFcmSender`` — hech narsa yubormaydigan, xavfsiz standart implementatsiya.
- ``LoggingFcmSender`` — jurnalga yozuvchi yupqa "real-stub" implementatsiya.
- ``FcmMessage`` — yuboriladigan xabar tarkibi (transient).
"""

from __future__ import annotations

from app.integrations.fcm import (
    FcmMessage,
    FcmSender,
    LoggingFcmSender,
    NoopFcmSender,
)

__all__ = [
    "FcmSender",
    "NoopFcmSender",
    "LoggingFcmSender",
    "FcmMessage",
]
