"""Rotas de autenticação — login, perfil e convites."""
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.config import settings
from app.core.auth import (
    verify_password, create_access_token, generate_invite_token, get_current_user,
    hash_invite_token, hash_password
)
from app.core.permissions import (
    can_approve_diario,
    ensure_obra_access,
    get_access_level,
    require_level,
)
from app.core.time import utc_now, utc_now_iso
from app.models import ConviteAcesso, Usuario
from app.schemas import InviteAcceptRequest, InviteCreateRequest

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
            "nivel_acesso": get_access_level(user),
            "pode_aprovar_diario": can_approve_diario(user),
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
        "nivel_acesso": get_access_level(current_user),
        "pode_aprovar_diario": can_approve_diario(current_user),
        "registro_profissional": current_user.registro_profissional,
        "empresa_vinculada": current_user.empresa_vinculada,
        "ativo": current_user.ativo,
    }


@router.post("/setup-password")
def setup_password(
    email: str,
    senha: str,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_level(2)),
):
    """Admin configura senha para um usuário existente (já cadastrado via bot)."""
    user = db.query(Usuario).filter(Usuario.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário com esse email não encontrado")
    if get_access_level(current_user) > 1:
        ensure_obra_access(current_user, user.obra_id, required_level=2)

    user.senha_hash = hash_password(senha)
    db.commit()
    return {"ok": True, "message": f"Senha configurada para {user.nome}"}


@router.post("/bootstrap")
def bootstrap(email: str, senha: str, bootstrap_token: str, db: Session = Depends(get_db)):
    """
    Bootstrap legado: agora requer token explícito de instalação.
    """
    if not settings.legacy_bootstrap_token:
        raise HTTPException(
            status_code=403,
            detail="Bootstrap legado desativado. Use o fluxo de convites."
        )
    if bootstrap_token != settings.legacy_bootstrap_token:
        raise HTTPException(status_code=403, detail="Token de bootstrap inválido")

    has_any_password = db.query(Usuario).filter(Usuario.senha_hash.isnot(None)).first()
    if has_any_password:
        raise HTTPException(status_code=403, detail="Bootstrap já foi executado")

    admin = db.query(Usuario).filter(
        Usuario.nivel_acesso == 1
    ).first()
    if not admin:
        admin = db.query(Usuario).first()
    if not admin:
        raise HTTPException(status_code=404, detail="Nenhum usuário cadastrado")

    admin.email = email
    admin.senha_hash = hash_password(senha)
    admin.nivel_acesso = 1
    admin.pode_aprovar_diario = True
    admin.role = "admin"
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
            "nivel_acesso": admin.nivel_acesso,
            "pode_aprovar_diario": admin.pode_aprovar_diario,
        },
        "message": f"Bootstrap completo. {admin.nome} agora pode acessar o painel."
    }


@router.post("/invites")
def create_invite(
    body: InviteCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_level(2)),
):
    creator_level = get_access_level(current_user)
    if body.nivel_acesso not in (1, 2, 3):
        raise HTTPException(status_code=400, detail="nivel_acesso inválido")
    if body.pode_aprovar_diario and body.nivel_acesso != 2:
        raise HTTPException(status_code=400, detail="Aprovação de diário só pode ser delegada ao nível 2")

    obra_id = body.obra_id
    if creator_level == 1:
        if body.nivel_acesso > 1 and obra_id is None:
            raise HTTPException(status_code=400, detail="obra_id é obrigatório para convites de nível 2 e 3")
        if body.nivel_acesso == 1:
            obra_id = None
    else:
        obra_id = current_user.obra_id
        if obra_id is None:
            raise HTTPException(status_code=403, detail="Usuário sem obra vinculada")
        if body.obra_id is not None and body.obra_id != obra_id:
            raise HTTPException(status_code=403, detail="Co-responsável só pode convidar para a própria obra")
        if body.nivel_acesso != 3:
            raise HTTPException(status_code=403, detail="Co-responsável só pode convidar usuários operacionais")

    token = generate_invite_token()
    invite = ConviteAcesso(
        obra_id=obra_id,
        email=body.email.lower(),
        telefone=body.telefone,
        role=body.role,
        nivel_acesso=body.nivel_acesso,
        pode_aprovar_diario=body.pode_aprovar_diario,
        cargo=body.cargo,
        token_hash=hash_invite_token(token),
        criado_por_id=current_user.id,
        expira_em=utc_now() + timedelta(hours=settings.invite_token_ttl_hours),
        request_metadata={
            "creator_ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
        },
    )
    db.add(invite)
    db.commit()
    db.refresh(invite)

    return {
        "invite": _serialize_invite(invite),
        "token": token,
    }


@router.get("/invites")
def list_invites(
    obra_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_level(2)),
):
    query = db.query(ConviteAcesso)
    creator_level = get_access_level(current_user)

    if creator_level == 1:
        if obra_id is not None:
            query = query.filter(ConviteAcesso.obra_id == obra_id)
    else:
        if current_user.obra_id is None:
            raise HTTPException(status_code=403, detail="Usuário sem obra vinculada")
        scoped_obra_id = current_user.obra_id
        if obra_id is not None and obra_id != scoped_obra_id:
            raise HTTPException(status_code=403, detail="Co-responsável só pode visualizar convites da própria obra")
        query = query.filter(ConviteAcesso.obra_id == scoped_obra_id)

    invites = query.order_by(ConviteAcesso.created_at.desc()).all()
    return [_serialize_invite(invite) for invite in invites]


