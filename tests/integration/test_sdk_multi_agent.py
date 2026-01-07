"""Integration tests for Claude Agent SDK multi-module interaction.

Tests cross-module integration:
- SDK + Skills integration
- SDK + Agents integration (orchestrator-worker pattern)
- Skills + Agents + Memory integration
- PII hooks + SDK tool calls
"""

from __future__ import annotations

import gc
import pytest

pytestmark = pytest.mark.integration


@pytest.mark.integration
@pytest.mark.sdk
@pytest.mark.xdist_group(name="sdk_integration")
class TestSDKSkillsIntegration:
    """Tests for SDK + Skills module integration."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_sdk_client_can_access_skills_registry(self):
        """SDK client should integrate with skills registry."""
        from mcp_server_langgraph.sdk import LangGraphAgentClient
        from mcp_server_langgraph.skills import SkillRegistry

        LangGraphAgentClient()
        registry = SkillRegistry()

        # Skills registry should be accessible from SDK context
        assert registry is not None
        assert hasattr(registry, "list_all")
        assert hasattr(registry, "get")

    @pytest.mark.asyncio
    async def test_sdk_tool_server_can_register_skill_tools(self):
        """In-process tool server should register skill-based tools."""
        from mcp_server_langgraph.sdk import InProcessToolServer
        from mcp_server_langgraph.skills import SkillRegistry

        server = InProcessToolServer(name="skill-tools")
        registry = SkillRegistry()

        # Register a skill-based tool
        async def skill_executor(skill_name: str, args: dict) -> str:
            skill = registry.get_skill(skill_name)
            if skill:
                return f"Executed skill: {skill.name}"
            return "Skill not found"

        server.register_tool(
            "execute_skill",
            skill_executor,
            {"skill_name": str, "args": dict},
            "Execute a registered skill",
        )

        # Verify tool is registered
        assert "execute_skill" in server.list_tools()

    @pytest.mark.asyncio
    async def test_sdk_calls_skill_through_tool_server(self):
        """SDK client should call skills through in-process tool server."""
        from mcp_server_langgraph.sdk import LangGraphAgentClient, InProcessToolServer

        # Create custom tool server with skill execution
        server = InProcessToolServer(name="skill-runner")

        async def mock_skill_executor(skill_name: str) -> str:
            return f"Skill '{skill_name}' executed successfully"

        server.register_tool(
            "run_skill",
            mock_skill_executor,
            {"skill_name": str},
            "Run a skill by name",
        )

        # Create client with custom tool server
        client = LangGraphAgentClient(tool_server=server)

        # Call skill through SDK
        result = await client.call_tool("run_skill", {"skill_name": "web-research"})
        assert "web-research" in result
        assert "executed" in result.lower()


@pytest.mark.integration
@pytest.mark.sdk
@pytest.mark.multi_agent
@pytest.mark.xdist_group(name="sdk_agents_integration")
class TestSDKAgentsIntegration:
    """Tests for SDK + Multi-Agent orchestration integration."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_sdk_client_uses_orchestrator(self):
        """SDK client should use orchestrator for task decomposition."""
        from mcp_server_langgraph.sdk import LangGraphAgentClient
        from mcp_server_langgraph.agents import Orchestrator

        client = LangGraphAgentClient()

        # Client should have orchestrator
        assert hasattr(client, "orchestrator")
        assert isinstance(client.orchestrator, Orchestrator)

    @pytest.mark.asyncio
    async def test_sdk_orchestrated_task_decomposes_correctly(self):
        """SDK orchestrated task should decompose into subtasks."""
        from mcp_server_langgraph.sdk import LangGraphAgentClient

        client = LangGraphAgentClient()

        # Run orchestrated task
        result = await client.run_orchestrated_task(
            task="Research quantum computing advances",
            subagent_count=3,
            strategy="parallel",
        )

        # Verify decomposition occurred
        assert "task" in result
        assert "subtask_count" in result
        assert result["subtask_count"] > 0
        assert "synthesis" in result

    @pytest.mark.asyncio
    async def test_sdk_uses_model_selector_for_tiers(self):
        """SDK client should use model selector for tier-based selection."""
        from mcp_server_langgraph.sdk import LangGraphAgentClient
        from mcp_server_langgraph.agents import ModelSelector

        # Create with different tiers
        simple_client = LangGraphAgentClient(model_tier="simple")
        complex_client = LangGraphAgentClient(model_tier="complex")

        # Both should have model selector
        assert hasattr(simple_client, "model_selector")
        assert isinstance(simple_client.model_selector, ModelSelector)
        assert isinstance(complex_client.model_selector, ModelSelector)

    @pytest.mark.asyncio
    async def test_sdk_parallel_execution_strategy(self):
        """SDK should support parallel execution strategy."""
        from mcp_server_langgraph.sdk import LangGraphAgentClient

        client = LangGraphAgentClient()

        # Run with parallel strategy
        result = await client.run_orchestrated_task(
            task="Analyze codebase for security issues",
            subagent_count=5,
            strategy="parallel",
        )

        assert result["strategy"] == "parallel"
        assert result["subtask_count"] <= 5


