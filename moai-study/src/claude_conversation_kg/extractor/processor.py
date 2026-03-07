"""Batch processing orchestration."""

from __future__ import annotations

import hashlib
import logging

from claude_conversation_kg.exceptions import ExtractionError, PromptTooLargeError
from claude_conversation_kg.extractor.client import ExtractionClient
from claude_conversation_kg.extractor.models import ExtractionResult, UsageStats
from claude_conversation_kg.parser.models import (
    ConversationMessage,
    ConversationSession,
)

logger = logging.getLogger(__name__)

# Minimum batch size below which we stop splitting
_MIN_BATCH_SIZE = 2


class BatchProcessor:
    """Process conversation sessions in batches with caching."""

    def __init__(self, client: ExtractionClient) -> None:
        self._client = client
        self._cache: dict[str, ExtractionResult] = {}

    def _session_hash(self, session: ConversationSession) -> str:
        """Compute a hash for a session based on its content."""
        content = "".join(f"{m.role}:{m.content}" for m in session.messages)
        return hashlib.sha256(content.encode()).hexdigest()

    def _extract_batch(
        self,
        batch: list[ConversationMessage],
    ) -> tuple[ExtractionResult, UsageStats]:
        """Extract from a batch, splitting in half if prompt is too large."""
        try:
            return self._client.extract(batch)
        except PromptTooLargeError:
            if len(batch) <= _MIN_BATCH_SIZE:
                logger.warning(
                    "Batch of %d messages still too large, skipping",
                    len(batch),
                )
                return ExtractionResult(entities=[], relationships=[]), UsageStats()

            mid = len(batch) // 2
            logger.info(
                "Batch too large (%d messages), splitting into %d + %d",
                len(batch),
                mid,
                len(batch) - mid,
            )
            r1, u1 = self._extract_batch(batch[:mid])
            r2, u2 = self._extract_batch(batch[mid:])
            combined = ExtractionResult(
                entities=r1.entities + r2.entities,
                relationships=r1.relationships + r2.relationships,
            )
            return combined, u1 + u2

    def process_session(
        self,
        session: ConversationSession,
        batch_size: int = 10,
    ) -> tuple[ExtractionResult, UsageStats]:
        """Process a session by batching messages and calling the extraction client.

        Each batch is processed independently — a single batch failure does
        not prevent remaining batches from being processed.
        Batches that exceed the token limit are automatically split.
        Returns a tuple of (ExtractionResult, UsageStats).
        """
        session_hash = self._session_hash(session)

        if session_hash in self._cache:
            logger.info("Cache hit for session %s", session.file_path)
            return self._cache[session_hash], UsageStats()

        all_entities = []
        all_relationships = []
        accumulated_usage = UsageStats()
        batch_errors = 0

        messages = session.messages
        for i in range(0, len(messages), batch_size):
            batch = messages[i : i + batch_size]
            try:
                result, usage = self._extract_batch(batch)
                all_entities.extend(result.entities)
                all_relationships.extend(result.relationships)
                accumulated_usage = accumulated_usage + usage
            except ExtractionError as e:
                batch_errors += 1
                logger.warning(
                    "Batch %d-%d failed (skipping): %s",
                    i,
                    min(i + batch_size, len(messages)),
                    e,
                )

        if batch_errors:
            total_batches = (len(messages) + batch_size - 1) // batch_size
            logger.info(
                "Session %s: %d/%d batches failed",
                session.file_path,
                batch_errors,
                total_batches,
            )

        combined = ExtractionResult(
            entities=all_entities,
            relationships=all_relationships,
        )
        self._cache[session_hash] = combined
        return combined, accumulated_usage
