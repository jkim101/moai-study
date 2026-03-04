"""Tests for exception hierarchy -- RED phase."""

from __future__ import annotations

from claude_conversation_kg.exceptions import (
    AuthenticationError,
    ExtractionError,
    KGError,
    ParseError,
    QueryError,
    StorageError,
    VisualizationError,
)


class TestExceptionHierarchy:
    """Specification tests for exception hierarchy."""

    def test_all_inherit_from_kg_error(self) -> None:
        """All custom exceptions inherit from KGError."""
        assert issubclass(ParseError, KGError)
        assert issubclass(ExtractionError, KGError)
        assert issubclass(AuthenticationError, KGError)
        assert issubclass(StorageError, KGError)
        assert issubclass(QueryError, KGError)
        assert issubclass(VisualizationError, KGError)

    def test_authentication_error_is_extraction_error(self) -> None:
        """AuthenticationError is a subclass of ExtractionError."""
        assert issubclass(AuthenticationError, ExtractionError)

    def test_exceptions_are_catchable(self) -> None:
        """Exceptions can be raised and caught."""
        with __import__("pytest").raises(KGError):
            raise ParseError("test parse error")

        with __import__("pytest").raises(ExtractionError):
            raise AuthenticationError("test auth error")

    def test_exception_messages(self) -> None:
        """Exception messages are preserved."""
        err = StorageError("database locked")
        assert str(err) == "database locked"
