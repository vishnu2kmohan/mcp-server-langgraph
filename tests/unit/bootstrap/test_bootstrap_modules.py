"""
Tests for bootstrap package modules.

TDD: These tests define the expected behavior for the bootstrap/ package
which handles app lifespan initialization in isolated, testable phases.
"""

import gc

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

pytestmark = pytest.mark.unit


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_bootstrap_module_imports")
class TestBootstrapModuleImports:
    """Test that all bootstrap modules can be imported."""

    def test_import_bootstrap_package(self):
        """Bootstrap package should be importable."""
        from mcp_server_langgraph import bootstrap

        assert bootstrap is not None

    def test_import_observability_bootstrap(self):
        """Observability bootstrap should be importable."""
        from mcp_server_langgraph.bootstrap import observability

        assert observability is not None
        assert hasattr(observability, "init_observability")

    def test_import_security_bootstrap(self):
        """Security bootstrap should be importable."""
        from mcp_server_langgraph.bootstrap import security

        assert security is not None
        assert hasattr(security, "init_auth")

    def test_import_storage_bootstrap(self):
        """Storage bootstrap should be importable."""
        from mcp_server_langgraph.bootstrap import storage

        assert storage is not None
        assert hasattr(storage, "init_storage")

    def test_import_http_bootstrap(self):
        """HTTP bootstrap should be importable."""
        from mcp_server_langgraph.bootstrap import http

        assert http is not None
        assert hasattr(http, "init_http_client")


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_observability_bootstrap")
class TestObservabilityBootstrap:
    """Test observability initialization."""

    def test_init_observability_returns_telemetry_state(self):
        """init_observability should return a TelemetryState."""
        from mcp_server_langgraph.bootstrap.observability import (
            init_observability,
            TelemetryState,
        )
        from mcp_server_langgraph.core.config import Settings

        settings = Settings()
        result = init_observability(settings)
        assert isinstance(result, TelemetryState)

    def test_telemetry_state_has_logger(self):
        """TelemetryState should have a logger attribute."""
        from mcp_server_langgraph.bootstrap.observability import TelemetryState

        state = TelemetryState()
        assert hasattr(state, "logger")


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_security_bootstrap")
class TestSecurityBootstrap:
    """Test security initialization."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_init_auth_returns_security_state(self):
        """init_auth should return a SecurityState."""
        from mcp_server_langgraph.bootstrap.security import (
            init_auth,
            SecurityState,
        )
        from mcp_server_langgraph.core.config import Settings

        settings = Settings()
        result = await init_auth(settings)
        assert isinstance(result, SecurityState)

    @pytest.mark.asyncio
    async def test_security_state_has_auth_middleware(self):
        """SecurityState should have auth_middleware attribute."""
        from mcp_server_langgraph.bootstrap.security import SecurityState

        state = SecurityState()
        assert hasattr(state, "auth_middleware")

    @pytest.mark.asyncio
    async def test_security_state_has_openfga_client(self):
        """SecurityState should have openfga_client attribute."""
        from mcp_server_langgraph.bootstrap.security import SecurityState

        state = SecurityState()
        assert hasattr(state, "openfga_client")


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_storage_bootstrap")
class TestStorageBootstrap:
    """Test storage initialization."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_init_storage_returns_storage_state(self):
        """init_storage should return a StorageState."""
        from mcp_server_langgraph.bootstrap.storage import (
            init_storage,
            StorageState,
        )
        from mcp_server_langgraph.core.config import Settings

        settings = Settings()
        result = await init_storage(settings)
        assert isinstance(result, StorageState)

    @pytest.mark.asyncio
    async def test_storage_state_has_audit_service(self):
        """StorageState should have audit_service attribute."""
        from mcp_server_langgraph.bootstrap.storage import StorageState

        state = StorageState()
        assert hasattr(state, "audit_service")

    @pytest.mark.asyncio
    async def test_storage_state_has_compliance_service(self):
        """StorageState should have compliance_service attribute."""
        from mcp_server_langgraph.bootstrap.storage import StorageState

        state = StorageState()
        assert hasattr(state, "compliance_service")

    @pytest.mark.asyncio
    async def test_storage_state_has_preferences_repository(self):
        """
        GIVEN the StorageState dataclass
        WHEN accessed
        THEN it should have a preferences_repository attribute.
        """
        from mcp_server_langgraph.bootstrap.storage import StorageState

        state = StorageState()
        assert hasattr(state, "preferences_repository")

    @pytest.mark.asyncio
    async def test_init_storage_initializes_preferences_repository(self):
        """
        GIVEN application settings
        WHEN init_storage is called
        THEN the StorageState should contain a preferences repository.
        """
        from mcp_server_langgraph.bootstrap.storage import init_storage
        from mcp_server_langgraph.core.config import Settings

        settings = Settings()
        result = await init_storage(settings)

        assert result.preferences_repository is not None

    @pytest.mark.asyncio
    async def test_init_storage_sets_global_preferences_repository(self):
        """
        GIVEN application settings
        WHEN init_storage is called
        THEN the global preferences repository should be set in notification_preferences module.
        """
        from mcp_server_langgraph.bootstrap.storage import init_storage
        from mcp_server_langgraph.core.config import Settings
        from mcp_server_langgraph.api.v1 import notification_preferences

        settings = Settings()
        await init_storage(settings)

        # Verify the global repository is set (not just using fallback)
        repo = notification_preferences.get_preferences_repository()
        assert repo is not None
        # Should not create a new in-memory fallback on each call
        repo2 = notification_preferences.get_preferences_repository()
        assert repo is repo2


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_http_bootstrap")
class TestHttpBootstrap:
    """Test HTTP client initialization."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_init_http_client_returns_http_state(self):
        """init_http_client should return an HttpState."""
        from mcp_server_langgraph.bootstrap.http import (
            init_http_client,
            HttpState,
        )
        from mcp_server_langgraph.core.config import Settings

        settings = Settings()
        result = await init_http_client(settings)
        assert isinstance(result, HttpState)

    @pytest.mark.asyncio
    async def test_http_state_has_client_manager(self):
        """HttpState should have http_client_manager attribute."""
        from mcp_server_langgraph.bootstrap.http import HttpState

        state = HttpState()
        assert hasattr(state, "http_client_manager")

    @pytest.mark.asyncio
    async def test_http_state_cleanup_closes_client(self):
        """HttpState.cleanup() should close the http client."""
        from mcp_server_langgraph.bootstrap.http import HttpState

        mock_manager = AsyncMock(return_value=None)  # async-mock-configured
        state = HttpState(http_client_manager=mock_manager)

        await state.cleanup()
        mock_manager.close.assert_called_once()


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_bootstrap_lifecycle")
class TestBootstrapLifecycle:
    """Test complete bootstrap lifecycle."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_bootstrap_all_returns_app_state(self):
        """bootstrap_all should return combined AppState."""
        from mcp_server_langgraph.bootstrap import bootstrap_all, AppState
        from mcp_server_langgraph.core.config import Settings

        settings = Settings()
        result = await bootstrap_all(settings)
        assert isinstance(result, AppState)

    @pytest.mark.asyncio
    async def test_app_state_has_all_components(self):
        """AppState should have all state components."""
        from mcp_server_langgraph.bootstrap import AppState

        state = AppState()
        assert hasattr(state, "telemetry")
        assert hasattr(state, "security")
        assert hasattr(state, "storage")
        assert hasattr(state, "http")

    @pytest.mark.asyncio
    async def test_app_state_cleanup_calls_all_cleanups(self):
        """AppState.cleanup() should cleanup all components."""
        from mcp_server_langgraph.bootstrap import AppState

        mock_security = AsyncMock(return_value=None)  # async-mock-configured
        mock_storage = AsyncMock(return_value=None)  # async-mock-configured
        mock_http = AsyncMock(return_value=None)  # async-mock-configured

        state = AppState(
            security=mock_security,
            storage=mock_storage,
            http=mock_http,
        )

        await state.cleanup()

        mock_security.cleanup.assert_called_once()
        mock_storage.cleanup.assert_called_once()
        mock_http.cleanup.assert_called_once()


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_bootstrap_streaming_wiring")
class TestBootstrapStreamingSettingsWiring:
    """Tests for StreamingSettings wiring through bootstrap_all.

    TDD RED Phase: These tests verify that bootstrap_all properly passes
    streaming settings to the WebSocket lifecycle initialization.
    """

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_bootstrap_all_passes_streaming_settings_to_websocket(self):
        """
        GIVEN Settings with custom streaming configuration
        WHEN bootstrap_all is called
        THEN should pass streaming settings to init_websocket_lifecycle.
        """
        from mcp_server_langgraph.bootstrap import bootstrap_all
        from mcp_server_langgraph.core.config import Settings

        settings = Settings(
            streaming_enabled=False,
            streaming_idle_cleanup_interval=120,
            streaming_metrics_cleanup_interval=600,
        )

        # Track what settings are passed to init_websocket_lifecycle
        captured_settings = []

        async def mock_init_websocket(streaming_settings=None):
            captured_settings.append(streaming_settings)
            # Return a mock WebSocketState
            mock_state = MagicMock()
            mock_state.cleanup = AsyncMock(return_value=None)  # async-mock-configured
            return mock_state

        with patch(
            "mcp_server_langgraph.bootstrap.init_websocket_lifecycle",
            side_effect=mock_init_websocket,
        ):
            state = await bootstrap_all(settings)
            await state.cleanup()

        # Verify streaming settings were passed
        assert len(captured_settings) == 1
        streaming_settings = captured_settings[0]
        assert streaming_settings is not None
        assert streaming_settings.streaming_enabled is False
        assert streaming_settings.streaming_idle_cleanup_interval == 120
        assert streaming_settings.streaming_metrics_cleanup_interval == 600

    @pytest.mark.asyncio
    async def test_bootstrap_all_extracts_streaming_settings_from_main_settings(self):
        """
        GIVEN Settings with all streaming fields
        WHEN bootstrap_all is called
        THEN should extract all streaming fields into StreamingSettings.
        """
        from mcp_server_langgraph.bootstrap import bootstrap_all
        from mcp_server_langgraph.core.config import Settings, StreamingSettings

        settings = Settings(
            streaming_enabled=True,
            streaming_idle_cleanup_interval=90,
            streaming_metrics_cleanup_interval=450,
            streaming_max_age_seconds=7200,
            streaming_max_chunk_size=32768,
        )

        captured_settings = []

        async def mock_init_websocket(streaming_settings=None):
            captured_settings.append(streaming_settings)
            mock_state = MagicMock()
            mock_state.cleanup = AsyncMock(return_value=None)  # async-mock-configured
            return mock_state

        with patch(
            "mcp_server_langgraph.bootstrap.init_websocket_lifecycle",
            side_effect=mock_init_websocket,
        ):
            state = await bootstrap_all(settings)
            await state.cleanup()

        streaming_settings = captured_settings[0]
        assert isinstance(streaming_settings, StreamingSettings)
        assert streaming_settings.streaming_enabled is True
        assert streaming_settings.streaming_idle_cleanup_interval == 90
        assert streaming_settings.streaming_metrics_cleanup_interval == 450
        assert streaming_settings.streaming_max_age_seconds == 7200
        assert streaming_settings.streaming_max_chunk_size == 32768

    @pytest.mark.asyncio
    async def test_bootstrap_websocket_lifecycle_uses_streaming_enabled(self):
        """
        GIVEN Settings with streaming_enabled=False
        WHEN bootstrap_all is called
        THEN lifecycle manager should not start cleanup tasks.
        """
        from mcp_server_langgraph.bootstrap import bootstrap_all
        from mcp_server_langgraph.core.config import Settings

        settings = Settings(streaming_enabled=False)

        with patch(
            "mcp_server_langgraph.api.v1.mcp_websocket._lifecycle_manager",
            None,
        ):
            state = await bootstrap_all(settings)

            # When streaming is disabled, cleanup task should not be started
            assert state.websocket is not None
            assert state.websocket.mcp_lifecycle_manager is not None
            assert state.websocket.mcp_lifecycle_manager.cleanup_task is None

            await state.cleanup()

    @pytest.mark.asyncio
    async def test_bootstrap_websocket_uses_configured_cleanup_intervals(self):
        """
        GIVEN Settings with custom cleanup intervals
        WHEN bootstrap_all is called
        THEN lifecycle manager should use configured intervals.
        """
        from mcp_server_langgraph.bootstrap import bootstrap_all
        from mcp_server_langgraph.core.config import Settings

        settings = Settings(
            streaming_enabled=True,
            streaming_idle_cleanup_interval=180,
            streaming_metrics_cleanup_interval=900,
        )

        with patch(
            "mcp_server_langgraph.api.v1.mcp_websocket._lifecycle_manager",
            None,
        ):
            state = await bootstrap_all(settings)

            manager = state.websocket.mcp_lifecycle_manager
            assert manager.cleanup_interval == 180
            assert manager.metrics_cleanup_interval == 900

            await state.cleanup()


