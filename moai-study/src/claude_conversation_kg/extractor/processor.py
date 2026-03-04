"""Batch processing orchestration."""

from __future__ import annotations

import hashlib
import logging

from claude_conversation_kg.extractor.client import ExtractionClient
from claude_conversation_kg.extractor.models import ExtractionResult
from claude_conversation_kg.parser.models import ConversationSession

logger = logging.getLogger(__name__)


class BatchProcessor:
    """Process conversation sessions in batches with caching."""

    def __init__(self, client: ExtractionClient) -> None:
        self._client = client
        self._cache: dict[str, ExtractionResult] = {}

    def _session_hash(self, session: ConversationSession) -> str:
        """Compute a hash for a session based on its content."""
        content = "".join(f"{m.role}:{m.content}" for m in session.messages)
        return hashlib.sha256(content.encode()).hexdigest()

    def process_session(
        self,
        session: ConversationSession,
        batch_size: int = 10,
    ) -> ExtractionResult:
        """Process a session by batching messages and calling the extraction client.

        Results are cached by session content hash to avoid re-processing.
        """
        session_hash = self._session_hash(session)

        if session_hash in self._cache:
            logger.info("Cache hit for session %s", session.file_path)
            return self._cache[session_hash]

        all_entities = []
        all_relationships = []

        messages = session.messages
        for i in range(0, len(messages), batch_size):
            batch = messages[i : i + batch_size]
            result = self._client.extract(batch)
            all_entities.extend(result.entities)
            all_relationships.extend(result.relationships)

        combined = ExtractionResult(
            entities=all_entities,
            relationships=all_relationships,
        )
        self._cache[session_hash] = combined
        return combined
