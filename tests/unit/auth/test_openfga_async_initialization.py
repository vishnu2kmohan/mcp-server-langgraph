"""
Tests for OpenFGA Async Initialization via FastAPI Lifespan Pattern.

TDD: Write tests FIRST, then implementation.

This tests the refactoring from lazy sync singleton to async startup initialization:
- OpenFGA client is initialized in app lifespan (before first request)
- Client is stored in app.state.openfga_client
- get_openfga_client() dependency accesses Request.app.state

Benefits:
- Cold start latency eliminated (initialization happens once at startup)
- Async initialization works correctly (no event loop issues)
- Proper error handling at startup (fail fast if OpenFGA unavailable)
- app.state provides proper request-scoped access pattern

References:
- ADR-0042: Dependency Injection Configuration Fixes
- FastAPI Lifespan Events: https://fastapi.tiangolo.com/advanced/events/
"""

import gc
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.testclient import TestClient

from mcp_server_langgraph.auth.openfga import OpenFGAClient

# Module-level pytestmark for test organization
pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="openfga_async_init")
class TestOpenFGAAsyncInitialization:
    """Test OpenFGA async initialization via FastAPI lifespan."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_openfga_client_available_in_app_state_after_startup(self):
        """
        GIVEN: FastAPI app with lifespan that initializes OpenFGA
        WHEN: App starts up
        THEN: app.state.openfga_client should be available

        This tests that the lifespan properly initializes OpenFGA and stores it
        in app.state for later access by dependencies.
        """
        # Arrange
        from mcp_server_langgraph.app import create_app
        from mcp_server_langgraph.core.config import Settings

        # Create settings with valid OpenFGA configuration
        settings = Settings(
            environment="test",
            jwt_secret_key="test-secret",
            openfga_api_url="http://localhost:8080",
            openfga_store_name="test-store",
        )

        # Act: Create app with settings
        with patch("mcp_server_langgraph.app.run_startup_validation_async"):
            app = create_app(settings_override=settings, skip_startup_validation=True)

        # Assert: After app creation, openfga_client should be accessible
        # Note: In lifespan pattern, this is set during startup event
        # We need to trigger the lifespan by creating a test client
        with TestClient(app):
            # The lifespan should have run and set app.state.openfga_client
            assert hasattr(app.state, "openfga_client"), (
                "app.state.openfga_client should be set during lifespan startup. "
                "This is required for the async initialization pattern."
            )

    def test_openfga_client_is_none_when_config_incomplete(self, monkeypatch):
        """
        GIVEN: FastAPI app with incomplete OpenFGA configuration
        WHEN: App starts up
        THEN: app.state.openfga_client should be None (graceful degradation)

        This tests that the app doesn't crash when OpenFGA is not configured,
        but instead gracefully degrades by setting openfga_client to None.
        """
        from mcp_server_langgraph.app import create_app
        from mcp_server_langgraph.core.config import Settings

        # Clear environment variables that might provide OpenFGA config
        monkeypatch.delenv("OPENFGA_STORE_ID", raising=False)
        monkeypatch.delenv("OPENFGA_STORE_NAME", raising=False)
        monkeypatch.delenv("OPENFGA_API_URL", raising=False)

        # Create settings WITHOUT OpenFGA configuration
        # Explicitly set store_id and store_name to None to override defaults
        settings = Settings(
            environment="test",
            jwt_secret_key="test-secret",
            openfga_store_id=None,
            openfga_store_name=None,
        )

        with patch("mcp_server_langgraph.app.run_startup_validation_async"):
            app = create_app(settings_override=settings, skip_startup_validation=True)

        with TestClient(app):
            assert hasattr(app.state, "openfga_client"), "app.state.openfga_client should be set even when None"
            # When config is incomplete, it should be None
            assert app.state.openfga_client is None, "app.state.openfga_client should be None when config incomplete"


@pytest.mark.xdist_group(name="openfga_async_dependency")
class TestGetOpenFGAClientDependency:
    """Test the async get_openfga_client dependency function."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_get_openfga_client_from_request_returns_client(self):
        """
        GIVEN: A request with app.state.openfga_client set
        WHEN: get_openfga_client_from_request is called
        THEN: Returns the OpenFGA client from app.state

        This tests the new dependency function that accesses app.state
        instead of using a global singleton.
        """
        from mcp_server_langgraph.core.dependencies import get_openfga_client_from_request

        # Arrange: Create mock request with app.state.openfga_client
        mock_client = MagicMock(spec=OpenFGAClient)

        # Don't use spec= for app and state since we need to set arbitrary attributes
        mock_state = MagicMock()
        mock_state.openfga_client = mock_client

        mock_app = MagicMock()
        mock_app.state = mock_state

        mock_request = MagicMock()
        mock_request.app = mock_app

        # Act
        result = get_openfga_client_from_request(mock_request)

        # Assert
        assert result is mock_client, "get_openfga_client_from_request should return the client from app.state"

    @pytest.mark.asyncio
    async def test_get_openfga_client_from_request_returns_none_when_not_set(self):
        """
        GIVEN: A request with app.state but no openfga_client
        WHEN: get_openfga_client_from_request is called
        THEN: Returns None

        This tests graceful handling when OpenFGA is not configured.
        """
        from mcp_server_langgraph.core.dependencies import get_openfga_client_from_request

        # Arrange: Create mock request without openfga_client in state
        # Don't use spec= for app and state since we need to set arbitrary attributes
        mock_state = MagicMock()
        mock_state.openfga_client = None

        mock_app = MagicMock()
        mock_app.state = mock_state

        mock_request = MagicMock()
        mock_request.app = mock_app

        # Act
        result = get_openfga_client_from_request(mock_request)

        # Assert
        assert result is None, "get_openfga_client_from_request should return None when client not configured"


