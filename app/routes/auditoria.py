"""Rotas de auditoria — trilha de alterações."""
from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.auth import get_current_user
from app.models import AuditLog, Usuario

router = APIRouter(prefix="/auditoria", tags=["Auditoria"])


@router.get("/{obra_id}/{data_ref}")
def listar_auditoria(obra_id: int, data_ref: date,
                     tabela: str = None, registro_id: int = None,
                     db: Session = Depends(get_db),
                     current_user: Usuario = Depends(get_current_user)):
    """Lista alterações de um dia, com filtros opcionais por tabela e registro."""
    query = db.query(AuditLog).filter(
        AuditLog.obra_id == obra_id, AuditLog.data_ref == data_ref
    )
    if tabela:
        query = query.filter(AuditLog.tabela == tabela)
    if registro_id:
        query = query.filter(AuditLog.registro_id == registro_id)

    logs = query.order_by(AuditLog.created_at.desc()).all()
    return [_serialize(log) for log in logs]


def _serialize(log: AuditLog) -> dict:
    return {
        "id": log.id,
        "tabela": log.tabela,
        "registro_id": log.registro_id,
        "campo": log.campo,
        "valor_anterior": log.valor_anterior,
        "valor_novo": log.valor_novo,
        "usuario_id": log.usuario_id,
        "created_at": str(log.created_at) if log.created_at else None,
    }
