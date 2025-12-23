"""
Tests for MCP Server Integration with Skills, Agents, and Security Hooks.

Tests the wiring of:
- Skills/Agents handlers into call_tool routing
- Skills/Agents tools into list_tools registration
- SDK security hooks into call_tool flow
- Feature flag control over tool visibility

Following TDD: Write tests FIRST, then implement.
"""

from __future__ import annotations

import gc
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_server_langgraph.auth.user_provider import TokenVerification
from mcp_server_langgraph.core.config import Settings

pytestmark = pytest.mark.unit


def create_mock_token_verification() -> TokenVerification:
    """Create a mock token verification result for tests."""
    return TokenVerification(
        valid=True,
        payload={"sub": "user:test-user", "preferred_username": "test-user"},
        error=None,
    )


def create_test_settings(**kwargs: object) -> Settings:
    """Create test settings with sensible defaults for MCP server tests.

    Uses MagicMock without spec so any attribute access returns MagicMock.
    We configure the boolean/falsy attributes explicitly to prevent issues.
    """
    mock_settings = MagicMock()
    # Auth and security settings
    mock_settings.auth_provider = "inmemory"
    mock_settings.environment = "test"
    mock_settings.jwt_secret_key = "test-secret-key-for-jwt"
    mock_settings.enable_code_execution = False
    # Apply custom overrides
    for key, value in kwargs.items():
        setattr(mock_settings, key, value)
    return mock_settings


@pytest.mark.unit
@pytest.mark.mcp
@pytest.mark.xdist_group(name="mcp_server_integration")
class TestSkillsToolRegistration:
    """Test skills tools appear in list_tools when feature enabled."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_skills_tool_registered_when_feature_enabled(self) -> None:
        """Skills tool should appear in list_tools when enable_skills_system=True."""
        from mcp_server_langgraph.mcp.server_streamable import MCPAgentStreamableServer

        mock_graph = MagicMock()
        mock_settings = create_test_settings()

        with patch("mcp_server_langgraph.mcp.server_streamable.feature_flags") as mock_flags:
            mock_flags.enable_skills_system = True
            mock_flags.enable_multi_agent_orchestration = False
            mock_flags.enable_think_tool = False
            mock_flags.enable_tool_examples = False

            server = MCPAgentStreamableServer(
                agent_graph=mock_graph,
                settings=mock_settings,
            )

            tools = await server._list_tools_handler()
            tool_names = [t.name for t in tools]
            assert "skills" in tool_names

    @pytest.mark.asyncio
    async def test_skills_tool_not_registered_when_feature_disabled(self) -> None:
        """Skills tool should NOT appear in list_tools when enable_skills_system=False."""
        from mcp_server_langgraph.mcp.server_streamable import MCPAgentStreamableServer

        mock_graph = MagicMock()
        mock_settings = create_test_settings()

        with patch("mcp_server_langgraph.mcp.server_streamable.feature_flags") as mock_flags:
            mock_flags.enable_skills_system = False
            mock_flags.enable_multi_agent_orchestration = False
            mock_flags.enable_think_tool = False

            server = MCPAgentStreamableServer(
                agent_graph=mock_graph,
                settings=mock_settings,
            )

            tools = await server._list_tools_handler()
            tool_names = [t.name for t in tools]
            assert "skills" not in tool_names


@pytest.mark.unit
@pytest.mark.mcp
@pytest.mark.xdist_group(name="mcp_server_integration")
class TestAgentsToolRegistration:
    """Test agents tools appear in list_tools when feature enabled."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_agents_tool_registered_when_feature_enabled(self) -> None:
        """Agents tool should appear in list_tools when enable_multi_agent_orchestration=True."""
        from mcp_server_langgraph.mcp.server_streamable import MCPAgentStreamableServer

        mock_graph = MagicMock()
        mock_settings = create_test_settings()

        with patch("mcp_server_langgraph.mcp.server_streamable.feature_flags") as mock_flags:
            mock_flags.enable_multi_agent_orchestration = True
            mock_flags.enable_skills_system = False
            mock_flags.enable_think_tool = False
            mock_flags.enable_tool_examples = False

            server = MCPAgentStreamableServer(
                agent_graph=mock_graph,
                settings=mock_settings,
            )

            tools = await server._list_tools_handler()
            tool_names = [t.name for t in tools]
            assert "agents" in tool_names

    @pytest.mark.asyncio
    async def test_agents_tool_not_registered_when_feature_disabled(self) -> None:
        """Agents tool should NOT appear in list_tools when enable_multi_agent_orchestration=False."""
        from mcp_server_langgraph.mcp.server_streamable import MCPAgentStreamableServer

        mock_graph = MagicMock()
        mock_settings = create_test_settings()

        with patch("mcp_server_langgraph.mcp.server_streamable.feature_flags") as mock_flags:
            mock_flags.enable_multi_agent_orchestration = False
            mock_flags.enable_skills_system = False
            mock_flags.enable_think_tool = False

            server = MCPAgentStreamableServer(
                agent_graph=mock_graph,
                settings=mock_settings,
            )

            tools = await server._list_tools_handler()
            tool_names = [t.name for t in tools]
            assert "agents" not in tool_names