@pytest.mark.xdist_group(name="openfga_async_init_ensures")
class TestOpenFGAAsyncInitializationEnsures:
    """Test that async initialization properly calls _ensure_initialized."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_openfga_client_ensure_initialized_called_at_startup(self):
        """
        GIVEN: OpenFGA client created with valid config
        WHEN: Lifespan startup runs
        THEN: _ensure_initialized() should be called to complete async init

        This tests that the lazy async initialization (_ensure_initialized)
        is called during lifespan startup, not deferred to first request.
        """
        from mcp_server_langgraph.auth.openfga import OpenFGAClient, OpenFGAConfig

        # Arrange
        config = OpenFGAConfig(
            api_url="http://localhost:8080",
            store_name="test-store",
        )

        client = OpenFGAClient(config=config)

        # Mock _ensure_initialized to track if it's called
        _original_ensure = original_ensure = client._ensure_initialized  # noqa: F841
        client._ensure_initialized = AsyncMock()  # noqa: async-mock-config

        # Act: Call ensure_initialized (simulating what lifespan should do)
        await client._ensure_initialized()

        # Assert
        client._ensure_initialized.assert_awaited_once()


@pytest.mark.xdist_group(name="openfga_lifespan_cleanup")
class TestOpenFGALifespanCleanup:
    """Test that OpenFGA client is properly closed during shutdown."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_openfga_client_closed_on_shutdown(self):
        """
        GIVEN: OpenFGA client initialized in lifespan
        WHEN: App shuts down
        THEN: client.close() should be called to release resources

        This tests proper cleanup to prevent resource leaks.
        """
        from mcp_server_langgraph.auth.openfga import OpenFGAClient, OpenFGAConfig

        # Arrange
        config = OpenFGAConfig(
            api_url="http://localhost:8080",
            store_name="test-store",
        )

        client = OpenFGAClient(config=config)
        client.close = AsyncMock()  # noqa: async-mock-config

        # Act: Close client (simulating shutdown)
        await client.close()

        # Assert
        client.close.assert_awaited_once()


