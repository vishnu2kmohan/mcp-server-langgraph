"""
Fallback Alerting query client.

Implements AlertingQueryClient with automatic fallback between multiple backends.
Provides resilience when primary backends (e.g., Grafana) are unavailable.

Fallback Order (configurable):
    1. Grafana - Primary, uses Grafana Unified Alerting API
    2. Mimir - Fallback, uses Mimir's built-in Alertmanager
    3. Stub - Last resort, returns empty results

Health Check Caching:
    Health checks are cached with configurable TTL to avoid hammering
    backends on every request. Default TTL is 30 seconds.

Error Handling:
    When a backend raises an exception during an operation, it is marked
    as unhealthy in the cache and the next backend in the chain is tried.

Configuration:
    ALERTING_FALLBACK_ENABLED: Enable fallback chain (default: true)
    ALERTING_HEALTH_CHECK_INTERVAL: Health check cache TTL in seconds (default: 30)

Example:
    from mcp_server_langgraph.observability.query.backends.fallback import (
        FallbackAlertingClient,
    )
    from mcp_server_langgraph.observability.query.backends.grafana import (
        GrafanaAlertingClient,
    )
    from mcp_server_langgraph.observability.query.backends.mimir import (
        MimirAlertingClient,
    )

    client = FallbackAlertingClient(backends=[
        GrafanaAlertingClient(),
        MimirAlertingClient(),
    ])
    await client.initialize()
    alerts = await client.list_alerts()
"""

import logging
import time
from datetime import datetime

from prometheus_client import Counter

from mcp_server_langgraph.observability.query.interfaces import (
    Alert,
    AlertingQueryClient,
    AlertRule,
    AlertSearchResult,
    AlertSeverity,
    AlertState,
)

logger = logging.getLogger(__name__)

# =============================================================================
# Prometheus Metrics for Fallback Observability
# =============================================================================

ALERTING_FALLBACK_ACTIVATIONS = Counter(
    "alerting_fallback_activations_total",
    "Total number of alerting fallback activations",
    ["from_backend", "to_backend", "operation"],
)

ALERTING_BACKEND_ERRORS = Counter(
    "alerting_backend_errors_total",
    "Total number of alerting backend errors",
    ["backend", "operation", "error_type"],
)

ALERTING_HEALTH_CHECKS = Counter(
    "alerting_health_checks_total",
    "Total number of alerting health checks performed",
    ["backend", "result"],
)


