"""Tests for CLI commands -- RED phase."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

kuzu = pytest.importorskip("kuzu")

from claude_conversation_kg.cli import app
from claude_conversation_kg.extractor.models import UsageStats

runner = CliRunner()


class TestCLI:
    """Specification tests for CLI commands."""

    def test_help_text(self) -> None:
        """kg --help shows all commands."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "ingest" in result.output
        assert "query" in result.output
        assert "visualize" in result.output
        assert "stats" in result.output
        assert "audit" in result.output
        assert "recent" in result.output
        assert "ask" in result.output

    @patch("claude_conversation_kg.cli._build_pipeline")
    def test_ingest_command(self, mock_build: MagicMock, tmp_path: Path) -> None:
        """kg ingest /path runs pipeline."""
        mock_pipeline = MagicMock()
        mock_pipeline.ingest.return_value = {
            "files_processed": 2,
            "files_skipped": 1,
            "sessions_skipped_short": 0,
            "entities_stored": 5,
            "relationships_stored": 3,
            "errors": 0,
            "usage": UsageStats(
                api_calls=3,
                input_tokens=1500,
                output_tokens=600,
                cache_creation_input_tokens=500,
                cache_read_input_tokens=200,
            ),
        }
        mock_build.return_value = mock_pipeline

        result = runner.invoke(app, ["ingest", str(tmp_path)])
        assert result.exit_code == 0
        assert "2" in result.output  # files processed
        assert "API Calls" in result.output
        assert "1,500" in result.output  # input tokens formatted

    @patch("claude_conversation_kg.cli._build_query_runner")
    def test_query_command(self, mock_build: MagicMock) -> None:
        """kg query 'MATCH ...' shows results."""
        mock_runner = MagicMock()
        mock_runner.execute.return_value = [
            {"n.name": "FastAPI", "n.type": "Technology"}
        ]
        mock_build.return_value = mock_runner

        result = runner.invoke(app, ["query", "MATCH (n:Entity) RETURN n.name, n.type"])
        assert result.exit_code == 0
        assert "FastAPI" in result.output

    @patch("claude_conversation_kg.cli._build_query_runner")
    @patch("claude_conversation_kg.cli.GraphRenderer")
    def test_visualize_command(
        self, mock_renderer_cls: MagicMock, mock_build: MagicMock, tmp_path: Path
    ) -> None:
        """kg visualize output.html generates file."""
        mock_runner = MagicMock()
        mock_build.return_value = mock_runner

        output = tmp_path / "graph.html"
        result = runner.invoke(app, ["visualize", str(output)])
        assert result.exit_code == 0
        mock_renderer_cls.return_value.render.assert_called_once()

    @patch("claude_conversation_kg.cli._build_query_runner")
    def test_stats_command(self, mock_build: MagicMock) -> None:
        """kg stats shows statistics table."""
        mock_runner = MagicMock()
        mock_runner.get_stats.return_value = {
            "total_entities": 10,
            "total_relationships": 5,
            "entities_by_type": {"Technology": 3, "Library": 7},
            "relationships_by_type": {"USES": 5},
        }
        mock_build.return_value = mock_runner

        result = runner.invoke(app, ["stats"])
        assert result.exit_code == 0
        assert "10" in result.output

    @patch("claude_conversation_kg.cli._build_query_runner")
    def test_audit_command_shows_top_entities(self, mock_build: MagicMock) -> None:
        """kg audit displays top entities by mention count."""
        mock_runner = MagicMock()
        mock_runner.get_audit.return_value = {
            "total_entities": 50,
            "top_entities": [
                {"name": "FastAPI", "type": "Technology", "mention_count": 42},
                {"name": "SQLAlchemy", "type": "Library", "mention_count": 18},
            ],
        }
        mock_build.return_value = mock_runner

        result = runner.invoke(app, ["audit"])
        assert result.exit_code == 0
        assert "FastAPI" in result.output
        assert "42" in result.output
        assert "SQLAlchemy" in result.output

    @patch("claude_conversation_kg.cli._build_query_runner")
    def test_audit_command_empty_graph(self, mock_build: MagicMock) -> None:
        """kg audit on empty graph shows a helpful message."""
        mock_runner = MagicMock()
        mock_runner.get_audit.return_value = {
            "total_entities": 0,
            "top_entities": [],
        }
        mock_build.return_value = mock_runner

        result = runner.invoke(app, ["audit"])
        assert result.exit_code == 0
        assert "empty" in result.output.lower() or "ingest" in result.output.lower()

    @patch("claude_conversation_kg.cli._build_query_runner")
    def test_audit_command_respects_limit(self, mock_build: MagicMock) -> None:
        """kg audit --limit 5 passes limit to get_audit."""
        mock_runner = MagicMock()
        mock_runner.get_audit.return_value = {
            "total_entities": 100,
            "top_entities": [],
        }
        mock_build.return_value = mock_runner

        runner.invoke(app, ["audit", "--limit", "5"])
        mock_runner.get_audit.assert_called_once_with(limit=5)

    # -- recent command tests --

    @patch("claude_conversation_kg.cli._build_query_runner")
    def test_recent_command_shows_entities(self, mock_build: MagicMock) -> None:
        """kg recent 7d displays recently first-seen entities."""
        mock_runner = MagicMock()
        mock_runner.get_recent_entities.return_value = [
            {
                "name": "Kuzu",
                "type": "Technology",
                "mention_count": 5,
                "first_seen": "2026-03-01 12:00:00",
            },
        ]
        mock_build.return_value = mock_runner

        result = runner.invoke(app, ["recent", "7d"])
        assert result.exit_code == 0
        assert "Kuzu" in result.output
        assert "1 entities found" in result.output

    @patch("claude_conversation_kg.cli._build_query_runner")
    def test_recent_command_with_type_filter(self, mock_build: MagicMock) -> None:
        """kg recent 30d --type Technology passes type filter."""
        mock_runner = MagicMock()
        mock_runner.get_recent_entities.return_value = []
        mock_build.return_value = mock_runner

        result = runner.invoke(app, ["recent", "30d", "--type", "Technology"])
        assert result.exit_code == 0
        mock_runner.get_recent_entities.assert_called_once_with(
            days=30, entity_type="Technology"
        )

    @patch("claude_conversation_kg.cli._build_query_runner")
    def test_recent_command_no_results(self, mock_build: MagicMock) -> None:
        """kg recent 1d with no results shows message."""
        mock_runner = MagicMock()
        mock_runner.get_recent_entities.return_value = []
        mock_build.return_value = mock_runner

        result = runner.invoke(app, ["recent", "1d"])
        assert result.exit_code == 0
        assert "No entities found" in result.output

    def test_recent_command_invalid_period(self) -> None:
        """kg recent xyz shows error for invalid period."""
        result = runner.invoke(app, ["recent", "xyz"])
        assert result.exit_code != 0

    # -- ask command tests --

    @patch("claude_conversation_kg.cli.NaturalLanguageQuerier")
    @patch("claude_conversation_kg.cli.initialize_schema")
    @patch("claude_conversation_kg.cli.KuzuConnection")
    @patch("claude_conversation_kg.cli._get_settings")
    def test_ask_command_shows_answer(
        self,
        mock_settings: MagicMock,
        mock_conn_cls: MagicMock,
        mock_init_schema: MagicMock,
        mock_querier_cls: MagicMock,
    ) -> None:
        """kg ask shows generated Cypher and answer."""
        mock_settings.return_value = MagicMock(
            anthropic_api_key="test-key",
            db_path="/tmp/test.db",
        )
        mock_querier = MagicMock()
        mock_querier.ask.return_value = (
            "MATCH (e:Entity) RETURN e.name LIMIT 5",
            "Here are the top entities.",
        )
        mock_querier.usage = UsageStats(
            api_calls=2, input_tokens=500, output_tokens=200
        )
        mock_querier_cls.return_value = mock_querier

        result = runner.invoke(app, ["ask", "What entities exist?"])
        assert result.exit_code == 0
        assert "MATCH" in result.output
        assert "Here are the top entities" in result.output
        assert "API Calls" in result.output

    @patch("claude_conversation_kg.cli._get_settings")
    def test_ask_command_no_api_key(self, mock_settings: MagicMock) -> None:
        """kg ask without API key shows error."""
        mock_settings.return_value = MagicMock(anthropic_api_key="")

        result = runner.invoke(app, ["ask", "What entities exist?"])
        assert result.exit_code == 1
        assert "ANTHROPIC_API_KEY" in result.output
