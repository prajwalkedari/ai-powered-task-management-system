"""Application settings, loaded from environment variables and an optional .env file."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]
PLACEHOLDER_SECRET_PREFIX = "replace-with"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "AI-Powered Task Management System"
    app_version: str = "1.0.0"

    database_url: str = Field(
        ..., description="SQLAlchemy URL, e.g. postgresql+psycopg://user:pass@host:5432/db"
    )

    jwt_secret_key: str = Field(..., min_length=32)
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = Field(default=60, ge=1, le=1440)

    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.5-flash"
    gemini_base_url: str = "https://generativelanguage.googleapis.com/v1beta"
    gemini_timeout_seconds: float = Field(default=20.0, gt=0, le=120)

    @field_validator("jwt_secret_key")
    @classmethod
    def reject_placeholder_secret(cls, value: str) -> str:
        if value.lower().startswith(PLACEHOLDER_SECRET_PREFIX):
            raise ValueError(
                "JWT_SECRET_KEY still holds the .env.example placeholder. "
                "Replace it with a random secret of at least 32 characters."
            )
        return value

    @field_validator("gemini_api_key")
    @classmethod
    def blank_api_key_means_unset(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None


@lru_cache
def get_settings() -> Settings:
    return Settings()
