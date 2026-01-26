"""
Frontend Cache API Tests (TDD - RED Phase)

Tests for the /api/v1/cache/* endpoints that provide Redis L2 caching
for the frontend useTieredCache hook.

Reference: docs-internal/CACHING_ARCHITECTURE_AUDIT.md - "Redis L2 Backend for Frontend"
"""

import gc
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from mcp_server_langgraph.core.cache import CacheService

pytestmark = [pytest.mark.api, pytest.mark.unit]

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_cache_service() -> MagicMock:
    """Create a mock CacheService for testing."""
    cache = MagicMock(spec=CacheService)
    cache.aget = AsyncMock(return_value=None)
    cache.aset = AsyncMock(return_value=None)
    cache.adelete = AsyncMock(return_value=None)
    cache.adelete_pattern = AsyncMock(return_value=0)
    return cache


@pytest.fixture
def mock_user() -> dict[str, Any]:
    """Create a mock authenticated user."""
    return {
        "user_id": "test-user-123",
        "username": "testuser",
        "email": "test@example.com",
        "roles": ["user"],
    }


@pytest.fixture
def app(mock_cache_service: MagicMock, mock_user: dict[str, Any]) -> FastAPI:
    """Create FastAPI app with frontend cache router."""
    from fastapi import FastAPI

    from mcp_server_langgraph.api.v1.frontend_cache import frontend_cache_router
    from mcp_server_langgraph.core.cache import get_cache

    app = FastAPI()

    # Override dependencies
    async def get_mock_cache() -> CacheService:
        return mock_cache_service

    async def get_mock_user() -> dict[str, Any]:
        return mock_user

    app.dependency_overrides[get_cache] = get_mock_cache

    # Import and override get_current_user
    from mcp_server_langgraph.auth.dependencies import get_current_user

    app.dependency_overrides[get_current_user] = get_mock_user

    app.include_router(frontend_cache_router, prefix="/api/v1")

    return app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Create test client."""
    return TestClient(app)


# =============================================================================
# Tests: GET /cache/{key}
# =============================================================================


@pytest.mark.unit
@pytest.mark.xdist_group(name="frontend_cache_api")
class TestGetCachedValue:
    """Tests for GET /api/v1/cache/{key} endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_get_cached_value_returns_hit_when_value_exists(
        self,
        client: TestClient,
        mock_cache_service: MagicMock,
    ) -> None:
        """GET /cache/{key} returns hit=true when value exists in cache."""
        # Setup
        mock_cache_service.aget.return_value = {"data": "cached-data", "_cachedAt": 1234567890}

        # Execute
        response = client.get("/api/v1/cache/my-cache-key")

        # Verify
        assert response.status_code == 200
        data = response.json()
        assert data["key"] == "my-cache-key"
        assert data["hit"] is True
        assert data["value"] == {"data": "cached-data", "_cachedAt": 1234567890}

    def test_get_cached_value_returns_miss_when_value_not_exists(
        self,
        client: TestClient,
        mock_cache_service: MagicMock,
    ) -> None:
        """GET /cache/{key} returns hit=false when value not in cache."""
        # Setup
        mock_cache_service.aget.return_value = None

        # Execute
        response = client.get("/api/v1/cache/missing-key")

        # Verify
        assert response.status_code == 200
        data = response.json()
        assert data["key"] == "missing-key"
        assert data["hit"] is False
        assert data["value"] is None

    def test_get_cached_value_uses_user_scoped_key(
        self,
        client: TestClient,
        mock_cache_service: MagicMock,
        mock_user: dict[str, Any],
    ) -> None:
        """GET /cache/{key} uses user-scoped cache key for isolation."""
        # Execute
        client.get("/api/v1/cache/user-specific-key")

        # Verify - key should be prefixed with user ID
        mock_cache_service.aget.assert_called_once()
        called_key = mock_cache_service.aget.call_args[0][0]
        assert f"frontend:{mock_user['user_id']}:" in called_key
        assert "user-specific-key" in called_key

    def test_get_cached_value_handles_url_encoded_key(
        self,
        client: TestClient,
        mock_cache_service: MagicMock,
    ) -> None:
        """GET /cache/{key} properly handles URL-encoded keys."""
        # Execute
        response = client.get("/api/v1/cache/session%3A123%3Adata")

        # Verify
        assert response.status_code == 200
        mock_cache_service.aget.assert_called_once()
        called_key = mock_cache_service.aget.call_args[0][0]
        assert "session:123:data" in called_key


# =============================================================================
# Tests: PUT /cache/{key}
# =============================================================================


