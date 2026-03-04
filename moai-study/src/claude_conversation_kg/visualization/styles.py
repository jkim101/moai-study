"""Visual style definitions for graph rendering."""

from __future__ import annotations

from claude_conversation_kg.extractor.models import EntityType

ENTITY_COLORS: dict[str, str] = {
    EntityType.TECHNOLOGY.value: "#4A90D9",
    EntityType.LIBRARY.value: "#7ED321",
    EntityType.PATTERN.value: "#F5A623",
    EntityType.DECISION.value: "#BD10E0",
    EntityType.PROBLEM.value: "#D0021B",
    EntityType.SOLUTION.value: "#417505",
    EntityType.FILE.value: "#9B9B9B",
    EntityType.FUNCTION.value: "#50E3C2",
    EntityType.CONCEPT.value: "#B8E986",
}

DEFAULT_COLOR = "#CCCCCC"
