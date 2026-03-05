"""Tests for ingestion pipeline -- RED phase."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

kuzu = pytest.importorskip("kuzu")

from claude_conversation_kg.extractor.models import (
    Entity,
    EntityType,
    ExtractionResult,
    UsageStats,
)
from claude_conversation_kg.graph.connection import KuzuConnection
from claude_conversation_kg.graph.schema import initialize_schema
from claude_conversation_kg.graph.store import GraphStore
from claude_conversation_kg.pipeline import IngestionPipeline


@pytest.fixture()
def graph_store(tmp_path: Path) -> GraphStore:
    """Create a GraphStore with initialized schema."""
    conn = KuzuConnection(tmp_path / "test.db")
    initialize_schema(conn.conn)
    return GraphStore(conn.conn)


def _make_jsonl_file(
    tmp_path: Path, name: str = "test.jsonl", num_messages: int = 4
) -> Path:
    """Create a valid JSONL file using Claude Code nested format.

    By default creates 4 messages (above MIN_SESSION_MESSAGES threshold).
    """
    tmp_path.mkdir(parents=True, exist_ok=True)
    path = tmp_path / name
    messages = []
    for i in range(num_messages):
        role = "user" if i % 2 == 0 else "assistant"
        messages.append(
            {
                "type": role,
                "timestamp": f"2025-01-01T00:{i:02d}:00Z",
                "message": {"role": role, "content": f"Message {i}"},
            }
        )
    path.write_text("\n".join(json.dumps(m) for m in messages) + "\n")
    return path


class TestIngestionPipeline:
    """Specification tests for IngestionPipeline."""

    def test_pipeline_ingests_single_file(
        self, tmp_path: Path, graph_store: GraphStore
    ) -> None:
        """Mock extractor stores entities in graph."""
        _make_jsonl_file(tmp_path / "data", "conv.jsonl")

        mock_processor = MagicMock()
        mock_processor.process_session.return_value = (
            ExtractionResult(
                entities=[
                    Entity(
                        name="FastAPI",
                        type=EntityType.TECHNOLOGY,
                        description="Framework",
                    )
                ],
                relationships=[],
            ),
            UsageStats(api_calls=1, input_tokens=200, output_tokens=100),
        )

        pipeline = IngestionPipeline(
            store=graph_store,
            processor=mock_processor,
        )
        result = pipeline.ingest(tmp_path / "data")

        assert result["files_processed"] == 1
        assert result["entities_stored"] >= 1
        assert result["usage"].api_calls == 1
        mock_processor.process_session.assert_called_once()

    def test_pipeline_skips_processed_files(
        self, tmp_path: Path, graph_store: GraphStore
    ) -> None:
        """Already processed file is skipped."""
        jsonl_path = _make_jsonl_file(tmp_path / "data", "conv.jsonl")

        # Mark file as already processed
        graph_store.mark_file_processed(jsonl_path, jsonl_path.stat().st_mtime)

        mock_processor = MagicMock()
        pipeline = IngestionPipeline(
            store=graph_store,
            processor=mock_processor,
        )
        result = pipeline.ingest(tmp_path / "data")

        assert result["files_processed"] == 0
        assert result["files_skipped"] == 1
        mock_processor.process_session.assert_not_called()

    def test_pipeline_handles_extraction_errors(
        self, tmp_path: Path, graph_store: GraphStore
    ) -> None:
        """Extraction failure is logged and pipeline continues."""
        _make_jsonl_file(tmp_path / "data", "a.jsonl")
        _make_jsonl_file(tmp_path / "data", "b.jsonl")

        mock_processor = MagicMock()
        mock_processor.process_session.side_effect = [
            RuntimeError("API failed"),
            (
                ExtractionResult(
                    entities=[Entity(name="X", type=EntityType.CONCEPT)],
                    relationships=[],
                ),
                UsageStats(api_calls=1),
            ),
        ]

        pipeline = IngestionPipeline(
            store=graph_store,
            processor=mock_processor,
        )
        result = pipeline.ingest(tmp_path / "data")

        assert result["files_processed"] == 1
        assert result["errors"] == 1

    def test_pipeline_skips_short_sessions(
        self, tmp_path: Path, graph_store: GraphStore
    ) -> None:
        """Sessions with fewer than MIN_SESSION_MESSAGES are skipped."""
        _make_jsonl_file(tmp_path / "data", "short.jsonl", num_messages=2)

        mock_processor = MagicMock()
        pipeline = IngestionPipeline(
            store=graph_store,
            processor=mock_processor,
        )
        result = pipeline.ingest(tmp_path / "data")

        assert result["files_processed"] == 0
        assert result["sessions_skipped_short"] == 1
        assert result["files_skipped"] == 1
        mock_processor.process_session.assert_not_called()
