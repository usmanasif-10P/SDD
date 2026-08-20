"""Shared API dependencies. Re-exports for router-level imports."""

from app.core.security import get_current_user  # noqa: F401
from app.db.base import get_db  # noqa: F401
