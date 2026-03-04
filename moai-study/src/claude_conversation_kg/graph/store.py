"""Entity and relationship storage operations."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

import kuzu

from claude_conversation_kg.extractor.models import Entity, Relationship

logger = logging.getLogger(__name__)


class GraphStore:
    """Repository for persisting entities and relationships in Kuzu."""

    def __init__(self, conn: kuzu.Connection) -> None:
        self._conn = conn

    def upsert_entity(
        self, entity: Entity, session_timestamp: datetime | None = None
    ) -> None:
        """Insert or update an entity by its id.

        Tracks mention_count (incremented each call), first_seen (set only on
        first insert), and last_seen (updated to session_timestamp when provided).
        """
        # Check whether entity already exists to determine first_seen logic
        existing = self._conn.execute(
            "MATCH (e:Entity {id: $id}) RETURN e.first_seen, e.mention_count",
            parameters={"id": entity.id},
        )

        if existing.has_next():
            # Entity exists: preserve first_seen, increment mention_count
            row = existing.get_next()
            current_first_seen = row[0]
            current_count = row[1] or 0
            new_count = current_count + 1
            new_first_seen = current_first_seen  # unchanged

            params: dict = {
                "id": entity.id,
                "name": entity.name,
                "type": entity.type.value,
                "description": entity.description,
                "confidence": entity.confidence,
                "mention_count": new_count,
                "first_seen": new_first_seen,
            }
            set_last_seen = ""
            if session_timestamp is not None:
                params["last_seen"] = session_timestamp
                set_last_seen = ", e.last_seen = $last_seen"

            self._conn.execute(
                f"""
                MATCH (e:Entity {{id: $id}})
                SET e.name = $name, e.type = $type,
                    e.description = $description, e.confidence = $confidence,
                    e.mention_count = $mention_count,
                    e.first_seen = $first_seen
                    {set_last_seen}
                """,
                parameters=params,
            )
        else:
            # New entity: set first_seen and last_seen from session_timestamp
            params = {
                "id": entity.id,
                "name": entity.name,
                "type": entity.type.value,
                "description": entity.description,
                "confidence": entity.confidence,
                "mention_count": 1,
                "first_seen": session_timestamp,
                "last_seen": session_timestamp,
            }
            self._conn.execute(
                """
                CREATE (e:Entity {
                    id: $id, name: $name, type: $type,
                    description: $description, confidence: $confidence,
                    mention_count: $mention_count,
                    first_seen: $first_seen, last_seen: $last_seen
                })
                """,
                parameters=params,
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

    def upsert_session(
        self, session_id: str, project_name: str, file_path: Path
    ) -> None:
        """Insert or update a Session node."""
        self._conn.execute(
            """
            MERGE (s:Session {id: $id})
            SET s.project_name = $project, s.file_path = $fp
            """,
            parameters={
                "id": session_id,
                "project": project_name,
                "fp": str(file_path),
            },
        )

    def link_entity_to_session(self, entity_id: str, session_id: str) -> None:
        """Create a MENTIONED_IN edge from an entity to a session."""
        self._conn.execute(
            """
            MATCH (e:Entity {id: $eid}), (s:Session {id: $sid})
            CREATE (e)-[:MENTIONED_IN]->(s)
            """,
            parameters={"eid": entity_id, "sid": session_id},
        )
