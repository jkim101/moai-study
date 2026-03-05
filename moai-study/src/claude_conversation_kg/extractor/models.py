"""Pydantic models for extraction results."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum

from pydantic import BaseModel, Field, model_validator


class EntityType(StrEnum):
    """Types of entities that can be extracted from conversations."""

    TECHNOLOGY = "Technology"
    LIBRARY = "Library"
    PATTERN = "Pattern"
    DECISION = "Decision"
    PROBLEM = "Problem"
    SOLUTION = "Solution"
    FILE = "File"
    FUNCTION = "Function"
    CONCEPT = "Concept"


class RelationshipType(StrEnum):
    """Types of relationships between entities."""

    USES = "USES"
    DEPENDS_ON = "DEPENDS_ON"
    SOLVES = "SOLVES"
    RELATES_TO = "RELATES_TO"
    DISCUSSED_IN = "DISCUSSED_IN"
    REPLACES = "REPLACES"
    CONFLICTS_WITH = "CONFLICTS_WITH"


def _slugify(text: str) -> str:
    """Convert text to a URL-friendly slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    return re.sub(r"[-\s]+", "-", text)


def _canonical_id_part(name: str) -> str:
    """Generate a canonical ID fragment by removing all separators.

    Collapses spaces, hyphens, and underscores so that variants like
    'FastAPI', 'fast api', and 'fast-api' all produce the same key.
    """
    text = name.lower().strip()
    text = re.sub(r"[^\w]", "", text)  # keep only alphanumerics
    return text or "unknown"


def _normalize_name(name: str) -> str:
    """Normalize an entity name for display.

    Strips leading/trailing whitespace and collapses internal runs of
    whitespace to a single space.
    """
    return re.sub(r"\s+", " ", name.strip())


class Entity(BaseModel):
    """An entity extracted from a conversation."""

    id: str = ""
    name: str
    type: EntityType
    description: str = ""
    confidence: float = 1.0

    @model_validator(mode="after")
    def _normalize_and_generate_id(self) -> Entity:
        """Normalize name and auto-generate id from canonical name + type."""
        self.name = _normalize_name(self.name)
        if not self.id:
            self.id = f"{_canonical_id_part(self.name)}-{_slugify(self.type.value)}"
        return self


class Relationship(BaseModel):
    """A relationship between two entities."""

    source_id: str
    target_id: str
    type: RelationshipType
    context: str = ""
    confidence: float = 0.8


class ExtractionResult(BaseModel):
    """Aggregated extraction output from a conversation batch."""

    entities: list[Entity] = Field(default_factory=list)
    relationships: list[Relationship] = Field(default_factory=list)


@dataclass
class UsageStats:
    """Accumulated token usage statistics from Anthropic API calls."""

    api_calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0

    def __add__(self, other: UsageStats) -> UsageStats:
        """Combine two UsageStats instances."""
        return UsageStats(
            api_calls=self.api_calls + other.api_calls,
            input_tokens=self.input_tokens + other.input_tokens,
            output_tokens=self.output_tokens + other.output_tokens,
            cache_creation_input_tokens=(
                self.cache_creation_input_tokens + other.cache_creation_input_tokens
            ),
            cache_read_input_tokens=(
                self.cache_read_input_tokens + other.cache_read_input_tokens
            ),
        )

    @property
    def estimated_cost_usd(self) -> float:
        """Estimate cost in USD based on Claude Haiku pricing.

        Pricing (per 1M tokens): input=$0.80, output=$4.00,
        cache_write=$1.00, cache_read=$0.08
        """
        cost = (
            (self.input_tokens * 0.80 / 1_000_000)
            + (self.output_tokens * 4.00 / 1_000_000)
            + (self.cache_creation_input_tokens * 1.00 / 1_000_000)
            + (self.cache_read_input_tokens * 0.08 / 1_000_000)
        )
        return round(cost, 6)
