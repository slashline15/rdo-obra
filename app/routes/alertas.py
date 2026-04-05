"""Rotas de alertas — listar, avaliar, resolver."""
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.auth import get_current_user
from app.models import Alerta, Usuario
from app.services.alert_engine import avaliar_alertas

router = APIRouter(prefix="/alertas", tags=["Alertas"])


@router.get("/{obra_id}/{data_ref}")
def listar_alertas(obra_id: int, data_ref: date, db: Session = Depends(get_db),
                   current_user: Usuario = Depends(get_current_user)):
    """Lista alertas de um dia (sem reavaliar)."""
    alertas = db.query(Alerta).filter(
        Alerta.obra_id == obra_id, Alerta.data == data_ref
    ).order_by(Alerta.severidade, Alerta.created_at).all()
    return [_serialize(a) for a in alertas]


@router.post("/avaliar/{obra_id}/{data_ref}")
def avaliar(obra_id: int, data_ref: date, db: Session = Depends(get_db),
            current_user: Usuario = Depends(get_current_user)):
    """Roda as 5 regras de alerta e retorna estado atualizado."""
    alertas = avaliar_alertas(db, obra_id, data_ref)
    total = {"alta": 0, "media": 0, "baixa": 0}
    for a in alertas:
        sev = a.severidade.value if hasattr(a.severidade, 'value') else a.severidade
        if not a.resolvido and sev in total:
            total[sev] += 1
    return {
        "alertas": [_serialize(a) for a in alertas],
        "total_por_severidade": total,
    }


@router.put("/{alerta_id}/resolver")
def resolver_alerta(alerta_id: int, observacao: str = None,
                    db: Session = Depends(get_db),
                    current_user: Usuario = Depends(get_current_user)):
    """Marca alerta como resolvido manualmente."""
    alerta = db.query(Alerta).filter(Alerta.id == alerta_id).first()
    if not alerta:
        raise HTTPException(status_code=404, detail="Alerta não encontrado")
    alerta.resolvido = True
    alerta.resolvido_por_id = current_user.id
    alerta.resolvido_em = datetime.utcnow()
    db.commit()
    return _serialize(alerta)


def _serialize(a: Alerta) -> dict:
    return {
        "id": a.id,
        "regra": a.regra,
        "severidade": a.severidade.value if hasattr(a.severidade, 'value') else a.severidade,
        "mensagem": a.mensagem,
        "resolvido": a.resolvido,
        "dados_contexto": a.dados_contexto,
        "created_at": str(a.created_at) if a.created_at else None,
    }
