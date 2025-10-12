"""Unit tests for health_check.py - Health Check Endpoints"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def test_client():
    """Create a test client for the health check app"""
    from mcp_server_langgraph.health.checks import app

    return TestClient(app)


@pytest.mark.unit
class TestHealthCheckEndpoints:
    """Test health check endpoints"""

    def test_health_check_success(self, test_client):
        """Test basic health check returns healthy status"""
        response = test_client.get("/health")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert data["version"]
        assert data["checks"]["application"] == "running"

    def test_health_check_response_format(self, test_client):
        """Test health check response has correct format"""
        response = test_client.get("/health")
        data = response.json()

        # Verify required fields
        assert "status" in data
        assert "timestamp" in data
        assert "version" in data
        assert "checks" in data

        # Verify timestamp is ISO format
        datetime.fromisoformat(data["timestamp"])

    @patch("mcp_server_langgraph.health.checks.settings")
    @patch("mcp_server_langgraph.health.checks.OpenFGAClient")
    def test_readiness_check_all_healthy(self, mock_openfga, mock_settings, test_client):
        """Test readiness check when all services are healthy"""
        # Configure settings
        mock_settings.openfga_store_id = "test-store"
        mock_settings.openfga_model_id = "test-model"
        mock_settings.openfga_api_url = "http://localhost:8080"
        mock_settings.anthropic_api_key = "test-key"
        mock_settings.jwt_secret_key = "test-secret"
        mock_settings.service_version = "1.0.0"
        mock_settings.infisical_site_url = "https://infisical.com"

        # Mock OpenFGA client initialization
        mock_openfga.return_value = MagicMock()

        # Mock secrets manager
        with patch("mcp_server_langgraph.health.checks.get_secrets_manager") as mock_get_secrets:
            mock_secrets_mgr = MagicMock()
            mock_secrets_mgr.client = MagicMock()
            mock_secrets_mgr.get_secret.return_value = "ok"
            mock_get_secrets.return_value = mock_secrets_mgr

            response = test_client.get("/health/ready")

            assert response.status_code == 200
            data = response.json()

            assert data["status"] == "ready"
            assert data["checks"]["openfga"]["status"] == "healthy"
            assert data["checks"]["infisical"]["status"] == "healthy"
            assert data["checks"]["secrets"]["status"] == "healthy"

    @patch("mcp_server_langgraph.health.checks.settings")
    @patch("mcp_server_langgraph.health.checks.OpenFGAClient")
    def test_readiness_check_openfga_unhealthy(self, mock_openfga, mock_settings, test_client):
        """Test readiness check when OpenFGA is unavailable"""
        mock_settings.openfga_store_id = "test-store"
        mock_settings.openfga_model_id = "test-model"
        mock_settings.openfga_api_url = "http://localhost:8080"
        mock_settings.anthropic_api_key = "test-key"
        mock_settings.jwt_secret_key = "test-secret"
        mock_settings.service_version = "1.0.0"
        mock_settings.infisical_site_url = "https://infisical.com"

        # Mock OpenFGA failure
        mock_openfga.side_effect = Exception("Connection refused")

        with patch("mcp_server_langgraph.health.checks.get_secrets_manager") as mock_get_secrets:
            mock_secrets_mgr = MagicMock()
            mock_secrets_mgr.client = MagicMock()
            mock_secrets_mgr.get_secret.return_value = "ok"
            mock_get_secrets.return_value = mock_secrets_mgr

            response = test_client.get("/health/ready")

            assert response.status_code == 503
            data = response.json()

            assert data["status"] == "not_ready"
            assert data["checks"]["openfga"]["status"] == "unhealthy"
            assert "error" in data["checks"]["openfga"]

    @patch("mcp_server_langgraph.health.checks.settings")
    def test_readiness_check_missing_critical_secrets(self, mock_settings, test_client):
        """Test readiness check when critical secrets are missing"""
        mock_settings.openfga_store_id = None
        mock_settings.openfga_model_id = None
        mock_settings.anthropic_api_key = None  # Missing
        mock_settings.jwt_secret_key = None  # Missing
        mock_settings.service_version = "1.0.0"
        mock_settings.infisical_site_url = "https://infisical.com"

        with patch("mcp_server_langgraph.health.checks.get_secrets_manager") as mock_get_secrets:
            mock_secrets_mgr = MagicMock()
            mock_secrets_mgr.client = None
            mock_get_secrets.return_value = mock_secrets_mgr

            response = test_client.get("/health/ready")

            assert response.status_code == 503
            data = response.json()

            assert data["status"] == "not_ready"
            assert data["checks"]["secrets"]["status"] == "unhealthy"
            assert "ANTHROPIC_API_KEY" in data["checks"]["secrets"]["missing"]
            assert "JWT_SECRET_KEY" in data["checks"]["secrets"]["missing"]

    @patch("mcp_server_langgraph.health.checks.settings")
    def test_readiness_check_openfga_not_configured(self, mock_settings, test_client):
        """Test readiness check when OpenFGA is not configured"""
        mock_settings.openfga_store_id = None
        mock_settings.openfga_model_id = None
        mock_settings.anthropic_api_key = "test-key"
        mock_settings.jwt_secret_key = "test-secret"
        mock_settings.service_version = "1.0.0"
        mock_settings.infisical_site_url = "https://infisical.com"

        with patch("mcp_server_langgraph.health.checks.get_secrets_manager") as mock_get_secrets:
            mock_secrets_mgr = MagicMock()
            mock_secrets_mgr.client = None
            mock_get_secrets.return_value = mock_secrets_mgr

            response = test_client.get("/health/ready")

            assert response.status_code == 200
            data = response.json()

            assert data["checks"]["openfga"]["status"] == "not_configured"

    @patch("mcp_server_langgraph.health.checks.settings")
    def test_readiness_check_infisical_degraded(self, mock_settings, test_client):
        """Test readiness check when Infisical is degraded"""
        mock_settings.openfga_store_id = None
        mock_settings.openfga_model_id = None
        mock_settings.anthropic_api_key = "test-key"
        mock_settings.jwt_secret_key = "test-secret"
        mock_settings.service_version = "1.0.0"
        mock_settings.infisical_site_url = "https://infisical.com"

        with patch("mcp_server_langgraph.health.checks.get_secrets_manager") as mock_get_secrets:
            mock_get_secrets.side_effect = Exception("Infisical connection failed")

            response = test_client.get("/health/ready")

            # Should still be healthy (degraded mode with fallback)
            assert response.status_code == 200
            data = response.json()

            assert data["checks"]["infisical"]["status"] == "degraded"
            assert "Fallback mode active" in data["checks"]["infisical"]["message"]

    @patch("mcp_server_langgraph.health.checks.settings")
    @patch("mcp_server_langgraph.health.checks.logger")
    def test_startup_check_success(self, mock_logger, mock_settings, test_client):
        """Test startup probe returns started status"""
        mock_settings.service_name = "mcp-server-langgraph"
        mock_settings.service_version = "1.0.0"

        response = test_client.get("/health/startup")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "started"
        assert "timestamp" in data
        assert data["checks"]["config"]["status"] == "loaded"
        assert data["checks"]["logging"]["status"] == "initialized"

    @patch("mcp_server_langgraph.health.checks.settings")
    @patch("mcp_server_langgraph.health.checks.logger")
    def test_startup_check_logging_failed(self, mock_logger, mock_settings, test_client):
        """Test startup probe when logging initialization fails"""
        mock_settings.service_name = "mcp-server-langgraph"
        mock_logger.info.side_effect = Exception("Logger initialization failed")

        response = test_client.get("/health/startup")

        assert response.status_code == 503
        data = response.json()

        assert data["status"] == "starting"
        assert data["checks"]["logging"]["status"] == "failed"

    @patch("mcp_server_langgraph.health.checks.settings")
    def test_prometheus_metrics_endpoint(self, mock_settings, test_client):
        """Test Prometheus metrics endpoint"""
        mock_settings.service_version = "1.0.0"
        mock_settings.service_name = "mcp-server-langgraph"

        response = test_client.get("/metrics/prometheus")

        assert response.status_code == 200
        data = response.json()

        # Verify metrics format
        assert "langgraph_agent_info" in str(data)
        assert "version" in str(data)


@pytest.mark.integration
class TestHealthCheckIntegration:
    """Integration tests for health checks"""

    @pytest.mark.skip(reason="Requires full infrastructure stack")
    def test_full_health_check_with_infrastructure(self, test_client):
        """Test health checks with real infrastructure components"""
        # This test would run with actual OpenFGA, Infisical, etc.
        response = test_client.get("/health/ready")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "ready"
        assert all(check["status"] in ["healthy", "not_configured"] for check in data["checks"].values())
