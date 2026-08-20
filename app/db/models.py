"""ORM models for `users` and `todos` per TDD §3.

UUID primary keys, varchar lengths matching the spec, status stored as a
string column with a CHECK constraint (design §9) so bad values fail at the
DB layer in addition to the Pydantic check.

The UUID column uses `CHAR(36)` under SQLite (via `with_variant`) so the
test suite can run on an in-memory aiosqlite database without needing a
live Postgres instance. On Postgres it uses the native `UUID` type.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    CHAR,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    func,
    types,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


# A portable UUID column: native UUID on Postgres, CHAR(36) on SQLite/MySQL.
# `with_variant` returns a `Uuid` instance whose dialect-level impl is swapped
# for SQLite/MySQL — no TypeDecorator subclass needed.
GUID = types.Uuid().with_variant(CHAR(36), "sqlite", "mysql")


class TodoStatus(str, enum.Enum):
    PENDING = "Pending"
    IN_PROGRESS = "InProgress"
    COMPLETED = "Completed"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(150), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        nullable=False,
        server_default=func.now(),
    )

    todos: Mapped[list["Todo"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )


class Todo(Base):
    __tablename__ = "todos"
    __table_args__ = (
        CheckConstraint(
            "status IN ('Pending', 'InProgress', 'Completed')",
            name="ck_todos_status",
        ),
        Index("ix_todos_user_id", "user_id"),
        Index("ix_todos_status", "status"),
        Index("ix_todos_due_date", "due_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=TodoStatus.PENDING.value,
    )
    priority: Mapped[int] = mapped_column(nullable=False, default=3)
    due_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=False), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    user: Mapped[User] = relationship(back_populates="todos")
