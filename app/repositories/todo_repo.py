"""Data access for `todos`. Always parameterized via SQLAlchemy 2.x `select()` / `delete()`."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Todo


async def create(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    title: str,
    description: str | None,
    status: str,
    priority: int,
    due_date: Any | None,
) -> Todo:
    todo = Todo(
        user_id=user_id,
        title=title,
        description=description,
        status=status,
        priority=priority,
        due_date=due_date,
    )
    db.add(todo)
    await db.flush()
    await db.refresh(todo)
    return todo


async def list_for_user(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    status: str | None = None,
    priority: int | None = None,
) -> list[Todo]:
    stmt = select(Todo).where(Todo.user_id == user_id)
    if status is not None:
        stmt = stmt.where(Todo.status == status)
    if priority is not None:
        stmt = stmt.where(Todo.priority == priority)
    stmt = stmt.order_by(Todo.created_at.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_for_user(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    todo_id: uuid.UUID,
) -> Todo | None:
    """Ownership-scoped lookup — returns None for non-owned and unknown ids
    so the API layer can map both to 404 (design §4)."""
    stmt = select(Todo).where(Todo.id == todo_id, Todo.user_id == user_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def update_for_user(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    todo_id: uuid.UUID,
    fields: dict[str, Any],
) -> Todo | None:
    """Apply `fields` to the row and return the updated instance, or None if
    the row is not owned by the user / does not exist."""
    todo = await get_for_user(db, user_id=user_id, todo_id=todo_id)
    if todo is None:
        return None
    for key, value in fields.items():
        if value is None and key not in {"description", "due_date"}:
            continue
        setattr(todo, key, value)
    await db.flush()
    await db.refresh(todo)
    return todo


async def delete_for_user(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    todo_id: uuid.UUID,
) -> bool:
    """Returns True iff a row was deleted."""
    stmt = (
        delete(Todo)
        .where(Todo.id == todo_id, Todo.user_id == user_id)
        .returning(Todo.id)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none() is not None
