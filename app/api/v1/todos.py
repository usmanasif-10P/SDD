"""The five §5 endpoints under `/api/v1/todos`."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.db.models import User
from app.schemas.todo import TodoCreate, TodoRead, TodoUpdate
from app.services import todo_service
from app.services.todo_service import (
    DomainError,
    NotFoundError,
    TransitionError,
    ValidationError,
)

router = APIRouter(prefix="/api/v1/todos", tags=["todos"])


def _serialize(todo) -> dict:
    return {
        "id": str(todo.id),
        "title": todo.title,
        "description": todo.description,
        "status": todo.status,
        "priority": todo.priority,
        "dueDate": todo.due_date,
        "createdAt": todo.created_at,
        "updatedAt": todo.updated_at,
    }


@router.post("", response_model=TodoRead, status_code=status.HTTP_201_CREATED)
async def create_todo(
    payload: TodoCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> dict:
    try:
        todo = await todo_service.create_todo(db, user_id=user.id, payload=payload)
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return _serialize(todo)


@router.get("", response_model=list[TodoRead])
async def list_todos(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    status_filter: str | None = Query(default=None, alias="status"),
    priority: int | None = Query(default=None, ge=1, le=3),
) -> list[dict]:
    try:
        items = await todo_service.list_todos(
            db,
            user_id=user.id,
            status=status_filter,
            priority=priority,
        )
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return [_serialize(t) for t in items]


@router.get("/{todo_id}", response_model=TodoRead)
async def get_todo(
    todo_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> dict:
    try:
        todo = await todo_service.get_todo(db, user_id=user.id, todo_id=todo_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Todo not found")
    return _serialize(todo)


@router.put("/{todo_id}")
async def update_todo(
    todo_id: uuid.UUID,
    payload: TodoUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> dict:
    try:
        await todo_service.update_todo(
            db, user_id=user.id, todo_id=todo_id, payload=payload
        )
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Todo not found")
    except (TransitionError, ValidationError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except DomainError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"message": "Todo updated successfully"}


@router.delete("/{todo_id}")
async def delete_todo(
    todo_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> dict:
    try:
        await todo_service.delete_todo(db, user_id=user.id, todo_id=todo_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Todo not found")
    return {"message": "Todo deleted successfully"}
