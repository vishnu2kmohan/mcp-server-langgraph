"""
Prompt Telemetry and Metrics (Phase 7 - ADR-0089).

Provides lightweight, non-blocking telemetry for prompt usage:
- Prometheus metrics for prompt version tracking
- Metadata retrieval for prompt name, version, and content hash
- Context manager for easy integration with LLM calls

Performance requirements:
- Metadata injection < 1ms overhead
- Non-blocking metrics recording
- Graceful degradation without prometheus_client
"""

from __future__ import annotations

import hashlib
import logging
from contextlib import asynccontextmanager, contextmanager
from typing import TYPE_CHECKING, Any, AsyncGenerator, Generator

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# =============================================================================
# BOUNDED LABEL CONSTANTS
# =============================================================================
# These constants prevent cardinality explosion in Prometheus metrics.

BOUNDED_PROMPT_NAMES: frozenset[str] = frozenset(
    {
        # Core prompts
        "router",
        "response",
        "verification",
        "orchestration_router",
        # AI UX prompts
        "error_analysis",
        "empty_state",
        "persona_analysis",
        "disclosure_analysis",
        "nudge_recommendation",
        "onboarding_personalization",
        "metrics_insights",
        "session_summarize",
        "session_group",
        "session_similarity",
        "trace_summarize",
        "trace_anomalies",
        "canvas_artifact_type",
        "canvas_code_analysis",
        "canvas_diff_explain",
        "diagram_analyze",
        "diagram_to_code",
        # GenUI prompts
        "genui_widget",
        "genui_render",
        "genui_form",
        # Workflow prompts
        "workflow_generator",
        # Plan editor prompts
        "plan_validation",
        "template_suggestion",
        # Fallback
        "other",
    }
)

BOUNDED_VERSIONS: frozenset[str] = frozenset(
    {
        "v1",
        "v2",
        "v3",
        "latest",
        "other",
    }
)


# =============================================================================
# LAZY-LOADED PROMETHEUS METRICS
# =============================================================================

_metrics_available: bool | None = None
_prompt_usage_total: Any = None


def _init_prompt_metrics() -> bool:
    """Initialize prompt metrics lazily."""
    global _metrics_available
    global _prompt_usage_total

    if _metrics_available is not None:
        return _metrics_available

    try:
        from prometheus_client import Counter

        _prompt_usage_total = Counter(
            "prompt_usage_total",
            "Total prompt invocations by name and version",
            ["prompt_name", "prompt_version"],
        )

        _metrics_available = True
        logger.debug("Prompt metrics initialized successfully")
        return True

    except ImportError:
        _metrics_available = False
        logger.debug("prometheus_client not available, prompt metrics disabled")
        return False


# Initialize on module load
_init_prompt_metrics()


# =============================================================================
# HASH COMPUTATION
# =============================================================================


def _compute_prompt_hash(content: str) -> str:
    """
    Compute 8-character truncated MD5 hash of prompt content.

    Args:
        content: Prompt content string

    Returns:
        8-character hexadecimal hash
    """
    return hashlib.md5(content.encode(), usedforsecurity=False).hexdigest()[:8]


# =============================================================================
# METADATA RETRIEVAL
# =============================================================================


def get_prompt_metadata(prompt_name: str) -> dict[str, str]:
    """
    Get telemetry metadata for a prompt.

    Args:
        prompt_name: Name of the registered prompt

    Returns:
        Dictionary with prompt_name, prompt_version, and prompt_hash

    Raises:
        ValueError: If prompt_name is not registered
    """
    # Import here to avoid circular dependency
    from mcp_server_langgraph.core.prompts import (
        _PROMPT_VERSIONS,
        get_prompt,
        get_prompt_version,
    )

    if prompt_name not in _PROMPT_VERSIONS:
        available = list(_PROMPT_VERSIONS.keys())
        msg = f"Unknown prompt: {prompt_name}. Available: {available}"
        raise ValueError(msg)

    version = get_prompt_version(prompt_name)
    content = get_prompt(prompt_name, version)
    content_hash = _compute_prompt_hash(content)

    return {
        "prompt_name": prompt_name,
        "prompt_version": version,
        "prompt_hash": content_hash,
    }


# =============================================================================
# USAGE RECORDING
# =============================================================================


def _normalize_prompt_name(prompt_name: str) -> str:
    """Normalize prompt name to bounded value."""
    if prompt_name in BOUNDED_PROMPT_NAMES:
        return prompt_name
    return "other"


def _normalize_version(version: str) -> str:
    """Normalize version to bounded value."""
    if version in BOUNDED_VERSIONS:
        return version
    return "other"