@router.post("/invites/{invite_id}/reissue")
def reissue_invite(
    invite_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_level(2)),
):
    invite = _get_scoped_invite(db, invite_id, current_user)
    if invite.status == "aceito":
        raise HTTPException(status_code=400, detail="Convites aceitos não podem ser reenviados")
    if invite.status == "revogado":
        raise HTTPException(status_code=400, detail="Convite revogado não pode ser reenviado")

    token = generate_invite_token()
    invite.token_hash = hash_invite_token(token)
    invite.status = "pendente"
    invite.usado_em = None
    invite.usado_por_id = None
    invite.expira_em = utc_now() + timedelta(hours=settings.invite_token_ttl_hours)
    metadata = dict(invite.request_metadata or {})
    history = list(metadata.get("reissues", []))
    history.append({
        "at": utc_now_iso(),
        "by_user_id": current_user.id,
        "ip": request.client.host if request.client else None,
    })
    metadata["reissues"] = history
    invite.request_metadata = metadata
    db.commit()
    db.refresh(invite)
    return {"invite": _serialize_invite(invite), "token": token}


@router.post("/invites/{invite_id}/revoke")
def revoke_invite(
    invite_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_level(2)),
):
    invite = _get_scoped_invite(db, invite_id, current_user)
    if invite.status == "aceito":
        raise HTTPException(status_code=400, detail="Convite aceito não pode ser revogado")
    if invite.status == "revogado":
        return _serialize_invite(invite)
    invite.status = "revogado"
    db.commit()
    db.refresh(invite)
    return _serialize_invite(invite)


@router.get("/invites/{token}")
def inspect_invite(token: str, db: Session = Depends(get_db)):
    invite = _get_valid_invite(db, token)
    return _serialize_invite(invite)


@router.post("/invites/accept")
def accept_invite(body: InviteAcceptRequest, db: Session = Depends(get_db)):
    invite = _get_valid_invite(db, body.token)

    existing = None
    normalized_email = (body.email or invite.email).lower()
    if normalized_email:
        existing = db.query(Usuario).filter(Usuario.email == normalized_email).first()
    if existing is None and body.telefone:
        existing = db.query(Usuario).filter(Usuario.telefone == body.telefone).first()

    if existing and existing.senha_hash:
        raise HTTPException(status_code=409, detail="Usuário já possui acesso ativo")

    if existing is None:
        user = Usuario(
            nome=body.nome,
            telefone=body.telefone,
            email=normalized_email,
            obra_id=invite.obra_id,
            role=invite.role,
            nivel_acesso=invite.nivel_acesso,
            pode_aprovar_diario=invite.pode_aprovar_diario,
            registro_profissional=body.registro_profissional,
            empresa_vinculada=body.empresa_vinculada,
            senha_hash=hash_password(body.senha),
            ativo=True,
        )
        db.add(user)
        db.flush()
    else:
        user = existing
        user.nome = body.nome
        user.telefone = body.telefone
        user.email = normalized_email
        user.obra_id = invite.obra_id
        user.role = invite.role
        user.nivel_acesso = invite.nivel_acesso
        user.pode_aprovar_diario = invite.pode_aprovar_diario
        user.registro_profissional = body.registro_profissional
        user.empresa_vinculada = body.empresa_vinculada
        user.senha_hash = hash_password(body.senha)
        user.ativo = True

    invite.status = "aceito"
    invite.usado_em = utc_now()
    invite.usado_por_id = user.id
    db.commit()
    db.refresh(user)

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
            "nivel_acesso": get_access_level(user),
            "pode_aprovar_diario": can_approve_diario(user),
        },
    }


def _get_valid_invite(db: Session, token: str) -> ConviteAcesso:
    invite = db.query(ConviteAcesso).filter(
        ConviteAcesso.token_hash == hash_invite_token(token)
    ).first()
    if not invite:
        raise HTTPException(status_code=404, detail="Convite não encontrado")
    if invite.status != "pendente" or invite.usado_em is not None:
        raise HTTPException(status_code=410, detail="Convite já utilizado")
    if invite.expira_em < utc_now():
        invite.status = "expirado"
        db.commit()
        raise HTTPException(status_code=410, detail="Convite expirado")
    return invite


def _get_scoped_invite(db: Session, invite_id: int, current_user: Usuario) -> ConviteAcesso:
    invite = db.query(ConviteAcesso).filter(ConviteAcesso.id == invite_id).first()
    if not invite:
        raise HTTPException(status_code=404, detail="Convite não encontrado")
    if get_access_level(current_user) > 1:
        if current_user.obra_id is None or invite.obra_id != current_user.obra_id:
            raise HTTPException(status_code=403, detail="Convite fora do escopo da sua obra")
    return invite


def _serialize_invite(invite: ConviteAcesso) -> dict:
    return {
        "id": invite.id,
        "email": invite.email,
        "obra_id": invite.obra_id,
        "role": invite.role,
        "nivel_acesso": invite.nivel_acesso,
        "pode_aprovar_diario": invite.pode_aprovar_diario,
        "cargo": invite.cargo,
        "status": invite.status,
        "expira_em": invite.expira_em.isoformat(),
        "created_at": invite.created_at.isoformat() if invite.created_at else None,
    }
