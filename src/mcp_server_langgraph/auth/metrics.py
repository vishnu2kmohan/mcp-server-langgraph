"""
Authentication Metrics for Observability

Defines comprehensive metrics for monitoring authentication workflows:
- Login attempts and success rates
- Token verification performance
- Session management
- JWKS cache efficiency
- OpenFGA role synchronization
"""

from opentelemetry import metrics as otel_metrics

# Get meter for auth metrics
meter = otel_metrics.get_meter(__name__)


# Authentication Metrics

auth_login_attempts = meter.create_counter(
    name="auth.login.attempts", description="Number of login attempts by provider and result", unit="1"
)

auth_login_duration = meter.create_histogram(
    name="auth.login.duration", description="Login duration in milliseconds", unit="ms"
)

auth_login_failures = meter.create_counter(name="auth.login.failures", description="Login failures by reason", unit="1")


# Token Management Metrics

auth_token_created = meter.create_counter(name="auth.token.created", description="Tokens created by provider", unit="1")

auth_token_verifications = meter.create_counter(
    name="auth.token.verifications", description="Token verification attempts by result", unit="1"
)

auth_token_verify_duration = meter.create_histogram(
    name="auth.token.verify.duration", description="Token verification duration in milliseconds", unit="ms"
)

auth_token_refresh_attempts = meter.create_counter(
    name="auth.token.refresh.attempts", description="Token refresh attempts by result", unit="1"
)


# JWKS Cache Metrics

auth_jwks_cache_operations = meter.create_counter(
    name="auth.jwks.cache.operations", description="JWKS cache hits and misses", unit="1"
)

auth_jwks_fetch_duration = meter.create_histogram(
    name="auth.jwks.fetch.duration", description="JWKS fetch duration in milliseconds", unit="ms"
)

auth_jwks_refresh_count = meter.create_counter(name="auth.jwks.refresh", description="JWKS cache refresh count", unit="1")


# Session Management Metrics

auth_sessions_active = meter.create_up_down_counter(
    name="auth.sessions.active", description="Number of active sessions", unit="1"
)

auth_session_created = meter.create_counter(name="auth.session.created", description="Sessions created by backend", unit="1")

auth_session_retrieved = meter.create_counter(
    name="auth.session.retrieved", description="Session retrieval attempts by result", unit="1"
)

auth_session_refreshed = meter.create_counter(name="auth.session.refreshed", description="Sessions refreshed", unit="1")

auth_session_revoked = meter.create_counter(name="auth.session.revoked", description="Sessions revoked (deleted)", unit="1")

auth_session_expired = meter.create_counter(
    name="auth.session.expired", description="Sessions that expired naturally", unit="1"
)

auth_session_duration = meter.create_histogram(
    name="auth.session.duration", description="Session lifetime in seconds", unit="seconds"
)

auth_session_operations_duration = meter.create_histogram(
    name="auth.session.operations.duration", description="Session operation duration in milliseconds", unit="ms"
)


# User Provider Metrics

auth_provider_calls = meter.create_counter(
    name="auth.provider.calls", description="User provider method calls by provider and method", unit="1"
)

auth_provider_duration = meter.create_histogram(
    name="auth.provider.duration", description="User provider operation duration", unit="ms"
)

auth_provider_errors = meter.create_counter(
    name="auth.provider.errors", description="User provider errors by provider and error type", unit="1"
)


# OpenFGA Integration Metrics

auth_openfga_sync_attempts = meter.create_counter(
    name="auth.openfga.sync.attempts", description="OpenFGA role sync attempts by result", unit="1"
)

auth_openfga_sync_duration = meter.create_histogram(
    name="auth.openfga.sync.duration", description="OpenFGA role sync duration in milliseconds", unit="ms"
)

auth_openfga_tuples_written = meter.create_histogram(
    name="auth.openfga.tuples.written", description="Number of tuples written per sync", unit="tuples"
)

auth_openfga_sync_errors = meter.create_counter(
    name="auth.openfga.sync.errors", description="OpenFGA sync errors by error type", unit="1"
)


# Authorization Metrics

