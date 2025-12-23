"""
Tests for MCP Orchestration Resources.

Tests the MCP resource endpoints for multi-agent orchestration:
- orchestrator://tasks/{task_id} - Task decomposition and status
- orchestrator://artifacts/{task_id}/{artifact_name} - Artifacts from subagents
- orchestrator://subagents/{task_id} - Subagent status

TDD: RED phase - Define expected behavior for orchestration resources.

References:
- Plan Section 10.4: Expose Multi-Agent as MCP Resources/Tools
- MCP Resources Protocol: https://modelcontextprotocol.io/specification/2025-11-25/server/resources
"""

import gc
import json

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="mcp_orchestrator_resources")
class TestOrchestratorResourceHandler:
    """Test orchestrator resource handler setup."""

    def teardown_method(self) -> None:
        """Clean up after each test."""
        gc.collect()

    def test_create_orchestrator_resource_handler_returns_handler(self) -> None:
        """create_orchestrator_resource_handler should return a ResourceHandler."""
        from mcp_server_langgraph.mcp.resources_orchestrator import (
            create_orchestrator_resource_handler,
        )

        handler = create_orchestrator_resource_handler()

        assert handler is not None

    def test_handler_has_task_template(self) -> None:
        """Handler should have task resource template registered."""
        from mcp_server_langgraph.mcp.resources_orchestrator import (
            create_orchestrator_resource_handler,
        )

        handler = create_orchestrator_resource_handler()
        templates = handler.list_templates()

        # Check for task template
        template_uris = [t.uriTemplate for t in templates]
        assert any("tasks" in uri for uri in template_uris), "Should have tasks template"

    def test_handler_has_artifact_template(self) -> None:
        """Handler should have artifact resource template registered."""
        from mcp_server_langgraph.mcp.resources_orchestrator import (
            create_orchestrator_resource_handler,
        )

        handler = create_orchestrator_resource_handler()
        templates = handler.list_templates()

        template_uris = [t.uriTemplate for t in templates]
        assert any("artifacts" in uri for uri in template_uris), "Should have artifacts template"

    def test_handler_has_subagent_template(self) -> None:
        """Handler should have subagent resource template registered."""
        from mcp_server_langgraph.mcp.resources_orchestrator import (
            create_orchestrator_resource_handler,
        )

        handler = create_orchestrator_resource_handler()
        templates = handler.list_templates()

        template_uris = [t.uriTemplate for t in templates]
        assert any("subagents" in uri for uri in template_uris), "Should have subagents template"


@pytest.mark.xdist_group(name="mcp_orchestrator_resources")
class TestTaskResourceProvider:
    """Test task resource provider."""

    def teardown_method(self) -> None:
        """Clean up after each test."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_task_provider_returns_task_decomposition(self) -> None:
        """Task provider should return task decomposition data."""
        from mcp_server_langgraph.agents.orchestrator import Subtask, TaskDecomposition
        from mcp_server_langgraph.mcp.resources_orchestrator import (
            OrchestratorResourceProvider,
        )

        # Create mock decomposition
        decomposition = TaskDecomposition(
            original_task="Research AI safety",
            subtasks=[
                Subtask(
                    task_id="task-001",
                    title="Survey literature",
                    instructions="Survey recent papers on AI safety",
                    complexity="complicated",
                ),
                Subtask(
                    task_id="task-002",
                    title="Identify gaps",
                    instructions="Identify research gaps",
                    complexity="complex",
                ),
            ],
            synthesis_instructions="Combine findings into summary",
        )

        # Create provider with mock storage
        provider = OrchestratorResourceProvider()
        provider.store_task("task-main-001", decomposition)

        # Read the resource
        content = await provider.read_task("orchestrator://tasks/task-main-001")

        assert content is not None
        assert content.mimeType == "application/json"

        data = json.loads(content.text)
        assert data["original_task"] == "Research AI safety"
        assert len(data["subtasks"]) == 2

    @pytest.mark.asyncio
    async def test_task_provider_not_found_raises_error(self) -> None:
        """Task provider should raise error for unknown task."""
        from mcp_server_langgraph.mcp.resources_orchestrator import (
            OrchestratorResourceProvider,
        )

        provider = OrchestratorResourceProvider()

        with pytest.raises(ValueError, match="Task not found"):
            await provider.read_task("orchestrator://tasks/nonexistent-task")


@pytest.mark.xdist_group(name="mcp_orchestrator_resources")
class TestArtifactResourceProvider:
    """Test artifact resource provider."""

    def teardown_method(self) -> None:
        """Clean up after each test."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_artifact_provider_returns_artifact_data(self) -> None:
        """Artifact provider should return artifact data."""
        from mcp_server_langgraph.agents.artifacts import ArtifactStorage
        from mcp_server_langgraph.mcp.resources_orchestrator import (
            OrchestratorResourceProvider,
        )

        # Create artifact storage with data
        storage = ArtifactStorage()
        storage.store(
            task_id="task-001",
            name="research_summary",
            data={"findings": ["Finding 1", "Finding 2"], "confidence": 0.85},
        )

        provider = OrchestratorResourceProvider(artifact_storage=storage)

        content = await provider.read_artifact("orchestrator://artifacts/task-001/research_summary")

        assert content is not None
        assert content.mimeType == "application/json"

        data = json.loads(content.text)
        assert "findings" in data["data"]
        assert data["task_id"] == "task-001"

    @pytest.mark.asyncio
    async def test_artifact_provider_not_found_raises_error(self) -> None:
        """Artifact provider should raise error for unknown artifact."""
        from mcp_server_langgraph.mcp.resources_orchestrator import (
            OrchestratorResourceProvider,
        )

        provider = OrchestratorResourceProvider()

        with pytest.raises(ValueError, match="Artifact not found"):
            await provider.read_artifact("orchestrator://artifacts/task-001/nonexistent")


