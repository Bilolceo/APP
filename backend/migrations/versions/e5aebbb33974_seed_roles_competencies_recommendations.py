"""seed — rollar, namunaviy kompetensiyalar va tavsiyalar (vazifa 21.1)

Ushbu migratsiya boshlang'ich (seed) ma'lumotlarni idempotent tarzda qo'shadi:

- **Rollar** (R1.7): ``Rahbar``, ``Ekspert``, ``Administrator`` — tizimdagi
  yagona yaroqli rollar (``app.domain.auth_validation.VALID_ROLES`` bilan
  bir xil kanonik satrlar).
- **Namunaviy kompetensiyalar** (R8, R14): MTT (maktabgacha ta'lim tashkiloti)
  rahbari uchun baholanadigan kompetensiya yo'nalishlari. Nomlar ekspert
  baholash mezonlari (``expert_reviews`` ustunlari) bilan izchil.
- **Namunaviy tavsiyalar** (R10.1, R10.4): har bir daraja (Past/O'rta/Yaxshi/
  Yuqori) uchun **umumiy standart** tavsiya (``competency_id IS NULL``) hamda
  ayrim kompetensiya+daraja kombinatsiyalari uchun **aniq** tavsiyalar.
  Umumiy standart tavsiyalar ``app.domain.recommendation.select_recommendations``
  totallik kafolatini (har doim tavsiya tanlanadi, R10.4) ta'minlaydi.

Idempotentlik: qo'shishdan oldin mavjud yozuvlar tekshiriladi (rol nomi,
kompetensiya nomi, (competency_id, level, text) uchligi bo'yicha), shu sababli
migratsiyani qayta ishga tushirish takror yozuvlar hosil qilmaydi. Birlamchi
kalitlar avtomatik generatsiya qilinadi (sxema BIGSERIAL/autoincrement
ishlatadi); kompetensiya ID'lari qo'shilgach nom bo'yicha qayta o'qiladi va
tavsiyalarga bog'lanadi.

``downgrade()`` aynan shu seed yozuvlarini (tavsiyalar matni, kompetensiya
nomi, rol nomi bo'yicha) o'chiradi.

Revision ID: e5aebbb33974
Revises: ab13cd15b85c
Create Date: 2026-05-31 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'e5aebbb33974'
down_revision: Union[str, Sequence[str], None] = 'ab13cd15b85c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ---------------------------------------------------------------------------
# Seed ma'lumotlari (yagona manba — upgrade va downgrade ham shulardan foydalanadi)
# ---------------------------------------------------------------------------

#: Yaroqli rollar (R1.7) — auth_validation.VALID_ROLES bilan bir xil.
SEED_ROLES: tuple[str, ...] = ("Rahbar", "Ekspert", "Administrator")

#: Namunaviy kompetensiyalar: (nom, tavsif). Nomlar ekspert baholash mezonlari
#: bilan izchil (boshqaruv madaniyati, jamoaviy ishlash, pedagogik jarayon,
#: innovatsiya, hujjatlar, strategik rejalashtirish).
SEED_COMPETENCIES: tuple[tuple[str, str], ...] = (
    (
        "Boshqaruv madaniyati",
        "Muassasani samarali boshqarish, qaror qabul qilish va rahbarlik "
        "ko'nikmalari.",
    ),
    (
        "Jamoaviy ishlash",
        "Jamoa bilan hamkorlik qilish, nizolarni hal etish va motivatsiya "
        "berish.",
    ),
    (
        "Pedagogik jarayonni tashkil etish",
        "Ta'lim-tarbiya jarayonini rejalashtirish, nazorat qilish va "
        "takomillashtirish.",
    ),
    (
        "Innovatsion faoliyat",
        "Zamonaviy pedagogik texnologiyalar va innovatsiyalarni joriy etish.",
    ),
    (
        "Hujjatlar bilan ishlash",
        "Me'yoriy hujjatlarni yuritish, hisobotlarni tayyorlash va arxivlash.",
    ),
    (
        "Strategik rejalashtirish",
        "Muassasaning rivojlanish maqsadlarini belgilash va strategiya ishlab "
        "chiqish.",
    ),
)

#: Umumiy standart tavsiyalar (competency_id IS NULL) — har bir daraja uchun
#: bittadan (R10.4). Bu tavsiyalar aniq mos topilmaganda tanlanadi va totallik
#: kafolatini ta'minlaydi (select_recommendations).
SEED_GENERAL_RECOMMENDATIONS: tuple[tuple[str, str], ...] = (
    (
        "Past",
        "Ushbu yo'nalish bo'yicha asosiy bilimlarni mustahkamlash uchun bazaviy "
        "malaka oshirish kurslarida qatnashing va mentordan yordam oling.",
    ),
    (
        "O'rta",
        "Bilim va ko'nikmalaringizni tizimli ravishda rivojlantirish uchun "
        "amaliy treninglarda ishtirok eting va tajriba almashing.",
    ),
    (
        "Yaxshi",
        "Erishilgan natijalarni saqlab qoling va ilg'or amaliyotlarni o'rganib, "
        "yangi loyihalarda qo'llang.",
    ),
    (
        "Yuqori",
        "Yuqori darajadagi kompetensiyangizni hamkasblar bilan bo'lishing va "
        "ustozlik (mentorlik) faoliyatini olib boring.",
    ),
)

#: Ayrim kompetensiya+daraja kombinatsiyalari uchun aniq tavsiyalar:
#: (kompetensiya_nomi, daraja, matn). Past va O'rta darajalar uchun beriladi —
#: rivojlanishga eng ko'p ehtiyoj shu darajalarda bo'ladi.
SEED_COMPETENCY_RECOMMENDATIONS: tuple[tuple[str, str, str], ...] = (
    (
        "Boshqaruv madaniyati",
        "Past",
        "Boshqaruv asoslari bo'yicha kurs o'tang: rejalashtirish, vakolat "
        "berish va qaror qabul qilish ko'nikmalarini shakllantiring.",
    ),
    (
        "Boshqaruv madaniyati",
        "O'rta",
        "Boshqaruv uslubingizni tahlil qiling va vaqtni boshqarish hamda "
        "vakolatlarni taqsimlash bo'yicha amaliyotni kuchaytiring.",
    ),
    (
        "Jamoaviy ishlash",
        "Past",
        "Jamoa bilan muloqot va nizolarni hal qilish bo'yicha trening o'ting; "
        "muntazam jamoa yig'ilishlarini tashkil eting.",
    ),
    (
        "Jamoaviy ishlash",
        "O'rta",
        "Jamoa a'zolarini motivatsiya qilish usullarini o'rganing va teskari "
        "aloqa (feedback) madaniyatini joriy eting.",
    ),
    (
        "Pedagogik jarayonni tashkil etish",
        "Past",
        "Pedagogik jarayonni rejalashtirish va nazorat qilish bo'yicha "
        "metodik materiallarni o'rganing va kuzatuv darslarida qatnashing.",
    ),
    (
        "Pedagogik jarayonni tashkil etish",
        "O'rta",
        "Ta'lim sifatini baholash mezonlarini joriy eting va tarbiyachilar "
        "bilan metodik seminarlar tashkil qiling.",
    ),
    (
        "Innovatsion faoliyat",
        "Past",
        "Zamonaviy pedagogik texnologiyalar bilan tanishing va bitta pilot "
        "innovatsion loyihani sinab ko'ring.",
    ),
    (
        "Innovatsion faoliyat",
        "O'rta",
        "Innovatsion tashabbuslarni tizimli joriy eting va ularning samarasini "
        "baholash mexanizmini yarating.",
    ),
    (
        "Hujjatlar bilan ishlash",
        "Past",
        "Me'yoriy hujjatlar va hisobot shakllarini o'rganing; hujjatlarni "
        "yuritish bo'yicha namunaviy tartibni joriy eting.",
    ),
    (
        "Hujjatlar bilan ishlash",
        "O'rta",
        "Hujjat aylanishini raqamlashtiring va hisobotlarni tayyorlash "
        "jarayonini standartlashtiring.",
    ),
    (
        "Strategik rejalashtirish",
        "Past",
        "Muassasaning kuchli va zaif tomonlarini (SWOT) tahlil qilishni "
        "o'rganing va qisqa muddatli maqsadlar belgilang.",
    ),
    (
        "Strategik rejalashtirish",
        "O'rta",
        "Uzoq muddatli rivojlanish strategiyasini ishlab chiqing va uni "
        "bosqichma-bosqich amalga oshirish rejasini tuzing.",
    ),
)


# Ad-hoc jadval ta'riflari (bulk_insert / delete uchun — ORM modellariga
# bog'lanmaydi, shunda migratsiya kelajakdagi model o'zgarishlaridan mustaqil).
_roles_table = sa.table("roles", sa.column("name", sa.String))
_competencies_table = sa.table(
    "competencies",
    sa.column("name", sa.String),
    sa.column("description", sa.Text),
)
_recommendations_table = sa.table(
    "recommendations",
    sa.column("competency_id", sa.BigInteger),
    sa.column("level", sa.String),
    sa.column("text", sa.Text),
)


def upgrade() -> None:
    """Seed ma'lumotlarni idempotent qo'shadi."""
    bind = op.get_bind()

    # --- Rollar (R1.7) ---
    existing_roles = {row[0] for row in bind.execute(sa.text("SELECT name FROM roles"))}
    new_roles = [{"name": name} for name in SEED_ROLES if name not in existing_roles]
    if new_roles:
        op.bulk_insert(_roles_table, new_roles)

    # --- Kompetensiyalar ---
    existing_comps = {
        row[0] for row in bind.execute(sa.text("SELECT name FROM competencies"))
    }
    new_comps = [
        {"name": name, "description": desc}
        for name, desc in SEED_COMPETENCIES
        if name not in existing_comps
    ]
    if new_comps:
        op.bulk_insert(_competencies_table, new_comps)

    # Kompetensiya nomidan ID xaritasini qayta o'qiymiz (avto-generatsiya
    # qilingan ID'larni tavsiyalarga bog'lash uchun).
    comp_id_by_name = {
        name: cid
        for cid, name in bind.execute(sa.text("SELECT id, name FROM competencies"))
    }

    # --- Tavsiyalar (R10.1, R10.4) ---
    existing_recs = {
        (row[0], row[1], row[2])
        for row in bind.execute(
            sa.text("SELECT competency_id, level, text FROM recommendations")
        )
    }

    rec_rows: list[dict] = []

    # Umumiy standart tavsiyalar (competency_id IS NULL) — har bir daraja (R10.4).
    for level, text in SEED_GENERAL_RECOMMENDATIONS:
        if (None, level, text) not in existing_recs:
            rec_rows.append({"competency_id": None, "level": level, "text": text})

    # Aniq kompetensiya+daraja tavsiyalari.
    for comp_name, level, text in SEED_COMPETENCY_RECOMMENDATIONS:
        cid = comp_id_by_name.get(comp_name)
        if cid is None:
            continue
        if (cid, level, text) not in existing_recs:
            rec_rows.append({"competency_id": cid, "level": level, "text": text})

    if rec_rows:
        op.bulk_insert(_recommendations_table, rec_rows)


def downgrade() -> None:
    """Aynan seed qilingan yozuvlarni o'chiradi (teskari tartibda)."""
    # 1) Tavsiyalar — matn bo'yicha (har bir seed matni noyob).
    seed_texts = [text for _, text in SEED_GENERAL_RECOMMENDATIONS]
    seed_texts += [text for _, _, text in SEED_COMPETENCY_RECOMMENDATIONS]
    op.execute(
        _recommendations_table.delete().where(
            _recommendations_table.c.text.in_(seed_texts)
        )
    )

    # 2) Kompetensiyalar — nom bo'yicha.
    op.execute(
        _competencies_table.delete().where(
            _competencies_table.c.name.in_([name for name, _ in SEED_COMPETENCIES])
        )
    )

    # 3) Rollar — nom bo'yicha.
    op.execute(
        _roles_table.delete().where(_roles_table.c.name.in_(list(SEED_ROLES)))
    )
