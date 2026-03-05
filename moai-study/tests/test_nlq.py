"""Tests for the natural language query module."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from claude_conversation_kg.exceptions import QueryError
from claude_conversation_kg.nlq import NaturalLanguageQuerier


class TestNaturalLanguageQuerier:
    """Specification tests for NaturalLanguageQuerier."""

    def _make_querier(self) -> tuple[NaturalLanguageQuerier, MagicMock]:
        """Create a querier with mocked Anthropic client and Kuzu connection."""
        mock_conn = MagicMock()
        with patch("claude_conversation_kg.nlq.anthropic") as mock_anthropic:
            mock_client = MagicMock()
            mock_anthropic.Anthropic.return_value = mock_client
            querier = NaturalLanguageQuerier(
                api_key="test-key", conn=mock_conn
            )
        return querier, mock_conn

    def _mock_api_response(
        self, querier: NaturalLanguageQuerier, text: str
    ) -> None:
        """Configure the mocked client to return a specific text response."""
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=text)]
        mock_response.usage = MagicMock(
            input_tokens=100,
            output_tokens=50,
            cache_creation_input_tokens=0,
            cache_read_input_tokens=0,
        )
        querier._client.messages.create.return_value = mock_response

    def test_parse_cypher_from_fenced_block(self) -> None:
        """Extracts Cypher from a ```cypher code fence."""
        raw = "Here is the query:\n```cypher\nMATCH (e:Entity) RETURN e.name\n```"
        result = NaturalLanguageQuerier._parse_cypher(raw)
        assert result == "MATCH (e:Entity) RETURN e.name"

    def test_parse_cypher_from_plain_fence(self) -> None:
        """Extracts Cypher from a ``` code fence without language."""
        raw = "```\nMATCH (e:Entity) RETURN e.name\n```"
        result = NaturalLanguageQuerier._parse_cypher(raw)
        assert result == "MATCH (e:Entity) RETURN e.name"

    def test_parse_cypher_fallback_plain_text(self) -> None:
        """Falls back to full text when no code fence is present."""
        raw = "MATCH (e:Entity) RETURN e.name"
        result = NaturalLanguageQuerier._parse_cypher(raw)
        assert result == "MATCH (e:Entity) RETURN e.name"

    def test_ask_returns_cypher_and_answer(self) -> None:
        """ask() returns generated Cypher and natural language summary."""
        querier, mock_conn = self._make_querier()

        # First API call returns Cypher.
        cypher_response = MagicMock()
        cypher_response.content = [
            MagicMock(text="```cypher\nMATCH (e:Entity) RETURN e.name LIMIT 5\n```")
        ]
        cypher_response.usage = MagicMock(
            input_tokens=100,
            output_tokens=50,
            cache_creation_input_tokens=0,
            cache_read_input_tokens=0,
        )

        # Second API call returns summary.
        summary_response = MagicMock()
        summary_response.content = [MagicMock(text="Found 5 entities.")]
        summary_response.usage = MagicMock(
            input_tokens=200,
            output_tokens=30,
            cache_creation_input_tokens=0,
            cache_read_input_tokens=0,
        )

        querier._client.messages.create.side_effect = [
            cypher_response,
            summary_response,
        ]

        # Mock Kuzu execute to return results.
        mock_result = MagicMock()
        mock_result.get_column_names.return_value = ["e.name"]
        mock_result.has_next.side_effect = [True, True, False]
        mock_result.get_next.side_effect = [["FastAPI"], ["Django"]]
        mock_conn.execute.return_value = mock_result

        cypher, answer = querier.ask("What technologies exist?")

        assert cypher == "MATCH (e:Entity) RETURN e.name LIMIT 5"
        assert answer == "Found 5 entities."
        assert querier.usage.api_calls == 2

    def test_ask_empty_results(self) -> None:
        """ask() returns 'no results' message when query has no rows."""
        querier, mock_conn = self._make_querier()

        cypher_response = MagicMock()
        cypher_response.content = [
            MagicMock(text="```cypher\nMATCH (e:Entity) RETURN e.name\n```")
        ]
        cypher_response.usage = MagicMock(
            input_tokens=100,
            output_tokens=50,
            cache_creation_input_tokens=0,
            cache_read_input_tokens=0,
        )
        querier._client.messages.create.return_value = cypher_response

        mock_result = MagicMock()
        mock_result.get_column_names.return_value = ["e.name"]
        mock_result.has_next.return_value = False
        mock_conn.execute.return_value = mock_result

        cypher, answer = querier.ask("Any entities?")
        assert "No results found" in answer
        # Only 1 API call (no summarization needed).
        assert querier.usage.api_calls == 1

    def test_ask_invalid_cypher_raises_query_error(self) -> None:
        """ask() raises QueryError when generated Cypher fails execution."""
        querier, mock_conn = self._make_querier()

        cypher_response = MagicMock()
        cypher_response.content = [
            MagicMock(text="```cypher\nINVALID QUERY\n```")
        ]
        cypher_response.usage = MagicMock(
            input_tokens=100,
            output_tokens=50,
            cache_creation_input_tokens=0,
            cache_read_input_tokens=0,
        )
        querier._client.messages.create.return_value = cypher_response

        mock_conn.execute.side_effect = RuntimeError("Parse error")

        with pytest.raises(QueryError, match="Generated Cypher query failed"):
            querier.ask("Bad question")

    def test_usage_accumulates_across_calls(self) -> None:
        """Usage stats accumulate from both API calls."""
        querier, mock_conn = self._make_querier()

        resp1 = MagicMock()
        cypher_text = "```cypher\nMATCH (e:Entity) RETURN e.name\n```"
        resp1.content = [MagicMock(text=cypher_text)]
        resp1.usage = MagicMock(
            input_tokens=100,
            output_tokens=50,
            cache_creation_input_tokens=10,
            cache_read_input_tokens=5,
        )

        resp2 = MagicMock()
        resp2.content = [MagicMock(text="Summary text")]
        resp2.usage = MagicMock(
            input_tokens=200,
            output_tokens=80,
            cache_creation_input_tokens=0,
            cache_read_input_tokens=20,
        )

        querier._client.messages.create.side_effect = [resp1, resp2]

        mock_result = MagicMock()
        mock_result.get_column_names.return_value = ["e.name"]
        mock_result.has_next.side_effect = [True, False]
        mock_result.get_next.return_value = ["FastAPI"]
        mock_conn.execute.return_value = mock_result

        querier.ask("Test question")

        assert querier.usage.api_calls == 2
        assert querier.usage.input_tokens == 300
        assert querier.usage.output_tokens == 130
        assert querier.usage.cache_creation_input_tokens == 10
        assert querier.usage.cache_read_input_tokens == 25
