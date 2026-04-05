"""
Controle de acesso por role.
admin      → aprova diários, gerencia usuários
engenheiro → edita, submete para revisão
estagiario → visualiza apenas
"""
from fastapi import Depends, HTTPException, status
from app.core.auth import get_current_user
from app.models import Usuario


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
