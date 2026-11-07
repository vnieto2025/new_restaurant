"""alertas y resumen diario

Revision ID: b7c41e2d9a10
Revises: f4f637d08dd4
Create Date: 2026-11-07 09:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7c41e2d9a10'
down_revision: Union[str, Sequence[str], None] = 'f4f637d08dd4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('restaurante', sa.Column('alertas', sa.JSON(), nullable=True))
    op.add_column('restaurante', sa.Column('resumen_diario', sa.JSON(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('restaurante', 'resumen_diario')
    op.drop_column('restaurante', 'alertas')
