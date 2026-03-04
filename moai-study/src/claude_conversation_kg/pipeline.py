"""Ingestion pipeline orchestrating parse-extract-store workflow."""

from __future__ import annotations

import logging
import re
from datetime import datetime
from pathlib import Path

from claude_conversation_kg.extractor.processor import BatchProcessor
from claude_conversation_kg.graph.store import GraphStore
from claude_conversation_kg.parser.models import ConversationSession
from claude_conversation_kg.parser.reader import discover_jsonl_files, read_jsonl_file
from claude_conversation_kg.parser.transformer import transform

logger = logging.getLogger(__name__)

# Common path segments to skip when extracting project names
_PATH_NOISE = {"users", "home", "workspace", "dev", "projects", "src", "code"}


def _session_timestamp(session: ConversationSession) -> datetime | None:
    """Return the latest message timestamp from a session, or None."""
    timestamps = [m.timestamp for m in session.messages if m.timestamp is not None]
    return max(timestamps) if timestamps else None


def _extract_project_name(file_path: Path) -> str:
    """Derive a human-readable project name from a JSONL file path.

    Converts encoded directory names like '-Users-jkim101-workspace-moai-study'
    into a cleaner label like 'moai-study'.
    """
    folder = file_path.parent.name  # e.g. '-Users-jkim101-workspace-moai-study'
    # Split on dashes and filter noise words / single chars
    parts = [
        p
        for p in re.split(r"[-_]", folder)
        if p and p.lower() not in _PATH_NOISE and len(p) > 1
    ]
    # Remove likely username (looks like an alphanumeric handle with digits)
    parts = [p for p in parts if not re.match(r"^[a-z]+\d+$", p.lower())]
    return "-".join(parts[-2:]) if len(parts) >= 2 else (parts[-1] if parts else folder)


class IngestionPipeline:
    """Orchestrate the full parse-extract-store workflow."""

    def __init__(
        self,
        store: GraphStore,
        processor: BatchProcessor,
    ) -> None:
        self._store = store
        self._processor = processor

    def ingest(self, path: Path) -> dict:
        """Ingest JSONL files from the given path.

        Returns a summary dict with processing statistics.
        """
        files_processed = 0
        files_skipped = 0
        entities_stored = 0
        relationships_stored = 0
        errors = 0

        for jsonl_path in discover_jsonl_files(path):
            mtime = jsonl_path.stat().st_mtime

            if self._store.is_file_processed(jsonl_path, mtime):
                logger.info("Skipping already processed file: %s", jsonl_path)
                files_skipped += 1
                continue

            try:
                raw_messages = read_jsonl_file(jsonl_path)
                session = transform(jsonl_path, raw_messages)

                if not session.messages:
                    logger.info("Skipping empty file: %s", jsonl_path)
                    files_skipped += 1
                    continue

                # Create Session node for this conversation file
                session_id = jsonl_path.stem  # UUID filename without extension
                project_name = _extract_project_name(jsonl_path)
                self._store.upsert_session(session_id, project_name, jsonl_path)

                result = self._processor.process_session(session)
                ts = _session_timestamp(session)

                for entity in result.entities:
                    self._store.upsert_entity(entity, session_timestamp=ts)
                    self._store.link_entity_to_session(entity.id, session_id)
                    entities_stored += 1

                for rel in result.relationships:
                    self._store.upsert_relationship(rel)
                    relationships_stored += 1

                self._store.mark_file_processed(jsonl_path, mtime)
                files_processed += 1

            except Exception:
                logger.exception("Error processing %s", jsonl_path)
                errors += 1

        return {
            "files_processed": files_processed,
            "files_skipped": files_skipped,
            "entities_stored": entities_stored,
            "relationships_stored": relationships_stored,
            "errors": errors,
        }