@pytest.mark.unit
@pytest.mark.mcp
@pytest.mark.xdist_group(name="mcp_server_integration")
class TestSkillsRouting:
    """Test skills operations route correctly in call_tool."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_skills_list_operation_routes_to_handler(self) -> None:
        """Skills list operation should route to SkillsToolHandler."""
        from mcp.types import TextContent

        from mcp_server_langgraph.mcp.server_streamable import MCPAgentStreamableServer

        mock_graph = MagicMock()
        mock_settings = create_test_settings()

        with patch("mcp_server_langgraph.mcp.server_streamable.feature_flags") as mock_flags:
            mock_flags.enable_skills_system = True
            mock_flags.enable_multi_agent_orchestration = False
            mock_flags.enable_think_tool = False

            server = MCPAgentStreamableServer(
                agent_graph=mock_graph,
                settings=mock_settings,
            )

            # Mock auth to bypass token verification and authorization
            server.auth.verify_token = AsyncMock(return_value=create_mock_token_verification())
            server.auth.authorize = AsyncMock(return_value=True)

            # Call skills tool with list operation
            result = await server._call_tool_handler(
                name="skills",
                arguments={
                    "operation": "list",
                    "token": "test-token",
                    "user_id": "test-user",
                },
            )

            assert isinstance(result, list)
            assert len(result) > 0
            assert isinstance(result[0], TextContent)

    @pytest.mark.asyncio
    async def test_skills_search_operation_routes_to_handler(self) -> None:
        """Skills search operation should route to SkillsToolHandler."""
        from mcp.types import TextContent

        from mcp_server_langgraph.mcp.server_streamable import MCPAgentStreamableServer

        mock_graph = MagicMock()
        mock_settings = create_test_settings()

        with patch("mcp_server_langgraph.mcp.server_streamable.feature_flags") as mock_flags:
            mock_flags.enable_skills_system = True
            mock_flags.enable_multi_agent_orchestration = False
            mock_flags.enable_think_tool = False

            server = MCPAgentStreamableServer(
                agent_graph=mock_graph,
                settings=mock_settings,
            )

            # Mock auth to bypass token verification and authorization
            server.auth.verify_token = AsyncMock(return_value=create_mock_token_verification())
            server.auth.authorize = AsyncMock(return_value=True)

            result = await server._call_tool_handler(
                name="skills",
                arguments={
                    "operation": "search",
                    "query": "test",
                    "token": "test-token",
                    "user_id": "test-user",
                },
            )

            assert isinstance(result, list)
            assert isinstance(result[0], TextContent)


@pytest.mark.unit
@pytest.mark.mcp
@pytest.mark.xdist_group(name="mcp_server_integration")
class TestAgentsRouting:
    """Test agents operations route correctly in call_tool."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_agents_decompose_operation_routes_to_handler(self) -> None:
        """Agents decompose operation should route to AgentsToolHandler."""
        from mcp.types import TextContent

        from mcp_server_langgraph.mcp.server_streamable import MCPAgentStreamableServer

        mock_graph = MagicMock()
        mock_settings = create_test_settings()

        with (
            patch("mcp_server_langgraph.mcp.server_streamable.feature_flags") as mock_flags,
            patch("mcp_server_langgraph.agents.orchestrator.feature_flags") as mock_orch_flags,
            patch("mcp_server_langgraph.core.feature_flags.feature_flags") as mock_core_flags,
        ):
            # Configure all mocked feature_flags instances
            for mf in [mock_flags, mock_orch_flags, mock_core_flags]:
                mf.enable_multi_agent_orchestration = True
                mf.enable_skills_system = False
                mf.enable_think_tool = False
                mf.require_feature = MagicMock()  # Skip feature check
                mf.max_subagents = 5
                mf.enable_cost_tracking = False
                mf.enable_agent_hitl = False

            server = MCPAgentStreamableServer(
                agent_graph=mock_graph,
                settings=mock_settings,
            )

            # Mock auth to bypass token verification and authorization
            server.auth.verify_token = AsyncMock(return_value=create_mock_token_verification())
            server.auth.authorize = AsyncMock(return_value=True)

            result = await server._call_tool_handler(
                name="agents",
                arguments={
                    "operation": "decompose",
                    "task": "Research and write a report",
                    "token": "test-token",
                    "user_id": "test-user",
                },
            )

            assert isinstance(result, list)
            assert isinstance(result[0], TextContent)

    @pytest.mark.asyncio
    async def test_agents_select_model_operation_routes_to_handler(self) -> None:
        """Agents select_model operation should route to AgentsToolHandler."""
        from mcp.types import TextContent

        from mcp_server_langgraph.mcp.server_streamable import MCPAgentStreamableServer

        mock_graph = MagicMock()
        mock_settings = create_test_settings()

        with patch("mcp_server_langgraph.mcp.server_streamable.feature_flags") as mock_flags:
            mock_flags.enable_multi_agent_orchestration = True
            mock_flags.enable_skills_system = False
            mock_flags.enable_think_tool = False

            server = MCPAgentStreamableServer(
                agent_graph=mock_graph,
                settings=mock_settings,
            )

            # Mock auth to bypass token verification and authorization
            server.auth.verify_token = AsyncMock(return_value=create_mock_token_verification())
            server.auth.authorize = AsyncMock(return_value=True)

            result = await server._call_tool_handler(
                name="agents",
                arguments={
                    "operation": "select_model",
                    "complexity": "complicated",
                    "token": "test-token",
                    "user_id": "test-user",
                },
            )

            assert isinstance(result, list)
            assert isinstance(result[0], TextContent)
            # Should contain model recommendation
            assert "model" in result[0].text


