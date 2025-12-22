"""
Tests for MCP Orchestrator Resources.

Tests for exposing multi-agent orchestration as MCP resources:
- orchestrator://tasks/{task_id}
- orchestrator://artifacts/{task_id}/{name}
- orchestrator://subagents/{task_id}

TDD: These tests are written FIRST before implementation.
"""

from __future__ import annotations

import gc
import json
from unittest.mock import AsyncMock, MagicMock

import pytest

pytestmark = [
    pytest.mark.unit,
    pytest.mark.mcp,
    pytest.mark.orchestrator,
]


@pytest.mark.xdist_group(name="orchestrator_resources")
class TestOrchestratorResourceHandlerExists:
    """Tests for orchestrator resource handler existence."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_create_orchestrator_resource_handler_exists(self) -> None:
        """
        GIVEN the resources_orchestrator module
        WHEN importing create_orchestrator_resource_handler
        THEN should be available.
        """
        from mcp_server_langgraph.mcp.resources_orchestrator import (
            create_orchestrator_resource_handler,
        )

        assert create_orchestrator_resource_handler is not None

    def test_creates_resource_handler(self) -> None:
        """
        GIVEN create_orchestrator_resource_handler
        WHEN called
        THEN should return a ResourceHandler.
        """
        from mcp_server_langgraph.mcp.resources import ResourceHandler
        from mcp_server_langgraph.mcp.resources_orchestrator import (
            create_orchestrator_resource_handler,
        )

        handler = create_orchestrator_resource_handler()
        assert isinstance(handler, ResourceHandler)


@pytest.mark.xdist_group(name="orchestrator_resources")
class TestOrchestratorResourceTemplates:
    """Tests for orchestrator resource templates."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_has_task_template(self) -> None:
        """
        GIVEN orchestrator resource handler
        WHEN listing templates
        THEN should have task template.
        """
        from mcp_server_langgraph.mcp.resources_orchestrator import (
            create_orchestrator_resource_handler,
        )

        handler = create_orchestrator_resource_handler()
        templates = handler.list_templates()

        template_uris = [t.uriTemplate for t in templates]
        assert "orchestrator://tasks/{task_id}" in template_uris

    def test_has_artifact_template(self) -> None:
        """
        GIVEN orchestrator resource handler
        WHEN listing templates
        THEN should have artifact template.
        """
        from mcp_server_langgraph.mcp.resources_orchestrator import (
            create_orchestrator_resource_handler,
        )

        handler = create_orchestrator_resource_handler()
        templates = handler.list_templates()

        template_uris = [t.uriTemplate for t in templates]
        assert "orchestrator://artifacts/{task_id}/{artifact_name}" in template_uris

    def test_has_subagents_template(self) -> None:
        """
        GIVEN orchestrator resource handler
        WHEN listing templates
        THEN should have subagents template.
        """
        from mcp_server_langgraph.mcp.resources_orchestrator import (
            create_orchestrator_resource_handler,
        )

        handler = create_orchestrator_resource_handler()
        templates = handler.list_templates()

        template_uris = [t.uriTemplate for t in templates]
        assert "orchestrator://subagents/{task_id}" in template_uris


