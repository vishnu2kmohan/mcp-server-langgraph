"""
Tests for Workflow Executions Router

TDD tests for /api/v1/workflows/{id}/executions endpoints.
Provides access to workflow execution history.
"""

import gc
from datetime import datetime, UTC
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

pytestmark = pytest.mark.unit


# Mock execution data
MOCK_EXECUTIONS = [
    {
        "id": "exec-1",
        "workflow_id": "wf-1",
        "status": "completed",
        "started_at": datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC).isoformat(),
        "completed_at": datetime(2025, 1, 1, 12, 5, 0, tzinfo=UTC).isoformat(),
        "input_data": {"query": "hello"},
        "output_data": {"response": "world"},
    },
    {
        "id": "exec-2",
        "workflow_id": "wf-1",
        "status": "running",
        "started_at": datetime(2025, 1, 2, 10, 0, 0, tzinfo=UTC).isoformat(),
        "completed_at": None,
        "input_data": {"query": "test"},
        "output_data": None,
    },
    {
        "id": "exec-3",
        "workflow_id": "wf-1",
        "status": "failed",
        "started_at": datetime(2025, 1, 3, 8, 0, 0, tzinfo=UTC).isoformat(),
        "completed_at": datetime(2025, 1, 3, 8, 1, 0, tzinfo=UTC).isoformat(),
        "input_data": {"query": "bad"},
        "output_data": None,
        "error": "Something went wrong",
    },
]


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_workflow_executions_router")
class TestWorkflowExecutionsListEndpoint:
    """Tests for GET /api/v1/workflows/{id}/executions endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def _create_mock_execution_manager(
        self,
        executions: list[dict] | None = None,
        workflow_exists: bool = True,
    ) -> AsyncMock:
        """Create a mock execution manager."""
        mock_manager = AsyncMock()  # async-mock-configured  # noqa: async-mock-config
        mock_manager.get_workflow.return_value = {"id": "wf-1", "name": "Test"} if workflow_exists else None
        mock_manager.list_executions.return_value = executions or []
        return mock_manager

    def _create_app(self, mock_manager: AsyncMock | None = None) -> FastAPI:
        """Create a FastAPI app with the workflow executions router."""
        from mcp_server_langgraph.api.v1.workflow_executions import (
            workflow_executions_router,
            get_execution_history_manager,
        )

        app = FastAPI()
        app.include_router(workflow_executions_router, prefix="/api/v1")

        if mock_manager:
            app.dependency_overrides[get_execution_history_manager] = lambda: mock_manager

        return app

    def _create_client(self, mock_manager: AsyncMock | None = None) -> TestClient:
        """Create a test client for the workflow executions API."""
        return TestClient(self._create_app(mock_manager))

    @pytest.mark.asyncio
    async def test_list_executions_returns_200(self) -> None:
        """GET /api/v1/workflows/{id}/executions should return 200."""
        mock_manager = self._create_mock_execution_manager(MOCK_EXECUTIONS)
        client = self._create_client(mock_manager)
        response = client.get("/api/v1/workflows/wf-1/executions")

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    @pytest.mark.asyncio
    async def test_list_executions_returns_all_executions(self) -> None:
        """GET /api/v1/workflows/{id}/executions should return all executions."""
        mock_manager = self._create_mock_execution_manager(MOCK_EXECUTIONS)
        client = self._create_client(mock_manager)
        response = client.get("/api/v1/workflows/wf-1/executions")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 3
        assert data["total"] == 3
        assert data["items"][0]["id"] == "exec-1"
        assert data["items"][0]["status"] == "completed"

    @pytest.mark.asyncio
    async def test_list_executions_returns_404_for_nonexistent_workflow(self) -> None:
        """GET /api/v1/workflows/{id}/executions should return 404 for nonexistent workflow."""
        mock_manager = self._create_mock_execution_manager(workflow_exists=False)
        client = self._create_client(mock_manager)
        response = client.get("/api/v1/workflows/nonexistent/executions")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_list_executions_with_status_filter(self) -> None:
        """GET /api/v1/workflows/{id}/executions?status=completed should filter by status."""
        completed_only = [e for e in MOCK_EXECUTIONS if e["status"] == "completed"]
        mock_manager = self._create_mock_execution_manager(completed_only)
        client = self._create_client(mock_manager)
        response = client.get("/api/v1/workflows/wf-1/executions?status=completed")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["status"] == "completed"

    @pytest.mark.asyncio
    async def test_list_executions_with_pagination(self) -> None:
        """GET /api/v1/workflows/{id}/executions should support pagination."""
        mock_manager = self._create_mock_execution_manager([MOCK_EXECUTIONS[0]])
        client = self._create_client(mock_manager)
        response = client.get("/api/v1/workflows/wf-1/executions?limit=1")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_workflow_executions_router")
class TestWorkflowExecutionGetEndpoint:
    """Tests for GET /api/v1/workflows/{id}/executions/{execution_id} endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def _create_mock_execution_manager(
        self,
        execution: dict | None = None,
        workflow_exists: bool = True,
    ) -> AsyncMock:
        """Create a mock execution manager."""
        mock_manager = AsyncMock()  # async-mock-configured  # noqa: async-mock-config
        mock_manager.get_workflow.return_value = {"id": "wf-1", "name": "Test"} if workflow_exists else None
        mock_manager.get_execution.return_value = execution
        return mock_manager

    def _create_app(self, mock_manager: AsyncMock | None = None) -> FastAPI:
        """Create a FastAPI app with the workflow executions router."""
        from mcp_server_langgraph.api.v1.workflow_executions import (
            workflow_executions_router,
            get_execution_history_manager,
        )

        app = FastAPI()
        app.include_router(workflow_executions_router, prefix="/api/v1")

        if mock_manager:
            app.dependency_overrides[get_execution_history_manager] = lambda: mock_manager

        return app

    def _create_client(self, mock_manager: AsyncMock | None = None) -> TestClient:
        """Create a test client for the workflow executions API."""
        return TestClient(self._create_app(mock_manager))

    @pytest.mark.asyncio
    async def test_get_execution_returns_200(self) -> None:
        """GET /api/v1/workflows/{id}/executions/{execution_id} should return 200."""
        mock_manager = self._create_mock_execution_manager(MOCK_EXECUTIONS[0])
        client = self._create_client(mock_manager)
        response = client.get("/api/v1/workflows/wf-1/executions/exec-1")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "exec-1"
        assert data["status"] == "completed"

    @pytest.mark.asyncio
    async def test_get_execution_returns_404_for_nonexistent(self) -> None:
        """GET /api/v1/workflows/{id}/executions/{execution_id} should return 404 for nonexistent."""
        mock_manager = self._create_mock_execution_manager(None)
        client = self._create_client(mock_manager)
        response = client.get("/api/v1/workflows/wf-1/executions/nonexistent")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_execution_returns_404_for_nonexistent_workflow(self) -> None:
        """GET /api/v1/workflows/{id}/executions/{execution_id} should return 404 for nonexistent workflow."""
        mock_manager = self._create_mock_execution_manager(MOCK_EXECUTIONS[0], workflow_exists=False)
        client = self._create_client(mock_manager)
        response = client.get("/api/v1/workflows/nonexistent/executions/exec-1")

        assert response.status_code == 404
