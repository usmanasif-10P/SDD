"""Password hashing, JWT encode/decode, and the `get_current_user` dependency.

Tokens carry the user UUID in `sub` (design §8). `get_current_user` decodes the
bearer token and resolves the user record, returning the ORM instance to the
router.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.base import get_db
from app.db.models import User
from app.repositories import user_repo

_settings = get_settings()
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# tokenUrl matches the login endpoint; FastAPI uses it for Swagger UI auth.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token", auto_error=False)


def hash_password(plain: str) -> str:
    return _pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd_context.verify(plain, hashed)


def create_access_token(subject: str | uuid.UUID, expires_delta: timedelta | None = None) -> str:
    if not _settings.jwt_secret:
        raise RuntimeError("JWT_SECRET not configured")
    expire = datetime.now(timezone.utc) + (
        expires_delta
        or timedelta(minutes=_settings.jwt_expiry_minutes)
    )
    payload = {"sub": str(subject), "exp": expire}
    return jwt.encode(payload, _settings.jwt_secret, algorithm=_settings.jwt_algorithm)


async def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Decode the bearer JWT and return the corresponding `User` row.

    Raises 401 when the token is missing, malformed, expired, signature-invalid,
    or refers to a user that no longer exists.
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = jwt.decode(
            token,
            _settings.jwt_secret,
            algorithms=[_settings.jwt_algorithm],
        )
        sub = payload.get("sub")
        if not sub:
            raise JWTError("missing sub")
        user_id = uuid.UUID(sub)
    except (JWTError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = await user_repo.get_by_id(db, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user
