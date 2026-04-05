"""Rotas de autenticação — login e perfil do usuário."""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.auth import (
    verify_password, create_access_token, hash_password, get_current_user
)
from app.models import Usuario

router = APIRouter(prefix="/auth", tags=["Autenticação"])


@router.post("/login")
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Login via email + senha. Retorna JWT."""
    user = db.query(Usuario).filter(Usuario.email == form.username).first()
    if not user or not user.senha_hash:
        raise HTTPException(status_code=401, detail="Credenciais inválidas")
    if not verify_password(form.password, user.senha_hash):
        raise HTTPException(status_code=401, detail="Credenciais inválidas")
    if not user.ativo:
        raise HTTPException(status_code=401, detail="Usuário inativo")

    token = create_access_token({"sub": str(user.id)})
    return {
        "access_token": token,
        "token_type": "bearer",
        "usuario": {
            "id": user.id,
            "nome": user.nome,
            "email": user.email,
            "role": user.role,
            "obra_id": user.obra_id,
        }
    }


@router.get("/me")
def me(current_user: Usuario = Depends(get_current_user)):
    """Retorna dados do usuário autenticado."""
    return {
        "id": current_user.id,
        "nome": current_user.nome,
        "email": current_user.email,
        "telefone": current_user.telefone,
        "role": current_user.role,
        "obra_id": current_user.obra_id,
        "ativo": current_user.ativo,
    }


@router.post("/setup-password")
def setup_password(
    email: str,
    senha: str,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Admin configura senha para um usuário existente (já cadastrado via bot)."""
    if current_user.role not in ("admin", "responsavel"):
        raise HTTPException(status_code=403, detail="Apenas admin pode configurar senhas")

    user = db.query(Usuario).filter(Usuario.email == email).first()
    if not user:
        # Se não tem email, busca por telefone e seta o email
        raise HTTPException(status_code=404, detail="Usuário com esse email não encontrado")

    user.senha_hash = hash_password(senha)
    db.commit()
    return {"ok": True, "message": f"Senha configurada para {user.nome}"}


@router.post("/bootstrap")
def bootstrap(email: str, senha: str, db: Session = Depends(get_db)):
    """
    Cria credenciais para o primeiro admin.
    Só funciona se NENHUM usuário tiver senha configurada.
    """
    has_any_password = db.query(Usuario).filter(Usuario.senha_hash.isnot(None)).first()
    if has_any_password:
        raise HTTPException(status_code=403, detail="Bootstrap já foi executado")

    # Pega o primeiro usuário com role admin/responsavel
    admin = db.query(Usuario).filter(
        Usuario.role.in_(["admin", "responsavel"])
    ).first()
    if not admin:
        # Pega qualquer usuário
        admin = db.query(Usuario).first()
    if not admin:
        raise HTTPException(status_code=404, detail="Nenhum usuário cadastrado")

    admin.email = email
    admin.senha_hash = hash_password(senha)
    db.commit()

    token = create_access_token({"sub": str(admin.id)})
    return {
        "access_token": token,
        "token_type": "bearer",
        "usuario": {
            "id": admin.id,
            "nome": admin.nome,
            "email": admin.email,
            "role": admin.role,
        },
        "message": f"Bootstrap completo. {admin.nome} agora pode acessar o painel."
    }
