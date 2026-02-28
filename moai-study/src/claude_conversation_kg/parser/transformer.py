"""Transform raw dicts into ConversationSession models."""
from __future__ import annotations

import logging
from collections.abc import Iterator
from pathlib import Path

from pydantic import ValidationError

from claude_conversation_kg.parser.models import (
    ConversationMessage,
    ConversationSession,
)

logger = logging.getLogger(__name__)


def transform(file_path: Path, raw_messages: Iterator[dict]) -> ConversationSession:
    """Convert an iterator of raw dicts into a ConversationSession.

    Handles Claude Code's nested JSONL format where role/content are inside
    a 'message' sub-object. Only processes 'user' and 'assistant' type entries.
    Invalid messages are logged and skipped.
    """
    messages: list[ConversationMessage] = []
    for raw in raw_messages:
        msg_type = raw.get("type")

        # Claude Code format: role/content are nested under 'message'
        if msg_type in ("user", "assistant") and "message" in raw:
            inner = raw["message"]
            flat = {
                "type": msg_type,
                "role": inner.get("role", msg_type),
                "content": inner.get("content", ""),
                "timestamp": raw.get("timestamp"),
            }
        else:
            # Skip internal types (progress, file-history-snapshot, system, etc.)
            continue

        try:
            msg = ConversationMessage.model_validate(flat)
            messages.append(msg)
        except ValidationError as e:
            logger.warning("Skipping invalid message in %s: %s", file_path, e)
    return ConversationSession(file_path=file_path, messages=messages)
