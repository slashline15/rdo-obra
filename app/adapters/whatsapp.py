"""
Adapter WhatsApp — via Evolution API (self-hosted, sem API oficial).
"""
import logging
import os
import httpx
from app.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)
from app.core.types import IncomingMessage, OutgoingMessage, Canal, TipoMensagem
from app.core.config import settings


class WhatsAppAdapter(BaseAdapter):

    def __init__(self, instance_override: str | None = None):
        self.api_url = settings.evolution_api_url
        self.api_key = settings.evolution_api_key
        # instance_override permite especificar qual instância usar no momento da chamada
        self.instance = instance_override or settings.evolution_instance

    @property
    def headers(self):
        return {"apikey": self.api_key, "Content-Type": "application/json"}

    @staticmethod
    def _unwrap_message_payload(raw_data: dict) -> tuple[dict, dict, dict]:
        data = raw_data.get("data", raw_data) or {}
        if isinstance(data.get("messages"), list) and data["messages"]:
            payload = data["messages"][0] or {}
            key = payload.get("key", data.get("key", {})) or {}
            message_data = payload.get("message", payload) or {}
        else:
            key = data.get("key", {}) or {}
            message_data = data.get("message", {}) or {}
        return data, key, message_data

    @staticmethod
    def _extract_reply_context(message: dict) -> tuple[str | None, str | None]:
        for container_key in ("extendedTextMessage", "imageMessage", "videoMessage", "audioMessage"):
            container = message.get(container_key, {}) or {}
            context = container.get("contextInfo", {}) or {}
            if not context:
                continue
            reply_to_id = context.get("stanzaId")
            quoted = context.get("quotedMessage", {}) or {}
            reply_text = (
                quoted.get("conversation")
                or quoted.get("extendedTextMessage", {}).get("text")
                or quoted.get("imageMessage", {}).get("caption")
                or quoted.get("documentMessage", {}).get("caption")
            )
            return reply_to_id, reply_text
        return None, None

    @staticmethod
    def _render_menu(text: str, botoes: list | None) -> str:
        if not botoes:
            return text

        linhas = [text.rstrip(), "", "Opções:"]
        for indice, botao in enumerate(botoes, start=1):
            linhas.append(f"{indice}. {botao.get('text', 'Opção')}")
        linhas.append("")
        linhas.append("Responda com o número da opção.")
        return "\n".join(linhas)

    async def parse_incoming(self, raw_data: dict) -> IncomingMessage:
        """Converte webhook da Evolution API para IncomingMessage."""
        data, key, message = self._unwrap_message_payload(raw_data)

        remote_jid = key.get("remoteJid", "") or ""
        participant = key.get("participant")
        telefone = remote_jid.replace("@s.whatsapp.net", "").replace("@lid", "")
        if remote_jid.endswith("@g.us") and participant:
            telefone = participant.replace("@s.whatsapp.net", "")

        # Determinar tipo
        tipo = TipoMensagem.TEXTO
        texto = message.get("conversation") or message.get("extendedTextMessage", {}).get("text")
        audio_path = None
        foto_path = None
        legenda = None
        reply_to_message_id, reply_to_text = self._extract_reply_context(message)

        if "audioMessage" in message:
            tipo = TipoMensagem.AUDIO
            msg_id = key.get("id", "audio")
            save_path = f"./uploads/audio/{msg_id}.ogg"
            audio_path = await self.download_media(msg_id, save_path)
            if not audio_path:
                # Fallback: tentar URL direta (pode ser não-criptografada)
                media_url = message.get("audioMessage", {}).get("url")
                if media_url:
                    audio_path = await self._download_url(media_url, save_path)

        elif "imageMessage" in message:
            tipo = TipoMensagem.FOTO
            legenda = message.get("imageMessage", {}).get("caption")
            msg_id = key.get("id", "foto")
            save_path = f"./uploads/fotos/{msg_id}.jpg"
            foto_path = await self.download_media(msg_id, save_path)
            if not foto_path:
                media_url = message.get("imageMessage", {}).get("url")
                if media_url:
                    foto_path = await self._download_url(media_url, save_path)
            texto = legenda

        return IncomingMessage(
            canal=Canal.WHATSAPP,
            telefone=telefone,
            tipo=tipo,
            texto=texto,
            audio_path=audio_path,
            foto_path=foto_path,
            legenda=legenda,
            message_id=str(key.get("id") or ""),
            reply_to_message_id=reply_to_message_id,
            reply_to_text=reply_to_text,
            raw_data=raw_data
        )

    _TIMEOUT = httpx.Timeout(15.0, connect=10.0)

    async def send_message(self, msg: OutgoingMessage) -> bool:
        """Envia mensagem de texto via Evolution API."""
        texto = self._render_menu(msg.texto, msg.botoes)
        payload = {
            "number": msg.telefone,
            "text": texto
        }
        try:
            async with httpx.AsyncClient(timeout=self._TIMEOUT) as client:
                resp = await client.post(
                    f"{self.api_url}/message/sendText/{self.instance}",
                    headers=self.headers,
                    json=payload
                )
                return resp.status_code in (200, 201)
        except Exception:
            return False

    async def send_document(self, telefone: str, file_path: str, caption: str | None = None) -> bool:
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
        try:
            async with httpx.AsyncClient(timeout=self._TIMEOUT) as client:
                resp = await client.post(
                    f"{self.api_url}/message/sendMedia/{self.instance}",
                    headers=self.headers,
                    json=payload
                )
                return resp.status_code in (200, 201)
        except Exception:
            return False

    async def download_media(self, media_id: str, save_path: str) -> str:
        """Baixa mídia via Evolution API (descriptografa automaticamente)."""
        try:
            async with httpx.AsyncClient(timeout=self._TIMEOUT) as client:
                resp = await client.post(
                    f"{self.api_url}/chat/getBase64FromMediaMessage/{self.instance}",
                    headers=self.headers,
                    json={"message": {"key": {"id": media_id}}}
                )
                if resp.status_code in (200, 201):
                    import base64
                    data = resp.json()
                    b64 = data.get("base64", "")
                    if not b64:
                        logger.warning("download_media: resposta sem base64 para %s", media_id)
                        return ""
                    os.makedirs(os.path.dirname(save_path), exist_ok=True)
                    with open(save_path, "wb") as f:
                        f.write(base64.b64decode(b64))
                    logger.info("download_media: salvo %s (%d bytes)", save_path, os.path.getsize(save_path))
                    return save_path
                else:
                    logger.warning("download_media: status=%d para %s", resp.status_code, media_id)
        except Exception as exc:
            logger.error("download_media: erro para %s: %s", media_id, exc)
        return ""

    async def _download_url(self, url: str, save_path: str) -> str:
        """Baixa arquivo de URL direta."""
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        try:
            async with httpx.AsyncClient(timeout=self._TIMEOUT) as client:
                resp = await client.get(url)
                with open(save_path, "wb") as f:
                    f.write(resp.content)
        except Exception:
            pass
        return save_path
