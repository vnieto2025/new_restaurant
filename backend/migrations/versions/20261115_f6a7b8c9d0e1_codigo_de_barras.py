"""codigo de barras de productos

Revision ID: f6a7b8c9d0e1
Revises: e5f1a2b3c4d5
Create Date: 2026-11-15 22:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f6a7b8c9d0e1'
down_revision: Union[str, Sequence[str], None] = 'e5f1a2b3c4d5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('producto', sa.Column('codigo_barras', sa.String(length=40), nullable=True))
    op.create_index('uq_producto_codigo_barras', 'producto', ['restaurante_id', 'codigo_barras'], unique=True,
                    postgresql_where=sa.text('codigo_barras IS NOT NULL AND eliminado_en IS NULL'))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('uq_producto_codigo_barras', table_name='producto')
    op.drop_column('producto', 'codigo_barras')
