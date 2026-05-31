"""Alembic muhiti (environment) — loyihaning ORM metama'lumotiga ulangan.

Bu skript Alembic migratsiyalarini ishga tushiradi. U `app.models.base.Base`
metama'lumotini (barcha jadvallar shu reestrda) `target_metadata` sifatida
ishlatadi va ulanish satrini `app.core.config.settings.database_url` dan oladi
(alembic.ini dagi qiymatdan ustun turadi). Shu tarzda migratsiyalar yagona
manbadan (sozlamalar + ORM modellari) boshqariladi.

Bog'liq vazifa: task 2.2 — Alembic migratsiyalari va cheklovlar.
"""

from __future__ import annotations

import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

# Loyiha ildizini (backend/) sys.path ga qo'shamiz, shunda `app` paketi
# import qilinadi (alembic.ini dagi `prepend_sys_path = .` ham buni ta'minlaydi,
# bu esa qo'shimcha kafolat).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings  # noqa: E402
from app.models.base import Base  # noqa: E402

# Barcha ORM modellarini import qilamiz — ular `Base.metadata` ga ro'yxatdan
# o'tishi va autogenerate butun sxemani ko'rishi uchun.
import app.models  # noqa: E402,F401

# Alembic Config obyekti — alembic.ini qiymatlariga kirish beradi.
config = context.config

# Ulanish satrini sozlamalardan o'rnatamiz (maxfiy URL kodga yozilmaydi).
config.set_main_option("sqlalchemy.url", settings.database_url)

# Python logging sozlamasi.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Autogenerate uchun nishon metama'lumot — barcha jadvallar shu reestrda.
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Migratsiyalarni 'offline' rejimda (faqat URL bilan) ishga tushiradi."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Migratsiyalarni 'online' rejimda (Engine va ulanish bilan) ishga tushiradi."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
            # SQLite kabi backendlarda ALTER cheklangan; batch rejim DDL'ni
            # xavfsiz qayta yozadi (ishlab chiqarish PostgreSQL'da ta'sir qilmaydi).
            render_as_batch=connection.dialect.name == "sqlite",
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
