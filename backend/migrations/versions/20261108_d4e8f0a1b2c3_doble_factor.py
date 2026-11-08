"""doble factor

Revision ID: d4e8f0a1b2c3
Revises: c3d9e1f2a7b4
Create Date: 2026-11-08 09:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4e8f0a1b2c3'
down_revision: Union[str, Sequence[str], None] = 'c3d9e1f2a7b4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('usuario', sa.Column('totp_secreto', sa.Text(), nullable=True))
    op.add_column('usuario', sa.Column('totp_activo_en', sa.DateTime(timezone=True), nullable=True))
    op.add_column('usuario', sa.Column('totp_ultimo_paso', sa.BigInteger(), nullable=True))
    op.add_column('usuario', sa.Column('codigos_respaldo', sa.JSON(), nullable=True))
    op.add_column('empresa', sa.Column('exigir_2fa', sa.Boolean(), server_default='false', nullable=False))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('empresa', 'exigir_2fa')
    op.drop_column('usuario', 'codigos_respaldo')
    op.drop_column('usuario', 'totp_ultimo_paso')
    op.drop_column('usuario', 'totp_activo_en')
    op.drop_column('usuario', 'totp_secreto')
