"""Tests for JSONL reader -- RED phase."""

from __future__ import annotations

import json
from pathlib import Path

from claude_conversation_kg.parser.reader import discover_jsonl_files, read_jsonl_file


class TestDiscoverJsonlFiles:
    """Specification tests for JSONL file discovery."""

    def test_discover_jsonl_files(self, tmp_path: Path) -> None:
        """Given a directory with .jsonl files, returns all paths recursively."""
        sub = tmp_path / "sub"
        sub.mkdir()
        (tmp_path / "a.jsonl").write_text("{}\n")
        (sub / "b.jsonl").write_text("{}\n")
        (tmp_path / "c.txt").write_text("not jsonl\n")

        paths = list(discover_jsonl_files(tmp_path))
        names = {p.name for p in paths}
        assert names == {"a.jsonl", "b.jsonl"}

    def test_default_path_is_claude_projects(self) -> None:
        """Without argument, uses ~/.claude/projects/ as default."""
        # We just verify the function signature accepts no argument
        # and returns an iterator (even if empty on CI)
        result = discover_jsonl_files()
        assert hasattr(result, "__iter__")


class TestReadJsonlFile:
    """Specification tests for JSONL line-by-line reading."""

    def test_read_valid_jsonl(self, tmp_path: Path) -> None:
        """Reads valid JSONL and yields raw dicts."""
        data = [{"key": "value1"}, {"key": "value2"}]
        path = tmp_path / "test.jsonl"
        path.write_text("\n".join(json.dumps(d) for d in data) + "\n")

        result = list(read_jsonl_file(path))
        assert result == data

    def test_skip_malformed_lines(self, tmp_path: Path) -> None:
        """Logs warning and skips malformed lines, continues."""
        path = tmp_path / "test.jsonl"
        path.write_text('{"valid": true}\nnot json\n{"also": "valid"}\n')

        result = list(read_jsonl_file(path))

        assert len(result) == 2
        assert result[0] == {"valid": True}
        assert result[1] == {"also": "valid"}

    def test_empty_file(self, tmp_path: Path) -> None:
        """Empty file yields no results."""
        path = tmp_path / "empty.jsonl"
        path.write_text("")
        result = list(read_jsonl_file(path))
        assert result == []
