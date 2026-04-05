"""Workflow de status do diário — rascunho → em_revisão → aprovado → reaberto."""
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.auth import get_current_user
from app.core.permissions import require_role
from app.models import DiarioDia, DiarioStatus, Usuario
from app.schemas import TransicaoDiario

router = APIRouter(prefix="/diario", tags=["Diário — Workflow"])

# Transições válidas: {de: {acao: para}}
TRANSICOES = {
    DiarioStatus.RASCUNHO: {"submeter": DiarioStatus.EM_REVISAO},
    DiarioStatus.EM_REVISAO: {
        "aprovar": DiarioStatus.APROVADO,
        "rejeitar": DiarioStatus.RASCUNHO,
    },
    DiarioStatus.APROVADO: {"reabrir": DiarioStatus.REABERTO},
    DiarioStatus.REABERTO: {"submeter": DiarioStatus.EM_REVISAO},
}

# Ações restritas a admin
ACOES_ADMIN = {"aprovar", "rejeitar", "reabrir"}


@router.get("/{obra_id}/{data_ref}")
def get_diario(obra_id: int, data_ref: date, db: Session = Depends(get_db),
               current_user: Usuario = Depends(get_current_user)):
    """Retorna ou auto-cria o diário de um dia."""
    diario = _get_or_create(db, obra_id, data_ref)
    return _serialize(diario)


@router.post("/{obra_id}/{data_ref}/transicao")
def transicao(obra_id: int, data_ref: date, body: TransicaoDiario,
              db: Session = Depends(get_db),
              current_user: Usuario = Depends(get_current_user)):
    """Executa transição de status no diário."""
    diario = _get_or_create(db, obra_id, data_ref)
    acao = body.acao

    # Verificar permissão
    role = current_user.role
    if role == "responsavel":
        role = "admin"
    if acao in ACOES_ADMIN and role not in ("admin",):
        raise HTTPException(status_code=403, detail=f"Ação '{acao}' restrita a admin")
    if role == "estagiario":
        raise HTTPException(status_code=403, detail="Estagiário não pode alterar status do diário")

    # Verificar transição válida
    transicoes_possiveis = TRANSICOES.get(diario.status, {})
    novo_status = transicoes_possiveis.get(acao)
    if not novo_status:
        raise HTTPException(
            status_code=400,
            detail=f"Transição inválida: '{acao}' a partir de '{diario.status.value}'"
        )

    # Executar transição
    diario.status = novo_status

    if acao == "submeter":
        diario.submetido_por_id = current_user.id
        diario.submetido_em = datetime.utcnow()
    elif acao == "aprovar":
        diario.aprovado_por_id = current_user.id
        diario.aprovado_em = datetime.utcnow()
        diario.observacao_aprovacao = body.observacao
    elif acao == "rejeitar":
        diario.submetido_por_id = None
        diario.submetido_em = None
        diario.observacao_aprovacao = body.observacao
    elif acao == "reabrir":
        diario.aprovado_por_id = None
        diario.aprovado_em = None

    db.commit()
    db.refresh(diario)
    return _serialize(diario)


def _get_or_create(db: Session, obra_id: int, data_ref: date) -> DiarioDia:
    diario = db.query(DiarioDia).filter(
        DiarioDia.obra_id == obra_id, DiarioDia.data == data_ref
    ).first()
    if not diario:
        diario = DiarioDia(obra_id=obra_id, data=data_ref, status=DiarioStatus.RASCUNHO)
        db.add(diario)
        db.commit()
        db.refresh(diario)
    return diario


def _serialize(d: DiarioDia) -> dict:
    return {
        "id": d.id,
        "obra_id": d.obra_id,
        "data": str(d.data),
        "status": d.status.value if hasattr(d.status, 'value') else d.status,
        "submetido_por_id": d.submetido_por_id,
        "submetido_em": str(d.submetido_em) if d.submetido_em else None,
        "aprovado_por_id": d.aprovado_por_id,
        "aprovado_em": str(d.aprovado_em) if d.aprovado_em else None,
        "observacao_aprovacao": d.observacao_aprovacao,
        "pdf_path": d.pdf_path,
    }
