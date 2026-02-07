"""Database driver protocol with cancellation contract.

Defines the abstract base class for all database drivers, the
CancellationType enum specifying how each driver handles query
cancellation, and the QueryLimits dataclass for per-query resource
constraints.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class CancellationType(Enum):
    """How the driver handles query cancellation."""

    CONNECTION_LEVEL = "connection"  # Cancel via connection (PostgreSQL, MySQL)
    JOB_BASED = "job"  # Cancel via job ID (BigQuery, Snowflake)
    NONE = "none"  # No cancellation support (SQLite)


class DatabaseDriver(ABC):
    """Abstract base class for database drivers with strict cancellation contract.

    Each driver implementation must declare its cancellation mechanism
    and provide connect/execute/cancel/close/is_healthy semantics.
    """

    @property
    @abstractmethod
    def cancellation_type(self) -> CancellationType:
        """Return the cancellation mechanism this driver uses."""
        ...

    @property
    @abstractmethod
    def driver_name(self) -> str:
        """Return the driver name for ParameterContract lookup.

        Must match a key in ``ParameterContract.DRIVER_STYLES``.
        """
        ...

    @abstractmethod
    async def connect(self) -> None:
        """Establish connection to database."""
        ...

    @abstractmethod
    async def execute(
        self,
        sql: str,
        params: Sequence[Any] | Mapping[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Execute query and return results as list of dicts."""
        ...

    @abstractmethod
    async def cancel(self) -> bool:
        """Cancel in-flight query. Returns True if cancellation was sent."""
        ...

    @abstractmethod
    async def close(self) -> None:
        """Close connection and cleanup resources."""
        ...

    @property
    @abstractmethod
    def is_healthy(self) -> bool:
        """Return True if connection is healthy and reusable."""
        ...


@dataclass
class QueryLimits:
    """Resource limits for query execution."""

    timeout_seconds: int = 30
    max_rows: int = 10000
    max_bytes: int = 50 * 1024 * 1024  # 50MB

    @classmethod
    def from_sandbox(cls, sandbox_type: str) -> QueryLimits:
        """Get limits based on sandbox type."""
        if sandbox_type == "pyodide":
            return cls(
                timeout_seconds=10,
                max_rows=1000,
                max_bytes=10 * 1024 * 1024,
            )
        elif sandbox_type == "docker":
            return cls(
                timeout_seconds=30,
                max_rows=10000,
                max_bytes=50 * 1024 * 1024,
            )
        else:  # kubernetes
            return cls(
                timeout_seconds=60,
                max_rows=50000,
                max_bytes=100 * 1024 * 1024,
            )
