from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import date
from sqlalchemy import func

from app.database import get_db
from app.models import Efetivo
from app.schemas import EfetivoCreate, EfetivoResponse, EfetivoUpdate
from app.core.auth import get_current_user
from app.core.diary_lock import check_diary_editable
from app.core.permissions import ensure_obra_access, resolve_obra_scope, scope_query_to_user
from app.services.audit import log_changes

router = APIRouter(prefix="/efetivo", tags=["Efetivo"])


@router.post("/", response_model=EfetivoResponse)
def criar_efetivo(
    efetivo: EfetivoCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    data = efetivo.model_dump()
    if not data.get("data"):
        data["data"] = date.today()
    data["obra_id"] = resolve_obra_scope(current_user, data.get("obra_id"), require_explicit=True)
    db_efetivo = Efetivo(**data)
    db.add(db_efetivo)
    db.commit()
    db.refresh(db_efetivo)
    return db_efetivo


@router.post("/batch", response_model=List[EfetivoResponse])
def criar_efetivo_batch(
    efetivos: List[EfetivoCreate],
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Cria múltiplos registros de efetivo de uma vez (ex: '8 pedreiros, 4 serventes')"""
    result = []
    for ef in efetivos:
        data = ef.model_dump()
        if not data.get("data"):
            data["data"] = date.today()
        data["obra_id"] = resolve_obra_scope(current_user, data.get("obra_id"), require_explicit=True)
        db_ef = Efetivo(**data)
        db.add(db_ef)
        result.append(db_ef)
    db.commit()
    for r in result:
        db.refresh(r)
    return result


@router.get("/", response_model=List[EfetivoResponse])
def listar_efetivo(
    obra_id: int = None,
    data_ref: date = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    query = scope_query_to_user(db.query(Efetivo), Efetivo, current_user)
    scoped_obra_id = resolve_obra_scope(current_user, obra_id, require_explicit=False)
    if scoped_obra_id:
        query = query.filter(Efetivo.obra_id == scoped_obra_id)
    if data_ref:
        query = query.filter(Efetivo.data == data_ref)
    return query.order_by(Efetivo.data.desc()).all()


@router.get("/resumo/{obra_id}")
def resumo_efetivo(obra_id: int, data_ref: date = None, db: Session = Depends(get_db),
                   current_user=Depends(get_current_user)):
    """Retorna resumo do efetivo (total por função) para uma obra/data"""
    ensure_obra_access(current_user, obra_id, required_level=3)
    if not data_ref:
        data_ref = date.today()
    registros = db.query(
        Efetivo.funcao,
        func.sum(Efetivo.quantidade).label("total")
    ).filter(
        Efetivo.obra_id == obra_id,
        Efetivo.data == data_ref
    ).group_by(Efetivo.funcao).all()

    total_geral = sum(r.total for r in registros)
    return {
        "data": str(data_ref),
        "obra_id": obra_id,
        "total": total_geral,
        "por_funcao": [{"funcao": r.funcao, "quantidade": r.total} for r in registros]
    }


@router.get("/{efetivo_id}", response_model=EfetivoResponse)
def buscar_efetivo(efetivo_id: int, db: Session = Depends(get_db),
                   current_user=Depends(get_current_user)):
    efetivo = db.query(Efetivo).filter(Efetivo.id == efetivo_id).first()
    if not efetivo:
        raise HTTPException(status_code=404, detail="Registro de efetivo não encontrado")
    ensure_obra_access(current_user, efetivo.obra_id, required_level=3)
    return efetivo


@router.put("/{efetivo_id}", response_model=EfetivoResponse)
def atualizar_efetivo(efetivo_id: int, dados: EfetivoUpdate, db: Session = Depends(get_db),
                      current_user=Depends(get_current_user)):
    efetivo = db.query(Efetivo).filter(Efetivo.id == efetivo_id).first()
    if not efetivo:
        raise HTTPException(status_code=404, detail="Registro de efetivo não encontrado")
    ensure_obra_access(current_user, efetivo.obra_id, required_level=2)
    check_diary_editable(db, efetivo.obra_id, efetivo.data)
    updates = dados.model_dump(exclude_unset=True)
    old = {k: getattr(efetivo, k) for k in updates}
    log_changes(db, efetivo.obra_id, efetivo.data, "efetivo", efetivo.id, old, updates, current_user.id)
    for key, value in updates.items():
        setattr(efetivo, key, value)
    db.commit()
    db.refresh(efetivo)
    return efetivo


@router.delete("/{efetivo_id}")
def deletar_efetivo(efetivo_id: int, db: Session = Depends(get_db),
                    current_user=Depends(get_current_user)):
    efetivo = db.query(Efetivo).filter(Efetivo.id == efetivo_id).first()
    if not efetivo:
        raise HTTPException(status_code=404, detail="Registro de efetivo não encontrado")
    ensure_obra_access(current_user, efetivo.obra_id, required_level=2)
    check_diary_editable(db, efetivo.obra_id, efetivo.data)
    db.delete(efetivo)
    db.commit()
    return {"detail": "Registro removido"}
