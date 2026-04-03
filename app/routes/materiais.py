from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import date
from sqlalchemy import func

from app.database import get_db
from app.models import Material
from app.schemas import MaterialCreate, MaterialResponse

router = APIRouter(prefix="/materiais", tags=["Materiais"])


@router.post("/", response_model=MaterialResponse)
def criar_material(material: MaterialCreate, db: Session = Depends(get_db)):
    data = material.model_dump()
    if not data.get("data"):
        data["data"] = date.today()
    db_material = Material(**data)
    db.add(db_material)
    db.commit()
    db.refresh(db_material)
    return db_material


@router.get("/", response_model=List[MaterialResponse])
def listar_materiais(obra_id: int = None, data_ref: date = None, tipo: str = None, db: Session = Depends(get_db)):
    query = db.query(Material)
    if obra_id:
        query = query.filter(Material.obra_id == obra_id)
    if data_ref:
        query = query.filter(Material.data == data_ref)
    if tipo:
        query = query.filter(Material.tipo == tipo)
    return query.order_by(Material.created_at.desc()).all()


@router.get("/resumo/{obra_id}")
def resumo_materiais(obra_id: int, material_nome: str = None, db: Session = Depends(get_db)):
    """Resumo de entradas/saídas de material (ex: 'quanto cimento chegou essa semana?')"""
    query = db.query(
        Material.material,
        Material.tipo,
        func.sum(Material.quantidade).label("total"),
        Material.unidade
    ).filter(Material.obra_id == obra_id)

    if material_nome:
        query = query.filter(Material.material.ilike(f"%{material_nome}%"))

    registros = query.group_by(Material.material, Material.tipo, Material.unidade).all()

    return {
        "obra_id": obra_id,
        "materiais": [
            {
                "material": r.material,
                "tipo": r.tipo,
                "total": r.total,
                "unidade": r.unidade
            } for r in registros
        ]
    }


@router.get("/{material_id}", response_model=MaterialResponse)
def buscar_material(material_id: int, db: Session = Depends(get_db)):
    material = db.query(Material).filter(Material.id == material_id).first()
    if not material:
        raise HTTPException(status_code=404, detail="Material não encontrado")
    return material


@router.delete("/{material_id}")
def deletar_material(material_id: int, db: Session = Depends(get_db)):
    material = db.query(Material).filter(Material.id == material_id).first()
    if not material:
        raise HTTPException(status_code=404, detail="Material não encontrado")
    db.delete(material)
    db.commit()
    return {"detail": "Material removido"}
