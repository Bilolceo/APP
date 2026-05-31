"""Ekspert_Moduli — ExpertReviewService (R13).

Ushbu servis ekspert tomonidan biriktirilgan rahbarni 6 mezon bo'yicha
baholashni biznes-mantiq darajasida birlashtiradi. Servis sof
**framework'dan mustaqil** (FastAPI/HTTP haqida hech narsa bilmaydi):
konstruktorda SQLAlchemy ``Session`` (yoki tayyor repositorylar) oladi, sof
domen funksiyalari (``app.domain.expert``) orqali validatsiya/o'rtacha
hisoblashni bajaradi va repository qatlami orqali ma'lumotlarga kiradi.

Mas'uliyat (design.md — "Ekspert_Moduli (ExpertReviewService)"):

- ``submit_review(expert_id, leader_id, scores)`` — oltita mezon bo'yicha
  baholashni qabul qiladi va quyidagilarni amalga oshiradi:
    1. **Validatsiya** (R13.1, R13.3, R13.4): har bir mezon 1–5 oralig'idagi
       butun son va oltita mezon to'liq bo'lishi shart. Yaroqsiz bo'lsa hech
       narsa saqlanmasdan ``ValidationError`` ko'tariladi.
    2. **O'rtacha** (R13.2): ``compute_expert_average`` orqali 1.00–5.00,
       2 kasr xonasigacha.
    3. **Biriktirilganlik tekshiruvi** (R13.5): ekspert rahbarga biriktirilmagan
       bo'lsa, hech narsa saqlanmasdan ``PermissionDeniedError`` (403).
    4. **Saqlash**: ``ExpertReviewRepository.create(...)`` orqali sharhni
       persist qiladi.
    5. **Qo'shimcha ko'rsatkich** (R13.2): ekspert o'rtacha bahosini rahbarning
       eng so'nggi natijasiga (``TestResult.expert_score``) qo'shadi.
    6. **Bildirishnoma** (R13.6): rahbarga ekspert tavsiyasi kelgani haqida
       push hodisasini ishga tushiradi.

Dizayn qarorlari (hujjatlangan)
-------------------------------
**PermissionDeniedError (403).** ``app.services.errors`` da 403 (Forbidden)
semantik tipi yo'q va u modul o'zgartirilmaydi. Shu sababli — ``PortfolioService``
dagi bilan **bir xil naqsh** bo'yicha — shu modulda ``ServiceError`` ustiga
``PermissionDeniedError`` (``code="forbidden"``) belgilanadi. Router qatlami uni
403 ga keltiradi (R4.5, R13.5).

**Validatsiya tartibi.** Avval mezonlar validatsiya qilinadi (R13.3, R13.4),
so'ng biriktirilganlik tekshiriladi (R13.5) — task 13.5 ko'rsatmasiga muvofiq.
Ikkala holatda ham hech narsa saqlanmaydi, shuning uchun tartib persistensiya
semantikasini o'zgartirmaydi.

**Natijasiz rahbar.** Agar rahbarda hali test natijasi bo'lmasa (``latest_for_user``
``None`` qaytarsa), ``expert_score`` qo'yiladigan natija yo'q: bu holda ekspert
bahosi qo'shilmaydi (o'tkazib yuboriladi), **lekin ekspert sharhi baribir
saqlanadi va bildirishnoma yuboriladi**. Ekspert bahosi rahbar keyingi testni
topshirib natija olganidan keyin emas, mavjud so'nggi natijaga qo'shiladi; natija
bo'lmasa sharhning o'zi mustaqil qiymatga ega (R13.1 baholash ruxsati). Bu
xatti-harakat ``submit_review`` qaytaradigan ``ExpertReviewOutcome.expert_score_applied``
bayrog'i orqali ham ko'rsatiladi.

**Bildirishnoma in'ektsiyasi.** Servis ``NotificationService`` ga **qattiq
bog'lanmaydi**: konstruktorda ixtiyoriy ``NotificationService`` (yoki ekvivalent
``notify_expert_review(leader)`` metodli obyekt) qabul qilinadi. ``None`` bo'lsa
bildirishnoma o'tkazib yuboriladi (masalan, push o'chirilgan muhitlarda yoki
testlarda). Bildirishnoma **commit dan keyin** chaqiriladi: push — qaytarib
bo'lmaydigan tashqi yon ta'sir, shuning uchun u faqat ma'lumot bardoshli
saqlangach yuborilishi kerak (R13.6 — "WHEN ekspert bahosi qo'shilganda").
Bildirishnoma chaqiruvi xato bersa ham, allaqachon saqlangan sharh/ball
buzilmaydi (xato izolyatsiya qilinadi va jurnalga yoziladi).

**Tranzaksiya boshqaruvi.** Holatni o'zgartiruvchi amal servis ichida ``commit``
qilinadi (AuthService/SessionService bilan bir xil konvensiya).

Bog'liq talablar: R13.1, R13.2, R13.3, R13.4, R13.5, R13.6.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Protocol

from sqlalchemy.orm import Session

from app.domain.expert import (
    EXPERT_CRITERIA,
    compute_expert_average,
    validate_expert_scores,
)
from app.models.expert import ExpertReview
from app.repositories.expert import ExpertReviewRepository
from app.repositories.results import ResultRepository
from app.services.errors import ServiceError, ValidationError

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Egalik/biriktirilganlik buzilishi (403) — errors.py da maxsus tip yo'q.
# PortfolioService dagi bilan bir xil naqsh (errors.py o'zgartirilmaydi).
# ---------------------------------------------------------------------------
class PermissionDeniedError(ServiceError):
    """So'rovchiga ruxsat yo'q — HTTP 403 (R4.5, R13.5).

    `app.services.errors` da Forbidden/Authorization tipi mavjud emas; uni
    o'zgartirmaslik uchun shu servis modulida `ServiceError` ustiga aniq
    semantik tip belgilanadi. Router qatlami ``code="forbidden"`` ni 403 ga
    keltiradi.
    """

    code = "forbidden"


class _ExpertNotifier(Protocol):
    """Bildirishnoma in'ektsiyasi uchun minimal interfeys (R13.6).

    ``NotificationService`` shu shartnomani qondiradi. Servis faqat shu metodga
    tayanadi — bu qattiq bog'lanishni kamaytiradi va testda stub bilan
    almashtirishni osonlashtiradi.
    """

    def notify_expert_review(self, leader: Any) -> int:
        """Rahbarga ekspert tavsiyasi kelgani haqida bildirishnoma yuboradi."""
        ...


@dataclass(frozen=True)
class ExpertReviewOutcome:
    """``submit_review`` natijasi — transient (I/O'siz) ko'rinish.

    Maydonlar:
    - ``review_id``: saqlangan ``expert_reviews`` yozuvi identifikatori.
    - ``average_score``: ekspert o'rtacha bahosi (1.00–5.00) (R13.2).
    - ``expert_score_applied``: ekspert bahosi rahbarning so'nggi natijasiga
      qo'shildimi (rahbarda natija bo'lmasa ``False``).
    """

    review_id: int
    average_score: Decimal
    expert_score_applied: bool


class ExpertReviewService:
    """Ekspert baholash biznes-mantiq servisi (R13).

    Args:
        session: faol SQLAlchemy ``Session``. Servis o'z yozuvlarini ushbu
            sessiyada ``commit`` qiladi (tranzaksiya chegarasi shu yerda).
        reviews: (ixtiyoriy) tayyor ``ExpertReviewRepository`` — testlar uchun.
            ``None`` bo'lsa ``session`` dan quriladi.
        results: (ixtiyoriy) tayyor ``ResultRepository`` — testlar uchun.
            ``None`` bo'lsa ``session`` dan quriladi.
        notifications: (ixtiyoriy) ``notify_expert_review(leader)`` metodli
            bildirishnoma servisi (``NotificationService``). ``None`` bo'lsa
            bildirishnoma o'tkazib yuboriladi (R13.6 seam).
    """

    def __init__(
        self,
        session: Session,
        *,
        reviews: ExpertReviewRepository | None = None,
        results: ResultRepository | None = None,
        notifications: _ExpertNotifier | None = None,
    ) -> None:
        self.session = session
        self._reviews = reviews or ExpertReviewRepository(session)
        self._results = results or ResultRepository(session)
        self._notifications = notifications

    # ------------------------------------------------------------------
    # R13.1–R13.6 — ekspert baholashni topshirish
    # ------------------------------------------------------------------

    def submit_review(
        self,
        expert_id: int,
        leader_id: int,
        scores: Mapping[str, Any],
    ) -> ExpertReviewOutcome:
        """Ekspert baholashni qabul qiladi, saqlaydi va bildirishnoma yuboradi.

        Oqim (modul docstring'idagi qarorlarga muvofiq):

        1. Mezonlarni validatsiya qiladi (R13.1, R13.3, R13.4) — yaroqsiz bo'lsa
           hech narsa saqlamasdan ``ValidationError``.
        2. O'rtacha bahoni hisoblaydi (R13.2).
        3. Biriktirilganlikni tekshiradi (R13.5) — biriktirilmagan bo'lsa hech
           narsa saqlamasdan ``PermissionDeniedError`` (403).
        4. Sharhni saqlaydi (R13.1, R13.2).
        5. Ekspert bahosini rahbarning so'nggi natijasiga qo'shadi (R13.2);
           natija bo'lmasa o'tkazib yuboriladi (sharh baribir saqlanadi).
        6. ``commit`` qiladi, so'ng bildirishnoma yuboradi (R13.6).

        Args:
            expert_id: baholayotgan ekspert identifikatori.
            leader_id: baholanayotgan rahbar identifikatori.
            scores: mezon nomi -> baho (1–5 butun son) moslamasi. Mezon nomlari
                ``app.domain.expert.EXPERT_CRITERIA`` ga mos bo'lishi kerak.

        Returns:
            :class:`ExpertReviewOutcome` — sharh identifikatori, o'rtacha baho va
            ekspert bahosi natijaga qo'shilgani haqidagi bayroq.

        Raises:
            ValidationError: bironta mezon yaroqsiz yoki to'ldirilmagan bo'lsa
                (R13.3, R13.4) — hech narsa saqlanmaydi.
            PermissionDeniedError: ekspert rahbarga biriktirilmagan bo'lsa
                (R13.5) — hech narsa saqlanmaydi.
        """
        # 1 — mezon validatsiyasi (R13.1, R13.3, R13.4). Sof domen funksiyasi
        # xato xabarlari ro'yxatini qaytaradi; bo'sh emas bo'lsa hech narsa
        # saqlanmasdan ValidationError ko'tariladi.
        errors = validate_expert_scores(scores)
        if errors:
            raise ValidationError(
                "Ekspert baholash yaroqsiz",
                field="scores",
                code="invalid_expert_scores",
                details={"errors": errors},
            )

        # 2 — o'rtacha baho (R13.2). Validatsiyadan o'tgani uchun bu yerda istisno
        # kutilmaydi, ammo himoya sifatida qayta hisoblanadi (sof funksiya).
        average = compute_expert_average(scores)

        # 3 — biriktirilganlik tekshiruvi (R13.5). Biriktirilmagan (yoki mavjud
        # bo'lmagan ekspert/rahbar) -> 403, hech narsa saqlanmaydi.
        if not self._reviews.is_expert_assigned(expert_id, leader_id):
            raise PermissionDeniedError(
                "Bu rahbarni baholashga ruxsat yo'q (biriktirilmagan)"
            )

        # 4 — sharhni saqlash (R13.1, R13.2). Mezonlar validatsiyadan o'tgan
        # butun sonlar; repository faqat hisoblangan qiymatlarni persist qiladi.
        review = self._reviews.create(
            expert_id=expert_id,
            leader_id=leader_id,
            average_score=average,
            **{criterion: int(scores[criterion]) for criterion in EXPERT_CRITERIA},
        )

        # 5 — ekspert bahosini rahbarning so'nggi natijasiga qo'shimcha
        # ko'rsatkich sifatida qo'shish (R13.2). Natija bo'lmasa o'tkazib
        # yuboriladi (sharh baribir saqlanadi) — modul docstring'iga qarang.
        latest_result = self._results.latest_for_user(leader_id)
        expert_score_applied = False
        if latest_result is not None:
            latest_result.expert_score = average
            self.session.flush()
            expert_score_applied = True

        review_id = review.id

        # 6 — tranzaksiyani yakunlash (commit servis ichida — AuthService/
        # SessionService konvensiyasi). Bildirishnoma commit'dan keyin yuboriladi.
        self.session.commit()

        # R13.6 — bildirishnoma (qaytarib bo'lmaydigan tashqi yon ta'sir):
        # faqat ma'lumot saqlangach yuboriladi. Xato izolyatsiya qilinadi —
        # bildirishnoma nosozligi allaqachon saqlangan sharhni buzmaydi.
        self._notify_leader(leader_id)

        return ExpertReviewOutcome(
            review_id=review_id,
            average_score=average,
            expert_score_applied=expert_score_applied,
        )

    # ------------------------------------------------------------------
    # Ichki yordamchilar
    # ------------------------------------------------------------------

    def _notify_leader(self, leader_id: int) -> None:
        """Rahbarga ekspert tavsiyasi bildirishnomasini yuboradi (R13.6).

        Bildirishnoma servisi berilmagan bo'lsa (``None``) hech narsa
        qilinmaydi. Tashqi xizmat nosozligi izolyatsiya qilinadi: bu yerdagi
        istisno yuqoriga tarqalmaydi, chunki sharh allaqachon commit qilingan.
        """
        if self._notifications is None:
            return
        try:
            self._notifications.notify_expert_review(leader_id)
        except Exception:  # noqa: BLE001 - tashqi bildirishnoma nosozligi izolyatsiyasi
            logger.warning(
                "Ekspert tavsiyasi bildirishnomasi yuborilmadi (leader_id=%s) — "
                "sharh saqlangan",
                leader_id,
            )


__all__ = [
    "ExpertReviewService",
    "ExpertReviewOutcome",
    "PermissionDeniedError",
]
