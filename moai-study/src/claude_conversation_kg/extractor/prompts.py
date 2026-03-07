"""Extraction prompt templates."""

from __future__ import annotations

from claude_conversation_kg.parser.models import ConversationMessage

SYSTEM_PROMPT = (
    "You are a knowledge graph extraction assistant. "
    "Analyze the given conversation messages and extract "
    "entities and relationships.\n\n"
    "VALID entity types (use ONLY these exact values):\n"
    '- "Technology" (programming languages, frameworks, databases, tools)\n'
    '- "Library" (packages, modules, dependencies)\n'
    '- "Pattern" (design patterns, architectural patterns)\n'
    '- "Decision" (choices made during development)\n'
    '- "Problem" (bugs, issues, errors encountered)\n'
    '- "Solution" (fixes, workarounds, resolutions)\n'
    '- "File" (source files, config files)\n'
    '- "Function" (functions, methods, classes)\n'
    '- "Concept" (abstract ideas, methodologies)\n\n'
    "VALID relationship types (use ONLY these exact values):\n"
    '- "USES" (entity A uses entity B)\n'
    '- "DEPENDS_ON" (entity A depends on entity B)\n'
    '- "SOLVES" (entity A solves entity B)\n'
    '- "RELATES_TO" (general relationship)\n'
    '- "DISCUSSED_IN" (entity A is discussed in entity B)\n'
    '- "REPLACES" (entity A replaces entity B)\n'
    '- "CONFLICTS_WITH" (entity A conflicts with entity B)\n\n'
    "Do NOT invent new types. "
    'If an entity does not fit any type, use "Concept". '
    'If a relationship does not fit any type, use "RELATES_TO".\n\n'
    "Return ONLY valid JSON with this structure:\n"
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
    "- Use the EXACT type values listed above. No other values.\n"
    "- Include a brief description for each entity.\n"
    "- Assign confidence scores between 0.0 and 1.0.\n"
    "- Do NOT include explanatory text outside the JSON.\n"
)


def build_user_prompt(messages: list[ConversationMessage]) -> str:
    """Format conversation messages into a user prompt.

    Each message is formatted as 'role: content' on its own line.
    """
    lines: list[str] = [
        "Extract entities and relationships from this conversation:\n",
    ]
    for msg in messages:
        content = (
            msg.content if isinstance(msg.content, str) else str(msg.content)
        )
        lines.append(f"{msg.role}: {content}")
    return "\n".join(lines)
