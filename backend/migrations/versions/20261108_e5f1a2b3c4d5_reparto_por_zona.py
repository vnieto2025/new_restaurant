"""reparto del pedido por zona

Revision ID: e5f1a2b3c4d5
Revises: d4e8f0a1b2c3
Create Date: 2026-11-08 18:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e5f1a2b3c4d5'
down_revision: Union[str, Sequence[str], None] = 'd4e8f0a1b2c3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('zona', sa.Column('reparto', sa.String(length=10), server_default='zona', nullable=False))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('zona', 'reparto')
