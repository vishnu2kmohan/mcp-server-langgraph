"""
CostRetentionPolicy - Retention policy for cost metrics.

Extracted from CostMetricsCollector as part of Phase 2.2 SRP decomposition.

Responsibilities:
- Define retention period configuration
- Execute cleanup of old records
- Log cleanup results

Reference: Plan - Phase 2.2 SRP: Decompose CostMetricsCollector
"""

from datetime import datetime, timedelta, UTC

from mcp_server_langgraph.monitoring.cost_storage import CostStorageBackend
from mcp_server_langgraph.observability.telemetry import logger


class CostRetentionPolicy:
    """
    Retention policy for cost metrics records.

    Encapsulates the logic for cleaning up old records based on
    a configurable retention period.

    Default retention is 90 days.
    """

    DEFAULT_RETENTION_DAYS = 90

    def __init__(self, retention_days: int | None = None) -> None:
        """
        Initialize the retention policy.

        Args:
            retention_days: Number of days to retain records (default: 90)
        """
        self._retention_days = retention_days or self.DEFAULT_RETENTION_DAYS

    @property
    def retention_days(self) -> int:
        """Get the configured retention period in days."""
        return self._retention_days

    async def cleanup(self, storage: CostStorageBackend) -> int:
        """
        Clean up records older than the retention period.

        Args:
            storage: Storage backend to clean up

        Returns:
            Number of records deleted
        """
        cutoff = datetime.now(UTC) - timedelta(days=self._retention_days)

        deleted_count = await storage.delete_records_before(cutoff)

        if deleted_count > 0:
            logger.info(
                f"Cleaned up {deleted_count} cost records older than {self._retention_days} days",
                extra={
                    "deleted_count": deleted_count,
                    "retention_days": self._retention_days,
                    "cutoff": cutoff.isoformat(),
                },
            )
        else:
            logger.info(
                "No old cost records to clean up",
                extra={
                    "retention_days": self._retention_days,
                    "cutoff": cutoff.isoformat(),
                },
            )

        return deleted_count
