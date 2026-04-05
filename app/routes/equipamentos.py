from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import date

from app.database import get_db
from app.models import Equipamento
from app.schemas import EquipamentoCreate, EquipamentoResponse, EquipamentoUpdate
from app.core.auth import get_current_user
from app.core.diary_lock import check_diary_editable
from app.services.audit import log_changes

router = APIRouter(prefix="/equipamentos", tags=["Equipamentos"])


@router.post("/", response_model=EquipamentoResponse)
def criar_equipamento(equipamento: EquipamentoCreate, db: Session = Depends(get_db)):
    data = equipamento.model_dump()
    if not data.get("data"):
        data["data"] = date.today()
    db_equip = Equipamento(**data)
    db.add(db_equip)
    db.commit()
    db.refresh(db_equip)
    return db_equip


@router.get("/", response_model=List[EquipamentoResponse])
def listar_equipamentos(obra_id: int = None, data_ref: date = None, db: Session = Depends(get_db)):
    query = db.query(Equipamento)
    if obra_id:
        query = query.filter(Equipamento.obra_id == obra_id)
    if data_ref:
        query = query.filter(Equipamento.data == data_ref)
    return query.order_by(Equipamento.created_at.desc()).all()


@router.get("/{equipamento_id}", response_model=EquipamentoResponse)
def buscar_equipamento(equipamento_id: int, db: Session = Depends(get_db)):
    equip = db.query(Equipamento).filter(Equipamento.id == equipamento_id).first()
    if not equip:
        raise HTTPException(status_code=404, detail="Equipamento não encontrado")
    return equip


@router.put("/{equipamento_id}", response_model=EquipamentoResponse)
def atualizar_equipamento(equipamento_id: int, dados: EquipamentoUpdate, db: Session = Depends(get_db),
                          current_user=Depends(get_current_user)):
    equip = db.query(Equipamento).filter(Equipamento.id == equipamento_id).first()
    if not equip:
        raise HTTPException(status_code=404, detail="Equipamento não encontrado")
    check_diary_editable(db, equip.obra_id, equip.data)
    updates = dados.model_dump(exclude_unset=True)
    old = {k: getattr(equip, k) for k in updates}
    log_changes(db, equip.obra_id, equip.data, "equipamentos", equip.id, old, updates, current_user.id)
    for key, value in updates.items():
        setattr(equip, key, value)
    db.commit()
    db.refresh(equip)
    return equip


@router.delete("/{equipamento_id}")
def deletar_equipamento(equipamento_id: int, db: Session = Depends(get_db)):
    equip = db.query(Equipamento).filter(Equipamento.id == equipamento_id).first()
    if not equip:
        raise HTTPException(status_code=404, detail="Equipamento não encontrado")
    db.delete(equip)
    db.commit()
    return {"detail": "Equipamento removido"}