auth_authz_checks = meter.create_counter(
    name="auth.authorization.checks", description="Authorization checks by result", unit="1"
)

auth_authz_duration = meter.create_histogram(
    name="auth.authorization.duration", description="Authorization check duration in milliseconds", unit="ms"
)

auth_authz_cache_operations = meter.create_counter(
    name="auth.authorization.cache.operations", description="Authorization cache hits and misses", unit="1"
)


# Role Mapping Metrics

auth_role_mapping_operations = meter.create_counter(
    name="auth.role_mapping.operations", description="Role mapping operations by mapping type", unit="1"
)

auth_role_mapping_rules_applied = meter.create_histogram(
    name="auth.role_mapping.rules.applied", description="Number of mapping rules applied per user", unit="rules"
)

auth_role_mapping_tuples_generated = meter.create_histogram(
    name="auth.role_mapping.tuples.generated", description="Number of tuples generated by role mapper", unit="tuples"
)

auth_role_mapping_duration = meter.create_histogram(
    name="auth.role_mapping.duration", description="Role mapping duration in milliseconds", unit="ms"
)


# Concurrent Session Metrics

auth_concurrent_sessions = meter.create_histogram(
    name="auth.concurrent.sessions", description="Number of concurrent sessions per user", unit="sessions"
)

auth_session_limit_reached = meter.create_counter(
    name="auth.session.limit.reached", description="Times concurrent session limit was reached", unit="1"
)


# Helper functions for common metric patterns


def record_login_attempt(provider: str, result: str, duration_ms: float) -> None:
    """Record login attempt with all relevant metrics"""
    auth_login_attempts.add(1, {"provider": provider, "result": result})
    auth_login_duration.record(duration_ms, {"provider": provider})

    if result != "success":
        auth_login_failures.add(1, {"provider": provider, "reason": result})


def record_token_verification(result: str, duration_ms: float, provider: str = "unknown") -> None:
    """Record token verification metrics"""
    auth_token_verifications.add(1, {"result": result, "provider": provider})
    auth_token_verify_duration.record(duration_ms, {"provider": provider})


def record_session_operation(operation: str, backend: str, result: str, duration_ms: float) -> None:
    """Record session operation metrics"""
    if operation == "create":
        auth_session_created.add(1, {"backend": backend, "result": result})
        if result == "success":
            auth_sessions_active.add(1, {"backend": backend})
    elif operation == "retrieve":
        auth_session_retrieved.add(1, {"backend": backend, "result": result})
    elif operation == "refresh":
        auth_session_refreshed.add(1, {"backend": backend, "result": result})
    elif operation == "revoke":
        auth_session_revoked.add(1, {"backend": backend, "result": result})
        if result == "success":
            auth_sessions_active.add(-1, {"backend": backend})

    auth_session_operations_duration.record(duration_ms, {"operation": operation, "backend": backend})


def record_jwks_operation(operation: str, result: str, duration_ms: float | None = None) -> None:
    """Record JWKS cache operation metrics"""
    if operation in ["hit", "miss"]:
        auth_jwks_cache_operations.add(1, {"type": operation})
    elif operation == "refresh":
        auth_jwks_refresh_count.add(1, {"result": result})

    if duration_ms is not None:
        auth_jwks_fetch_duration.record(duration_ms)


def record_openfga_sync(result: str, duration_ms: float, tuple_count: int) -> None:
    """Record OpenFGA role sync metrics"""
    auth_openfga_sync_attempts.add(1, {"result": result})
    auth_openfga_sync_duration.record(duration_ms)

    if result == "success":
        auth_openfga_tuples_written.record(tuple_count)
    else:
        auth_openfga_sync_errors.add(1, {"result": result})


def record_role_mapping(mapping_type: str, rules_count: int, tuples_count: int, duration_ms: float) -> None:
    """Record role mapping metrics"""
    auth_role_mapping_operations.add(1, {"type": mapping_type})
    auth_role_mapping_rules_applied.record(rules_count)
    auth_role_mapping_tuples_generated.record(tuples_count)
    auth_role_mapping_duration.record(duration_ms)
