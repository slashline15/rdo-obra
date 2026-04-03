from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models import Obra
from app.schemas import ObraCreate, ObraResponse

router = APIRouter(prefix="/obras", tags=["Obras"])


@router.post("/", response_model=ObraResponse)
def criar_obra(obra: ObraCreate, db: Session = Depends(get_db)):
    db_obra = Obra(**obra.model_dump())
    db.add(db_obra)
    db.commit()
    db.refresh(db_obra)
    return db_obra


@router.get("/", response_model=List[ObraResponse])
def listar_obras(status: str = None, db: Session = Depends(get_db)):
    query = db.query(Obra)
    if status:
        query = query.filter(Obra.status == status)
    return query.all()


@router.get("/{obra_id}", response_model=ObraResponse)
def buscar_obra(obra_id: int, db: Session = Depends(get_db)):
    obra = db.query(Obra).filter(Obra.id == obra_id).first()
    if not obra:
        raise HTTPException(status_code=404, detail="Obra não encontrada")
    return obra


@router.put("/{obra_id}", response_model=ObraResponse)
def atualizar_obra(obra_id: int, dados: ObraCreate, db: Session = Depends(get_db)):
    obra = db.query(Obra).filter(Obra.id == obra_id).first()
    if not obra:
        raise HTTPException(status_code=404, detail="Obra não encontrada")
    for key, value in dados.model_dump().items():
        setattr(obra, key, value)
    db.commit()
    db.refresh(obra)
    return obra


@router.delete("/{obra_id}")
def deletar_obra(obra_id: int, db: Session = Depends(get_db)):
    obra = db.query(Obra).filter(Obra.id == obra_id).first()
    if not obra:
        raise HTTPException(status_code=404, detail="Obra não encontrada")
    db.delete(obra)
    db.commit()
    return {"detail": "Obra removida"}
