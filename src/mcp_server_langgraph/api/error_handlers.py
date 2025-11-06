"""
FastAPI exception handlers for custom exceptions.

Provides structured error responses with proper HTTP status codes,
trace IDs, and user-friendly messages.

See ADR-0029 for design rationale.
"""

import logging
from typing import Any, Dict, Optional

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from mcp_server_langgraph.core.exceptions import MCPServerException

logger = logging.getLogger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    """
    Register custom exception handlers with FastAPI application.

    Args:
        app: FastAPI application instance

    Usage:
        from fastapi import FastAPI
        from mcp_server_langgraph.api.error_handlers import register_exception_handlers

        app = FastAPI()
        register_exception_handlers(app)
    """

    @app.exception_handler(MCPServerException)
    async def mcp_exception_handler(request: Request, exc: MCPServerException) -> JSONResponse:
        """
        Handle MCP server exceptions.

        Provides:
        - Structured JSON error response
        - Trace ID in response headers
        - Metrics emission
        - Detailed logging with context
        """
        # Log with full context
        logger.error(
            f"Exception: {exc.error_code}",
            exc_info=True,
            extra={
                "error_code": exc.error_code,
                "status_code": exc.status_code,
                "category": exc.category.value,
                "retry_policy": exc.retry_policy.value,
                "trace_id": exc.trace_id,
                "metadata": exc.metadata,
                "user_message": exc.user_message,
                "request_method": request.method,
                "request_url": str(request.url),
            },
        )

        # Record metric
        try:
            from mcp_server_langgraph.observability.telemetry import error_counter

            error_counter.add(
                1,
                attributes={
                    "error_code": exc.error_code,
                    "status_code": str(exc.status_code),
                    "category": exc.category.value,
                    "retry_policy": exc.retry_policy.value,
                },
            )
        except Exception as metric_error:
            logger.warning(f"Failed to record error metric: {metric_error}")

        # Build response headers
        headers = {}
        if exc.trace_id:
            headers["X-Trace-ID"] = exc.trace_id

        # Add Retry-After header for rate limit errors
        if exc.status_code == 429:
            retry_after = exc.metadata.get("retry_after", 60)
            headers["Retry-After"] = str(retry_after)

        # Return JSON response
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.to_dict(),
            headers=headers,
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """
        Handle unexpected exceptions.

        Wraps generic exceptions in InternalServerError for consistent handling.
        """
        # Log unexpected error
        logger.error(
            f"Unexpected exception: {type(exc).__name__}",
            exc_info=True,
            extra={
                "exception_type": type(exc).__name__,
                "request_method": request.method,
                "request_url": str(request.url),
            },
        )

        # Wrap in InternalServerError
        from mcp_server_langgraph.core.exceptions import UnexpectedError

        wrapped_exc = UnexpectedError(
            message=str(exc),
            metadata={
                "original_exception": type(exc).__name__,
                "request_method": request.method,
                "request_path": str(request.url.path),
            },
            cause=exc,
        )

        return await mcp_exception_handler(request, wrapped_exc)

    logger.info("Exception handlers registered")


def create_error_response(
    error_code: str,
    message: str,
    status_code: int = 500,
    metadata: Optional[Dict[str, Any]] = None,
    trace_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create a standardized error response dictionary.

    Args:
        error_code: Machine-readable error code
        message: Human-readable error message
        status_code: HTTP status code
        metadata: Additional error context
        trace_id: OpenTelemetry trace ID

    Returns:
        Standardized error response dictionary

    Usage:
        return create_error_response(
            error_code="auth.token_expired",
            message="Your session has expired",
            status_code=401,
            metadata={"user_id": "user_123"},
            trace_id="abc123def456"
        )
    """
    return {
        "error": {
            "code": error_code,
            "message": message,
            "status_code": status_code,
            "metadata": metadata or {},
            "trace_id": trace_id,
        }
    }
