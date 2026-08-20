"""initial users and todos tables

Revision ID: 0001_initial
Revises:
Create Date: 2026-08-20
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("email", sa.String(150), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "todos",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.String(2000), nullable=True),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="Pending",
        ),
        sa.Column("priority", sa.Integer, nullable=False, server_default="3"),
        sa.Column("due_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "status IN ('Pending', 'InProgress', 'Completed')",
            name="ck_todos_status",
        ),
    )
    op.create_index("ix_todos_user_id", "todos", ["user_id"], unique=False)
    op.create_index("ix_todos_status", "todos", ["status"], unique=False)
    op.create_index("ix_todos_due_date", "todos", ["due_date"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_todos_due_date", table_name="todos")
    op.drop_index("ix_todos_status", table_name="todos")
    op.drop_index("ix_todos_user_id", table_name="todos")
    op.drop_table("todos")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
