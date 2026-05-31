"""Reyting_Moduli domen yadrosi — sof saralash va o'rin berish funksiyalari.

Ushbu modul reyting hisoblashning I/O'dan mustaqil, deterministik yadrosini
o'z ichiga oladi. U faqat ``app.domain.types`` dagi sof ma'lumot
strukturalariga (``RatingRecord`` -> ``RankedEntry``) tayanadi va hech qanday
DB, fayl yoki tarmoq operatsiyasini bajarmaydi. Shu sababli u property-based
testlar uchun ideal nishon hisoblanadi (sof, deterministik, framework'dan
mustaqil).

Bog'liq talablar (requirements.md — Requirement 12):
- R12.1: har bir yozuv uchun reyting o'rni (rank) va saralash ko'rsatkichi
  (umumiy foiz, 0–100%, 2 kasr) qaytariladi.
- R12.2: yozuvlar saralash ko'rsatkichi bo'yicha **kamayish** tartibida
  tartiblanadi.
- R12.3: teng saralash ko'rsatkichiga ega yozuvlar **bir xil** rank oladi,
  keyingi o'rin teng yozuvlar soniga mos ravishda **o'tkazib yuboriladi**
  (standart musobaqa reytingi, "1224"), va teng yozuvlar natijaga erishilgan
  sana (``achieved_at``) bo'yicha **o'suvchi** tartibda joylashtiriladi.

4.3-vazifa ushbu modulga anonimlashtirish (R12.4) va natijasiz foydalanuvchini
reytingdan chiqarish (R12.5) mantig'ini qo'shadi. Bu funksiyalar ham sof bo'lib,
tartiblash/o'rin berishda mavjud ``compute_ranking`` ni qayta ishlatadi.
"""

from __future__ import annotations

from collections.abc import Hashable
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from app.domain.types import RankedEntry, RatingRecord

__all__ = [
    "compute_ranking",
    # 4.3-vazifa — anonimlashtirish va natijasiz foydalanuvchini chiqarish
    "RatingParticipant",
    "AnonymizedRatingEntry",
    "OutOfRankingEntry",
    "RatingPartition",
    "AnonymizedRating",
    "is_ranked",
    "exclude_unranked",
    "build_anonymized_rating",
]


def compute_ranking(records: list[RatingRecord]) -> list[RankedEntry]:
    """Reyting yozuvlarini saralab, ularga reyting o'rni (rank) beradi.

    Standart musobaqa reytingi ("1224") qo'llaniladi:

    - Yozuvlar saralash ko'rsatkichi (``sort_metric`` — umumiy foiz) bo'yicha
      **kamayish** tartibida saralanadi (R12.2).
    - Teng ``sort_metric`` qiymatiga ega yozuvlar **bir xil** rank oladi va
      keyingi (qat'iy kichik) ko'rsatkich teng yozuvlar soniga mos ravishda
      o'tkazib yuborilgan rankni oladi (R12.3). Masalan, ko'rsatkichlar
      ``[90, 80, 80, 70]`` -> ranklar ``[1, 2, 2, 4]``.
    - Teng ``sort_metric`` ichida yozuvlar ``achieved_at`` bo'yicha **o'suvchi**
      (eng erta birinchi) tartibda joylashtiriladi (R12.3).

    Funksiya kirish ro'yxatining tartibiga nisbatan **deterministik**: bir xil
    yozuvlar to'plami qanday tartibda berilishidan qat'i nazar, bir xil natija
    qaytariladi. To'liq determinizmni ta'minlash uchun ``sort_metric`` va
    ``achieved_at`` bo'yicha teng bo'lgan yozuvlar ``entity_id`` bo'yicha
    barqaror tartiblanadi (bu ularning rankiga ta'sir qilmaydi, faqat chiqish
    ro'yxatidagi joylashuvni aniqlaydi).

    Args:
        records: Reyting yozuvlari ro'yxati. Kirish o'zgartirilmaydi.

    Returns:
        ``RankedEntry`` ro'yxati — saralash ko'rsatkichi bo'yicha kamayuvchi
        tartibda, har bir yozuv uchun hisoblangan rank bilan. Bo'sh kirish
        bo'sh ro'yxat qaytaradi.
    """
    # Determinizm uchun to'liq aniqlangan saralash kaliti:
    #   1) sort_metric kamayuvchi (kattadan kichikka) — manfiy bilan o'suvchiga aylantiramiz,
    #   2) achieved_at o'suvchi (eng erta birinchi),
    #   3) entity_id o'suvchi — qolgan teng holatlarni barqaror uzish uchun.
    ordered = sorted(
        records,
        key=lambda record: (-record.sort_metric, record.achieved_at, record.entity_id),
    )

    ranked: list[RankedEntry] = []
    previous_metric = None
    previous_rank = 0

    for index, record in enumerate(ordered):
        # Standart musobaqa reytingi: yangi (kichikroq) ko'rsatkich uchun rank
        # joriy pozitsiya (1 dan boshlab) bo'ladi; teng ko'rsatkich avvalgi
        # rankni saqlaydi. Bu teng guruh hajmiga mos ravishda o'rinlarni
        # o'tkazib yuborishni avtomatik ta'minlaydi.
        if previous_metric is None or record.sort_metric != previous_metric:
            rank = index + 1
            previous_metric = record.sort_metric
            previous_rank = rank
        else:
            rank = previous_rank

        ranked.append(
            RankedEntry(
                entity_id=record.entity_id,
                rank=rank,
                sort_metric=record.sort_metric,
            )
        )

    return ranked


