"""Tests for batch processor -- RED phase."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from claude_conversation_kg.extractor.models import (
    Entity,
    EntityType,
    ExtractionResult,
    Relationship,
    RelationshipType,
)
from claude_conversation_kg.extractor.processor import BatchProcessor
from claude_conversation_kg.parser.models import (
    ConversationMessage,
    ConversationSession,
)


def _make_session(n_messages: int) -> ConversationSession:
    messages = [
        ConversationMessage(role="user", content=f"Message {i}")
        for i in range(n_messages)
    ]
    return ConversationSession(
        file_path=Path(f"/tmp/test_{n_messages}.jsonl"),
        messages=messages,
    )


def _make_extraction_result() -> ExtractionResult:
    entity = Entity(name="FastAPI", type=EntityType.TECHNOLOGY, description="Framework")
    return ExtractionResult(entities=[entity], relationships=[])


class TestBatchProcessor:
    """Specification tests for BatchProcessor."""

    def test_messages_batched_by_size(self) -> None:
        """25 messages are split into 3 batches (10+10+5)."""
        mock_client = MagicMock()
        mock_client.extract.return_value = _make_extraction_result()

        processor = BatchProcessor(client=mock_client)
        session = _make_session(25)
        processor.process_session(session, batch_size=10)

        assert mock_client.extract.call_count == 3

    def test_cache_by_session_hash(self) -> None:
        """Same session hash skips API call on second invocation."""
        mock_client = MagicMock()
        mock_client.extract.return_value = _make_extraction_result()

        processor = BatchProcessor(client=mock_client)
        session = _make_session(5)

        result1 = processor.process_session(session, batch_size=10)
        result2 = processor.process_session(session, batch_size=10)

        # Should only call extract once (cached on second call)
        assert mock_client.extract.call_count == 1
        assert len(result1.entities) == len(result2.entities)

    def test_results_aggregated(self) -> None:
        """Multiple batches produce a combined ExtractionResult."""
        entity1 = Entity(name="FastAPI", type=EntityType.TECHNOLOGY)
        entity2 = Entity(name="SQLAlchemy", type=EntityType.LIBRARY)
        rel = Relationship(
            source_id=entity1.id,
            target_id=entity2.id,
            type=RelationshipType.USES,
        )

        mock_client = MagicMock()
        mock_client.extract.side_effect = [
            ExtractionResult(entities=[entity1], relationships=[]),
            ExtractionResult(entities=[entity2], relationships=[rel]),
        ]

        processor = BatchProcessor(client=mock_client)
        session = _make_session(15)
        result = processor.process_session(session, batch_size=10)

        assert len(result.entities) == 2
        assert len(result.relationships) == 1
