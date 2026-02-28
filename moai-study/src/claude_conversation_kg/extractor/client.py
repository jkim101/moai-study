"""Anthropic API client with retry logic."""
from __future__ import annotations

import json
import logging
import time

import anthropic

from claude_conversation_kg.exceptions import AuthenticationError, ExtractionError
from claude_conversation_kg.extractor.models import (
    Entity,
    EntityType,
    ExtractionResult,
    Relationship,
    RelationshipType,
)
from claude_conversation_kg.extractor.prompts import SYSTEM_PROMPT, build_user_prompt
from claude_conversation_kg.parser.models import ConversationMessage

logger = logging.getLogger(__name__)


class ExtractionClient:
    """Client for extracting entities and relationships via Claude API."""

    def __init__(
        self, api_key: str, model: str = "claude-haiku-4-5-20251001"
    ) -> None:
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

    def extract(
        self,
        messages: list[ConversationMessage],
        max_retries: int = 3,
    ) -> ExtractionResult:
        """Extract entities and relationships from conversation messages.

        Implements exponential backoff for rate limit errors.
        Halts immediately on authentication errors.
        """
        user_prompt = build_user_prompt(messages)

        for attempt in range(max_retries + 1):
            try:
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=4096,
                    system=SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": user_prompt}],
                )
                raw_text = response.content[0].text
                return self._parse_response(raw_text)

            except anthropic.AuthenticationError as e:
                raise AuthenticationError(
                    f"Invalid API key. Please check your ANTHROPIC_API_KEY: {e}"
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

    def _parse_response(self, raw_text: str) -> ExtractionResult:
        """Parse the JSON response into an ExtractionResult."""
        text = raw_text.strip()
        # Strip markdown code fences if present (e.g. ```json ... ```)
        if text.startswith("```"):
            text = text.split("\n", 1)[-1]
            if text.endswith("```"):
                text = text.rsplit("```", 1)[0]
            text = text.strip()
        try:
            data = json.loads(text)
        except json.JSONDecodeError as e:
            raise ExtractionError(f"Failed to parse API response as JSON: {e}") from e

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
