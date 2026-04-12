"""Testes para a expiração de estados conversacionais."""
from datetime import timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.time import utc_now
from app.database import Base
from app.models import ConversationState
from app.services.conversation_state import ConversationStateService


class FakeRedis:
    """Redis mockado que não faz nada."""

    def __init__(self):
        self.storage = {}

    @classmethod
    def from_url(cls, *_args, **_kwargs):
        return cls()

    def ping(self):
        return True

    def setex(self, key, _ttl, value):
        self.storage[key] = value

    def get(self, key):
        return self.storage.get(key)

    def delete(self, key):
        self.storage.pop(key, None)


def _make_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    return TestingSessionLocal(), engine


def test_expire_stale_states(monkeypatch):
    """Testa a expiração de estados stale."""
    # Mock do Redis como None (simula ambiente sem Redis)
    monkeypatch.setattr(ConversationStateService, "_build_redis", lambda self: None)

    db, engine = _make_session()
    try:
        service = ConversationStateService(db)
        now = utc_now()

        # Estado 1: expirado (expires_at < now, consumed_at IS NULL)
        expired_state = ConversationState(
            channel="whatsapp",
            scope_key="whatsapp:5511999990001",
            state_type="intent_choice",
            state_token="token-expired",
            payload={"value": "test"},
            expires_at=now - timedelta(hours=1),
            consumed_at=None,
        )
        db.add(expired_state)

        # Estado 2: ativo (expires_at > now, consumed_at IS NULL)
        active_state = ConversationState(
            channel="whatsapp",
            scope_key="whatsapp:5511999990002",
            state_type="intent_choice",
            state_token="token-active",
            payload={"value": "test"},
            expires_at=now + timedelta(hours=1),
            consumed_at=None,
        )
        db.add(active_state)

        # Estado 3: já consumido (expires_at < now, consumed_at NOT NULL)
        consumed_state = ConversationState(
            channel="whatsapp",
            scope_key="whatsapp:5511999990003",
            state_type="intent_choice",
            state_token="token-consumed",
            payload={"value": "test"},
            expires_at=now - timedelta(hours=1),
            consumed_at=now - timedelta(minutes=30),
        )
        db.add(consumed_state)

        db.commit()

        # Executa a expiração
        count = service.expire_stale_states()

        # Verifica o resultado
        assert count == 1, "Deveria retornar 1 estado expirado"

        # Recarrega os estados do banco
        db.expire_all()

        expired = db.query(ConversationState).filter(
            ConversationState.scope_key == "whatsapp:5511999990001"
        ).first()
        active = db.query(ConversationState).filter(
            ConversationState.scope_key == "whatsapp:5511999990002"
        ).first()
        consumed = db.query(ConversationState).filter(
            ConversationState.scope_key == "whatsapp:5511999990003"
        ).first()

        # Estado expirado deve estar marcado como consumido
        assert expired.consumed_at is not None, "Estado expirado deve ter consumed_at preenchido"

        # Estado ativo não deve ser afetado
        assert active.consumed_at is None, "Estado ativo não deve ser afetado"

        # Estado já consumido não deve ser afetado
        assert consumed.consumed_at is not None, "Estado já consumido não deve ser afetado"
        assert consumed.consumed_at == now - timedelta(minutes=30), "consumed_at deve permanecer inalterado"
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)