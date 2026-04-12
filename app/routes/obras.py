from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models import Obra
from app.schemas import ObraCreate, ObraResponse
from app.core.auth import get_current_user
from app.core.permissions import ensure_obra_access, get_access_level

router = APIRouter(prefix="/obras", tags=["Obras"])


def _require_adminish(current_user) -> None:
    if get_access_level(current_user) != 1:
        raise HTTPException(status_code=403, detail="Acesso negado. Necessário: admin")


@router.post("", response_model=ObraResponse)
@router.post("/", response_model=ObraResponse)
def criar_obra(
    obra: ObraCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    _require_adminish(current_user)
    db_obra = Obra(**obra.model_dump())
    db.add(db_obra)
    db.commit()
    db.refresh(db_obra)
    return db_obra


@router.get("", response_model=List[ObraResponse])
@router.get("/", response_model=List[ObraResponse])
def listar_obras(
    status: str = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    query = db.query(Obra)
    if get_access_level(current_user) > 1:
        if current_user.obra_id is None:
            return []
        query = query.filter(Obra.id == current_user.obra_id)
    if status:
        query = query.filter(Obra.status == status)
    return query.all()


@router.get("/{obra_id}", response_model=ObraResponse)
def buscar_obra(
    obra_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    obra = db.query(Obra).filter(Obra.id == obra_id).first()
    if not obra:
        raise HTTPException(status_code=404, detail="Obra não encontrada")
    ensure_obra_access(current_user, obra.id, required_level=3)
    return obra


@router.put("/{obra_id}", response_model=ObraResponse)
def atualizar_obra(
    obra_id: int,
    dados: ObraCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    obra = db.query(Obra).filter(Obra.id == obra_id).first()
    if not obra:
        raise HTTPException(status_code=404, detail="Obra não encontrada")
    ensure_obra_access(current_user, obra.id, required_level=2)
    for key, value in dados.model_dump().items():
        setattr(obra, key, value)
    db.commit()
    db.refresh(obra)
    return obra


@router.delete("/{obra_id}")
def deletar_obra(
    obra_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    _require_adminish(current_user)
    obra = db.query(Obra).filter(Obra.id == obra_id).first()
    if not obra:
        raise HTTPException(status_code=404, detail="Obra não encontrada")
    db.delete(obra)
    db.commit()
    return {"detail": "Obra removida"}
