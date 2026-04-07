from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models import Usuario
from app.schemas import UsuarioCreate, UsuarioResponse
from app.core.auth import get_current_user
from app.core.permissions import get_access_level, require_level, resolve_obra_scope

router = APIRouter(prefix="/usuarios", tags=["Usuários"])


@router.post("/", response_model=UsuarioResponse)
def criar_usuario(
    usuario: UsuarioCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_level(2)),
):
    obra_id = resolve_obra_scope(current_user, usuario.obra_id, require_explicit=False)
    if get_access_level(current_user) > 1 and (usuario.nivel_acesso or 3) < 3:
        raise HTTPException(status_code=403, detail="Co-responsável só pode criar usuários operacionais")
    db_usuario = Usuario(**usuario.model_dump())
    db_usuario.obra_id = obra_id
    db.add(db_usuario)
    db.commit()
    db.refresh(db_usuario)
    return db_usuario


@router.get("/", response_model=List[UsuarioResponse])
def listar_usuarios(
    obra_id: int = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_level(2)),
):
    query = db.query(Usuario)
    scoped_obra_id = resolve_obra_scope(current_user, obra_id, require_explicit=False)
    if scoped_obra_id:
        query = query.filter(Usuario.obra_id == scoped_obra_id)
    return query.all()


@router.get("/telefone/{telefone}", response_model=UsuarioResponse)
def buscar_por_telefone(
    telefone: str,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_level(2)),
):
    usuario = db.query(Usuario).filter(Usuario.telefone == telefone).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    resolve_obra_scope(current_user, usuario.obra_id, require_explicit=False)
    return usuario


@router.get("/{usuario_id}", response_model=UsuarioResponse)
def buscar_usuario(
    usuario_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    if usuario.id != current_user.id:
        resolve_obra_scope(current_user, usuario.obra_id, require_explicit=False)
    return usuario


@router.put("/{usuario_id}", response_model=UsuarioResponse)
def atualizar_usuario(
    usuario_id: int,
    dados: UsuarioCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_level(2)),
):
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    resolve_obra_scope(current_user, usuario.obra_id, require_explicit=False)
    if get_access_level(current_user) > 1 and (dados.nivel_acesso or usuario.nivel_acesso or 3) < 3:
        raise HTTPException(status_code=403, detail="Co-responsável não pode promover usuários")
    for key, value in dados.model_dump().items():
        setattr(usuario, key, value)
    db.commit()
    db.refresh(usuario)
    return usuario


@router.delete("/{usuario_id}")
def deletar_usuario(
    usuario_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_level(2)),
):
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    resolve_obra_scope(current_user, usuario.obra_id, require_explicit=False)
    if get_access_level(current_user) > 1 and (usuario.nivel_acesso or 3) < 3:
        raise HTTPException(status_code=403, detail="Co-responsável não pode apagar usuários de nível superior")
    db.delete(usuario)
    db.commit()
    return {"detail": "Usuário removido"}
