"""Tests for graph schema -- RED phase."""
from __future__ import annotations

from pathlib import Path

import pytest

kuzu = pytest.importorskip("kuzu")

from claude_conversation_kg.graph.connection import KuzuConnection
from claude_conversation_kg.graph.schema import initialize_schema


@pytest.fixture()
def db_conn(tmp_path: Path) -> KuzuConnection:
    """Create a temporary KuzuConnection."""
    return KuzuConnection(tmp_path / "test.db")


class TestSchema:
    """Specification tests for graph schema initialization."""

    def test_schema_creates_entity_table(self, db_conn: KuzuConnection) -> None:
        """Entity node table exists after init."""
        initialize_schema(db_conn.conn)
        result = db_conn.conn.execute("MATCH (n:Entity) RETURN count(n)")
        assert result.get_next() == [0]

    def test_schema_creates_relationship_tables(self, db_conn: KuzuConnection) -> None:
        """All 7 relationship tables exist after init."""
        initialize_schema(db_conn.conn)
        rel_types = [
            "USES", "DEPENDS_ON", "SOLVES", "RELATES_TO",
            "DISCUSSED_IN", "REPLACES", "CONFLICTS_WITH",
        ]
        for rel_type in rel_types:
            # Insert two test entities
            src_q = (
                "CREATE (e:Entity {"
                f"id: 'src_{rel_type}', name: 'src', "
                "type: 'Technology', description: '', "
                "confidence: 1.0})"
            )
            tgt_q = (
                "CREATE (e:Entity {"
                f"id: 'tgt_{rel_type}', name: 'tgt', "
                "type: 'Technology', description: '', "
                "confidence: 1.0})"
            )
            db_conn.conn.execute(src_q)
            db_conn.conn.execute(tgt_q)
            # Verify the rel table exists by matching (even if empty)
            query = f"MATCH (a:Entity)-[r:{rel_type}]->(b:Entity) RETURN count(r)"
            result = db_conn.conn.execute(query)
            assert result.get_next() == [0]

    def test_schema_idempotent(self, db_conn: KuzuConnection) -> None:
        """Calling init twice does not raise an error."""
        initialize_schema(db_conn.conn)
        initialize_schema(db_conn.conn)  # Should not raise
