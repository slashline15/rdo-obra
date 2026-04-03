from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models import Empresa
from app.schemas import EmpresaCreate, EmpresaResponse

router = APIRouter(prefix="/empresas", tags=["Empresas"])


@router.post("/", response_model=EmpresaResponse)
def criar_empresa(empresa: EmpresaCreate, db: Session = Depends(get_db)):
    db_empresa = Empresa(**empresa.model_dump())
    db.add(db_empresa)
    db.commit()
    db.refresh(db_empresa)
    return db_empresa


@router.get("/", response_model=List[EmpresaResponse])
def listar_empresas(db: Session = Depends(get_db)):
    return db.query(Empresa).all()


@router.get("/{empresa_id}", response_model=EmpresaResponse)
def buscar_empresa(empresa_id: int, db: Session = Depends(get_db)):
    empresa = db.query(Empresa).filter(Empresa.id == empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
    return empresa


@router.put("/{empresa_id}", response_model=EmpresaResponse)
def atualizar_empresa(empresa_id: int, dados: EmpresaCreate, db: Session = Depends(get_db)):
    empresa = db.query(Empresa).filter(Empresa.id == empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
    for key, value in dados.model_dump().items():
        setattr(empresa, key, value)
    db.commit()
    db.refresh(empresa)
    return empresa


@router.delete("/{empresa_id}")
def deletar_empresa(empresa_id: int, db: Session = Depends(get_db)):
    empresa = db.query(Empresa).filter(Empresa.id == empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
    db.delete(empresa)
    db.commit()
    return {"detail": "Empresa removida"}
