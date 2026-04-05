"""add_usuario_admin_em_obras

Revision ID: c9a2f8d11e44
Revises: b3cfdd8a99bb
Create Date: 2026-04-05 12:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c9a2f8d11e44'
down_revision: Union[str, Sequence[str], None] = 'b3cfdd8a99bb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('obras', sa.Column('usuario_admin', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_obras_usuario_admin_usuarios',
        'obras',
        'usuarios',
        ['usuario_admin'],
        ['id'],
        ondelete='SET NULL'
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('fk_obras_usuario_admin_usuarios', 'obras', type_='foreignkey')
    op.drop_column('obras', 'usuario_admin')
