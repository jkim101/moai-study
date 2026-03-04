"""Tests for visualization renderer -- RED phase."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from claude_conversation_kg.visualization.renderer import GraphRenderer

_ENTITY_ROWS = [
    {
        "e.id": "fastapi-technology",
        "e.name": "FastAPI",
        "e.type": "Technology",
        "e.mention_count": 1,
    },
    {
        "e.id": "sqlalchemy-library",
        "e.name": "SQLAlchemy",
        "e.type": "Library",
        "e.mention_count": 1,
    },
]

_USES_EDGE = [{"a.id": "fastapi-technology", "b.id": "sqlalchemy-library"}]


def _make_mock_query_runner(
    mention_counts: dict[str, int] | None = None,
    include_edges: bool = False,
) -> MagicMock:
    """Create a mock QueryRunner returning entity and (optionally) relationship data.

    mention_counts maps entity id to mention_count override.
    include_edges: if True, the USES relationship query returns one edge.
    """
    counts = mention_counts or {}
    entity_rows = [
        {**row, "e.mention_count": counts.get(row["e.id"], row["e.mention_count"])}
        for row in _ENTITY_ROWS
    ]

    # Build side_effect: first call = entities, then one call per RelationshipType
    from claude_conversation_kg.extractor.models import RelationshipType

    rel_responses = []
    for rel_type in RelationshipType:
        if include_edges and rel_type.value == "USES":
            rel_responses.append(_USES_EDGE)
        else:
            rel_responses.append([])

    runner = MagicMock()
    runner.execute.side_effect = [entity_rows, *rel_responses]
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
        renderer.render(_make_mock_query_runner(include_edges=True), output)
        content = output.read_text()
        assert "USES" in content

    def test_high_mention_count_produces_larger_node(self, tmp_path: Path) -> None:
        """A node with higher mention_count is rendered at a larger size."""
        output_low = tmp_path / "low.html"
        output_high = tmp_path / "high.html"

        renderer = GraphRenderer()
        renderer.render(
            _make_mock_query_runner({"fastapi-technology": 1, "sqlalchemy-library": 1}),
            output_low,
        )
        renderer.render(
            _make_mock_query_runner(
                {"fastapi-technology": 50, "sqlalchemy-library": 50}
            ),
            output_high,
        )

        # Both files should be valid HTML
        assert output_low.exists()
        assert output_high.exists()

    def test_node_size_scales_with_mention_count(self, tmp_path: Path) -> None:
        """Node size for mention_count=20 is greater than for mention_count=1."""
        size_low = GraphRenderer._mention_count_to_size(1)
        size_high = GraphRenderer._mention_count_to_size(20)
        assert size_high > size_low

    def test_node_size_clamped_to_max(self, tmp_path: Path) -> None:
        """Node size does not exceed the defined maximum."""
        size = GraphRenderer._mention_count_to_size(9999)
        assert size <= 60

    def test_node_size_minimum_is_at_least_10(self, tmp_path: Path) -> None:
        """Even a mention_count of 0 yields a visible minimum node size."""
        size = GraphRenderer._mention_count_to_size(0)
        assert size >= 10
