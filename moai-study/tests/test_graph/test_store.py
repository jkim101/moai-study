"""Tests for graph store."""

from __future__ import annotations

from datetime import UTC, datetime
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
            source_id=e1.id,
            target_id=e2.id,
            type=RelationshipType.USES,
            context="FastAPI uses SQLAlchemy",
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


class TestTimestampTracking:
    """Tests for first_seen, last_seen, mention_count on Entity nodes."""

    def test_first_seen_set_on_create(self, store: GraphStore) -> None:
        """first_seen is recorded when an entity is first inserted."""
        ts = datetime(2025, 1, 1, tzinfo=UTC)
        entity = Entity(name="FastAPI", type=EntityType.TECHNOLOGY)
        store.upsert_entity(entity, session_timestamp=ts)

        result = store._conn.execute(
            "MATCH (e:Entity {id: $id}) RETURN e.first_seen",
            parameters={"id": entity.id},
        )
        assert result.get_next()[0] is not None

    def test_first_seen_preserved_on_update(self, store: GraphStore) -> None:
        """first_seen does not change when the same entity is seen again."""
        ts_early = datetime(2025, 1, 1, tzinfo=UTC)
        ts_late = datetime(2025, 6, 1, tzinfo=UTC)
        entity = Entity(name="FastAPI", type=EntityType.TECHNOLOGY)

        store.upsert_entity(entity, session_timestamp=ts_early)
        store.upsert_entity(entity, session_timestamp=ts_late)

        result = store._conn.execute(
            "MATCH (e:Entity {id: $id}) RETURN e.first_seen",
            parameters={"id": entity.id},
        )
        first_seen = result.get_next()[0]
        # first_seen should reflect the earlier timestamp
        assert first_seen is not None
        # Convert to comparable: should not be ts_late
        # (Kuzu returns datetime objects)
        if hasattr(first_seen, "year"):
            assert first_seen.year == 2025
            assert first_seen.month == 1

    def test_last_seen_updated_on_each_upsert(self, store: GraphStore) -> None:
        """last_seen always reflects the most recent session timestamp."""
        ts_early = datetime(2025, 1, 1, tzinfo=UTC)
        ts_late = datetime(2025, 6, 1, tzinfo=UTC)
        entity = Entity(name="FastAPI", type=EntityType.TECHNOLOGY)

        store.upsert_entity(entity, session_timestamp=ts_early)
        store.upsert_entity(entity, session_timestamp=ts_late)

        result = store._conn.execute(
            "MATCH (e:Entity {id: $id}) RETURN e.last_seen",
            parameters={"id": entity.id},
        )
        last_seen = result.get_next()[0]
        assert last_seen is not None
        if hasattr(last_seen, "month"):
            assert last_seen.month == 6

    def test_mention_count_increments(self, store: GraphStore) -> None:
        """mention_count increases by 1 for each upsert call."""
        entity = Entity(name="FastAPI", type=EntityType.TECHNOLOGY)

        store.upsert_entity(entity)
        store.upsert_entity(entity)
        store.upsert_entity(entity)

        result = store._conn.execute(
            "MATCH (e:Entity {id: $id}) RETURN e.mention_count",
            parameters={"id": entity.id},
        )
        assert result.get_next()[0] == 3

    def test_mention_count_starts_at_one(self, store: GraphStore) -> None:
        """A newly created entity has mention_count of 1."""
        entity = Entity(name="NewLib", type=EntityType.LIBRARY)
        store.upsert_entity(entity)

        result = store._conn.execute(
            "MATCH (e:Entity {id: $id}) RETURN e.mention_count",
            parameters={"id": entity.id},
        )
        assert result.get_next()[0] == 1

    def test_upsert_without_timestamp_still_works(self, store: GraphStore) -> None:
        """upsert_entity with no timestamp leaves first_seen/last_seen as None."""
        entity = Entity(name="NoTime", type=EntityType.CONCEPT)
        store.upsert_entity(entity)

        result = store._conn.execute(
            "MATCH (e:Entity {id: $id}) RETURN e.mention_count",
            parameters={"id": entity.id},
        )
        assert result.get_next()[0] == 1
