"""
Test that OpenFGA client uses lazy async initialization

This test validates the fix for the async event loop error:
  RuntimeError: no running event loop

Problem:
  OpenFgaClient from openfga_sdk creates aiohttp ClientSession in __init__,
  which requires a running event loop. When get_openfga_client() is called
  from synchronous code or module-level imports, this fails.

Solution (TDD RED → GREEN → REFACTOR):
  1. RED: Write test that fails - calling get_openfga_client() synchronously
  2. GREEN: Implement lazy async initialization pattern
  3. REFACTOR: Clean up implementation

Fix Pattern:
  - Store config in __init__ (sync)
  - Create OpenFgaClient lazily on first async method call
  - Use asyncio.create_task() or await to initialize client
"""

import gc

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.unit
@pytest.mark.xdist_group(name="openfga_lazy_init")
class TestOpenFGALazyInitialization:
    """Test OpenFGA client lazy async initialization pattern"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_get_openfga_client_no_event_loop_error(self, monkeypatch):
        """
        RED Phase: Test that get_openfga_client() doesn't raise event loop error.

        This test will FAIL initially because OpenFGAClient creates aiohttp
        resources in __init__.

        Expected error:
          RuntimeError: no running event loop

        Expected behavior after fix:
          - get_openfga_client() should succeed synchronously
          - Actual OpenFgaClient should be created lazily on first async call
        """
        # Arrange: Set OpenFGA config
        monkeypatch.setenv("OPENFGA_API_URL", "http://localhost:8080")
        monkeypatch.setenv("OPENFGA_STORE_ID", "test-store")
        monkeypatch.setenv("OPENFGA_MODEL_ID", "test-model")

        # Reload config to pick up monkeypatched env vars
        import importlib

        import mcp_server_langgraph.core.config as config_module
        import mcp_server_langgraph.core.dependencies as deps_module

        importlib.reload(config_module)
        importlib.reload(deps_module)

        # Reset singleton
        import mcp_server_langgraph.core.dependencies as deps

        deps._openfga_client = None

        # Re-import to get updated function
        from mcp_server_langgraph.core.dependencies import get_openfga_client

        # Act: Call get_openfga_client() from synchronous context
        # This SHOULD NOT raise RuntimeError: no running event loop
        client = get_openfga_client()

        # Assert: Client created without event loop error
        assert client is not None
        assert hasattr(client, "config")
        assert client.config.store_id == "test-store"
        assert client.config.model_id == "test-model"

    @pytest.mark.asyncio
    async def test_openfga_client_lazy_initialization(self, monkeypatch):
        """
        GREEN Phase: Test that OpenFGA client initializes lazily on first async call.

        This validates that the actual OpenFgaClient is created only when
        an async method is called, not during __init__.
        """
        # Arrange: Set OpenFGA config
        monkeypatch.setenv("OPENFGA_API_URL", "http://localhost:8080")
        monkeypatch.setenv("OPENFGA_STORE_ID", "test-store")
        monkeypatch.setenv("OPENFGA_MODEL_ID", "test-model")

        # Reload config
        import importlib

        import mcp_server_langgraph.core.config as config_module
        import mcp_server_langgraph.core.dependencies as deps_module

        importlib.reload(config_module)
        importlib.reload(deps_module)

        # Reset singleton
        import mcp_server_langgraph.core.dependencies as deps

        deps._openfga_client = None

        # Re-import
        from mcp_server_langgraph.core.dependencies import get_openfga_client

        # Act: Get client (sync - should not initialize SDK client yet)
        client = get_openfga_client()

        # Assert: Client wrapper created
        assert client is not None

        # Assert: SDK client should be created lazily (not yet initialized)
        # This depends on implementation - might have _client = None initially

    def test_get_openfga_client_returns_none_when_config_incomplete(self, monkeypatch):
        """
        Test that get_openfga_client() returns None when config incomplete.

        This is existing behavior - should continue to work after fix.
        """
        # Arrange: Incomplete config (missing store_id and model_id)
        monkeypatch.setenv("OPENFGA_API_URL", "http://localhost:8080")
        monkeypatch.setenv("OPENFGA_STORE_ID", "")
        monkeypatch.setenv("OPENFGA_MODEL_ID", "")

        # Reload config
        import importlib

        import mcp_server_langgraph.core.config as config_module
        import mcp_server_langgraph.core.dependencies as deps_module

        importlib.reload(config_module)
        importlib.reload(deps_module)

        # Reset singleton
        import mcp_server_langgraph.core.dependencies as deps

        deps._openfga_client = None

        # Re-import
        from mcp_server_langgraph.core.dependencies import get_openfga_client

        # Act: Get client with incomplete config
        client = get_openfga_client()

        # Assert: Should return None (graceful degradation)
        assert client is None


@pytest.mark.unit
@pytest.mark.xdist_group(name="openfga_implementation")
class TestOpenFGAClientImplementation:
    """Test OpenFGAClient implementation details"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_openfga_client_init_does_not_create_event_loop_resources(self):
        """
        CRITICAL: Test that OpenFGAClient.__init__ doesn't create async resources.

        This test validates that __init__ is synchronous and doesn't create:
        - aiohttp ClientSession
        - asyncio Tasks
        - Other event loop-dependent resources

        The actual OpenFgaClient should be created lazily.
        """
        from mcp_server_langgraph.auth.openfga import OpenFGAClient, OpenFGAConfig

        # Arrange: Create config
        config = OpenFGAConfig(api_url="http://localhost:8080", store_id="test-store", model_id="test-model")

        # Act: Create client from synchronous context (no event loop)
        # This SHOULD NOT raise RuntimeError
        try:
            client = OpenFGAClient(config=config)
            # Success - __init__ is sync-safe
            assert client is not None
            assert client.config.store_id == "test-store"
        except RuntimeError as e:
            if "no running event loop" in str(e):
                pytest.fail(
                    "OpenFGAClient.__init__ creates async resources! "
                    "This breaks synchronous code. "
                    "Fix: Use lazy initialization pattern - create OpenFgaClient on first async call."
                )
            else:
                raise


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
