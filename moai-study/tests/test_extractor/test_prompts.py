"""Tests for extraction prompts -- RED phase."""

from __future__ import annotations

from claude_conversation_kg.extractor.models import EntityType
from claude_conversation_kg.extractor.prompts import SYSTEM_PROMPT, build_user_prompt
from claude_conversation_kg.parser.models import ConversationMessage


class TestPrompts:
    """Specification tests for extraction prompt generation."""

    def test_system_prompt_contains_entity_types(self) -> None:
        """System prompt lists all 9 entity types."""
        for entity_type in EntityType:
            assert entity_type.value in SYSTEM_PROMPT

    def test_user_prompt_includes_messages(self) -> None:
        """Messages are included in user prompt."""
        messages = [
            ConversationMessage(role="user", content="Let's use FastAPI"),
            ConversationMessage(role="assistant", content="Good choice!"),
        ]
        prompt = build_user_prompt(messages)
        assert "FastAPI" in prompt
        assert "Good choice!" in prompt

    def test_prompt_requests_json_output(self) -> None:
        """System prompt asks for JSON format output."""
        assert "JSON" in SYSTEM_PROMPT or "json" in SYSTEM_PROMPT
