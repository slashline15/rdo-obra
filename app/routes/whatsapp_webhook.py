"""Webhook route para Evolution API (WhatsApp)."""
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.adapters.whatsapp import WhatsAppAdapter
from app.core.orchestrator import Orchestrator
from app.database import get_db

router = APIRouter(prefix="/whatsapp", tags=["WhatsApp"])
adapter = WhatsAppAdapter()


def _normalizar_evento(evento: str | None) -> str:
    if not evento:
        return ""
    return str(evento).strip().lower().replace("_", ".").replace("-", ".")


def _extrair_key(payload: dict) -> dict:
    if isinstance(payload.get("messages"), list) and payload["messages"]:
        primeiro = payload["messages"][0] or {}
        return primeiro.get("key", {}) or {}
    return payload.get("key", {}) or {}


@router.post("/webhook")
async def whatsapp_webhook(request: Request, db: Session = Depends(get_db)):
    """Recebe webhooks da Evolution API."""
    raw_data = await request.json()
    payload = raw_data.get("data", raw_data) or {}

    # Só processar mensagens recebidas
    event = _normalizar_evento(raw_data.get("event") or payload.get("event"))
    if event and event not in {"messages.upsert"}:
        return {"ok": True}

    # Ignorar mensagens enviadas por nós
    key = _extrair_key(payload)
    if key.get("fromMe"):
        return {"ok": True}

    msg = await adapter.parse_incoming(raw_data)

    orchestrator = Orchestrator(db)
    resposta = await orchestrator.processar(msg)

    await adapter.send_message(resposta)

    return {"ok": True}
