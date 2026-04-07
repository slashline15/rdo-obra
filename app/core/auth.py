"""
Autenticação JWT para o painel web.
Bot (Telegram/WhatsApp) continua autenticando por telefone — não passa por aqui.
"""
from datetime import timedelta
import hashlib
import secrets
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
import bcrypt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.time import utc_now
from app.database import get_db
from app.models import Usuario

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24h


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = utc_now() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": int(expire.timestamp())})
    return jwt.encode(to_encode, settings.jwt_secret, algorithm=ALGORITHM)


def generate_invite_token() -> str:
    return secrets.token_urlsafe(32)


def hash_invite_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> Usuario:
    """Dependency que extrai o usuário do JWT. Retorna 401 se inválido."""
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token não fornecido",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[ALGORITHM],
            options={"verify_exp": False},
        )
        sub = payload.get("sub")
        exp = payload.get("exp")
        if sub is None:
            raise HTTPException(status_code=401, detail="Token inválido")
        if not isinstance(exp, (int, float)) or exp < utc_now().timestamp():
            raise HTTPException(status_code=401, detail="Token inválido ou expirado")
        user_id = int(sub)
        if not user_id:
            raise HTTPException(status_code=401, detail="Token inválido")
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido ou expirado")

    user = db.query(Usuario).filter(Usuario.id == user_id).first()
    if not user or not user.ativo:
        raise HTTPException(status_code=401, detail="Usuário não encontrado ou inativo")
    return user


def get_optional_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> Optional[Usuario]:
    """Dependency que retorna o usuário se autenticado, None se não."""
    if not token:
        return None
    try:
        return get_current_user(token, db)
    except HTTPException:
        return None
