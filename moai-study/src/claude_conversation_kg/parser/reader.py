"""JSONL file discovery and reading."""
from __future__ import annotations

import json
import logging
from collections.abc import Iterator
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_CLAUDE_PROJECTS_PATH = Path.home() / ".claude" / "projects"


def discover_jsonl_files(path: Path | None = None) -> Iterator[Path]:
    """Discover all .jsonl files under the given path recursively.

    If no path is provided, defaults to ~/.claude/projects/.
    """
    search_path = path if path is not None else DEFAULT_CLAUDE_PROJECTS_PATH
    if not search_path.exists():
        return
    yield from sorted(search_path.rglob("*.jsonl"))


def read_jsonl_file(path: Path) -> Iterator[dict]:
    """Read a JSONL file and yield parsed JSON dicts per line.

    Malformed lines are logged as warnings and skipped.
    """
    with open(path, encoding="utf-8") as f:
        for line_num, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as e:
                logger.warning(
                    "Skipping malformed line %d in %s: %s", line_num, path, e
                )