@pytest.mark.xdist_group(name="orchestrator_resources")
class TestTaskResourceProvider:
    """Tests for task resource provider."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_task_provider_exists(self) -> None:
        """
        GIVEN the resources_orchestrator module
        WHEN importing task_provider
        THEN should be available.
        """
        from mcp_server_langgraph.mcp.resources_orchestrator import task_provider

        assert task_provider is not None

    @pytest.mark.asyncio
    async def test_task_provider_returns_task_data(self) -> None:
        """
        GIVEN a task exists in orchestrator
        WHEN task_provider is called
        THEN should return task data as JSON.
        """
        from mcp_server_langgraph.mcp.resources_orchestrator import task_provider

        # Mock orchestrator with task data
        mock_orchestrator = MagicMock()
        mock_orchestrator.get_task = MagicMock(
            return_value={
                "task_id": "task-123",
                "status": "completed",
                "subtasks": ["sub-1", "sub-2"],
            }
        )

        content = await task_provider(
            uri="orchestrator://tasks/task-123",
            orchestrator=mock_orchestrator,
        )

        assert content.uri == "orchestrator://tasks/task-123"
        assert content.mimeType == "application/json"

        # Parse JSON content
        data = json.loads(content.text)
        assert data["task_id"] == "task-123"
        assert data["status"] == "completed"

    @pytest.mark.asyncio
    async def test_task_provider_raises_for_missing_task(self) -> None:
        """
        GIVEN a task does not exist
        WHEN task_provider is called
        THEN should raise ValueError.
        """
        from mcp_server_langgraph.mcp.resources_orchestrator import task_provider

        mock_orchestrator = MagicMock()
        mock_orchestrator.get_task = MagicMock(return_value=None)

        with pytest.raises(ValueError, match="Task not found"):
            await task_provider(
                uri="orchestrator://tasks/missing-task",
                orchestrator=mock_orchestrator,
            )


@pytest.mark.xdist_group(name="orchestrator_resources")
class TestArtifactResourceProvider:
    """Tests for artifact resource provider."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_artifact_provider_exists(self) -> None:
        """
        GIVEN the resources_orchestrator module
        WHEN importing artifact_provider
        THEN should be available.
        """
        from mcp_server_langgraph.mcp.resources_orchestrator import artifact_provider

        assert artifact_provider is not None

    @pytest.mark.asyncio
    async def test_artifact_provider_returns_artifact_data(self) -> None:
        """
        GIVEN an artifact exists in storage
        WHEN artifact_provider is called
        THEN should return artifact data as JSON.
        """
        from datetime import UTC, datetime

        from mcp_server_langgraph.mcp.resources_orchestrator import artifact_provider

        # Mock artifact storage
        mock_storage = MagicMock()
        mock_artifact = MagicMock()
        mock_artifact.task_id = "task-123"
        mock_artifact.name = "result"
        mock_artifact.data = {"key": "value"}
        mock_artifact.created_at = datetime.now(UTC)
        mock_artifact.metadata = {}
        mock_storage.retrieve = MagicMock(return_value=mock_artifact)

        content = await artifact_provider(
            uri="orchestrator://artifacts/task-123/result",
            artifact_storage=mock_storage,
        )

        assert content.uri == "orchestrator://artifacts/task-123/result"
        assert content.mimeType == "application/json"

        data = json.loads(content.text)
        assert data["task_id"] == "task-123"
        assert data["name"] == "result"
        assert data["data"]["key"] == "value"

    @pytest.mark.asyncio
    async def test_artifact_provider_raises_for_missing_artifact(self) -> None:
        """
        GIVEN an artifact does not exist
        WHEN artifact_provider is called
        THEN should raise ValueError.
        """
        from mcp_server_langgraph.mcp.resources_orchestrator import artifact_provider

        mock_storage = MagicMock()
        mock_storage.retrieve = MagicMock(return_value=None)

        with pytest.raises(ValueError, match="Artifact not found"):
            await artifact_provider(
                uri="orchestrator://artifacts/task-123/missing",
                artifact_storage=mock_storage,
            )


@pytest.mark.xdist_group(name="orchestrator_resources")
class TestSubagentsResourceProvider:
    """Tests for subagents resource provider."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_subagents_provider_exists(self) -> None:
        """
        GIVEN the resources_orchestrator module
        WHEN importing subagents_provider
        THEN should be available.
        """
        from mcp_server_langgraph.mcp.resources_orchestrator import subagents_provider

        assert subagents_provider is not None

    @pytest.mark.asyncio
    async def test_subagents_provider_returns_subagent_statuses(self) -> None:
        """
        GIVEN subagents exist for a task
        WHEN subagents_provider is called
        THEN should return list of subagent statuses.
        """
        from mcp_server_langgraph.mcp.resources_orchestrator import subagents_provider

        # Mock coordinator
        mock_coordinator = MagicMock()
        mock_coordinator.get_subagents = MagicMock(
            return_value=[
                {"task_id": "sub-1", "status": "completed", "model": "gpt-4"},
                {"task_id": "sub-2", "status": "running", "model": "gpt-4o-mini"},
            ]
        )

        content = await subagents_provider(
            uri="orchestrator://subagents/task-123",
            coordinator=mock_coordinator,
        )

        assert content.uri == "orchestrator://subagents/task-123"
        assert content.mimeType == "application/json"

        data = json.loads(content.text)
        assert len(data["subagents"]) == 2
        assert data["subagents"][0]["status"] == "completed"
