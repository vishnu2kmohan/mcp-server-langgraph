"""
HTTP metrics middleware for FastAPI.

Provides Prometheus metrics for HTTP requests:
- http_requests_total (Counter) - Total requests by method, endpoint, status
- http_request_duration_seconds (Histogram) - Request duration by method, endpoint

This middleware integrates with the LGTM observability stack (Grafana/Mimir).
See ADR-0028 for design rationale.
"""

import time
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, cast

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

if TYPE_CHECKING:
    from starlette.types import ASGIApp

# Lazy load prometheus_client to handle missing dependency gracefully
_prometheus_available: bool | None = None
_http_requests_total: Any = None
_http_request_duration_seconds: Any = None


def _init_metrics() -> bool:
    """Initialize Prometheus metrics lazily."""
    global _prometheus_available, _http_requests_total, _http_request_duration_seconds

    if _prometheus_available is not None:
        return _prometheus_available

    try:
        from prometheus_client import Counter, Histogram

        _http_requests_total = Counter(
            "http_requests_total",
            "Total number of HTTP requests",
            ["method", "endpoint", "status"],
        )

        _http_request_duration_seconds = Histogram(
            "http_request_duration_seconds",
            "HTTP request duration in seconds",
            ["method", "endpoint"],
            buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
        )

        _prometheus_available = True
        return True

    except ImportError:
        _prometheus_available = False
        return False


# Endpoints to exclude from metrics
EXCLUDED_PATHS = frozenset(
    {
        "/health",
        "/healthz",
        "/ready",
        "/readyz",
        "/live",
        "/livez",
        "/metrics",
        "/metrics/",
    }
)


def normalize_path(request: Request) -> str:
    """
    Normalize request path to prevent high cardinality in metrics.

    Path parameters are replaced with their template names:
    - /users/123 -> /users/{user_id}
    - /items/abc/details -> /items/{item_id}/details

    Args:
        request: The incoming request

    Returns:
        Normalized path string
    """
    # Try to get the matched route template
    if hasattr(request, "scope") and "route" in request.scope:
        route = request.scope["route"]
        if hasattr(route, "path"):
            return route.path  # type: ignore[no-any-return]

    # Fallback to raw path (should rarely happen with FastAPI)
    return request.url.path


def should_skip_metrics(path: str) -> bool:
    """
    Check if metrics should be skipped for this path.

    Args:
        path: Request path

    Returns:
        True if metrics should be skipped
    """
    # Check exact matches
    if path in EXCLUDED_PATHS:
        return True

    # Check prefix matches for common patterns
    return path.startswith("/health") or path.startswith("/metrics")


class MetricsMiddleware(BaseHTTPMiddleware):
    """
    HTTP metrics middleware for FastAPI.

    Records:
    - http_requests_total: Counter with labels (method, endpoint, status)
    - http_request_duration_seconds: Histogram with labels (method, endpoint)

    Excludes health and metrics endpoints to prevent noise.
    Normalizes path parameters to prevent high cardinality.
    """

    def __init__(self, app: "ASGIApp") -> None:
        """Initialize the metrics middleware."""
        super().__init__(app)
        self._metrics_available = _init_metrics()

    async def dispatch(self, request: Request, call_next: Callable) -> Response:  # type: ignore[type-arg]
        """
        Process request and record metrics.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware/handler in chain

        Returns:
            HTTP response
        """
        path = request.url.path

        # Skip metrics for excluded paths
        if should_skip_metrics(path):
            return cast(Response, await call_next(request))

        # Record start time
        start_time = time.perf_counter()

        # Process request and handle exceptions
        status_code = 500  # Default to 500 for unhandled exceptions
        response: Response | None = None

        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception:
            # Let the exception propagate, but record metrics first
            duration = time.perf_counter() - start_time
            self._record_metrics(request, status_code, duration)
            raise

        # Calculate duration
        duration = time.perf_counter() - start_time

        # Record metrics for successful response handling
        self._record_metrics(request, status_code, duration)

        return response

    def _record_metrics(self, request: Request, status_code: int, duration: float) -> None:
        """
        Record request metrics.

        Args:
            request: The HTTP request
            status_code: Response status code
            duration: Request duration in seconds
        """
        if not self._metrics_available:
            return

        method = request.method
        endpoint = normalize_path(request)
        status = str(status_code)

        try:
            # Increment request counter - use module-level reference
            counter = http_requests_total
            if counter is not None:
                counter.labels(
                    method=method,
                    endpoint=endpoint,
                    status=status,
                ).inc()

            # Record duration histogram - use module-level reference
            histogram = http_request_duration_seconds
            if histogram is not None:
                histogram.labels(
                    method=method,
                    endpoint=endpoint,
                ).observe(duration)

        except Exception:
            # Don't let metrics failures break the request
            pass


# Module-level references for patching in tests
# These are set when the module loads and can be patched by tests
http_requests_total: Any = None
http_request_duration_seconds: Any = None


def _ensure_metrics_initialized() -> None:
    """Ensure metrics are initialized and module-level references are set."""
    global http_requests_total, http_request_duration_seconds

    if _init_metrics():
        http_requests_total = _http_requests_total
        http_request_duration_seconds = _http_request_duration_seconds


# Initialize on module load
_ensure_metrics_initialized()
