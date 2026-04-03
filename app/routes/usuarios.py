from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models import Usuario
from app.schemas import UsuarioCreate, UsuarioResponse

router = APIRouter(prefix="/usuarios", tags=["Usuários"])


@router.post("/", response_model=UsuarioResponse)
def criar_usuario(usuario: UsuarioCreate, db: Session = Depends(get_db)):
    db_usuario = Usuario(**usuario.model_dump())
    db.add(db_usuario)
    db.commit()
    db.refresh(db_usuario)
    return db_usuario


@router.get("/", response_model=List[UsuarioResponse])
def listar_usuarios(obra_id: int = None, db: Session = Depends(get_db)):
    query = db.query(Usuario)
    if obra_id:
        query = query.filter(Usuario.obra_id == obra_id)
    return query.all()


@router.get("/telefone/{telefone}", response_model=UsuarioResponse)
def buscar_por_telefone(telefone: str, db: Session = Depends(get_db)):
    usuario = db.query(Usuario).filter(Usuario.telefone == telefone).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    return usuario


@router.get("/{usuario_id}", response_model=UsuarioResponse)
def buscar_usuario(usuario_id: int, db: Session = Depends(get_db)):
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    return usuario


@router.put("/{usuario_id}", response_model=UsuarioResponse)
def atualizar_usuario(usuario_id: int, dados: UsuarioCreate, db: Session = Depends(get_db)):
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    for key, value in dados.model_dump().items():
        setattr(usuario, key, value)
    db.commit()
    db.refresh(usuario)
    return usuario


@router.delete("/{usuario_id}")
def deletar_usuario(usuario_id: int, db: Session = Depends(get_db)):
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    db.delete(usuario)
    db.commit()
    return {"detail": "Usuário removido"}