@pytest.mark.unit
@pytest.mark.mcp
@pytest.mark.sdk
@pytest.mark.xdist_group(name="mcp_server_integration")
class TestSecurityHooksIntegration:
    """Test security hooks are called before tool execution."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_security_hook_registry_is_used(self) -> None:
        """Server should use SecurityHookRegistry for pre-tool hooks."""
        from mcp_server_langgraph.mcp.server_streamable import MCPAgentStreamableServer

        mock_graph = MagicMock()
        mock_settings = create_test_settings()

        server = MCPAgentStreamableServer(
            agent_graph=mock_graph,
            settings=mock_settings,
        )

        # Verify server has security_hooks attribute after wiring
        assert hasattr(server, "security_hooks") or hasattr(server, "_security_hook_registry")

    @pytest.mark.asyncio
    async def test_denied_hook_prevents_tool_execution(self) -> None:
        """If security hook denies, tool execution should not proceed."""
        from mcp_server_langgraph.mcp.server_streamable import MCPAgentStreamableServer
        from mcp_server_langgraph.sdk.hooks import HookResult

        mock_graph = MagicMock()
        mock_settings = create_test_settings()

        server = MCPAgentStreamableServer(
            agent_graph=mock_graph,
            settings=mock_settings,
        )

        # Mock auth to bypass token verification and authorization
        server.auth.verify_token = AsyncMock(return_value=create_mock_token_verification())
        server.auth.authorize = AsyncMock(return_value=True)

        # Mock the hook registry to deny
        mock_registry = MagicMock()
        mock_registry.execute_hooks = AsyncMock(return_value=HookResult.deny("PII detected - blocked"))
        server._security_hook_registry = mock_registry

        # Tool call should be blocked by the security hook
        with pytest.raises(PermissionError, match="denied|blocked"):
            await server._call_tool_handler(
                name="search_tools",
                arguments={
                    "query": "test",
                    "token": "test-token",
                    "user_id": "test-user",
                },
            )


@pytest.mark.unit
@pytest.mark.mcp
@pytest.mark.xdist_group(name="mcp_server_integration")
class TestThinkToolRegistration:
    """Test think tool registration controlled by feature flag."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_think_tool_registered_when_enabled(self) -> None:
        """Think tool should appear in list_tools when enable_think_tool=True."""
        from mcp_server_langgraph.mcp.server_streamable import MCPAgentStreamableServer

        mock_graph = MagicMock()
        mock_settings = create_test_settings()

        with patch("mcp_server_langgraph.mcp.server_streamable.feature_flags") as mock_flags:
            mock_flags.enable_think_tool = True
            mock_flags.enable_skills_system = False
            mock_flags.enable_multi_agent_orchestration = False
            mock_flags.enable_tool_examples = False

            server = MCPAgentStreamableServer(
                agent_graph=mock_graph,
                settings=mock_settings,
            )

            tools = await server._list_tools_handler()
            tool_names = [t.name for t in tools]
            assert "think" in tool_names

    @pytest.mark.asyncio
    async def test_think_tool_not_registered_when_disabled(self) -> None:
        """Think tool should NOT appear in list_tools when enable_think_tool=False."""
        from mcp_server_langgraph.mcp.server_streamable import MCPAgentStreamableServer

        mock_graph = MagicMock()
        mock_settings = create_test_settings()

        with patch("mcp_server_langgraph.mcp.server_streamable.feature_flags") as mock_flags:
            mock_flags.enable_think_tool = False
            mock_flags.enable_skills_system = False
            mock_flags.enable_multi_agent_orchestration = False

            server = MCPAgentStreamableServer(
                agent_graph=mock_graph,
                settings=mock_settings,
            )

            tools = await server._list_tools_handler()
            tool_names = [t.name for t in tools]
            assert "think" not in tool_names


