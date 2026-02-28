"""Pydantic models for parsed conversation data."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field


class ConversationMessage(BaseModel):
    """A single message from a Claude conversation JSONL file."""

    type: str = "message"
    role: Literal["user", "assistant", "system"]
    content: str | list[Any] = ""
    timestamp: datetime | None = None


class ConversationSession(BaseModel):
    """A collection of messages from a single conversation file."""

    file_path: Path
    messages: list[ConversationMessage] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
