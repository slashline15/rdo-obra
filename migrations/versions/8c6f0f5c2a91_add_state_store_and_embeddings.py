"""add_state_store_and_embeddings

Revision ID: 8c6f0f5c2a91
Revises: f74a0f9f9a61
Create Date: 2026-04-11 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector


revision: str = "8c6f0f5c2a91"
down_revision: Union[str, Sequence[str], None] = "f74a0f9f9a61"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "conversation_states",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("channel", sa.String(length=20), nullable=False),
        sa.Column("scope_key", sa.String(length=120), nullable=False),
        sa.Column("state_type", sa.String(length=50), nullable=False),
        sa.Column("state_token", sa.String(length=64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("text_original", sa.Text(), nullable=True),
        sa.Column("source_message_id", sa.String(length=120), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("consumed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
        sa.UniqueConstraint("scope_key", name="uq_conversation_states_scope_key"),
        sa.UniqueConstraint("state_token", name="uq_conversation_states_state_token"),
    )
    op.create_index("ix_conversation_states_channel", "conversation_states", ["channel"])
    op.create_index("ix_conversation_states_state_type", "conversation_states", ["state_type"])
    op.create_index("ix_conversation_states_expires_at", "conversation_states", ["expires_at"])

    op.create_table(
        "atividade_embeddings",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("obra_id", sa.Integer(), sa.ForeignKey("obras.id"), nullable=False),
        sa.Column("atividade_id", sa.Integer(), sa.ForeignKey("atividades.id"), nullable=False),
        sa.Column("texto_canonico", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(1024), nullable=True),
        sa.Column(
            "embedding_model",
            sa.String(length=100),
            nullable=False,
            server_default=sa.text("'qwen3-embedding:0.6b'"),
        ),
        sa.Column("embedding_dim", sa.Integer(), nullable=False, server_default=sa.text("1024")),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
        sa.UniqueConstraint("atividade_id", name="uq_atividade_embeddings_atividade_id"),
    )
    op.create_index("ix_atividade_embeddings_obra_id", "atividade_embeddings", ["obra_id"])
    op.create_index(
        "ix_atividade_embeddings_embedding_hnsw",
        "atividade_embeddings",
        ["embedding"],
        postgresql_using="hnsw",
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )


def downgrade() -> None:
    op.drop_index("ix_atividade_embeddings_embedding_hnsw", table_name="atividade_embeddings")
    op.drop_index("ix_atividade_embeddings_obra_id", table_name="atividade_embeddings")
    op.drop_table("atividade_embeddings")

    op.drop_index("ix_conversation_states_expires_at", table_name="conversation_states")
    op.drop_index("ix_conversation_states_state_type", table_name="conversation_states")
    op.drop_index("ix_conversation_states_channel", table_name="conversation_states")
    op.drop_table("conversation_states")
