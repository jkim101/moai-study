"""Configuration management via environment variables."""
from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    Environment variable prefix: CCKG_ (except ANTHROPIC_API_KEY).
    """

    model_config = SettingsConfigDict(
        env_prefix="CCKG_",
        env_file=".env",
        extra="ignore",
    )

    db_path: Path = Field(
        default_factory=lambda: Path.home() / ".claude-conversation-kg" / "graph.db"
    )
    log_level: str = "INFO"
    anthropic_api_key: str = Field(
        default="",
        validation_alias="ANTHROPIC_API_KEY",
    )
    batch_size: int = 10
