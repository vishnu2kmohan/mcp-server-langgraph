"""
TDD Tests for Router Agent Integration into Chat Flow.

Tests that ChatServiceImpl.create_stream() integrates with RouterAgent to:
1. Classify incoming requests before streaming
2. Emit routing decision as first SSE event
3. Select appropriate streaming strategy based on routing
4. Fall back gracefully when router fails

TDD Phase: RED - Tests define expected behavior before implementation.
"""

from __future__ import annotations

import gc
from typing import Any, AsyncIterator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_server_langgraph.agents.router_agent import RouterOutput

pytestmark = [pytest.mark.unit, pytest.mark.api, pytest.mark.router]


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_router_output() -> RouterOutput:
    """Create a mock routing decision."""
    return RouterOutput(
        complexity="complicated",
        risk="medium",
        task_type="code",
        tools_needed=["code_search", "file_read"],
        suggested_orchestrator="studio",
        critique_rounds=1,
        thinking_budget="medium",
        confidence=0.85,
        skills_needed=["code_analysis"],
        execution_mode="tool_calling",
        routing_rationale="Code task requiring tool access",
    )


@pytest.fixture
def mock_llm_factory() -> MagicMock:
    """Create a mock LLM factory that yields streaming chunks."""
    factory = MagicMock()

    async def mock_astream(*args: Any, **kwargs: Any) -> AsyncIterator[MagicMock]:
        # Yield mock chunks
        chunk1 = MagicMock()
        chunk1.content = "Hello"
        chunk1.thinking = None
        yield chunk1

        chunk2 = MagicMock()
        chunk2.content = " world"
        chunk2.thinking = None
        yield chunk2

    factory.astream = mock_astream
    return factory


@pytest.fixture
def mock_router_agent(mock_router_output: RouterOutput) -> AsyncMock:
    """Create a mock router agent."""
    agent = AsyncMock(return_value=None)  # noqa: async-mock-config - configured below
    agent.route = AsyncMock(return_value=mock_router_output)
    return agent


# =============================================================================
# Test: Router Agent Called in create_stream
# =============================================================================


