"""Data access for `users`. All queries are parameterized via SQLAlchemy 2.x `select()`."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User


async def get_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_by_id(db: AsyncSession, user_id: uuid.UUID) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def create(
    db: AsyncSession,
    *,
    name: str,
    email: str,
    password_hash: str,
) -> User:
    user = User(name=name, email=email, password_hash=password_hash)
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user
