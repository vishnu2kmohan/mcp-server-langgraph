"""End-to-end tests for complete SDK workflow scenarios.

Tests realistic agent workflows that exercise the full SDK stack:
- Client initialization with all components
- Hook execution flow
- Multi-phase task execution with checkpoints
- Error recovery and graceful degradation

These tests simulate real-world usage patterns.
"""

from __future__ import annotations

import gc
import uuid
from typing import Any

import pytest

pytestmark = [pytest.mark.e2e, pytest.mark.sdk]


@pytest.mark.e2e
@pytest.mark.sdk
@pytest.mark.xdist_group(name="sdk_e2e_workflow")
class TestSDKCompleteWorkflow:
    """End-to-end tests for complete SDK workflows."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_complete_research_workflow(self) -> None:
        """Test a complete research workflow: query -> checkpoint -> tool call."""
        from mcp_server_langgraph.sdk import (
            LangGraphAgentClient,
            InProcessToolServer,
            SecurityHookRegistry,
            HookResult,
        )

        # Track hook execution
        hook_execution_log: list[str] = []

        async def tracking_pre_hook(input_data: dict, tool_use_id: str, context: dict) -> HookResult:
            tool_name = input_data.get("tool_name", "unknown")
            hook_execution_log.append(f"PRE:{tool_name}")
            return HookResult.allow()

        # Setup components
        registry = SecurityHookRegistry()
        registry.register("PreToolUse", "*", tracking_pre_hook)

        server = InProcessToolServer(name="research-tools")

        async def search_tool(query: str) -> str:
            return f"Found 5 results for: {query}"

        async def analyze_tool(content: str) -> str:
            return f"Analysis complete: {len(content)} chars processed"

        server.register_tool("search", search_tool, {"query": str}, "Search for information")
        server.register_tool("analyze", analyze_tool, {"content": str}, "Analyze content")

        client = LangGraphAgentClient(
            tool_server=server,
            hook_registry=registry,
        )
        session_id = f"research-{uuid.uuid4().hex[:8]}"

        # Phase 1: Initial query
        result = await client.call_tool("search", {"query": "quantum computing"})
        assert "quantum computing" in result

        # Phase 2: Create checkpoint
        await client.checkpoint_session(
            session_id=session_id,
            phase="research",
            summary="Initial research completed",
        )

        # Phase 3: Analysis
        analysis_result = await client.call_tool("analyze", {"content": result})
        assert "Analysis complete" in analysis_result

        # Verify hook execution order
        assert len(hook_execution_log) == 2  # 2 tools
        assert hook_execution_log[0] == "PRE:search"
        assert hook_execution_log[1] == "PRE:analyze"

        # Verify checkpoint was saved
        state = await client.state_manager.resume_session(session_id)
        assert state is not None
        assert "checkpoints" in state
        assert state["checkpoints"][0]["phase"] == "research"

    @pytest.mark.asyncio
    async def test_security_hook_blocks_dangerous_operation(self) -> None:
        """Test that security hooks properly block dangerous operations."""
        from mcp_server_langgraph.sdk import (
            LangGraphAgentClient,
            InProcessToolServer,
            SecurityHookRegistry,
            HookResult,
        )

        blocked_operations: list[str] = []

        async def security_hook(input_data: dict, tool_use_id: str, context: dict) -> HookResult:
            tool_input = input_data.get("tool_input", {})
            command = tool_input.get("command", "")
            # Block dangerous rm commands
            if "rm -rf" in command or "rm -r /" in command:
                blocked_operations.append(command)
                return HookResult.deny("Blocked dangerous rm command")
            return HookResult.allow()

        registry = SecurityHookRegistry()
        registry.register("PreToolUse", "Bash", security_hook)

        server = InProcessToolServer()

        async def bash_handler(command: str) -> str:
            return f"Executed: {command}"

        server.register_tool("Bash", bash_handler, {"command": str}, "Execute bash command")

        client = LangGraphAgentClient(
            tool_server=server,
            hook_registry=registry,
        )

        # Safe command should work
        result = await client.call_tool("Bash", {"command": "ls -la"})
        assert "Executed: ls -la" in result

        # Dangerous command should be blocked
        with pytest.raises(PermissionError) as exc_info:
            await client.call_tool("Bash", {"command": "rm -rf /"})

        assert "Blocked dangerous rm command" in str(exc_info.value)
        assert len(blocked_operations) == 1

    @pytest.mark.asyncio
    async def test_hook_input_transformation(self) -> None:
        """Test that hooks can transform input before tool execution."""
        from mcp_server_langgraph.sdk import (
            LangGraphAgentClient,
            InProcessToolServer,
            SecurityHookRegistry,
            HookResult,
        )

        async def sanitize_hook(input_data: dict, tool_use_id: str, context: dict) -> HookResult:
            sanitized = {**input_data}
            tool_input = sanitized.get("tool_input", {})
            # Add prefix to all queries
            if "query" in tool_input:
                tool_input["query"] = f"[SANITIZED] {tool_input['query']}"
                sanitized["tool_input"] = tool_input
            return HookResult.allow(modified_input=sanitized)

        registry = SecurityHookRegistry()
        registry.register("PreToolUse", "*", sanitize_hook)

        server = InProcessToolServer()

        captured_input: dict[str, Any] = {}

        async def capture_handler(query: str) -> str:
            captured_input["query"] = query
            return f"Processed: {query}"

        server.register_tool("search", capture_handler, {"query": str}, "Search")

        client = LangGraphAgentClient(
            tool_server=server,
            hook_registry=registry,
        )

        await client.call_tool("search", {"query": "test query"})

        # Verify the hook transformed the input
        assert "[SANITIZED]" in captured_input["query"]
        assert "test query" in captured_input["query"]

    @pytest.mark.asyncio
    async def test_multi_phase_workflow_with_state_persistence(self) -> None:
        """Test multi-phase workflow with state persistence across phases."""
        from mcp_server_langgraph.sdk import LangGraphAgentClient, InProcessToolServer

        server = InProcessToolServer()

        async def phase_handler(phase: str, data: str) -> str:
            return f"Phase {phase} completed with: {data}"

        server.register_tool("execute_phase", phase_handler, {"phase": str, "data": str}, "Execute workflow phase")

        client = LangGraphAgentClient(tool_server=server)
        session_id = f"multi-phase-{uuid.uuid4().hex[:8]}"

        # Phase 1: Gather
        result1 = await client.call_tool("execute_phase", {"phase": "gather", "data": "initial data"})
        await client.checkpoint_session(
            session_id=session_id,
            phase="gather",
            summary="Data gathering complete",
        )

        # Phase 2: Process
        result2 = await client.call_tool("execute_phase", {"phase": "process", "data": result1})
        await client.checkpoint_session(
            session_id=session_id,
            phase="process",
            summary="Processing complete",
        )

        # Phase 3: Verify
        await client.call_tool("execute_phase", {"phase": "verify", "data": result2})
        await client.checkpoint_session(
            session_id=session_id,
            phase="verify",
            summary="Verification complete",
        )

        # Verify all checkpoints
        state = await client.state_manager.resume_session(session_id)
        assert state is not None
        assert len(state["checkpoints"]) == 3
        phases = [cp["phase"] for cp in state["checkpoints"]]
        assert phases == ["gather", "process", "verify"]

    @pytest.mark.asyncio
    async def test_error_recovery_in_workflow(self) -> None:
        """Test graceful error recovery when a tool fails mid-workflow."""
        from mcp_server_langgraph.sdk import (
            LangGraphAgentClient,
            InProcessToolServer,
            SecurityHookRegistry,
            HookResult,
        )

        error_count = 0

        async def error_tracking_hook(input_data: dict, tool_use_id: str, context: dict) -> HookResult:
            return HookResult.allow()

        registry = SecurityHookRegistry()
        registry.register("PreToolUse", "*", error_tracking_hook)

        server = InProcessToolServer()

        async def flaky_handler(attempt: int) -> str:
            nonlocal error_count
            if attempt == 1:
                error_count += 1
                raise RuntimeError("Transient failure")
            return f"Success on attempt {attempt}"

        async def stable_handler(data: str) -> str:
            return f"Stable: {data}"

        server.register_tool("flaky", flaky_handler, {"attempt": int}, "Flaky tool")
        server.register_tool("stable", stable_handler, {"data": str}, "Stable tool")

        client = LangGraphAgentClient(
            tool_server=server,
            hook_registry=registry,
        )

        # First attempt fails
        with pytest.raises(RuntimeError):
            await client.call_tool("flaky", {"attempt": 1})

        assert error_count == 1

        # Retry succeeds
        result = await client.call_tool("flaky", {"attempt": 2})
        assert "Success on attempt 2" in result

        # Stable tool should work after failure
        stable_result = await client.call_tool("stable", {"data": "test"})
        assert "Stable: test" in stable_result

    @pytest.mark.asyncio
    async def test_all_sdk_exports_work_together(self) -> None:
        """Integration test verifying all SDK exports work together."""
        from mcp_server_langgraph.sdk import (
            LangGraphAgentClient,
            InProcessToolServer,
            ToolDefinition,
            create_default_server,
            think_tool,
            search_tools_tool,
            HookResult,
            PreToolUseHook,
            SecurityHookRegistry,
            DEFAULT_SECURITY_HOOKS,
            pii_detection_hook,
            command_allowlist_hook,
            rate_limit_hook,
            AgentStateManager,
        )

        # Verify all exports are usable
        assert LangGraphAgentClient is not None
        assert InProcessToolServer is not None
        assert ToolDefinition is not None
        assert create_default_server is not None
        assert think_tool is not None
        assert search_tools_tool is not None
        assert HookResult is not None
        assert PreToolUseHook is not None
        assert SecurityHookRegistry is not None
        assert DEFAULT_SECURITY_HOOKS is not None
        assert pii_detection_hook is not None
        assert command_allowlist_hook is not None
        assert rate_limit_hook is not None
        assert AgentStateManager is not None

        # Create a working client using multiple exports
        server = create_default_server()
        registry = SecurityHookRegistry()
        AgentStateManager()

        # Register a custom hook
        async def custom_hook(input_data: dict, tool_use_id: str, context: dict) -> HookResult:
            return HookResult.allow()

        registry.register("PreToolUse", "*", custom_hook)

        client = LangGraphAgentClient(
            tool_server=server,
            hook_registry=registry,
        )

        # Verify client is functional
        assert hasattr(client, "call_tool")
        assert hasattr(client, "query")
        assert hasattr(client, "state_manager")
        assert hasattr(client, "hook_registry")


@pytest.mark.e2e
@pytest.mark.sdk
@pytest.mark.xdist_group(name="sdk_e2e_agents")
class TestSDKAgentsE2E:
    """End-to-end tests for SDK agent components."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_model_selector_selects_models(self) -> None:
        """Test that ModelSelector properly selects models for different tiers."""
        from mcp_server_langgraph.agents import ModelSelector

        selector = ModelSelector()

        # Simple tier should return a model
        simple_model = selector.select_model("simple")
        assert simple_model is not None
        assert isinstance(simple_model, str)

        # Complicated tier should return a model
        complicated_model = selector.select_model("complicated")
        assert complicated_model is not None
        assert isinstance(complicated_model, str)

        # Complex tier should return a model
        complex_model = selector.select_model("complex")
        assert complex_model is not None
        assert isinstance(complex_model, str)

    @pytest.mark.asyncio
    async def test_agent_definition_structure(self) -> None:
        """Test that AgentDefinition has the expected structure."""
        from mcp_server_langgraph.agents import AgentDefinition

        # Create a simple agent definition
        definition = AgentDefinition(
            name="test-agent",
            description="A test agent for research",
            prompt="You are a helpful assistant",
            tools=["Read", "Write", "Grep"],
            model="haiku",
        )

        # Verify fields
        assert definition.name == "test-agent"
        assert definition.description == "A test agent for research"
        assert definition.prompt == "You are a helpful assistant"
        assert "Read" in definition.tools
        assert definition.model == "haiku"

    @pytest.mark.asyncio
    async def test_orchestrator_initialization(self) -> None:
        """Test that Orchestrator initializes correctly."""
        from mcp_server_langgraph.agents import Orchestrator, ModelSelector

        selector = ModelSelector()
        orchestrator = Orchestrator(model_selector=selector)

        # Verify orchestrator is functional
        assert orchestrator is not None
        assert hasattr(orchestrator, "decompose_task")
        assert hasattr(orchestrator, "execute")
        assert hasattr(orchestrator, "synthesize")

    @pytest.mark.asyncio
    async def test_client_with_custom_components(self) -> None:
        """Test client initialization with custom components."""
        from mcp_server_langgraph.sdk import (
            LangGraphAgentClient,
            InProcessToolServer,
            SecurityHookRegistry,
            AgentStateManager,
        )
        from mcp_server_langgraph.agents import ModelSelector, Orchestrator

        # Create custom components
        selector = ModelSelector()
        orchestrator = Orchestrator(model_selector=selector)
        server = InProcessToolServer(name="custom-tools")
        registry = SecurityHookRegistry()
        state_manager = AgentStateManager()

        # Register test tool
        async def test_tool(message: str) -> str:
            return f"Echo: {message}"

        server.register_tool("echo", test_tool, {"message": str}, "Echo tool")

        # Create client with all custom components
        client = LangGraphAgentClient(
            model_tier="simple",
            model_selector=selector,
            orchestrator=orchestrator,
            tool_server=server,
            hook_registry=registry,
            state_manager=state_manager,
        )

        # Verify client has all components
        assert client.model_selector is selector
        assert client.orchestrator is orchestrator
        assert client.tool_server is server
        assert client.hook_registry is registry
        assert client.state_manager is state_manager

        # Verify tool works
        result = await client.call_tool("echo", {"message": "Hello"})
        assert "Echo: Hello" in result

    @pytest.mark.asyncio
    async def test_state_manager_session_lifecycle(self) -> None:
        """Test complete session lifecycle with state manager."""
        from mcp_server_langgraph.sdk import AgentStateManager

        state_manager = AgentStateManager()
        session_id = f"lifecycle-test-{uuid.uuid4().hex[:8]}"

        # Save initial state
        await state_manager.save_state(
            session_id,
            {
                "step": 1,
                "data": "initial",
            },
        )

        # Resume and verify
        state = await state_manager.resume_session(session_id)
        assert state is not None
        assert state.get("step") == 1
        assert state.get("data") == "initial"

        # Create checkpoint
        await state_manager.checkpoint(session_id, "phase1", "First phase complete")

        # Verify checkpoint in state
        updated_state = await state_manager.resume_session(session_id)
        assert "checkpoints" in updated_state
        assert len(updated_state["checkpoints"]) == 1
        assert updated_state["checkpoints"][0]["phase"] == "phase1"

        # Add more checkpoints
        await state_manager.checkpoint(session_id, "phase2", "Second phase complete")
        await state_manager.checkpoint(session_id, "phase3", "Third phase complete")

        # Verify all checkpoints
        final_state = await state_manager.resume_session(session_id)
        assert len(final_state["checkpoints"]) == 3
