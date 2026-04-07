"""Workflow de status do diário — rascunho → em_revisão → aprovado → reaberto."""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.auth import get_current_user
from app.core.permissions import can_approve_diario, ensure_obra_access, get_access_level, require_level
from app.core.time import utc_now
from app.models import DiarioDia, DiarioStatus, Usuario
from app.schemas import ExcluirDiarioRequest, TransicaoDiario
from app.services.audit import log_changes

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
    ensure_obra_access(current_user, obra_id, required_level=3)
    diario = _get_or_create(db, obra_id, data_ref, current_user)
    return _serialize(diario)


@router.post("/{obra_id}/{data_ref}/transicao")
def transicao(obra_id: int, data_ref: date, body: TransicaoDiario,
              db: Session = Depends(get_db),
              current_user: Usuario = Depends(get_current_user)):
    """Executa transição de status no diário."""
    ensure_obra_access(current_user, obra_id, required_level=2)
    diario = _get_or_create(db, obra_id, data_ref, current_user)
    acao = body.acao

    level = get_access_level(current_user)
    if acao in ACOES_ADMIN and not can_approve_diario(current_user):
        raise HTTPException(status_code=403, detail=f"Ação '{acao}' requer aprovação delegada")
    if level > 2:
        raise HTTPException(status_code=403, detail="Usuário operacional não pode alterar status do diário")

    transicoes_possiveis = TRANSICOES.get(diario.status, {})
    novo_status = transicoes_possiveis.get(acao)
    if not novo_status:
        raise HTTPException(
            status_code=400,
            detail=f"Transição inválida: '{acao}' a partir de '{diario.status.value}'"
        )

    # Executar transição
    old_values = {
        "status": diario.status.value if hasattr(diario.status, "value") else diario.status,
        "submetido_por_id": diario.submetido_por_id,
        "submetido_em": diario.submetido_em,
        "aprovado_por_id": diario.aprovado_por_id,
        "aprovado_em": diario.aprovado_em,
        "observacao_aprovacao": diario.observacao_aprovacao,
        "pdf_path": diario.pdf_path,
    }

    diario.status = novo_status

    if acao == "submeter":
        diario.submetido_por_id = current_user.id
        diario.submetido_em = utc_now()
        diario.pdf_path = None
    elif acao == "aprovar":
        diario.aprovado_por_id = current_user.id
        diario.aprovado_em = utc_now()
        diario.observacao_aprovacao = body.observacao
    elif acao == "rejeitar":
        diario.submetido_por_id = None
        diario.submetido_em = None
        diario.observacao_aprovacao = body.observacao
        diario.pdf_path = None
    elif acao == "reabrir":
        diario.aprovado_por_id = None
        diario.aprovado_em = None
        diario.pdf_path = None

    new_values = {
        "status": diario.status.value if hasattr(diario.status, "value") else diario.status,
        "submetido_por_id": diario.submetido_por_id,
        "submetido_em": diario.submetido_em,
        "aprovado_por_id": diario.aprovado_por_id,
        "aprovado_em": diario.aprovado_em,
        "observacao_aprovacao": diario.observacao_aprovacao,
        "pdf_path": diario.pdf_path,
    }
    log_changes(db, obra_id, data_ref, "diarios_dia", diario.id, old_values, new_values, current_user.id)
    db.commit()
    db.refresh(diario)
    return _serialize(diario)