# ======================================================================
# 4.3-vazifa — Anonimlashtirish (R12.4) va natijasiz foydalanuvchini
# reytingdan chiqarish (R12.5)
# ======================================================================
#
# Quyidagi tiplar va funksiyalar reyting taqdimotini sof (I/O'siz) shaklda
# tayyorlaydi:
#   1) Reyting subyektini (rahbar) faqat anonim, taqdim etish mumkin bo'lgan
#      maydonlarga qisqartirish: hudud, tashkilot turi, lavozim, saralash
#      ko'rsatkichi (umumiy foiz) va reyting o'rni (rank). To'liq ism, telefon
#      raqami va boshqa bevosita identifikatsiyalovchi shaxsiy ma'lumotlar
#      taqdimotdan butunlay chiqariladi (R12.4).
#   2) So'rovchining o'z yozuvini ajratib ko'rsatish uchun ``is_requester``
#      bayrog'i (UI uni ajratishi uchun) (R12.4).
#   3) Kamida bitta yakunlangan natijasi bo'lmagan foydalanuvchini reytingdan
#      chiqarish — bunday subyektga rank berilmaydi (R12.5).
#
# Tartiblash va o'rin berish mavjud ``compute_ranking`` ga topshiriladi, shu
# tarzda R12.2/R12.3 mantig'i takrorlanmaydi.


@dataclass(frozen=True)
class RatingParticipant:
    """Reyting taqdimoti uchun bitta subyekt (rahbar) kirish yozuvi (transient).

    Bu yozuv ``RatingRecord`` (saralash uchun zarur minimal ma'lumot) ni
    anonim taqdimot maydonlari bilan kengaytiradi. ``percentage`` ``None``
    bo'lsa, subyektning hali yakunlangan test natijasi yo'q va u reytingdan
    chiqariladi (R12.5).

    DIQQAT: bu yozuv MAXFIY/identifikatsiyalovchi maydonlarni (to'liq ism,
    telefon raqami va h.k.) ATAYIN o'z ichiga olmaydi — anonimlik buzilmasligi
    uchun bunday ma'lumotlar domen yadrosiga umuman uzatilmaydi (R12.4).

    Maydonlar:
    - ``entity_id``: subyekt identifikatori (rahbar/tashkilot/hudud). Faqat
      so'rovchining o'z yozuvini aniqlash va tartiblashni barqarorlashtirish
      uchun ishlatiladi; anonim chiqishda oshkor qilinmaydi.
    - ``percentage``: saralash ko'rsatkichi — umumiy foiz (0–100, 2 kasr), yoki
      yakunlangan natijasi bo'lmasa ``None`` (R12.5).
    - ``region``: hudud kesimi (taqdim etiladi, R12.4).
    - ``org_type``: tashkilot turi (taqdim etiladi, R12.4).
    - ``position``: lavozim (taqdim etiladi, R12.4).
    - ``achieved_at``: natijaga erishilgan sana/vaqt; teng ko'rsatkichlarni
      o'suvchi tartibda joylashtirish uchun (R12.3). ``percentage is None``
      bo'lganda e'tiborga olinmaydi.
    """

    entity_id: int
    percentage: Decimal | None
    region: Hashable | None = None
    org_type: Hashable | None = None
    position: Hashable | None = None
    achieved_at: datetime | None = None


