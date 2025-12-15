"""
Unit tests for Qdrant connectivity validation in health checks.

Tests verify that Qdrant validation is properly integrated into:
- Startup validation (`run_startup_validation_async`)
- Health check endpoint (`/api/v1/health`)

TDD RED Phase: These tests define expected behavior for Qdrant validation integration.
"""

import gc
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.health]


@pytest.mark.xdist_group(name="qdrant_validation")
class TestQdrantValidationFunction:
    """Tests for the validate_qdrant_connectivity_async function."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_validate_qdrant_success(self) -> None:
        """Test successful Qdrant connectivity validation."""
        from mcp_server_langgraph.api.health import validate_qdrant_connectivity_async

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.message = "Connected successfully. Found 2 collection(s)."

        with (
            patch("mcp_server_langgraph.api.health.settings") as mock_settings,
            patch(
                "mcp_server_langgraph.core.startup_validation.validate_qdrant_connection",
                new_callable=AsyncMock,
                return_value=mock_result,
            ),
        ):
            # Enable Qdrant validation by setting a URL
            mock_settings.qdrant_url = "http://localhost:6333"
            mock_settings.enable_dynamic_context_loading = True

            is_healthy, message = await validate_qdrant_connectivity_async()

        assert is_healthy is True
        assert "Connected" in message or "collection" in message

    @pytest.mark.asyncio
    async def test_validate_qdrant_failure(self) -> None:
        """Test Qdrant connectivity validation when connection fails."""
        from mcp_server_langgraph.api.health import validate_qdrant_connectivity_async

        mock_result = MagicMock()
        mock_result.success = False
        mock_result.error = "Connection refused"

        with (
            patch("mcp_server_langgraph.api.health.settings") as mock_settings,
            patch(
                "mcp_server_langgraph.core.startup_validation.validate_qdrant_connection",
                new_callable=AsyncMock,
                return_value=mock_result,
            ),
        ):
            # Enable Qdrant validation by setting a URL
            mock_settings.qdrant_url = "http://localhost:6333"
            mock_settings.enable_dynamic_context_loading = True

            is_healthy, message = await validate_qdrant_connectivity_async()

        assert is_healthy is False
        assert "Connection refused" in message or "failed" in message.lower()

    @pytest.mark.asyncio
    async def test_validate_qdrant_skipped_when_disabled(self) -> None:
        """Test that Qdrant validation is skipped when not configured."""
        from mcp_server_langgraph.api.health import validate_qdrant_connectivity_async

        # When Qdrant URL is not configured, validation should skip gracefully
        with patch("mcp_server_langgraph.api.health.settings") as mock_settings:
            mock_settings.qdrant_url = ""
            mock_settings.enable_dynamic_context_loading = False

            is_healthy, message = await validate_qdrant_connectivity_async()

        assert is_healthy is True
        assert "disabled" in message.lower() or "not configured" in message.lower()


@pytest.mark.xdist_group(name="qdrant_validation")
class TestStartupValidationIncludesQdrant:
    """Tests for Qdrant integration in startup validation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_startup_validation_includes_qdrant_check(self) -> None:
        """Test that run_startup_validation_async includes Qdrant check."""
        from mcp_server_langgraph.api.health import run_startup_validation_async

        # Mock all validations to return success
        with (
            patch(
                "mcp_server_langgraph.api.health.validate_observability_initialized",
                return_value=(True, "OK"),
            ),
            patch(
                "mcp_server_langgraph.api.health.validate_session_store_registered",
                return_value=(True, "OK"),
            ),
            patch(
                "mcp_server_langgraph.api.health.validate_api_key_cache_configured",
                return_value=(True, "OK"),
            ),
            patch(
                "mcp_server_langgraph.api.health.validate_docker_sandbox_security",
                return_value=(True, "OK"),
            ),
            patch(
                "mcp_server_langgraph.api.health.validate_database_connectivity_async",
                new_callable=AsyncMock,
                return_value=(True, "OK"),
            ),
            patch(
                "mcp_server_langgraph.api.health.validate_qdrant_connectivity_async",
                new_callable=AsyncMock,
                return_value=(True, "Qdrant connected"),
            ) as mock_qdrant,
        ):
            # Should not raise
            await run_startup_validation_async()

            # Qdrant validation should have been called
            mock_qdrant.assert_called_once()

    @pytest.mark.asyncio
    async def test_startup_validation_fails_on_qdrant_error_when_required(self) -> None:
        """Test that startup fails when Qdrant validation fails and is required."""
        from mcp_server_langgraph.api.health import (
            SystemValidationError,
            run_startup_validation_async,
        )

        # Mock Qdrant as failing, others as success
        with (
            patch(
                "mcp_server_langgraph.api.health.validate_observability_initialized",
                return_value=(True, "OK"),
            ),
            patch(
                "mcp_server_langgraph.api.health.validate_session_store_registered",
                return_value=(True, "OK"),
            ),
            patch(
                "mcp_server_langgraph.api.health.validate_api_key_cache_configured",
                return_value=(True, "OK"),
            ),
            patch(
                "mcp_server_langgraph.api.health.validate_docker_sandbox_security",
                return_value=(True, "OK"),
            ),
            patch(
                "mcp_server_langgraph.api.health.validate_database_connectivity_async",
                new_callable=AsyncMock,
                return_value=(True, "OK"),
            ),
            patch(
                "mcp_server_langgraph.api.health.validate_qdrant_connectivity_async",
                new_callable=AsyncMock,
                return_value=(False, "Qdrant connection refused"),
            ),
            patch("mcp_server_langgraph.api.health.settings") as mock_settings,
        ):
            # Make Qdrant required (dynamic context loading enabled)
            mock_settings.enable_dynamic_context_loading = True
            mock_settings.qdrant_validation_required = True

            with pytest.raises(SystemValidationError) as exc_info:
                await run_startup_validation_async()

            assert "qdrant" in str(exc_info.value).lower()