def record_prompt_usage(
    prompt_name: str,
    prompt_version: str,
    model: str | None = None,
    operation: str | None = None,
) -> None:
    """
    Record prompt usage in Prometheus metrics.

    This is a fire-and-forget operation that never raises exceptions.

    Args:
        prompt_name: Name of the prompt being used
        prompt_version: Version of the prompt (e.g., "v1", "latest")
        model: Optional model name (for future use)
        operation: Optional operation type (for future use)
    """
    if not _metrics_available:
        return

    try:
        if _prompt_usage_total:
            normalized_name = _normalize_prompt_name(prompt_name)
            normalized_version = _normalize_version(prompt_version)
            _prompt_usage_total.labels(
                prompt_name=normalized_name,
                prompt_version=normalized_version,
            ).inc()
    except Exception as e:
        # Fire-and-forget: never let metrics recording affect application
        logger.debug("Failed to record prompt usage: %s", e)


# =============================================================================
# SPAN ATTRIBUTES
# =============================================================================


def attach_prompt_to_span(span: Any | None, prompt_name: str) -> None:
    """
    Attach prompt metadata to an OpenTelemetry span.

    This is the recommended integration point for LLM call sites.
    Call this within the span context after creating the span.

    Args:
        span: OpenTelemetry span (or None for no-op)
        prompt_name: Name of the prompt being used

    Example:
        with tracer.start_as_current_span("llm.ainvoke") as span:
            attach_prompt_to_span(span, "orchestration_router")
            response = await llm.ainvoke(messages)
    """
    if span is None:
        return

    try:
        metadata = get_prompt_metadata(prompt_name)
        span.set_attribute("prompt.name", metadata["prompt_name"])
        span.set_attribute("prompt.version", metadata["prompt_version"])
        span.set_attribute("prompt.hash", metadata["prompt_hash"])
    except ValueError:
        # Unknown prompt - set minimal attributes
        span.set_attribute("prompt.name", prompt_name)
        span.set_attribute("prompt.version", "unknown")
        span.set_attribute("prompt.hash", "unknown")
    except Exception as e:
        # Never let telemetry affect application
        logger.debug("Failed to attach prompt metadata to span: %s", e)


# =============================================================================
# CONTEXT MANAGER
# =============================================================================


@contextmanager
def prompt_telemetry_context(
    prompt_name: str,
    prompt_version: str | None = None,
) -> Generator[dict[str, str], None, None]:
    """
    Context manager for prompt telemetry.

    Provides metadata on entry and records usage on exit.
    Lightweight and non-blocking (< 1ms overhead).

    Args:
        prompt_name: Name of the prompt being used
        prompt_version: Optional version override (defaults to current version)

    Yields:
        Dictionary with prompt_name, prompt_version, and prompt_hash

    Example:
        with prompt_telemetry_context("orchestration_router") as ctx:
            response = await llm.complete(prompt, metadata=ctx)
    """
    # Import here to avoid circular dependency
    from mcp_server_langgraph.core.prompts import get_prompt_version

    try:
        # Get version if not provided
        if prompt_version is None:
            prompt_version = get_prompt_version(prompt_name)

        # Get metadata
        metadata = get_prompt_metadata(prompt_name)

        yield metadata

    except ValueError:
        # Unknown prompt - yield minimal metadata
        metadata = {
            "prompt_name": prompt_name,
            "prompt_version": prompt_version or "unknown",
            "prompt_hash": "unknown",
        }
        yield metadata

    finally:
        # Record usage on exit (fire-and-forget)
        record_prompt_usage(
            prompt_name=prompt_name,
            prompt_version=prompt_version or "unknown",
        )


@asynccontextmanager
async def async_prompt_telemetry_context(
    prompt_name: str,
    prompt_version: str | None = None,
    span: Any | None = None,
) -> AsyncGenerator[dict[str, str], None]:
    """
    Async context manager for prompt telemetry.

    Provides metadata on entry and records usage on exit.
    Designed for async LLM calls with optional span attachment.
    Lightweight and non-blocking (< 1ms overhead).

    Args:
        prompt_name: Name of the prompt being used
        prompt_version: Optional version override (defaults to current version)
        span: Optional OpenTelemetry span to attach metadata to

    Yields:
        Dictionary with prompt_name, prompt_version, and prompt_hash

    Example:
        async with async_prompt_telemetry_context("orchestration_router", span=span) as ctx:
            response = await llm.ainvoke(messages)
    """
    # Import here to avoid circular dependency
    from mcp_server_langgraph.core.prompts import get_prompt_version

    try:
        # Get version if not provided
        if prompt_version is None:
            try:
                prompt_version = get_prompt_version(prompt_name)
            except ValueError:
                prompt_version = "unknown"

        # Get metadata
        try:
            metadata = get_prompt_metadata(prompt_name)
        except ValueError:
            metadata = {
                "prompt_name": prompt_name,
                "prompt_version": prompt_version,
                "prompt_hash": "unknown",
            }

        # Attach to span if provided
        if span is not None:
            attach_prompt_to_span(span, prompt_name)

        yield metadata

    finally:
        # Record usage on exit (fire-and-forget)
        record_prompt_usage(
            prompt_name=prompt_name,
            prompt_version=prompt_version or "unknown",
        )
