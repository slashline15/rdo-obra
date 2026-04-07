from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import date

from app.database import get_db
from app.models import Clima, StatusPluviometrico
from app.schemas import ClimaCreate, ClimaResponse, ClimaUpdate
from app.core.auth import get_current_user
from app.core.diary_lock import check_diary_editable
from app.core.permissions import ensure_obra_access, resolve_obra_scope, scope_query_to_user
from app.services.audit import log_changes

router = APIRouter(prefix="/clima", tags=["Clima"])


@router.post("/", response_model=ClimaResponse)
def criar_clima(clima: ClimaCreate, db: Session = Depends(get_db),
                current_user=Depends(get_current_user)):
    data = clima.model_dump()
    if not data.get("data"):
        data["data"] = date.today()
    data["obra_id"] = resolve_obra_scope(current_user, data.get("obra_id"), require_explicit=True)
    db_clima = Clima(**data)
    db.add(db_clima)
    db.commit()
    db.refresh(db_clima)
    return db_clima


@router.get("/", response_model=List[ClimaResponse])
def listar_clima(obra_id: int = None, data_ref: date = None, db: Session = Depends(get_db),
                 current_user=Depends(get_current_user)):
    query = scope_query_to_user(db.query(Clima), Clima, current_user)
    scoped_obra_id = resolve_obra_scope(current_user, obra_id, require_explicit=False)
    if scoped_obra_id:
        query = query.filter(Clima.obra_id == scoped_obra_id)
    if data_ref:
        query = query.filter(Clima.data == data_ref)
    return query.order_by(Clima.data.desc()).all()


@router.get("/{clima_id}", response_model=ClimaResponse)
def buscar_clima(clima_id: int, db: Session = Depends(get_db),
                 current_user=Depends(get_current_user)):
    clima = db.query(Clima).filter(Clima.id == clima_id).first()
    if not clima:
        raise HTTPException(status_code=404, detail="Registro de clima não encontrado")
    ensure_obra_access(current_user, clima.obra_id, required_level=3)
    return clima


@router.put("/{clima_id}", response_model=ClimaResponse)
def atualizar_clima(clima_id: int, dados: ClimaUpdate, db: Session = Depends(get_db),
                    current_user=Depends(get_current_user)):
    clima = db.query(Clima).filter(Clima.id == clima_id).first()
    if not clima:
        raise HTTPException(status_code=404, detail="Registro de clima não encontrado")
    ensure_obra_access(current_user, clima.obra_id, required_level=2)
    check_diary_editable(db, clima.obra_id, clima.data)
    updates = dados.model_dump(exclude_unset=True)
    old = {k: getattr(clima, k) for k in updates}
    # Converter status_pluviometrico string para enum se fornecido
    if "status_pluviometrico" in updates and isinstance(updates["status_pluviometrico"], str):
        updates["status_pluviometrico"] = StatusPluviometrico(updates["status_pluviometrico"])
    log_changes(db, clima.obra_id, clima.data, "clima", clima.id, old, updates, current_user.id)
    for key, value in updates.items():
        setattr(clima, key, value)
    db.commit()
    db.refresh(clima)
    return clima


@router.delete("/{clima_id}")
def deletar_clima(clima_id: int, db: Session = Depends(get_db),
                  current_user=Depends(get_current_user)):
    clima = db.query(Clima).filter(Clima.id == clima_id).first()
    if not clima:
        raise HTTPException(status_code=404, detail="Registro de clima não encontrado")
    ensure_obra_access(current_user, clima.obra_id, required_level=2)
    check_diary_editable(db, clima.obra_id, clima.data)
    db.delete(clima)
    db.commit()
    return {"detail": "Registro removido"}
