"""Pre-built Cypher query templates."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

import kuzu

from claude_conversation_kg.exceptions import QueryError
from claude_conversation_kg.extractor.models import RelationshipType

logger = logging.getLogger(__name__)


class QueryRunner:
    """Execute Cypher queries against the Kuzu graph database."""

    def __init__(self, conn: kuzu.Connection) -> None:
        self._conn = conn

    def get_stats(self) -> dict:
        """Return graph statistics including entity and relationship counts."""
        stats: dict = {}

        # Total entities
        result = self._conn.execute("MATCH (n:Entity) RETURN count(n)")
        stats["total_entities"] = result.get_next()[0]

        # Entity counts by type
        result = self._conn.execute(
            "MATCH (n:Entity) RETURN n.type, count(n) ORDER BY n.type"
        )
        entity_by_type: dict[str, int] = {}
        while result.has_next():
            row = result.get_next()
            entity_by_type[row[0]] = row[1]
        stats["entities_by_type"] = entity_by_type

        # Total relationships across all types
        total_rels = 0
        rel_by_type: dict[str, int] = {}
        for rel_type in RelationshipType:
            try:
                result = self._conn.execute(
                    f"MATCH ()-[r:{rel_type.value}]->() RETURN count(r)"
                )
                count = result.get_next()[0]
                rel_by_type[rel_type.value] = count
                total_rels += count
            except RuntimeError:
                rel_by_type[rel_type.value] = 0

        stats["total_relationships"] = total_rels
        stats["relationships_by_type"] = rel_by_type

        return stats

    def get_audit(self, limit: int = 10) -> dict:
        """Return knowledge graph audit insights.

        Returns top entities by mention_count, total entity count,
        and type breakdown sorted by mention frequency.
        """
        audit: dict = {}

        # Total entity count
        result = self._conn.execute("MATCH (n:Entity) RETURN count(n)")
        audit["total_entities"] = result.get_next()[0]

        if audit["total_entities"] == 0:
            audit["top_entities"] = []
            return audit

        # Top N entities by mention_count
        result = self._conn.execute(
            "MATCH (e:Entity) "
            "RETURN e.name, e.type, e.mention_count "
            "ORDER BY e.mention_count DESC "
            f"LIMIT {limit}"
        )
        top: list[dict] = []
        while result.has_next():
            row = result.get_next()
            top.append(
                {
                    "name": row[0],
                    "type": row[1],
                    "mention_count": row[2] or 0,
                }
            )
        audit["top_entities"] = top

        return audit

    def get_recent_entities(
        self, days: int, entity_type: str | None = None
    ) -> list[dict]:
        """Return entities first seen within the last N days.

        Args:
            days: Number of days to look back from now.
            entity_type: Optional entity type filter (e.g. "Technology").

        Returns:
            List of dicts with name, type, mention_count, first_seen keys.
        """
        since = datetime.now(tz=UTC) - timedelta(days=days)
        since_str = since.strftime("%Y-%m-%d %H:%M:%S")

        if entity_type:
            query = (
                "MATCH (e:Entity) "
                "WHERE e.first_seen >= timestamp($since) AND e.type = $type "
                "RETURN e.name, e.type, e.mention_count, e.first_seen "
                "ORDER BY e.first_seen DESC"
            )
            result = self._conn.execute(
                query,
                parameters={"since": since_str, "type": entity_type},
            )
        else:
            query = (
                "MATCH (e:Entity) "
                "WHERE e.first_seen >= timestamp($since) "
                "RETURN e.name, e.type, e.mention_count, e.first_seen "
                "ORDER BY e.first_seen DESC"
            )
            result = self._conn.execute(
                query,
                parameters={"since": since_str},
            )

        rows: list[dict] = []
        while result.has_next():
            row = result.get_next()
            rows.append(
                {
                    "name": row[0],
                    "type": row[1],
                    "mention_count": row[2] or 0,
                    "first_seen": row[3],
                }
            )
        return rows

    def search_entities(self, query: str, limit: int = 20) -> list[dict]:
        """Search entities by name (case-insensitive substring match).

        Args:
            query: Substring to search for in entity names.
            limit: Maximum number of results to return.

        Returns:
            List of dicts with id, name, type, mention_count keys.
        """
        result = self._conn.execute(
            "MATCH (e:Entity) "
            "WHERE lower(e.name) CONTAINS lower($query) "
            "RETURN e.id, e.name, e.type, e.mention_count "
            "ORDER BY e.mention_count DESC "
            "LIMIT $limit",
            parameters={"query": query, "limit": limit},
        )
        rows: list[dict] = []
        while result.has_next():
            row = result.get_next()
            rows.append(
                {
                    "id": row[0],
                    "name": row[1],
                    "type": row[2],
                    "mention_count": row[3] or 0,
                }
            )
        return rows

    def get_entity_connections(self, entity_id: str) -> dict | None:
        """Get entity details and all its connections.

        Args:
            entity_id: The unique identifier of the entity.

        Returns:
            Dict with entity info and connections list, or None if not found.
        """
        # Get entity info
        result = self._conn.execute(
            "MATCH (e:Entity) WHERE e.id = $id "
            "RETURN e.id, e.name, e.type, e.mention_count, "
            "e.first_seen, e.last_seen",
            parameters={"id": entity_id},
        )
        if not result.has_next():
            return None

        row = result.get_next()
        entity = {
            "id": row[0],
            "name": row[1],
            "type": row[2],
            "mention_count": row[3] or 0,
            "first_seen": str(row[4]) if row[4] else None,
            "last_seen": str(row[5]) if row[5] else None,
        }

        # Get connections (both outgoing and incoming)
        connections: list[dict] = []
        for rel_type in RelationshipType:
            try:
                # Outgoing relationships
                rels = self._conn.execute(
                    f"MATCH (a:Entity)-[r:{rel_type.value}]->(b:Entity) "
                    f"WHERE a.id = $id "
                    f"RETURN b.id, b.name, b.type, b.mention_count",
                    parameters={"id": entity_id},
                )
                while rels.has_next():
                    r = rels.get_next()
                    connections.append(
                        {
                            "direction": "outgoing",
                            "relationship": rel_type.value,
                            "entity": {
                                "id": r[0],
                                "name": r[1],
                                "type": r[2],
                                "mention_count": r[3] or 0,
                            },
                        }
                    )
            except RuntimeError:
                pass

            try:
                # Incoming relationships
                rels = self._conn.execute(
                    f"MATCH (a:Entity)-[r:{rel_type.value}]->(b:Entity) "
                    f"WHERE b.id = $id "
                    f"RETURN a.id, a.name, a.type, a.mention_count",
                    parameters={"id": entity_id},
                )
                while rels.has_next():
                    r = rels.get_next()
                    connections.append(
                        {
                            "direction": "incoming",
                            "relationship": rel_type.value,
                            "entity": {
                                "id": r[0],
                                "name": r[1],
                                "type": r[2],
                                "mention_count": r[3] or 0,
                            },
                        }
                    )
            except RuntimeError:
                pass

        return {"entity": entity, "connections": connections}

    def execute(self, cypher: str) -> list[dict]:
        """Execute an arbitrary Cypher query and return results as dicts."""
        try:
            result = self._conn.execute(cypher)
        except RuntimeError as e:
            raise QueryError(f"Invalid Cypher query: {e}") from e

        columns = result.get_column_names()
        rows: list[dict] = []
        while result.has_next():
            row = result.get_next()
            rows.append(dict(zip(columns, row)))
        return rows
