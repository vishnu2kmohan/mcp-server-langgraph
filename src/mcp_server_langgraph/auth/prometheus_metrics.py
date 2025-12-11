"""
Prometheus-compatible authentication metrics.

These metrics are exposed via the /metrics endpoint for Alloy/Prometheus scraping.
They complement the OpenTelemetry metrics in auth/metrics.py which are sent via OTLP.

Metrics:
- auth_login_attempts_total: Login attempts by provider and result
- auth_login_failures_total: Login failures by provider and reason
- auth_login_duration_seconds: Login duration histogram
- auth_token_verifications_total: Token verification attempts by result
- auth_jwks_cache_operations_total: JWKS cache hits/misses
- auth_sessions_active: Current active session count
- auth_session_created_total: Sessions created
- auth_session_revoked_total: Sessions revoked
- auth_authorization_checks_total: Authorization checks by result and resource
"""

from typing import Any

# Lazy-load prometheus_client to handle missing dependency
_metrics_available: bool | None = None
_auth_login_attempts_total: Any = None
_auth_login_failures_total: Any = None
_auth_login_duration_seconds: Any = None
_auth_token_verifications_total: Any = None
_auth_token_created_total: Any = None
_auth_token_refresh_total: Any = None
_auth_jwks_cache_operations_total: Any = None
_auth_sessions_active: Any = None
_auth_session_created_total: Any = None
_auth_session_revoked_total: Any = None
_auth_authorization_checks_total: Any = None
_auth_authorization_duration_seconds: Any = None


def _init_metrics() -> bool:
    """Initialize Prometheus auth metrics lazily."""
    global _metrics_available  # noqa: PLW0603
    global _auth_login_attempts_total  # noqa: PLW0603
    global _auth_login_failures_total  # noqa: PLW0603
    global _auth_login_duration_seconds  # noqa: PLW0603
    global _auth_token_verifications_total  # noqa: PLW0603
    global _auth_token_created_total  # noqa: PLW0603
    global _auth_token_refresh_total  # noqa: PLW0603
    global _auth_jwks_cache_operations_total  # noqa: PLW0603
    global _auth_sessions_active  # noqa: PLW0603
    global _auth_session_created_total  # noqa: PLW0603
    global _auth_session_revoked_total  # noqa: PLW0603
    global _auth_authorization_checks_total  # noqa: PLW0603
    global _auth_authorization_duration_seconds  # noqa: PLW0603

    if _metrics_available is not None:
        return _metrics_available

    try:
        from prometheus_client import Counter, Gauge, Histogram

        # Login metrics
        _auth_login_attempts_total = Counter(
            "auth_login_attempts_total",
            "Total login attempts by provider and result",
            ["provider", "result"],  # provider: keycloak, local; result: success, failure
        )

        _auth_login_failures_total = Counter(
            "auth_login_failures_total",
            "Total login failures by provider and reason",
            ["provider", "reason"],  # reason: invalid_credentials, expired, locked, etc.
        )

        _auth_login_duration_seconds = Histogram(
            "auth_login_duration_seconds",
            "Login duration in seconds",
            ["provider"],
            buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
        )

        # Token metrics
        _auth_token_verifications_total = Counter(
            "auth_token_verifications_total",
            "Token verification attempts by result",
            ["result", "provider"],  # result: success, expired, invalid, revoked
        )

        _auth_token_created_total = Counter(
            "auth_token_created_total",
            "Tokens created by provider",
            ["provider"],
        )

        _auth_token_refresh_total = Counter(
            "auth_token_refresh_total",
            "Token refresh attempts by result",
            ["result"],  # success, failure
        )

        # JWKS cache metrics
        _auth_jwks_cache_operations_total = Counter(
            "auth_jwks_cache_operations_total",
            "JWKS cache operations by type",
            ["type"],  # hit, miss, refresh
        )

        # Session metrics
        _auth_sessions_active = Gauge(
            "auth_sessions_active",
            "Current number of active sessions",
            ["backend"],  # redis, memory, postgres
        )

        _auth_session_created_total = Counter(
            "auth_session_created_total",
            "Sessions created by backend",
            ["backend"],
        )

        _auth_session_revoked_total = Counter(
            "auth_session_revoked_total",
            "Sessions revoked by backend",
            ["backend"],
        )

        # Authorization metrics
        _auth_authorization_checks_total = Counter(
            "auth_authorization_checks_total",
            "Authorization checks by result and resource type",
            ["result", "resource_type"],  # result: allowed, denied
        )

        _auth_authorization_duration_seconds = Histogram(
            "auth_authorization_duration_seconds",
            "Authorization check duration in seconds",
            ["resource_type"],
            buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0),
        )

        _metrics_available = True
        return True

    except ImportError:
        _metrics_available = False
        return False


