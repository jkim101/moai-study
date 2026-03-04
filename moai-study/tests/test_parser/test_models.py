"""Tests for parser models -- RED phase."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from claude_conversation_kg.parser.models import (
    ConversationMessage,
    ConversationSession,
)


class TestConversationMessage:
    """Specification tests for ConversationMessage model."""

    def test_valid_message_parsed_correctly(self) -> None:
        """Valid JSONL dict creates a ConversationMessage with all fields."""
        data = {
            "type": "message",
            "role": "user",
            "content": "Hello world",
            "timestamp": "2026-01-01T10:00:00Z",
        }
        msg = ConversationMessage.model_validate(data)
        assert msg.type == "message"
        assert msg.role == "user"
        assert msg.content == "Hello world"
        assert msg.timestamp == datetime(2026, 1, 1, 10, 0, 0, tzinfo=UTC)

    def test_invalid_role_raises_error(self) -> None:
        """Unknown role value raises ValidationError."""
        data = {
            "type": "message",
            "role": "unknown_role",
            "content": "Hello",
        }
        with pytest.raises(ValidationError):
            ConversationMessage.model_validate(data)

    def test_missing_content_defaults(self) -> None:
        """Missing content field defaults to empty string."""
        data = {
            "type": "message",
            "role": "assistant",
        }
        msg = ConversationMessage.model_validate(data)
        assert msg.content == ""

    def test_content_as_list(self) -> None:
        """Content can be a list (e.g., multi-part messages)."""
        data = {
            "type": "message",
            "role": "assistant",
            "content": [{"type": "text", "text": "Hello"}],
        }
        msg = ConversationMessage.model_validate(data)
        assert isinstance(msg.content, list)

    def test_timestamp_optional(self) -> None:
        """Timestamp is optional and defaults to None."""
        data = {"type": "message", "role": "user", "content": "Hi"}
        msg = ConversationMessage.model_validate(data)
        assert msg.timestamp is None


class TestConversationSession:
    """Specification tests for ConversationSession model."""

    def test_session_aggregates_messages(self) -> None:
        """ConversationSession holds a list of ConversationMessage objects."""
        messages = [
            ConversationMessage(type="message", role="user", content="Hello"),
            ConversationMessage(type="message", role="assistant", content="Hi"),
        ]
        session = ConversationSession(
            file_path=Path("/tmp/test.jsonl"),
            messages=messages,
        )
        assert len(session.messages) == 2
        assert session.file_path == Path("/tmp/test.jsonl")
        assert session.metadata == {}

    def test_session_with_metadata(self) -> None:
        """ConversationSession can include arbitrary metadata."""
        session = ConversationSession(
            file_path=Path("/tmp/test.jsonl"),
            messages=[],
            metadata={"source": "test"},
        )
        assert session.metadata == {"source": "test"}
