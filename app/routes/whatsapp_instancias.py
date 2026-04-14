"""
Gerenciamento de instâncias WhatsApp por usuário via Evolution API.

Cada usuário tem no máximo uma instância. O nome da instância é o telefone
normalizado (ex.: "5511999998888"). As obras acessíveis dependem do usuário.

Endpoints:
  POST   /api/whatsapp/instancias          — cria instância para um usuário
  GET    /api/whatsapp/instancias          — lista instâncias (admin)
  GET    /api/whatsapp/instancias/me       — instância do usuário logado
  GET    /api/whatsapp/instancias/{id}/qrcode  — QR code para conectar
  POST   /api/whatsapp/instancias/{id}/reconectar  — dispara nova geração de QR
  DELETE /api/whatsapp/instancias/{id}    — remove instância
"""
from __future__ import annotations

import re

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.database import get_db
from app.models import Usuario, WhatsAppInstancia
from app import services


def _exige_admin(usuario: Usuario) -> None:
    """Lança 403 se o usuário não for admin (nivel_acesso == 1)."""
    if usuario.nivel_acesso > 1:
        raise HTTPException(status_code=403, detail="Acesso restrito a administradores")

router = APIRouter(prefix="/whatsapp/instancias", tags=["WhatsApp Instâncias"])


def _normalizar_telefone(telefone: str) -> str:
    """Remove tudo que não for dígito."""
    return re.sub(r"\D", "", telefone)


# ── Schemas ──────────────────────────────────────────────────────────────────

class CriarInstanciaRequest(BaseModel):
    usuario_id: int


class InstanciaOut(BaseModel):
    id: int
    usuario_id: int
    nome_instancia: str
    numero_bot: str | None
    status: str
    webhook_configurado: bool

    class Config:
        from_attributes = True


# ── Helpers ──────────────────────────────────────────────────────────────────

def _get_instancia_or_404(instancia_id: int, db: Session) -> WhatsAppInstancia:
    inst = db.get(WhatsAppInstancia, instancia_id)
    if not inst:
        raise HTTPException(status_code=404, detail="Instância não encontrada")
    return inst


# ── Rotas ─────────────────────────────────────────────────────────────────────

@router.post("", response_model=InstanciaOut, status_code=status.HTTP_201_CREATED)
async def criar_instancia(
    body: CriarInstanciaRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Cria instância WhatsApp para um usuário. Requer nível de acesso 1 (admin)."""
    _exige_admin(current_user)

    usuario = db.get(Usuario, body.usuario_id)
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    # Verificar se já existe instância
    existente = db.query(WhatsAppInstancia).filter(
        WhatsAppInstancia.usuario_id == body.usuario_id
    ).first()
    if existente:
        raise HTTPException(
            status_code=400,
            detail=f"Usuário já possui instância '{existente.nome_instancia}'",
        )

    nome = _normalizar_telefone(usuario.telefone)
    if not nome:
        raise HTTPException(status_code=400, detail="Telefone do usuário inválido")

    # Criar no Evolution API
    try:
        from app.services import evolution
        await evolution.criar_instancia(nome)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Erro ao criar instância no Evolution API: {exc}",
        )

    # Persistir no banco
    instancia = WhatsAppInstancia(
        usuario_id=body.usuario_id,
        nome_instancia=nome,
        status="pending",
        webhook_configurado=True,  # webhook já configurado no create
    )
    db.add(instancia)
    db.commit()
    db.refresh(instancia)
    return instancia


@router.get("", response_model=list[InstanciaOut])
def listar_instancias(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Lista todas as instâncias. Requer admin."""
    _exige_admin(current_user)
    return db.query(WhatsAppInstancia).all()


@router.get("/me", response_model=InstanciaOut)
def minha_instancia(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Retorna a instância WhatsApp do usuário logado."""
    inst = db.query(WhatsAppInstancia).filter(
        WhatsAppInstancia.usuario_id == current_user.id
    ).first()
    if not inst:
        raise HTTPException(status_code=404, detail="Nenhuma instância configurada para este usuário")
    return inst


@router.get("/{instancia_id}/qrcode")
async def obter_qrcode(
    instancia_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Retorna QR code para conexão da instância."""
    inst = _get_instancia_or_404(instancia_id, db)

    # Usuário comum só acessa a própria instância; admin acessa qualquer
    if current_user.nivel_acesso > 1 and inst.usuario_id != current_user.id:
        raise HTTPException(status_code=403, detail="Acesso negado")

    from app.services import evolution

    # 1. Tentar cache (QR entregue via webhook)
    qr_cache = evolution.obter_qrcode_cache(inst.nome_instancia)
    if qr_cache:
        return qr_cache

    # 2. Consultar status atual e informar se já conectado
    try:
        dados = await evolution.status_instancia(inst.nome_instancia)
        state = dados.get("instance", {}).get("state", "")
        if state == "open":
            return {"status": "connected", "message": "Instância já conectada ao WhatsApp"}
    except Exception:
        pass

    return {
        "status": "waiting",
        "message": "QR code ainda não gerado. Aguarde alguns segundos e tente novamente.",
    }


@router.get("/{instancia_id}/status")
async def status_instancia(
    instancia_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Retorna o estado de conexão da instância no Evolution."""
    inst = _get_instancia_or_404(instancia_id, db)

    if current_user.nivel_acesso > 1 and inst.usuario_id != current_user.id:
        raise HTTPException(status_code=403, detail="Acesso negado")

    try:
        from app.services import evolution
        dados = await evolution.status_instancia(inst.nome_instancia)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Erro ao buscar status: {exc}")

    # Atualizar status no banco se mudou
    novo_status = dados.get("instance", {}).get("state", inst.status)
    if novo_status != inst.status:
        inst.status = novo_status
        db.commit()

    return {"id": inst.id, "nome_instancia": inst.nome_instancia, "status": dados}


@router.post("/{instancia_id}/reconectar")
async def reconectar(
    instancia_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Dispara nova geração de QR code (logout + reconectar)."""
    inst = _get_instancia_or_404(instancia_id, db)

    if current_user.nivel_acesso > 1 and inst.usuario_id != current_user.id:
        raise HTTPException(status_code=403, detail="Acesso negado")

    try:
        from app.services import evolution
        await evolution.logout_instancia(inst.nome_instancia)
        dados = await evolution.obter_qrcode(inst.nome_instancia)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Erro ao reconectar: {exc}")

    inst.status = "connecting"
    db.commit()
    return dados


@router.delete("/{instancia_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deletar_instancia(
    instancia_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Remove instância do Evolution API e do banco. Requer admin."""
    _exige_admin(current_user)
    inst = _get_instancia_or_404(instancia_id, db)

    try:
        from app.services import evolution
        await evolution.deletar_instancia(inst.nome_instancia)
    except Exception:
        pass  # mesmo que falhe no Evolution, remove do banco

    db.delete(inst)
    db.commit()