@pytest.mark.xdist_group(name="mcp_orchestrator_resources")
class TestSubagentResourceProvider:
    """Test subagent status resource provider."""

    def teardown_method(self) -> None:
        """Clean up after each test."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_subagent_provider_returns_status_list(self) -> None:
        """Subagent provider should return list of subagent statuses."""
        from mcp_server_langgraph.agents.subagent import SubagentResult
        from mcp_server_langgraph.mcp.resources_orchestrator import (
            OrchestratorResourceProvider,
        )

        # Create mock subagent results
        results = [
            SubagentResult(
                task_id="sub-001",
                success=True,
                output={"summary": "Analysis complete"},
                duration_ms=1500.0,
                confidence=0.92,
            ),
            SubagentResult(
                task_id="sub-002",
                success=False,
                error="Timeout",
                duration_ms=5000.0,
                confidence=0.0,
            ),
        ]

        provider = OrchestratorResourceProvider()
        provider.store_subagent_results("task-main-001", results)

        content = await provider.read_subagents("orchestrator://subagents/task-main-001")

        assert content is not None
        assert content.mimeType == "application/json"

        data = json.loads(content.text)
        assert len(data["subagents"]) == 2
        assert data["subagents"][0]["task_id"] == "sub-001"
        assert data["subagents"][0]["success"] is True
        assert data["subagents"][1]["success"] is False

    @pytest.mark.asyncio
    async def test_subagent_provider_empty_for_unknown_task(self) -> None:
        """Subagent provider should return empty list for unknown task."""
        from mcp_server_langgraph.mcp.resources_orchestrator import (
            OrchestratorResourceProvider,
        )

        provider = OrchestratorResourceProvider()

        content = await provider.read_subagents("orchestrator://subagents/unknown-task")

        data = json.loads(content.text)
        assert data["subagents"] == []


@pytest.mark.xdist_group(name="mcp_orchestrator_resources")
class TestResourceURIParsing:
    """Test URI parsing for orchestrator resources."""

    def teardown_method(self) -> None:
        """Clean up after each test."""
        gc.collect()

    def test_parse_task_uri(self) -> None:
        """Should correctly parse task URI."""
        from mcp_server_langgraph.mcp.resources_orchestrator import parse_orchestrator_uri

        result = parse_orchestrator_uri("orchestrator://tasks/my-task-123")

        assert result["resource_type"] == "tasks"
        assert result["task_id"] == "my-task-123"
        assert result["artifact_name"] is None

    def test_parse_artifact_uri(self) -> None:
        """Should correctly parse artifact URI with task and artifact name."""
        from mcp_server_langgraph.mcp.resources_orchestrator import parse_orchestrator_uri

        result = parse_orchestrator_uri("orchestrator://artifacts/task-123/my_artifact")

        assert result["resource_type"] == "artifacts"
        assert result["task_id"] == "task-123"
        assert result["artifact_name"] == "my_artifact"

    def test_parse_subagent_uri(self) -> None:
        """Should correctly parse subagent URI."""
        from mcp_server_langgraph.mcp.resources_orchestrator import parse_orchestrator_uri

        result = parse_orchestrator_uri("orchestrator://subagents/main-task")

        assert result["resource_type"] == "subagents"
        assert result["task_id"] == "main-task"

    def test_parse_invalid_uri_raises_error(self) -> None:
        """Should raise error for invalid URI format."""
        from mcp_server_langgraph.mcp.resources_orchestrator import parse_orchestrator_uri

        with pytest.raises(ValueError, match="Invalid orchestrator URI"):
            parse_orchestrator_uri("invalid://uri")
