"""Entity and relationship storage operations."""
from __future__ import annotations

import logging
from pathlib import Path

import kuzu

from claude_conversation_kg.extractor.models import Entity, Relationship

logger = logging.getLogger(__name__)


class GraphStore:
    """Repository for persisting entities and relationships in Kuzu."""

    def __init__(self, conn: kuzu.Connection) -> None:
        self._conn = conn

    def upsert_entity(self, entity: Entity) -> None:
        """Insert or update an entity by its id."""
        self._conn.execute(
            """
            MERGE (e:Entity {id: $id})
            SET e.name = $name, e.type = $type,
                e.description = $description, e.confidence = $confidence
            """,
            parameters={
                "id": entity.id,
                "name": entity.name,
                "type": entity.type.value,
                "description": entity.description,
                "confidence": entity.confidence,
            },
        )

    def upsert_relationship(self, rel: Relationship) -> None:
        """Insert a relationship between two entities."""
        query = f"""
            MATCH (a:Entity {{id: $src}}), (b:Entity {{id: $tgt}})
            CREATE (a)-[r:{rel.type.value} {{context: $ctx, confidence: $conf}}]->(b)
        """
        self._conn.execute(
            query,
            parameters={
                "src": rel.source_id,
                "tgt": rel.target_id,
                "ctx": rel.context,
                "conf": rel.confidence,
            },
        )

    def is_file_processed(self, file_path: Path, mtime: float) -> bool:
        """Check if a file has already been processed with the given mtime."""
        result = self._conn.execute(
            "MATCH (f:ProcessedFile {file_path: $fp}) RETURN f.mtime",
            parameters={"fp": str(file_path)},
        )
        if result.has_next():
            row = result.get_next()
            return row[0] == mtime
        return False

    def mark_file_processed(self, file_path: Path, mtime: float) -> None:
        """Record that a file has been processed."""
        self._conn.execute(
            """
            MERGE (f:ProcessedFile {file_path: $fp})
            SET f.mtime = $mtime
            """,
            parameters={"fp": str(file_path), "mtime": mtime},
        )
