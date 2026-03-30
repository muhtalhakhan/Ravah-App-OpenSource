from __future__ import annotations

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    GOOGLE_API_KEY: str | None = None
    GOOGLE_AI_MODEL: str = "gemini-2.5-flash-preview-04-17"

    model_config = SettingsConfigDict(
        # Look in the current directory first, then ~/.ravah/.env
        env_file=[".env", str(Path.home() / ".ravah" / ".env")],
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
