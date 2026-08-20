"""Auth router: registration + OAuth2 password → JWT token.

Kept minimal — out of the §5 surface area but required to make the JWT auth
flow end-to-end exercisable (design §8).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from app.db.base import get_db
from app.repositories import user_repo
from app.schemas.user import UserCreate, UserRead

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(payload: UserCreate, db: AsyncSession = Depends(get_db)) -> UserRead:
    existing = await user_repo.get_by_email(db, payload.email)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )
    user = await user_repo.create(
        db,
        name=payload.name,
        email=payload.email,
        password_hash=hash_password(payload.password),
    )
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )
    await db.refresh(user)
    return UserRead.model_validate(user)


@router.post("/token")
async def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    # OAuth2PasswordRequestForm uses `username` as the identifier; we treat it
    # as the email address to match the user record.
    user = await user_repo.get_by_email(db, form.username)
    if user is None or not verify_password(form.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token(user.id)
    return {"access_token": token, "token_type": "bearer"}
