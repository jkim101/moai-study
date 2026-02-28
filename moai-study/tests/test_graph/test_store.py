"""Tests for graph store -- RED phase."""
from __future__ import annotations

from pathlib import Path

import pytest

kuzu = pytest.importorskip("kuzu")

from claude_conversation_kg.extractor.models import (
    Entity,
    EntityType,
    Relationship,
    RelationshipType,
)
from claude_conversation_kg.graph.connection import KuzuConnection
from claude_conversation_kg.graph.schema import initialize_schema
from claude_conversation_kg.graph.store import GraphStore


@pytest.fixture()
def store(tmp_path: Path) -> GraphStore:
    """Create a GraphStore with initialized schema."""
    conn = KuzuConnection(tmp_path / "test.db")
    initialize_schema(conn.conn)
    return GraphStore(conn.conn)


class TestGraphStore:
    """Specification tests for GraphStore."""

    def test_insert_entity(self, store: GraphStore) -> None:
        """Entity is stored and retrievable."""
        entity = Entity(
            name="FastAPI",
            type=EntityType.TECHNOLOGY,
            description="Framework",
        )
        store.upsert_entity(entity)

        result = store._conn.execute(
            "MATCH (e:Entity {id: $id}) RETURN e.name",
            parameters={"id": entity.id},
        )
        assert result.get_next() == ["FastAPI"]

    def test_upsert_entity(self, store: GraphStore) -> None:
        """Duplicate ID updates the entity, does not duplicate."""
        entity = Entity(name="FastAPI", type=EntityType.TECHNOLOGY, description="v1")
        store.upsert_entity(entity)

        entity_v2 = Entity(name="FastAPI", type=EntityType.TECHNOLOGY, description="v2")
        store.upsert_entity(entity_v2)

        result = store._conn.execute("MATCH (e:Entity) RETURN count(e)")
        assert result.get_next() == [1]

        result = store._conn.execute(
            "MATCH (e:Entity {id: $id}) RETURN e.description",
            parameters={"id": entity.id},
        )
        assert result.get_next() == ["v2"]

    def test_insert_relationship(self, store: GraphStore) -> None:
        """Relationship is stored between two entities."""
        e1 = Entity(name="FastAPI", type=EntityType.TECHNOLOGY)
        e2 = Entity(name="SQLAlchemy", type=EntityType.LIBRARY)
        store.upsert_entity(e1)
        store.upsert_entity(e2)

        rel = Relationship(
            source_id=e1.id, target_id=e2.id,
            type=RelationshipType.USES, context="FastAPI uses SQLAlchemy",
        )
        store.upsert_relationship(rel)

        result = store._conn.execute(
            "MATCH (a:Entity)-[r:USES]->(b:Entity) RETURN a.name, b.name"
        )
        assert result.get_next() == ["FastAPI", "SQLAlchemy"]

    def test_incremental_tracking(self, store: GraphStore) -> None:
        """Processed files table tracks path and mtime."""
        store.mark_file_processed(Path("/tmp/test.jsonl"), 1234567890.0)
        assert store.is_file_processed(Path("/tmp/test.jsonl"), 1234567890.0)

    def test_skip_already_processed(self, store: GraphStore) -> None:
        """File with same path and mtime is considered processed."""
        store.mark_file_processed(Path("/tmp/test.jsonl"), 100.0)
        assert store.is_file_processed(Path("/tmp/test.jsonl"), 100.0)
        # Modified file should NOT be considered processed
        assert not store.is_file_processed(Path("/tmp/test.jsonl"), 200.0)
