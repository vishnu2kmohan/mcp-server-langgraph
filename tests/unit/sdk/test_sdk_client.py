"""
Tests for Claude Agent SDK Integration

PR 12: SDK-agnostic interface that can adapt to future Claude Agent SDK.
Provides abstraction layer for agent orchestration.
"""

from __future__ import annotations

import gc
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.unit

if TYPE_CHECKING:
    from mcp_server_langgraph.sdk.client import LangGraphAgentClient
    from mcp_server_langgraph.sdk.tools import InProcessToolServer
    from mcp_server_langgraph.sdk.state import AgentStateManager


@pytest.mark.unit
@pytest.mark.sdk
@pytest.mark.xdist_group(name="sdk_client")
class TestLangGraphAgentClient:
    """Tests for SDK-agnostic agent client."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_client_class_exists(self) -> None:
        """Test that LangGraphAgentClient class exists."""
        from mcp_server_langgraph.sdk.client import LangGraphAgentClient

        assert LangGraphAgentClient is not None

    def test_client_initialization(self) -> None:
        """Test client initialization with default settings."""
        from mcp_server_langgraph.sdk.client import LangGraphAgentClient

        client = LangGraphAgentClient()

        assert client.model_tier == "complicated"
        assert client.model_selector is not None

    def test_client_initialization_with_tier(self) -> None:
        """Test client initialization with specific tier."""
        from mcp_server_langgraph.sdk.client import LangGraphAgentClient

        client = LangGraphAgentClient(model_tier="complex")

        assert client.model_tier == "complex"

    def test_client_has_model_selector(self) -> None:
        """Test client has model selector integration."""
        from mcp_server_langgraph.sdk.client import LangGraphAgentClient
        from mcp_server_langgraph.agents import ModelSelector

        selector = ModelSelector()
        client = LangGraphAgentClient(model_selector=selector)

        assert client.model_selector is selector

    def test_client_has_orchestrator(self) -> None:
        """Test client has orchestrator integration."""
        from mcp_server_langgraph.sdk.client import LangGraphAgentClient
        from mcp_server_langgraph.agents import Orchestrator

        orchestrator = Orchestrator()
        client = LangGraphAgentClient(orchestrator=orchestrator)

        assert client.orchestrator is orchestrator

    @pytest.mark.asyncio
    async def test_query_returns_response(self) -> None:
        """Test query method returns response."""
        from mcp_server_langgraph.sdk.client import LangGraphAgentClient

        client = LangGraphAgentClient()

        # Query without actual LLM (returns placeholder)
        response = await client.query("What is 2 + 2?")

        assert response is not None
        assert isinstance(response, str)

    @pytest.mark.asyncio
    async def test_run_orchestrated_task(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test running orchestrated multi-agent task."""
        import sys

        from mcp_server_langgraph.agents import orchestrator as orch_module

        # Get the actual module (not the exported singleton)
        ff_module = sys.modules["mcp_server_langgraph.core.feature_flags"]

        # Use shared MockFeatureFlags with multi-agent enabled
        from tests.fixtures.feature_flags_fixtures import MockFeatureFlags

        mock_flags = MockFeatureFlags(enable_multi_agent_orchestration=True)

        # Patch at both the core module level and the orchestrator's import
        monkeypatch.setattr(ff_module, "feature_flags", mock_flags)
        monkeypatch.setattr(orch_module, "feature_flags", mock_flags)

        # Import client after patching
        from mcp_server_langgraph.sdk.client import LangGraphAgentClient

        client = LangGraphAgentClient()

        result = await client.run_orchestrated_task(
            task="Research quantum computing",
            subagent_count=3,
        )

        assert result is not None
        assert "subtask_count" in result or "status" in str(result)

    @pytest.mark.asyncio
    async def test_query_with_session_id(self) -> None:
        """Test query with session ID for state tracking."""
        from mcp_server_langgraph.sdk.client import LangGraphAgentClient
        from mcp_server_langgraph.sdk.state import AgentStateManager

        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            state_manager = AgentStateManager(state_dir=Path(tmp))
            client = LangGraphAgentClient(state_manager=state_manager)

            response = await client.query("What is 2 + 2?", session_id="test-session")

            assert response is not None
            # State should have been saved
            state = await state_manager.resume_session("test-session")
            assert state is not None
            assert "last_query" in state

    @pytest.mark.asyncio
    async def test_call_tool(self) -> None:
        """Test calling a tool through the client."""
        from mcp_server_langgraph.sdk.client import LangGraphAgentClient
        from mcp_server_langgraph.sdk.tools import InProcessToolServer
        from mcp_server_langgraph.sdk.hooks import SecurityHookRegistry

        # Create custom tool server with a test tool
        server = InProcessToolServer(name="test", version="1.0.0")

        async def add_tool(a: int, b: int) -> int:
            return a + b

        server.register_tool("add", add_tool, {"a": int, "b": int})

        client = LangGraphAgentClient(
            tool_server=server,
            hook_registry=SecurityHookRegistry(),  # Empty registry
        )

        result = await client.call_tool("add", {"a": 2, "b": 3})

        assert result == 5

    @pytest.mark.asyncio
    async def test_call_tool_denied_by_hook(self) -> None:
        """Test tool call denied by security hook."""
        from mcp_server_langgraph.sdk.client import LangGraphAgentClient
        from mcp_server_langgraph.sdk.tools import InProcessToolServer
        from mcp_server_langgraph.sdk.hooks import SecurityHookRegistry, HookResult

        server = InProcessToolServer(name="test", version="1.0.0")

        async def safe_tool() -> str:
            return "result"

        server.register_tool("safe_tool", safe_tool, {})

        registry = SecurityHookRegistry()

        async def deny_hook(input_data, tool_use_id, context):
            return HookResult.deny("All tools blocked for testing")

        registry.register("PreToolUse", "*", deny_hook)

        client = LangGraphAgentClient(tool_server=server, hook_registry=registry)

        with pytest.raises(PermissionError, match="Tool call denied"):
            await client.call_tool("safe_tool", {})

    def test_get_available_tools(self) -> None:
        """Test getting list of available tools."""
        from mcp_server_langgraph.sdk.client import LangGraphAgentClient
        from mcp_server_langgraph.sdk.tools import InProcessToolServer

        server = InProcessToolServer(name="test", version="1.0.0")

        async def tool_a() -> str:
            return "a"

        async def tool_b() -> str:
            return "b"

        server.register_tool("tool_a", tool_a, {})
        server.register_tool("tool_b", tool_b, {})

        client = LangGraphAgentClient(tool_server=server)

        tools = client.get_available_tools()

        assert "tool_a" in tools
        assert "tool_b" in tools

    @pytest.mark.asyncio
    async def test_checkpoint_session(self) -> None:
        """Test creating a session checkpoint."""
        from mcp_server_langgraph.sdk.client import LangGraphAgentClient
        from mcp_server_langgraph.sdk.state import AgentStateManager

        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            state_manager = AgentStateManager(state_dir=Path(tmp))
            client = LangGraphAgentClient(state_manager=state_manager)

            await client.checkpoint_session(
                session_id="session-1",
                phase="research",
                summary="Completed initial research",
            )

            state = await state_manager.resume_session("session-1")
            assert state is not None
            assert "checkpoints" in state
            assert len(state["checkpoints"]) == 1


