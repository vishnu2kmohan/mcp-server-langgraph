"""
Integration tests for MCP Orchestration Roundtrip.

Tests the complete orchestration flow exposed via MCP:
- orchestrator://tasks/{task_id} resources
- orchestrator://artifacts/{task_id}/{name} resources
- orchestrator://subagents/{task_id} resources
- Orchestration tool operations (decompose, execute, status, cancel)

TDD: Tests written FIRST.
"""

from __future__ import annotations

import gc
import json
import os
from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.mcp,
    pytest.mark.orchestrator,
]


@pytest.fixture
def enable_orchestration_features():
    """Enable orchestration MCP feature flags."""
    originals = {
        "FF_ENABLE_ORCHESTRATION_MCP_TOOLS": os.environ.get("FF_ENABLE_ORCHESTRATION_MCP_TOOLS"),
        "FF_ENABLE_ORCHESTRATION_MCP_RESOURCES": os.environ.get("FF_ENABLE_ORCHESTRATION_MCP_RESOURCES"),
    }
    os.environ["FF_ENABLE_ORCHESTRATION_MCP_TOOLS"] = "true"
    os.environ["FF_ENABLE_ORCHESTRATION_MCP_RESOURCES"] = "true"
    yield
    for key, val in originals.items():
        if val is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = val


@pytest.fixture
def mock_orchestrator():
    """Create a mock orchestrator for testing."""
    orchestrator = MagicMock()
    orchestrator.get_task = MagicMock(
        return_value={
            "task_id": "task-123",
            "status": "completed",
            "subtasks": ["sub-1", "sub-2"],
            "created_at": datetime.now(UTC).isoformat(),
        }
    )
    return orchestrator


@pytest.fixture
def mock_artifact_storage():
    """Create a mock artifact storage."""
    storage = MagicMock()
    mock_artifact = MagicMock()
    mock_artifact.task_id = "task-123"
    mock_artifact.name = "result"
    mock_artifact.data = {"analysis": "complete", "score": 0.95}
    mock_artifact.created_at = datetime.now(UTC)
    mock_artifact.metadata = {"type": "analysis_result"}
    storage.retrieve = MagicMock(return_value=mock_artifact)
    return storage


@pytest.fixture
def mock_coordinator():
    """Create a mock coordinator."""
    coordinator = MagicMock()
    coordinator.get_subagents = MagicMock(
        return_value=[
            {"task_id": "sub-1", "status": "completed", "model": "gpt-4"},
            {"task_id": "sub-2", "status": "running", "model": "gpt-4o-mini"},
        ]
    )
    return coordinator


@pytest.mark.xdist_group(name="mcp_orchestration_roundtrip")
class TestOrchestratorResourceTemplates:
    """Tests for orchestrator resource template registration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_resource_handler_creates_all_templates(self) -> None:
        """
        GIVEN create_orchestrator_resource_handler
        WHEN called
        THEN should create handler with all 3 resource templates.
        """
        from mcp_server_langgraph.mcp.resources_orchestrator import (
            create_orchestrator_resource_handler,
        )

        handler = create_orchestrator_resource_handler()
        templates = handler.list_templates()

        template_uris = [t.uriTemplate for t in templates]
        assert "orchestrator://tasks/{task_id}" in template_uris
        assert "orchestrator://artifacts/{task_id}/{artifact_name}" in template_uris
        assert "orchestrator://subagents/{task_id}" in template_uris


@pytest.mark.xdist_group(name="mcp_orchestration_roundtrip")
class TestTaskResourceProvider:
    """Tests for task resource provider."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_task_provider_returns_task_data(self, mock_orchestrator) -> None:
        """
        GIVEN a task exists in orchestrator
        WHEN task_provider is called
        THEN should return task data as JSON ResourceContent.
        """
        from mcp_server_langgraph.mcp.resources_orchestrator import task_provider

        content = await task_provider(
            uri="orchestrator://tasks/task-123",
            orchestrator=mock_orchestrator,
        )

        assert content.uri == "orchestrator://tasks/task-123"
        assert content.mimeType == "application/json"

        data = json.loads(content.text)
        assert data["task_id"] == "task-123"
        assert data["status"] == "completed"
        assert "subtasks" in data

    @pytest.mark.asyncio
    async def test_task_provider_raises_for_missing_task(self, mock_orchestrator) -> None:
        """
        GIVEN task does not exist
        WHEN task_provider is called
        THEN should raise ValueError.
        """
        from mcp_server_langgraph.mcp.resources_orchestrator import task_provider

        mock_orchestrator.get_task = MagicMock(return_value=None)

        with pytest.raises(ValueError, match="Task not found"):
            await task_provider(
                uri="orchestrator://tasks/missing-task",
                orchestrator=mock_orchestrator,
            )

    @pytest.mark.asyncio
    async def test_task_provider_requires_orchestrator(self) -> None:
        """
        GIVEN no orchestrator provided
        WHEN task_provider is called
        THEN should raise ValueError.
        """
        from mcp_server_langgraph.mcp.resources_orchestrator import task_provider

        with pytest.raises(ValueError, match="Orchestrator not provided"):
            await task_provider(
                uri="orchestrator://tasks/task-123",
                orchestrator=None,
            )


