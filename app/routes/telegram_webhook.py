"""Webhook route para Telegram Bot API."""
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.adapters.telegram import TelegramAdapter
from app.core.orchestrator import Orchestrator

router = APIRouter(prefix="/telegram", tags=["Telegram"])
adapter = TelegramAdapter()


@router.post("/webhook")
async def telegram_webhook(request: Request, db: Session = Depends(get_db)):
    """Recebe updates do Telegram Bot API."""
    raw_data = await request.json()

    # Ignorar se não for mensagem
    if "message" not in raw_data:
        return {"ok": True}

    # Parsear
    msg = await adapter.parse_incoming(raw_data)

    # Processar
    orchestrator = Orchestrator(db)
    resposta = await orchestrator.processar(msg)

    # Enviar resposta
    await adapter.send_message(resposta)

    return {"ok": True}
