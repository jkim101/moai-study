"""Tests for extraction client -- RED phase."""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from claude_conversation_kg.exceptions import AuthenticationError, ExtractionError
from claude_conversation_kg.extractor.client import ExtractionClient
from claude_conversation_kg.parser.models import ConversationMessage


def _make_messages() -> list[ConversationMessage]:
    return [
        ConversationMessage(role="user", content="Let's use FastAPI"),
        ConversationMessage(role="assistant", content="Great choice!"),
    ]


def _mock_response(content: str) -> MagicMock:
    """Create a mock Anthropic API response."""
    block = MagicMock()
    block.text = content
    response = MagicMock()
    response.content = [block]
    return response


class TestExtractionClient:
    """Specification tests for ExtractionClient."""

    @patch("claude_conversation_kg.extractor.client.anthropic.Anthropic")
    def test_successful_extraction(self, mock_anthropic_cls: MagicMock) -> None:
        """Mock API response produces an ExtractionResult."""
        api_response = json.dumps({
            "entities": [
                {
                    "name": "FastAPI",
                    "type": "Technology",
                    "description": "Web framework",
                },
                {
                    "name": "Python",
                    "type": "Technology",
                    "description": "Language",
                },
            ],
            "relationships": [
                {
                    "source": "FastAPI",
                    "target": "Python",
                    "type": "USES",
                    "context": "FastAPI is a Python framework",
                    "confidence": 0.9,
                }
            ],
        })
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _mock_response(api_response)
        mock_anthropic_cls.return_value = mock_client

        client = ExtractionClient(api_key="test-key")
        result = client.extract(_make_messages())

        assert len(result.entities) == 2
        assert result.entities[0].name == "FastAPI"
        assert len(result.relationships) == 1

    @patch("claude_conversation_kg.extractor.client.anthropic.Anthropic")
    def test_retry_on_rate_limit(self, mock_anthropic_cls: MagicMock) -> None:
        """Mock 429 then 200 retries and succeeds."""
        import anthropic as anthropic_lib

        rate_limit_error = anthropic_lib.RateLimitError(
            message="rate limited",
            response=MagicMock(status_code=429),
            body=None,
        )

        api_response = json.dumps({
            "entities": [{"name": "X", "type": "Technology", "description": ""}],
            "relationships": [],
        })

        mock_client = MagicMock()
        mock_client.messages.create.side_effect = [
            rate_limit_error,
            _mock_response(api_response),
        ]
        mock_anthropic_cls.return_value = mock_client

        client = ExtractionClient(api_key="test-key")
        result = client.extract(_make_messages(), max_retries=3)
        assert len(result.entities) == 1

    @patch("claude_conversation_kg.extractor.client.anthropic.Anthropic")
    def test_halt_on_auth_error(self, mock_anthropic_cls: MagicMock) -> None:
        """Mock 401 raises AuthenticationError."""
        import anthropic as anthropic_lib

        auth_error = anthropic_lib.AuthenticationError(
            message="invalid api key",
            response=MagicMock(status_code=401),
            body=None,
        )

        mock_client = MagicMock()
        mock_client.messages.create.side_effect = auth_error
        mock_anthropic_cls.return_value = mock_client

        client = ExtractionClient(api_key="bad-key")
        with pytest.raises(AuthenticationError):
            client.extract(_make_messages())

    @patch("claude_conversation_kg.extractor.client.anthropic.Anthropic")
    @patch("claude_conversation_kg.extractor.client.time.sleep")
    def test_max_retries_exceeded(
        self, mock_sleep: MagicMock, mock_anthropic_cls: MagicMock
    ) -> None:
        """Mock 3x 429 raises ExtractionError."""
        import anthropic as anthropic_lib

        rate_limit_error = anthropic_lib.RateLimitError(
            message="rate limited",
            response=MagicMock(status_code=429),
            body=None,
        )

        mock_client = MagicMock()
        mock_client.messages.create.side_effect = rate_limit_error
        mock_anthropic_cls.return_value = mock_client

        client = ExtractionClient(api_key="test-key")
        with pytest.raises(ExtractionError):
            client.extract(_make_messages(), max_retries=3)
