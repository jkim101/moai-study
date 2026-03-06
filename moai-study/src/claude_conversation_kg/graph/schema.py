"""Graph schema initialization."""

from __future__ import annotations

import logging

import kuzu

from claude_conversation_kg.extractor.models import RelationshipType

logger = logging.getLogger(__name__)

ENTITY_TABLE_DDL = """
CREATE NODE TABLE IF NOT EXISTS Entity (
    id STRING,
    name STRING,
    type STRING,
    description STRING,
    confidence DOUBLE,
    first_seen TIMESTAMP,
    last_seen TIMESTAMP,
    mention_count INT64,
    PRIMARY KEY (id)
)
"""

# Migration: columns added after initial release; safe to run on existing DBs
_ENTITY_MIGRATION_QUERIES = [
    "ALTER TABLE Entity ADD COLUMN first_seen TIMESTAMP",
    "ALTER TABLE Entity ADD COLUMN last_seen TIMESTAMP",
    "ALTER TABLE Entity ADD COLUMN mention_count INT64 DEFAULT 0",
]

PROCESSED_FILES_TABLE_DDL = """
CREATE NODE TABLE IF NOT EXISTS ProcessedFile (
    file_path STRING,
    mtime DOUBLE,
    processed_at TIMESTAMP,
    PRIMARY KEY (file_path)
)
"""

SESSION_TABLE_DDL = """
CREATE NODE TABLE IF NOT EXISTS Session (
    id STRING,
    project_name STRING,
    file_path STRING,
    started_at TIMESTAMP,
    ended_at TIMESTAMP,
    PRIMARY KEY (id)
)
"""

_SESSION_MIGRATION_QUERIES = [
    "ALTER TABLE Session ADD COLUMN started_at TIMESTAMP",
    "ALTER TABLE Session ADD COLUMN ended_at TIMESTAMP",
]

MENTIONED_IN_DDL = """
CREATE REL TABLE IF NOT EXISTS MENTIONED_IN (
    FROM Entity TO Session
)
"""


def _relationship_ddl(rel_type: str) -> str:
    """Generate DDL for a relationship table."""
    return f"""
CREATE REL TABLE IF NOT EXISTS {rel_type} (
    FROM Entity TO Entity,
    context STRING,
    confidence DOUBLE
)
"""


def _migrate(conn: kuzu.Connection) -> None:
    """Apply incremental migrations for existing databases.

    Each ALTER TABLE is wrapped in try/except so re-running is idempotent:
    Kuzu raises RuntimeError if the column already exists.
    """
    for query in _ENTITY_MIGRATION_QUERIES + _SESSION_MIGRATION_QUERIES:
        try:
            conn.execute(query)
            logger.debug("Migration applied: %s", query.split("COLUMN")[1].strip())
        except RuntimeError:
            pass  # Column already exists — migration already applied


def initialize_schema(conn: kuzu.Connection) -> None:
    """Create all node and relationship tables with IF NOT EXISTS.

    Safe to call multiple times (idempotent).
    Also applies incremental migrations for existing databases.
    """
    conn.execute(ENTITY_TABLE_DDL)
    conn.execute(PROCESSED_FILES_TABLE_DDL)
    conn.execute(SESSION_TABLE_DDL)
    conn.execute(MENTIONED_IN_DDL)

    for rel_type in RelationshipType:
        conn.execute(_relationship_ddl(rel_type.value))

    _migrate(conn)
    logger.info("Graph schema initialized successfully")
