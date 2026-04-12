import asyncio

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.core.orchestrator as orchestrator_module
from app.core.orchestrator import Orchestrator
from app.core.types import Canal, IncomingMessage
from app.database import Base
from app.models import Atividade, ConversationState, Obra, Usuario


def _make_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    return TestingSessionLocal(), engine


def test_orchestrator_resolve_estado_pendente_e_registra_atividade(monkeypatch):
    db, engine = _make_session()
    try:
        admin = Usuario(nome="Operador", telefone="5511999990001", ativo=True, role="estagiario")
        obra = Obra(nome="Obra Teste")
        db.add_all([admin, obra])
        db.flush()
        admin.obra_id = obra.id
        db.commit()

        async def fake_classify_intent(text, obra_id=None, forced_intent=None):
            if forced_intent:
                return {
                    "intent": forced_intent,
                    "confidence": 0.95,
                    "data": {
                        "descricao": "Execução de alvenaria do térreo",
                        "local": "Térreo",
                        "etapa": "Alvenaria",
                    },
                }

            return {
                "intent": "atividade",
                "confidence": 0.35,
                "candidates": ["atividade", "efetivo"],
                "data": {},
            }

        monkeypatch.setattr(orchestrator_module, "classify_intent", fake_classify_intent)
        monkeypatch.setattr(orchestrator_module.ConversationStateService, "_build_redis", lambda self: None)
        async def fake_upsert(self, atividade):
            return None

        monkeypatch.setattr(
            orchestrator_module.ActivitySemanticSearch,
            "upsert_activity_embedding",
            fake_upsert,
        )

        orchestrator = Orchestrator(db)

        msg1 = IncomingMessage(canal=Canal.WHATSAPP, telefone=admin.telefone, texto="vamos registrar algo")
        resp1 = asyncio.run(orchestrator.processar(msg1))

        assert resp1.texto == "📋 O que você quer registrar?"
        assert resp1.botoes is not None
        assert db.query(ConversationState).filter(ConversationState.scope_key == "whatsapp:5511999990001").count() == 1

        msg2 = IncomingMessage(canal=Canal.WHATSAPP, telefone=admin.telefone, texto="1")
        resp2 = asyncio.run(orchestrator.processar(msg2))

        assert "Atividade iniciada" in resp2.texto
        atividade = db.query(Atividade).filter(Atividade.obra_id == obra.id).first()
        assert atividade is not None
        assert atividade.descricao == "Execução de alvenaria do térreo"

        estado = db.query(ConversationState).filter(ConversationState.scope_key == "whatsapp:5511999990001").first()
        assert estado is not None
        assert estado.consumed_at is not None
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
