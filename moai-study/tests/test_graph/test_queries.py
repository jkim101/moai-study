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
        source_id=e1.id,
        target_id=e2.id,
        type=RelationshipType.USES,
        context="FastAPI uses SQLAlchemy",
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


class TestAuditQuery:
    """Tests for get_audit() -- frequency and time-range insights."""

    @pytest.fixture()
    def audit_runner(self, tmp_path: Path) -> QueryRunner:
        """QueryRunner with entities that have varied mention counts."""
        conn = KuzuConnection(tmp_path / "audit.db")
        initialize_schema(conn.conn)
        store = GraphStore(conn.conn)

        # Insert entities with varying mention_counts by calling upsert multiple times
        hot = Entity(name="FastAPI", type=EntityType.TECHNOLOGY)
        warm = Entity(name="SQLAlchemy", type=EntityType.LIBRARY)
        cold = Entity(name="OldLib", type=EntityType.LIBRARY)

        # hot: 5 mentions, warm: 2, cold: 1
        for _ in range(5):
            store.upsert_entity(hot)
        for _ in range(2):
            store.upsert_entity(warm)
        store.upsert_entity(cold)

        return QueryRunner(conn.conn)

    def test_get_audit_returns_top_entities(self, audit_runner: QueryRunner) -> None:
        """get_audit() returns top entities ordered by mention_count desc."""
        result = audit_runner.get_audit()
        top = result["top_entities"]
        assert len(top) >= 1
        # Most-mentioned entity is first
        assert top[0]["name"] == "FastAPI"
        assert top[0]["mention_count"] == 5

    def test_get_audit_respects_limit(self, audit_runner: QueryRunner) -> None:
        """get_audit(limit=1) returns at most 1 entity."""
        result = audit_runner.get_audit(limit=1)
        assert len(result["top_entities"]) == 1

    def test_get_audit_empty_graph(self, query_runner: QueryRunner) -> None:
        """get_audit() on empty graph returns empty lists without error."""
        result = query_runner.get_audit()
        assert result["top_entities"] == []
        assert result["total_entities"] == 0