@pytest.mark.unit
@pytest.mark.sdk
@pytest.mark.xdist_group(name="sdk_tools")
class TestInProcessToolServer:
    """Tests for in-process tool server."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_tool_server_class_exists(self) -> None:
        """Test that InProcessToolServer class exists."""
        from mcp_server_langgraph.sdk.tools import InProcessToolServer

        assert InProcessToolServer is not None

    def test_tool_server_initialization(self) -> None:
        """Test tool server initialization."""
        from mcp_server_langgraph.sdk.tools import InProcessToolServer

        server = InProcessToolServer(name="test-server", version="1.0.0")

        assert server.name == "test-server"
        assert server.version == "1.0.0"

    def test_register_tool(self) -> None:
        """Test registering a tool."""
        from mcp_server_langgraph.sdk.tools import InProcessToolServer

        server = InProcessToolServer(name="test-server")

        async def my_tool(arg: str) -> str:
            return f"Result: {arg}"

        server.register_tool("my_tool", my_tool, {"arg": str})

        assert "my_tool" in server.list_tools()

    @pytest.mark.asyncio
    async def test_call_tool(self) -> None:
        """Test calling a registered tool."""
        from mcp_server_langgraph.sdk.tools import InProcessToolServer

        server = InProcessToolServer(name="test-server")

        async def echo_tool(message: str) -> str:
            return f"Echo: {message}"

        server.register_tool("echo", echo_tool, {"message": str})

        result = await server.call_tool("echo", {"message": "hello"})

        assert result == "Echo: hello"

    @pytest.mark.asyncio
    async def test_call_nonexistent_tool(self) -> None:
        """Test calling a nonexistent tool raises error."""
        from mcp_server_langgraph.sdk.tools import InProcessToolServer

        server = InProcessToolServer(name="test-server")

        with pytest.raises(KeyError):
            await server.call_tool("nonexistent", {})


@pytest.mark.unit
@pytest.mark.sdk
@pytest.mark.xdist_group(name="sdk_state")
class TestAgentStateManager:
    """Tests for cross-session state management."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_state_manager_class_exists(self) -> None:
        """Test that AgentStateManager class exists."""
        from mcp_server_langgraph.sdk.state import AgentStateManager

        assert AgentStateManager is not None

    def test_state_manager_initialization(self, tmp_path) -> None:
        """Test state manager initialization."""
        from mcp_server_langgraph.sdk.state import AgentStateManager

        manager = AgentStateManager(state_dir=tmp_path)

        assert manager.state_dir == tmp_path

    @pytest.mark.asyncio
    async def test_save_state(self, tmp_path) -> None:
        """Test saving session state."""
        from mcp_server_langgraph.sdk.state import AgentStateManager

        manager = AgentStateManager(state_dir=tmp_path)

        await manager.save_state("session-1", {"progress": "50%"})

        state = await manager.resume_session("session-1")
        assert state["progress"] == "50%"

    @pytest.mark.asyncio
    async def test_resume_nonexistent_session(self, tmp_path) -> None:
        """Test resuming nonexistent session returns None."""
        from mcp_server_langgraph.sdk.state import AgentStateManager

        manager = AgentStateManager(state_dir=tmp_path)

        state = await manager.resume_session("nonexistent")

        assert state is None

    @pytest.mark.asyncio
    async def test_checkpoint(self, tmp_path) -> None:
        """Test creating checkpoint."""
        from mcp_server_langgraph.sdk.state import AgentStateManager

        manager = AgentStateManager(state_dir=tmp_path)

        await manager.checkpoint("session-1", "phase-1", "Completed research")

        state = await manager.resume_session("session-1")
        assert "checkpoints" in state
        assert len(state["checkpoints"]) == 1
        assert state["checkpoints"][0]["phase"] == "phase-1"


