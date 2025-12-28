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

from typing import Any

import litellm

from mcp_server_langgraph.core.feature_flags import feature_flags
from mcp_server_langgraph.observability.telemetry import logger

# Flag to track if OTEL has been configured (idempotency)
_otel_configured = False


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
) -> dict[str, Any]:
    """
    Build metadata dict for LiteLLM OTEL span attributes.

    LiteLLM's OTEL callback prefixes these with 'metadata.' on spans,
    enabling filtering and grouping by session, workflow, etc.

    Args:
        session_id: Session identifier for multi-turn conversations
        workflow_id: Workflow identifier for cost attribution
        orchestrator_id: Orchestrator/Agent identifier
        user_id: User identifier for per-user cost tracking
        request_id: Unique request ID for tracing
        feature: Feature tag (e.g., "chat", "summarization", "verification")

    Returns:
        Dictionary of metadata to pass to LiteLLM's metadata parameter.
        None values are omitted.

    Example:
        metadata = build_otel_metadata(
            session_id="sess-123",
            workflow_id="wf-456",
        )
        response = await litellm.acompletion(..., metadata=metadata)

        # On OTEL span, these appear as:
        # metadata.session_id = "sess-123"
        # metadata.workflow_id = "wf-456"
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

    return metadata


def reset_otel_configuration() -> None:
    """
    Reset OTEL configuration flag (for testing only).

    This allows re-running configure_litellm_otel() in tests.
    """
    global _otel_configured
    _otel_configured = False
