"""dogrulanan_alanlar eklendi

Revision ID: b70604b6218d
Revises: 3f40c72cb489
Create Date: 2026-08-11 22:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b70604b6218d'
down_revision: Union[str, Sequence[str], None] = '3f40c72cb489'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('kampanyalar', sa.Column('dogrulanan_alanlar', sa.JSON(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('kampanyalar', 'dogrulanan_alanlar')
