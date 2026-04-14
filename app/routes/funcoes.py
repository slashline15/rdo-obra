from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models import Funcao
from app.schemas import FuncaoCreate, FuncaoResponse, FuncaoUpdate
from app.core.auth import get_current_user

router = APIRouter(prefix="/funcoes", tags=["Funções"])


@router.post("/", response_model=FuncaoResponse)
def criar_funcao(
    funcao: FuncaoCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    existing = (
        db.query(Funcao)
        .filter(Funcao.nome == funcao.nome, Funcao.empresa_id == funcao.empresa_id)
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="Função já cadastrada para esta empresa")
    db_funcao = Funcao(**funcao.model_dump())
    db.add(db_funcao)
    db.commit()
    db.refresh(db_funcao)
    return db_funcao


@router.get("/", response_model=List[FuncaoResponse])
def listar_funcoes(
    empresa_id: int = None,
    ativa: bool = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    query = db.query(Funcao)
    if empresa_id is not None:
        query = query.filter(Funcao.empresa_id == empresa_id)
    if ativa is not None:
        query = query.filter(Funcao.ativa == ativa)
    return query.order_by(Funcao.nome).all()


@router.put("/{funcao_id}", response_model=FuncaoResponse)
def atualizar_funcao(
    funcao_id: int,
    dados: FuncaoUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    funcao = db.query(Funcao).filter(Funcao.id == funcao_id).first()
    if not funcao:
        raise HTTPException(status_code=404, detail="Função não encontrada")
    for key, value in dados.model_dump(exclude_unset=True).items():
        setattr(funcao, key, value)
    db.commit()
    db.refresh(funcao)
    return funcao


@router.delete("/{funcao_id}")
def deletar_funcao(
    funcao_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    funcao = db.query(Funcao).filter(Funcao.id == funcao_id).first()
    if not funcao:
        raise HTTPException(status_code=404, detail="Função não encontrada")
    funcao.ativa = False
    db.commit()
    return {"detail": "Função desativada"}
