"""sikayet denetim alanlari eklendi

Complaint Insight plan revizyonu (26 Agustos 2026) - P0 kalemleri:
  - icerik_hash / yineleme_supheli : dedup/spam ISARETLEME (engelleme
    degil), complaint/toplama.py::_dedup_anahtari
  - tema_surumu                    : hangi kural setiyle siniflandirildi,
    complaint/tema_siniflandirici.py::TEMA_SURUMU
  - cozum_durumu                   : sikayet cozum/isleyis durumu - HENUZ
    HICBIR YOL DOLDURMAZ, Faz 2'ye kadar DAIMA NULL kalir

Hepsi nullable: mevcut (sentetik/bos) kayitlar bu sutunlar olmadan
yazilmis olsa da gecerliligini korumali - "acik" gibi bir varsayim
UYDURULMAZ (bkz. api/models.py::Sikayet docstring'i).

Revision ID: 4fae96f0556c
Revises: 348b48b28c29
Create Date: 2026-08-27 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4fae96f0556c'
down_revision: Union[str, Sequence[str], None] = '348b48b28c29'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('sikayetler', sa.Column('icerik_hash', sa.String(length=64), nullable=True))
    op.add_column('sikayetler', sa.Column('yineleme_supheli', sa.Boolean(), nullable=True))
    op.add_column('sikayetler', sa.Column('tema_surumu', sa.String(length=20), nullable=True))
    op.add_column('sikayetler', sa.Column('cozum_durumu', sa.String(length=30), nullable=True))
    op.create_index(op.f('ix_sikayetler_icerik_hash'), 'sikayetler', ['icerik_hash'])
    op.create_index(op.f('ix_sikayetler_yineleme_supheli'), 'sikayetler', ['yineleme_supheli'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_sikayetler_yineleme_supheli'), table_name='sikayetler')
    op.drop_index(op.f('ix_sikayetler_icerik_hash'), table_name='sikayetler')
    op.drop_column('sikayetler', 'cozum_durumu')
    op.drop_column('sikayetler', 'tema_surumu')
    op.drop_column('sikayetler', 'yineleme_supheli')
    op.drop_column('sikayetler', 'icerik_hash')
