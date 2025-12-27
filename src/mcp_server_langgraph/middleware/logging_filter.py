"""
Logging filter middleware for reducing access log noise.

Filters out requests to noisy endpoints (health checks, metrics, static assets)
from application logging while still allowing full OTEL tracing.

Usage:
    # Enable quiet logging mode
    export QUIET_LOGS=true

    # Or call programmatically during startup
    from mcp_server_langgraph.middleware.logging_filter import setup_quiet_logging
    setup_quiet_logging()

Reference: Plan for log noise reduction in docker-compose.test.yml environment
"""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

# Paths to exclude from access logging (exact matches)
# These are high-frequency endpoints that create log noise
QUIET_PATHS: frozenset[str] = frozenset(
    {
        "/health",
        "/healthz",
        "/health/live",
        "/health/ready",
        "/metrics",
        "/ready",
        "/readyz",
        "/livez",
        "/favicon.ico",
    }
)

# Path prefixes to exclude from access logging
# Matches patterns like /health/*, /studio/assets/*, etc.
QUIET_PATH_PREFIXES: tuple[str, ...] = (
    "/health/",
    "/metrics/",
    "/studio/assets/",
    "/static/",
    "/fonts/",
    "/sounds/",
    "/studio/workbox",
    "/studio/sw.js",
)


class QuietPathsLoggingFilter(logging.Filter):
    """
    Logging filter that suppresses logs for noisy paths when QUIET_LOGS=true.

    This filter is applied to the uvicorn.access logger to reduce noise from:
    - Health check endpoints (/health, /health/live, /health/ready, etc.)
    - Metrics endpoints (/metrics)
    - Static assets (/studio/assets/*, /static/*, /fonts/*)
    - Service worker files (/studio/sw.js, /studio/workbox-*.js)

    Usage:
        # Add to uvicorn access logger
        uvicorn_logger = logging.getLogger("uvicorn.access")
        uvicorn_logger.addFilter(QuietPathsLoggingFilter())

    Environment Variables:
        QUIET_LOGS: Set to "true" to enable filtering (default: "false")
    """

    def __init__(self, name: str = "") -> None:
        super().__init__(name)
        self._quiet_logs_enabled: bool = os.getenv("QUIET_LOGS", "false").lower() in (
            "true",
            "1",
            "yes",
        )

    @property
    def quiet_logs_enabled(self) -> bool:
        """Check if quiet logs mode is enabled."""
        return self._quiet_logs_enabled

    def filter(self, record: logging.LogRecord) -> bool:
        """
        Filter log records based on path patterns.

        Returns:
            True to allow the log, False to suppress it.
        """
        if not self._quiet_logs_enabled:
            return True  # Allow all logs when quiet mode disabled

        # Get the log message for path matching
        try:
            message = record.getMessage()
        except Exception:
            return True  # Allow on error

        # Check exact path matches
        for path in QUIET_PATHS:
            # Match paths in various log formats:
            # - Uvicorn: '127.0.0.1:8000 - "GET /health HTTP/1.1" 200'
            # - Traefik JSON: {"RequestPath":"/health",...}
            if f'"{path}' in message or f" {path} " in message or f":{path}" in message:
                return False  # Suppress

        # Check prefix matches - suppress if any prefix is found in message
        return all(prefix not in message for prefix in QUIET_PATH_PREFIXES)


def setup_quiet_logging() -> None:
    """
    Configure quiet logging for uvicorn and application loggers.

    This function applies the QuietPathsLoggingFilter to relevant loggers
    to reduce noise from health checks, metrics, and static asset requests.

    Call this during application startup to enable filtering.

    Example:
        from mcp_server_langgraph.middleware.logging_filter import setup_quiet_logging

        # In your FastAPI app startup
        @app.on_event("startup")
        async def startup():
            setup_quiet_logging()
    """
    quiet_enabled = os.getenv("QUIET_LOGS", "false").lower() in ("true", "1", "yes")

    if not quiet_enabled:
        return

    # Apply filter to uvicorn access logger
    uvicorn_access = logging.getLogger("uvicorn.access")
    if not any(isinstance(f, QuietPathsLoggingFilter) for f in uvicorn_access.filters):
        uvicorn_access.addFilter(QuietPathsLoggingFilter())

    # Apply filter to main app logger
    app_logger = logging.getLogger("mcp_server_langgraph")
    if not any(isinstance(f, QuietPathsLoggingFilter) for f in app_logger.filters):
        app_logger.addFilter(QuietPathsLoggingFilter())

    # Apply filter to starlette access logger (if used)
    starlette_logger = logging.getLogger("starlette.access")
    if not any(isinstance(f, QuietPathsLoggingFilter) for f in starlette_logger.filters):
        starlette_logger.addFilter(QuietPathsLoggingFilter())
