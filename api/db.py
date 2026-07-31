"""Veritabani baglantisi (SQLAlchemy engine + oturum).

api/models.py ORM siniflarini tanimlar, bu dosya onlari calistiran
baglantiyi kurar. DATABASE_URL ortam degiskeni yoksa docker-compose.yml'deki
yerel gelistirme varsayilanina duser (Zeynep Veri Toplama Rehberi Bolum 8.3
ile ayni desen).
"""

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+psycopg://katilim:katilim_dev@localhost:5432/katilimai",
)

# connect_timeout: Postgres kapaliyken (ozellikle Docker Desktop'ta port
# yonlendirmesi konteyner durduktan sonra da bir sure "acik" gorunebiliyor)
# baglanti denemesinin saniyeler yerine ANINDA basarisiz olmasini saglar.
engine = create_engine(
    DATABASE_URL, pool_pre_ping=True, connect_args={"connect_timeout": 2}
)
OturumYerel = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def oturum_al():
    """FastAPI bagimliligi olarak kullanilir: Depends(oturum_al)."""
    oturum = OturumYerel()
    try:
        yield oturum
    finally:
        oturum.close()