@dataclass(frozen=True)
class AnonymizedRatingEntry:
    """Reytingda taqdim etiladigan bitta anonim yozuv (chiqish, transient) — R12.4.

    ATAYIN faqat quyidagi maydonlarni oshkor qiladi: ``region``, ``org_type``,
    ``position``, ``percentage`` (saralash ko'rsatkichi) va ``rank``. To'liq
    ism, telefon raqami yoki boshqa bevosita identifikatsiyalovchi shaxsiy
    ma'lumotlar bu yerda MAVJUD EMAS.

    Maydonlar:
    - ``rank``: reyting o'rni (1 dan boshlanadi) (R12.1).
    - ``percentage``: saralash ko'rsatkichi — umumiy foiz (R12.1).
    - ``region``: hudud (R12.4).
    - ``org_type``: tashkilot turi (R12.4).
    - ``position``: lavozim (R12.4).
    - ``is_requester``: ``True`` bo'lsa, bu yozuv so'rovchining o'ziga tegishli;
      UI uni ajratib ko'rsatishi uchun bayroq (R12.4). Anonimlikni buzmaydi,
      chunki hech qanday identifikatsiyalovchi qiymat qo'shilmaydi.
    """

    rank: int
    percentage: Decimal
    region: Hashable | None = None
    org_type: Hashable | None = None
    position: Hashable | None = None
    is_requester: bool = False


@dataclass(frozen=True)
class OutOfRankingEntry:
    """Reytingdan tashqaridagi subyekt (yakunlangan natijasi yo'q) — R12.5.

    Bunday subyektga reyting o'rni (rank) BERILMAYDI. Faqat anonim taqdimot
    maydonlari va so'rovchi bayrog'i saqlanadi, shunda so'rovchi o'zining
    reytingdan tashqarida ekanini ko'ra oladi.

    Maydonlar:
    - ``region``: hudud (R12.4).
    - ``org_type``: tashkilot turi (R12.4).
    - ``position``: lavozim (R12.4).
    - ``is_requester``: ``True`` bo'lsa, bu so'rovchining o'z (reytingsiz)
      yozuvi.
    """

    region: Hashable | None = None
    org_type: Hashable | None = None
    position: Hashable | None = None
    is_requester: bool = False


@dataclass(frozen=True)
class RatingPartition:
    """``RatingParticipant`` larni reytingli/reytingsizga ajratish natijasi — R12.5.

    Maydonlar:
    - ``ranked``: kamida bitta yakunlangan natijasi bor (``percentage is not
      None``) subyektlar, ``RatingRecord`` ko'rinishida — to'g'ridan-to'g'ri
      ``compute_ranking`` ga uzatish uchun.
    - ``unranked``: yakunlangan natijasi bo'lmagan (``percentage is None``)
      subyektlar, asl ``RatingParticipant`` ko'rinishida saqlanadi.
    """

    ranked: list[RatingRecord]
    unranked: list[RatingParticipant]


@dataclass(frozen=True)
class AnonymizedRating:
    """To'liq anonim reyting taqdimoti (chiqish, transient) — R12.4, R12.5.

    Maydonlar:
    - ``ranked``: tartiblangan anonim yozuvlar (kamayuvchi ko'rsatkich, R12.2),
      har biri rank bilan.
    - ``out_of_ranking``: yakunlangan natijasi bo'lmagani uchun reytingdan
      tashqaridagi subyektlar (rank berilmagan) (R12.5).
    """

    ranked: list[AnonymizedRatingEntry]
    out_of_ranking: list[OutOfRankingEntry]


def is_ranked(participant: RatingParticipant) -> bool:
    """Subyekt reytingga kiritilishi mumkinligini bildiradi (R12.5).

    Subyekt faqat kamida bitta yakunlangan test natijasiga ega bo'lsa
    (``percentage is not None``) reytingga kiritiladi.

    Args:
        participant: reyting subyekti.

    Returns:
        ``True`` — subyektning yakunlangan natijasi bor (reytingga kiradi);
        ``False`` — natijasi yo'q (reytingdan tashqarida).

    Validates: Requirements 12.5
    """
    return participant.percentage is not None


