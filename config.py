"""
WZDM LiveRecord - Core configuration.

Project-level defaults. Application-level settings are in
`backend/app/core/config.py`. This module exists for local dev and tests.
"""

from functools import lru_cache

from pydantic import BaseSettings, SecretStr
from pydantic_settings import SettingsConfigDict


class ProjectSettings(BaseSettings):
    APP_NAME: str = "WZDM LiveRecord"
    APP_ENV: str = "development"
    DEBUG: bool = True

    # Supabase credentials (loaded from backend/.env)
    SUPABASE_URL: str
    SUPABASE_ANON_KEY: SecretStr
    SUPABASE_SERVICE_ROLE_KEY: SecretStr

    FRONTEND_URL: str = "http://localhost:5173"
    HOST: str = "0.0.0.0"
    PORT: int = 4000

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> ProjectSettings:
    """Return a cached settings instance."""
    return ProjectSettings()


settings = get_settings()
