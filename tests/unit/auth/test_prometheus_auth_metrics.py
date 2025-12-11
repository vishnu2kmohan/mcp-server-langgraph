"""
Tests for Prometheus-compatible authentication metrics.

These tests validate that auth metrics are properly exposed for
Prometheus/Alloy scraping via the /metrics endpoint.

TDD: Tests written FIRST before implementation.
"""

import gc

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.auth]


@pytest.mark.xdist_group(name="test_prometheus_auth_metrics")
class TestPrometheusAuthMetricsDefinitions:
    """Test that all Prometheus auth metrics are properly defined."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_auth_login_attempts_total_defined(self) -> None:
        """Test auth_login_attempts_total counter is defined."""
        from mcp_server_langgraph.auth import prometheus_metrics

        assert prometheus_metrics._init_metrics()
        assert prometheus_metrics._auth_login_attempts_total is not None

    def test_auth_login_failures_total_defined(self) -> None:
        """Test auth_login_failures_total counter is defined."""
        from mcp_server_langgraph.auth import prometheus_metrics

        assert prometheus_metrics._init_metrics()
        assert prometheus_metrics._auth_login_failures_total is not None

    def test_auth_login_duration_seconds_defined(self) -> None:
        """Test auth_login_duration_seconds histogram is defined."""
        from mcp_server_langgraph.auth import prometheus_metrics

        assert prometheus_metrics._init_metrics()
        assert prometheus_metrics._auth_login_duration_seconds is not None

    def test_auth_token_verifications_total_defined(self) -> None:
        """Test auth_token_verifications_total counter is defined."""
        from mcp_server_langgraph.auth import prometheus_metrics

        assert prometheus_metrics._init_metrics()
        assert prometheus_metrics._auth_token_verifications_total is not None

    def test_auth_jwks_cache_operations_total_defined(self) -> None:
        """Test auth_jwks_cache_operations_total counter is defined."""
        from mcp_server_langgraph.auth import prometheus_metrics

        assert prometheus_metrics._init_metrics()
        assert prometheus_metrics._auth_jwks_cache_operations_total is not None

    def test_auth_sessions_active_defined(self) -> None:
        """Test auth_sessions_active gauge is defined."""
        from mcp_server_langgraph.auth import prometheus_metrics

        assert prometheus_metrics._init_metrics()
        assert prometheus_metrics._auth_sessions_active is not None

    def test_auth_authorization_checks_total_defined(self) -> None:
        """Test auth_authorization_checks_total counter is defined."""
        from mcp_server_langgraph.auth import prometheus_metrics

        assert prometheus_metrics._init_metrics()
        assert prometheus_metrics._auth_authorization_checks_total is not None


@pytest.mark.xdist_group(name="test_prometheus_auth_metrics_record")
class TestPrometheusAuthMetricsRecording:
    """Test that metrics are properly recorded."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_record_login_success(self) -> None:
        """Test recording a successful login attempt."""
        from mcp_server_langgraph.auth import prometheus_metrics

        # Should not raise
        prometheus_metrics.record_login_attempt(provider="keycloak", result="success", duration_seconds=0.5)

    def test_record_login_failure(self) -> None:
        """Test recording a failed login attempt."""
        from mcp_server_langgraph.auth import prometheus_metrics

        # Should not raise
        prometheus_metrics.record_login_attempt(provider="keycloak", result="invalid_credentials", duration_seconds=0.1)

    def test_record_token_verification_success(self) -> None:
        """Test recording a successful token verification."""
        from mcp_server_langgraph.auth import prometheus_metrics

        # Should not raise
        prometheus_metrics.record_token_verification(result="success", provider="keycloak")

    def test_record_token_verification_failure(self) -> None:
        """Test recording a failed token verification."""
        from mcp_server_langgraph.auth import prometheus_metrics

        # Should not raise
        prometheus_metrics.record_token_verification(result="expired", provider="keycloak")

    def test_record_jwks_cache_hit(self) -> None:
        """Test recording a JWKS cache hit."""
        from mcp_server_langgraph.auth import prometheus_metrics

        # Should not raise
        prometheus_metrics.record_jwks_cache_operation(operation_type="hit")

    def test_record_jwks_cache_miss(self) -> None:
        """Test recording a JWKS cache miss."""
        from mcp_server_langgraph.auth import prometheus_metrics

        # Should not raise
        prometheus_metrics.record_jwks_cache_operation(operation_type="miss")

    def test_record_session_created(self) -> None:
        """Test recording session creation."""
        from mcp_server_langgraph.auth import prometheus_metrics

        # Should not raise
        prometheus_metrics.record_session_created(backend="redis")

    def test_record_session_revoked(self) -> None:
        """Test recording session revocation."""
        from mcp_server_langgraph.auth import prometheus_metrics

        # Should not raise
        prometheus_metrics.record_session_revoked(backend="redis")

    def test_record_authorization_check_allowed(self) -> None:
        """Test recording an allowed authorization check."""
        from mcp_server_langgraph.auth import prometheus_metrics

        # Should not raise
        prometheus_metrics.record_authorization_check(result="allowed", resource_type="document")

    def test_record_authorization_check_denied(self) -> None:
        """Test recording a denied authorization check."""
        from mcp_server_langgraph.auth import prometheus_metrics

        # Should not raise
        prometheus_metrics.record_authorization_check(result="denied", resource_type="workflow")


@pytest.mark.xdist_group(name="test_prometheus_auth_metrics_noop")
class TestPrometheusAuthMetricsNoOp:
    """Test that metrics functions work gracefully when prometheus_client unavailable."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_metrics_noop_when_unavailable(self) -> None:
        """Test that metric functions don't raise when prometheus_client is unavailable."""
        from mcp_server_langgraph.auth import prometheus_metrics

        # Temporarily disable metrics
        original = prometheus_metrics._metrics_available
        prometheus_metrics._metrics_available = False

        try:
            # None of these should raise
            prometheus_metrics.record_login_attempt("test", "success", 0.1)
            prometheus_metrics.record_token_verification("success", "test")
            prometheus_metrics.record_jwks_cache_operation("hit")
            prometheus_metrics.record_session_created("memory")
            prometheus_metrics.record_session_revoked("memory")
            prometheus_metrics.record_authorization_check("allowed", "test")
        finally:
            prometheus_metrics._metrics_available = original
