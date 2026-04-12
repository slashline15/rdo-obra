"""Busca semântica de atividades com embeddings locais e pgvector."""
from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Any, Iterable, Optional, cast

import httpx
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.time import utc_now
from app.core.vector import vector_literal
from app.models import Atividade, AtividadeEmbedding, AtividadeStatus


STOPWORDS = {
    "a", "ao", "aos", "as", "de", "da", "das", "do", "dos", "e", "em", "no", "na",
    "nos", "nas", "para", "por", "com", "sem", "um", "uma", "uns", "umas", "o", "os",
    "que", "se", "su", "sua", "seu", "hoje", "ontem", "amanha", "amanhã", "vamos",
    "vai", "fazer", "fazendo", "terminar", "concluir", "registrar", "obra", "do", "da",
    "de", "dos", "das", "aqui", "lá", "la", "isso", "essa", "esse", "essa", "frente",
}


@dataclass
class ActivityMatch:
    atividade_id: int
    descricao: str
    score: float
    local: Optional[str] = None
    etapa: Optional[str] = None


@dataclass
class ActivityMatchResult:
    selected: Optional[ActivityMatch]
    candidates: list[ActivityMatch]
    best_score: float = 0.0
    second_score: float = 0.0
    strategy: str = "embedding"

    @property
    def needs_disambiguation(self) -> bool:
        if not self.selected:
            return bool(self.candidates)
        if len(self.candidates) < 2:
            return False
        return (self.best_score < settings.semantic_match_threshold) or (
            (self.best_score - self.second_score) < settings.semantic_match_margin
        )


