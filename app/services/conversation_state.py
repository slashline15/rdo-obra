"""Persistência de estados conversacionais com PostgreSQL + Redis."""
from __future__ import annotations

import json
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Optional, cast

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.time import utc_now
from app.models import ConversationState

try:  # pragma: no cover - dependência opcional em runtime de testes
    from redis import Redis  # type: ignore
except Exception:  # pragma: no cover - fallback quando o pacote não estiver instalado
    Redis = None


@dataclass
class ConversationStateSnapshot:
    id: int
    channel: str
    scope_key: str
    state_type: str
    state_token: str
    payload: dict[str, Any]
    text_original: Optional[str]
    source_message_id: Optional[str]
    expires_at: Optional[datetime]
    consumed_at: Optional[datetime]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    @property
    def is_active(self) -> bool:
        return self.consumed_at is None and (self.expires_at is not None and self.expires_at > utc_now())


class ConversationStateService:
    """Mantém o estado durável no Postgres e espelha em Redis."""

    def __init__(self, db: Session):
        self.db = db
        self.redis = self._build_redis()

    @staticmethod
    def build_scope_key(channel: str, identifier: str) -> str:
        return f"{channel}:{identifier}"

    def _build_redis(self):
        if Redis is None or not settings.redis_url:
            return None
        try:
            client = Redis.from_url(settings.redis_url, decode_responses=True)
            client.ping()
            return client
        except Exception:
            return None

    @staticmethod
    def _cache_key(scope_key: str) -> str:
        return f"conversation_state:{scope_key}"

    @staticmethod
    def _ttl_seconds() -> int:
        # Usado apenas como fallback; o TTL do Redis é calculado a partir do expires_at do snapshot
        return max(int(settings.state_ttl_hours_default * 3600), 60)

    @staticmethod
    def _ttl_hours_by_channel(channel: str) -> int:
        """Retorna o TTL em horas baseado no canal."""
        _TTL_BY_CHANNEL = {
            "whatsapp": settings.state_ttl_hours_whatsapp,
            "telegram": settings.state_ttl_hours_telegram,
        }
        return _TTL_BY_CHANNEL.get(channel, settings.state_ttl_hours_default)

    @staticmethod
    def _serialize(snapshot: ConversationStateSnapshot) -> str:
        return json.dumps({
            "id": snapshot.id,
            "channel": snapshot.channel,
            "scope_key": snapshot.scope_key,
            "state_type": snapshot.state_type,
            "state_token": snapshot.state_token,
            "payload": snapshot.payload,
            "text_original": snapshot.text_original,
            "source_message_id": snapshot.source_message_id,
            "expires_at": snapshot.expires_at.isoformat() if snapshot.expires_at else None,
            "consumed_at": snapshot.consumed_at.isoformat() if snapshot.consumed_at else None,
            "created_at": snapshot.created_at.isoformat() if snapshot.created_at else None,
            "updated_at": snapshot.updated_at.isoformat() if snapshot.updated_at else None,
        }, ensure_ascii=False)

    @staticmethod
    def _deserialize(data: str) -> ConversationStateSnapshot:
        payload = json.loads(data)
        return ConversationStateSnapshot(
            id=payload["id"],
            channel=payload["channel"],
            scope_key=payload["scope_key"],
            state_type=payload["state_type"],
            state_token=payload["state_token"],
            payload=payload.get("payload") or {},
            text_original=payload.get("text_original"),
            source_message_id=payload.get("source_message_id"),
            expires_at=ConversationStateService._parse_dt(payload.get("expires_at")),
            consumed_at=ConversationStateService._parse_dt(payload.get("consumed_at")),
            created_at=ConversationStateService._parse_dt(payload.get("created_at")),
            updated_at=ConversationStateService._parse_dt(payload.get("updated_at")),
        )

    @staticmethod
    def _parse_dt(value):
        if not value:
            return None
        from datetime import datetime

        return datetime.fromisoformat(value)

    @staticmethod
    def _from_model(state: ConversationState) -> ConversationStateSnapshot:
        return ConversationStateSnapshot(
            id=cast(int, getattr(state, "id", 0)),
            channel=cast(str, getattr(state, "channel", "")),
            scope_key=cast(str, getattr(state, "scope_key", "")),
            state_type=cast(str, getattr(state, "state_type", "")),
            state_token=cast(str, getattr(state, "state_token", "")),
            payload=cast(dict, getattr(state, "payload", {}) or {}),
            text_original=cast(Optional[str], getattr(state, "text_original", None)),
            source_message_id=cast(Optional[str], getattr(state, "source_message_id", None)),
            expires_at=cast(Optional[datetime], getattr(state, "expires_at", None)),
            consumed_at=cast(Optional[datetime], getattr(state, "consumed_at", None)),
            created_at=cast(Optional[datetime], getattr(state, "created_at", None)),
            updated_at=cast(Optional[datetime], getattr(state, "updated_at", None)),
        )

    def _cache_snapshot(self, snapshot: ConversationStateSnapshot):
        if not self.redis:
            return
        if not snapshot.is_active:
            self.redis.delete(self._cache_key(snapshot.scope_key))
            return
        if snapshot.expires_at is None:
            ttl = self._ttl_seconds()
        else:
            ttl = max(int((snapshot.expires_at - utc_now()).total_seconds()), 1)
        self.redis.setex(self._cache_key(snapshot.scope_key), ttl, self._serialize(snapshot))

    def _clear_cache(self, scope_key: str):
        if self.redis:
            self.redis.delete(self._cache_key(scope_key))

    def get_active_state(self, scope_key: str) -> ConversationStateSnapshot | None:
        if self.redis:
            cached = self.redis.get(self._cache_key(scope_key))
            if cached:
                snapshot = self._deserialize(cast(str, cached))
                if snapshot.is_active:
                    return snapshot
                self._clear_cache(scope_key)

        state = self.db.query(ConversationState).filter(
            ConversationState.scope_key == scope_key,
            ConversationState.consumed_at.is_(None),
            ConversationState.expires_at > utc_now(),
        ).first()
        if not state:
            return None

        snapshot = self._from_model(state)
        if not snapshot.is_active:
            self._clear_cache(scope_key)
            return None

        self._cache_snapshot(snapshot)
        return snapshot

    def get_state_by_token(self, state_token: str) -> ConversationStateSnapshot | None:
        state = self.db.query(ConversationState).filter(
            ConversationState.state_token == state_token,
            ConversationState.consumed_at.is_(None),
            ConversationState.expires_at > utc_now(),
        ).first()
        if not state:
            return None
        snapshot = self._from_model(state)
        if not snapshot.is_active:
            self._clear_cache(snapshot.scope_key)
            return None
        self._cache_snapshot(snapshot)
        return snapshot

    def set_state(
        self,
        channel: str,
        identifier: str,
        state_type: str,
        payload: dict[str, Any],
        text_original: str | None = None,
        source_message_id: str | None = None,
    ) -> ConversationStateSnapshot:
        scope_key = self.build_scope_key(channel, identifier)
        state = self.db.query(ConversationState).filter(
            ConversationState.scope_key == scope_key
        ).first()

        now = utc_now()
        ttl_hours = self._ttl_hours_by_channel(channel)
        expires_at = now + timedelta(hours=ttl_hours)
        token = secrets.token_urlsafe(10)

        if state:
            setattr(state, "channel", channel)
            setattr(state, "state_type", state_type)
            setattr(state, "state_token", token)
            setattr(state, "payload", payload)
            setattr(state, "text_original", text_original)
            setattr(state, "source_message_id", source_message_id)
            setattr(state, "expires_at", expires_at)
            setattr(state, "consumed_at", None)
            setattr(state, "updated_at", now)
        else:
            state = ConversationState(
                channel=channel,
                scope_key=scope_key,
                state_type=state_type,
                state_token=token,
                payload=payload,
                text_original=text_original,
                source_message_id=source_message_id,
                expires_at=expires_at,
            )
            self.db.add(state)

        self.db.commit()
        self.db.refresh(state)

        snapshot = self._from_model(state)
        self._cache_snapshot(snapshot)
        return snapshot

    def consume_state(
        self,
        scope_key: str | None = None,
        state_token: str | None = None,
    ) -> ConversationStateSnapshot | None:
        query = self.db.query(ConversationState)
        if state_token:
            query = query.filter(
                ConversationState.state_token == state_token,
                ConversationState.consumed_at.is_(None),
                ConversationState.expires_at > utc_now(),
            )
        elif scope_key:
            query = query.filter(
                ConversationState.scope_key == scope_key,
                ConversationState.consumed_at.is_(None),
                ConversationState.expires_at > utc_now(),
            )
        else:
            return None

        state = query.with_for_update().first()
        if not state:
            return None

        snapshot = self._from_model(state)
        if not snapshot.is_active:
            self._clear_cache(snapshot.scope_key)
            return None

        setattr(state, "consumed_at", utc_now())
        setattr(state, "updated_at", utc_now())
        self.db.commit()
        self.db.refresh(state)

        self._clear_cache(snapshot.scope_key)
        return self._from_model(state)

    def clear_state(self, scope_key: str) -> bool:
        state = self.db.query(ConversationState).filter(
            ConversationState.scope_key == scope_key
        ).first()
        if not state:
            self._clear_cache(scope_key)
            return False

        setattr(state, "consumed_at", utc_now())
        setattr(state, "updated_at", utc_now())
        self.db.commit()
        self._clear_cache(scope_key)
        return True

    def expire_stale_states(self) -> int:
        """Marca estados expirados como consumidos.

        Faz UPDATE em lote: SET consumed_at = now(), updated_at = now()
        WHERE expires_at < now() AND consumed_at IS NULL.

        Retorna o número de linhas afetadas.
        """
        now = utc_now()

        # Primeiro, busca as chaves dos registros afetados para limpar o Redis
        stale_states = self.db.query(ConversationState).filter(
            ConversationState.expires_at < now,
            ConversationState.consumed_at.is_(None),
        ).with_for_update(skip_locked=True).all()

        if not stale_states:
            return 0

        # Limpa o cache Redis antes de marcar como consumidos
        for state in stale_states:
            self._clear_cache(cast(str, state.scope_key))

        # Atualiza os registros em lote
        result = self.db.query(ConversationState).filter(
            ConversationState.expires_at < now,
            ConversationState.consumed_at.is_(None),
        ).update(
            {
                ConversationState.consumed_at: now,
                ConversationState.updated_at: now,
            },
            synchronize_session=False,
        )

        self.db.commit()
        return result
