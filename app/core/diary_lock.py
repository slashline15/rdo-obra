"""Helper para verificar se um diário pode ser editado."""
from datetime import date
from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.models import DiarioDia, DiarioStatus


def check_diary_editable(db: Session, obra_id: int, data_ref: date):
    """Levanta 423 Locked se o diário está aprovado."""
    diario = db.query(DiarioDia).filter(
        DiarioDia.obra_id == obra_id,
        DiarioDia.data == data_ref
    ).first()
    if diario and diario.status == DiarioStatus.APROVADO:
        raise HTTPException(
            status_code=423,
            detail="Diário aprovado — edição bloqueada. Reabra o diário para editar."
        )