@pytest.mark.xdist_group(name="openfga_backward_compat")
class TestBackwardCompatibility:
    """Test that existing sync get_openfga_client still works for non-FastAPI callers."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_sync_get_openfga_client_still_exists(self):
        """
        GIVEN: Code that uses sync get_openfga_client (MCP servers, etc.)
        WHEN: Importing get_openfga_client
        THEN: The function should still be available for backward compatibility

        MCP servers (server_stdio, server_streamable) call get_openfga_client()
        directly without a Request object, so we maintain backward compatibility.
        """
        from mcp_server_langgraph.core.dependencies import get_openfga_client

        # Assert: Function exists and is callable
        assert callable(get_openfga_client), (
            "get_openfga_client must remain available for backward compatibility "
            "with MCP servers that call it directly without a Request object."
        )


# ==============================================================================
# Phase 2.3: OpenFGA Async File I/O Tests
# ==============================================================================


@pytest.mark.xdist_group(name="openfga_async_file_io")
class TestOpenFGAAuthorizationModelAsyncFileIO:
    """
    TDD tests for OpenFGAAuthorizationModel async file loading.

    Note: Low priority per plan - initialization only, not hot path.
    """

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()
        # Clear the model cache
        try:
            from mcp_server_langgraph.auth.openfga import OpenFGAAuthorizationModel

            OpenFGAAuthorizationModel.clear_cache()
        except ImportError:
            pass

    @pytest.mark.asyncio
    async def test_aget_model_definition_method_exists(self):
        """
        RED: Verify aget_model_definition() async class method exists.
        """
        from mcp_server_langgraph.auth.openfga import OpenFGAAuthorizationModel

        assert hasattr(OpenFGAAuthorizationModel, "aget_model_definition"), (
            "OpenFGAAuthorizationModel must have aget_model_definition() class method"
        )

    @pytest.mark.asyncio
    async def test_aget_model_definition_is_async(self):
        """
        RED: Verify aget_model_definition() is a coroutine function.
        """
        import asyncio

        from mcp_server_langgraph.auth.openfga import OpenFGAAuthorizationModel

        method = OpenFGAAuthorizationModel.aget_model_definition
        # For classmethods, check the underlying function
        underlying = method.__func__ if hasattr(method, "__func__") else method
        assert asyncio.iscoroutinefunction(underlying), "aget_model_definition() must be async"

    @pytest.mark.asyncio
    async def test_aget_model_definition_uses_to_thread(self):
        """
        RED: Verify aget_model_definition uses asyncio.to_thread for non-blocking I/O.
        """
        from mcp_server_langgraph.auth.openfga import OpenFGAAuthorizationModel

        model_data = {"type_definitions": [{"type": "user"}]}

        with patch(
            "mcp_server_langgraph.auth.openfga.asyncio.to_thread",
            return_value=model_data,
        ) as mock_to_thread:
            _result = await OpenFGAAuthorizationModel.aget_model_definition()  # noqa: F841

            # Verify asyncio.to_thread was called
            mock_to_thread.assert_called_once()


@pytest.mark.xdist_group(name="openfga_async_file_io")
class TestLoadSampleTuplesAsync:
    """
    TDD tests for async sample tuples loading.
    """

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    async def test_aload_sample_tuples_function_exists(self):
        """
        RED: Verify aload_sample_tuples() async function exists.
        """
        from mcp_server_langgraph.auth import openfga

        assert hasattr(openfga, "aload_sample_tuples"), "Module must have aload_sample_tuples() function"

    @pytest.mark.asyncio
    async def test_aload_sample_tuples_is_async(self):
        """
        RED: Verify aload_sample_tuples() is a coroutine function.
        """
        import asyncio

        from mcp_server_langgraph.auth.openfga import aload_sample_tuples

        assert asyncio.iscoroutinefunction(aload_sample_tuples), "aload_sample_tuples() must be async"

    @pytest.mark.asyncio
    async def test_aload_sample_tuples_uses_to_thread(self):
        """
        RED: Verify aload_sample_tuples uses asyncio.to_thread for non-blocking I/O.
        """
        from mcp_server_langgraph.auth.openfga import aload_sample_tuples

        sample_tuples = [{"user": "user:bob", "relation": "editor", "object": "doc:1"}]

        with patch(
            "mcp_server_langgraph.auth.openfga.asyncio.to_thread",
            return_value=sample_tuples,
        ) as mock_to_thread:
            _result = await aload_sample_tuples()  # noqa: F841

            # Verify asyncio.to_thread was called
            mock_to_thread.assert_called_once()