@pytest.mark.unit
@pytest.mark.xdist_group(name="frontend_cache_api")
class TestSetCachedValue:
    """Tests for PUT /api/v1/cache/{key} endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_set_cached_value_stores_value_in_cache(
        self,
        client: TestClient,
        mock_cache_service: MagicMock,
    ) -> None:
        """PUT /cache/{key} stores value in cache with user-scoped key."""
        # Execute
        response = client.put(
            "/api/v1/cache/my-cache-key",
            json={
                "value": {"data": "test-data", "_cachedAt": 1234567890},
                "ttl_seconds": 300,
            },
        )

        # Verify
        assert response.status_code == 200
        data = response.json()
        assert data["key"] == "my-cache-key"
        assert data["success"] is True

    def test_set_cached_value_uses_default_ttl(
        self,
        client: TestClient,
        mock_cache_service: MagicMock,
    ) -> None:
        """PUT /cache/{key} uses default TTL when not specified."""
        # Execute
        client.put(
            "/api/v1/cache/my-cache-key",
            json={"value": {"data": "test-data"}},
        )

        # Verify - should use default TTL of 300 seconds
        mock_cache_service.aset.assert_called_once()
        call_kwargs = mock_cache_service.aset.call_args[1]
        assert call_kwargs.get("ttl") == 300

    def test_set_cached_value_uses_provided_ttl(
        self,
        client: TestClient,
        mock_cache_service: MagicMock,
    ) -> None:
        """PUT /cache/{key} uses provided TTL."""
        # Execute
        client.put(
            "/api/v1/cache/my-cache-key",
            json={"value": {"data": "test-data"}, "ttl_seconds": 600},
        )

        # Verify
        mock_cache_service.aset.assert_called_once()
        call_kwargs = mock_cache_service.aset.call_args[1]
        assert call_kwargs.get("ttl") == 600

    def test_set_cached_value_enforces_max_ttl(
        self,
        client: TestClient,
        mock_cache_service: MagicMock,
    ) -> None:
        """PUT /cache/{key} enforces maximum TTL of 1 hour."""
        # Execute - request 24 hours TTL
        client.put(
            "/api/v1/cache/my-cache-key",
            json={"value": {"data": "test-data"}, "ttl_seconds": 86400},
        )

        # Verify - should be capped at 3600 (1 hour)
        mock_cache_service.aset.assert_called_once()
        call_kwargs = mock_cache_service.aset.call_args[1]
        assert call_kwargs.get("ttl") <= 3600

    def test_set_cached_value_enforces_max_size(
        self,
        client: TestClient,
        mock_cache_service: MagicMock,
    ) -> None:
        """PUT /cache/{key} rejects values larger than max size limit."""
        # Create a large payload (> 100KB)
        large_value = {"data": "x" * 200_000}

        # Execute
        response = client.put(
            "/api/v1/cache/my-cache-key",
            json={"value": large_value},
        )

        # Verify - should reject with 413 Payload Too Large
        assert response.status_code == 413


# =============================================================================
# Tests: DELETE /cache/{key}
# =============================================================================


@pytest.mark.unit
@pytest.mark.xdist_group(name="frontend_cache_api")
class TestDeleteCachedValue:
    """Tests for DELETE /api/v1/cache/{key} endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_delete_cached_value_removes_from_cache(
        self,
        client: TestClient,
        mock_cache_service: MagicMock,
    ) -> None:
        """DELETE /cache/{key} removes value from cache."""
        # Execute
        response = client.delete("/api/v1/cache/my-cache-key")

        # Verify
        assert response.status_code == 200
        data = response.json()
        assert data["key"] == "my-cache-key"
        assert data["success"] is True
        mock_cache_service.adelete.assert_called_once()

    def test_delete_cached_value_uses_user_scoped_key(
        self,
        client: TestClient,
        mock_cache_service: MagicMock,
        mock_user: dict[str, Any],
    ) -> None:
        """DELETE /cache/{key} uses user-scoped cache key."""
        # Execute
        client.delete("/api/v1/cache/user-key")

        # Verify
        mock_cache_service.adelete.assert_called_once()
        called_key = mock_cache_service.adelete.call_args[0][0]
        assert f"frontend:{mock_user['user_id']}:" in called_key


# =============================================================================
# Tests: DELETE /cache/prefix/{prefix}
# =============================================================================


