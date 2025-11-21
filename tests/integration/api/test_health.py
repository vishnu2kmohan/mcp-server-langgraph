"""
TDD Tests for Health Check and Startup Validation

Tests validate that health checks detect all critical system issues
identified in OpenAI Codex security audit.
"""

import gc
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from mcp_server_langgraph.api.health import (

pytestmark = pytest.mark.integration

    SystemValidationError,
    router,
    run_startup_validation,
    validate_api_key_cache_configured,
    validate_observability_initialized,
    validate_session_store_registered,
)


@pytest.mark.unit
@pytest.mark.xdist_group(name="api_health_tests")
class TestObservabilityValidation:
    """Test observability validation checks"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_validate_observability_when_initialized(self):
        """Test validation passes when observability is initialized"""
        with patch("mcp_server_langgraph.api.health.logger") as mock_logger:
            mock_logger.debug.return_value = None  # No exception

            is_healthy, message = validate_observability_initialized()

            assert is_healthy is True
            assert "initialized and functional" in message.lower()

    def test_validate_observability_when_not_initialized(self):
        """Test validation fails when observability not initialized"""
        with patch("mcp_server_langgraph.api.health.logger") as mock_logger:
            mock_logger.debug.side_effect = RuntimeError("Observability not initialized")

            is_healthy, message = validate_observability_initialized()

            assert is_healthy is False
            assert "not initialized" in message.lower()


@pytest.mark.unit
@pytest.mark.xdist_group(name="api_health_tests")
class TestSessionStoreValidation:
    """Test session store validation checks"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_validate_session_store_when_token_mode(self):
        """Test validation passes when using token auth (no sessions)"""
        with patch("mcp_server_langgraph.api.health.settings") as mock_settings:
            mock_settings.auth_mode = "token"

            is_healthy, message = validate_session_store_registered()

            assert is_healthy is True
            assert "token mode" in message.lower()

    def test_validate_session_store_when_properly_registered_memory(self):
        """Test validation passes when memory session store registered"""
        with patch("mcp_server_langgraph.api.health.settings") as mock_settings:
            mock_settings.auth_mode = "session"
            mock_settings.session_backend = "memory"

            with patch("mcp_server_langgraph.auth.session.get_session_store") as mock_get:
                from mcp_server_langgraph.auth.session import InMemorySessionStore

                mock_store = MagicMock(spec=InMemorySessionStore)
                type(mock_store).__name__ = "InMemorySessionStore"
                mock_get.return_value = mock_store

                is_healthy, message = validate_session_store_registered()

                assert is_healthy is True
                assert "InMemorySessionStore" in message

    def test_validate_session_store_when_miswired_redis(self):
        """Test validation fails when Redis configured but using fallback"""
        with patch("mcp_server_langgraph.api.health.settings") as mock_settings:
            mock_settings.auth_mode = "session"
            mock_settings.session_backend = "redis"

            with patch("mcp_server_langgraph.auth.session.get_session_store") as mock_get:
                from mcp_server_langgraph.auth.session import InMemorySessionStore

                # Fallback to memory despite Redis config (the bug!)
                mock_store = MagicMock(spec=InMemorySessionStore)
                type(mock_store).__name__ = "InMemorySessionStore"
                mock_get.return_value = mock_store

                is_healthy, message = validate_session_store_registered()

                assert is_healthy is False
                assert "fallback detected" in message.lower()


@pytest.mark.unit
@pytest.mark.xdist_group(name="api_health_tests")
class TestAPICacheValidation:
    """Test API key cache validation checks"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_validate_cache_when_disabled(self):
        """Test validation passes when caching disabled"""
        with patch("mcp_server_langgraph.api.health.settings") as mock_settings:
            mock_settings.api_key_cache_enabled = False

            is_healthy, message = validate_api_key_cache_configured()

            assert is_healthy is True
            assert "disabled" in message.lower()

    def test_validate_cache_when_enabled_and_configured(self):
        """Test validation passes when caching properly configured"""
        with patch("mcp_server_langgraph.api.health.settings") as mock_settings:
            mock_settings.api_key_cache_enabled = True
            mock_settings.redis_url = "redis://localhost:6379"
            mock_settings.api_key_cache_ttl = 3600

            is_healthy, message = validate_api_key_cache_configured()

            assert is_healthy is True
            assert "properly configured" in message.lower()

    def test_validate_cache_when_enabled_but_no_redis(self):
        """Test validation passes when caching enabled but no Redis URL"""
        with patch("mcp_server_langgraph.api.health.settings") as mock_settings:
            mock_settings.api_key_cache_enabled = True
            mock_settings.redis_url = ""

            is_healthy, message = validate_api_key_cache_configured()

            assert is_healthy is True
            assert "disabled" in message.lower()

    def test_validate_cache_when_invalid_ttl(self):
        """Test validation fails when TTL is invalid"""
        with patch("mcp_server_langgraph.api.health.settings") as mock_settings:
            mock_settings.api_key_cache_enabled = True
            mock_settings.redis_url = "redis://localhost:6379"
            mock_settings.api_key_cache_ttl = -1  # Invalid

            is_healthy, message = validate_api_key_cache_configured()

            assert is_healthy is False
            assert "configuration issues" in message.lower()


@pytest.mark.unit
@pytest.mark.xdist_group(name="api_health_tests")
class TestStartupValidation:
    """Test complete startup validation"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_run_startup_validation_all_healthy(self):
        """Test startup validation passes when all systems healthy"""
        with patch("mcp_server_langgraph.api.health.validate_observability_initialized", return_value=(True, "OK")):
            with patch("mcp_server_langgraph.api.health.validate_session_store_registered", return_value=(True, "OK")):
                with patch("mcp_server_langgraph.api.health.validate_api_key_cache_configured", return_value=(True, "OK")):
                    with patch("mcp_server_langgraph.api.health.validate_docker_sandbox_security", return_value=(True, "OK")):
                        # Should not raise
                        run_startup_validation()

    def test_run_startup_validation_fails_on_critical_error(self):
        """Test startup validation raises SystemValidationError on failure"""
        with patch(
            "mcp_server_langgraph.api.health.validate_observability_initialized",
            return_value=(False, "Observability broken"),
        ):
            with patch("mcp_server_langgraph.api.health.validate_session_store_registered", return_value=(True, "OK")):
                with patch("mcp_server_langgraph.api.health.validate_api_key_cache_configured", return_value=(True, "OK")):
                    with patch("mcp_server_langgraph.api.health.validate_docker_sandbox_security", return_value=(True, "OK")):
                        with pytest.raises(SystemValidationError, match="Startup validation failed"):
                            run_startup_validation()

    def test_run_startup_validation_logs_warnings(self):
        """Test startup validation logs warnings for non-critical issues"""
        with patch("mcp_server_langgraph.api.health.validate_observability_initialized", return_value=(True, "OK")):
            with patch("mcp_server_langgraph.api.health.validate_session_store_registered", return_value=(True, "OK")):
                with patch("mcp_server_langgraph.api.health.validate_api_key_cache_configured", return_value=(True, "OK")):
                    with patch(
                        "mcp_server_langgraph.api.health.validate_docker_sandbox_security",
                        return_value=(True, "Docker sandbox warnings: Network allowlist not implemented"),
                    ):
                        # Should not raise, but will log warning
                        run_startup_validation()


