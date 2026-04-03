"""
Base adapter — interface que todo adapter de canal deve implementar.
"""
from abc import ABC, abstractmethod
from app.core.types import IncomingMessage, OutgoingMessage


class BaseAdapter(ABC):
    """Interface base para adapters de canal (WhatsApp, Telegram, Web)."""

    @abstractmethod
    async def parse_incoming(self, raw_data: dict) -> IncomingMessage:
        """Converte dados brutos do canal para IncomingMessage."""
        ...

    @abstractmethod
    async def send_message(self, msg: OutgoingMessage) -> bool:
        """Envia mensagem de volta pelo canal."""
        ...

    @abstractmethod
    async def send_document(self, telefone: str, file_path: str, caption: str = None) -> bool:
        """Envia documento (PDF) pelo canal."""
        ...

    @abstractmethod
    async def download_media(self, media_id: str, save_path: str) -> str:
        """Baixa mídia (áudio/foto) e retorna path local."""
        ...
