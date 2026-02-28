"""Tests for config module -- RED phase."""
from __future__ import annotations

from pathlib import Path

from claude_conversation_kg.config import Settings


class TestSettings:
    """Specification tests for Settings configuration."""

    def test_default_db_path(self) -> None:
        """Default db_path is ~/.claude-conversation-kg/graph.db."""
        settings = Settings(anthropic_api_key="test-key")
        expected = Path.home() / ".claude-conversation-kg" / "graph.db"
        assert settings.db_path == expected

    def test_env_var_overrides_default(self, monkeypatch: object) -> None:
        """CCKG_DB_PATH env var overrides the default."""
        monkeypatch.setenv("CCKG_DB_PATH", "/custom/path/graph.db")  # type: ignore[attr-defined]
        settings = Settings(anthropic_api_key="test-key")
        assert settings.db_path == Path("/custom/path/graph.db")

    def test_api_key_from_env(self, monkeypatch: object) -> None:
        """Reads ANTHROPIC_API_KEY from environment."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-123")  # type: ignore[attr-defined]
        settings = Settings()
        assert settings.anthropic_api_key == "sk-test-123"

    def test_batch_size_configurable(self, monkeypatch: object) -> None:
        """CCKG_BATCH_SIZE env var configures batch size."""
        monkeypatch.setenv("CCKG_BATCH_SIZE", "20")  # type: ignore[attr-defined]
        settings = Settings(anthropic_api_key="test-key")
        assert settings.batch_size == 20

    def test_default_batch_size(self) -> None:
        """Default batch size is 10."""
        settings = Settings(anthropic_api_key="test-key")
        assert settings.batch_size == 10

    def test_default_log_level(self) -> None:
        """Default log level is INFO."""
        settings = Settings(anthropic_api_key="test-key")
        assert settings.log_level == "INFO"
