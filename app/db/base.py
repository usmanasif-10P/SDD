"""SQLAlchemy 2.x async engine, session factory, and declarative base.

The application and database are both expected to run in UTC. Set the
Postgres session timezone via either of:

- `postgresql.conf`:   `timezone = 'UTC'`
- per-role:            `ALTER ROLE <user> SET timezone = 'UTC';`

With the server's `timezone` aligned to the app's `datetime.now(timezone.utc)`
logic, naive timestamps round-trip without any per-connection event code.
"""

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings

_settings = get_settings()

engine = create_async_engine(
    _settings.database_url,
    echo=False,
    pool_pre_ping=True,
)

AsyncSessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


async def get_db() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency that yields a session and ensures cleanup."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
