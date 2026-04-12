import asyncio
from datetime import date
from typing import cast
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import pytest

from app.database import Base
from app.models import Atividade, AtividadeEmbedding, AtividadeStatus, Obra
from app.services.activity_semantics import ActivitySemanticSearch


def _make_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    return TestingSessionLocal(), engine


def _basis(index: int, dim: int = 1024) -> list[float]:
    vector = [0.0] * dim
    vector[index] = 1.0
    return vector


def _mixed(indices: tuple[int, int], dim: int = 1024) -> list[float]:
    vector = [0.0] * dim
    for index in indices:
        vector[index] = 1.0
    return vector


def test_busca_semantica_autoseleciona_candidato_claro(monkeypatch):
    db, engine = _make_session()
    try:
        obra = Obra(nome="Obra Teste")
        db.add(obra)
        db.flush()

        ativ1 = Atividade(
            obra_id=obra.id,
            descricao="Concretagem da laje do térreo",
            data_inicio=date(2026, 4, 10),
            status=AtividadeStatus.INICIADA,
        )
        ativ2 = Atividade(
            obra_id=obra.id,
            descricao="Instalações elétricas do térreo",
            data_inicio=date(2026, 4, 10),
            status=AtividadeStatus.INICIADA,
        )
        db.add_all([ativ1, ativ2])
        db.flush()

        db.add_all(
            [
                AtividadeEmbedding(
                    obra_id=obra.id,
                    atividade_id=ativ1.id,
                    texto_canonico="Concretagem da laje do térreo",
                    embedding=_basis(0),
                    embedding_model="qwen3-embedding:0.6b",
                    embedding_dim=1024,
                ),
                AtividadeEmbedding(
                    obra_id=obra.id,
                    atividade_id=ativ2.id,
                    texto_canonico="Instalações elétricas do térreo",
                    embedding=_basis(1),
                    embedding_model="qwen3-embedding:0.6b",
                    embedding_dim=1024,
                ),
            ]
        )
        db.commit()

        service = ActivitySemanticSearch(db)

        async def fake_embed(_texto):
            return _basis(0)

        monkeypatch.setattr(service, "_embed_text", fake_embed)

        result = asyncio.run(service.search(cast(int, obra.id), "vamos concluir a concretagem"))

        assert result.selected is not None
        assert result.selected.atividade_id == ativ1.id
        assert result.best_score >= 0.98
        assert result.strategy == "lexical"
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


def test_busca_semantica_pede_desambiguacao_quando_empatado(monkeypatch):
    db, engine = _make_session()
    try:
        obra = Obra(nome="Obra Teste")
        db.add(obra)
        db.flush()

        ativ1 = Atividade(
            obra_id=obra.id,
            descricao="Alvenaria do térreo",
            data_inicio=date(2026, 4, 10),
            status=AtividadeStatus.INICIADA,
        )
        ativ2 = Atividade(
            obra_id=obra.id,
            descricao="Instalações hidráulicas do térreo",
            data_inicio=date(2026, 4, 10),
            status=AtividadeStatus.INICIADA,
        )
        db.add_all([ativ1, ativ2])
        db.flush()

        db.add_all(
            [
                AtividadeEmbedding(
                    obra_id=obra.id,
                    atividade_id=ativ1.id,
                    texto_canonico="Alvenaria do térreo",
                    embedding=_basis(0),
                    embedding_model="qwen3-embedding:0.6b",
                    embedding_dim=1024,
                ),
                AtividadeEmbedding(
                    obra_id=obra.id,
                    atividade_id=ativ2.id,
                    texto_canonico="Instalações hidráulicas do térreo",
                    embedding=_basis(1),
                    embedding_model="qwen3-embedding:0.6b",
                    embedding_dim=1024,
                ),
            ]
        )
        db.commit()

        service = ActivitySemanticSearch(db)

        async def fake_embed(_texto):
            return _mixed((0, 1))

        monkeypatch.setattr(service, "_embed_text", fake_embed)

        result = asyncio.run(service.search(cast(int, obra.id), "térreo"))

        assert result.selected is None
        assert len(result.candidates) == 2
        assert result.best_score == pytest.approx(result.second_score, rel=1e-9)
        assert result.strategy == "python"
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


def test_busca_semantica_usa_atalho_lexical_para_match_exato(monkeypatch):
    db, engine = _make_session()
    try:
        obra = Obra(nome="Obra Teste")
        db.add(obra)
        db.flush()

        ativ = Atividade(
            obra_id=obra.id,
            descricao="Concretagem da laje do térreo",
            data_inicio=date(2026, 4, 10),
            status=AtividadeStatus.INICIADA,
        )
        db.add(ativ)
        db.commit()

        service = ActivitySemanticSearch(db)

        async def fail_embed(_texto):
            raise AssertionError("Embedding não deveria ser chamado em match lexical exato")

        monkeypatch.setattr(service, "_embed_text", fail_embed)

        result = asyncio.run(service.search(cast(int, obra.id), "Concretagem da laje do térreo"))

        assert result.selected is not None
        assert result.selected.atividade_id == ativ.id
        assert result.strategy == "lexical"
        assert result.best_score >= 0.98
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
