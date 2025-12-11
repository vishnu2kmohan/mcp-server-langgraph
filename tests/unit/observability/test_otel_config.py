"""
Tests for OTEL (OpenTelemetry) configuration environment variable handling.

This test follows TDD principles:
- Written FIRST to define expected behavior for OTEL_EXPORTER_OTLP_ENDPOINT
- Fails initially (RED phase) because config doesn't read standard env var
- Passes after adding validation_alias to config.py (GREEN phase)

See: ADR-0026, Grafana LGTM stack integration
"""

import gc
import os
from unittest.mock import patch

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="otel_config_tests")
class TestOtelEndpointConfiguration:
    """Test OTEL endpoint configuration reads from standard environment variables."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_otlp_endpoint_reads_from_otel_exporter_env_var(self) -> None:
        """
        Test that otlp_endpoint reads from OTEL_EXPORTER_OTLP_ENDPOINT env var.

        The OpenTelemetry standard environment variable is OTEL_EXPORTER_OTLP_ENDPOINT.
        The Settings model should read from this variable when set.

        This test was written to fix Grafana "No Data" issue where:
        - docker-compose.test.yml sets OTEL_EXPORTER_OTLP_ENDPOINT=http://alloy-test:4318
        - But the MCP server was using hardcoded localhost:4317 default

        GIVEN: OTEL_EXPORTER_OTLP_ENDPOINT is set in environment
        WHEN: Settings is instantiated
        THEN: otlp_endpoint should use the environment variable value
        """
        # Clear any cached settings instance to force re-instantiation
        # Use a fresh environment with only our test variable set
        test_env = {
            "OTEL_EXPORTER_OTLP_ENDPOINT": "http://alloy-test:4318",
            # Required settings to avoid validation errors
            "ENVIRONMENT": "development",  # Non-production to skip security checks
            "JWT_SECRET_KEY": "test-secret-for-unit-test",
            "GDPR_STORAGE_BACKEND": "memory",
            "AUTH_PROVIDER": "inmemory",
        }

        with patch.dict(os.environ, test_env, clear=True):
            # Import Settings fresh to pick up env vars
            from mcp_server_langgraph.core.config import Settings

            settings = Settings()

            assert settings.otlp_endpoint == "http://alloy-test:4318", (
                f"Expected otlp_endpoint to read from OTEL_EXPORTER_OTLP_ENDPOINT env var, but got: {settings.otlp_endpoint}"
            )

    def test_otlp_endpoint_fallback_to_default_when_env_not_set(self) -> None:
        """
        Test that otlp_endpoint uses default value when env var is not set.

        GIVEN: OTEL_EXPORTER_OTLP_ENDPOINT is NOT set in environment
        WHEN: Settings is instantiated
        THEN: otlp_endpoint should use the localhost default
        """
        test_env = {
            # Required settings only - no OTEL env var
            "ENVIRONMENT": "development",
            "JWT_SECRET_KEY": "test-secret-for-unit-test",
            "GDPR_STORAGE_BACKEND": "memory",
            "AUTH_PROVIDER": "inmemory",
        }

        with patch.dict(os.environ, test_env, clear=True):
            from mcp_server_langgraph.core.config import Settings

            settings = Settings()

            # Should use default value
            assert settings.otlp_endpoint == "http://localhost:4317", (
                f"Expected default localhost:4317 when env not set, but got: {settings.otlp_endpoint}"
            )

    def test_otlp_endpoint_also_accepts_custom_env_var_name(self) -> None:
        """
        Test that OTLP_ENDPOINT custom env var is also accepted for backwards compatibility.

        Some deployments may use OTLP_ENDPOINT instead of the standard
        OTEL_EXPORTER_OTLP_ENDPOINT. We should support both.

        GIVEN: OTLP_ENDPOINT is set (custom name)
        WHEN: Settings is instantiated
        THEN: otlp_endpoint should use the custom env var value
        """
        test_env = {
            "OTLP_ENDPOINT": "http://custom-collector:4317",
            "ENVIRONMENT": "development",
            "JWT_SECRET_KEY": "test-secret-for-unit-test",
            "GDPR_STORAGE_BACKEND": "memory",
            "AUTH_PROVIDER": "inmemory",
        }

        with patch.dict(os.environ, test_env, clear=True):
            from mcp_server_langgraph.core.config import Settings

            settings = Settings()

            assert settings.otlp_endpoint == "http://custom-collector:4317", (
                f"Expected otlp_endpoint to read from OTLP_ENDPOINT env var, but got: {settings.otlp_endpoint}"
            )

    def test_standard_otel_env_var_takes_precedence_over_custom(self) -> None:
        """
        Test that OTEL_EXPORTER_OTLP_ENDPOINT takes precedence over OTLP_ENDPOINT.

        When both are set, the standard OpenTelemetry env var should win.

        GIVEN: Both OTEL_EXPORTER_OTLP_ENDPOINT and OTLP_ENDPOINT are set
        WHEN: Settings is instantiated
        THEN: otlp_endpoint should use OTEL_EXPORTER_OTLP_ENDPOINT value
        """
        test_env = {
            "OTEL_EXPORTER_OTLP_ENDPOINT": "http://standard-otel:4318",
            "OTLP_ENDPOINT": "http://custom-should-not-use:4317",
            "ENVIRONMENT": "development",
            "JWT_SECRET_KEY": "test-secret-for-unit-test",
            "GDPR_STORAGE_BACKEND": "memory",
            "AUTH_PROVIDER": "inmemory",
        }

        with patch.dict(os.environ, test_env, clear=True):
            from mcp_server_langgraph.core.config import Settings

            settings = Settings()

            # Standard OTEL env var should take precedence
            assert settings.otlp_endpoint == "http://standard-otel:4318", (
                f"Expected OTEL_EXPORTER_OTLP_ENDPOINT to take precedence, but got: {settings.otlp_endpoint}"
            )
