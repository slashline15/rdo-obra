"""create_solicitacoes_cadastro

Revision ID: 7f3b2a1c9d10
Revises: c9a2f8d11e44
Create Date: 2026-04-05 13:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7f3b2a1c9d10'
down_revision: Union[str, Sequence[str], None] = 'c9a2f8d11e44'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'solicitacoes_cadastro',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('obra_id', sa.Integer(), nullable=False),
        sa.Column('solicitante_chat_id', sa.String(length=20), nullable=False),
        sa.Column('solicitante_nome', sa.String(length=255), nullable=True),
        sa.Column('solicitante_username', sa.String(length=255), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='pendente'),
        sa.Column('admin_decisor_id', sa.Integer(), nullable=True),
        sa.Column('observacao', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['admin_decisor_id'], ['usuarios.id']),
        sa.ForeignKeyConstraint(['obra_id'], ['obras.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_solicitacoes_cadastro_id'), 'solicitacoes_cadastro', ['id'], unique=False)
    op.create_index(op.f('ix_solicitacoes_cadastro_solicitante_chat_id'), 'solicitacoes_cadastro', ['solicitante_chat_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_solicitacoes_cadastro_solicitante_chat_id'), table_name='solicitacoes_cadastro')
    op.drop_index(op.f('ix_solicitacoes_cadastro_id'), table_name='solicitacoes_cadastro')
    op.drop_table('solicitacoes_cadastro')
