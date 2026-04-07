import os
from datetime import date
from typing import List
from urllib.parse import unquote

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.auth import get_current_user
from app.core.permissions import ensure_obra_access, resolve_obra_scope, scope_query_to_user
from app.database import get_db
from app.models import Foto
from app.schemas import FotoCreate, FotoResponse

router = APIRouter(prefix="/fotos", tags=["Fotos"])


@router.post("/", response_model=FotoResponse)
def criar_foto(foto: FotoCreate, db: Session = Depends(get_db),
               current_user=Depends(get_current_user)):
    data = foto.model_dump()
    if not data.get("data"):
        data["data"] = date.today()
    data["obra_id"] = resolve_obra_scope(current_user, data.get("obra_id"), require_explicit=True)
    db_foto = Foto(**data)
    db.add(db_foto)
    db.commit()
    db.refresh(db_foto)
    return db_foto


@router.get("/", response_model=List[FotoResponse])
def listar_fotos(obra_id: int = None, data_ref: date = None, categoria: str = None, db: Session = Depends(get_db),
                 current_user=Depends(get_current_user)):
    query = scope_query_to_user(db.query(Foto), Foto, current_user)
    scoped_obra_id = resolve_obra_scope(current_user, obra_id, require_explicit=False)
    if scoped_obra_id:
        query = query.filter(Foto.obra_id == scoped_obra_id)
    if data_ref:
        query = query.filter(Foto.data == data_ref)
    if categoria:
        query = query.filter(Foto.categoria == categoria)
    return query.order_by(Foto.created_at.desc()).all()


@router.get("/arquivo/{file_path:path}")
def servir_arquivo_foto(file_path: str, db: Session = Depends(get_db),
                        current_user=Depends(get_current_user)):
    upload_dir = os.path.abspath(settings.upload_dir)
    resolved_path = os.path.abspath(os.path.join(upload_dir, unquote(file_path)))

    if resolved_path != upload_dir and not resolved_path.startswith(upload_dir + os.sep):
        raise HTTPException(status_code=403, detail="Caminho de arquivo inválido")
    if not os.path.isfile(resolved_path):
        raise HTTPException(status_code=404, detail="Arquivo de foto não encontrado")
    foto = db.query(Foto).filter(Foto.arquivo == file_path).first()
    if not foto:
        foto = db.query(Foto).filter(Foto.arquivo == resolved_path).first()
    if not foto:
        raise HTTPException(status_code=404, detail="Arquivo não vinculado a foto cadastrada")
    ensure_obra_access(current_user, foto.obra_id, required_level=3)

    return FileResponse(resolved_path)


@router.get("/{foto_id}", response_model=FotoResponse)
def buscar_foto(foto_id: int, db: Session = Depends(get_db),
                current_user=Depends(get_current_user)):
    foto = db.query(Foto).filter(Foto.id == foto_id).first()
    if not foto:
        raise HTTPException(status_code=404, detail="Foto não encontrada")
    ensure_obra_access(current_user, foto.obra_id, required_level=3)
    return foto


@router.delete("/{foto_id}")
def deletar_foto(foto_id: int, db: Session = Depends(get_db),
                 current_user=Depends(get_current_user)):
    foto = db.query(Foto).filter(Foto.id == foto_id).first()
    if not foto:
        raise HTTPException(status_code=404, detail="Foto não encontrada")
    ensure_obra_access(current_user, foto.obra_id, required_level=2)
    db.delete(foto)
    db.commit()
    return {"detail": "Foto removida"}
