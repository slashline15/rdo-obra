"""Webhook route para Evolution API (WhatsApp) — multi-instância."""
import logging

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.adapters.whatsapp import WhatsAppAdapter
from app.core.orchestrator import Orchestrator
from app.core.time import utc_now
from app.database import get_db
from app.models import WhatsAppInstancia

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/whatsapp", tags=["WhatsApp"])


def _normalizar_evento(evento: str | None) -> str:
    if not evento:
        return ""
    return str(evento).strip().lower().replace("_", ".").replace("-", ".")


def _extrair_key(payload: dict) -> dict:
    if isinstance(payload.get("messages"), list) and payload["messages"]:
        primeiro = payload["messages"][0] or {}
        return primeiro.get("key", {}) or {}
    return payload.get("key", {}) or {}


def _adapter_para(nome_instancia: str) -> WhatsAppAdapter:
    """Retorna um adapter configurado para a instância correta."""
    return WhatsAppAdapter(instance_override=nome_instancia)


@router.post("/webhook")
@router.post("/webhook/{event_suffix}")
async def whatsapp_webhook(request: Request, db: Session = Depends(get_db), event_suffix: str = ""):
    """
    Recebe webhooks da Evolution API para todas as instâncias.

    O campo 'instance' no payload identifica qual instância enviou o evento,
    permitindo rotear a mensagem para o usuário correto.
    """
    raw_data = await request.json()

    # ── Identificar instância ────────────────────────────────────────────────
    nome_instancia: str = (
        raw_data.get("instance")
        or raw_data.get("instanceName")
        or ""
    )

    # ── Tratar eventos de status de conexão ─────────────────────────────────
    event_raw = raw_data.get("event", "")
    event = _normalizar_evento(event_raw)
    logger.debug("WA webhook: instance=%s event=%s keys=%s", nome_instancia, event_raw, list(raw_data.keys()))

    if event == "qrcode.updated":
        _handle_qrcode_updated(nome_instancia, raw_data)
        return {"ok": True}

    if event == "connection.update":
        _handle_connection_update(nome_instancia, raw_data, db)
        return {"ok": True}

    # Só processar mensagens recebidas
    if event and event not in {"messages.upsert"}:
        return {"ok": True}

    payload = raw_data.get("data", raw_data) or {}

    # Ignorar mensagens enviadas por nós
    key = _extrair_key(payload)
    if key.get("fromMe"):
        return {"ok": True}

    adapter = _adapter_para(nome_instancia)
    msg = await adapter.parse_incoming(raw_data)

    logger.info(
        "WA msg: tel=%s tipo=%s texto=%s audio=%s",
        msg.telefone, msg.tipo.value, repr((msg.texto or "")[:80]), msg.audio_path,
    )

    orchestrator = Orchestrator(db)
    resposta = await orchestrator.processar(msg)

    logger.info("WA resp: %s", repr(resposta.texto[:120]))
    await adapter.send_message(resposta)

    return {"ok": True}


def _handle_qrcode_updated(nome_instancia: str, raw_data: dict) -> None:
    """Armazena o QR code em cache para ser consultado via API."""
    if not nome_instancia:
        return
    from app.services import evolution as evo_svc
    data = raw_data.get("data", {}) or {}
    qr_data = {
        "base64": data.get("qrcode", {}).get("base64") or data.get("base64"),
        "code": data.get("qrcode", {}).get("code") or data.get("code"),
    }
    if qr_data.get("base64") or qr_data.get("code"):
        evo_svc.armazenar_qrcode(nome_instancia, qr_data)


def _handle_connection_update(nome_instancia: str, raw_data: dict, db: Session) -> None:
    """Atualiza o status da instância no banco quando a conexão muda."""
    if not nome_instancia:
        return

    data = raw_data.get("data", {}) or {}
    state = data.get("state") or data.get("status")  # "open" | "close" | "connecting"
    numero = data.get("wuid") or data.get("number")  # número conectado, se disponível

    inst = db.query(WhatsAppInstancia).filter(
        WhatsAppInstancia.nome_instancia == nome_instancia
    ).first()

    if not inst:
        return

    if state:
        inst.status = state
    if numero:
        inst.numero_bot = numero.replace("@s.whatsapp.net", "").replace("@lid", "")
    if state == "open":
        # Conexão estabelecida — QR não é mais necessário
        from app.services import evolution as evo_svc
        evo_svc.limpar_qrcode_cache(nome_instancia)
    inst.atualizado_em = utc_now()
    try:
        db.commit()
    except Exception as exc:
        logger.warning("Erro ao salvar status da instância %s: %s", nome_instancia, exc)
        db.rollback()
