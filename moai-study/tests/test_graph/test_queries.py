"""Tests for graph queries -- RED phase."""
from __future__ import annotations

from pathlib import Path

import pytest

kuzu = pytest.importorskip("kuzu")

from claude_conversation_kg.exceptions import QueryError
from claude_conversation_kg.extractor.models import (
    Entity,
    EntityType,
    Relationship,
    RelationshipType,
)
from claude_conversation_kg.graph.connection import KuzuConnection
from claude_conversation_kg.graph.queries import QueryRunner
from claude_conversation_kg.graph.schema import initialize_schema
from claude_conversation_kg.graph.store import GraphStore


@pytest.fixture()
def query_runner(tmp_path: Path) -> QueryRunner:
    """Create a QueryRunner with initialized schema."""
    conn = KuzuConnection(tmp_path / "test.db")
    initialize_schema(conn.conn)
    return QueryRunner(conn.conn)


@pytest.fixture()
def populated_runner(tmp_path: Path) -> QueryRunner:
    """Create a QueryRunner with pre-populated data."""
    conn = KuzuConnection(tmp_path / "test.db")
    initialize_schema(conn.conn)
    store = GraphStore(conn.conn)

    e1 = Entity(name="FastAPI", type=EntityType.TECHNOLOGY, description="Web framework")
    e2 = Entity(name="SQLAlchemy", type=EntityType.LIBRARY, description="ORM")
    store.upsert_entity(e1)
    store.upsert_entity(e2)

    rel = Relationship(
        source_id=e1.id, target_id=e2.id,
        type=RelationshipType.USES, context="FastAPI uses SQLAlchemy",
    )
    store.upsert_relationship(rel)

    return QueryRunner(conn.conn)


class TestQueryRunner:
    """Specification tests for QueryRunner."""

    def test_get_stats_empty_graph(self, query_runner: QueryRunner) -> None:
        """Stats on empty graph returns zeros."""
        stats = query_runner.get_stats()
        assert stats["total_entities"] == 0
        assert stats["total_relationships"] == 0

    def test_get_stats_with_data(self, populated_runner: QueryRunner) -> None:
        """Entity and relationship counts are correct."""
        stats = populated_runner.get_stats()
        assert stats["total_entities"] == 2
        assert stats["total_relationships"] >= 1

    def test_execute_cypher(self, populated_runner: QueryRunner) -> None:
        """Arbitrary Cypher query returns results."""
        results = populated_runner.execute(
            "MATCH (n:Entity) RETURN n.name ORDER BY n.name"
        )
        names = [r["n.name"] for r in results]
        assert "FastAPI" in names
        assert "SQLAlchemy" in names

    def test_execute_invalid_cypher(self, query_runner: QueryRunner) -> None:
        """Invalid Cypher raises QueryError."""
        with pytest.raises(QueryError):
            query_runner.execute("THIS IS NOT VALID CYPHER")
