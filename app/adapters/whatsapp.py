"""
Adapter WhatsApp — via Evolution API (self-hosted, sem API oficial).
"""
import os
import httpx
from app.adapters.base import BaseAdapter
from app.core.types import IncomingMessage, OutgoingMessage, Canal, TipoMensagem
from app.core.config import settings


class WhatsAppAdapter(BaseAdapter):

    def __init__(self):
        self.api_url = settings.evolution_api_url
        self.api_key = settings.evolution_api_key
        self.instance = settings.evolution_instance

    @property
    def headers(self):
        return {"apikey": self.api_key, "Content-Type": "application/json"}

    async def parse_incoming(self, raw_data: dict) -> IncomingMessage:
        """Converte webhook da Evolution API para IncomingMessage."""
        data = raw_data.get("data", raw_data)
        message = data.get("message", {})
        key = data.get("key", {})

        telefone = key.get("remoteJid", "").replace("@s.whatsapp.net", "")

        # Determinar tipo
        tipo = TipoMensagem.TEXTO
        texto = message.get("conversation") or message.get("extendedTextMessage", {}).get("text")
        audio_path = None
        foto_path = None
        legenda = None

        if "audioMessage" in message:
            tipo = TipoMensagem.AUDIO
            media_url = message.get("audioMessage", {}).get("url")
            if media_url:
                audio_path = await self._download_url(
                    media_url, f"./uploads/audio/{key.get('id', 'audio')}.ogg"
                )

        elif "imageMessage" in message:
            tipo = TipoMensagem.FOTO
            legenda = message.get("imageMessage", {}).get("caption")
            media_url = message.get("imageMessage", {}).get("url")
            if media_url:
                foto_path = await self._download_url(
                    media_url, f"./uploads/fotos/{key.get('id', 'foto')}.jpg"
                )
            texto = legenda

        return IncomingMessage(
            canal=Canal.WHATSAPP,
            telefone=telefone,
            tipo=tipo,
            texto=texto,
            audio_path=audio_path,
            foto_path=foto_path,
            legenda=legenda,
            raw_data=raw_data
        )

    async def send_message(self, msg: OutgoingMessage) -> bool:
        """Envia mensagem de texto via Evolution API."""
        payload = {
            "number": msg.telefone,
            "text": msg.texto
        }
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.api_url}/message/sendText/{self.instance}",
                headers=self.headers,
                json=payload
            )
            return resp.status_code == 200

    async def send_document(self, telefone: str, file_path: str, caption: str = None) -> bool:
        """Envia documento (PDF) via Evolution API."""
        import base64
        with open(file_path, "rb") as f:
            file_b64 = base64.b64encode(f.read()).decode()

        payload = {
            "number": telefone,
            "media": file_b64,
            "mimetype": "application/pdf",
            "fileName": os.path.basename(file_path),
            "caption": caption or ""
        }
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.api_url}/message/sendMedia/{self.instance}",
                headers=self.headers,
                json=payload
            )
            return resp.status_code == 200

    async def download_media(self, media_id: str, save_path: str) -> str:
        """Baixa mídia via Evolution API."""
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.api_url}/chat/getBase64FromMediaMessage/{self.instance}",
                headers=self.headers,
                json={"message": {"key": {"id": media_id}}}
            )
            if resp.status_code == 200:
                import base64
                data = resp.json()
                os.makedirs(os.path.dirname(save_path), exist_ok=True)
                with open(save_path, "wb") as f:
                    f.write(base64.b64decode(data.get("base64", "")))
                return save_path
        return ""

    async def _download_url(self, url: str, save_path: str) -> str:
        """Baixa arquivo de URL direta."""
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        async with httpx.AsyncClient() as client:
            resp = await client.get(url)
            with open(save_path, "wb") as f:
                f.write(resp.content)
        return save_path