@pytest.mark.integration
@pytest.mark.sdk
@pytest.mark.memory
@pytest.mark.xdist_group(name="sdk_memory_integration")
class TestSDKMemoryIntegration:
    """Tests for SDK + Memory module integration."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_sdk_client_has_state_manager(self):
        """SDK client should have state manager for memory."""
        from mcp_server_langgraph.sdk import LangGraphAgentClient, AgentStateManager

        client = LangGraphAgentClient()

        assert hasattr(client, "state_manager")
        assert isinstance(client.state_manager, AgentStateManager)

    @pytest.mark.asyncio
    async def test_sdk_session_state_persistence(self):
        """SDK should persist session state across calls."""
        from mcp_server_langgraph.sdk import LangGraphAgentClient

        client = LangGraphAgentClient()
        session_id = "test-session-001"

        # Make query with session ID
        await client.query("First query", session_id=session_id)

        # State should be saved
        state = await client.state_manager.resume_session(session_id)
        assert state is not None
        assert "last_query" in state

    @pytest.mark.asyncio
    async def test_sdk_checkpoint_creation(self):
        """SDK should create checkpoints for phase completion."""
        from mcp_server_langgraph.sdk import LangGraphAgentClient
        import uuid

        client = LangGraphAgentClient()
        # Use unique session ID to avoid state from previous test runs
        session_id = f"test-checkpoint-session-{uuid.uuid4().hex[:8]}"

        # Create checkpoint
        await client.checkpoint_session(
            session_id=session_id,
            phase="research",
            summary="Completed initial research phase",
        )

        # Verify checkpoint exists
        state = await client.state_manager.resume_session(session_id)
        assert state is not None
        assert "checkpoints" in state
        assert len(state["checkpoints"]) == 1
        assert state["checkpoints"][0]["phase"] == "research"


@pytest.mark.integration
@pytest.mark.sdk
@pytest.mark.pii
@pytest.mark.xdist_group(name="sdk_pii_integration")
class TestSDKPIIIntegration:
    """Tests for SDK + PII tokenization hooks integration."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_sdk_client_has_hook_registry(self):
        """SDK client should have security hook registry."""
        from mcp_server_langgraph.sdk import LangGraphAgentClient, SecurityHookRegistry

        client = LangGraphAgentClient()

        assert hasattr(client, "hook_registry")
        assert isinstance(client.hook_registry, SecurityHookRegistry)

    @pytest.mark.asyncio
    async def test_sdk_hooks_execute_before_tool_call(self):
        """Security hooks should execute before tool calls."""
        from mcp_server_langgraph.sdk import (
            LangGraphAgentClient,
            SecurityHookRegistry,
            InProcessToolServer,
            HookResult,
        )

        # Track hook execution
        hook_executed = False

        async def tracking_hook(input_data, tool_use_id, context):
            nonlocal hook_executed
            hook_executed = True
            return HookResult.allow()

        # Create registry with tracking hook
        registry = SecurityHookRegistry()
        registry.register("PreToolUse", "*", tracking_hook)

        # Create tool server with async handler
        async def test_handler() -> str:
            return "test result"

        server = InProcessToolServer()
        server.register_tool(
            "test_tool",
            test_handler,
            {},
            "Test tool",
        )

        # Create client with custom registry
        client = LangGraphAgentClient(
            tool_server=server,
            hook_registry=registry,
        )

        # Call tool
        await client.call_tool("test_tool", {})

        # Hook should have executed
        assert hook_executed

    @pytest.mark.asyncio
    async def test_sdk_denied_hook_prevents_tool_execution(self):
        """Denied hook should prevent tool execution."""
        from mcp_server_langgraph.sdk import (
            LangGraphAgentClient,
            SecurityHookRegistry,
            InProcessToolServer,
            HookResult,
        )

        async def deny_hook(input_data, tool_use_id, context):
            return HookResult.deny("Access denied for testing")

        registry = SecurityHookRegistry()
        registry.register("PreToolUse", "*", deny_hook)

        async def blocked_handler() -> str:
            return "should not execute"

        server = InProcessToolServer()
        server.register_tool(
            "blocked_tool",
            blocked_handler,
            {},
            "Blocked tool",
        )

        client = LangGraphAgentClient(
            tool_server=server,
            hook_registry=registry,
        )

        # Call should raise PermissionError
        with pytest.raises(PermissionError) as exc_info:
            await client.call_tool("blocked_tool", {})

        assert "Access denied" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_sdk_command_allowlist_hook_blocks_dangerous_commands(self):
        """Command allowlist hook should block dangerous bash commands."""
        from mcp_server_langgraph.sdk import (
            LangGraphAgentClient,
            DEFAULT_SECURITY_HOOKS,
            InProcessToolServer,
        )

        server = InProcessToolServer()
        server.register_tool(
            "Bash",
            lambda command: f"Executed: {command}",
            {"command": str},
            "Execute bash command",
        )

        client = LangGraphAgentClient(
            tool_server=server,
            hook_registry=DEFAULT_SECURITY_HOOKS,
        )

        # Dangerous command should be blocked
        with pytest.raises(PermissionError) as exc_info:
            await client.call_tool("Bash", {"command": "rm -rf /"})

        assert "Blocked dangerous pattern" in str(exc_info.value)


