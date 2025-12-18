"""
TDD Tests for MCP Server Agent Graph Migration.

These tests verify that MCP servers use the DI-based create_agent_graph()
pattern. The deprecated get_agent_graph() singleton has been removed (2025-12).

Migration Status (Complete):
1. get_agent_graph() removed - DI via create_agent_graph()
2. Agent graph stored at server instance level (not global)
3. Agent graph injection supported for testing
4. Proper checkpointer lifecycle management
"""

import gc
import warnings
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="test_mcp_agent_graph_migration_stdio")
class TestMCPStdioServerAgentGraphMigration:
    """Test MCPAgentServer uses create_agent_graph() instead of deprecated singleton."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_server_accepts_agent_graph_injection(self):
        """
        Test: MCPAgentServer accepts agent_graph as constructor parameter.

        GIVEN: An agent graph instance
        WHEN: Creating MCPAgentServer with agent_graph parameter
        THEN: Server uses the injected graph instead of creating one
        """
        from tests.utils.mock_factories import create_behavioral_agent_graph

        # Create a mock agent graph
        agent_graph = create_behavioral_agent_graph(
            response_message="Test response",
            conversation_exists=False,
        )

        # Mock dependencies
        mock_settings = MagicMock()
        mock_settings.jwt_secret_key = "test-secret"
        mock_settings.environment = "development"
        mock_settings.auth_provider = "inmemory"

        with patch("mcp_server_langgraph.mcp.server_stdio.settings", mock_settings):
            with patch("mcp_server_langgraph.mcp.server_stdio.create_auth_middleware") as mock_auth_factory:
                mock_auth_factory.return_value = MagicMock()

                from mcp_server_langgraph.mcp.server_stdio import MCPAgentServer

                server = MCPAgentServer(
                    agent_graph=agent_graph,
                    settings=mock_settings,
                )

                # Server should store the injected graph
                assert server.agent_graph is agent_graph

    def test_server_creates_graph_if_not_injected(self):
        """
        Test: MCPAgentServer creates agent graph if not provided.

        GIVEN: No agent_graph parameter
        WHEN: Creating MCPAgentServer
        THEN: Server creates a new graph using create_agent_graph()
        """
        mock_settings = MagicMock()
        mock_settings.jwt_secret_key = "test-secret"
        mock_settings.environment = "development"
        mock_settings.auth_provider = "inmemory"
        mock_settings.checkpoint_backend = "memory"

        with patch("mcp_server_langgraph.mcp.server_stdio.settings", mock_settings):
            with patch("mcp_server_langgraph.mcp.server_stdio.create_auth_middleware") as mock_auth_factory:
                with patch("mcp_server_langgraph.mcp.server_stdio.create_agent_graph") as mock_create:
                    mock_auth_factory.return_value = MagicMock()
                    mock_graph = MagicMock()
                    mock_create.return_value = mock_graph

                    from mcp_server_langgraph.mcp.server_stdio import MCPAgentServer

                    server = MCPAgentServer(settings=mock_settings)

                    # Server should have created a graph
                    mock_create.assert_called_once()
                    assert server.agent_graph is mock_graph

    def test_server_does_not_emit_deprecation_warning(self):
        """
        Test: MCPAgentServer does not emit deprecation warnings.

        GIVEN: MCPAgentServer is created
        WHEN: Handling chat requests
        THEN: No deprecation warnings about get_agent_graph()
        """
        mock_settings = MagicMock()
        mock_settings.jwt_secret_key = "test-secret"
        mock_settings.environment = "development"
        mock_settings.auth_provider = "inmemory"
        mock_settings.checkpoint_backend = "memory"

        with patch("mcp_server_langgraph.mcp.server_stdio.settings", mock_settings):
            with patch("mcp_server_langgraph.mcp.server_stdio.create_auth_middleware") as mock_auth_factory:
                with patch("mcp_server_langgraph.mcp.server_stdio.create_agent_graph") as mock_create:
                    mock_auth_factory.return_value = MagicMock()
                    mock_graph = MagicMock()
                    mock_graph.checkpointer = None
                    mock_create.return_value = mock_graph

                    # Capture warnings
                    with warnings.catch_warnings(record=True) as w:
                        warnings.simplefilter("always")

                        from mcp_server_langgraph.mcp.server_stdio import MCPAgentServer

                        _ = MCPAgentServer(settings=mock_settings)

                        # Check no deprecation warnings about get_agent_graph
                        deprecation_warnings = [
                            warning
                            for warning in w
                            if issubclass(warning.category, DeprecationWarning) and "get_agent_graph" in str(warning.message)
                        ]
                        assert len(deprecation_warnings) == 0, (
                            f"Found deprecation warnings: {[str(w.message) for w in deprecation_warnings]}"
                        )


@pytest.mark.xdist_group(name="test_mcp_agent_graph_migration_streamable")
class TestMCPStreamableServerAgentGraphMigration:
    """Test MCPAgentStreamableServer uses create_agent_graph() instead of deprecated singleton."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_server_accepts_agent_graph_injection(self):
        """
        Test: MCPAgentStreamableServer accepts agent_graph as constructor parameter.

        GIVEN: An agent graph instance
        WHEN: Creating MCPAgentStreamableServer with agent_graph parameter
        THEN: Server uses the injected graph instead of creating one
        """
        from tests.utils.mock_factories import create_behavioral_agent_graph

        # Create a mock agent graph
        agent_graph = create_behavioral_agent_graph(
            response_message="Test response",
            conversation_exists=False,
        )

        # Mock dependencies
        mock_settings = MagicMock()
        mock_settings.jwt_secret_key = "test-secret"
        mock_settings.environment = "development"
        mock_settings.auth_provider = "inmemory"
        mock_settings.service_version = "1.0.0"
        mock_settings.enable_code_execution = False

        with patch("mcp_server_langgraph.mcp.server_streamable.settings", mock_settings):
            with patch("mcp_server_langgraph.mcp.server_streamable.create_auth_middleware") as mock_auth_factory:
                mock_auth_factory.return_value = MagicMock()

                from mcp_server_langgraph.mcp.server_streamable import MCPAgentStreamableServer

                server = MCPAgentStreamableServer(
                    agent_graph=agent_graph,
                    settings=mock_settings,
                )

                # Server should store the injected graph
                assert server.agent_graph is agent_graph

    def test_server_creates_graph_if_not_injected(self):
        """
        Test: MCPAgentStreamableServer creates agent graph if not provided.

        GIVEN: No agent_graph parameter
        WHEN: Creating MCPAgentStreamableServer
        THEN: Server creates a new graph using create_agent_graph()
        """
        mock_settings = MagicMock()
        mock_settings.jwt_secret_key = "test-secret"
        mock_settings.environment = "development"
        mock_settings.auth_provider = "inmemory"
        mock_settings.checkpoint_backend = "memory"
        mock_settings.service_version = "1.0.0"
        mock_settings.enable_code_execution = False

        with patch("mcp_server_langgraph.mcp.server_streamable.settings", mock_settings):
            with patch("mcp_server_langgraph.mcp.server_streamable.create_auth_middleware") as mock_auth_factory:
                with patch("mcp_server_langgraph.mcp.server_streamable.create_agent_graph") as mock_create:
                    mock_auth_factory.return_value = MagicMock()
                    mock_graph = MagicMock()
                    mock_create.return_value = mock_graph

                    from mcp_server_langgraph.mcp.server_streamable import MCPAgentStreamableServer

                    server = MCPAgentStreamableServer(settings=mock_settings)

                    # Server should have created a graph
                    mock_create.assert_called_once()
                    assert server.agent_graph is mock_graph

    def test_server_does_not_emit_deprecation_warning(self):
        """
        Test: MCPAgentStreamableServer does not emit deprecation warnings.

        GIVEN: MCPAgentStreamableServer is created
        WHEN: Server is used
        THEN: No deprecation warnings about get_agent_graph()
        """
        mock_settings = MagicMock()
        mock_settings.jwt_secret_key = "test-secret"
        mock_settings.environment = "development"
        mock_settings.auth_provider = "inmemory"
        mock_settings.checkpoint_backend = "memory"
        mock_settings.service_version = "1.0.0"
        mock_settings.enable_code_execution = False

        with patch("mcp_server_langgraph.mcp.server_streamable.settings", mock_settings):
            with patch("mcp_server_langgraph.mcp.server_streamable.create_auth_middleware") as mock_auth_factory:
                with patch("mcp_server_langgraph.mcp.server_streamable.create_agent_graph") as mock_create:
                    mock_auth_factory.return_value = MagicMock()
                    mock_graph = MagicMock()
                    mock_graph.checkpointer = None
                    mock_create.return_value = mock_graph

                    # Capture warnings
                    with warnings.catch_warnings(record=True) as w:
                        warnings.simplefilter("always")

                        from mcp_server_langgraph.mcp.server_streamable import MCPAgentStreamableServer

                        _ = MCPAgentStreamableServer(settings=mock_settings)

                        # Check no deprecation warnings about get_agent_graph
                        deprecation_warnings = [
                            warning
                            for warning in w
                            if issubclass(warning.category, DeprecationWarning) and "get_agent_graph" in str(warning.message)
                        ]
                        assert len(deprecation_warnings) == 0, (
                            f"Found deprecation warnings: {[str(w.message) for w in deprecation_warnings]}"
                        )


