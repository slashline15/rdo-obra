from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import date

from app.database import get_db
from app.models import Anotacao
from app.schemas import AnotacaoCreate, AnotacaoResponse, AnotacaoUpdate
from app.core.auth import get_current_user
from app.core.diary_lock import check_diary_editable
from app.core.permissions import ensure_obra_access, resolve_obra_scope, scope_query_to_user
from app.services.audit import log_changes

router = APIRouter(prefix="/anotacoes", tags=["Anotações"])


@router.post("/", response_model=AnotacaoResponse)
def criar_anotacao(anotacao: AnotacaoCreate, db: Session = Depends(get_db),
                   current_user=Depends(get_current_user)):
    data = anotacao.model_dump()
    if not data.get("data"):
        data["data"] = date.today()
    data["obra_id"] = resolve_obra_scope(current_user, data.get("obra_id"), require_explicit=True)
    db_anotacao = Anotacao(**data)
    db.add(db_anotacao)
    db.commit()
    db.refresh(db_anotacao)
    return db_anotacao


@router.get("/", response_model=List[AnotacaoResponse])
def listar_anotacoes(obra_id: int = None, data_ref: date = None, tipo: str = None, db: Session = Depends(get_db),
                     current_user=Depends(get_current_user)):
    query = scope_query_to_user(db.query(Anotacao), Anotacao, current_user)
    scoped_obra_id = resolve_obra_scope(current_user, obra_id, require_explicit=False)
    if scoped_obra_id:
        query = query.filter(Anotacao.obra_id == scoped_obra_id)
    if data_ref:
        query = query.filter(Anotacao.data == data_ref)
    if tipo:
        query = query.filter(Anotacao.tipo == tipo)
    return query.order_by(Anotacao.created_at.desc()).all()


@router.get("/{anotacao_id}", response_model=AnotacaoResponse)
def buscar_anotacao(anotacao_id: int, db: Session = Depends(get_db),
                    current_user=Depends(get_current_user)):
    anotacao = db.query(Anotacao).filter(Anotacao.id == anotacao_id).first()
    if not anotacao:
        raise HTTPException(status_code=404, detail="Anotação não encontrada")
    ensure_obra_access(current_user, anotacao.obra_id, required_level=3)
    return anotacao


@router.put("/{anotacao_id}", response_model=AnotacaoResponse)
def atualizar_anotacao(anotacao_id: int, dados: AnotacaoUpdate, db: Session = Depends(get_db),
                       current_user=Depends(get_current_user)):
    anotacao = db.query(Anotacao).filter(Anotacao.id == anotacao_id).first()
    if not anotacao:
        raise HTTPException(status_code=404, detail="Anotação não encontrada")
    ensure_obra_access(current_user, anotacao.obra_id, required_level=2)
    check_diary_editable(db, anotacao.obra_id, anotacao.data)
    updates = dados.model_dump(exclude_unset=True)
    old = {k: getattr(anotacao, k) for k in updates}
    log_changes(db, anotacao.obra_id, anotacao.data, "anotacoes", anotacao.id, old, updates, current_user.id)
    for key, value in updates.items():
        setattr(anotacao, key, value)
    db.commit()
    db.refresh(anotacao)
    return anotacao


@router.delete("/{anotacao_id}")
def deletar_anotacao(anotacao_id: int, db: Session = Depends(get_db),
                     current_user=Depends(get_current_user)):
    anotacao = db.query(Anotacao).filter(Anotacao.id == anotacao_id).first()
    if not anotacao:
        raise HTTPException(status_code=404, detail="Anotação não encontrada")
    ensure_obra_access(current_user, anotacao.obra_id, required_level=2)
    check_diary_editable(db, anotacao.obra_id, anotacao.data)
    db.delete(anotacao)
    db.commit()
    return {"detail": "Anotação removida"}
