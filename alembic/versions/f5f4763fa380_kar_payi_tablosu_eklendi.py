"""kar payi tablosu eklendi

Revision ID: f5f4763fa380
Revises: b70604b6218d
Create Date: 2026-08-19 23:58:34.733163

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f5f4763fa380'
down_revision: Union[str, Sequence[str], None] = 'b70604b6218d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('kampanyalar', sa.Column('kar_payi_tablosu', sa.JSON(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('kampanyalar', 'kar_payi_tablosu')