@pytest.mark.xdist_group(name="mcp_orchestration_roundtrip")
class TestArtifactResourceProvider:
    """Tests for artifact resource provider."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_artifact_provider_returns_artifact_data(self, mock_artifact_storage) -> None:
        """
        GIVEN an artifact exists in storage
        WHEN artifact_provider is called
        THEN should return artifact data as JSON ResourceContent.
        """
        from mcp_server_langgraph.mcp.resources_orchestrator import artifact_provider

        content = await artifact_provider(
            uri="orchestrator://artifacts/task-123/result",
            artifact_storage=mock_artifact_storage,
        )

        assert content.uri == "orchestrator://artifacts/task-123/result"
        assert content.mimeType == "application/json"

        data = json.loads(content.text)
        assert data["task_id"] == "task-123"
        assert data["name"] == "result"
        assert data["data"]["analysis"] == "complete"
        assert data["data"]["score"] == 0.95

    @pytest.mark.asyncio
    async def test_artifact_provider_raises_for_missing_artifact(self, mock_artifact_storage) -> None:
        """
        GIVEN artifact does not exist
        WHEN artifact_provider is called
        THEN should raise ValueError.
        """
        from mcp_server_langgraph.mcp.resources_orchestrator import artifact_provider

        mock_artifact_storage.retrieve = MagicMock(return_value=None)

        with pytest.raises(ValueError, match="Artifact not found"):
            await artifact_provider(
                uri="orchestrator://artifacts/task-123/missing",
                artifact_storage=mock_artifact_storage,
            )


@pytest.mark.xdist_group(name="mcp_orchestration_roundtrip")
class TestSubagentResourceProvider:
    """Tests for subagent status resource provider."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_subagent_provider_returns_status_list(self, mock_coordinator) -> None:
        """
        GIVEN subagents exist for a task
        WHEN subagents_provider is called
        THEN should return list of subagent statuses.
        """
        from mcp_server_langgraph.mcp.resources_orchestrator import subagents_provider

        content = await subagents_provider(
            uri="orchestrator://subagents/task-123",
            coordinator=mock_coordinator,
        )

        assert content.uri == "orchestrator://subagents/task-123"
        assert content.mimeType == "application/json"

        data = json.loads(content.text)
        assert "subagents" in data
        assert len(data["subagents"]) == 2
        assert data["subagents"][0]["status"] == "completed"
        assert data["subagents"][1]["status"] == "running"

    @pytest.mark.asyncio
    async def test_subagent_provider_returns_empty_for_unknown_task(self) -> None:
        """
        GIVEN no coordinator or unknown task
        WHEN subagents_provider is called
        THEN should return empty list.
        """
        from mcp_server_langgraph.mcp.resources_orchestrator import subagents_provider

        content = await subagents_provider(
            uri="orchestrator://subagents/unknown-task",
            coordinator=None,
        )

        data = json.loads(content.text)
        assert data["subagents"] == []


