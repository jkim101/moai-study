"""Natural language query interface for the knowledge graph."""

from __future__ import annotations

import json
import logging
import re

import anthropic
import kuzu

from claude_conversation_kg.exceptions import QueryError
from claude_conversation_kg.extractor.models import UsageStats

logger = logging.getLogger(__name__)

# System prompt describing the graph schema for Cypher generation.
NLQ_SCHEMA_PROMPT = (
    "You are a Cypher query generator for a Kuzu graph database.\n\n"
    "Graph schema:\n"
    "Node tables:\n"
    "- Entity(id STRING PK, name STRING, type STRING, description STRING, "
    "confidence DOUBLE, first_seen TIMESTAMP, last_seen TIMESTAMP, "
    "mention_count INT64)\n"
    "  type values: Technology, Library, Concept, Pattern, File, Function, "
    "Problem, Solution, Decision, Tool\n"
    "- Session(id STRING PK, project_name STRING, file_path STRING)\n"
    "- ProcessedFile(file_path STRING PK, mtime DOUBLE, "
    "processed_at TIMESTAMP)\n\n"
    "Relationship tables (Entity -> Entity):\n"
    "- USES, DEPENDS_ON, SOLVES, RELATES_TO, DISCUSSED_IN, REPLACES, "
    "CONFLICTS_WITH\n"
    "  Properties: context STRING, confidence DOUBLE\n\n"
    "Relationship tables (Entity -> Session):\n"
    "- MENTIONED_IN\n\n"
    "Rules:\n"
    "- Generate ONLY a single Cypher query. No explanation.\n"
    "- Wrap the query in a ```cypher code fence.\n"
    "- Kuzu does not support the type() function on relationships. "
    "Query each relationship type separately if needed.\n"
    "- Use LIMIT to keep results manageable (default 20).\n"
    "- For timestamp filtering use: timestamp('YYYY-MM-DD HH:MM:SS').\n\n"
    "Examples:\n"
    "Q: What technologies are in the graph?\n"
    "```cypher\n"
    "MATCH (e:Entity) WHERE e.type = 'Technology' "
    "RETURN e.name, e.description, e.mention_count "
    "ORDER BY e.mention_count DESC LIMIT 20\n"
    "```\n\n"
    "Q: What libraries does FastAPI use?\n"
    "```cypher\n"
    "MATCH (a:Entity)-[:USES]->(b:Entity) "
    "WHERE a.name = 'FastAPI' AND b.type = 'Library' "
    "RETURN b.name, b.description LIMIT 20\n"
    "```\n"
)

SUMMARIZE_SYSTEM_PROMPT = (
    "You are a helpful assistant that summarizes database query results "
    "in natural language. Be concise and informative. "
    "Answer in the same language as the user's question."
)


class NaturalLanguageQuerier:
    """Convert natural language questions to Cypher queries and summarize results."""

    def __init__(
        self,
        api_key: str,
        conn: kuzu.Connection,
        model: str = "claude-haiku-4-5-20251001",
    ) -> None:
        self._client = anthropic.Anthropic(api_key=api_key)
        self._conn = conn
        self._model = model
        self.usage = UsageStats()

    def ask(self, question: str) -> tuple[str, str]:
        """Answer a natural language question about the knowledge graph.

        Returns:
            A tuple of (generated_cypher_query, natural_language_answer).

        Raises:
            QueryError: When the generated Cypher is invalid or execution fails.
        """
        # Step 1: Generate Cypher from the question.
        cypher = self._generate_cypher(question)

        # Step 2: Execute the Cypher query.
        try:
            result = self._conn.execute(cypher)
        except RuntimeError as e:
            raise QueryError(
                f"Generated Cypher query failed: {e}\nQuery: {cypher}"
            ) from e

        columns = result.get_column_names()
        rows: list[dict] = []
        while result.has_next():
            row = result.get_next()
            rows.append(dict(zip(columns, row)))

        # Step 3: Summarize results.
        if not rows:
            return cypher, "No results found for your query."

        summary = self._summarize(question, rows)
        return cypher, summary

    def _generate_cypher(self, question: str) -> str:
        """Send the question to Claude to generate a Cypher query."""
        response = self._client.messages.create(
            model=self._model,
            max_tokens=1024,
            system=[
                {
                    "type": "text",
                    "text": NLQ_SCHEMA_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": question}],
        )
        self.usage = self.usage + self._extract_usage(response)

        raw_text = response.content[0].text
        return self._parse_cypher(raw_text)

    def _summarize(self, question: str, rows: list[dict]) -> str:
        """Send query results to Claude for natural language summarization."""
        # Truncate results to avoid exceeding token limits.
        results_text = json.dumps(rows[:50], default=str, ensure_ascii=False)

        response = self._client.messages.create(
            model=self._model,
            max_tokens=1024,
            system=[
                {
                    "type": "text",
                    "text": SUMMARIZE_SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Question: {question}\n\n"
                        f"Query results ({len(rows)} rows):\n{results_text}\n\n"
                        "Summarize these results concisely."
                    ),
                }
            ],
        )
        self.usage = self.usage + self._extract_usage(response)
        return response.content[0].text

    @staticmethod
    def _parse_cypher(raw_text: str) -> str:
        """Extract a Cypher query from Claude's response text."""
        # Try to extract from ```cypher ... ``` fence first.
        match = re.search(r"```(?:cypher)?\s*([\s\S]*?)```", raw_text)
        if match:
            return match.group(1).strip()
        # Fallback: use the entire response stripped.
        return raw_text.strip()

    @staticmethod
    def _extract_usage(response: object) -> UsageStats:
        """Extract token usage from an Anthropic API response."""
        usage = getattr(response, "usage", None)
        if usage is None:
            return UsageStats(api_calls=1)
        return UsageStats(
            api_calls=1,
            input_tokens=getattr(usage, "input_tokens", 0),
            output_tokens=getattr(usage, "output_tokens", 0),
            cache_creation_input_tokens=getattr(
                usage, "cache_creation_input_tokens", 0
            )
            or 0,
            cache_read_input_tokens=getattr(
                usage, "cache_read_input_tokens", 0
            )
            or 0,
        )