@pytest.mark.integration
@pytest.mark.sdk
@pytest.mark.skills
@pytest.mark.multi_agent
@pytest.mark.memory
@pytest.mark.xdist_group(name="full_workflow_integration")
class TestFullWorkflowIntegration:
    """Tests for full workflow: SDK + Skills + Agents + Memory."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_full_agent_workflow_with_memory(self):
        """Test complete agent workflow with memory persistence."""
        from mcp_server_langgraph.sdk import LangGraphAgentClient
        from mcp_server_langgraph.memory import NotesManager, CheckpointManager
        from pathlib import Path
        import tempfile

        # Create temp directory for persistence
        with tempfile.TemporaryDirectory() as tmpdir:
            notes_manager = NotesManager(notes_path=Path(tmpdir) / "NOTES.md")
            checkpoint_manager = CheckpointManager()

            client = LangGraphAgentClient()
            session_id = "workflow-session"

            # Phase 1: Research
            await client.query("Research AI safety", session_id=session_id)
            notes_manager.add_note(
                content="Researched AI safety approaches",
                category="research",
            )
            checkpoint_manager.create_checkpoint(
                phase="research",
                summary="Completed AI safety research",
            )

            # Phase 2: Analysis
            result = await client.run_orchestrated_task(
                task="Analyze AI safety findings",
                subagent_count=2,
            )
            notes_manager.add_note(
                content=f"Analysis complete: {result['subtask_count']} subtasks",
                category="analysis",
            )
            checkpoint_manager.create_checkpoint(
                phase="analysis",
                summary="Synthesized findings",
            )

            # Verify memory state
            all_notes = notes_manager.list_notes()
            assert len(all_notes) == 2

            session_summary = checkpoint_manager.summarize_session()
            assert "research" in session_summary.lower()
            assert "analysis" in session_summary.lower()

    @pytest.mark.asyncio
    async def test_sdk_client_exports_available(self):
        """All SDK exports should be importable."""
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

        # All imports should succeed
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

    @pytest.mark.asyncio
    async def test_agents_module_exports_available(self):
        """All agents module exports should be importable."""
        from mcp_server_langgraph.agents import (
            Orchestrator,
            Subagent,
            Coordinator,
            ArtifactStorage,
            ModelSelector,
            TaskDecomposition,
            SubagentResult,
        )

        # All imports should succeed
        assert Orchestrator is not None
        assert Subagent is not None
        assert Coordinator is not None
        assert ArtifactStorage is not None
        assert ModelSelector is not None
        assert TaskDecomposition is not None
        assert SubagentResult is not None

    @pytest.mark.asyncio
    async def test_memory_module_exports_available(self):
        """All memory module exports should be importable."""
        from mcp_server_langgraph.memory import (
            Note,
            NotesManager,
            Checkpoint,
            CheckpointManager,
        )

        # All imports should succeed
        assert Note is not None
        assert NotesManager is not None
        assert Checkpoint is not None
        assert CheckpointManager is not None

    @pytest.mark.asyncio
    async def test_skills_module_exports_available(self):
        """All skills module exports should be importable."""
        from mcp_server_langgraph.skills import (
            Skill,
            SandboxConfig,
            SkillLoader,
            SkillRegistry,
        )

        # All imports should succeed
        assert Skill is not None
        assert SandboxConfig is not None
        assert SkillLoader is not None
        assert SkillRegistry is not None
