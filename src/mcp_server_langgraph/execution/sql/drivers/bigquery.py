"""BigQuery database driver with job-based cancellation.

Uses the google-cloud-bigquery client library to execute parameterized
queries against Google BigQuery. Cancellation is performed via
``job.cancel()`` on the in-flight ``QueryJob``.

The BigQuery client is expected to be shared across driver instances
(one client per project), so ``close()`` is intentionally a no-op.

google-cloud-bigquery is an optional dependency; importing this module
without it installed raises a clear error at construction time.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

from mcp_server_langgraph.execution.sql.drivers.base import (
    CancellationType,
    DatabaseDriver,
)
from mcp_server_langgraph.execution.sql.exceptions import (
    SQLConnectionError,
    SQLExecutionError,
    SQLTimeoutError,
)

logger = logging.getLogger(__name__)

try:
    from google.cloud import bigquery
    from google.cloud.bigquery import QueryJobConfig

    _HAS_BIGQUERY = True
except ImportError:
    _HAS_BIGQUERY = False

if TYPE_CHECKING:
    from google.cloud.bigquery import Client, QueryJob


class BigQueryPriority(Enum):
    """BigQuery query priority tiers."""

    INTERACTIVE = "INTERACTIVE"
    BATCH = "BATCH"


@dataclass
class BigQueryLimits:
    """Tiered cost-control limits for BigQuery queries.

    Attributes:
        max_bytes_billed: Maximum bytes billed for a query.  ``None``
            means no limit (use with caution).  Default is 1 GiB.
        timeout_seconds: Per-query timeout in seconds.
        use_query_cache: Whether to allow BigQuery result caching.
        priority: Query priority (INTERACTIVE or BATCH).
    """

    max_bytes_billed: int | None = 1 * 1024 * 1024 * 1024  # 1 GiB
    timeout_seconds: float = 30.0
    use_query_cache: bool = True
    priority: BigQueryPriority = field(default=BigQueryPriority.INTERACTIVE)

    @classmethod
    def for_sandbox(cls, sandbox_type: str) -> BigQueryLimits:
        """Return limits appropriate for a given sandbox tier."""
        if sandbox_type == "pyodide":
            return cls(
                max_bytes_billed=100 * 1024 * 1024,  # 100 MiB
                timeout_seconds=10.0,
                use_query_cache=True,
                priority=BigQueryPriority.BATCH,
            )
        elif sandbox_type == "docker":
            return cls(
                max_bytes_billed=1 * 1024 * 1024 * 1024,  # 1 GiB
                timeout_seconds=30.0,
                use_query_cache=True,
                priority=BigQueryPriority.INTERACTIVE,
            )
        else:  # kubernetes
            return cls(
                max_bytes_billed=10 * 1024 * 1024 * 1024,  # 10 GiB
                timeout_seconds=60.0,
                use_query_cache=True,
                priority=BigQueryPriority.INTERACTIVE,
            )


class BigQueryDriver(DatabaseDriver):
    """BigQuery driver using google-cloud-bigquery.

    Parameters:
        project: GCP project ID.
        client: Optional pre-constructed ``bigquery.Client``.  When
            ``None`` a new client is created for *project* during
            ``connect()``.
        limits: Optional ``BigQueryLimits`` for cost control.  When
            ``None`` default limits are applied.
    """

    def __init__(
        self,
        project: str,
        client: Client | None = None,
        limits: BigQueryLimits | None = None,
    ) -> None:
        if not _HAS_BIGQUERY:
            raise ImportError(
                "google-cloud-bigquery is required for BigQueryDriver. Install it with: pip install google-cloud-bigquery"
            )
        self._project = project
        self._client: Client | None = client
        self._limits = limits or BigQueryLimits()
        self._current_job: QueryJob | None = None
        self._healthy = False

    # -- DatabaseDriver interface ------------------------------------------

    @property
    def cancellation_type(self) -> CancellationType:
        return CancellationType.JOB_BASED

    @property
    def driver_name(self) -> str:
        """bigquery driver for ParameterContract lookup."""
        return "bigquery"

    async def connect(self) -> None:
        """Initialise the BigQuery client if not already provided."""
        if self._client is not None:
            self._healthy = True
            return
        try:
            loop = asyncio.get_running_loop()
            self._client = await loop.run_in_executor(None, lambda: bigquery.Client(project=self._project))
            self._healthy = True
            logger.info("BigQuery client initialised for project %s", self._project)
        except Exception as exc:
            self._healthy = False
            raise SQLConnectionError(f"Failed to create BigQuery client for project {self._project}") from exc

    async def execute(
        self,
        sql: str,
        params: Sequence[Any] | Mapping[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Execute *sql* against BigQuery and return rows as dicts."""
        if self._client is None or not self._healthy:
            raise SQLConnectionError("BigQuery client is not connected")

        job_config = QueryJobConfig()

        # Cost-control settings
        if self._limits.max_bytes_billed is not None:
            job_config.maximum_bytes_billed = self._limits.max_bytes_billed
        job_config.use_query_cache = self._limits.use_query_cache

        # Parameterised queries (BigQuery uses named @param style)
        if params and isinstance(params, Mapping):
            query_params = [
                bigquery.ScalarQueryParameter(name, _python_type_to_bq(value), value) for name, value in params.items()
            ]
            job_config.query_parameters = query_params

        loop = asyncio.get_running_loop()

        try:
            job: QueryJob = await loop.run_in_executor(
                None,
                lambda: self._client.query(sql, job_config=job_config),  # type: ignore[union-attr]
            )
            self._current_job = job

            rows = await loop.run_in_executor(
                None,
                lambda: list(job.result(timeout=self._limits.timeout_seconds)),
            )

            return [dict(row) for row in rows]

        except Exception as exc:
            exc_name = type(exc).__name__
            if "Timeout" in exc_name or "DeadlineExceeded" in exc_name:
                raise SQLTimeoutError(f"BigQuery query timed out after {self._limits.timeout_seconds}s") from exc
            raise SQLExecutionError(f"BigQuery query execution failed: {exc}") from exc
        finally:
            self._current_job = None

    async def cancel(self) -> bool:
        """Cancel the in-flight BigQuery job, if any."""
        job = self._current_job
        if job is None:
            logger.debug("No in-flight BigQuery job to cancel")
            return False

        try:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, job.cancel)
            logger.info("Cancelled BigQuery job %s", job.job_id)
            return True
        except Exception:
            logger.warning("Failed to cancel BigQuery job %s", job.job_id, exc_info=True)
            return False

    async def close(self) -> None:
        """No-op: BigQuery client is shared and not owned by this driver."""

    @property
    def is_healthy(self) -> bool:
        return self._healthy


# -- helpers ---------------------------------------------------------------


def _python_type_to_bq(value: Any) -> str:
    """Map a Python value to a BigQuery scalar type string."""
    if isinstance(value, bool):
        return "BOOL"
    if isinstance(value, int):
        return "INT64"
    if isinstance(value, float):
        return "FLOAT64"
    if isinstance(value, bytes):
        return "BYTES"
    # Default to STRING for str and anything else
    return "STRING"