@pytest.mark.unit
@pytest.mark.mcp
@pytest.mark.xdist_group(name="mcp_server_integration")
class TestThinkToolRouting:
    """Test think tool routes correctly in call_tool."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_think_tool_routes_correctly(self) -> None:
        """Think tool should route to handler and return recorded thought."""
        from mcp.types import TextContent

        from mcp_server_langgraph.mcp.server_streamable import MCPAgentStreamableServer

        mock_graph = MagicMock()
        mock_settings = create_test_settings()

        with patch("mcp_server_langgraph.mcp.server_streamable.feature_flags") as mock_flags:
            mock_flags.enable_think_tool = True
            mock_flags.enable_skills_system = False
            mock_flags.enable_multi_agent_orchestration = False

            server = MCPAgentStreamableServer(
                agent_graph=mock_graph,
                settings=mock_settings,
            )

            # Mock auth to bypass token verification and authorization
            server.auth.verify_token = AsyncMock(return_value=create_mock_token_verification())
            server.auth.authorize = AsyncMock(return_value=True)

            result = await server._call_tool_handler(
                name="think",
                arguments={
                    "thought": "Let me analyze this problem step by step",
                    "token": "test-token",
                    "user_id": "test-user",
                },
            )

            assert isinstance(result, list)
            assert isinstance(result[0], TextContent)
            # Should contain the thought
            assert "thought" in result[0].text.lower() or "recorded" in result[0].text.lower()