# Initialize on module load
_init_metrics()


# =============================================================================
# Login Metrics Recording Functions
# =============================================================================


def record_login_attempt(provider: str, result: str, duration_seconds: float) -> None:
    """
    Record a login attempt.

    Args:
        provider: Authentication provider (e.g., "keycloak", "local")
        result: Result of the attempt (e.g., "success", "invalid_credentials", "error")
        duration_seconds: Duration of the login attempt in seconds
    """
    if not _metrics_available:
        return

    try:
        if _auth_login_attempts_total:
            _auth_login_attempts_total.labels(provider=provider, result=result).inc()

        if _auth_login_duration_seconds:
            _auth_login_duration_seconds.labels(provider=provider).observe(duration_seconds)

        # Record failures separately with reason
        if result != "success" and _auth_login_failures_total:
            _auth_login_failures_total.labels(provider=provider, reason=result).inc()
    except Exception:
        pass  # Silently ignore metric recording errors


# =============================================================================
# Token Metrics Recording Functions
# =============================================================================


def record_token_verification(result: str, provider: str = "unknown") -> None:
    """
    Record a token verification attempt.

    Args:
        result: Result of verification (e.g., "success", "expired", "invalid")
        provider: Token provider (e.g., "keycloak")
    """
    if not _metrics_available:
        return

    try:
        if _auth_token_verifications_total:
            _auth_token_verifications_total.labels(result=result, provider=provider).inc()
    except Exception:
        pass


def record_token_created(provider: str = "unknown") -> None:
    """
    Record token creation.

    Args:
        provider: Token provider (e.g., "keycloak")
    """
    if not _metrics_available:
        return

    try:
        if _auth_token_created_total:
            _auth_token_created_total.labels(provider=provider).inc()
    except Exception:
        pass


def record_token_refresh(result: str) -> None:
    """
    Record a token refresh attempt.

    Args:
        result: Result of refresh ("success" or "failure")
    """
    if not _metrics_available:
        return

    try:
        if _auth_token_refresh_total:
            _auth_token_refresh_total.labels(result=result).inc()
    except Exception:
        pass


# =============================================================================
# JWKS Cache Metrics Recording Functions
# =============================================================================


def record_jwks_cache_operation(operation_type: str) -> None:
    """
    Record a JWKS cache operation.

    Args:
        operation_type: Type of operation ("hit", "miss", "refresh")
    """
    if not _metrics_available:
        return

    try:
        if _auth_jwks_cache_operations_total:
            _auth_jwks_cache_operations_total.labels(type=operation_type).inc()
    except Exception:
        pass


# =============================================================================
# Session Metrics Recording Functions
# =============================================================================


def record_session_created(backend: str) -> None:
    """
    Record session creation.

    Args:
        backend: Session storage backend (e.g., "redis", "memory", "postgres")
    """
    if not _metrics_available:
        return

    try:
        if _auth_session_created_total:
            _auth_session_created_total.labels(backend=backend).inc()
        if _auth_sessions_active:
            _auth_sessions_active.labels(backend=backend).inc()
    except Exception:
        pass


def record_session_revoked(backend: str) -> None:
    """
    Record session revocation.

    Args:
        backend: Session storage backend (e.g., "redis", "memory", "postgres")
    """
    if not _metrics_available:
        return

    try:
        if _auth_session_revoked_total:
            _auth_session_revoked_total.labels(backend=backend).inc()
        if _auth_sessions_active:
            _auth_sessions_active.labels(backend=backend).dec()
    except Exception:
        pass


def set_active_sessions(backend: str, count: int) -> None:
    """
    Set the current active session count.

    Args:
        backend: Session storage backend
        count: Number of active sessions
    """
    if not _metrics_available:
        return

    try:
        if _auth_sessions_active:
            _auth_sessions_active.labels(backend=backend).set(count)
    except Exception:
        pass


# =============================================================================
# Authorization Metrics Recording Functions
# =============================================================================


def record_authorization_check(result: str, resource_type: str, duration_seconds: float | None = None) -> None:
    """
    Record an authorization check.

    Args:
        result: Result of the check ("allowed" or "denied")
        resource_type: Type of resource being authorized (e.g., "document", "workflow")
        duration_seconds: Optional duration of the check in seconds
    """
    if not _metrics_available:
        return

    try:
        if _auth_authorization_checks_total:
            _auth_authorization_checks_total.labels(result=result, resource_type=resource_type).inc()

        if duration_seconds is not None and _auth_authorization_duration_seconds:
            _auth_authorization_duration_seconds.labels(resource_type=resource_type).observe(duration_seconds)
    except Exception:
        pass
