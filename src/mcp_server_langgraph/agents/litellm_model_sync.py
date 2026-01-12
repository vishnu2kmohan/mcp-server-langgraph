"""
LiteLLM Model Sync

Synchronizes model information from LiteLLM to ModelRegistry.
Enables dynamic model discovery and pricing updates.

Sprint 1 - Enhanced Model Selector: LiteLLM Dynamic Model Sync

Usage:
    from mcp_server_langgraph.agents.litellm_model_sync import (
        LiteLLMModelSync,
        start_model_sync_scheduler,
    )

    # One-time sync
    sync = LiteLLMModelSync()
    updated_count = sync.sync_pricing()

    # Background scheduler
    task = await start_model_sync_scheduler()
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

import litellm

from mcp_server_langgraph.agents.litellm_prometheus_metrics import (
    record_sync_failure,
    record_sync_success,
)
from mcp_server_langgraph.agents.model_registry import get_default_registry
from mcp_server_langgraph.core.feature_flags import feature_flags
from mcp_server_langgraph.observability.telemetry import logger

# Sync interval: 24 hours (model info is relatively static)
SYNC_INTERVAL_SECONDS = 86400

# Initial delay to avoid startup load (60 seconds)
INITIAL_DELAY_SECONDS = 60


class LiteLLMModelSync:
    """
    Synchronizes model information from LiteLLM to ModelRegistry.

    LiteLLM maintains a comprehensive model_cost dictionary with pricing
    information for all supported models. This class syncs that data
    to the ModelRegistry, enabling:

    - Dynamic pricing updates without code changes
    - Discovery of new models supported by LiteLLM
    - Consistent pricing across frontend and backend

    Example:
        >>> sync = LiteLLMModelSync()
        >>> updated = sync.sync_pricing()
        >>> print(f"Updated {updated} models")
        Updated 5 models
    """

    def __init__(self) -> None:
        """Initialize the LiteLLM model sync."""
        self._registry = get_default_registry()

    def get_litellm_models(self) -> dict[str, dict[str, Any]]:
        """
        Get the model cost dictionary from LiteLLM.

        Returns a dictionary mapping model IDs to their pricing information.
        Each model entry contains:
        - input_cost_per_token: Cost per input token
        - output_cost_per_token: Cost per output token
        - max_tokens: Maximum context length (optional)
        - supports_vision: Whether model supports images (optional)

        Returns:
            Dictionary of model IDs to pricing/capability info.
            Returns empty dict if LiteLLM data is unavailable.
        """
        try:
            model_cost = getattr(litellm, "model_cost", None)
            if model_cost is None:
                logger.debug("LiteLLM model_cost not available")
                return {}
            return dict(model_cost)
        except Exception as e:
            logger.warning(f"Failed to get LiteLLM models: {e}")
            return {}

    def sync_pricing(self) -> int:
        """
        Synchronize pricing from LiteLLM to ModelRegistry.

        Updates pricing for models that exist in both LiteLLM's model_cost
        and the ModelRegistry. Does not add new models to the registry.

        Returns:
            Number of models updated.
        """
        start_time = time.monotonic()
        try:
            litellm_models = self.get_litellm_models()
            if not litellm_models:
                logger.debug("No LiteLLM models to sync")
                duration = time.monotonic() - start_time
                record_sync_success(duration_seconds=duration, models_updated=0)
                return 0

            updated_count = 0
            for model_id, model_info in litellm_models.items():
                normalized_id = self._normalize_model_id(model_id)

                # Check if model exists in registry
                if normalized_id in self._registry._models:
                    caps = self._registry._models[normalized_id]

                    # Extract pricing from LiteLLM
                    input_cost = model_info.get("input_cost_per_token", 0)
                    output_cost = model_info.get("output_cost_per_token", 0)

                    if input_cost or output_cost:
                        # Convert per-token to per-1M
                        new_input = self._convert_to_per_1m(input_cost)
                        new_output = self._convert_to_per_1m(output_cost)

                        # Only update if prices differ
                        if caps.input_cost_per_1m != new_input or caps.output_cost_per_1m != new_output:
                            caps.input_cost_per_1m = new_input
                            caps.output_cost_per_1m = new_output
                            updated_count += 1
                            logger.debug(
                                f"Updated pricing for {normalized_id}: ${new_input}/1M input, ${new_output}/1M output"
                            )

            if updated_count > 0:
                logger.info(f"LiteLLM sync: updated pricing for {updated_count} models")
            else:
                logger.debug("LiteLLM sync: no pricing updates needed")

            # Record success metrics
            duration = time.monotonic() - start_time
            record_sync_success(duration_seconds=duration, models_updated=updated_count)

            return updated_count

        except Exception as e:
            logger.error(f"LiteLLM sync error: {e}")
            # Record failure metrics
            duration = time.monotonic() - start_time
            error_type = type(e).__name__
            record_sync_failure(error_type=error_type, duration_seconds=duration)
            return 0

    def update_registry(self) -> int:
        """
        Update ModelRegistry with LiteLLM data.

        Currently delegates to sync_pricing(). In the future, this could
        also sync capabilities (vision, tools, etc.) if LiteLLM provides them.

        Returns:
            Number of models updated.
        """
        return self.sync_pricing()

    def _convert_to_per_1m(self, per_token_cost: float) -> float:
        """
        Convert per-token cost to per-1M tokens cost.

        Args:
            per_token_cost: Cost per single token

        Returns:
            Cost per 1 million tokens
        """
        return per_token_cost * 1_000_000

    def _normalize_model_id(self, model_id: str) -> str:
        """
        Normalize LiteLLM model ID to ModelRegistry format.

        LiteLLM uses various prefixes like "openai/gpt-4" or "anthropic/claude".
        This removes the provider prefix to match ModelRegistry format.

        Args:
            model_id: LiteLLM model identifier

        Returns:
            Normalized model ID for registry lookup
        """
        # Common provider prefixes to strip
        prefixes = [
            "openai/",
            "anthropic/",
            "google/",
            "azure/",
            "bedrock/",
            "vertex_ai/",
            "ollama/",
            "huggingface/",
        ]

        for prefix in prefixes:
            if model_id.startswith(prefix):
                return model_id[len(prefix) :]

        return model_id


async def start_model_sync_scheduler() -> asyncio.Task:
    """
    Start background model sync scheduler.

    Creates a background task that periodically syncs model pricing
    from LiteLLM to the ModelRegistry.

    The scheduler:
    - Waits 60 seconds before first sync (avoid startup load)
    - Runs sync every 24 hours
    - Respects the enable_litellm_model_sync feature flag
    - Logs errors but does not crash

    Returns:
        The background asyncio.Task for lifecycle management.

    Example:
        >>> task = await start_model_sync_scheduler()
        >>> # ... application runs ...
        >>> task.cancel()  # Shutdown
    """
    return asyncio.create_task(
        _model_sync_loop(),
        name="litellm_model_sync_scheduler",
    )


async def _model_sync_loop() -> None:
    """
    Background loop for model sync.

    Runs indefinitely, syncing model pricing from LiteLLM every 24 hours.
    Initial delay of 60 seconds to avoid startup load.
    """
    # Initial delay to avoid startup load
    await asyncio.sleep(INITIAL_DELAY_SECONDS)

    sync = LiteLLMModelSync()

    while True:
        try:
            # Check feature flag before syncing
            if feature_flags.enable_litellm_model_sync:
                updated = sync.sync_pricing()
                if updated > 0:
                    logger.info(f"LiteLLM model sync: updated {updated} models")
                else:
                    logger.debug("LiteLLM model sync: no updates needed")
            else:
                logger.debug("LiteLLM model sync disabled (enable_litellm_model_sync=false)")

            await asyncio.sleep(SYNC_INTERVAL_SECONDS)

        except asyncio.CancelledError:
            logger.info("LiteLLM model sync scheduler stopped")
            raise
        except Exception as e:
            logger.error(f"LiteLLM model sync error: {e}")
            await asyncio.sleep(SYNC_INTERVAL_SECONDS)
