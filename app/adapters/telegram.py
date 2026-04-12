"""
Adapter Telegram — Bot API oficial (grátis, sem limitações).
Suporta: texto, áudio, fotos, botões inline.
"""
import os
import httpx
from app.adapters.base import BaseAdapter
from app.core.types import IncomingMessage, OutgoingMessage, Canal, TipoMensagem
from app.core.config import settings


class TelegramAdapter(BaseAdapter):

    def __init__(self):
        self.token = settings.telegram_bot_token
        self.base_url = f"https://api.telegram.org/bot{self.token}"

    @staticmethod
    def _extract_reply_context(message: dict) -> tuple[str | None, str | None]:
        reply = message.get("reply_to_message", {}) or {}
        reply_id = reply.get("message_id")
        reply_text = reply.get("text") or reply.get("caption")
        return (str(reply_id) if reply_id is not None else None, reply_text)

    async def parse_incoming(self, raw_data: dict) -> IncomingMessage:
        """Converte update do Telegram para IncomingMessage."""
        message = raw_data.get("message", {})
        chat = message.get("chat", {})
        user = message.get("from", {})

        # Determinar tipo
        tipo = TipoMensagem.TEXTO
        texto = message.get("text")
        audio_path = None
        foto_path = None
        legenda = message.get("caption")
        reply_to_message_id, reply_to_text = self._extract_reply_context(message)

        if "voice" in message or "audio" in message:
            tipo = TipoMensagem.AUDIO
            media = message.get("voice") or message.get("audio")
            audio_path = await self.download_media(
                media["file_id"],
                f"./uploads/audio/{media['file_id']}.ogg"
            )

        elif "photo" in message:
            tipo = TipoMensagem.FOTO
            # Pegar a maior resolução
            photo = message["photo"][-1]
            foto_path = await self.download_media(
                photo["file_id"],
                f"./uploads/fotos/{photo['file_id']}.jpg"
            )
            texto = legenda

        # Usar chat_id como identificador (mapear para telefone na camada de usuário)
        telefone = str(chat.get("id", ""))

        return IncomingMessage(
            canal=Canal.TELEGRAM,
            telefone=telefone,
            tipo=tipo,
            texto=texto,
            audio_path=audio_path,
            foto_path=foto_path,
            legenda=legenda,
            message_id=str(message.get("message_id") or ""),
            reply_to_message_id=reply_to_message_id,
            reply_to_text=reply_to_text,
            raw_data=raw_data
        )

    async def send_message(self, msg: OutgoingMessage) -> bool:
        """Envia mensagem de texto (com botões opcionais)."""
        payload: dict = {
            "chat_id": msg.telefone,
            "text": msg.texto,
            "parse_mode": "HTML"
        }

        # Adicionar botões inline se houver
        if msg.reply_markup:
            payload["reply_markup"] = msg.reply_markup
        elif msg.botoes:
            inline_keyboard = []
            for btn in msg.botoes:
                inline_keyboard.append([{
                    "text": btn["text"],
                    "callback_data": btn.get("data", btn["text"])
                }])
            payload["reply_markup"] = {
                "inline_keyboard": inline_keyboard
            }

        async with httpx.AsyncClient() as client:
            resp = await client.post(f"{self.base_url}/sendMessage", json=payload)
            return resp.status_code == 200

    async def answer_callback(self, callback_query_id: str) -> bool:
        """Responde callback query (remove loading do botão)."""
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/answerCallbackQuery",
                json={"callback_query_id": callback_query_id}
            )
            return resp.status_code == 200

    async def send_message_raw(self, chat_id: str, text: str) -> bool:
        """Envia mensagem simples por chat_id (sem OutgoingMessage)."""
        payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
        async with httpx.AsyncClient() as client:
            resp = await client.post(f"{self.base_url}/sendMessage", json=payload)
            return resp.status_code == 200

    async def send_document(self, telefone: str, file_path: str, caption: str | None = None) -> bool:
        """Envia PDF ou documento."""
        async with httpx.AsyncClient() as client:
            with open(file_path, "rb") as f:
                resp = await client.post(
                    f"{self.base_url}/sendDocument",
                    data={"chat_id": telefone, "caption": caption or ""},
                    files={"document": (os.path.basename(file_path), f)}
                )
                return resp.status_code == 200

    async def download_media(self, media_id: str, save_path: str) -> str:
        """Baixa arquivo do Telegram."""
        os.makedirs(os.path.dirname(save_path), exist_ok=True)

        async with httpx.AsyncClient() as client:
            # Obter file_path
            resp = await client.get(f"{self.base_url}/getFile", params={"file_id": media_id})
            file_data = resp.json()
            file_path = file_data["result"]["file_path"]

            # Baixar arquivo
            download_url = f"https://api.telegram.org/file/bot{self.token}/{file_path}"
            resp = await client.get(download_url)

            with open(save_path, "wb") as f:
                f.write(resp.content)

        return save_path

    async def setup_webhook(self, webhook_url: str):
        """Configura webhook do bot."""
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/setWebhook",
                json={"url": f"{webhook_url}/telegram/webhook"}
            )
            return resp.json()
