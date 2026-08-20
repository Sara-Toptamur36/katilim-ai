"""Alembic ortam yapilandirmasi.

Veritabani adresi ORTAM DEGISKENINDEN okunur, alembic.ini'ye yazilmaz.
Boylece parola repoya girmez (bkz. .gitignore -> .env).
"""

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# Projedeki modelleri autogenerate'in gorebilmesi icin
from api.models import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def veritabani_adresi() -> str:
    """Once DATABASE_URL ortam degiskeni, yoksa yerel gelistirme varsayilani.

    Varsayilan yalnizca docker-compose ile ayaga kalkan YEREL ortam icindir.
    """
    return os.environ.get(
        "DATABASE_URL",
        "postgresql+psycopg://katilim:katilim_dev@localhost:5432/katilimai",
    )


def run_migrations_offline() -> None:
    """Baglanti kurmadan, SQL betigi uretme modu."""
    context.configure(
        url=veritabani_adresi(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Gercek veritabanina baglanarak calistirma modu."""
    bolum = config.get_section(config.config_ini_section, {})
    bolum["sqlalchemy.url"] = veritabani_adresi()

    # connect_timeout: api/db.py ile ayni duzeltme (DENETIM BULGUSU, kuru
    # prova 20 Agustos) - "localhost" bu makinede once IPv6 (::1) adresini
    # deniyor, orada dinleyen olmadigi icin Windows'ta bu deneme saniyeler
    # yerine DAKIKALARCA takiliyor (varsayilan isletim sistemi baglanti
    # zaman asimi). connect_timeout olmadan "alembic upgrade head" ve
    # "alembic current" 60 sn'lik subprocess zaman asimini bile asip
    # basarisiz oluyordu; IPv4'e (127.0.0.1) dusmesi zaten ~saniyeler
    # icinde oluyor, sadece IPv6 denemesinin kendisi cok uzun suruyor.
    connectable = engine_from_config(
        bolum,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        connect_args={"connect_timeout": 2},
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
