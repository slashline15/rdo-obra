"""Helpers centralizados para datas em UTC sem usar APIs depreciadas."""
from datetime import UTC, datetime


def utc_now_aware() -> datetime:
    """Retorna datetime timezone-aware em UTC."""
    return datetime.now(UTC)


def utc_now() -> datetime:
    """Retorna datetime UTC sem tzinfo para compatibilidade com o schema atual."""
    return utc_now_aware().replace(tzinfo=None)


def utc_now_iso() -> str:
    """Serializa o instante atual em ISO 8601 com sufixo Z."""
    return utc_now_aware().isoformat().replace("+00:00", "Z")
