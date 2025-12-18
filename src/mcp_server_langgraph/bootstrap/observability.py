"""
Observability Bootstrap Module.

Initializes logging, tracing, and metrics for the application.
This is a SYNC initialization that must run FIRST before any logging.

Per OpenAI Codex Finding #3: Observability must be initialized before
logger is used, or RuntimeError will occur.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from mcp_server_langgraph.core.config import Settings


@dataclass
class TelemetryState:
    """
    Telemetry state after observability initialization.

    Holds references to the logger and any tracing/metrics state.
    """

    logger: Any = None
    initialized: bool = False


def init_observability(settings: "Settings") -> TelemetryState:
    """
    Initialize observability components (logging, tracing, metrics).

    This MUST be called FIRST before any logging occurs.
    It is synchronous because OpenTelemetry SDK init is sync.

    Args:
        settings: Application settings

    Returns:
        TelemetryState with initialized logger

    Example:
        state = init_observability(settings)
        state.logger.info("Observability initialized")
    """
    from mcp_server_langgraph.observability.telemetry import init_observability as _init_observability, logger

    # Initialize OTEL SDK and configure logger
    _init_observability(settings)

    # Verify logger is usable (prevents regression of Codex Finding #3)
    try:
        logger.debug("Observability bootstrap complete")
    except RuntimeError as e:
        msg = f"Observability initialization failed: {e}"
        raise RuntimeError(msg) from e

    return TelemetryState(
        logger=logger,
        initialized=True,
    )
