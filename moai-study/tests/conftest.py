"""Shared test fixtures."""
from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture()
def fixtures_dir() -> Path:
    """Return the path to the test fixtures directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture()
def sample_conversation_path(fixtures_dir: Path) -> Path:
    """Return the path to the sample conversation JSONL file."""
    return fixtures_dir / "sample_conversation.jsonl"