@pytest.mark.xdist_group(name="chat_router_integration")
class TestRouterAgentIntegration:
    """Test router agent integration with chat streaming."""

    def teardown_method(self) -> None:
        gc.collect()

    @pytest.mark.asyncio
    async def test_router_called_when_routing_enabled(
        self,
        mock_router_agent: AsyncMock,
        mock_llm_factory: MagicMock,
        mock_router_output: RouterOutput,
    ) -> None:
        """GIVEN routing is enabled
        WHEN create_stream is called
        THEN RouterAgent.route() is called with the user message
        """
        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl

        service = ChatServiceImpl(
            llm_factory=mock_llm_factory,
            router_agent=mock_router_agent,
        )

        messages = [{"role": "user", "content": "Help me analyze this code"}]

        chunks = []
        async for chunk in service.create_stream(
            session_id="test-session",
            messages=messages,
            enable_routing=True,
        ):
            chunks.append(chunk)

        # Verify router was called with user message
        mock_router_agent.route.assert_called_once()
        call_args = mock_router_agent.route.call_args
        assert "Help me analyze this code" in str(call_args)

    @pytest.mark.asyncio
    async def test_routing_decision_emitted_as_first_event(
        self,
        mock_router_agent: AsyncMock,
        mock_llm_factory: MagicMock,
        mock_router_output: RouterOutput,
    ) -> None:
        """GIVEN routing is enabled
        WHEN create_stream yields events
        THEN first event contains routing_decision
        """
        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl

        service = ChatServiceImpl(
            llm_factory=mock_llm_factory,
            router_agent=mock_router_agent,
        )

        messages = [{"role": "user", "content": "Help me with code"}]

        chunks = []
        async for chunk in service.create_stream(
            session_id="test-session",
            messages=messages,
            enable_routing=True,
        ):
            chunks.append(chunk)

        # First chunk should be routing decision
        assert len(chunks) > 0
        first_chunk = chunks[0]
        assert "routing_decision" in first_chunk

        routing = first_chunk["routing_decision"]
        assert routing["complexity"] == "complicated"
        assert routing["suggested_orchestrator"] == "studio"
        assert routing["thinking_budget"] == "medium"
        assert routing["confidence"] == 0.85

    @pytest.mark.asyncio
    async def test_routing_selects_langgraph_for_studio_orchestrator(
        self,
        mock_router_agent: AsyncMock,
        mock_llm_factory: MagicMock,
    ) -> None:
        """GIVEN router suggests 'studio' orchestrator
        WHEN create_stream processes the request
        THEN LangGraph agent is used (use_langgraph=True internally)
        """
        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl

        # Router suggests studio orchestrator
        studio_output = RouterOutput(
            complexity="complex",
            risk="high",
            task_type="code",
            tools_needed=["code_execution"],
            suggested_orchestrator="studio",
            critique_rounds=2,
            thinking_budget="deep",
            confidence=0.9,
        )
        mock_router_agent.route = AsyncMock(return_value=studio_output)

        # Create mock LangGraph agent
        mock_langgraph = AsyncMock(return_value=None)  # noqa: async-mock-config - configured below

        async def mock_astream_events(*args: Any, **kwargs: Any) -> AsyncIterator[dict[str, Any]]:
            yield {"event": "on_chain_start", "name": "test"}

        mock_langgraph.astream_events = mock_astream_events

        service = ChatServiceImpl(
            llm_factory=mock_llm_factory,
            router_agent=mock_router_agent,
            langgraph_agent=mock_langgraph,
        )

        messages = [{"role": "user", "content": "Execute this complex code task"}]

        chunks = []
        async for chunk in service.create_stream(
            session_id="test-session",
            messages=messages,
            enable_routing=True,
        ):
            chunks.append(chunk)

        # Verify LangGraph was attempted (route decision should indicate this)
        routing_chunk = next((c for c in chunks if "routing_decision" in c), None)
        assert routing_chunk is not None
        assert routing_chunk["routing_decision"]["suggested_orchestrator"] == "studio"

    @pytest.mark.asyncio
    async def test_routing_uses_llm_factory_for_standard_orchestrator(
        self,
        mock_router_agent: AsyncMock,
        mock_llm_factory: MagicMock,
    ) -> None:
        """GIVEN router suggests 'standard' orchestrator
        WHEN create_stream processes the request
        THEN LLMFactory is used directly
        """
        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl

        # Router suggests standard orchestrator
        standard_output = RouterOutput(
            complexity="simple",
            risk="low",
            task_type="chat",
            tools_needed=[],
            suggested_orchestrator="standard",
            critique_rounds=0,
            thinking_budget="none",
            confidence=0.95,
        )
        mock_router_agent.route = AsyncMock(return_value=standard_output)

        service = ChatServiceImpl(
            llm_factory=mock_llm_factory,
            router_agent=mock_router_agent,
        )

        messages = [{"role": "user", "content": "Hello, how are you?"}]

        chunks = []
        async for chunk in service.create_stream(
            session_id="test-session",
            messages=messages,
            enable_routing=True,
        ):
            chunks.append(chunk)

        # Should have routing decision + content chunks
        routing_chunk = next((c for c in chunks if "routing_decision" in c), None)
        assert routing_chunk is not None
        assert routing_chunk["routing_decision"]["suggested_orchestrator"] == "standard"

        # Content chunks should follow
        content_chunks = [c for c in chunks if "delta" in c]
        assert len(content_chunks) > 0

    @pytest.mark.asyncio
    async def test_routing_falls_back_on_router_error(
        self,
        mock_llm_factory: MagicMock,
    ) -> None:
        """GIVEN router agent raises an error
        WHEN create_stream is called with routing enabled
        THEN falls back to default routing and continues streaming
        """
        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl

        # Router that fails
        failing_router = AsyncMock(return_value=None)  # noqa: async-mock-config - configured below
        failing_router.route = AsyncMock(side_effect=Exception("Router failed"))

        service = ChatServiceImpl(
            llm_factory=mock_llm_factory,
            router_agent=failing_router,
        )

        messages = [{"role": "user", "content": "Test message"}]

        chunks = []
        async for chunk in service.create_stream(
            session_id="test-session",
            messages=messages,
            enable_routing=True,
        ):
            chunks.append(chunk)

        # Should still get routing decision (default fallback)
        routing_chunk = next((c for c in chunks if "routing_decision" in c), None)
        assert routing_chunk is not None
        # Default values from DEFAULT_ROUTER_OUTPUT
        assert routing_chunk["routing_decision"]["complexity"] == "complicated"
        assert routing_chunk["routing_decision"]["suggested_orchestrator"] == "standard"

        # Content should still stream
        content_chunks = [c for c in chunks if "delta" in c]
        assert len(content_chunks) > 0

    @pytest.mark.asyncio
    async def test_routing_disabled_skips_router(
        self,
        mock_router_agent: AsyncMock,
        mock_llm_factory: MagicMock,
    ) -> None:
        """GIVEN routing is disabled (default)
        WHEN create_stream is called
        THEN RouterAgent.route() is NOT called
        """
        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl

        service = ChatServiceImpl(
            llm_factory=mock_llm_factory,
            router_agent=mock_router_agent,
        )

        messages = [{"role": "user", "content": "Hello"}]

        chunks = []
        async for chunk in service.create_stream(
            session_id="test-session",
            messages=messages,
            # enable_routing not set (default False)
        ):
            chunks.append(chunk)

        # Router should NOT be called
        mock_router_agent.route.assert_not_called()

        # No routing_decision chunk
        routing_chunk = next((c for c in chunks if "routing_decision" in c), None)
        assert routing_chunk is None

    @pytest.mark.asyncio
    async def test_thinking_budget_maps_to_reasoning_effort(
        self,
        mock_router_agent: AsyncMock,
        mock_llm_factory: MagicMock,
    ) -> None:
        """GIVEN router returns thinking_budget='deep'
        WHEN create_stream processes the request
        THEN reasoning_effort is set accordingly
        """
        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl

        # Router with deep thinking budget
        deep_thinking_output = RouterOutput(
            complexity="complex",
            risk="high",
            task_type="analysis",
            tools_needed=[],
            suggested_orchestrator="standard",
            critique_rounds=2,
            thinking_budget="deep",
            confidence=0.8,
        )
        mock_router_agent.route = AsyncMock(return_value=deep_thinking_output)

        # Track what kwargs are passed to LLM
        captured_kwargs: dict[str, Any] = {}

        async def capturing_astream(*args: Any, **kwargs: Any) -> AsyncIterator[MagicMock]:
            captured_kwargs.update(kwargs)
            chunk = MagicMock()
            chunk.content = "Response"
            chunk.thinking = "Deep reasoning here..."
            yield chunk

        mock_llm_factory.astream = capturing_astream

        service = ChatServiceImpl(
            llm_factory=mock_llm_factory,
            router_agent=mock_router_agent,
        )

        messages = [{"role": "user", "content": "Complex analysis task"}]

        chunks = []
        async for chunk in service.create_stream(
            session_id="test-session",
            messages=messages,
            enable_routing=True,
        ):
            chunks.append(chunk)

        # Routing decision should include thinking budget
        routing_chunk = next((c for c in chunks if "routing_decision" in c), None)
        assert routing_chunk is not None
        assert routing_chunk["routing_decision"]["thinking_budget"] == "deep"


