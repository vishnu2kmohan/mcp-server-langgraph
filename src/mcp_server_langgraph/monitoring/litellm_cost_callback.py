"""
LiteLLM callback for automatic cost tracking.

This module provides a CustomLogger callback that automatically records costs
on every LLM call using LiteLLM's kwargs["response_cost"] as the authoritative
source for cost calculation.

Benefits:
- LiteLLM maintains live pricing for 100+ models
- Automatic pricing updates without code changes
- Handles special pricing (caching, >200k context)
- Single source of truth for cost calculation

Reference:
- https://docs.litellm.ai/docs/completion/token_usage
- https://docs.litellm.ai/docs/proxy/cost_tracking

Phase 1: LiteLLM Cost Integration via Custom Callback
"""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from litellm.integrations.custom_logger import CustomLogger


class CostTrackingCallback(CustomLogger):
    """
    LiteLLM callback that automatically records costs on every LLM call.

    LiteLLM passes kwargs["response_cost"] to success callbacks -
    we use this as the authoritative cost source instead of maintaining
    our own pricing table.

    Usage:
        import litellm
        from mcp_server_langgraph.monitoring.litellm_cost_callback import CostTrackingCallback

        # Register on startup
        litellm.callbacks = [CostTrackingCallback()]

        # Pass metadata in completion calls
        response = await litellm.acompletion(
            model="claude-sonnet-4-5-20250929",
            messages=[{"role": "user", "content": "Hello"}],
            metadata={
                "user_id": "user:alice",
                "session_id": "session-123",
                "organization_id": "organization:acme",
                "project_id": "project:backend",
                "team_id": "team:platform",
            }
        )
    """

    async def async_log_success_event(
        self,
        kwargs: dict[str, Any],
        response_obj: Any,
        start_time: datetime,
        end_time: datetime,
    ) -> None:
        """
        Record cost after successful LLM call.

        Args:
            kwargs: LiteLLM call kwargs including:
                - response_cost: Calculated cost from LiteLLM (authoritative)
                - model: Model name
                - custom_llm_provider: Provider name
                - litellm_params.metadata: User-provided metadata
            response_obj: LLM response with usage data
            start_time: Call start time
            end_time: Call end time
        """
        # Import here to avoid circular imports
        from mcp_server_langgraph.monitoring.cost_tracker import get_cost_collector

        # Extract usage data - required for recording
        usage = getattr(response_obj, "usage", None)
        if not usage:
            # No usage data - can't record meaningful cost
            return

        # Get LiteLLM's calculated cost (authoritative source)
        response_cost = kwargs.get("response_cost", 0)

        # Extract metadata from litellm_params
        litellm_params = kwargs.get("litellm_params", {})
        metadata = litellm_params.get("metadata", {})

        # Get collector and record usage
        collector = get_cost_collector()
        await collector.record_usage(
            timestamp=datetime.now(UTC),
            # User context
            user_id=metadata.get("user_id", "anonymous"),
            session_id=metadata.get("session_id", "unknown"),
            # Model info from kwargs
            model=kwargs.get("model", "unknown"),
            provider=kwargs.get("custom_llm_provider", "unknown"),
            # Token counts from usage
            prompt_tokens=usage.prompt_tokens,
            completion_tokens=usage.completion_tokens,
            # Cost from LiteLLM (authoritative)
            estimated_cost_usd=Decimal(str(response_cost)),
            feature=metadata.get("feature", "chat"),
            # Organizational context for cost attribution
            organization_id=metadata.get("organization_id"),
            project_id=metadata.get("project_id"),
            team_id=metadata.get("team_id"),
            # Tracing context
            trace_id=metadata.get("trace_id"),
            workflow_id=metadata.get("workflow_id"),
            # Custom allocation tags for flexible cost attribution
            allocation_tags=metadata.get("allocation_tags"),
        )


def get_model_cost_from_litellm(
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
) -> Decimal:
    """
    Calculate cost for a model using LiteLLM's pricing data.

    This function is used as a fallback when CostTrackingCallback doesn't fire
    (e.g., direct API calls not through LiteLLM, testing scenarios).

    Args:
        model: Model name (e.g., "gpt-4", "claude-3-5-sonnet-20241022")
        prompt_tokens: Number of input/prompt tokens
        completion_tokens: Number of output/completion tokens

    Returns:
        Total cost in USD as Decimal. Returns Decimal("0") for unknown models.

    Example:
        >>> cost = get_model_cost_from_litellm(
        ...     model="gpt-4",
        ...     prompt_tokens=1000,
        ...     completion_tokens=500,
        ... )
        >>> print(f"${cost}")
        $0.075
    """
    if prompt_tokens == 0 and completion_tokens == 0:
        return Decimal("0")

    try:
        # Use LiteLLM's cost_per_token function
        # This returns (prompt_cost, completion_cost) - the TOTAL cost for the tokens
        from litellm import cost_per_token

        prompt_cost, completion_cost = cost_per_token(
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )

        # cost_per_token already returns the total cost for the given tokens
        total_cost = prompt_cost + completion_cost

        return Decimal(str(total_cost))

    except Exception:
        # Unknown model or LiteLLM error - return 0 instead of raising
        # This maintains backward compatibility and prevents failures
        return Decimal("0")


def configure_cost_tracking() -> None:
    """
    Configure LiteLLM to use CostTrackingCallback for automatic cost tracking.

    This function is idempotent - calling it multiple times is safe.

    Usage:
        # Call during application startup
        from mcp_server_langgraph.monitoring.litellm_cost_callback import configure_cost_tracking
        configure_cost_tracking()
    """
    import litellm

    # Check if callback is already registered
    callback_type = CostTrackingCallback
    for callback in litellm.callbacks:
        if isinstance(callback, callback_type):
            # Already registered
            return

    # Register the callback
    litellm.callbacks.append(CostTrackingCallback())
