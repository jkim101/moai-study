"""Custom exception hierarchy."""
from __future__ import annotations


class KGError(Exception):
    """Base exception for all Knowledge Graph errors."""


class ParseError(KGError):
    """Error during JSONL parsing."""


class ExtractionError(KGError):
    """Error during entity/relationship extraction."""


class AuthenticationError(ExtractionError):
    """Authentication failure with the Claude API."""


class StorageError(KGError):
    """Error during graph database operations."""


class QueryError(KGError):
    """Error executing a Cypher query."""


class VisualizationError(KGError):
    """Error generating graph visualization."""
