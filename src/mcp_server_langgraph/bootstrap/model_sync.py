"""
Model Sync Bootstrap Module.

Provides initialization for LiteLLM model sync scheduler that
periodically syncs pricing from LiteLLM to the ModelRegistry.

This enables dynamic pricing updates without code changes,
supporting multi-provider cost tracking accuracy.

Follows existing pattern from bootstrap/context_graph.py.

Sprint 1 - Enhanced Model Selector: LiteLLM Dynamic Model Sync
"""

import asyncio
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from mcp_server_langgraph.core.feature_flags import feature_flags
from mcp_server_langgraph.observability.telemetry import logger

if TYPE_CHECKING:
    from mcp_server_langgraph.core.config import Settings


@dataclass
class ModelSyncState:
    """Model sync component state.

    Holds references to the sync scheduler task and instance,
    and provides cleanup method for graceful shutdown.

    Attributes:
        sync_task: Background asyncio.Task for the scheduler
        sync_instance: LiteLLMModelSync instance for one-time syncs
    """

    sync_task: asyncio.Task[None] | None = None
    sync_instance: Any | None = None

    async def cleanup(self) -> None:
        """Cancel the sync task gracefully.

        Handles:
        1. None task (not started)
        2. Already-done task (completed or failed)
        3. Running task (needs cancellation)
        """
        if self.sync_task is None:
            return

        if self.sync_task.done():
            logger.debug("Model sync task already completed")
            return

        self.sync_task.cancel()
        try:
            await self.sync_task
        except asyncio.CancelledError:
            pass
        logger.debug("Model sync scheduler cancelled")


async def init_model_sync(settings: "Settings") -> ModelSyncState | None:
    """Initialize model sync if enabled.

    Creates the LiteLLMModelSync instance and starts the background
    scheduler that syncs pricing every 24 hours.

    The scheduler:
    - Waits 60 seconds before first sync (avoid startup load)
    - Runs sync every 24 hours
    - Respects the enable_litellm_model_sync feature flag
    - Logs errors but does not crash

    Args:
        settings: Application settings (not currently used but follows pattern)

    Returns:
        ModelSyncState if enabled, None if disabled
    """
    if not feature_flags.enable_litellm_model_sync:
        logger.debug("LiteLLM model sync disabled")
        return None

    from mcp_server_langgraph.agents.litellm_model_sync import (
        LiteLLMModelSync,
        start_model_sync_scheduler,
    )

    # Create sync instance (useful for one-time syncs and testing)
    sync_instance = LiteLLMModelSync()

    # Start background scheduler
    sync_task = await start_model_sync_scheduler()

    logger.info("LiteLLM model sync initialized")
    return ModelSyncState(
        sync_task=sync_task,
        sync_instance=sync_instance,
    )
