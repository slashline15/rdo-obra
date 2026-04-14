"""
Cliente para a Evolution API v2.
Gerencia o ciclo de vida das instâncias WhatsApp por usuário.

Fluxo do QR code (Evolution v2 Baileys):
  1. `criar_instancia()` → Evolution inicia conexão e emite evento QRCODE_UPDATED
  2. O webhook recebe o evento e chama `armazenar_qrcode()`
  3. O admin chama `GET /api/whatsapp/instancias/{id}/qrcode` → retorna do cache
  4. Após scan, Evolution emite CONNECTION_UPDATE com state="open"
"""
from __future__ import annotations

import os
import httpx
from app.core.config import settings

_TIMEOUT = httpx.Timeout(20.0, connect=10.0)

# Cache em memória: nome_instancia → {"base64": "...", "code": "..."}
# Válido apenas até o QR ser escaneado ou expirar
_qrcode_cache: dict[str, dict] = {}


def armazenar_qrcode(nome_instancia: str, dados_qr: dict) -> None:
    """Chamado pelo webhook quando um QRCODE_UPDATED é recebido."""
    _qrcode_cache[nome_instancia] = dados_qr


def obter_qrcode_cache(nome_instancia: str) -> dict | None:
    """Retorna o QR code armazenado em cache, se disponível."""
    return _qrcode_cache.get(nome_instancia)


def limpar_qrcode_cache(nome_instancia: str) -> None:
    """Remove QR do cache após conexão estabelecida."""
    _qrcode_cache.pop(nome_instancia, None)


def _headers() -> dict:
    return {"apikey": settings.evolution_api_key or "", "Content-Type": "application/json"}


def _base() -> str:
    return (settings.evolution_api_url or "http://localhost:8080").rstrip("/")


def _webhook_url() -> str:
    """
    Em produção: URL pública (Cloudflare).
    Em dev local: usa localhost para que o Evolution (host mode) alcance o backend.
    """
    debug = getattr(settings, "debug", False)
    if debug:
        # Evolution roda em host mode → localhost é o próprio host WSL
        port = os.environ.get("BACKEND_PORT", "8000")
        return f"http://localhost:{port}/whatsapp/webhook"
    return f"{settings.public_url}/whatsapp/webhook"


async def criar_instancia(nome: str) -> dict:
    """Cria uma nova instância no Evolution API."""
    payload = {
        "instanceName": nome,
        "qrcode": True,
        "integration": "WHATSAPP-BAILEYS",
        "webhook": _webhook_url(),
        "webhookByEvents": False,
        "webhookBase64": False,
        "events": [
            "MESSAGES_UPSERT",
            "CONNECTION_UPDATE",
            "QRCODE_UPDATED",
        ],
    }
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.post(
            f"{_base()}/instance/create",
            headers=_headers(),
            json=payload,
        )
        resp.raise_for_status()
        return resp.json()


async def obter_qrcode(nome: str) -> dict:
    """Retorna o QR code atual da instância (base64 + código)."""
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.get(
            f"{_base()}/instance/connect/{nome}",
            headers=_headers(),
        )
        resp.raise_for_status()
        return resp.json()


async def status_instancia(nome: str) -> dict:
    """Retorna o estado de conexão da instância."""
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.get(
            f"{_base()}/instance/connectionState/{nome}",
            headers=_headers(),
        )
        resp.raise_for_status()
        return resp.json()


async def deletar_instancia(nome: str) -> bool:
    """Remove a instância do Evolution API."""
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.delete(
            f"{_base()}/instance/delete/{nome}",
            headers=_headers(),
        )
        return resp.status_code in (200, 204)


async def configurar_webhook(nome: str) -> bool:
    """(Re)configura o webhook de uma instância já criada."""
    payload = {
        "webhook": {
            "url": _webhook_url(),
            "byEvents": False,
            "base64": False,
            "enabled": True,
            "events": [
                "MESSAGES_UPSERT",
                "CONNECTION_UPDATE",
                "QRCODE_UPDATED",
            ],
        }
    }
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.post(
            f"{_base()}/webhook/set/{nome}",
            headers=_headers(),
            json=payload,
        )
        return resp.status_code == 200


async def listar_instancias() -> list[dict]:
    """Lista todas as instâncias registradas no Evolution."""
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.get(
            f"{_base()}/instance/fetchInstances",
            headers=_headers(),
        )
        resp.raise_for_status()
        data = resp.json()
        return data if isinstance(data, list) else []


async def logout_instancia(nome: str) -> bool:
    """Desconecta (logout) do WhatsApp sem deletar a instância."""
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.delete(
            f"{_base()}/instance/logout/{nome}",
            headers=_headers(),
        )
        return resp.status_code in (200, 204)
