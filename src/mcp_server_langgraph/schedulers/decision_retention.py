"""Decision trace retention scheduler.

Simple DELETE-based cleanup (not partition-based like audit_logs).
Runs daily, deletes traces older than retention_days.

Reference: ADR-0101 Context Graphs
"""

import asyncio
from typing import TYPE_CHECKING

from mcp_server_langgraph.core.feature_flags import feature_flags
from mcp_server_langgraph.observability.telemetry import logger

if TYPE_CHECKING:
    from mcp_server_langgraph.repositories.decision_trace import (
        DecisionTraceRepositoryBase,
    )

CLEANUP_INTERVAL_SECONDS = 86400  # 24 hours


async def start_retention_scheduler(
    repository: "DecisionTraceRepositoryBase",
) -> asyncio.Task[None]:
    """Start background retention task.

    Creates a background task that periodically deletes expired
    decision traces based on the retention_days setting.

    Args:
        repository: Repository for deleting expired traces

    Returns:
        The background task for lifecycle management
    """
    return asyncio.create_task(
        _retention_loop(repository),
        name="decision_retention_scheduler",
    )


async def _retention_loop(repository: "DecisionTraceRepositoryBase") -> None:
    """Background loop for retention cleanup.

    Runs indefinitely, cleaning up expired traces once per day.
    Initial delay of 60 seconds to avoid startup load.
    """
    # Initial delay to avoid startup load
    await asyncio.sleep(60)

    while True:
        try:
            retention_days = feature_flags.context_graph_retention_days
            deleted = await repository.delete_expired(retention_days)

            if deleted > 0:
                logger.info(f"Decision retention: deleted {deleted} expired traces")
            else:
                logger.debug("Decision retention: no expired traces")

            await asyncio.sleep(CLEANUP_INTERVAL_SECONDS)

        except asyncio.CancelledError:
            logger.info("Decision retention scheduler stopped")
            raise
        except Exception as e:
            logger.error(f"Decision retention error: {e}")
            await asyncio.sleep(CLEANUP_INTERVAL_SECONDS)
