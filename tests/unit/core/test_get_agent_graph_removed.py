"""
TDD Tests: Verify get_agent_graph() has been removed.

These tests verify that the deprecated get_agent_graph() singleton function
has been completely removed from the codebase after the DI migration.

TDD Phase: RED - Tests fail until get_agent_graph is removed
"""

import gc
import importlib

import pytest

pytestmark = [pytest.mark.unit]


@pytest.mark.xdist_group(name="test_get_agent_graph_removed")
class TestGetAgentGraphRemoved:
    """Verify get_agent_graph() has been removed from the codebase."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_get_agent_graph_not_in_module_exports(self):
        """
        GIVEN: The agent module
        WHEN: Checking the public API
        THEN: get_agent_graph should not be exported
        """
        from mcp_server_langgraph.core import agent

        # Reload to ensure fresh state
        importlib.reload(agent)

        # Check that get_agent_graph is not in __all__ or public API
        public_names = [name for name in dir(agent) if not name.startswith("_")]

        # get_agent_graph should NOT be in the public API
        assert "get_agent_graph" not in public_names, (
            "get_agent_graph should be removed from agent module public API. "
            "All consumers should use create_agent_graph() instead."
        )

    def test_import_get_agent_graph_raises_error(self):
        """
        GIVEN: A consumer trying to import get_agent_graph
        WHEN: Using 'from mcp_server_langgraph.core.agent import get_agent_graph'
        THEN: ImportError should be raised
        """
        with pytest.raises(ImportError):
            # This should fail after removal
            from mcp_server_langgraph.core.agent import get_agent_graph  # noqa: F401

    def test_agent_graph_cache_not_in_module(self):
        """
        GIVEN: The agent module
        WHEN: Checking for _agent_graph_cache
        THEN: The singleton cache should not exist
        """
        from mcp_server_langgraph.core import agent

        # Reload to ensure fresh state
        importlib.reload(agent)

        assert not hasattr(agent, "_agent_graph_cache"), (
            "_agent_graph_cache singleton should be removed. DI pattern via create_agent_graph() is the new standard."
        )

    def test_create_agent_graph_is_primary_api(self):
        """
        GIVEN: The agent module
        WHEN: Checking the public API
        THEN: create_agent_graph should be the primary way to get an agent graph
        """
        from mcp_server_langgraph.core import agent

        # create_agent_graph should exist and be callable
        assert hasattr(agent, "create_agent_graph"), "create_agent_graph should exist"
        assert callable(agent.create_agent_graph), "create_agent_graph should be callable"

    def test_cleanup_checkpointer_still_available(self):
        """
        GIVEN: The agent module
        WHEN: Checking for cleanup_checkpointer
        THEN: It should still be available for resource management
        """
        from mcp_server_langgraph.core import agent

        assert hasattr(agent, "cleanup_checkpointer"), "cleanup_checkpointer should exist"
        assert callable(agent.cleanup_checkpointer), "cleanup_checkpointer should be callable"


@pytest.mark.xdist_group(name="test_get_agent_graph_removed")
class TestNoSingletonPatternInTestHelpers:
    """Verify singleton cache clearing is not needed in tests."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_agent_module_has_no_cache_attribute(self):
        """
        GIVEN: Test code that previously used agent_module._agent_graph_cache = None
        WHEN: The DI pattern is fully adopted
        THEN: There should be no _agent_graph_cache attribute to clear
        """
        from mcp_server_langgraph.core import agent as agent_module

        # The singleton cache pattern should be removed
        assert not hasattr(agent_module, "_agent_graph_cache"), (
            "Tests should no longer need to clear _agent_graph_cache. "
            "The DI pattern eliminates the need for singleton state management."
        )
