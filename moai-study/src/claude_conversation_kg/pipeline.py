"""Ingestion pipeline orchestrating parse-extract-store workflow."""
from __future__ import annotations

import logging
from pathlib import Path

from claude_conversation_kg.extractor.processor import BatchProcessor
from claude_conversation_kg.graph.store import GraphStore
from claude_conversation_kg.parser.reader import discover_jsonl_files, read_jsonl_file
from claude_conversation_kg.parser.transformer import transform

logger = logging.getLogger(__name__)


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

                result = self._processor.process_session(session)

                for entity in result.entities:
                    self._store.upsert_entity(entity)
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
