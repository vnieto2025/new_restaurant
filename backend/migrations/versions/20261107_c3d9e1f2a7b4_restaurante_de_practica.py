"""restaurante de practica

Revision ID: c3d9e1f2a7b4
Revises: b7c41e2d9a10
Create Date: 2026-11-07 12:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3d9e1f2a7b4'
down_revision: Union[str, Sequence[str], None] = 'b7c41e2d9a10'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('restaurante', sa.Column('practica_de', sa.BigInteger(), nullable=True))
    op.create_foreign_key('fk_restaurante_practica', 'restaurante', 'restaurante', ['practica_de'], ['id'])
    op.create_unique_constraint('restaurante_practica_de_key', 'restaurante', ['practica_de'])
    op.add_column('cliente', sa.Column('practica_restaurante_id', sa.BigInteger(), nullable=True))
    op.create_foreign_key('fk_cliente_practica', 'cliente', 'restaurante', ['practica_restaurante_id'], ['id'])
    op.drop_constraint('uq_cliente_telefono', 'cliente', type_='unique')
    op.create_index('uq_cliente_telefono', 'cliente', ['empresa_id', 'telefono'], unique=True,
                    postgresql_where=sa.text('practica_restaurante_id IS NULL'))
    op.create_index('uq_cliente_telefono_practica', 'cliente', ['practica_restaurante_id', 'telefono'], unique=True,
                    postgresql_where=sa.text('practica_restaurante_id IS NOT NULL'))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('uq_cliente_telefono_practica', table_name='cliente')
    op.drop_index('uq_cliente_telefono', table_name='cliente')
    op.create_unique_constraint('uq_cliente_telefono', 'cliente', ['empresa_id', 'telefono'])
    op.drop_constraint('fk_cliente_practica', 'cliente', type_='foreignkey')
    op.drop_column('cliente', 'practica_restaurante_id')
    op.drop_constraint('restaurante_practica_de_key', 'restaurante', type_='unique')
    op.drop_constraint('fk_restaurante_practica', 'restaurante', type_='foreignkey')
    op.drop_column('restaurante', 'practica_de')