@router.delete("/{obra_id}/{data_ref}")
def excluir_diario(
    obra_id: int,
    data_ref: date,
    body: ExcluirDiarioRequest | None = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    ensure_obra_access(current_user, obra_id, required_level=1)
    diario = db.query(DiarioDia).filter(
        DiarioDia.obra_id == obra_id,
        DiarioDia.data == data_ref,
    ).first()
    if not diario:
        raise HTTPException(status_code=404, detail="Diário não encontrado")
    if diario.deletado_em:
        return _serialize(diario)

    old_values = {
        "deletado_em": diario.deletado_em,
        "deletado_por_id": diario.deletado_por_id,
        "motivo_exclusao": diario.motivo_exclusao,
        "pdf_path": diario.pdf_path,
    }
    diario.deletado_em = utc_now()
    diario.deletado_por_id = current_user.id
    diario.motivo_exclusao = body.motivo if body else None
    diario.pdf_path = None
    log_changes(
        db,
        obra_id,
        data_ref,
        "diarios_dia",
        diario.id,
        old_values,
        {
            "deletado_em": diario.deletado_em,
            "deletado_por_id": diario.deletado_por_id,
            "motivo_exclusao": diario.motivo_exclusao,
            "pdf_path": diario.pdf_path,
        },
        current_user.id,
    )
    db.commit()
    db.refresh(diario)
    return _serialize(diario)


@router.get("/lixeira")
def listar_lixeira_global(
    obra_id: int | None = None,
    data_inicio: date | None = None,
    data_fim: date | None = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_level(1)),
):
    query = db.query(DiarioDia).filter(DiarioDia.deletado_em.isnot(None))
    if obra_id is not None:
        query = query.filter(DiarioDia.obra_id == obra_id)
    if data_inicio is not None:
        query = query.filter(DiarioDia.data >= data_inicio)
    if data_fim is not None:
        query = query.filter(DiarioDia.data <= data_fim)
    diarios = query.order_by(DiarioDia.data.desc()).all()
    return [_serialize(diario) for diario in diarios]


@router.get("/lixeira/obra/{obra_id}")
def listar_lixeira(
    obra_id: int,
    data_inicio: date | None = None,
    data_fim: date | None = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    ensure_obra_access(current_user, obra_id, required_level=1)
    diarios = db.query(DiarioDia).filter(
        DiarioDia.obra_id == obra_id,
        DiarioDia.deletado_em.isnot(None),
    )
    if data_inicio is not None:
        diarios = diarios.filter(DiarioDia.data >= data_inicio)
    if data_fim is not None:
        diarios = diarios.filter(DiarioDia.data <= data_fim)
    diarios = diarios.order_by(DiarioDia.data.desc()).all()
    return [_serialize(diario) for diario in diarios]


@router.post("/{obra_id}/{data_ref}/restaurar")
def restaurar_diario(
    obra_id: int,
    data_ref: date,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    ensure_obra_access(current_user, obra_id, required_level=1)
    diario = db.query(DiarioDia).filter(
        DiarioDia.obra_id == obra_id,
        DiarioDia.data == data_ref,
    ).first()
    if not diario:
        raise HTTPException(status_code=404, detail="Diário não encontrado")
    old_values = {
        "deletado_em": diario.deletado_em,
        "deletado_por_id": diario.deletado_por_id,
        "motivo_exclusao": diario.motivo_exclusao,
    }
    diario.deletado_em = None
    diario.deletado_por_id = None
    diario.motivo_exclusao = None
    log_changes(
        db,
        obra_id,
        data_ref,
        "diarios_dia",
        diario.id,
        old_values,
        {
            "deletado_em": diario.deletado_em,
            "deletado_por_id": diario.deletado_por_id,
            "motivo_exclusao": diario.motivo_exclusao,
        },
        current_user.id,
    )
    db.commit()
    db.refresh(diario)
    return _serialize(diario)


def _get_or_create(db: Session, obra_id: int, data_ref: date, current_user: Usuario) -> DiarioDia:
    diario = db.query(DiarioDia).filter(
        DiarioDia.obra_id == obra_id, DiarioDia.data == data_ref
    ).first()
    if diario and diario.deletado_em and get_access_level(current_user) > 1:
        raise HTTPException(status_code=404, detail="Diário removido para esta obra")
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
        "deletado_em": str(d.deletado_em) if d.deletado_em else None,
        "deletado_por_id": d.deletado_por_id,
        "motivo_exclusao": d.motivo_exclusao,
    }
