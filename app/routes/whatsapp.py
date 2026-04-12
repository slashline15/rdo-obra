"""
Gateway legado do WhatsApp.

Este módulo foi aposentado em favor de `/whatsapp/webhook`, que recebe
os webhooks da Evolution API e passa pelo orquestrador atual.
"""
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/whatsapp", tags=["WhatsApp Gateway"])


@router.post("/webhook")
async def processar_mensagem(*args, **kwargs):
    raise HTTPException(
        status_code=410,
        detail="Gateway legado desativado. Use /whatsapp/webhook com Evolution API.",
    )
