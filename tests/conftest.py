"""Test fixtures.

Uses SQLite in-memory via aiosqlite so the test suite runs without a real
Postgres. A small adapter in `_patch_asyncpg` swaps the default asyncpg driver
to aiosqlite for the duration of the test process.

For environments that already provide Postgres (and prefer to run against the
real DB), set `TEST_DATABASE_URL=postgresql+asyncpg://...` before pytest and
the fixture will use it.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

# Default: SQLite. Override via env var when a real Postgres is preferred.
TEST_DB_URL = os.environ.get(
    "TEST_DATABASE_URL", "sqlite+aiosqlite:///:memory:"
)

# The settings module reads DATABASE_URL at import time; point it at the
# test DB before app modules are imported.
os.environ.setdefault("DATABASE_URL", TEST_DB_URL)
os.environ.setdefault("JWT_SECRET", "test-secret-key-for-unit-tests-only")
os.environ.setdefault("JWT_ALGORITHM", "HS256")
os.environ.setdefault("JWT_EXPIRY_MINUTES", "60")

# Import after env so Settings picks them up.
from app.core.config import get_settings  # noqa: E402
from app.core.security import (  # noqa: E402
    create_access_token,
    hash_password,
)
from app.db import base as db_base  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.models import User  # noqa: E402
from app.main import create_app  # noqa: E402

# Build an isolated engine + sessionmaker for tests.
_test_engine = create_async_engine(TEST_DB_URL, future=True)
_test_sessionmaker: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=_test_engine, expire_on_commit=False, autoflush=False
)

# Override the module-level engine + sessionmaker so app code uses our test ones.
db_base.engine = _test_engine
db_base.AsyncSessionLocal = _test_sessionmaker
get_settings.cache_clear()


async def _override_get_db() -> AsyncIterator[AsyncSession]:
    async with _test_sessionmaker() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


@pytest_asyncio.fixture(autouse=True)
async def _create_tables() -> AsyncIterator[None]:
    # SQLite doesn't have native UUID / timezone types, but for unit tests we
    # don't rely on those — only on the schema and CRUD behavior.
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    async with _test_sessionmaker() as session:
        yield session


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    app = create_app()
    app.dependency_overrides[db_base.get_db] = _override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


async def _make_user(
    session: AsyncSession,
    *,
    email: str,
    password: str = "Password123!",
    name: str | None = None,
) -> User:
    user = User(
        name=name or email.split("@")[0],
        email=email,
        password_hash=hash_password(password),
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


@pytest_asyncio.fixture
async def user_factory(db_session: AsyncSession):
    async def _factory(email: str, password: str = "Password123!") -> User:
        return await _make_user(db_session, email=email, password=password)

    return _factory


def _token_for(user: User) -> str:
    return create_access_token(user.id)


@pytest_asyncio.fixture
async def auth_headers(user_factory):
    """Returns a callable that builds {Authorization: Bearer ...} for a user."""
    async def _builder(
        email: str = "alice@example.com",
        password: str = "Password123!",
    ) -> dict[str, str]:
        user = await user_factory(email=email, password=password)
        return {"Authorization": f"Bearer {_token_for(user)}"}

    return _builder


def future_iso(days: int = 1) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()
