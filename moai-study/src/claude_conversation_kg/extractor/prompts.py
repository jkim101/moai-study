"""Extraction prompt templates."""
from __future__ import annotations

from claude_conversation_kg.extractor.models import (
    EntityType,
    RelationshipType,
)
from claude_conversation_kg.parser.models import ConversationMessage

_entity_types = ", ".join(e.value for e in EntityType)
_relationship_types = ", ".join(r.value for r in RelationshipType)

SYSTEM_PROMPT = (
    "You are a knowledge graph extraction assistant. "
    "Analyze the given conversation messages and extract "
    "entities and relationships.\n\n"
    f"Entity types: {_entity_types}\n"
    f"Relationship types: {_relationship_types}\n\n"
    "Return your response as a JSON object with this structure:\n"
    "{\n"
    '  "entities": [\n'
    '    {"name": "string", "type": "EntityType", '
    '"description": "string"}\n'
    "  ],\n"
    '  "relationships": [\n'
    '    {"source": "entity name", "target": "entity name", '
    '"type": "RelationshipType", "context": "string", '
    '"confidence": 0.8}\n'
    "  ]\n"
    "}\n\n"
    "Rules:\n"
    "- Extract only clearly mentioned entities.\n"
    "- Use the exact entity type values listed above.\n"
    "- Use the exact relationship type values listed above.\n"
    "- Include a brief description for each entity.\n"
    "- Assign confidence scores between 0.0 and 1.0.\n"
)


def build_user_prompt(messages: list[ConversationMessage]) -> str:
    """Format conversation messages into a user prompt.

    Each message is formatted as 'role: content' on its own line.
    """
    lines: list[str] = [
        "Extract entities and relationships from "
        "this conversation:\n"
    ]
    for msg in messages:
        content = (
            msg.content
            if isinstance(msg.content, str)
            else str(msg.content)
        )
        lines.append(f"{msg.role}: {content}")
    return "\n".join(lines)