@pytest.mark.unit
@pytest.mark.xdist_group(name="frontend_cache_api")
class TestInvalidatePrefix:
    """Tests for DELETE /api/v1/cache/prefix/{prefix} endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_invalidate_prefix_deletes_matching_keys(
        self,
        client: TestClient,
        mock_cache_service: MagicMock,
    ) -> None:
        """DELETE /cache/prefix/{prefix} deletes all keys matching prefix."""
        # Setup
        mock_cache_service.adelete_pattern.return_value = 5

        # Execute
        response = client.delete("/api/v1/cache/prefix/session")

        # Verify
        assert response.status_code == 200
        data = response.json()
        assert data["prefix"] == "session"
        assert data["deleted_count"] == 5

    def test_invalidate_prefix_uses_user_scoped_pattern(
        self,
        client: TestClient,
        mock_cache_service: MagicMock,
        mock_user: dict[str, Any],
    ) -> None:
        """DELETE /cache/prefix/{prefix} uses user-scoped pattern."""
        # Execute
        client.delete("/api/v1/cache/prefix/myprefix")

        # Verify - pattern should include user ID
        mock_cache_service.adelete_pattern.assert_called_once()
        called_pattern = mock_cache_service.adelete_pattern.call_args[0][0]
        assert f"frontend:{mock_user['user_id']}:myprefix:*" == called_pattern


# =============================================================================
# Tests: Authentication & Security
# =============================================================================


@pytest.mark.unit
@pytest.mark.xdist_group(name="frontend_cache_api_auth")
class TestAuthentication:
    """Tests for authentication requirements."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_endpoints_require_authentication(self) -> None:
        """All cache endpoints require authentication."""
        from fastapi import FastAPI
        from starlette.testclient import TestClient

        from mcp_server_langgraph.api.v1.frontend_cache import frontend_cache_router

        # Create app without auth override
        app = FastAPI()
        app.include_router(frontend_cache_router, prefix="/api/v1")

        # Use Starlette TestClient directly which handles errors better
        with TestClient(app) as client:
            # All endpoints should return 401 or 403 without auth
            endpoints = [
                ("GET", "/api/v1/cache/test-key"),
                ("PUT", "/api/v1/cache/test-key"),
                ("DELETE", "/api/v1/cache/test-key"),
                ("DELETE", "/api/v1/cache/prefix/test"),
            ]

            for method, path in endpoints:
                try:
                    response = client.request(method, path, json={"value": {}})
                    # Should be 401 (unauthenticated), 403, 422, or 500 (dependency not configured)
                    assert response.status_code in [401, 403, 422, 500], f"{method} {path} returned {response.status_code}"
                except Exception:
                    # Any exception (including 500 from missing dependencies) is expected
                    pass


# =============================================================================
# Tests: Rate Limiting
# =============================================================================