# =============================================================================
# NEW: Tests for Skills Bootstrap - TDD RED Phase
# =============================================================================


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_skills_bootstrap")
class TestSkillsBootstrap:
    """Test skills system initialization.

    The skills bootstrap module should:
    1. Initialize the AutoUpdateScheduler if skills marketplace is enabled
    2. Register installed skills from disk
    3. Provide cleanup for scheduler shutdown
    """

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_import_skills_bootstrap(self):
        """Skills bootstrap module should be importable."""
        from mcp_server_langgraph.bootstrap import skills

        assert skills is not None
        assert hasattr(skills, "init_skills")
        assert hasattr(skills, "SkillsState")

    @pytest.mark.asyncio
    async def test_init_skills_returns_skills_state(self):
        """init_skills should return a SkillsState."""
        from mcp_server_langgraph.bootstrap.skills import (
            init_skills,
            SkillsState,
        )
        from mcp_server_langgraph.core.config import Settings

        settings = Settings()
        result = await init_skills(settings)
        assert isinstance(result, SkillsState)

    @pytest.mark.asyncio
    async def test_skills_state_has_auto_update_scheduler(self):
        """SkillsState should have auto_update_scheduler attribute."""
        from mcp_server_langgraph.bootstrap.skills import SkillsState

        state = SkillsState()
        assert hasattr(state, "auto_update_scheduler")

    @pytest.mark.asyncio
    async def test_skills_state_cleanup_stops_scheduler(self):
        """SkillsState.cleanup() should stop the scheduler."""
        from mcp_server_langgraph.bootstrap.skills import SkillsState

        mock_scheduler = MagicMock()
        mock_scheduler.stop = AsyncMock(return_value=None)
        state = SkillsState(auto_update_scheduler=mock_scheduler)

        await state.cleanup()
        mock_scheduler.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_init_skills_respects_feature_flag(self):
        """init_skills should not start scheduler if marketplace disabled."""
        from mcp_server_langgraph.bootstrap.skills import init_skills
        from mcp_server_langgraph.core.config import Settings

        # Disable skills marketplace
        settings = Settings()

        with patch("mcp_server_langgraph.skills.auto_update.is_auto_update_enabled", return_value=False):
            result = await init_skills(settings)

        # Scheduler should be None when disabled
        assert result.auto_update_scheduler is None

    @pytest.mark.asyncio
    async def test_init_skills_starts_scheduler_when_enabled(self):
        """init_skills should start scheduler when marketplace enabled."""
        from mcp_server_langgraph.bootstrap.skills import init_skills
        from mcp_server_langgraph.core.config import Settings

        settings = Settings()

        with patch("mcp_server_langgraph.skills.auto_update.is_auto_update_enabled", return_value=True):
            with patch("mcp_server_langgraph.skills.auto_update.AutoUpdateScheduler") as mock_scheduler_class:
                mock_scheduler = MagicMock()
                mock_scheduler.start = AsyncMock(return_value=None)
                mock_scheduler_class.return_value = mock_scheduler

                result = await init_skills(settings)

                assert result.auto_update_scheduler is mock_scheduler
                mock_scheduler.start.assert_called_once()


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_bootstrap_skills_integration")
class TestBootstrapSkillsIntegration:
    """Test skills bootstrap integration with bootstrap_all."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_app_state_has_skills_component(self):
        """AppState should have skills state component."""
        from mcp_server_langgraph.bootstrap import AppState

        state = AppState()
        assert hasattr(state, "skills")

    @pytest.mark.asyncio
    async def test_bootstrap_all_initializes_skills(self):
        """bootstrap_all should initialize skills state."""
        from mcp_server_langgraph.bootstrap import bootstrap_all
        from mcp_server_langgraph.core.config import Settings

        settings = Settings()

        with patch("mcp_server_langgraph.skills.auto_update.is_auto_update_enabled", return_value=False):
            state = await bootstrap_all(settings)

            assert hasattr(state, "skills")
            assert state.skills is not None

            await state.cleanup()
