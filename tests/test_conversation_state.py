import json
from datetime import timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.time import utc_now
from app.database import Base
from app.models import ConversationState
from app.services.conversation_state import ConversationStateService


class FakeRedis:
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


def test_state_store_usa_cache_e_fallback_no_expirar(monkeypatch):
    fake_redis = FakeRedis()
    monkeypatch.setattr(ConversationStateService, "_build_redis", lambda self: fake_redis)

    db, engine = _make_session()
    try:
        service = ConversationStateService(db)
        state = service.set_state(
            channel="whatsapp",
            identifier="5511999990001",
            state_type="intent_choice",
            payload={"choices": [{"value": "atividade", "label": "🏗️ Atividade"}]},
            text_original="vamos registrar",
            source_message_id="msg-1",
        )

        cached = fake_redis.get("conversation_state:whatsapp:5511999990001")
        assert cached is not None

        active = service.get_active_state("whatsapp:5511999990001")
        assert active is not None
        assert active.state_token == state.state_token
        assert active.is_active is True

        row = db.query(ConversationState).filter(ConversationState.scope_key == "whatsapp:5511999990001").first()
        row.expires_at = utc_now() - timedelta(seconds=1)
        db.commit()
        cache_key = "conversation_state:whatsapp:5511999990001"
        cached_state = json.loads(fake_redis.get(cache_key))
        cached_state["expires_at"] = (utc_now() - timedelta(seconds=1)).isoformat()
        fake_redis.storage[cache_key] = json.dumps(cached_state)

        assert service.get_active_state("whatsapp:5511999990001") is None
        assert fake_redis.get(cache_key) is None
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


def test_state_store_consumo_idempotente_sem_redis(monkeypatch):
    monkeypatch.setattr(ConversationStateService, "_build_redis", lambda self: None)

    db, engine = _make_session()
    try:
        service = ConversationStateService(db)
        state = service.set_state(
            channel="telegram",
            identifier="123",
            state_type="confirmation",
            payload={"choices": [{"value": "yes", "label": "✅ Sim"}, {"value": "no", "label": "❌ Não"}]},
            text_original="Confirma?",
            source_message_id="msg-2",
        )

        active = service.get_active_state("telegram:123")
        assert active is not None
        assert active.state_token == state.state_token

        consumed = service.consume_state(state_token=state.state_token)
        assert consumed is not None
        assert consumed.consumed_at is not None
        assert service.consume_state(state_token=state.state_token) is None
        assert service.get_active_state("telegram:123") is None
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


def test_set_state_whatsapp_ttl_48h(monkeypatch):
    """Testa que estados WhatsApp têm TTL de 48 horas."""
    monkeypatch.setattr(ConversationStateService, "_build_redis", lambda self: None)

    db, engine = _make_session()
    try:
        service = ConversationStateService(db)
        now = utc_now()

        state = service.set_state(
            channel="whatsapp",
            identifier="5511999990001",
            state_type="intent_choice",
            payload={"value": "test"},
        )

        # TTL deve ser aproximadamente 48h (margem de 1h para tolerância)
        assert state.expires_at > now + timedelta(hours=47)
        assert state.expires_at <= now + timedelta(hours=49)
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


def test_set_state_telegram_ttl_24h(monkeypatch):
    """Testa que estados Telegram têm TTL de 24 horas."""
    monkeypatch.setattr(ConversationStateService, "_build_redis", lambda self: None)

    db, engine = _make_session()
    try:
        service = ConversationStateService(db)
        now = utc_now()

        state = service.set_state(
            channel="telegram",
            identifier="123456",
            state_type="intent_choice",
            payload={"value": "test"},
        )

        # TTL deve ser aproximadamente 24h (margem de 1h para tolerância)
        assert state.expires_at > now + timedelta(hours=23)
        assert state.expires_at <= now + timedelta(hours=25)
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
