"""Tests for CLI commands -- RED phase."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

kuzu = pytest.importorskip("kuzu")

from claude_conversation_kg.cli import app

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

    @patch("claude_conversation_kg.cli._build_pipeline")
    def test_ingest_command(self, mock_build: MagicMock, tmp_path: Path) -> None:
        """kg ingest /path runs pipeline."""
        mock_pipeline = MagicMock()
        mock_pipeline.ingest.return_value = {
            "files_processed": 2,
            "files_skipped": 1,
            "entities_stored": 5,
            "relationships_stored": 3,
            "errors": 0,
        }
        mock_build.return_value = mock_pipeline

        result = runner.invoke(app, ["ingest", str(tmp_path)])
        assert result.exit_code == 0
        assert "2" in result.output  # files processed

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
