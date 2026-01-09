"""
Tests for Router Agent Semantic Discovery.

TDD tests for route_with_semantic_discovery method that uses
SemanticIndexManager to discover relevant tools and skills
before routing.

RED Phase: These tests define the expected behavior.
GREEN Phase: Implementation in router_agent.py will make them pass.
"""

import gc
from unittest.mock import AsyncMock, MagicMock

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_router_semantic_output")
class TestRouterOutputWithDiscovery:
    """Tests for RouterOutputWithDiscovery model."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_router_output_with_discovery_extends_router_output(self) -> None:
        """RouterOutputWithDiscovery should extend RouterOutput."""
        from mcp_server_langgraph.agents.router_agent import (
            RouterOutput,
            RouterOutputWithDiscovery,
        )

        # Should be a subclass of RouterOutput
        assert issubclass(RouterOutputWithDiscovery, RouterOutput)

    def test_router_output_with_discovery_has_discovered_tools(self) -> None:
        """RouterOutputWithDiscovery should have discovered_tools field."""
        from mcp_server_langgraph.agents.router_agent import RouterOutputWithDiscovery
        from mcp_server_langgraph.tools.semantic_index import ToolIndexEntry

        output = RouterOutputWithDiscovery(
            complexity="simple",
            risk="low",
            task_type="chat",
            tools_needed=["calculator"],
            suggested_orchestrator="standard",
            critique_rounds=0,
            thinking_budget="none",
            confidence=0.9,
            discovered_tools=[
                ToolIndexEntry(
                    tool_id="tool-1",
                    name="calculator",
                    description="Perform calculations",
                    category="math",
                )
            ],
            discovered_skills=[],
        )

        assert len(output.discovered_tools) == 1
        assert output.discovered_tools[0].name == "calculator"

    def test_router_output_with_discovery_has_discovered_skills(self) -> None:
        """RouterOutputWithDiscovery should have discovered_skills field."""
        from mcp_server_langgraph.agents.router_agent import RouterOutputWithDiscovery
        from mcp_server_langgraph.tools.semantic_index import SkillIndexEntry

        output = RouterOutputWithDiscovery(
            complexity="complicated",
            risk="medium",
            task_type="code",
            tools_needed=["read_file"],
            suggested_orchestrator="standard",
            critique_rounds=1,
            thinking_budget="light",
            confidence=0.85,
            discovered_tools=[],
            discovered_skills=[
                SkillIndexEntry(
                    skill_id="skill-1",
                    name="code_review",
                    description="Review code for quality",
                    category="development",
                )
            ],
        )

        assert len(output.discovered_skills) == 1
        assert output.discovered_skills[0].name == "code_review"

    def test_router_output_with_discovery_default_empty_lists(self) -> None:
        """RouterOutputWithDiscovery should have empty lists as defaults."""
        from mcp_server_langgraph.agents.router_agent import RouterOutputWithDiscovery

        output = RouterOutputWithDiscovery(
            complexity="simple",
            risk="low",
            task_type="chat",
            tools_needed=[],
            suggested_orchestrator="standard",
            critique_rounds=0,
            thinking_budget="none",
            confidence=0.8,
        )

        assert output.discovered_tools == []
        assert output.discovered_skills == []


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_router_semantic_method")
class TestRouterAgentSemanticDiscovery:
    """Tests for route_with_semantic_discovery method."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.fixture
    def mock_llm_factory(self) -> MagicMock:
        """Create a mock LLM factory."""
        mock = MagicMock()
        mock.ainvoke = AsyncMock(
            return_value=MagicMock(
                content='{"complexity": "simple", "risk": "low", "task_type": "chat", '
                '"tools_needed": ["calculator"], "suggested_orchestrator": "standard", '
                '"critique_rounds": 0, "thinking_budget": "none", "confidence": 0.9}'
            )
        )
        return mock

    @pytest.fixture
    def mock_semantic_index(self) -> AsyncMock:
        """Create a mock SemanticIndexManager."""
        from mcp_server_langgraph.tools.semantic_index import (
            SkillIndexEntry,
            ToolIndexEntry,
        )

        mock = AsyncMock()
        mock.search_tools = AsyncMock(
            return_value=[
                ToolIndexEntry(
                    tool_id="tool-1",
                    name="calculator",
                    description="Perform calculations",
                    category="math",
                )
            ]
        )
        mock.search_skills = AsyncMock(
            return_value=[
                SkillIndexEntry(
                    skill_id="skill-1",
                    name="code_review",
                    description="Review code",
                    category="development",
                )
            ]
        )
        return mock

    def test_router_agent_has_route_with_semantic_discovery(self) -> None:
        """RouterAgent should have route_with_semantic_discovery method."""
        from mcp_server_langgraph.agents.router_agent import RouterAgent

        assert hasattr(RouterAgent, "route_with_semantic_discovery")

    @pytest.mark.asyncio
    async def test_route_with_semantic_discovery_calls_semantic_index(
        self, mock_llm_factory: MagicMock, mock_semantic_index: AsyncMock
    ) -> None:
        """route_with_semantic_discovery should call semantic index methods."""
        from mcp_server_langgraph.agents.router_agent import RouterAgent

        agent = RouterAgent(llm_factory=mock_llm_factory)

        await agent.route_with_semantic_discovery(
            message="Calculate 2 + 2",
            semantic_index=mock_semantic_index,
            user_id="user:alice",
        )

        # Verify semantic search was called
        mock_semantic_index.search_tools.assert_called_once()
        mock_semantic_index.search_skills.assert_called_once()

    @pytest.mark.asyncio
    async def test_route_with_semantic_discovery_returns_discovered_tools(
        self, mock_llm_factory: MagicMock, mock_semantic_index: AsyncMock
    ) -> None:
        """route_with_semantic_discovery should return discovered tools."""
        from mcp_server_langgraph.agents.router_agent import RouterAgent

        agent = RouterAgent(llm_factory=mock_llm_factory)

        result = await agent.route_with_semantic_discovery(
            message="Calculate 2 + 2",
            semantic_index=mock_semantic_index,
            user_id="user:alice",
        )

        assert len(result.discovered_tools) == 1
        assert result.discovered_tools[0].name == "calculator"

    @pytest.mark.asyncio
    async def test_route_with_semantic_discovery_returns_discovered_skills(
        self, mock_llm_factory: MagicMock, mock_semantic_index: AsyncMock
    ) -> None:
        """route_with_semantic_discovery should return discovered skills."""
        from mcp_server_langgraph.agents.router_agent import RouterAgent

        agent = RouterAgent(llm_factory=mock_llm_factory)

        result = await agent.route_with_semantic_discovery(
            message="Review my code",
            semantic_index=mock_semantic_index,
            user_id="user:alice",
        )

        assert len(result.discovered_skills) == 1
        assert result.discovered_skills[0].name == "code_review"

    @pytest.mark.asyncio
    async def test_route_with_semantic_discovery_respects_limits(
        self, mock_llm_factory: MagicMock, mock_semantic_index: AsyncMock
    ) -> None:
        """route_with_semantic_discovery should respect tool and skill limits."""
        from mcp_server_langgraph.agents.router_agent import RouterAgent

        agent = RouterAgent(llm_factory=mock_llm_factory)

        await agent.route_with_semantic_discovery(
            message="Help me",
            semantic_index=mock_semantic_index,
            user_id="user:alice",
            max_tools=5,
            max_skills=3,
        )

        # Verify limits were passed (user_id is now required for authorization)
        mock_semantic_index.search_tools.assert_called_with(query="Help me", user_id="user:alice", limit=5)
        mock_semantic_index.search_skills.assert_called_with(query="Help me", user_id="user:alice", limit=3)

    @pytest.mark.asyncio
    async def test_route_with_semantic_discovery_passes_tools_to_route(
        self, mock_llm_factory: MagicMock, mock_semantic_index: AsyncMock
    ) -> None:
        """route_with_semantic_discovery should pass discovered tools to route."""
        from mcp_server_langgraph.agents.router_agent import RouterAgent

        agent = RouterAgent(llm_factory=mock_llm_factory)

        result = await agent.route_with_semantic_discovery(
            message="Calculate 2 + 2",
            semantic_index=mock_semantic_index,
            user_id="user:alice",
        )

        # The discovered tool name should be in the routing context
        assert result.tools_needed == ["calculator"]

    @pytest.mark.asyncio
    async def test_route_with_semantic_discovery_handles_empty_results(self, mock_llm_factory: MagicMock) -> None:
        """route_with_semantic_discovery should handle empty semantic results."""
        from mcp_server_langgraph.agents.router_agent import RouterAgent

        mock_semantic_index = AsyncMock()
        mock_semantic_index.search_tools = AsyncMock(return_value=[])
        mock_semantic_index.search_skills = AsyncMock(return_value=[])

        agent = RouterAgent(llm_factory=mock_llm_factory)

        result = await agent.route_with_semantic_discovery(
            message="Hello",
            semantic_index=mock_semantic_index,
            user_id="user:alice",
        )

        assert result.discovered_tools == []
        assert result.discovered_skills == []

    @pytest.mark.asyncio
    async def test_route_with_semantic_discovery_handles_semantic_errors(self, mock_llm_factory: MagicMock) -> None:
        """route_with_semantic_discovery should handle semantic search errors gracefully."""
        from mcp_server_langgraph.agents.router_agent import RouterAgent

        mock_semantic_index = AsyncMock()
        mock_semantic_index.search_tools = AsyncMock(side_effect=Exception("Qdrant unavailable"))
        mock_semantic_index.search_skills = AsyncMock(side_effect=Exception("Qdrant unavailable"))

        agent = RouterAgent(llm_factory=mock_llm_factory)

        # Should not raise, should return fallback output
        result = await agent.route_with_semantic_discovery(
            message="Hello",
            semantic_index=mock_semantic_index,
            user_id="user:alice",
        )

        # Should still have a valid output with empty discovered lists
        assert result is not None
        assert result.discovered_tools == []
        assert result.discovered_skills == []


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_router_semantic_integration")
class TestRouterSemanticIntegration:
    """Integration tests for router semantic discovery."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_semantic_discovery_integrates_with_routing(self, monkeypatch) -> None:
        """Semantic discovery should integrate with normal routing flow."""
        monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-32-chars-long1234")
        monkeypatch.setenv("ENVIRONMENT", "test")

        from mcp_server_langgraph.agents.router_agent import RouterAgent

        # Verify the method signature
        import inspect

        sig = inspect.signature(RouterAgent.route_with_semantic_discovery)
        params = list(sig.parameters.keys())

        assert "message" in params
        assert "semantic_index" in params
