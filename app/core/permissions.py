"""
Controle de acesso por role.
admin      → aprova diários, gerencia usuários
engenheiro → edita, submete para revisão
estagiario → visualiza apenas
"""
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Query
from app.core.auth import get_current_user
from app.models import Usuario


ROLE_LEVEL_FALLBACK = {
    "admin": 1,
    "responsavel": 2,
    "engenheiro": 2,
    "fiscal": 2,
    "encarregado": 3,
    "mestre": 3,
    "estagiario": 3,
}


def get_access_level(current_user: Usuario) -> int:
    if getattr(current_user, "nivel_acesso", None):
        return int(current_user.nivel_acesso)
    return ROLE_LEVEL_FALLBACK.get(current_user.role or "", 3)


def can_approve_diario(current_user: Usuario) -> bool:
    level = get_access_level(current_user)
    if level == 1:
        return True
    return level == 2 and bool(getattr(current_user, "pode_aprovar_diario", False))


def require_level(required_level: int):
    """Permite o acesso a usuários com nível igual ou superior em privilégio."""
    def _check(current_user: Usuario = Depends(get_current_user)) -> Usuario:
        level = get_access_level(current_user)
        if level > required_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Acesso negado. Necessário nível {required_level} ou superior."
            )
        return current_user
    return _check


def resolve_obra_scope(current_user: Usuario, obra_id: int | None, require_explicit: bool = False) -> int | None:
    level = get_access_level(current_user)
    if level == 1:
        if require_explicit and obra_id is None:
            raise HTTPException(status_code=400, detail="obra_id é obrigatório para esta operação")
        return obra_id

    if current_user.obra_id is None:
        raise HTTPException(status_code=403, detail="Usuário sem obra vinculada")
    if obra_id is not None and obra_id != current_user.obra_id:
        raise HTTPException(status_code=403, detail="Acesso negado a outra obra")
    return current_user.obra_id


def ensure_obra_access(current_user: Usuario, obra_id: int, required_level: int = 3) -> None:
    level = get_access_level(current_user)
    if level > required_level:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Acesso negado. Necessário nível {required_level} ou superior."
        )
    resolve_obra_scope(current_user, obra_id, require_explicit=True)


def scope_query_to_user(query: Query, model, current_user: Usuario):
    level = get_access_level(current_user)
    if level == 1:
        return query
    return query.filter(getattr(model, "obra_id") == current_user.obra_id)


def require_role(*allowed_roles: str):
    """Dependency factory: restringe acesso a roles específicos."""
    def _check(current_user: Usuario = Depends(get_current_user)) -> Usuario:
        # "responsavel" é tratado como admin (compatibilidade com o bot)
        role = current_user.role
        if role == "responsavel":
            role = "admin"
        if role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Acesso negado. Necessário: {', '.join(allowed_roles)}"
            )
        return current_user
    return _check
