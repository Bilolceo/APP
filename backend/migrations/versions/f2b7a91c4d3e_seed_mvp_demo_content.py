"""seed — MVP demo foydalanuvchi va diagnostika testi.

Revision ID: f2b7a91c4d3e
Revises: e5aebbb33974
Create Date: 2026-06-05 13:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f2b7a91c4d3e"
down_revision: Union[str, Sequence[str], None] = "e5aebbb33974"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


DEMO_PHONE = "+998901112236"
DEMO_PASSWORD = "secret123"
DEMO_USER_NAME = "Demo Rahbar"
DEMO_TEST_TITLE = "MVP diagnostika demo testi"

# `secret123` uchun argon2id hash. Ochiq parol faqat demo qo'llanmada beriladi.
DEMO_PASSWORD_HASH = (
    "$argon2id$v=19$m=65536,t=3,p=4$GINw7v2/d87ZG8MYI+Qcww$"
    "SV4oSfYEXUFDSDqmtURMm8ndVpXHQntfM4rk0aHilIg"
)

DEMO_REGION = "Toshkent shahri"
DEMO_ORGANIZATION = "Demo MTT"

DEMO_QUESTIONS = (
    {
        "competency": "Boshqaruv madaniyati",
        "text": "Rahbar muhim qaror qabul qilishdan oldin nimalarga tayanishi kerak?",
        "type": "cognitive",
        "order": 1,
        "answers": (
            ("Faqat shaxsiy taxminiga", False, "0.00"),
            ("Jamoa fikri, dalil va me'yoriy hujjatlarga", True, "10.00"),
            ("Faqat tezkor buyruqqa", False, "2.00"),
        ),
    },
    {
        "competency": "Jamoaviy ishlash",
        "text": "Jamoada ochiq muloqot va teskari aloqa madaniyati qanchalik yo'lga qo'yilgan?",
        "type": "likert",
        "order": 2,
        "answers": (),
    },
    {
        "competency": "Pedagogik jarayonni tashkil etish",
        "text": "Ta'lim-tarbiya jarayoni sifati pasaysa, eng to'g'ri birinchi qadam qaysi?",
        "type": "situational",
        "order": 3,
        "answers": (
            ("Muammoni faqat ijrochiga yuklash", False, "1.00"),
            ("Kuzatuv o'tkazib, sabablarni tahlil qilish va reja tuzish", True, "10.00"),
            ("Hech narsa qilmasdan kutish", False, "0.00"),
        ),
    },
    {
        "competency": "Innovatsion faoliyat",
        "text": "Siz muassasada yangi pedagogik texnologiyalarni sinovdan o'tkazishga qanchalik tayyorsiz?",
        "type": "likert",
        "order": 4,
        "answers": (),
    },
    {
        "competency": "Hujjatlar bilan ishlash",
        "text": "Hisobot va hujjat aylanishida eng muhim tamoyil qaysi?",
        "type": "cognitive",
        "order": 5,
        "answers": (
            ("Aniqlik, muddat va izchillik", True, "10.00"),
            ("Faqat ko'p hujjat yig'ish", False, "2.00"),
            ("Hujjatlarni keyinga qoldirish", False, "0.00"),
        ),
    },
    {
        "competency": "Strategik rejalashtirish",
        "text": "Muassasa rivojlanish maqsadlari va ustuvor yo'nalishlari qanchalik aniq belgilangan?",
        "type": "likert",
        "order": 6,
        "answers": (),
    },
)


def _scalar(bind: sa.engine.Connection, sql: str, **params):
    return bind.execute(sa.text(sql), params).scalar()


def _ensure_role(bind: sa.engine.Connection, name: str) -> int:
    role_id = _scalar(bind, "SELECT id FROM roles WHERE name = :name", name=name)
    if role_id is None:
        bind.execute(sa.text("INSERT INTO roles (name) VALUES (:name)"), {"name": name})
        role_id = _scalar(bind, "SELECT id FROM roles WHERE name = :name", name=name)
    return int(role_id)


def _ensure_region(bind: sa.engine.Connection) -> int:
    region_id = _scalar(
        bind, "SELECT id FROM regions WHERE name = :name", name=DEMO_REGION
    )
    if region_id is None:
        bind.execute(
            sa.text("INSERT INTO regions (name) VALUES (:name)"),
            {"name": DEMO_REGION},
        )
        region_id = _scalar(
            bind, "SELECT id FROM regions WHERE name = :name", name=DEMO_REGION
        )
    return int(region_id)


def _ensure_organization(bind: sa.engine.Connection, region_id: int) -> int:
    org_id = _scalar(
        bind,
        "SELECT id FROM organizations WHERE name = :name",
        name=DEMO_ORGANIZATION,
    )
    if org_id is None:
        bind.execute(
            sa.text(
                """
                INSERT INTO organizations (name, region_id, org_type)
                VALUES (:name, :region_id, :org_type)
                """
            ),
            {
                "name": DEMO_ORGANIZATION,
                "region_id": region_id,
                "org_type": "Maktabgacha ta'lim tashkiloti",
            },
        )
        org_id = _scalar(
            bind,
            "SELECT id FROM organizations WHERE name = :name",
            name=DEMO_ORGANIZATION,
        )
    return int(org_id)


def _ensure_demo_user(
    bind: sa.engine.Connection, *, role_id: int, region_id: int, organization_id: int
) -> None:
    exists = _scalar(
        bind, "SELECT id FROM users WHERE phone = :phone", phone=DEMO_PHONE
    )
    if exists is None:
        bind.execute(
            sa.text(
                """
                INSERT INTO users (
                    full_name, phone, password_hash, role_id, organization_id,
                    region_id, position, experience_years, education_level, org_type
                )
                VALUES (
                    :full_name, :phone, :password_hash, :role_id,
                    :organization_id, :region_id, :position, :experience_years,
                    :education_level, :org_type
                )
                """
            ),
            {
                "full_name": DEMO_USER_NAME,
                "phone": DEMO_PHONE,
                "password_hash": DEMO_PASSWORD_HASH,
                "role_id": role_id,
                "organization_id": organization_id,
                "region_id": region_id,
                "position": "MTT rahbari",
                "experience_years": 5,
                "education_level": "Oliy",
                "org_type": "Maktabgacha ta'lim tashkiloti",
            },
        )
    else:
        bind.execute(
            sa.text(
                """
                UPDATE users
                SET role_id = :role_id,
                    organization_id = COALESCE(organization_id, :organization_id),
                    region_id = COALESCE(region_id, :region_id),
                    position = COALESCE(position, :position),
                    experience_years = COALESCE(experience_years, :experience_years),
                    education_level = COALESCE(education_level, :education_level),
                    org_type = COALESCE(org_type, :org_type)
                WHERE phone = :phone
                """
            ),
            {
                "phone": DEMO_PHONE,
                "role_id": role_id,
                "organization_id": organization_id,
                "region_id": region_id,
                "position": "MTT rahbari",
                "experience_years": 5,
                "education_level": "Oliy",
                "org_type": "Maktabgacha ta'lim tashkiloti",
            },
        )


def _competency_ids(bind: sa.engine.Connection) -> dict[str, int]:
    rows = bind.execute(sa.text("SELECT id, name FROM competencies")).fetchall()
    return {str(name): int(cid) for cid, name in rows}


def _ensure_demo_test(bind: sa.engine.Connection) -> int:
    test_id = _scalar(
        bind,
        "SELECT id FROM tests WHERE title = :title",
        title=DEMO_TEST_TITLE,
    )
    if test_id is None:
        bind.execute(
            sa.text(
                """
                INSERT INTO tests (title, description, category, duration_minutes, is_active)
                VALUES (:title, :description, :category, :duration_minutes, true)
                """
            ),
            {
                "title": DEMO_TEST_TITLE,
                "description": (
                    "MVP uchun tayyor demo test: variantli va Likert savollar "
                    "orqali asosiy kompetensiyalarni baholaydi."
                ),
                "category": "kompetensiya",
                "duration_minutes": 30,
            },
        )
        test_id = _scalar(
            bind, "SELECT id FROM tests WHERE title = :title", title=DEMO_TEST_TITLE
        )
    else:
        bind.execute(
            sa.text("UPDATE tests SET is_active = true WHERE id = :test_id"),
            {"test_id": test_id},
        )
    return int(test_id)


def _ensure_questions(bind: sa.engine.Connection, *, test_id: int) -> None:
    comp_ids = _competency_ids(bind)
    for item in DEMO_QUESTIONS:
        question_id = _scalar(
            bind,
            """
            SELECT id FROM questions
            WHERE test_id = :test_id AND order_index = :order_index
            """,
            test_id=test_id,
            order_index=item["order"],
        )
        if question_id is None:
            bind.execute(
                sa.text(
                    """
                    INSERT INTO questions (
                        test_id, competency_id, question_text, question_type,
                        score, order_index
                    )
                    VALUES (
                        :test_id, :competency_id, :question_text, :question_type,
                        :score, :order_index
                    )
                    """
                ),
                {
                    "test_id": test_id,
                    "competency_id": comp_ids.get(str(item["competency"])),
                    "question_text": item["text"],
                    "question_type": item["type"],
                    "score": "10.00",
                    "order_index": item["order"],
                },
            )
            question_id = _scalar(
                bind,
                """
                SELECT id FROM questions
                WHERE test_id = :test_id AND order_index = :order_index
                """,
                test_id=test_id,
                order_index=item["order"],
            )

        question_id = int(question_id)
        for answer_text, is_correct, score in item["answers"]:
            answer_exists = _scalar(
                bind,
                """
                SELECT id FROM answers
                WHERE question_id = :question_id AND answer_text = :answer_text
                """,
                question_id=question_id,
                answer_text=answer_text,
            )
            if answer_exists is None:
                bind.execute(
                    sa.text(
                        """
                        INSERT INTO answers (question_id, answer_text, is_correct, score)
                        VALUES (:question_id, :answer_text, :is_correct, :score)
                        """
                    ),
                    {
                        "question_id": question_id,
                        "answer_text": answer_text,
                        "is_correct": is_correct,
                        "score": score,
                    },
                )


def upgrade() -> None:
    bind = op.get_bind()
    role_id = _ensure_role(bind, "Rahbar")
    region_id = _ensure_region(bind)
    organization_id = _ensure_organization(bind, region_id)
    _ensure_demo_user(
        bind,
        role_id=role_id,
        region_id=region_id,
        organization_id=organization_id,
    )
    test_id = _ensure_demo_test(bind)
    _ensure_questions(bind, test_id=test_id)


def downgrade() -> None:
    bind = op.get_bind()
    test_id = _scalar(
        bind, "SELECT id FROM tests WHERE title = :title", title=DEMO_TEST_TITLE
    )
    if test_id is not None:
        question_ids = [
            row[0]
            for row in bind.execute(
                sa.text("SELECT id FROM questions WHERE test_id = :test_id"),
                {"test_id": test_id},
            )
        ]
        for question_id in question_ids:
            bind.execute(
                sa.text("DELETE FROM answers WHERE question_id = :question_id"),
                {"question_id": question_id},
            )
        bind.execute(
            sa.text("DELETE FROM questions WHERE test_id = :test_id"),
            {"test_id": test_id},
        )
        bind.execute(sa.text("DELETE FROM tests WHERE id = :test_id"), {"test_id": test_id})