def exclude_unranked(participants: list[RatingParticipant]) -> RatingPartition:
    """Subyektlarni reytingli (natijasi bor) va reytingsizga ajratadi (R12.5).

    Yakunlangan natijasi bor subyektlar (``percentage is not None``) reytingga
    kiritiladi va ``RatingRecord`` ga aylantiriladi (``compute_ranking`` uchun);
    natijasi bo'lmaganlar (``percentage is None``) reytingdan chiqariladi va
    ularga rank berilmaydi.

    Sof va deterministik: kirish tartibi saqlanadi, kirish ro'yxati
    o'zgartirilmaydi.

    Args:
        participants: reyting subyektlari ro'yxati.

    Returns:
        ``RatingPartition`` — reytingli ``RatingRecord`` lar va reytingsiz
        ``RatingParticipant`` lar.

    Validates: Requirements 12.5
    """
    ranked: list[RatingRecord] = []
    unranked: list[RatingParticipant] = []

    for participant in participants:
        if is_ranked(participant):
            # ``is_ranked`` percentage None emasligini kafolatlaydi. Yakunlangan
            # natijasi bor subyekt uchun ``achieved_at`` ham mavjud bo'lishi
            # shart (R12.3 teng ko'rsatkichlarni sana bo'yicha tartiblaydi).
            # Uni datetime "fallback" bilan to'ldirmaymiz: naive/aware
            # datetime aralashmasi ``compute_ranking`` saralashida TypeError
            # keltirib chiqaradi va izchillikni buzadi.
            if participant.achieved_at is None:
                raise ValueError(
                    "Reytingli subyekt (percentage mavjud) uchun achieved_at "
                    f"berilishi shart: entity_id={participant.entity_id}."
                )
            ranked.append(
                RatingRecord(
                    entity_id=participant.entity_id,
                    sort_metric=participant.percentage,
                    achieved_at=participant.achieved_at,
                )
            )
        else:
            unranked.append(participant)

    return RatingPartition(ranked=ranked, unranked=unranked)


def build_anonymized_rating(
    participants: list[RatingParticipant],
    requester_id: int | None = None,
) -> AnonymizedRating:
    """Anonim, tartiblangan reyting taqdimotini quradi (R12.4, R12.5).

    Bosqichlar:
    1. Yakunlangan natijasi bo'lmagan subyektlar reytingdan chiqariladi va
       ``out_of_ranking`` ga (rank berilmasdan) joylanadi (R12.5).
    2. Qolgan subyektlar ``compute_ranking`` orqali umumiy foiz bo'yicha
       kamayuvchi tartibda saralanadi va rank oladi (R12.2, R12.3).
    3. Har bir yozuv faqat anonim maydonlar (hudud, tashkilot turi, lavozim,
       ko'rsatkich, rank) bilan taqdim etiladi; to'liq ism, telefon raqami va
       boshqa identifikatsiyalovchi ma'lumotlar oshkor qilinmaydi (R12.4).
    4. ``requester_id`` ga mos yozuv(lar) ``is_requester=True`` bilan ajratiladi
       (R12.4) — reytingli va reytingsiz qismlarda ham.

    Sof va deterministik: kirish o'zgartirilmaydi; chiqish tartibi
    ``compute_ranking`` (reytingli qism) va kirish tartibi (reytingsiz qism)
    bilan to'liq aniqlangan.

    Args:
        participants: reyting subyektlari (anonim maydonlar + ko'rsatkich).
        requester_id: so'rovchining ``entity_id`` si; ``None`` bo'lsa hech
            qaysi yozuv so'rovchi sifatida belgilanmaydi.

    Returns:
        ``AnonymizedRating`` — anonim reytingli yozuvlar va reytingdan
        tashqaridagi yozuvlar.

    Validates: Requirements 12.4, 12.5
    """
    partition = exclude_unranked(participants)

    # entity_id -> anonim taqdimot maydonlari (faqat reytingli subyektlar uchun).
    # Anonimlik: faqat region/org_type/position saqlanadi, identifikatsiyalovchi
    # maydonlar (ism, telefon) bu yerga umuman kirmaydi (R12.4).
    presentation: dict[int, RatingParticipant] = {
        participant.entity_id: participant
        for participant in participants
        if is_ranked(participant)
    }

    ordered = compute_ranking(partition.ranked)

    ranked_entries: list[AnonymizedRatingEntry] = []
    for entry in ordered:
        source = presentation[entry.entity_id]
        ranked_entries.append(
            AnonymizedRatingEntry(
                rank=entry.rank,
                percentage=entry.sort_metric,
                region=source.region,
                org_type=source.org_type,
                position=source.position,
                is_requester=(
                    requester_id is not None and entry.entity_id == requester_id
                ),
            )
        )

    out_of_ranking = [
        OutOfRankingEntry(
            region=participant.region,
            org_type=participant.org_type,
            position=participant.position,
            is_requester=(
                requester_id is not None and participant.entity_id == requester_id
            ),
        )
        for participant in partition.unranked
    ]

    return AnonymizedRating(ranked=ranked_entries, out_of_ranking=out_of_ranking)
