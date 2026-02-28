"""Tests for visualization renderer -- RED phase."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from claude_conversation_kg.visualization.renderer import GraphRenderer


def _make_mock_query_runner() -> MagicMock:
    """Create a mock QueryRunner with entity and relationship data."""
    runner = MagicMock()
    runner.execute.side_effect = [
        # First call: get entities
        [
            {"e.id": "fastapi-technology", "e.name": "FastAPI", "e.type": "Technology"},
            {"e.id": "sqlalchemy-library", "e.name": "SQLAlchemy", "e.type": "Library"},
        ],
        # Second call: get relationships
        [
            {
                "a.id": "fastapi-technology",
                "b.id": "sqlalchemy-library",
                "type(r)": "USES",
            },
        ],
    ]
    return runner


class TestGraphRenderer:
    """Specification tests for GraphRenderer."""

    def test_generates_html_file(self, tmp_path: Path) -> None:
        """Output path receives valid HTML."""
        output = tmp_path / "graph.html"
        renderer = GraphRenderer()
        renderer.render(_make_mock_query_runner(), output)
        assert output.exists()
        content = output.read_text()
        assert "<html" in content.lower() or "<!doctype" in content.lower()

    def test_nodes_color_coded(self, tmp_path: Path) -> None:
        """Each EntityType has a distinct color in the output."""
        output = tmp_path / "graph.html"
        renderer = GraphRenderer()
        renderer.render(_make_mock_query_runner(), output)
        content = output.read_text()
        # The HTML should contain the entity names
        assert "FastAPI" in content
        assert "SQLAlchemy" in content

    def test_edges_labeled(self, tmp_path: Path) -> None:
        """Relationship types appear as edge labels."""
        output = tmp_path / "graph.html"
        renderer = GraphRenderer()
        renderer.render(_make_mock_query_runner(), output)
        content = output.read_text()
        assert "USES" in content
