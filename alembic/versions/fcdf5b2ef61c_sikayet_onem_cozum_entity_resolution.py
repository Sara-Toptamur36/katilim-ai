"""sikayet onem/cozum/entity-resolution alanlari eklendi

Complaint Insight plan revizyonu (27 Agustos 2026) - mentor geri bildirimine
yanit (sentetik veriyle olculdu, gercek veri entegre edilmedi):
  - dusuk_bilgi_supheli        : cok kisa/bilgisiz metin ISARETI (silme
                                  degil), complaint/toplama.py::_dusuk_bilgi_supheli_mi
  - onem_derecesi               : YUKSEK/ORTA/DUSUK, complaint/onem_derecesi.py
  - cozum_durumu (mevcut kolon) : ARTIK complaint/cozum_tespiti.py tarafindan
                                   doldurulur - CRM entegrasyonu degil,
                                   metnin kendi ifadesinden tespit
  - banka_eslesti / urun_turu_guveni : uc seviyeli entity resolution'in
    Seviye 1 (banka) ve Seviye 2 (urun turu) sinyalleri - kampanya (Seviye
    3, eslesen_kampanya_id/eslesme_guveni) esik altinda kalsa bile AYRI
    saklanir (bkz. complaint/kampanya_eslestirme.py::EslesmeSonucu)

Hepsi nullable: mevcut (sentetik/bos) kayitlar bu sutunlar olmadan
yazilmis olsa da gecerliligini korumali - "acik"/"ORTA" gibi bir varsayim
UYDURULMAZ (bkz. api/models.py::Sikayet docstring'i). Tablo bu revizyon
sirasinda BOS kalmaya devam ediyor - izin kapisi (complaint/izin_kapisi.py)
hicbir kaynak icin acilmadi, gercek veri toplanmadi.

Revision ID: fcdf5b2ef61c
Revises: 4fae96f0556c
Create Date: 2026-08-27 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fcdf5b2ef61c'
down_revision: Union[str, Sequence[str], None] = '4fae96f0556c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('sikayetler', sa.Column('dusuk_bilgi_supheli', sa.Boolean(), nullable=True))
    op.add_column('sikayetler', sa.Column('onem_derecesi', sa.String(length=10), nullable=True))
    op.add_column('sikayetler', sa.Column('banka_eslesti', sa.Boolean(), nullable=True))
    op.add_column('sikayetler', sa.Column('urun_turu_guveni', sa.Float(), nullable=True))
    op.create_index(op.f('ix_sikayetler_dusuk_bilgi_supheli'), 'sikayetler', ['dusuk_bilgi_supheli'])
    op.create_index(op.f('ix_sikayetler_onem_derecesi'), 'sikayetler', ['onem_derecesi'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_sikayetler_onem_derecesi'), table_name='sikayetler')
    op.drop_index(op.f('ix_sikayetler_dusuk_bilgi_supheli'), table_name='sikayetler')
    op.drop_column('sikayetler', 'urun_turu_guveni')
    op.drop_column('sikayetler', 'banka_eslesti')
    op.drop_column('sikayetler', 'onem_derecesi')
    op.drop_column('sikayetler', 'dusuk_bilgi_supheli')
