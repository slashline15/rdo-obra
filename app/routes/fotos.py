import os
from datetime import date
from typing import List
from urllib.parse import unquote

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database import get_db
from app.models import Foto
from app.schemas import FotoCreate, FotoResponse

router = APIRouter(prefix="/fotos", tags=["Fotos"])


@router.post("/", response_model=FotoResponse)
def criar_foto(foto: FotoCreate, db: Session = Depends(get_db)):
    data = foto.model_dump()
    if not data.get("data"):
        data["data"] = date.today()
    db_foto = Foto(**data)
    db.add(db_foto)
    db.commit()
    db.refresh(db_foto)
    return db_foto


@router.get("/", response_model=List[FotoResponse])
def listar_fotos(obra_id: int = None, data_ref: date = None, categoria: str = None, db: Session = Depends(get_db)):
    query = db.query(Foto)
    if obra_id:
        query = query.filter(Foto.obra_id == obra_id)
    if data_ref:
        query = query.filter(Foto.data == data_ref)
    if categoria:
        query = query.filter(Foto.categoria == categoria)
    return query.order_by(Foto.created_at.desc()).all()


@router.get("/arquivo/{file_path:path}")
def servir_arquivo_foto(file_path: str):
    upload_dir = os.path.abspath(settings.upload_dir)
    resolved_path = os.path.abspath(os.path.join(upload_dir, unquote(file_path)))

    if resolved_path != upload_dir and not resolved_path.startswith(upload_dir + os.sep):
        raise HTTPException(status_code=403, detail="Caminho de arquivo inválido")
    if not os.path.isfile(resolved_path):
        raise HTTPException(status_code=404, detail="Arquivo de foto não encontrado")

    return FileResponse(resolved_path)


@router.get("/{foto_id}", response_model=FotoResponse)
def buscar_foto(foto_id: int, db: Session = Depends(get_db)):
    foto = db.query(Foto).filter(Foto.id == foto_id).first()
    if not foto:
        raise HTTPException(status_code=404, detail="Foto não encontrada")
    return foto


@router.delete("/{foto_id}")
def deletar_foto(foto_id: int, db: Session = Depends(get_db)):
    foto = db.query(Foto).filter(Foto.id == foto_id).first()
    if not foto:
        raise HTTPException(status_code=404, detail="Foto não encontrada")
    db.delete(foto)
    db.commit()
    return {"detail": "Foto removida"}
