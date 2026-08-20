"""Application settings loaded from environment variables.

The service refuses to start when `JWT_SECRET` is missing — fail loud on a
deployment misconfiguration rather than booting with an empty signing key.
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/todos",
        alias="DATABASE_URL",
    )
    jwt_secret: str | None = Field(default=None, alias="JWT_SECRET")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    jwt_expiry_minutes: int = Field(default=60, alias="JWT_EXPIRY_MINUTES")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings()
    if not settings.jwt_secret:
        # Fail loud: an empty signing key would let any caller mint tokens.
        raise RuntimeError(
            "JWT_SECRET environment variable is required. "
            "Set it to a long, random secret before starting the service."
        )
    return settings
