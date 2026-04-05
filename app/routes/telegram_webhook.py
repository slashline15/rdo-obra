"""Webhook route para Telegram Bot API."""
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.adapters.telegram import TelegramAdapter
from app.core.orchestrator import Orchestrator
from app.core.config import settings
from app.models import Usuario

router = APIRouter(prefix="/telegram", tags=["Telegram"])


@router.post("/webhook")
async def telegram_webhook(request: Request, db: Session = Depends(get_db)):
    """Recebe updates do Telegram Bot API."""
    raw_data = await request.json()
    adapter = TelegramAdapter()

    # ─── Callback query (botão inline pressionado) ───
    if "callback_query" in raw_data:
        callback = raw_data["callback_query"]
        chat_id = str(callback["message"]["chat"]["id"])
        callback_data = callback.get("data", "")
        callback_id = callback["id"]

        # Responder o callback (tira o "loading" do botão)
        await adapter.answer_callback(callback_id)

        if callback_data == "cancelar":
            await adapter.send_message_raw(chat_id, "❌ Cancelado.")
            return {"ok": True}

        # Identificar usuário
        user = db.query(Usuario).filter(Usuario.telefone == chat_id).first()
        if not user or not user.obra_id:
            await adapter.send_message_raw(chat_id, "❌ Usuário não cadastrado.")
            return {"ok": True}

        orchestrator = Orchestrator(db)
        resposta = await orchestrator.processar_callback(callback_data, chat_id, user.nome, user.obra_id)
        await adapter.send_message_raw(chat_id, resposta)
        return {"ok": True}

    # ─── Mensagem normal ───
    if "message" not in raw_data:
        return {"ok": True}

    message = raw_data.get("message", {})
    text = message.get("text", "")
    chat_id = str(message.get("chat", {}).get("id", ""))

    # Auto-registro: /start mapeia chat_id ao primeiro usuário disponível
    if text.strip() == "/start":
        user = db.query(Usuario).filter(Usuario.telefone == chat_id).first()
        if user:
            await adapter.send_message_raw(chat_id, f"✅ Já cadastrado como {user.nome}.")
        else:
            user = db.query(Usuario).filter(
                Usuario.telefone.op("~")(r"^\+?\d{10,}")
            ).first()
            if user:
                user.telefone = chat_id
                db.commit()
                await adapter.send_message_raw(
                    chat_id,
                    f"✅ Vinculado como <b>{user.nome}</b> ({user.role}).\n"
                    f"Pode começar a registrar!"
                )
            else:
                await adapter.send_message_raw(chat_id, "⚠️ Nenhum usuário disponível. Peça ao responsável.")
        return {"ok": True}

    # Parsear e processar
    msg = await adapter.parse_incoming(raw_data)
    orchestrator = Orchestrator(db)
    resposta = await orchestrator.processar(msg)
    await adapter.send_message(resposta)

    return {"ok": True}