class ActivitySemanticSearch:
    """Indexa e pesquisa atividades por significado, não só por palavras."""

    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def build_canonical_text(atividade: Atividade) -> str:
        parts = [
            atividade.descricao,
            atividade.local,
            atividade.etapa,
            atividade.observacoes,
            atividade.texto_original,
        ]
        filtered = [str(part).strip() for part in parts if part is not None and str(part).strip()]
        return " | ".join(filtered)

    @staticmethod
    def _normalize_vector(values: Iterable[float]) -> list[float]:
        vector = [float(value) for value in values]
        if len(vector) != settings.embedding_dimensions:
            raise ValueError(
                f"Embedding esperado com {settings.embedding_dimensions} dimensões, recebido {len(vector)}"
            )
        return vector

    @staticmethod
    def _tokenize(text_value: str) -> list[str]:
        tokens = re.findall(r"[a-z0-9áàâãéêíóôõúç]+", text_value.lower())
        return [token for token in tokens if len(token) > 2 and token not in STOPWORDS]

    def _lexical_score(self, query_value: str, candidate: Atividade) -> float:
        canonical = self.build_canonical_text(candidate).lower()
        query_tokens = self._tokenize(query_value)
        query_clean = " ".join(query_tokens)
        candidate_tokens = set(self._tokenize(canonical))
        if not query_clean or not candidate_tokens:
            return 0.0

        query_token_set = set(query_tokens)
        overlap = query_token_set & candidate_tokens
        if not overlap:
            return 0.0

        if query_token_set == candidate_tokens and len(query_tokens) == len(candidate_tokens):
            return 0.99

        coverage = len(overlap) / max(len(query_token_set), 1)
        precision = len(overlap) / max(len(candidate_tokens), 1)
        phrase_match = query_clean in canonical or canonical in query_clean
        score = (coverage * 0.72) + (precision * 0.18)
        if phrase_match:
            score = max(score, 0.98)
        return min(score, 1.0)

    def _lexical_search(self, obra_id: int, text_value: str, limit: int) -> list[ActivityMatch]:
        query = self.db.query(Atividade).filter(
            Atividade.obra_id == obra_id,
            Atividade.status != AtividadeStatus.CONCLUIDA,
        ).all()

        matches: list[ActivityMatch] = []
        for atividade in query:
            score = self._lexical_score(text_value, atividade)
            if score <= 0:
                continue
            matches.append(ActivityMatch(
                atividade_id=cast(int, atividade.id),
                descricao=cast(str, atividade.descricao),
                score=score,
                local=cast(Optional[str], getattr(atividade, "local", None)),
                etapa=cast(Optional[str], getattr(atividade, "etapa", None)),
            ))

        matches.sort(key=lambda item: (item.score, len(item.descricao or ""), -item.atividade_id), reverse=True)
        return matches[:limit]

    def _has_embeddings_for_obra(self, obra_id: int) -> bool:
        return bool(self.db.query(AtividadeEmbedding.id).filter(
            AtividadeEmbedding.obra_id == obra_id
        ).first())

    async def _embed_text(self, text_value: str) -> list[float]:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{settings.ollama_base_url}/api/embed",
                json={
                    "model": settings.embedding_model,
                    "input": text_value,
                },
            )
            response.raise_for_status()
            payload = response.json()

        embeddings = payload.get("embeddings") or payload.get("embedding")
        if isinstance(embeddings, list) and embeddings and isinstance(embeddings[0], list):
            embeddings = embeddings[0]
        if not embeddings:
            raise RuntimeError("Ollama não retornou embeddings")
        return self._normalize_vector(embeddings)

    async def upsert_activity_embedding(self, atividade: Atividade) -> AtividadeEmbedding:
        canonical_text = self.build_canonical_text(atividade)
        embedding = await self._embed_text(canonical_text)

        row = self.db.query(AtividadeEmbedding).filter(
            AtividadeEmbedding.atividade_id == atividade.id
        ).first()
        now = utc_now()
        if row:
            setattr(row, "obra_id", atividade.obra_id)
            setattr(row, "texto_canonico", canonical_text)
            setattr(row, "embedding", embedding)
            setattr(row, "embedding_model", settings.embedding_model)
            setattr(row, "embedding_dim", len(embedding))
            setattr(row, "updated_at", now)
        else:
            row = AtividadeEmbedding(
                obra_id=cast(int, atividade.obra_id),
                atividade_id=cast(int, atividade.id),
                texto_canonico=canonical_text,
                embedding=embedding,
                embedding_model=settings.embedding_model,
                embedding_dim=len(embedding),
            )
            self.db.add(row)

        self.db.commit()
        self.db.refresh(row)
        return row

    def delete_activity_embedding(self, atividade_id: int) -> bool:
        row = self.db.query(AtividadeEmbedding).filter(
            AtividadeEmbedding.atividade_id == atividade_id
        ).first()
        if not row:
            return False
        self.db.delete(row)
        self.db.commit()
        return True

    async def rebuild_obra_index(self, obra_id: int) -> int:
        atividades = self.db.query(Atividade).filter(
            Atividade.obra_id == obra_id,
            Atividade.status != AtividadeStatus.CONCLUIDA,
        ).all()
        count = 0
        for atividade in atividades:
            await self.upsert_activity_embedding(atividade)
            count += 1
        return count

    @staticmethod
    def _cosine_similarity(a: list[float], b: list[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(y * y for y in b))
        if not norm_a or not norm_b:
            return 0.0
        return dot / (norm_a * norm_b)

    def _fallback_search(self, obra_id: int, query_embedding: list[float], limit: int) -> list[ActivityMatch]:
        rows = self.db.query(AtividadeEmbedding, Atividade).join(
            Atividade,
            Atividade.id == AtividadeEmbedding.atividade_id,
        ).filter(
            AtividadeEmbedding.obra_id == obra_id,
            Atividade.status != AtividadeStatus.CONCLUIDA,
        ).all()

        matches: list[ActivityMatch] = []
        for embedding_row, atividade in rows:
            if not embedding_row.embedding:
                continue
            score = self._cosine_similarity(query_embedding, list(embedding_row.embedding))
            matches.append(ActivityMatch(
                atividade_id=cast(int, atividade.id),
                descricao=cast(str, atividade.descricao),
                score=score,
                local=cast(Optional[str], getattr(atividade, "local", None)),
                etapa=cast(Optional[str], getattr(atividade, "etapa", None)),
            ))

        matches.sort(key=lambda item: item.score, reverse=True)
        return matches[:limit]

    def _postgres_search(self, obra_id: int, query_embedding: list[float], limit: int) -> list[ActivityMatch]:
        query_vector = vector_literal(query_embedding)
        rows = self.db.execute(
            text(
                """
                SELECT
                    ae.atividade_id,
                    a.descricao,
                    a.local,
                    a.etapa,
                    1 - (ae.embedding <=> CAST(:query_vector AS vector)) AS score
                FROM atividade_embeddings ae
                JOIN atividades a ON a.id = ae.atividade_id
                WHERE ae.obra_id = :obra_id
                  AND a.status != 'concluida'
                ORDER BY ae.embedding <=> CAST(:query_vector AS vector)
                LIMIT :limit
                """
            ),
            {
                "obra_id": obra_id,
                "query_vector": query_vector,
                "limit": limit,
            },
        ).mappings().all()

        return [
            ActivityMatch(
                atividade_id=row["atividade_id"],
                descricao=row["descricao"],
                score=float(row["score"] or 0.0),
                local=row.get("local"),
                etapa=row.get("etapa"),
            )
            for row in rows
        ]

    async def search(self, obra_id: int, text_value: str, limit: int = 3) -> ActivityMatchResult:
        lexical_candidates = self._lexical_search(obra_id, text_value, limit)
        if lexical_candidates:
            best_lexical = lexical_candidates[0]
            second_lexical = lexical_candidates[1] if len(lexical_candidates) > 1 else None
            if (
                best_lexical.score >= settings.semantic_match_threshold
                and (second_lexical is None or (best_lexical.score - second_lexical.score) >= settings.semantic_match_margin)
            ):
                return ActivityMatchResult(
                    selected=best_lexical,
                    candidates=lexical_candidates,
                    best_score=best_lexical.score,
                    second_score=second_lexical.score if second_lexical else 0.0,
                    strategy="lexical",
                )

        if not self._has_embeddings_for_obra(obra_id):
            if lexical_candidates:
                best = lexical_candidates[0]
                second = lexical_candidates[1] if len(lexical_candidates) > 1 else None
                return ActivityMatchResult(
                    selected=None,
                    candidates=lexical_candidates,
                    best_score=best.score,
                    second_score=second.score if second else 0.0,
                    strategy="lexical",
                )
            return ActivityMatchResult(selected=None, candidates=[], strategy="lexical")

        query_embedding = await self._embed_text(text_value)
        dialect_name = "postgresql" if settings.database_url.startswith("postgresql") else "sqlite"

        try:
            if dialect_name == "postgresql":
                candidates = self._postgres_search(obra_id, query_embedding, limit)
                strategy = "pgvector"
            else:
                candidates = self._fallback_search(obra_id, query_embedding, limit)
                strategy = "python"
        except Exception:
            candidates = self._fallback_search(obra_id, query_embedding, limit)
            strategy = "python-fallback"

        if lexical_candidates and candidates:
            merged: dict[int, ActivityMatch] = {match.atividade_id: match for match in candidates}
            for lexical_match in lexical_candidates:
                existing = merged.get(lexical_match.atividade_id)
                if existing is None:
                    # Candidato lexical não retornado pelo pgvector — incluir
                    merged[lexical_match.atividade_id] = lexical_match
                elif lexical_match.score >= 0.95:
                    # Phrase match confirmado lexicamente supera o embedding
                    merged[lexical_match.atividade_id] = lexical_match
                # Scores intermediários: mantém o embedding (mais confiável semanticamente)
            candidates = sorted(
                merged.values(),
                key=lambda item: item.score,
                reverse=True,
            )[:limit]

        if not candidates:
            return ActivityMatchResult(selected=None, candidates=[], strategy=strategy)

        best = candidates[0]
        second = candidates[1] if len(candidates) > 1 else None
        selected = best if (
            best.score >= settings.semantic_match_threshold
            and (second is None or (best.score - second.score) >= settings.semantic_match_margin)
        ) else None

        return ActivityMatchResult(
            selected=selected,
            candidates=candidates[:limit],
            best_score=best.score,
            second_score=second.score if second else 0.0,
            strategy=strategy,
        )

    def get_activity(self, atividade_id: int) -> Atividade | None:
        return self.db.query(Atividade).filter(Atividade.id == atividade_id).first()