@pytest.mark.unit
@pytest.mark.sdk
@pytest.mark.xdist_group(name="sdk_llm_integration")
class TestLangGraphAgentClientLLMIntegration:
    """Tests for LLM factory integration in SDK client."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_client_accepts_llm_factory(self) -> None:
        """Test client can be initialized with an LLM factory."""
        from mcp_server_langgraph.sdk.client import LangGraphAgentClient

        # Create a mock LLM factory
        mock_factory = MagicMock()

        client = LangGraphAgentClient(llm_factory=mock_factory)

        assert client.llm_factory is mock_factory

    def test_client_has_llm_factory_attribute(self) -> None:
        """Test client has llm_factory attribute (None by default)."""
        from mcp_server_langgraph.sdk.client import LangGraphAgentClient

        client = LangGraphAgentClient()

        assert hasattr(client, "llm_factory")

    @pytest.mark.asyncio
    async def test_query_uses_llm_factory_when_provided(self) -> None:
        """Test query method uses LLM factory when provided."""
        from langchain_core.messages import AIMessage

        from mcp_server_langgraph.sdk.client import LangGraphAgentClient

        # Create mock LLM factory with ainvoke
        mock_factory = MagicMock()
        mock_factory.ainvoke = AsyncMock(
            return_value=AIMessage(content="LLM response: The answer is 4")
        )

        client = LangGraphAgentClient(llm_factory=mock_factory)

        response = await client.query("What is 2 + 2?")

        # Should call the LLM factory
        mock_factory.ainvoke.assert_called_once()

        # Should return the LLM response content
        assert "LLM response" in response or "4" in response

    @pytest.mark.asyncio
    async def test_query_falls_back_to_placeholder_without_factory(self) -> None:
        """Test query returns placeholder when no LLM factory provided."""
        from mcp_server_langgraph.sdk.client import LangGraphAgentClient

        client = LangGraphAgentClient()

        response = await client.query("What is 2 + 2?")

        # Should return a placeholder response (not an actual LLM call)
        assert response is not None
        assert isinstance(response, str)

    @pytest.mark.asyncio
    async def test_query_formats_prompt_as_human_message(self) -> None:
        """Test query formats prompt correctly for LLM."""
        from langchain_core.messages import AIMessage, HumanMessage

        from mcp_server_langgraph.sdk.client import LangGraphAgentClient

        mock_factory = MagicMock()
        mock_factory.ainvoke = AsyncMock(
            return_value=AIMessage(content="Response")
        )

        client = LangGraphAgentClient(llm_factory=mock_factory)

        await client.query("Test prompt")

        # Check that ainvoke was called with a list containing HumanMessage
        call_args = mock_factory.ainvoke.call_args
        messages = call_args[0][0]  # First positional arg

        assert len(messages) >= 1
        assert isinstance(messages[-1], HumanMessage)
        assert "Test prompt" in str(messages[-1].content)

    @pytest.mark.asyncio
    async def test_query_handles_llm_error_gracefully(self) -> None:
        """Test query handles LLM errors gracefully."""
        from mcp_server_langgraph.sdk.client import LangGraphAgentClient

        mock_factory = MagicMock()
        mock_factory.ainvoke = AsyncMock(side_effect=Exception("LLM unavailable"))

        client = LangGraphAgentClient(llm_factory=mock_factory)

        # Should not crash, may return error message or raise specific exception
        with pytest.raises(Exception) as exc_info:
            await client.query("Test prompt")

        assert "LLM" in str(exc_info.value) or "unavailable" in str(exc_info.value)