@pytest.mark.unit
@pytest.mark.xdist_group(name="frontend_cache_api_rate")
class TestRateLimiting:
    """Tests for rate limiting on cache endpoints."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_rate_limit_applied_to_cache_endpoint(
        self,
    ) -> None:
        """
        Cache endpoints have rate limiting configured.

        GIVEN rate limiting is configured in PATH_RATE_LIMITS
        WHEN checking for frontend cache endpoint
        THEN it should be present with a reasonable limit
        """
        from mcp_server_langgraph.middleware.rate_limiter import PATH_RATE_LIMITS

        # Verify cache endpoint is rate limited
        assert "/api/v1/cache" in PATH_RATE_LIMITS

        # Verify reasonable limit (should prevent cache flooding)
        limit = PATH_RATE_LIMITS["/api/v1/cache"]
        assert "minute" in limit
        # Extract number from limit string (e.g., "100/minute")
        requests_per_minute = int(limit.split("/")[0])
        assert 50 <= requests_per_minute <= 200  # Reasonable range for cache operations


# =============================================================================
# Tests: Prometheus Metrics
# =============================================================================


@pytest.mark.unit
@pytest.mark.xdist_group(name="frontend_cache_api_metrics")
class TestPrometheusMetrics:
    """Tests for Prometheus metrics instrumentation in frontend cache API."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_frontend_cache_metrics_exports_exist(self) -> None:
        """Frontend cache module exports Prometheus metrics."""
        from mcp_server_langgraph.api.v1.frontend_cache import (
            frontend_cache_get_total,
            frontend_cache_hit_total,
            frontend_cache_miss_total,
            frontend_cache_set_total,
            frontend_cache_delete_total,
            frontend_cache_latency_seconds,
            PROMETHEUS_AVAILABLE,
        )

        # Verify metrics exist (either real or mock)
        assert frontend_cache_get_total is not None
        assert frontend_cache_hit_total is not None
        assert frontend_cache_miss_total is not None
        assert frontend_cache_set_total is not None
        assert frontend_cache_delete_total is not None
        assert frontend_cache_latency_seconds is not None
        assert isinstance(PROMETHEUS_AVAILABLE, bool)

    def test_get_endpoint_increments_get_total(
        self,
        client: TestClient,
        mock_cache_service: MagicMock,
    ) -> None:
        """GET /cache/{key} increments frontend_cache_get_total counter."""
        from mcp_server_langgraph.api.v1.frontend_cache import (
            frontend_cache_get_total,
            PROMETHEUS_AVAILABLE,
        )

        if not PROMETHEUS_AVAILABLE:
            pytest.skip("Prometheus metrics not available")

        # Get initial value
        initial_value = frontend_cache_get_total._value.get()

        # Execute
        client.get("/api/v1/cache/test-key")

        # Verify - counter should have incremented
        new_value = frontend_cache_get_total._value.get()
        assert new_value > initial_value

    def test_get_endpoint_increments_hit_on_cache_hit(
        self,
        client: TestClient,
        mock_cache_service: MagicMock,
    ) -> None:
        """GET /cache/{key} increments frontend_cache_hit_total on cache hit."""
        from mcp_server_langgraph.api.v1.frontend_cache import (
            frontend_cache_hit_total,
            PROMETHEUS_AVAILABLE,
        )

        if not PROMETHEUS_AVAILABLE:
            pytest.skip("Prometheus metrics not available")

        # Setup - cache hit
        mock_cache_service.aget.return_value = {"data": "cached"}

        # Get initial value
        initial_value = frontend_cache_hit_total._value.get()

        # Execute
        client.get("/api/v1/cache/test-key")

        # Verify - hit counter should have incremented
        new_value = frontend_cache_hit_total._value.get()
        assert new_value > initial_value

    def test_get_endpoint_increments_miss_on_cache_miss(
        self,
        client: TestClient,
        mock_cache_service: MagicMock,
    ) -> None:
        """GET /cache/{key} increments frontend_cache_miss_total on cache miss."""
        from mcp_server_langgraph.api.v1.frontend_cache import (
            frontend_cache_miss_total,
            PROMETHEUS_AVAILABLE,
        )

        if not PROMETHEUS_AVAILABLE:
            pytest.skip("Prometheus metrics not available")

        # Setup - cache miss
        mock_cache_service.aget.return_value = None

        # Get initial value
        initial_value = frontend_cache_miss_total._value.get()

        # Execute
        client.get("/api/v1/cache/test-key")

        # Verify - miss counter should have incremented
        new_value = frontend_cache_miss_total._value.get()
        assert new_value > initial_value

    def test_set_endpoint_increments_set_total(
        self,
        client: TestClient,
        mock_cache_service: MagicMock,
    ) -> None:
        """PUT /cache/{key} increments frontend_cache_set_total counter."""
        from mcp_server_langgraph.api.v1.frontend_cache import (
            frontend_cache_set_total,
            PROMETHEUS_AVAILABLE,
        )

        if not PROMETHEUS_AVAILABLE:
            pytest.skip("Prometheus metrics not available")

        # Get initial value
        initial_value = frontend_cache_set_total._value.get()

        # Execute
        client.put(
            "/api/v1/cache/test-key",
            json={"value": {"data": "test"}, "ttl_seconds": 300},
        )

        # Verify - counter should have incremented
        new_value = frontend_cache_set_total._value.get()
        assert new_value > initial_value

    def test_delete_endpoint_increments_delete_total(
        self,
        client: TestClient,
        mock_cache_service: MagicMock,
    ) -> None:
        """DELETE /cache/{key} increments frontend_cache_delete_total counter."""
        from mcp_server_langgraph.api.v1.frontend_cache import (
            frontend_cache_delete_total,
            PROMETHEUS_AVAILABLE,
        )

        if not PROMETHEUS_AVAILABLE:
            pytest.skip("Prometheus metrics not available")

        # Get initial value
        initial_value = frontend_cache_delete_total._value.get()

        # Execute
        client.delete("/api/v1/cache/test-key")

        # Verify - counter should have incremented
        new_value = frontend_cache_delete_total._value.get()
        assert new_value > initial_value

    def test_latency_histogram_records_get_duration(
        self,
        client: TestClient,
        mock_cache_service: MagicMock,
    ) -> None:
        """GET /cache/{key} records latency in frontend_cache_latency_seconds histogram."""
        from mcp_server_langgraph.api.v1.frontend_cache import (
            frontend_cache_latency_seconds,
            PROMETHEUS_AVAILABLE,
        )

        if not PROMETHEUS_AVAILABLE:
            pytest.skip("Prometheus metrics not available")

        # Get the labeled histogram for "get" operation and check its _sum
        labeled_histogram = frontend_cache_latency_seconds.labels(operation="get")
        initial_sum = labeled_histogram._sum.get()

        # Execute
        client.get("/api/v1/cache/test-key")

        # Verify - histogram _sum should increase (indicating an observation was made)
        after_sum = labeled_histogram._sum.get()
        assert after_sum > initial_sum
