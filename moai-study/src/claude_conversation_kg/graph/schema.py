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
    PRIMARY KEY (id)
)
"""

PROCESSED_FILES_TABLE_DDL = """
CREATE NODE TABLE IF NOT EXISTS ProcessedFile (
    file_path STRING,
    mtime DOUBLE,
    processed_at TIMESTAMP,
    PRIMARY KEY (file_path)
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


def initialize_schema(conn: kuzu.Connection) -> None:
    """Create all node and relationship tables with IF NOT EXISTS.

    Safe to call multiple times (idempotent).
    """
    conn.execute(ENTITY_TABLE_DDL)
    conn.execute(PROCESSED_FILES_TABLE_DDL)

    for rel_type in RelationshipType:
        conn.execute(_relationship_ddl(rel_type.value))

    logger.info("Graph schema initialized successfully")
