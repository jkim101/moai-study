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

    Invalid messages are logged and skipped.
    """
    messages: list[ConversationMessage] = []
    for raw in raw_messages:
        try:
            msg = ConversationMessage.model_validate(raw)
            messages.append(msg)
        except ValidationError as e:
            logger.warning("Skipping invalid message in %s: %s", file_path, e)
    return ConversationSession(file_path=file_path, messages=messages)
