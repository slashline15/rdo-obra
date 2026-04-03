"""Webhook route para Evolution API (WhatsApp)."""
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.adapters.whatsapp import WhatsAppAdapter
from app.core.orchestrator import Orchestrator

router = APIRouter(prefix="/whatsapp", tags=["WhatsApp"])
adapter = WhatsAppAdapter()


@router.post("/webhook")
async def whatsapp_webhook(request: Request, db: Session = Depends(get_db)):
    """Recebe webhooks da Evolution API."""
    raw_data = await request.json()
    event = raw_data.get("event")

    # Só processar mensagens recebidas
    if event not in ("messages.upsert", None):
        return {"ok": True}

    # Ignorar mensagens enviadas por nós
    key = raw_data.get("data", {}).get("key", {})
    if key.get("fromMe"):
        return {"ok": True}

    # Parsear
    msg = await adapter.parse_incoming(raw_data)

    # Processar
    orchestrator = Orchestrator(db)
    resposta = await orchestrator.processar(msg)

    # Enviar resposta
    await adapter.send_message(resposta)

    return {"ok": True}
