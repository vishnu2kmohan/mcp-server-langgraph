"""
LiteLLM OpenTelemetry Integration

Enables LiteLLM's native OTEL callback for enhanced distributed tracing
of LLM operations. This provides:

1. Automatic span creation for all LiteLLM calls
2. gen_ai.client.token.cost histogram for cost observability
3. gen_ai.token.usage histogram with token breakdown
4. Custom metadata propagation (session_id, workflow_id, etc.)

Usage:
    # At application startup
    from mcp_server_langgraph.llm.otel_integration import configure_litellm_otel
    configure_litellm_otel()

    # When making LLM calls
    from mcp_server_langgraph.llm.otel_integration import build_otel_metadata
    metadata = build_otel_metadata(
        session_id="sess-123",
        workflow_id="wf-456",
        user_id="user-789",
    )
    response = await litellm.acompletion(..., metadata=metadata)

References:
    - LiteLLM OTEL: https://docs.litellm.ai/docs/observability/opentelemetry_integration
    - GenAI Semantic Conventions: https://opentelemetry.io/docs/specs/semconv/gen-ai/
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import litellm

if TYPE_CHECKING:
    from mcp_server_langgraph.monitoring.litellm_cost_callback import CostTrackingCallback

from mcp_server_langgraph.core.feature_flags import feature_flags
from mcp_server_langgraph.observability.telemetry import logger

# Flag to track if OTEL has been configured (idempotency)
_otel_configured = False
_cost_tracking_configured = False

# Store reference to the cost tracking callback instance
_cost_tracking_callback: CostTrackingCallback | None = None


def configure_litellm_otel() -> None:
    """
    Configure LiteLLM to use the native OpenTelemetry callback.

    This function:
    1. Adds 'otel' to litellm.callbacks (if not already present)
    2. Configures drop_params=True to handle unsupported params gracefully
    3. Respects existing TracerProvider (doesn't override)

    Should be called once at application startup.

    The OTEL callback provides:
    - gen_ai.client.token.cost histogram (cost in USD)
    - gen_ai.token.usage histogram (input/output tokens)
    - Span attributes: gen_ai.operation.name, gen_ai.system, gen_ai.request.model

    Note:
        Controlled by feature_flags.enable_litellm_otel flag.
    """
    global _otel_configured

    # Check feature flag
    if not feature_flags.enable_litellm_otel:
        logger.debug("LiteLLM OTEL integration disabled by feature flag")
        return

    # Ensure idempotency
    if _otel_configured:
        logger.debug("LiteLLM OTEL already configured, skipping")
        return

    # Add OTEL callback if not already present
    if "otel" not in litellm.callbacks:
        litellm.callbacks.append("otel")
        logger.info(
            "Enabled LiteLLM native OTEL callback",
            extra={"callbacks": litellm.callbacks},
        )

    # Configure drop_params to handle provider-specific params gracefully
    # This prevents errors when OTEL callback adds extra params
    litellm.drop_params = True

    _otel_configured = True

    logger.info(
        "LiteLLM OTEL integration configured successfully",
        extra={
            "callbacks": litellm.callbacks,
            "drop_params": litellm.drop_params,
        },
    )


def build_otel_metadata(
    *,
    session_id: str | None = None,
    workflow_id: str | None = None,
    orchestrator_id: str | None = None,
    user_id: str | None = None,
    request_id: str | None = None,
    feature: str | None = None,
    # Organizational hierarchy for cost attribution
    organization_id: str | None = None,
    project_id: str | None = None,
    team_id: str | None = None,
    # Tracing
    trace_id: str | None = None,
) -> dict[str, Any]:
    """
    Build metadata dict for LiteLLM span attributes and cost tracking.

    This metadata is used by:
    - OTEL callback: Prefixes with 'metadata.' on spans for filtering
    - CostTrackingCallback: Extracts org context for cost attribution

    Args:
        session_id: Session identifier for multi-turn conversations
        workflow_id: Workflow identifier for cost attribution
        orchestrator_id: Orchestrator/Agent identifier
        user_id: User identifier for per-user cost tracking
        request_id: Unique request ID for tracing
        feature: Feature tag (e.g., "chat", "summarization", "verification")
        organization_id: Organization ID for multi-tenant cost attribution
        project_id: Project ID for project-level cost breakdown
        team_id: Team/group ID for team-level cost attribution
        trace_id: Trace ID for distributed tracing correlation

    Returns:
        Dictionary of metadata to pass to LiteLLM's metadata parameter.
        None values are omitted.

    Example:
        metadata = build_otel_metadata(
            session_id="sess-123",
            workflow_id="wf-456",
            organization_id="organization:acme",
            project_id="project:backend",
            team_id="team:platform",
        )
        response = await litellm.acompletion(..., metadata=metadata)

        # CostTrackingCallback will extract org fields for cost attribution
        # OTEL span will include metadata.session_id, metadata.workflow_id, etc.
    """
    metadata: dict[str, Any] = {}

    if session_id is not None:
        metadata["session_id"] = session_id

    if workflow_id is not None:
        metadata["workflow_id"] = workflow_id

    if orchestrator_id is not None:
        metadata["orchestrator_id"] = orchestrator_id

    if user_id is not None:
        metadata["user_id"] = user_id

    if request_id is not None:
        metadata["request_id"] = request_id

    if feature is not None:
        metadata["feature"] = feature

    # Organizational hierarchy
    if organization_id is not None:
        metadata["organization_id"] = organization_id

    if project_id is not None:
        metadata["project_id"] = project_id

    if team_id is not None:
        metadata["team_id"] = team_id

    # Tracing
    if trace_id is not None:
        metadata["trace_id"] = trace_id

    return metadata


def reset_otel_configuration() -> None:
    """
    Reset OTEL configuration flag (for testing only).

    This allows re-running configure_litellm_otel() in tests.
    """
    global _otel_configured
    _otel_configured = False


def configure_litellm_cost_tracking() -> None:
    """
    Configure LiteLLM to use the CostTrackingCallback for automatic cost recording.

    This function:
    1. Creates a CostTrackingCallback instance
    2. Adds it to litellm.callbacks if not already present
    3. Uses LiteLLM's response_cost as the authoritative cost source

    Should be called once at application startup.

    The callback provides:
    - Automatic cost recording for all LLM calls
    - Organizational cost attribution (org, project, team)
    - Integration with the cost collector singleton

    Note:
        Unlike OTEL, this is not controlled by a feature flag as cost tracking
        is a core requirement for operational visibility.
    """
    global _cost_tracking_configured, _cost_tracking_callback

    # Ensure idempotency
    if _cost_tracking_configured:
        logger.debug("LiteLLM cost tracking already configured, skipping")
        return

    # Import here to avoid circular imports
    from mcp_server_langgraph.monitoring.litellm_cost_callback import (
        CostTrackingCallback as CostTrackingCallbackClass,
    )

    # Check if we already have a CostTrackingCallback in callbacks
    for callback in litellm.callbacks:
        if isinstance(callback, CostTrackingCallbackClass):
            logger.debug("CostTrackingCallback already present in litellm.callbacks")
            _cost_tracking_configured = True
            _cost_tracking_callback = callback
            return

    # Create and add callback
    _cost_tracking_callback = CostTrackingCallbackClass()
    litellm.callbacks.append(_cost_tracking_callback)

    _cost_tracking_configured = True

    logger.info(
        "LiteLLM cost tracking callback configured",
        extra={
            "callbacks_count": len(litellm.callbacks),
        },
    )


def reset_cost_tracking_configuration() -> None:
    """
    Reset cost tracking configuration (for testing only).

    This allows re-running configure_litellm_cost_tracking() in tests.
    Also removes the callback from litellm.callbacks if present.
    """
    global _cost_tracking_configured, _cost_tracking_callback

    # Import here to avoid circular imports
    from mcp_server_langgraph.monitoring.litellm_cost_callback import (
        CostTrackingCallback as CostTrackingCallbackClass,
    )

    # Remove any CostTrackingCallback instances from litellm.callbacks
    litellm.callbacks = [cb for cb in litellm.callbacks if not isinstance(cb, CostTrackingCallbackClass)]

    _cost_tracking_configured = False
    _cost_tracking_callback = None
