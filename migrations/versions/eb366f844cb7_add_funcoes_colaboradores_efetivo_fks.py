"""add_funcoes_colaboradores_efetivo_fks

Revision ID: eb366f844cb7
Revises: 1c898ef1db20
Create Date: 2026-04-14 02:09:24.673889

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'eb366f844cb7'
down_revision: Union[str, Sequence[str], None] = '1c898ef1db20'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Adiciona FKs de funcao e colaborador + campo observacao_interna ao efetivo."""
    op.add_column('efetivo', sa.Column('funcao_id', sa.Integer(), nullable=True))
    op.add_column('efetivo', sa.Column('colaborador_id', sa.Integer(), nullable=True))
    op.add_column('efetivo', sa.Column('observacao_interna', sa.Text(), nullable=True))
    op.create_foreign_key(
        'fk_efetivo_funcao_id', 'efetivo', 'funcoes',
        ['funcao_id'], ['id']
    )
    op.create_foreign_key(
        'fk_efetivo_colaborador_id', 'efetivo', 'colaboradores',
        ['colaborador_id'], ['id']
    )


def downgrade() -> None:
    """Remove FKs e colunas adicionadas."""
    op.drop_constraint('fk_efetivo_colaborador_id', 'efetivo', type_='foreignkey')
    op.drop_constraint('fk_efetivo_funcao_id', 'efetivo', type_='foreignkey')
    op.drop_column('efetivo', 'observacao_interna')
    op.drop_column('efetivo', 'colaborador_id')
    op.drop_column('efetivo', 'funcao_id')
