from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import date

from app.database import get_db
from app.models import Anotacao
from app.schemas import AnotacaoCreate, AnotacaoResponse

router = APIRouter(prefix="/anotacoes", tags=["Anotações"])


@router.post("/", response_model=AnotacaoResponse)
def criar_anotacao(anotacao: AnotacaoCreate, db: Session = Depends(get_db)):
    data = anotacao.model_dump()
    if not data.get("data"):
        data["data"] = date.today()
    db_anotacao = Anotacao(**data)
    db.add(db_anotacao)
    db.commit()
    db.refresh(db_anotacao)
    return db_anotacao


@router.get("/", response_model=List[AnotacaoResponse])
def listar_anotacoes(obra_id: int = None, data_ref: date = None, tipo: str = None, db: Session = Depends(get_db)):
    query = db.query(Anotacao)
    if obra_id:
        query = query.filter(Anotacao.obra_id == obra_id)
    if data_ref:
        query = query.filter(Anotacao.data == data_ref)
    if tipo:
        query = query.filter(Anotacao.tipo == tipo)
    return query.order_by(Anotacao.created_at.desc()).all()


@router.get("/{anotacao_id}", response_model=AnotacaoResponse)
def buscar_anotacao(anotacao_id: int, db: Session = Depends(get_db)):
    anotacao = db.query(Anotacao).filter(Anotacao.id == anotacao_id).first()
    if not anotacao:
        raise HTTPException(status_code=404, detail="Anotação não encontrada")
    return anotacao


@router.put("/{anotacao_id}", response_model=AnotacaoResponse)
def atualizar_anotacao(anotacao_id: int, dados: AnotacaoCreate, db: Session = Depends(get_db)):
    anotacao = db.query(Anotacao).filter(Anotacao.id == anotacao_id).first()
    if not anotacao:
        raise HTTPException(status_code=404, detail="Anotação não encontrada")
    for key, value in dados.model_dump().items():
        if value is not None:
            setattr(anotacao, key, value)
    db.commit()
    db.refresh(anotacao)
    return anotacao


@router.delete("/{anotacao_id}")
def deletar_anotacao(anotacao_id: int, db: Session = Depends(get_db)):
    anotacao = db.query(Anotacao).filter(Anotacao.id == anotacao_id).first()
    if not anotacao:
        raise HTTPException(status_code=404, detail="Anotação não encontrada")
    db.delete(anotacao)
    db.commit()
    return {"detail": "Anotação removida"}