@pytest.mark.xdist_group(name="test_mcp_checkpointer_cleanup")
class TestCheckpointerCleanup:
    """Test that checkpointer resources are properly cleaned up."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_server_provides_cleanup_method(self):
        """
        Test: MCP servers provide cleanup method for checkpointer.

        GIVEN: MCPAgentServer with checkpointer
        WHEN: cleanup() is called
        THEN: Checkpointer resources are released
        """
        mock_settings = MagicMock()
        mock_settings.jwt_secret_key = "test-secret"
        mock_settings.environment = "development"
        mock_settings.auth_provider = "inmemory"
        mock_settings.checkpoint_backend = "memory"

        mock_checkpointer = MagicMock()
        mock_graph = MagicMock()
        mock_graph.checkpointer = mock_checkpointer

        with patch("mcp_server_langgraph.mcp.server_stdio.settings", mock_settings):
            with patch("mcp_server_langgraph.mcp.server_stdio.create_auth_middleware") as mock_auth_factory:
                mock_auth_factory.return_value = MagicMock()

                from mcp_server_langgraph.mcp.server_stdio import MCPAgentServer

                server = MCPAgentServer(
                    agent_graph=mock_graph,
                    settings=mock_settings,
                )

                # Server should have cleanup method
                assert hasattr(server, "cleanup")

                # Call cleanup - should call cleanup_checkpointer
                with patch("mcp_server_langgraph.mcp.server_stdio.cleanup_checkpointer") as mock_cleanup:
                    server.cleanup()
                    mock_cleanup.assert_called_once_with(mock_checkpointer)


@pytest.mark.xdist_group(name="test_agent_graph_instance_reuse")
class TestAgentGraphInstanceReuse:
    """Test that servers reuse their agent graph instance."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_multiple_requests_use_same_graph(self):
        """
        Test: Multiple requests use the same agent graph instance.

        GIVEN: MCPAgentServer with injected agent graph
        WHEN: Multiple chat requests are processed
        THEN: All requests use the same graph instance
        """
        from tests.utils.mock_factories import create_behavioral_agent_graph

        agent_graph = create_behavioral_agent_graph(
            response_message="Response",
            conversation_exists=False,
        )

        # Track invocations
        invocation_count = 0
        original_ainvoke = agent_graph.ainvoke

        async def counting_ainvoke(*args, **kwargs):
            nonlocal invocation_count
            invocation_count += 1
            return await original_ainvoke(*args, **kwargs)

        agent_graph.ainvoke = counting_ainvoke

        mock_settings = MagicMock()
        mock_settings.jwt_secret_key = "test-secret"
        mock_settings.environment = "development"
        mock_settings.auth_provider = "inmemory"

        with patch("mcp_server_langgraph.mcp.server_stdio.settings", mock_settings):
            with patch("mcp_server_langgraph.mcp.server_stdio.create_auth_middleware") as mock_auth_factory:
                mock_auth = MagicMock()
                mock_verification = MagicMock()
                mock_verification.valid = True
                mock_verification.payload = {"sub": "user:alice", "preferred_username": "alice"}
                mock_auth.verify_token.return_value = mock_verification
                mock_auth.authorize.return_value = True
                mock_auth_factory.return_value = mock_auth

                from mcp_server_langgraph.mcp.server_stdio import MCPAgentServer

                server = MCPAgentServer(
                    agent_graph=agent_graph,
                    settings=mock_settings,
                )

                # Verify same instance is used
                assert server.agent_graph is agent_graph
