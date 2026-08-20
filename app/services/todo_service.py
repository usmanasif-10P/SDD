"""Business rules for todos (TDD §6).

- Default `status = Pending` on create.
- Due date must be in the future.
- A `Completed` todo cannot revert to `Pending`.
- The service raises domain exceptions; the API layer maps them to 400/404.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Todo, TodoStatus
from app.repositories import todo_repo
from app.schemas.todo import TodoCreate, TodoUpdate


def _to_naive_utc(value: datetime) -> datetime:
    """Coerce an aware datetime to naive UTC.

    The `todos.due_date` column is `TIMESTAMP WITHOUT TIME ZONE` (TDD §3), so we
    must strip the tzinfo before asyncpg tries to bind the value. Naive values
    are assumed to already be UTC (FastAPI's default parser produces aware
    values, so this branch is rare — but harmless if it does happen).
    """
    if value.tzinfo is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)


class DomainError(Exception):
    """Base for service-layer domain errors."""


class ValidationError(DomainError):
    """Maps to HTTP 400."""


class NotFoundError(DomainError):
    """Maps to HTTP 404."""


class TransitionError(DomainError):
    """Maps to HTTP 400 (e.g. Completed → Pending forbidden)."""


async def create_todo(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    payload: TodoCreate,
) -> Todo:
    status_value = payload.status or TodoStatus.PENDING.value
    due_date = _to_naive_utc(payload.due_date) if payload.due_date is not None else None
    todo = await todo_repo.create(
        db,
        user_id=user_id,
        title=payload.title,
        description=payload.description,
        status=status_value,
        priority=payload.priority,
        due_date=due_date,
    )
    await db.commit()
    await db.refresh(todo)
    return todo


async def list_todos(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    status: str | None = None,
    priority: int | None = None,
) -> list[Todo]:
    if status is not None and status not in {
        TodoStatus.PENDING.value,
        TodoStatus.IN_PROGRESS.value,
        TodoStatus.COMPLETED.value,
    }:
        raise ValidationError(f"Invalid status filter: {status}")
    if priority is not None and not 1 <= priority <= 3:
        raise ValidationError(f"Invalid priority filter: {priority}")
    return await todo_repo.list_for_user(
        db, user_id=user_id, status=status, priority=priority
    )


async def get_todo(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    todo_id: uuid.UUID,
) -> Todo:
    todo = await todo_repo.get_for_user(db, user_id=user_id, todo_id=todo_id)
    if todo is None:
        raise NotFoundError("Todo not found")
    return todo


async def update_todo(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    todo_id: uuid.UUID,
    payload: TodoUpdate,
) -> Todo:
    existing = await todo_repo.get_for_user(db, user_id=user_id, todo_id=todo_id)
    if existing is None:
        raise NotFoundError("Todo not found")

    # Completed → Pending is forbidden (TDD §6).
    if (
        payload.status is not None
        and existing.status == TodoStatus.COMPLETED.value
        and payload.status == TodoStatus.PENDING.value
    ):
        raise TransitionError("Cannot revert a Completed todo to Pending")

    # Due date past-check (service layer mirrors the schema validator for
    # the update case to keep the rule consistent if the schema is bypassed).
    if payload.due_date is not None:
        v = payload.due_date
        v_aware = v if v.tzinfo else v.replace(tzinfo=timezone.utc)
        if v_aware <= datetime.now(timezone.utc):
            raise ValidationError("dueDate must be in the future")

    updates: dict[str, object] = {}
    if payload.title is not None:
        updates["title"] = payload.title
    if payload.description is not None:
        updates["description"] = payload.description
    if payload.priority is not None:
        updates["priority"] = payload.priority
    if payload.status is not None:
        updates["status"] = payload.status
    if payload.due_date is not None:
        updates["due_date"] = _to_naive_utc(payload.due_date)

    todo = await todo_repo.update_for_user(
        db, user_id=user_id, todo_id=todo_id, fields=updates
    )
    if todo is None:
        raise NotFoundError("Todo not found")
    await db.commit()
    await db.refresh(todo)
    return todo


async def delete_todo(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    todo_id: uuid.UUID,
) -> None:
    deleted = await todo_repo.delete_for_user(db, user_id=user_id, todo_id=todo_id)
    if not deleted:
        raise NotFoundError("Todo not found")
    await db.commit()
