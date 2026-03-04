"""Kuzu database connection management."""

from __future__ import annotations

from pathlib import Path
from types import TracebackType

import kuzu


class KuzuConnection:
    """Manages a Kuzu embedded database connection.

    Supports context manager protocol for safe resource handling.
    """

    def __init__(self, db_path: Path) -> None:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._db = kuzu.Database(str(db_path))
        self.conn = kuzu.Connection(self._db)

    def __enter__(self) -> KuzuConnection:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        pass