@pytest.mark.unit
@pytest.mark.xdist_group(name="api_health_tests")
class TestHealthCheckEndpoint:
    """Test health check HTTP endpoint"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.fixture
    def client(self):
        """Create test client with health router"""
        app = FastAPI()
        app.include_router(router)
        return TestClient(app)

    def test_health_endpoint_returns_200_when_healthy(self, client):
        """Test health endpoint returns 200 when all systems healthy"""
        with patch("mcp_server_langgraph.api.health.validate_observability_initialized", return_value=(True, "OK")):
            with patch("mcp_server_langgraph.api.health.validate_session_store_registered", return_value=(True, "OK")):
                with patch("mcp_server_langgraph.api.health.validate_api_key_cache_configured", return_value=(True, "OK")):
                    with patch("mcp_server_langgraph.api.health.validate_docker_sandbox_security", return_value=(True, "OK")):
                        response = client.get("/api/v1/health")

                        assert response.status_code == 200
                        data = response.json()
                        assert data["status"] == "healthy"
                        assert all(data["checks"].values())
                        assert data["errors"] == []

    def test_health_endpoint_shows_degraded_with_warnings(self, client):
        """Test health endpoint shows degraded status with warnings"""
        with patch("mcp_server_langgraph.api.health.validate_observability_initialized", return_value=(True, "OK")):
            with patch("mcp_server_langgraph.api.health.validate_session_store_registered", return_value=(True, "OK")):
                with patch("mcp_server_langgraph.api.health.validate_api_key_cache_configured", return_value=(True, "OK")):
                    with patch(
                        "mcp_server_langgraph.api.health.validate_docker_sandbox_security",
                        return_value=(True, "Warning: Network allowlist not implemented"),
                    ):
                        response = client.get("/api/v1/health")

                        assert response.status_code == 200
                        data = response.json()
                        assert data["status"] == "degraded"
                        assert len(data["warnings"]) > 0

    def test_health_endpoint_shows_unhealthy_with_errors(self, client):
        """Test health endpoint shows unhealthy status with errors"""
        with patch(
            "mcp_server_langgraph.api.health.validate_observability_initialized",
            return_value=(False, "Observability broken"),
        ):
            with patch("mcp_server_langgraph.api.health.validate_session_store_registered", return_value=(True, "OK")):
                with patch("mcp_server_langgraph.api.health.validate_api_key_cache_configured", return_value=(True, "OK")):
                    with patch("mcp_server_langgraph.api.health.validate_docker_sandbox_security", return_value=(True, "OK")):
                        response = client.get("/api/v1/health")

                        assert response.status_code == 200  # Endpoint still works
                        data = response.json()
                        assert data["status"] == "unhealthy"
                        assert len(data["errors"]) > 0
                        assert data["checks"]["observability"] is False


@pytest.mark.integration
@pytest.mark.xdist_group(name="api_health_tests")
class TestHealthCheckIntegration:
    """Integration tests for health check with real systems"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_health_check_with_real_app(self):
        """Test health check works with real app instance"""
        from mcp_server_langgraph.app import create_app

        app = create_app()
        client = TestClient(app)

        response = client.get("/api/v1/health")

        # Should work (app creation succeeded, so validation passed)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["healthy", "degraded"]  # May have warnings

    def test_startup_validation_called_during_app_creation(self):
        """Test that run_startup_validation is called when app is created"""
        with patch("mcp_server_langgraph.app.run_startup_validation") as mock_validation:
            from mcp_server_langgraph.app import create_app

            create_app()

            # Verify startup validation was called
            mock_validation.assert_called_once()