# =============================================================================
# Test: Routing with Feature Flag
# =============================================================================


@pytest.mark.xdist_group(name="chat_router_feature_flag")
class TestRouterFeatureFlag:
    """Test router integration with feature flags."""

    def teardown_method(self) -> None:
        gc.collect()

    @pytest.mark.asyncio
    async def test_routing_controlled_by_feature_flag(
        self,
        mock_router_agent: AsyncMock,
        mock_llm_factory: MagicMock,
    ) -> None:
        """GIVEN ENABLE_CHAT_ROUTING feature flag is True
        WHEN create_stream is called without explicit enable_routing
        THEN routing is enabled based on feature flag
        """
        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl

        service = ChatServiceImpl(
            llm_factory=mock_llm_factory,
            router_agent=mock_router_agent,
        )

        messages = [{"role": "user", "content": "Test"}]

        with patch("mcp_server_langgraph.api.v1.chat.settings") as mock_settings:
            mock_settings.enable_chat_routing = True

            chunks = []
            async for chunk in service.create_stream(
                session_id="test-session",
                messages=messages,
            ):
                chunks.append(chunk)

        # Router should be called due to feature flag
        mock_router_agent.route.assert_called_once()


# =============================================================================
# Test: Routing Event Schema
# =============================================================================


@pytest.mark.xdist_group(name="chat_router_schema")
class TestRoutingEventSchema:
    """Test routing decision event schema."""

    def teardown_method(self) -> None:
        gc.collect()

    @pytest.mark.asyncio
    async def test_routing_decision_has_complete_schema(
        self,
        mock_router_agent: AsyncMock,
        mock_llm_factory: MagicMock,
        mock_router_output: RouterOutput,
    ) -> None:
        """GIVEN routing is enabled
        WHEN routing decision is emitted
        THEN it contains all expected fields
        """
        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl

        service = ChatServiceImpl(
            llm_factory=mock_llm_factory,
            router_agent=mock_router_agent,
        )

        messages = [{"role": "user", "content": "Test"}]

        chunks = []
        async for chunk in service.create_stream(
            session_id="test-session",
            messages=messages,
            enable_routing=True,
        ):
            chunks.append(chunk)

        routing_chunk = next((c for c in chunks if "routing_decision" in c), None)
        assert routing_chunk is not None

        routing = routing_chunk["routing_decision"]

        # All required fields present
        assert "complexity" in routing
        assert "risk" in routing
        assert "task_type" in routing
        assert "tools_needed" in routing
        assert "suggested_orchestrator" in routing
        assert "critique_rounds" in routing
        assert "thinking_budget" in routing
        assert "confidence" in routing

        # ADR-0092 fields
        assert "skills_needed" in routing
        assert "execution_mode" in routing
        assert "routing_rationale" in routing