class FallbackAlertingClient(AlertingQueryClient):
    """
    Fallback-aware alerting client.

    Tries backends in order, falling back to the next on failure.
    Uses health checks with caching to skip known-unhealthy backends.
    """

    def __init__(
        self,
        backends: list[AlertingQueryClient],
        health_check_ttl: int = 30,
    ) -> None:
        """
        Initialize fallback client.

        Args:
            backends: List of AlertingQueryClient instances in priority order
            health_check_ttl: Health check cache TTL in seconds (default: 30)
        """
        self._backends = backends
        self._health_check_ttl = health_check_ttl

        # Health cache: backend_id -> (is_healthy, timestamp)
        self._health_cache: dict[int, tuple[bool, float]] = {}

    async def initialize(self) -> None:
        """Initialize all backends."""
        for backend in self._backends:
            try:
                await backend.initialize()
            except Exception as e:
                backend_name = type(backend).__name__
                logger.warning(f"Failed to initialize backend {backend_name}: {e}")
                # Mark as unhealthy
                self._health_cache[id(backend)] = (False, time.time())

    async def close(self) -> None:
        """Close all backends."""
        for backend in self._backends:
            try:
                await backend.close()
            except Exception as e:
                backend_name = type(backend).__name__
                logger.warning(f"Failed to close backend {backend_name}: {e}")

    async def _is_backend_healthy(self, backend: AlertingQueryClient) -> bool:
        """
        Check if a backend is healthy, using cached results when valid.

        Args:
            backend: The backend to check

        Returns:
            True if backend is healthy, False otherwise
        """
        backend_id = id(backend)
        backend_name = type(backend).__name__
        now = time.time()

        # Check cache
        if backend_id in self._health_cache:
            is_healthy, timestamp = self._health_cache[backend_id]
            if now - timestamp < self._health_check_ttl:
                return is_healthy

        # Perform health check
        try:
            is_healthy = await backend.health_check()
            self._health_cache[backend_id] = (is_healthy, now)

            # Track health check result
            result = "healthy" if is_healthy else "unhealthy"
            ALERTING_HEALTH_CHECKS.labels(backend=backend_name, result=result).inc()

            return is_healthy
        except Exception as e:
            logger.debug(f"Health check failed for {backend_name}: {e}")
            self._health_cache[backend_id] = (False, now)

            # Track health check error as unhealthy
            ALERTING_HEALTH_CHECKS.labels(backend=backend_name, result="error").inc()

            return False

    def _mark_unhealthy(self, backend: AlertingQueryClient) -> None:
        """Mark a backend as unhealthy after an operation failure."""
        backend_id = id(backend)
        self._health_cache[backend_id] = (False, time.time())
        backend_name = type(backend).__name__
        logger.warning(f"Marked backend {backend_name} as unhealthy after failure")

    async def list_alerts(
        self,
        state: AlertState | None = None,
        severity: AlertSeverity | None = None,
        labels: dict[str, str] | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int = 100,
    ) -> AlertSearchResult:
        """
        List alerts using the first healthy backend.

        Falls back to subsequent backends on failure.
        """
        failed_backend: str | None = None

        for backend in self._backends:
            backend_name = type(backend).__name__

            if not await self._is_backend_healthy(backend):
                continue

            try:
                result = await backend.list_alerts(
                    state=state,
                    severity=severity,
                    labels=labels,
                    start=start,
                    end=end,
                    limit=limit,
                )

                # Track fallback if we succeeded after a failure
                if failed_backend is not None:
                    ALERTING_FALLBACK_ACTIVATIONS.labels(
                        from_backend=failed_backend,
                        to_backend=backend_name,
                        operation="list_alerts",
                    ).inc()

                return result
            except Exception as e:
                logger.warning(f"list_alerts failed for {backend_name}: {e}")
                self._mark_unhealthy(backend)

                # Track backend error
                ALERTING_BACKEND_ERRORS.labels(
                    backend=backend_name,
                    operation="list_alerts",
                    error_type=type(e).__name__,
                ).inc()

                # Mark this backend as failed for fallback tracking
                failed_backend = backend_name
                continue

        # All backends failed
        return AlertSearchResult(alerts=[], total_count=0)

    async def get_alert(self, alert_id: str) -> Alert | None:
        """
        Get a specific alert by ID using the first healthy backend.
        """
        failed_backend: str | None = None

        for backend in self._backends:
            backend_name = type(backend).__name__

            if not await self._is_backend_healthy(backend):
                continue

            try:
                result = await backend.get_alert(alert_id)

                # Track fallback if we succeeded after a failure
                if failed_backend is not None:
                    ALERTING_FALLBACK_ACTIVATIONS.labels(
                        from_backend=failed_backend,
                        to_backend=backend_name,
                        operation="get_alert",
                    ).inc()

                return result
            except Exception as e:
                logger.warning(f"get_alert failed for {backend_name}: {e}")
                self._mark_unhealthy(backend)

                # Track backend error
                ALERTING_BACKEND_ERRORS.labels(
                    backend=backend_name,
                    operation="get_alert",
                    error_type=type(e).__name__,
                ).inc()

                # Mark this backend as failed for fallback tracking
                failed_backend = backend_name
                continue

        return None

    async def get_alerts_for_service(
        self,
        service_name: str,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int = 100,
    ) -> AlertSearchResult:
        """
        Get alerts for a specific service using the first healthy backend.
        """
        failed_backend: str | None = None

        for backend in self._backends:
            backend_name = type(backend).__name__

            if not await self._is_backend_healthy(backend):
                continue

            try:
                result = await backend.get_alerts_for_service(
                    service_name=service_name,
                    start=start,
                    end=end,
                    limit=limit,
                )

                # Track fallback if we succeeded after a failure
                if failed_backend is not None:
                    ALERTING_FALLBACK_ACTIVATIONS.labels(
                        from_backend=failed_backend,
                        to_backend=backend_name,
                        operation="get_alerts_for_service",
                    ).inc()

                return result
            except Exception as e:
                logger.warning(f"get_alerts_for_service failed for {backend_name}: {e}")
                self._mark_unhealthy(backend)

                # Track backend error
                ALERTING_BACKEND_ERRORS.labels(
                    backend=backend_name,
                    operation="get_alerts_for_service",
                    error_type=type(e).__name__,
                ).inc()

                # Mark this backend as failed for fallback tracking
                failed_backend = backend_name
                continue

        return AlertSearchResult(alerts=[], total_count=0)

    async def list_alert_rules(
        self,
        enabled_only: bool = True,
        limit: int = 100,
    ) -> list[AlertRule]:
        """
        List alert rules using the first healthy backend.
        """
        failed_backend: str | None = None

        for backend in self._backends:
            backend_name = type(backend).__name__

            if not await self._is_backend_healthy(backend):
                continue

            try:
                result = await backend.list_alert_rules(
                    enabled_only=enabled_only,
                    limit=limit,
                )

                # Track fallback if we succeeded after a failure
                if failed_backend is not None:
                    ALERTING_FALLBACK_ACTIVATIONS.labels(
                        from_backend=failed_backend,
                        to_backend=backend_name,
                        operation="list_alert_rules",
                    ).inc()

                return result
            except Exception as e:
                logger.warning(f"list_alert_rules failed for {backend_name}: {e}")
                self._mark_unhealthy(backend)

                # Track backend error
                ALERTING_BACKEND_ERRORS.labels(
                    backend=backend_name,
                    operation="list_alert_rules",
                    error_type=type(e).__name__,
                ).inc()

                # Mark this backend as failed for fallback tracking
                failed_backend = backend_name
                continue

        return []

    async def health_check(self) -> bool:
        """
        Check if any backend is healthy.

        Returns True if at least one backend is healthy.
        """
        for backend in self._backends:
            if await self._is_backend_healthy(backend):
                return True
        return False
