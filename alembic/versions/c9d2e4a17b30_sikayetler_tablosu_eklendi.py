"""sikayetler tablosu eklendi

Sikayet verisi kampanya tablosuna KARISMAZ (Rehber_Zeynep_Veri.md kirmizi
cizgisi) - bu yuzden AYRI bir tablodur ve `kampanyalar`a FOREIGN KEY
BILEREK konulmamistir: eslesme silinebilir/duzeltilebilir bir HIPOTEZDIR
(bkz. complaint/kampanya_eslestirme.py), semanin garantisi degil.

Tablo su an BOS kalir: kurumsal/hukuki (KVKK) onay tamamlanmadan veri
ingest edilmez (complaint/izin_kapisi.py). Semayi simdiden kurmak,
onay geldiginde aceleyle sema tasarlamak zorunda kalmamak icindir.

Revision ID: c9d2e4a17b30
Revises: f5f4763fa380
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c9d2e4a17b30"
down_revision: Union[str, Sequence[str], None] = "f5f4763fa380"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "sikayetler",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        # HAM METIN SUTUNU YOKTUR - yalnizca temizlenmis surum saklanir
        # (complaint/pii_temizleme.py, "temizlik kayittan once" cizgisi).
        sa.Column("temiz_metin", sa.String(length=4000), nullable=False),
        sa.Column("pii_bulundu", sa.Boolean(), nullable=True),
        sa.Column("insan_kontrolu_gerekir", sa.Boolean(), nullable=True),
        sa.Column("tema", sa.String(length=50), nullable=True),
        sa.Column("tema_kaniti", sa.String(length=200), nullable=True),
        sa.Column("kaynak", sa.String(length=100), nullable=False),
        sa.Column("izin_onaylayan", sa.String(length=100), nullable=True),
        sa.Column("izin_onay_tarihi", sa.Date(), nullable=True),
        sa.Column("eslesen_kampanya_id", sa.Integer(), nullable=True),
        sa.Column("eslesme_guveni", sa.Float(), nullable=True),
        sa.Column("eslesme_gerekcesi", sa.JSON(), nullable=True),
        sa.Column("sikayet_tarihi", sa.Date(), nullable=True),
        sa.Column(
            "kayit_zamani",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_sikayetler_tema"), "sikayetler", ["tema"])
    op.create_index(op.f("ix_sikayetler_kaynak"), "sikayetler", ["kaynak"])
    op.create_index(
        op.f("ix_sikayetler_sikayet_tarihi"), "sikayetler", ["sikayet_tarihi"]
    )
    op.create_index(
        op.f("ix_sikayetler_eslesen_kampanya_id"), "sikayetler", ["eslesen_kampanya_id"]
    )
    # Insan kontrolu bekleyenleri hizli listelemek icin: PII bulunan her
    # kayit gozden gecirilmeli, bu sorgu operasyonel olarak sik calisir.
    op.create_index(
        op.f("ix_sikayetler_insan_kontrolu_gerekir"),
        "sikayetler",
        ["insan_kontrolu_gerekir"],
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_sikayetler_insan_kontrolu_gerekir"), table_name="sikayetler")
    op.drop_index(op.f("ix_sikayetler_eslesen_kampanya_id"), table_name="sikayetler")
    op.drop_index(op.f("ix_sikayetler_sikayet_tarihi"), table_name="sikayetler")
    op.drop_index(op.f("ix_sikayetler_kaynak"), table_name="sikayetler")
    op.drop_index(op.f("ix_sikayetler_tema"), table_name="sikayetler")
    op.drop_table("sikayetler")
