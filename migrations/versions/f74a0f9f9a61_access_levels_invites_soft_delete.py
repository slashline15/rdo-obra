"""access_levels_invites_soft_delete

Revision ID: f74a0f9f9a61
Revises: 352ace8296e0
Create Date: 2026-04-07 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f74a0f9f9a61"
down_revision: Union[str, Sequence[str], None] = "352ace8296e0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("usuarios", sa.Column("nivel_acesso", sa.Integer(), nullable=True))
    op.add_column("usuarios", sa.Column("pode_aprovar_diario", sa.Boolean(), nullable=True))
    op.add_column("usuarios", sa.Column("registro_profissional", sa.String(length=255), nullable=True))
    op.add_column("usuarios", sa.Column("empresa_vinculada", sa.String(length=255), nullable=True))

    op.execute(
        """
        UPDATE usuarios
        SET nivel_acesso = CASE
            WHEN role = 'admin' THEN 1
            WHEN role IN ('responsavel', 'engenheiro', 'fiscal') THEN 2
            ELSE 3
        END
        """
    )
    op.execute(
        """
        UPDATE usuarios
        SET pode_aprovar_diario = CASE
            WHEN role = 'admin' THEN true
            ELSE false
        END
        """
    )
    op.alter_column("usuarios", "nivel_acesso", nullable=False)
    op.alter_column("usuarios", "pode_aprovar_diario", nullable=False)

    op.add_column("diarios_dia", sa.Column("deletado_em", sa.DateTime(), nullable=True))
    op.add_column("diarios_dia", sa.Column("deletado_por_id", sa.Integer(), nullable=True))
    op.add_column("diarios_dia", sa.Column("motivo_exclusao", sa.Text(), nullable=True))
    op.create_foreign_key(
        "fk_diarios_dia_deletado_por",
        "diarios_dia",
        "usuarios",
        ["deletado_por_id"],
        ["id"],
    )

    op.create_table(
        "convites_acesso",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("obra_id", sa.Integer(), sa.ForeignKey("obras.id"), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("telefone", sa.String(length=20), nullable=True),
        sa.Column("role", sa.String(length=50), nullable=False),
        sa.Column("nivel_acesso", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("pode_aprovar_diario", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("cargo", sa.String(length=255), nullable=True),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pendente"),
        sa.Column("request_metadata", sa.JSON(), nullable=True),
        sa.Column("criado_por_id", sa.Integer(), sa.ForeignKey("usuarios.id"), nullable=False),
        sa.Column("usado_por_id", sa.Integer(), sa.ForeignKey("usuarios.id"), nullable=True),
        sa.Column("expira_em", sa.DateTime(), nullable=False),
        sa.Column("usado_em", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.UniqueConstraint("token_hash", name="uq_convites_acesso_token_hash"),
    )
    op.create_index("ix_convites_acesso_email", "convites_acesso", ["email"])


def downgrade() -> None:
    op.drop_index("ix_convites_acesso_email", table_name="convites_acesso")
    op.drop_table("convites_acesso")
    op.drop_constraint("fk_diarios_dia_deletado_por", "diarios_dia", type_="foreignkey")
    op.drop_column("diarios_dia", "motivo_exclusao")
    op.drop_column("diarios_dia", "deletado_por_id")
    op.drop_column("diarios_dia", "deletado_em")
    op.drop_column("usuarios", "empresa_vinculada")
    op.drop_column("usuarios", "registro_profissional")
    op.drop_column("usuarios", "pode_aprovar_diario")
    op.drop_column("usuarios", "nivel_acesso")