@pytest.mark.xdist_group(name="qdrant_validation")
class TestHealthEndpointIncludesQdrant:
    """Tests for Qdrant integration in health check endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_health_endpoint_includes_qdrant_status(self) -> None:
        """Test that health check endpoint includes Qdrant status."""
        from mcp_server_langgraph.api.health import health_check

        # Mock all validations
        with (
            patch(
                "mcp_server_langgraph.api.health.validate_observability_initialized",
                return_value=(True, "OK"),
            ),
            patch(
                "mcp_server_langgraph.api.health.validate_session_store_registered",
                return_value=(True, "OK"),
            ),
            patch(
                "mcp_server_langgraph.api.health.validate_api_key_cache_configured",
                return_value=(True, "OK"),
            ),
            patch(
                "mcp_server_langgraph.api.health.validate_docker_sandbox_security",
                return_value=(True, "OK"),
            ),
            patch(
                "mcp_server_langgraph.api.health.validate_database_connectivity_async",
                new_callable=AsyncMock,
                return_value=(True, "OK"),
            ),
            patch(
                "mcp_server_langgraph.api.health.validate_qdrant_connectivity_async",
                new_callable=AsyncMock,
                return_value=(True, "Qdrant connected"),
            ),
        ):
            result = await health_check()

        # Health check should include qdrant in checks
        assert "qdrant" in result.checks or "qdrant_connectivity" in result.checks
        assert result.status == "healthy"

    @pytest.mark.asyncio
    async def test_health_endpoint_degraded_when_qdrant_fails(self) -> None:
        """Test that health status is degraded when Qdrant fails."""
        from mcp_server_langgraph.api.health import health_check

        # Mock Qdrant as failing
        with (
            patch(
                "mcp_server_langgraph.api.health.validate_observability_initialized",
                return_value=(True, "OK"),
            ),
            patch(
                "mcp_server_langgraph.api.health.validate_session_store_registered",
                return_value=(True, "OK"),
            ),
            patch(
                "mcp_server_langgraph.api.health.validate_api_key_cache_configured",
                return_value=(True, "OK"),
            ),
            patch(
                "mcp_server_langgraph.api.health.validate_docker_sandbox_security",
                return_value=(True, "OK"),
            ),
            patch(
                "mcp_server_langgraph.api.health.validate_database_connectivity_async",
                new_callable=AsyncMock,
                return_value=(True, "OK"),
            ),
            patch(
                "mcp_server_langgraph.api.health.validate_qdrant_connectivity_async",
                new_callable=AsyncMock,
                return_value=(False, "Qdrant connection refused"),
            ),
        ):
            result = await health_check()

        # When Qdrant fails, status should be unhealthy or degraded
        assert result.status in ["unhealthy", "degraded"]
        assert len(result.errors) > 0 or len(result.warnings) > 0


@pytest.mark.xdist_group(name="qdrant_validation")
class TestQdrantCollectionBootstrapAtStartup:
    """Tests for Qdrant collection bootstrap during startup.

    TDD RED Phase: These tests define expected behavior for automatic
    collection creation during app startup.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_bootstrap_called_during_startup_when_qdrant_configured(self) -> None:
        """
        GIVEN: Qdrant URL is configured and enable_dynamic_context_loading=True
        WHEN: run_startup_validation_async is called
        THEN: bootstrap_qdrant_collection should be called with default collection
        """
        from mcp_server_langgraph.api.health import run_startup_validation_async

        with (
            # Mock all validations to pass
            patch(
                "mcp_server_langgraph.api.health.validate_observability_initialized",
                return_value=(True, "OK"),
            ),
            patch(
                "mcp_server_langgraph.api.health.validate_session_store_registered",
                return_value=(True, "OK"),
            ),
            patch(
                "mcp_server_langgraph.api.health.validate_api_key_cache_configured",
                return_value=(True, "OK"),
            ),
            patch(
                "mcp_server_langgraph.api.health.validate_docker_sandbox_security",
                return_value=(True, "OK"),
            ),
            patch(
                "mcp_server_langgraph.api.health.validate_database_connectivity_async",
                new_callable=AsyncMock,
                return_value=(True, "OK"),
            ),
            patch(
                "mcp_server_langgraph.api.health.validate_qdrant_connectivity_async",
                new_callable=AsyncMock,
                return_value=(True, "Connected"),
            ),
            patch(
                "mcp_server_langgraph.api.health.validate_loki_connectivity_async",
                new_callable=AsyncMock,
                return_value=(True, "Disabled"),
            ),
            patch(
                "mcp_server_langgraph.api.health.validate_tempo_connectivity_async",
                new_callable=AsyncMock,
                return_value=(True, "Disabled"),
            ),
            patch(
                "mcp_server_langgraph.api.health.validate_mimir_connectivity_async",
                new_callable=AsyncMock,
                return_value=(True, "Disabled"),
            ),
            patch("mcp_server_langgraph.api.health.settings") as mock_settings,
            patch(
                "mcp_server_langgraph.api.health.bootstrap_qdrant_default_collection_async",
                new_callable=AsyncMock,
            ) as mock_bootstrap,
        ):
            mock_settings.qdrant_url = "http://localhost:6333"
            mock_settings.enable_dynamic_context_loading = True
            mock_settings.qdrant_collection_name = "mcp_context"

            # Mock bootstrap to return success tuple (bool, str)
            mock_bootstrap.return_value = (True, "Qdrant collection 'mcp_context' already exists")

            await run_startup_validation_async()

            # Bootstrap should have been called
            mock_bootstrap.assert_called_once()

    @pytest.mark.asyncio
    async def test_bootstrap_skipped_when_qdrant_not_configured(self) -> None:
        """
        GIVEN: Qdrant URL is empty (not configured)
        WHEN: run_startup_validation_async is called
        THEN: bootstrap_qdrant_collection should NOT be called
        """
        from mcp_server_langgraph.api.health import run_startup_validation_async

        with (
            patch(
                "mcp_server_langgraph.api.health.validate_observability_initialized",
                return_value=(True, "OK"),
            ),
            patch(
                "mcp_server_langgraph.api.health.validate_session_store_registered",
                return_value=(True, "OK"),
            ),
            patch(
                "mcp_server_langgraph.api.health.validate_api_key_cache_configured",
                return_value=(True, "OK"),
            ),
            patch(
                "mcp_server_langgraph.api.health.validate_docker_sandbox_security",
                return_value=(True, "OK"),
            ),
            patch(
                "mcp_server_langgraph.api.health.validate_database_connectivity_async",
                new_callable=AsyncMock,
                return_value=(True, "OK"),
            ),
            patch(
                "mcp_server_langgraph.api.health.validate_qdrant_connectivity_async",
                new_callable=AsyncMock,
                return_value=(True, "Disabled - not configured"),
            ),
            patch(
                "mcp_server_langgraph.api.health.validate_loki_connectivity_async",
                new_callable=AsyncMock,
                return_value=(True, "Disabled"),
            ),
            patch(
                "mcp_server_langgraph.api.health.validate_tempo_connectivity_async",
                new_callable=AsyncMock,
                return_value=(True, "Disabled"),
            ),
            patch(
                "mcp_server_langgraph.api.health.validate_mimir_connectivity_async",
                new_callable=AsyncMock,
                return_value=(True, "Disabled"),
            ),
            patch("mcp_server_langgraph.api.health.settings") as mock_settings,
            patch(
                "mcp_server_langgraph.api.health.bootstrap_qdrant_default_collection_async",
                new_callable=AsyncMock,
            ) as mock_bootstrap,
        ):
            mock_settings.qdrant_url = ""
            mock_settings.enable_dynamic_context_loading = False

            await run_startup_validation_async()

            # Bootstrap should NOT have been called
            mock_bootstrap.assert_not_called()

    @pytest.mark.asyncio
    async def test_bootstrap_failure_does_not_block_startup(self) -> None:
        """
        GIVEN: Qdrant is configured but bootstrap fails
        WHEN: run_startup_validation_async is called
        THEN: Startup should continue (graceful degradation)
        """
        from mcp_server_langgraph.api.health import run_startup_validation_async

        with (
            patch(
                "mcp_server_langgraph.api.health.validate_observability_initialized",
                return_value=(True, "OK"),
            ),
            patch(
                "mcp_server_langgraph.api.health.validate_session_store_registered",
                return_value=(True, "OK"),
            ),
            patch(
                "mcp_server_langgraph.api.health.validate_api_key_cache_configured",
                return_value=(True, "OK"),
            ),
            patch(
                "mcp_server_langgraph.api.health.validate_docker_sandbox_security",
                return_value=(True, "OK"),
            ),
            patch(
                "mcp_server_langgraph.api.health.validate_database_connectivity_async",
                new_callable=AsyncMock,
                return_value=(True, "OK"),
            ),
            patch(
                "mcp_server_langgraph.api.health.validate_qdrant_connectivity_async",
                new_callable=AsyncMock,
                return_value=(True, "Connected"),
            ),
            patch(
                "mcp_server_langgraph.api.health.validate_loki_connectivity_async",
                new_callable=AsyncMock,
                return_value=(True, "Disabled"),
            ),
            patch(
                "mcp_server_langgraph.api.health.validate_tempo_connectivity_async",
                new_callable=AsyncMock,
                return_value=(True, "Disabled"),
            ),
            patch(
                "mcp_server_langgraph.api.health.validate_mimir_connectivity_async",
                new_callable=AsyncMock,
                return_value=(True, "Disabled"),
            ),
            patch("mcp_server_langgraph.api.health.settings") as mock_settings,
            patch(
                "mcp_server_langgraph.api.health.bootstrap_qdrant_default_collection_async",
                new_callable=AsyncMock,
            ) as mock_bootstrap,
            patch("mcp_server_langgraph.api.health.logger") as mock_logger,
        ):
            mock_settings.qdrant_url = "http://localhost:6333"
            mock_settings.enable_dynamic_context_loading = True
            mock_settings.qdrant_collection_name = "mcp_context"

            # Bootstrap fails - return failure tuple (bool, str)
            mock_bootstrap.return_value = (False, "Qdrant bootstrap failed: Permission denied")

            # Should NOT raise - graceful degradation
            await run_startup_validation_async()

            # Warning should be logged
            mock_logger.warning.assert_called()
