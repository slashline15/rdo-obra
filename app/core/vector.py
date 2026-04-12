"""Tipos e helpers para embeddings vetoriais com fallback em SQLite."""
from __future__ import annotations

import json
from typing import Sequence

from sqlalchemy import JSON
from sqlalchemy.types import TypeDecorator

try:  # pragma: no cover - dependência opcional em runtime de testes
    from pgvector.sqlalchemy import Vector as PGVector
except Exception:  # pragma: no cover - fallback quando a lib não estiver instalada
    PGVector = None


def vector_literal(values: Sequence[float]) -> str:
    """Serializa lista de floats no literal aceito pelo pgvector."""
    return "[" + ",".join(f"{float(value):.10f}".rstrip("0").rstrip(".") for value in values) + "]"


class VectorEmbeddingType(TypeDecorator):
    """Tipo SQLAlchemy que usa pgvector no Postgres e JSON em SQLite."""

    impl = JSON
    cache_ok = True

    def __init__(self, dimensions: int = 1024):
        super().__init__()
        self.dimensions = dimensions

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            if PGVector is None:
                raise RuntimeError(
                    "pgvector não está instalado. Adicione a dependência para usar embeddings no PostgreSQL."
                )
            return dialect.type_descriptor(PGVector(self.dimensions))
        return dialect.type_descriptor(JSON())

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        sequence = [float(item) for item in value]
        if self.dimensions and len(sequence) != self.dimensions:
            raise ValueError(f"Embedding esperado com {self.dimensions} dimensões, recebido {len(sequence)}")
        return sequence

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, str):
            value = json.loads(value)
        return [float(item) for item in value]

    def copy(self, **kw):
        return VectorEmbeddingType(self.dimensions)
