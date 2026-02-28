"""Pre-built Cypher query templates."""
from __future__ import annotations

import logging

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
