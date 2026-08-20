"""Pydantic schemas for todo create / update / read.

Validation rules from TDD §7:
- title required, 1–200 characters
- priority in 1..=3
- status ∈ {"Pending", "InProgress", "Completed"}
- dueDate must be strictly in the future (rejects past and "now" timestamps)
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Literal

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, PlainSerializer, field_validator


TodoStatusLiteral = Literal["Pending", "InProgress", "Completed"]


def _serialize_utc(dt: datetime | None) -> str | None:
    """Render a datetime as ISO-8601 with explicit UTC offset.

    The DB column is `TIMESTAMP WITHOUT TIME ZONE` (TDD §3), so values come
    back naive; we tag them as UTC before serializing so the response is
    unambiguous to clients regardless of server locale.
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


class TodoCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    priority: int = Field(default=3, ge=1, le=3)
    status: TodoStatusLiteral | None = None
    due_date: datetime | None = Field(default=None, alias="dueDate")

    @field_validator("due_date")
    @classmethod
    def due_date_must_be_future(cls, v: datetime | None) -> datetime | None:
        if v is None:
            return v
        # Treat naive datetimes as UTC for comparison — server-clock semantics.
        v_aware = v if v.tzinfo else v.replace(tzinfo=timezone.utc)
        if v_aware <= datetime.now(timezone.utc):
            raise ValueError("dueDate must be in the future")
        return v


class TodoUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    priority: int | None = Field(default=None, ge=1, le=3)
    status: TodoStatusLiteral | None = None
    due_date: datetime | None = Field(default=None, alias="dueDate")

    @field_validator("due_date")
    @classmethod
    def due_date_must_be_future(cls, v: datetime | None) -> datetime | None:
        if v is None:
            return v
        v_aware = v if v.tzinfo else v.replace(tzinfo=timezone.utc)
        if v_aware <= datetime.now(timezone.utc):
            raise ValueError("dueDate must be in the future")
        return v


UtcDateTime = Annotated[
    datetime,
    PlainSerializer(
        lambda dt: _serialize_utc(dt),
        return_type=str | None,
        when_used="json",
    ),
]
UtcDateTimeOrNone = Annotated[
    datetime | None,
    PlainSerializer(
        lambda dt: _serialize_utc(dt),
        return_type=str | None,
        when_used="json",
    ),
]


class TodoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    title: str
    description: str | None = None
    status: str
    priority: int
    due_date: UtcDateTimeOrNone = Field(default=None, alias="dueDate")
    created_at: UtcDateTime = Field(alias="createdAt")
    updated_at: UtcDateTimeOrNone = Field(default=None, alias="updatedAt")
