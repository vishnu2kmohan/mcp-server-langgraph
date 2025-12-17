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
    """Tests for the validate_qdrant_connectivity_async function.

    PYTEST-XDIST FIX (2025-12-16):
    ==============================
    Added setup_method to reset singleton dependencies and clean up any
    module-level mock pollution that might leak between xdist workers.
    """

    def setup_method(self) -> None:
        """Reset singleton dependencies to prevent xdist pollution."""
        from mcp_server_langgraph.core.dependencies import reset_singleton_dependencies

        reset_singleton_dependencies()

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        from mcp_server_langgraph.core.dependencies import reset_singleton_dependencies

        reset_singleton_dependencies()
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
    """Tests for Qdrant integration in startup validation.

    PYTEST-XDIST FIX (2025-12-16):
    ==============================
    Added setup_method to reset singleton dependencies and clean up any
    module-level mock pollution that might leak between xdist workers.
    """

    def setup_method(self) -> None:
        """Reset singleton dependencies to prevent xdist pollution."""
        from mcp_server_langgraph.core.dependencies import reset_singleton_dependencies

        reset_singleton_dependencies()

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        from mcp_server_langgraph.core.dependencies import reset_singleton_dependencies

        reset_singleton_dependencies()
        gc.collect()

    @pytest.mark.asyncio
    async def test_startup_validation_includes_qdrant_check(self) -> None:
        """Test that run_startup_validation_async includes Qdrant check.

        PYTEST-XDIST FIX (2025-12-16): Use side_effect=lambda instead of
        return_value to prevent MagicMock pollution across xdist workers.
        """
        from mcp_server_langgraph.api.health import run_startup_validation_async

        # PYTEST-XDIST FIX: Track calls via mutable container
        call_tracker = {"qdrant_called": False}

        async def mock_qdrant_validation():
            call_tracker["qdrant_called"] = True
            return (True, "Qdrant connected")

        # Mock all validations to return success using side_effect for xdist safety
        with (
            patch(
                "mcp_server_langgraph.api.health.validate_observability_initialized",
                side_effect=lambda: (True, "OK"),
            ),
            patch(
                "mcp_server_langgraph.api.health.validate_session_store_registered",
                side_effect=lambda: (True, "OK"),
            ),
            patch(
                "mcp_server_langgraph.api.health.validate_api_key_cache_configured",
                side_effect=lambda: (True, "OK"),
            ),
            patch(
                "mcp_server_langgraph.api.health.validate_docker_sandbox_security",
                side_effect=lambda: (True, "OK"),
            ),
            patch(
                "mcp_server_langgraph.api.health.validate_database_connectivity_async",
                new_callable=AsyncMock,
                side_effect=lambda: (True, "OK"),
            ),
            patch(
                "mcp_server_langgraph.api.health.validate_qdrant_connectivity_async",
                new_callable=AsyncMock,
                side_effect=mock_qdrant_validation,
            ),
            patch(
                "mcp_server_langgraph.api.health.validate_loki_connectivity_async",
                new_callable=AsyncMock,
                side_effect=lambda: (True, "Loki disabled"),
            ),
            patch(
                "mcp_server_langgraph.api.health.validate_tempo_connectivity_async",
                new_callable=AsyncMock,
                side_effect=lambda: (True, "Tempo disabled"),
            ),
            patch(
                "mcp_server_langgraph.api.health.validate_mimir_connectivity_async",
                new_callable=AsyncMock,
                side_effect=lambda: (True, "Mimir disabled"),
            ),
            patch("mcp_server_langgraph.api.health.settings") as mock_settings,
            patch(
                "mcp_server_langgraph.api.health.bootstrap_qdrant_default_collection_async",
                new_callable=AsyncMock,
                side_effect=lambda: (True, "Bootstrap skipped"),
            ),
        ):
            # Disable Qdrant URL to skip bootstrap step
            mock_settings.qdrant_url = ""

            # Should not raise
            await run_startup_validation_async()

            # Qdrant validation should have been called
            assert call_tracker["qdrant_called"], "Expected Qdrant validation to be called"

    @pytest.mark.asyncio
    async def test_startup_validation_fails_on_qdrant_error_when_required(self) -> None:
        """Test that startup fails when Qdrant validation fails and is required."""
        from mcp_server_langgraph.api.health import (
            SystemValidationError,
            run_startup_validation_async,
        )

        # PYTEST-XDIST FIX: Use side_effect factory functions instead of return_value
        # to prevent mock pollution across xdist workers
        async def mock_db_validation():
            return (True, "OK")

        async def mock_qdrant_validation():
            return (False, "Qdrant connection refused")

        async def mock_loki_validation():
            return (True, "Loki disabled")

        async def mock_tempo_validation():
            return (True, "Tempo disabled")

        async def mock_mimir_validation():
            return (True, "Mimir disabled")

        # Mock Qdrant as failing, others as success
        with (
            patch(
                "mcp_server_langgraph.api.health.validate_observability_initialized",
                side_effect=lambda: (True, "OK"),
            ),
            patch(
                "mcp_server_langgraph.api.health.validate_session_store_registered",
                side_effect=lambda: (True, "OK"),
            ),
            patch(
                "mcp_server_langgraph.api.health.validate_api_key_cache_configured",
                side_effect=lambda: (True, "OK"),
            ),
            patch(
                "mcp_server_langgraph.api.health.validate_docker_sandbox_security",
                side_effect=lambda: (True, "OK"),
            ),
            patch(
                "mcp_server_langgraph.api.health.validate_database_connectivity_async",
                new_callable=AsyncMock,
                side_effect=mock_db_validation,
            ),
            patch(
                "mcp_server_langgraph.api.health.validate_qdrant_connectivity_async",
                new_callable=AsyncMock,
                side_effect=mock_qdrant_validation,
            ),
            patch(
                "mcp_server_langgraph.api.health.validate_loki_connectivity_async",
                new_callable=AsyncMock,
                side_effect=mock_loki_validation,
            ),
            patch(
                "mcp_server_langgraph.api.health.validate_tempo_connectivity_async",
                new_callable=AsyncMock,
                side_effect=mock_tempo_validation,
            ),
            patch(
                "mcp_server_langgraph.api.health.validate_mimir_connectivity_async",
                new_callable=AsyncMock,
                side_effect=mock_mimir_validation,
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
    """Tests for Qdrant integration in health check endpoint.

    PYTEST-XDIST FIX (2025-12-16):
    ==============================
    Added setup_method to reset singleton dependencies and clean up any
    module-level mock pollution that might leak between xdist workers.
    """

    def setup_method(self) -> None:
        """Reset singleton dependencies to prevent xdist pollution."""
        from mcp_server_langgraph.core.dependencies import reset_singleton_dependencies

        reset_singleton_dependencies()

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        from mcp_server_langgraph.core.dependencies import reset_singleton_dependencies

        reset_singleton_dependencies()
        gc.collect()

    @pytest.mark.asyncio
    async def test_health_endpoint_includes_qdrant_status(self) -> None:
        """Test that health check endpoint includes Qdrant status."""
        from mcp_server_langgraph.api.health import health_check

        # PYTEST-XDIST FIX: Use side_effect factory functions instead of return_value
        async def mock_db_validation():
            return (True, "OK")

        async def mock_qdrant_validation():
            return (True, "Qdrant connected")

        async def mock_loki_validation():
            return (True, "Loki disabled")

        async def mock_tempo_validation():
            return (True, "Tempo disabled")

        async def mock_mimir_validation():
            return (True, "Mimir disabled")

        # Mock all validations
        with (
            patch(
                "mcp_server_langgraph.api.health.validate_observability_initialized",
                side_effect=lambda: (True, "OK"),
            ),
            patch(
                "mcp_server_langgraph.api.health.validate_session_store_registered",
                side_effect=lambda: (True, "OK"),
            ),
            patch(
                "mcp_server_langgraph.api.health.validate_api_key_cache_configured",
                side_effect=lambda: (True, "OK"),
            ),
            patch(
                "mcp_server_langgraph.api.health.validate_docker_sandbox_security",
                side_effect=lambda: (True, "OK"),
            ),
            patch(
                "mcp_server_langgraph.api.health.validate_database_connectivity_async",
                new_callable=AsyncMock,
                side_effect=mock_db_validation,
            ),
            patch(
                "mcp_server_langgraph.api.health.validate_qdrant_connectivity_async",
                new_callable=AsyncMock,
                side_effect=mock_qdrant_validation,
            ),
            patch(
                "mcp_server_langgraph.api.health.validate_loki_connectivity_async",
                new_callable=AsyncMock,
                side_effect=mock_loki_validation,
            ),
            patch(
                "mcp_server_langgraph.api.health.validate_tempo_connectivity_async",
                new_callable=AsyncMock,
                side_effect=mock_tempo_validation,
            ),
            patch(
                "mcp_server_langgraph.api.health.validate_mimir_connectivity_async",
                new_callable=AsyncMock,
                side_effect=mock_mimir_validation,
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

        # PYTEST-XDIST FIX: Use side_effect factory functions instead of return_value
        async def mock_db_validation():
            return (True, "OK")

        async def mock_qdrant_validation():
            return (False, "Qdrant connection refused")

        async def mock_loki_validation():
            return (True, "Loki disabled")

        async def mock_tempo_validation():
            return (True, "Tempo disabled")

        async def mock_mimir_validation():
            return (True, "Mimir disabled")

        # Mock Qdrant as failing
        with (
            patch(
                "mcp_server_langgraph.api.health.validate_observability_initialized",
                side_effect=lambda: (True, "OK"),
            ),
            patch(
                "mcp_server_langgraph.api.health.validate_session_store_registered",
                side_effect=lambda: (True, "OK"),
            ),
            patch(
                "mcp_server_langgraph.api.health.validate_api_key_cache_configured",
                side_effect=lambda: (True, "OK"),
            ),
            patch(
                "mcp_server_langgraph.api.health.validate_docker_sandbox_security",
                side_effect=lambda: (True, "OK"),
            ),
            patch(
                "mcp_server_langgraph.api.health.validate_database_connectivity_async",
                new_callable=AsyncMock,
                side_effect=mock_db_validation,
            ),
            patch(
                "mcp_server_langgraph.api.health.validate_qdrant_connectivity_async",
                new_callable=AsyncMock,
                side_effect=mock_qdrant_validation,
            ),
            patch(
                "mcp_server_langgraph.api.health.validate_loki_connectivity_async",
                new_callable=AsyncMock,
                side_effect=mock_loki_validation,
            ),
            patch(
                "mcp_server_langgraph.api.health.validate_tempo_connectivity_async",
                new_callable=AsyncMock,
                side_effect=mock_tempo_validation,
            ),
            patch(
                "mcp_server_langgraph.api.health.validate_mimir_connectivity_async",
                new_callable=AsyncMock,
                side_effect=mock_mimir_validation,
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

    PYTEST-XDIST FIX (2025-12-16):
    ==============================
    Added setup_method to reset singleton dependencies and clean up any
    module-level mock pollution that might leak between xdist workers.
    """

    def setup_method(self) -> None:
        """Reset singleton dependencies to prevent xdist pollution."""
        from mcp_server_langgraph.core.dependencies import reset_singleton_dependencies

        reset_singleton_dependencies()

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        from mcp_server_langgraph.core.dependencies import reset_singleton_dependencies

        reset_singleton_dependencies()
        gc.collect()

    @pytest.mark.asyncio
    async def test_bootstrap_called_during_startup_when_qdrant_configured(self) -> None:
        """
        GIVEN: Qdrant URL is configured and enable_dynamic_context_loading=True
        WHEN: run_startup_validation_async is called
        THEN: bootstrap_qdrant_collection should be called with default collection

        PYTEST-XDIST FIX (2025-12-16): Use side_effect factory functions instead of return_value
        to prevent mock pollution across xdist workers.
        """
        from mcp_server_langgraph.api.health import run_startup_validation_async

        # PYTEST-XDIST FIX: Track calls via mutable container
        call_tracker = {"bootstrap_called": False}

        async def mock_bootstrap_success():
            call_tracker["bootstrap_called"] = True
            return (True, "Qdrant collection 'mcp_context' already exists")

        async def mock_db_validation():
            return (True, "OK")

        async def mock_qdrant_validation():
            return (True, "Connected")

        async def mock_loki_validation():
            return (True, "Disabled")

        async def mock_tempo_validation():
            return (True, "Disabled")

        async def mock_mimir_validation():
            return (True, "Disabled")

        with (
            # Mock all validations to pass - use side_effect for xdist safety
            patch(
                "mcp_server_langgraph.api.health.validate_observability_initialized",
                side_effect=lambda: (True, "OK"),
            ),
            patch(
                "mcp_server_langgraph.api.health.validate_session_store_registered",
                side_effect=lambda: (True, "OK"),
            ),
            patch(
                "mcp_server_langgraph.api.health.validate_api_key_cache_configured",
                side_effect=lambda: (True, "OK"),
            ),
            patch(
                "mcp_server_langgraph.api.health.validate_docker_sandbox_security",
                side_effect=lambda: (True, "OK"),
            ),
            patch(
                "mcp_server_langgraph.api.health.validate_database_connectivity_async",
                new_callable=AsyncMock,
                side_effect=mock_db_validation,
            ),
            patch(
                "mcp_server_langgraph.api.health.validate_qdrant_connectivity_async",
                new_callable=AsyncMock,
                side_effect=mock_qdrant_validation,
            ),
            patch(
                "mcp_server_langgraph.api.health.validate_loki_connectivity_async",
                new_callable=AsyncMock,
                side_effect=mock_loki_validation,
            ),
            patch(
                "mcp_server_langgraph.api.health.validate_tempo_connectivity_async",
                new_callable=AsyncMock,
                side_effect=mock_tempo_validation,
            ),
            patch(
                "mcp_server_langgraph.api.health.validate_mimir_connectivity_async",
                new_callable=AsyncMock,
                side_effect=mock_mimir_validation,
            ),
            patch("mcp_server_langgraph.api.health.settings") as mock_settings,
            patch(
                "mcp_server_langgraph.api.health.bootstrap_qdrant_default_collection_async",
                new_callable=AsyncMock,
                side_effect=mock_bootstrap_success,
            ),
        ):
            mock_settings.qdrant_url = "http://localhost:6333"
            mock_settings.enable_dynamic_context_loading = True
            mock_settings.qdrant_collection_name = "mcp_context"

            await run_startup_validation_async()

            # Bootstrap should have been called
            assert call_tracker["bootstrap_called"], "Expected bootstrap to be called"

    @pytest.mark.asyncio
    async def test_bootstrap_skipped_when_qdrant_not_configured(self) -> None:
        """
        GIVEN: Qdrant URL is empty (not configured)
        WHEN: run_startup_validation_async is called
        THEN: bootstrap_qdrant_collection should NOT be called

        PYTEST-XDIST FIX (2025-12-16): Use side_effect factory functions instead of return_value
        to prevent mock pollution across xdist workers.
        """
        from mcp_server_langgraph.api.health import run_startup_validation_async

        # PYTEST-XDIST FIX: Track calls via mutable container
        call_tracker = {"bootstrap_called": False}

        async def mock_bootstrap_should_not_be_called():
            call_tracker["bootstrap_called"] = True
            return (True, "Should not be called")

        async def mock_db_validation():
            return (True, "OK")

        async def mock_qdrant_validation():
            return (True, "Disabled - not configured")

        async def mock_loki_validation():
            return (True, "Disabled")

        async def mock_tempo_validation():
            return (True, "Disabled")

        async def mock_mimir_validation():
            return (True, "Disabled")

        with (
            patch(
                "mcp_server_langgraph.api.health.validate_observability_initialized",
                side_effect=lambda: (True, "OK"),
            ),
            patch(
                "mcp_server_langgraph.api.health.validate_session_store_registered",
                side_effect=lambda: (True, "OK"),
            ),
            patch(
                "mcp_server_langgraph.api.health.validate_api_key_cache_configured",
                side_effect=lambda: (True, "OK"),
            ),
            patch(
                "mcp_server_langgraph.api.health.validate_docker_sandbox_security",
                side_effect=lambda: (True, "OK"),
            ),
            patch(
                "mcp_server_langgraph.api.health.validate_database_connectivity_async",
                new_callable=AsyncMock,
                side_effect=mock_db_validation,
            ),
            patch(
                "mcp_server_langgraph.api.health.validate_qdrant_connectivity_async",
                new_callable=AsyncMock,
                side_effect=mock_qdrant_validation,
            ),
            patch(
                "mcp_server_langgraph.api.health.validate_loki_connectivity_async",
                new_callable=AsyncMock,
                side_effect=mock_loki_validation,
            ),
            patch(
                "mcp_server_langgraph.api.health.validate_tempo_connectivity_async",
                new_callable=AsyncMock,
                side_effect=mock_tempo_validation,
            ),
            patch(
                "mcp_server_langgraph.api.health.validate_mimir_connectivity_async",
                new_callable=AsyncMock,
                side_effect=mock_mimir_validation,
            ),
            patch("mcp_server_langgraph.api.health.settings") as mock_settings,
            patch(
                "mcp_server_langgraph.api.health.bootstrap_qdrant_default_collection_async",
                new_callable=AsyncMock,
                side_effect=mock_bootstrap_should_not_be_called,
            ),
        ):
            mock_settings.qdrant_url = ""
            mock_settings.enable_dynamic_context_loading = False

            await run_startup_validation_async()

            # Bootstrap should NOT have been called
            assert not call_tracker["bootstrap_called"], "Bootstrap should not be called when Qdrant not configured"

    @pytest.mark.asyncio
    async def test_bootstrap_failure_does_not_block_startup(self) -> None:
        """
        GIVEN: Qdrant is configured but bootstrap fails
        WHEN: run_startup_validation_async is called
        THEN: Startup should continue (graceful degradation)

        PYTEST-XDIST FIX (2025-12-16): Use side_effect factory functions instead of return_value
        to prevent mock pollution across xdist workers.
        """
        from mcp_server_langgraph.api.health import run_startup_validation_async

        # PYTEST-XDIST FIX: Track calls via mutable container
        call_tracker = {"bootstrap_called": False, "warning_logged": False}

        async def mock_bootstrap_fails():
            call_tracker["bootstrap_called"] = True
            return (False, "Qdrant bootstrap failed: Permission denied")

        async def mock_db_validation():
            return (True, "OK")

        async def mock_qdrant_validation():
            return (True, "Connected")

        async def mock_loki_validation():
            return (True, "Disabled")

        async def mock_tempo_validation():
            return (True, "Disabled")

        async def mock_mimir_validation():
            return (True, "Disabled")

        def mock_warning_call(*args, **kwargs):
            call_tracker["warning_logged"] = True

        with (
            patch(
                "mcp_server_langgraph.api.health.validate_observability_initialized",
                side_effect=lambda: (True, "OK"),
            ),
            patch(
                "mcp_server_langgraph.api.health.validate_session_store_registered",
                side_effect=lambda: (True, "OK"),
            ),
            patch(
                "mcp_server_langgraph.api.health.validate_api_key_cache_configured",
                side_effect=lambda: (True, "OK"),
            ),
            patch(
                "mcp_server_langgraph.api.health.validate_docker_sandbox_security",
                side_effect=lambda: (True, "OK"),
            ),
            patch(
                "mcp_server_langgraph.api.health.validate_database_connectivity_async",
                new_callable=AsyncMock,
                side_effect=mock_db_validation,
            ),
            patch(
                "mcp_server_langgraph.api.health.validate_qdrant_connectivity_async",
                new_callable=AsyncMock,
                side_effect=mock_qdrant_validation,
            ),
            patch(
                "mcp_server_langgraph.api.health.validate_loki_connectivity_async",
                new_callable=AsyncMock,
                side_effect=mock_loki_validation,
            ),
            patch(
                "mcp_server_langgraph.api.health.validate_tempo_connectivity_async",
                new_callable=AsyncMock,
                side_effect=mock_tempo_validation,
            ),
            patch(
                "mcp_server_langgraph.api.health.validate_mimir_connectivity_async",
                new_callable=AsyncMock,
                side_effect=mock_mimir_validation,
            ),
            patch("mcp_server_langgraph.api.health.settings") as mock_settings,
            patch(
                "mcp_server_langgraph.api.health.bootstrap_qdrant_default_collection_async",
                new_callable=AsyncMock,
                side_effect=mock_bootstrap_fails,
            ),
            patch("mcp_server_langgraph.api.health.logger") as mock_logger,
        ):
            mock_settings.qdrant_url = "http://localhost:6333"
            mock_settings.enable_dynamic_context_loading = True
            mock_settings.qdrant_collection_name = "mcp_context"

            # Track warning calls via side_effect
            mock_logger.warning.side_effect = mock_warning_call

            # Should NOT raise - graceful degradation
            await run_startup_validation_async()

            # Warning should be logged (bootstrap was called but startup didn't fail)
            assert call_tracker["bootstrap_called"], "Bootstrap should have been called"
            assert call_tracker["warning_logged"], "Warning should have been logged for bootstrap failure"
