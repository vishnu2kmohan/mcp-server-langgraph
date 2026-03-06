"""
Tests for Granular Health Probes (K8s Probe Pattern).

Tests for:
- /health/live - Liveness probe
- /health/startup - Startup probe
- /health/ready - Readiness probe
- /health/deps - Dependency status
"""

import gc

import pytest
from fastapi.testclient import TestClient

# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit


class TestLivenessProbe:
    """Tests for /health/live endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_liveness_returns_alive(self, test_client: TestClient):
        """Liveness probe should return status='alive'."""
        response = test_client.get("/api/v1/health/live")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "alive"

    def test_liveness_is_lightweight(self, test_client: TestClient):
        """Liveness probe should be fast (no dependency checks)."""
        import time

        start = time.perf_counter()
        response = test_client.get("/api/v1/health/live")
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert response.status_code == 200
        # Should complete in under 50ms (no external calls)
        assert elapsed_ms < 50, f"Liveness probe took {elapsed_ms}ms, expected < 50ms"


class TestStartupProbe:
    """Tests for /health/startup endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_startup_returns_started(self, test_client: TestClient):
        """Startup probe should return status='started' when observability is ready."""
        response = test_client.get("/api/v1/health/startup")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "started"
        assert data["observability"] is True

    def test_startup_includes_observability_field(self, test_client: TestClient):
        """Startup probe should include observability field."""
        response = test_client.get("/api/v1/health/startup")

        assert response.status_code == 200
        data = response.json()
        assert "observability" in data


class TestReadinessProbe:
    """Tests for /health/ready endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_readiness_returns_status(self, test_client: TestClient):
        """Readiness probe should return status field."""
        response = test_client.get("/api/v1/health/ready")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] in ["ready", "not_ready"]

    def test_readiness_includes_checks(self, test_client: TestClient):
        """Readiness probe should include checks dict."""
        response = test_client.get("/api/v1/health/ready")

        assert response.status_code == 200
        data = response.json()
        assert "checks" in data
        assert "observability" in data["checks"]


class TestDependencyStatus:
    """Tests for /health/deps endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_deps_returns_list(self, test_client: TestClient):
        """Dependency status should return a list."""
        response = test_client.get("/api/v1/health/deps")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_deps_includes_observability(self, test_client: TestClient):
        """Dependency status should include observability."""
        response = test_client.get("/api/v1/health/deps")

        assert response.status_code == 200
        data = response.json()

        names = [d["name"] for d in data]
        assert "observability" in names

    def test_deps_includes_latency(self, test_client: TestClient):
        """Dependency status should include latency_ms field."""
        response = test_client.get("/api/v1/health/deps")

        assert response.status_code == 200
        data = response.json()

        for dep in data:
            assert "latency_ms" in dep
            assert dep["latency_ms"] is None or isinstance(dep["latency_ms"], (int, float))

    def test_deps_includes_message(self, test_client: TestClient):
        """Dependency status should include message field."""
        response = test_client.get("/api/v1/health/deps")

        assert response.status_code == 200
        data = response.json()

        for dep in data:
            assert "message" in dep
            assert "healthy" in dep


@pytest.fixture
def test_client(monkeypatch):
    """Create test client with proper environment."""
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-32-chars-long1234")
    monkeypatch.setenv("ENVIRONMENT", "test")

    from mcp_server_langgraph.app import create_app

    app = create_app(skip_startup_validation=True)

    with TestClient(app) as client:
        yield client