@pytest.mark.xdist_group(name="mcp_orchestration_roundtrip")
class TestOrchestrationToolHandler:
    """Tests for orchestration tool handler."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_orchestration_handler_accepts_dependencies(self) -> None:
        """
        GIVEN OrchestrationToolHandler
        WHEN initialized with dependencies
        THEN should store them correctly.
        """
        from mcp_server_langgraph.mcp.handlers.orchestration import (
            OrchestrationToolHandler,
        )

        mock_orchestrator = MagicMock()
        mock_provider = MagicMock()

        handler = OrchestrationToolHandler(
            orchestrator=mock_orchestrator,
            resource_provider=mock_provider,
        )

        assert handler.orchestrator == mock_orchestrator
        assert handler.resource_provider == mock_provider

    @pytest.mark.asyncio
    async def test_handle_status_operation(self) -> None:
        """
        GIVEN orchestration handler
        WHEN calling status operation
        THEN should return status information.
        """
        from mcp_server_langgraph.mcp.handlers.orchestration import (
            OrchestrationToolHandler,
        )

        handler = OrchestrationToolHandler()

        result = await handler.handle_operation(
            operation="status",
            arguments={"task_id": "task-123"},
        )

        # Status should work even without orchestrator (returns message)
        assert isinstance(result, dict)


@pytest.mark.xdist_group(name="mcp_orchestration_roundtrip")
class TestResourceURIParsing:
    """Tests for resource URI parsing."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_parse_task_uri(self) -> None:
        """
        GIVEN a task resource URI
        WHEN parsed
        THEN should extract task_id correctly.
        """
        from mcp_server_langgraph.mcp.resources_orchestrator import (
            parse_orchestrator_uri,
        )

        result = parse_orchestrator_uri("orchestrator://tasks/task-123")

        assert result["resource_type"] == "tasks"
        assert result["task_id"] == "task-123"
        assert result["artifact_name"] is None

    def test_parse_artifact_uri(self) -> None:
        """
        GIVEN an artifact resource URI
        WHEN parsed
        THEN should extract task_id and artifact_name correctly.
        """
        from mcp_server_langgraph.mcp.resources_orchestrator import (
            parse_orchestrator_uri,
        )

        result = parse_orchestrator_uri("orchestrator://artifacts/task-123/result")

        assert result["resource_type"] == "artifacts"
        assert result["task_id"] == "task-123"
        assert result["artifact_name"] == "result"

    def test_parse_subagent_uri(self) -> None:
        """
        GIVEN a subagent resource URI
        WHEN parsed
        THEN should extract task_id correctly.
        """
        from mcp_server_langgraph.mcp.resources_orchestrator import (
            parse_orchestrator_uri,
        )

        result = parse_orchestrator_uri("orchestrator://subagents/task-123")

        assert result["resource_type"] == "subagents"
        assert result["task_id"] == "task-123"

    def test_parse_invalid_uri_raises_error(self) -> None:
        """
        GIVEN an invalid URI
        WHEN parsed
        THEN should raise ValueError.
        """
        from mcp_server_langgraph.mcp.resources_orchestrator import (
            parse_orchestrator_uri,
        )

        with pytest.raises(ValueError, match="Invalid orchestrator URI"):
            parse_orchestrator_uri("invalid://tasks/task-123")


@pytest.mark.xdist_group(name="mcp_orchestration_roundtrip")
class TestOrchestratorResourceProviderClass:
    """Tests for OrchestratorResourceProvider class."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_provider_stores_and_retrieves_tasks(self) -> None:
        """
        GIVEN OrchestratorResourceProvider
        WHEN task is stored and read
        THEN should return task data.
        """
        from mcp_server_langgraph.mcp.resources_orchestrator import (
            OrchestratorResourceProvider,
        )

        provider = OrchestratorResourceProvider()

        # Create a mock task decomposition
        mock_decomposition = MagicMock()
        mock_decomposition.model_dump = MagicMock(
            return_value={
                "task_id": "task-456",
                "subtasks": [{"id": "sub-1", "description": "Task 1"}],
            }
        )

        provider.store_task("task-456", mock_decomposition)

        # Verify task was stored
        assert "task-456" in provider._tasks

    @pytest.mark.asyncio
    async def test_provider_read_task(self) -> None:
        """
        GIVEN a stored task
        WHEN read_task is called
        THEN should return ResourceContent with task data.
        """
        from mcp_server_langgraph.mcp.resources_orchestrator import (
            OrchestratorResourceProvider,
        )

        provider = OrchestratorResourceProvider()

        mock_decomposition = MagicMock()
        mock_decomposition.model_dump = MagicMock(return_value={"task_id": "task-789", "status": "pending"})

        provider.store_task("task-789", mock_decomposition)

        content = await provider.read_task("orchestrator://tasks/task-789")

        assert content.uri == "orchestrator://tasks/task-789"
        assert content.mimeType == "application/json"
        data = json.loads(content.text)
        assert data["task_id"] == "task-789"
