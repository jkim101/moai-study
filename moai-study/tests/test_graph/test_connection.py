"""Tests for Kuzu connection -- RED phase."""
from __future__ import annotations

from pathlib import Path

import pytest

kuzu = pytest.importorskip("kuzu")

from claude_conversation_kg.graph.connection import KuzuConnection


class TestKuzuConnection:
    """Specification tests for KuzuConnection."""

    def test_connection_creates_directory(self, tmp_path: Path) -> None:
        """Creates db directory if it does not exist."""
        db_path = tmp_path / "subdir" / "graph.db"
        conn = KuzuConnection(db_path)
        assert db_path.parent.exists()
        assert conn.conn is not None

    def test_connection_is_reusable(self, tmp_path: Path) -> None:
        """Second connection to same path works."""
        db_path = tmp_path / "graph.db"
        conn1 = KuzuConnection(db_path)
        del conn1
        conn2 = KuzuConnection(db_path)
        assert conn2.conn is not None

    def test_context_manager(self, tmp_path: Path) -> None:
        """with KuzuConnection(path) as conn: pattern works."""
        db_path = tmp_path / "graph.db"
        with KuzuConnection(db_path) as conn:
            assert conn.conn is not None
