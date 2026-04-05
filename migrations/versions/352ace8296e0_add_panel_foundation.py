"""add_panel_foundation

Revision ID: 352ace8296e0
Revises: 7f3b2a1c9d10
Create Date: 2026-04-05 10:55:41.834549

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '352ace8296e0'
down_revision: Union[str, Sequence[str], None] = '7f3b2a1c9d10'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # --- Enums ---
    diariostatus = sa.Enum('rascunho', 'em_revisao', 'aprovado', 'reaberto', name='diariostatus')
    diariostatus.create(op.get_bind(), checkfirst=True)

    alertaseveridade = sa.Enum('alta', 'media', 'baixa', name='alertaseveridade')
    alertaseveridade.create(op.get_bind(), checkfirst=True)

    # --- Usuario: add email + senha_hash ---
    op.add_column('usuarios', sa.Column('email', sa.String(length=255), nullable=True))
    op.add_column('usuarios', sa.Column('senha_hash', sa.String(length=255), nullable=True))
    op.create_unique_constraint('uq_usuarios_email', 'usuarios', ['email'])

    # --- Obras: add usuario_admin FK (if not already present) ---
    # May already exist from previous create_all, so use checkfirst logic
    try:
        op.add_column('obras', sa.Column('usuario_admin', sa.Integer(), nullable=True))
        op.create_foreign_key('fk_obras_usuario_admin', 'obras', 'usuarios', ['usuario_admin'], ['id'])
    except Exception:
        pass  # column may already exist from init_db

    # --- diarios_dia ---
    op.create_table(
        'diarios_dia',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('obra_id', sa.Integer(), sa.ForeignKey('obras.id'), nullable=False),
        sa.Column('data', sa.Date(), nullable=False),
        sa.Column('status', diariostatus, server_default='rascunho'),
        sa.Column('submetido_por_id', sa.Integer(), sa.ForeignKey('usuarios.id'), nullable=True),
        sa.Column('submetido_em', sa.DateTime(), nullable=True),
        sa.Column('aprovado_por_id', sa.Integer(), sa.ForeignKey('usuarios.id'), nullable=True),
        sa.Column('aprovado_em', sa.DateTime(), nullable=True),
        sa.Column('observacao_aprovacao', sa.Text(), nullable=True),
        sa.Column('pdf_path', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now()),
        sa.UniqueConstraint('obra_id', 'data', name='uq_diario_dia'),
    )

    # --- audit_log ---
    op.create_table(
        'audit_log',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('obra_id', sa.Integer(), sa.ForeignKey('obras.id'), nullable=False),
        sa.Column('data_ref', sa.Date(), nullable=False),
        sa.Column('tabela', sa.String(50), nullable=False),
        sa.Column('registro_id', sa.Integer(), nullable=False),
        sa.Column('campo', sa.String(100), nullable=False),
        sa.Column('valor_anterior', sa.Text(), nullable=True),
        sa.Column('valor_novo', sa.Text(), nullable=True),
        sa.Column('usuario_id', sa.Integer(), sa.ForeignKey('usuarios.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index('ix_audit_log_obra_data', 'audit_log', ['obra_id', 'data_ref'])

    # --- alertas ---
    op.create_table(
        'alertas',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('obra_id', sa.Integer(), sa.ForeignKey('obras.id'), nullable=False),
        sa.Column('data', sa.Date(), nullable=False),
        sa.Column('regra', sa.String(50), nullable=False),
        sa.Column('severidade', alertaseveridade, nullable=False),
        sa.Column('mensagem', sa.Text(), nullable=False),
        sa.Column('resolvido', sa.Boolean(), server_default='false'),
        sa.Column('resolvido_por_id', sa.Integer(), sa.ForeignKey('usuarios.id'), nullable=True),
        sa.Column('resolvido_em', sa.DateTime(), nullable=True),
        sa.Column('dados_contexto', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index('ix_alertas_obra_data', 'alertas', ['obra_id', 'data', 'resolvido'])

    # --- Performance indexes on existing tables ---
    op.create_index('ix_efetivo_obra_data', 'efetivo', ['obra_id', 'data'])
    op.create_index('ix_anotacoes_obra_data', 'anotacoes', ['obra_id', 'data'])
    op.create_index('ix_materiais_obra_data', 'materiais', ['obra_id', 'data'])
    op.create_index('ix_equipamentos_obra_data', 'equipamentos', ['obra_id', 'data'])
    op.create_index('ix_clima_obra_data', 'clima', ['obra_id', 'data'])
    op.create_index('ix_fotos_obra_data', 'fotos', ['obra_id', 'data'])
    op.create_index('ix_atividades_obra_status', 'atividades', ['obra_id', 'status'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_atividades_obra_status', 'atividades')
    op.drop_index('ix_fotos_obra_data', 'fotos')
    op.drop_index('ix_clima_obra_data', 'clima')
    op.drop_index('ix_equipamentos_obra_data', 'equipamentos')
    op.drop_index('ix_materiais_obra_data', 'materiais')
    op.drop_index('ix_anotacoes_obra_data', 'anotacoes')
    op.drop_index('ix_efetivo_obra_data', 'efetivo')
    op.drop_table('alertas')
    op.drop_index('ix_audit_log_obra_data', 'audit_log')
    op.drop_table('audit_log')
    op.drop_table('diarios_dia')
    op.drop_constraint('uq_usuarios_email', 'usuarios', type_='unique')
    op.drop_column('usuarios', 'senha_hash')
    op.drop_column('usuarios', 'email')
    try:
        op.drop_constraint('fk_obras_usuario_admin', 'obras', type_='foreignkey')
        op.drop_column('obras', 'usuario_admin')
    except Exception:
        pass

    sa.Enum(name='alertaseveridade').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='diariostatus').drop(op.get_bind(), checkfirst=True)
