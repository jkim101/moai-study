"""Tests for JSONL transformer -- RED phase."""

from __future__ import annotations

from pathlib import Path

from claude_conversation_kg.parser.transformer import transform


class TestTransformer:
    """Specification tests for raw dict to ConversationSession transformation."""

    def test_transform_valid_messages(self) -> None:
        """List of raw dicts produces a ConversationSession with messages."""
        raw = [
            {"type": "user", "message": {"role": "user", "content": "Hello"}},
            {
                "type": "assistant",
                "message": {"role": "assistant", "content": "Hi there"},
            },
        ]
        session = transform(Path("/tmp/test.jsonl"), iter(raw))
        assert len(session.messages) == 2
        assert session.messages[0].role == "user"
        assert session.messages[1].content == "Hi there"
        assert session.file_path == Path("/tmp/test.jsonl")

    def test_malformed_messages_skipped(self) -> None:
        """Invalid messages are logged and skipped."""
        raw = [
            {"type": "user", "message": {"role": "user", "content": "Valid"}},
            {
                "type": "assistant",
                "message": {"role": "bad_role", "content": "Invalid"},
            },
            {
                "type": "assistant",
                "message": {"role": "assistant", "content": "Also valid"},
            },
        ]
        session = transform(Path("/tmp/test.jsonl"), iter(raw))
        assert len(session.messages) == 2
        assert session.messages[0].content == "Valid"
        assert session.messages[1].content == "Also valid"

    def test_empty_file_returns_empty_session(self) -> None:
        """No messages produces an empty session."""
        session = transform(Path("/tmp/empty.jsonl"), iter([]))
        assert len(session.messages) == 0
        assert session.file_path == Path("/tmp/empty.jsonl")
