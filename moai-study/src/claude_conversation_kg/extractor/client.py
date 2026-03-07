"""Anthropic API client with retry logic."""

from __future__ import annotations

import json
import logging
import time

import anthropic

from claude_conversation_kg.exceptions import (
    AuthenticationError,
    ExtractionError,
    PromptTooLargeError,
)
from claude_conversation_kg.extractor.models import (
    Entity,
    EntityType,
    ExtractionResult,
    Relationship,
    RelationshipType,
    UsageStats,
)
from claude_conversation_kg.extractor.prompts import SYSTEM_PROMPT, build_user_prompt
from claude_conversation_kg.parser.models import ConversationMessage

logger = logging.getLogger(__name__)


class ExtractionClient:
    """Client for extracting entities and relationships via Claude API."""

    def __init__(self, api_key: str, model: str = "claude-haiku-4-5-20251001") -> None:
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

    # Rough chars-per-token ratio; conservative to avoid 400 errors.
    _CHARS_PER_TOKEN = 4
    _MAX_PROMPT_TOKENS = 180_000

    @classmethod
    def estimate_tokens(cls, text: str) -> int:
        """Estimate token count from character length."""
        return len(text) // cls._CHARS_PER_TOKEN

    def extract(
        self,
        messages: list[ConversationMessage],
        max_retries: int = 3,
    ) -> tuple[ExtractionResult, UsageStats]:
        """Extract entities and relationships from conversation messages.

        Implements exponential backoff for rate limit errors.
        Halts immediately on authentication errors.
        Raises PromptTooLargeError if estimated tokens exceed the limit.
        Returns a tuple of (ExtractionResult, UsageStats).
        """
        user_prompt = build_user_prompt(messages)
        estimated = self.estimate_tokens(SYSTEM_PROMPT + user_prompt)
        if estimated > self._MAX_PROMPT_TOKENS:
            raise PromptTooLargeError(
                f"Estimated {estimated:,} tokens exceeds "
                f"{self._MAX_PROMPT_TOKENS:,} limit "
                f"({len(messages)} messages)"
            )

        for attempt in range(max_retries + 1):
            try:
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=4096,
                    system=[
                        {
                            "type": "text",
                            "text": SYSTEM_PROMPT,
                            "cache_control": {"type": "ephemeral"},
                        }
                    ],
                    messages=[{"role": "user", "content": user_prompt}],
                )
                raw_text = response.content[0].text
                usage = self._extract_usage(response)
                return self._parse_response(raw_text), usage

            except anthropic.AuthenticationError as e:
                raise AuthenticationError(
                    f"Invalid API key. Please check your ANTHROPIC_API_KEY: {e}"
                ) from e

            except anthropic.BadRequestError as e:
                raise ExtractionError(
                    f"Bad request (not retryable): {e}"
                ) from e

            except anthropic.RateLimitError:
                if attempt >= max_retries - 1:
                    raise ExtractionError(
                        f"Rate limit exceeded after {max_retries} retries"
                    )
                wait_time = 2 ** (attempt + 1)
                logger.warning(
                    "Rate limited, retrying in %d seconds (attempt %d/%d)",
                    wait_time,
                    attempt + 1,
                    max_retries,
                )
                time.sleep(wait_time)

            except anthropic.APIError as e:
                if attempt >= max_retries - 1:
                    raise ExtractionError(
                        f"API error after {max_retries} retries: {e}"
                    ) from e
                wait_time = 2 ** (attempt + 1)
                time.sleep(wait_time)

        raise ExtractionError("Extraction failed: unexpected state")

    @staticmethod
    def _extract_usage(response: object) -> UsageStats:
        """Extract token usage statistics from an Anthropic API response."""
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
            cache_read_input_tokens=getattr(usage, "cache_read_input_tokens", 0) or 0,
        )

    def _extract_json_blocks(self, text: str) -> list[dict]:
        """Extract all JSON objects from text.

        Handles markdown code fences and multiple consecutive JSON objects.
        Returns a list of parsed dicts (may be empty on total failure).
        """
        import re

        blocks: list[dict] = []

        # Extract content from all ```json ... ``` or ``` ... ``` fences
        fenced = re.findall(r"```(?:json)?\s*([\s\S]*?)```", text)
        if fenced:
            for block in fenced:
                try:
                    blocks.append(json.loads(block.strip()))
                except json.JSONDecodeError:
                    pass
            if blocks:
                return blocks

        # No fences found — try streaming JSON decoder to handle multiple objects
        decoder = json.JSONDecoder()
        pos = 0
        while pos < len(text):
            try:
                obj, pos = decoder.raw_decode(text, pos)
                if isinstance(obj, dict):
                    blocks.append(obj)
            except json.JSONDecodeError:
                pos += 1

        return blocks

    def _parse_response(self, raw_text: str) -> ExtractionResult:
        """Parse the JSON response into an ExtractionResult.

        Handles single JSON objects, multiple JSON blocks, and markdown fences.
        """
        blocks = self._extract_json_blocks(raw_text.strip())
        if not blocks:
            raise ExtractionError(
                "No valid JSON found in API response. "
                f"Raw text (first 200 chars): {raw_text[:200]!r}"
            )

        # Merge entities and relationships from all blocks
        merged_entities: list = []
        merged_relationships: list = []
        for block in blocks:
            merged_entities.extend(block.get("entities", []))
            merged_relationships.extend(block.get("relationships", []))
        data = {"entities": merged_entities, "relationships": merged_relationships}

        entities: list[Entity] = []
        for raw_entity in data.get("entities", []):
            try:
                entity_type = EntityType(raw_entity["type"])
                entities.append(
                    Entity(
                        name=raw_entity["name"],
                        type=entity_type,
                        description=raw_entity.get("description", ""),
                    )
                )
            except (KeyError, ValueError) as e:
                logger.warning("Skipping invalid entity: %s", e)

        relationships: list[Relationship] = []
        for raw_rel in data.get("relationships", []):
            try:
                rel_type = RelationshipType(raw_rel["type"])
                # Map source/target names to entity IDs
                source_name = raw_rel["source"]
                target_name = raw_rel["target"]
                source_entity = next(
                    (e for e in entities if e.name == source_name), None
                )
                target_entity = next(
                    (e for e in entities if e.name == target_name), None
                )
                if source_entity and target_entity:
                    relationships.append(
                        Relationship(
                            source_id=source_entity.id,
                            target_id=target_entity.id,
                            type=rel_type,
                            context=raw_rel.get("context", ""),
                            confidence=raw_rel.get("confidence", 0.8),
                        )
                    )
            except (KeyError, ValueError) as e:
                logger.warning("Skipping invalid relationship: %s", e)

        return ExtractionResult(entities=entities, relationships=relationships)
