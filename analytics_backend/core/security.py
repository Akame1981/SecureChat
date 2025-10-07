from datetime import datetime, timedelta
from typing import Optional
import jwt
from passlib.context import CryptContext
from .config import get_settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, stored_password: str, stored_hash: str | None = None) -> bool:
    if stored_hash:
        return pwd_context.verify(plain_password, stored_hash)
    # fallback to plain compare or bcrypt hash in stored_password
    try:
        if stored_password.startswith('$2b$') or stored_password.startswith('$2a$'):
            return pwd_context.verify(plain_password, stored_password)
    except Exception:
        pass
    return plain_password == stored_password


def create_access_token(subject: str, expires_minutes: Optional[int] = None) -> str:
    settings = get_settings()
    if expires_minutes is None:
        expires_minutes = settings.access_token_expire_minutes
    expire = datetime.utcnow() + timedelta(minutes=expires_minutes)
    payload = {"sub": subject, "exp": expire}
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return token


def decode_token(token: str) -> Optional[str]:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        return payload.get("sub")
    except Exception:
        return None
