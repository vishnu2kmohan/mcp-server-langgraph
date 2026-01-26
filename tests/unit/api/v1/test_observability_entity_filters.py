"""
Observability Entity Filters Tests

TDD tests for per-entity observability filtering:
- user_id: Filter by user identity
- workflow_id: Filter by workflow
- project_id: Filter by project
- organization_id: Filter by organization (multi-tenant)

These tests are written FIRST (RED phase) before implementation.
"""

import gc
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


pytestmark = [
    pytest.mark.unit,
    pytest.mark.api,
]


@pytest.fixture
def test_app() -> FastAPI:
    """Create a test app with the observability router."""
    from mcp_server_langgraph.api.v1.observability import observability_router
    from mcp_server_langgraph.auth.dependencies import (
        get_current_user,
        require_observability_admin,
        require_observability_viewer,
    )

    app = FastAPI()
    app.include_router(observability_router, prefix="/api/v1")

    # Mock authentication for all tests
    mock_user = {
        "sub": "test-user-id",
        "user_id": "test-user-id",
        "username": "testuser",
        "roles": ["user", "observability-viewer", "observability-admin"],
        "realm_access": {"roles": ["user", "observability-viewer", "observability-admin"]},
    }
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[require_observability_viewer] = lambda: mock_user
    app.dependency_overrides[require_observability_admin] = lambda: mock_user

    return app


@pytest.fixture
def client(test_app: FastAPI) -> TestClient:
    """Create a test client."""
    return TestClient(test_app)


# ============================================================================
# Traces Entity Filtering Tests
# ============================================================================


@pytest.mark.xdist_group(name="test_observability_entity_filters")
class TestTracesUserIdFilter:
    """Tests for user_id filtering on traces endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_list_traces_filter_by_user_id(self, test_app: FastAPI) -> None:
        """
        GIVEN traces exist for a specific user
        WHEN GET request is made with user_id parameter
        THEN service should receive user_id filter
        """
        user_id = str(uuid4())
        with patch("mcp_server_langgraph.api.v1.observability.get_observability_service") as mock_get_service:
            mock_service = AsyncMock(return_value=None)  # return_value configured below
            mock_service.list_traces.return_value = (
                [{"trace_id": "abc123", "name": "User Request"}],
                None,
            )
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            response = client.get(f"/api/v1/observability/traces?user_id={user_id}")

            assert response.status_code == 200
            mock_service.list_traces.assert_called_once()
            call_kwargs = mock_service.list_traces.call_args.kwargs
            assert call_kwargs.get("user_id") == user_id

    def test_list_traces_user_id_with_session_id(self, test_app: FastAPI) -> None:
        """
        GIVEN traces exist
        WHEN GET request is made with both user_id and session_id
        THEN service should receive both filters
        """
        user_id = str(uuid4())
        session_id = str(uuid4())
        with patch("mcp_server_langgraph.api.v1.observability.get_observability_service") as mock_get_service:
            mock_service = AsyncMock(return_value=None)  # return_value configured below
            mock_service.list_traces.return_value = ([], None)
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            response = client.get(f"/api/v1/observability/traces?user_id={user_id}&session_id={session_id}")

            assert response.status_code == 200
            call_kwargs = mock_service.list_traces.call_args.kwargs
            assert call_kwargs.get("user_id") == user_id
            assert call_kwargs.get("session_id") == session_id


@pytest.mark.xdist_group(name="test_observability_entity_filters")
class TestTracesWorkflowIdFilter:
    """Tests for workflow_id filtering on traces endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_list_traces_filter_by_workflow_id(self, test_app: FastAPI) -> None:
        """
        GIVEN traces exist for a specific workflow
        WHEN GET request is made with workflow_id parameter
        THEN service should receive workflow_id filter
        """
        workflow_id = str(uuid4())
        with patch("mcp_server_langgraph.api.v1.observability.get_observability_service") as mock_get_service:
            mock_service = AsyncMock(return_value=None)  # return_value configured below
            mock_service.list_traces.return_value = (
                [{"trace_id": "def456", "name": "Workflow Execution"}],
                None,
            )
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            response = client.get(f"/api/v1/observability/traces?workflow_id={workflow_id}")

            assert response.status_code == 200
            call_kwargs = mock_service.list_traces.call_args.kwargs
            assert call_kwargs.get("workflow_id") == workflow_id


@pytest.mark.xdist_group(name="test_observability_entity_filters")
class TestTracesProjectIdFilter:
    """Tests for project_id filtering on traces endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_list_traces_filter_by_project_id(self, test_app: FastAPI) -> None:
        """
        GIVEN traces exist for a specific project
        WHEN GET request is made with project_id parameter
        THEN service should receive project_id filter
        """
        project_id = str(uuid4())
        with patch("mcp_server_langgraph.api.v1.observability.get_observability_service") as mock_get_service:
            mock_service = AsyncMock(return_value=None)  # return_value configured below
            mock_service.list_traces.return_value = ([], None)
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            response = client.get(f"/api/v1/observability/traces?project_id={project_id}")

            assert response.status_code == 200
            call_kwargs = mock_service.list_traces.call_args.kwargs
            assert call_kwargs.get("project_id") == project_id


@pytest.mark.xdist_group(name="test_observability_entity_filters")
class TestTracesOrganizationIdFilter:
    """Tests for organization_id filtering on traces endpoint (multi-tenant)."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_list_traces_filter_by_organization_id(self, test_app: FastAPI) -> None:
        """
        GIVEN traces exist for a specific organization
        WHEN GET request is made with organization_id parameter
        THEN service should receive organization_id filter
        """
        organization_id = str(uuid4())
        with patch("mcp_server_langgraph.api.v1.observability.get_observability_service") as mock_get_service:
            mock_service = AsyncMock(return_value=None)  # return_value configured below
            mock_service.list_traces.return_value = ([], None)
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            response = client.get(f"/api/v1/observability/traces?organization_id={organization_id}")

            assert response.status_code == 200
            call_kwargs = mock_service.list_traces.call_args.kwargs
            assert call_kwargs.get("organization_id") == organization_id


@pytest.mark.xdist_group(name="test_observability_entity_filters")
class TestTracesCombinedEntityFilters:
    """Tests for combining multiple entity filters."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_list_traces_all_entity_filters(self, test_app: FastAPI) -> None:
        """
        GIVEN traces exist
        WHEN GET request is made with all entity filters
        THEN service should receive all filters
        """
        user_id = str(uuid4())
        session_id = str(uuid4())
        workflow_id = str(uuid4())
        project_id = str(uuid4())
        organization_id = str(uuid4())

        with patch("mcp_server_langgraph.api.v1.observability.get_observability_service") as mock_get_service:
            mock_service = AsyncMock(return_value=None)  # return_value configured below
            mock_service.list_traces.return_value = ([], None)
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            response = client.get(
                f"/api/v1/observability/traces?"
                f"user_id={user_id}&"
                f"session_id={session_id}&"
                f"workflow_id={workflow_id}&"
                f"project_id={project_id}&"
                f"organization_id={organization_id}"
            )

            assert response.status_code == 200
            call_kwargs = mock_service.list_traces.call_args.kwargs
            assert call_kwargs.get("user_id") == user_id
            assert call_kwargs.get("session_id") == session_id
            assert call_kwargs.get("workflow_id") == workflow_id
            assert call_kwargs.get("project_id") == project_id
            assert call_kwargs.get("organization_id") == organization_id


# ============================================================================
# Logs Entity Filtering Tests
# ============================================================================


@pytest.mark.xdist_group(name="test_observability_entity_filters_logs")
class TestLogsUserIdFilter:
    """Tests for user_id filtering on logs endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_list_logs_filter_by_user_id(self, test_app: FastAPI) -> None:
        """
        GIVEN logs exist for a specific user
        WHEN GET request is made with user_id parameter
        THEN service should receive user_id filter
        """
        user_id = str(uuid4())
        with patch("mcp_server_langgraph.api.v1.observability.get_observability_service") as mock_get_service:
            mock_service = AsyncMock(return_value=None)  # return_value configured below
            mock_service.list_logs.return_value = ([], None)
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            response = client.get(f"/api/v1/observability/logs?user_id={user_id}")

            assert response.status_code == 200
            call_kwargs = mock_service.list_logs.call_args.kwargs
            assert call_kwargs.get("user_id") == user_id


@pytest.mark.xdist_group(name="test_observability_entity_filters_logs")
class TestLogsWorkflowIdFilter:
    """Tests for workflow_id filtering on logs endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_list_logs_filter_by_workflow_id(self, test_app: FastAPI) -> None:
        """
        GIVEN logs exist for a specific workflow
        WHEN GET request is made with workflow_id parameter
        THEN service should receive workflow_id filter
        """
        workflow_id = str(uuid4())
        with patch("mcp_server_langgraph.api.v1.observability.get_observability_service") as mock_get_service:
            mock_service = AsyncMock(return_value=None)  # return_value configured below
            mock_service.list_logs.return_value = ([], None)
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            response = client.get(f"/api/v1/observability/logs?workflow_id={workflow_id}")

            assert response.status_code == 200
            call_kwargs = mock_service.list_logs.call_args.kwargs
            assert call_kwargs.get("workflow_id") == workflow_id


@pytest.mark.xdist_group(name="test_observability_entity_filters_logs")
class TestLogsProjectIdFilter:
    """Tests for project_id filtering on logs endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_list_logs_filter_by_project_id(self, test_app: FastAPI) -> None:
        """
        GIVEN logs exist for a specific project
        WHEN GET request is made with project_id parameter
        THEN service should receive project_id filter
        """
        project_id = str(uuid4())
        with patch("mcp_server_langgraph.api.v1.observability.get_observability_service") as mock_get_service:
            mock_service = AsyncMock(return_value=None)  # return_value configured below
            mock_service.list_logs.return_value = ([], None)
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            response = client.get(f"/api/v1/observability/logs?project_id={project_id}")

            assert response.status_code == 200
            call_kwargs = mock_service.list_logs.call_args.kwargs
            assert call_kwargs.get("project_id") == project_id


# ============================================================================
# Metrics By Session/Workflow Endpoints Tests
# ============================================================================


@pytest.mark.xdist_group(name="test_observability_metrics_by_entity")
class TestMetricsBySession:
    """Tests for GET /api/v1/observability/metrics/by-session/{session_id}."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_get_metrics_by_session_returns_200(self, test_app: FastAPI) -> None:
        """
        GIVEN a session with traces exists
        WHEN GET request is made to /metrics/by-session/{session_id}
        THEN response should be 200 OK with aggregated metrics
        """
        session_id = str(uuid4())
        with patch("mcp_server_langgraph.api.v1.observability.get_observability_service") as mock_get_service:
            mock_service = AsyncMock(return_value=None)  # return_value configured below
            mock_service.get_metrics_by_session.return_value = {
                "total_requests": 10,
                "total_errors": 1,
                "avg_latency_ms": 150.5,
                "p95_latency_ms": 450.0,
            }
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            response = client.get(f"/api/v1/observability/metrics/by-session/{session_id}")

            assert response.status_code == 200
            data = response.json()
            assert "total_requests" in data
            assert "total_errors" in data
            assert "avg_latency_ms" in data

    def test_get_metrics_by_session_empty(self, test_app: FastAPI) -> None:
        """
        GIVEN a session with no traces
        WHEN GET request is made
        THEN response should be 200 OK with zero metrics
        """
        session_id = str(uuid4())
        with patch("mcp_server_langgraph.api.v1.observability.get_observability_service") as mock_get_service:
            mock_service = AsyncMock(return_value=None)  # return_value configured below
            mock_service.get_metrics_by_session.return_value = {
                "total_requests": 0,
                "total_errors": 0,
                "avg_latency_ms": 0.0,
                "p95_latency_ms": 0.0,
            }
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            response = client.get(f"/api/v1/observability/metrics/by-session/{session_id}")

            assert response.status_code == 200
            data = response.json()
            assert data["total_requests"] == 0


@pytest.mark.xdist_group(name="test_observability_metrics_by_entity")
class TestMetricsByWorkflow:
    """Tests for GET /api/v1/observability/metrics/by-workflow/{workflow_id}."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_get_metrics_by_workflow_returns_200(self, test_app: FastAPI) -> None:
        """
        GIVEN a workflow with executions exists
        WHEN GET request is made to /metrics/by-workflow/{workflow_id}
        THEN response should be 200 OK with aggregated metrics
        """
        workflow_id = str(uuid4())
        with patch("mcp_server_langgraph.api.v1.observability.get_observability_service") as mock_get_service:
            mock_service = AsyncMock(return_value=None)  # return_value configured below
            mock_service.get_metrics_by_workflow.return_value = {
                "total_executions": 50,
                "total_errors": 5,
                "avg_latency_ms": 200.0,
                "p95_latency_ms": 800.0,
            }
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            response = client.get(f"/api/v1/observability/metrics/by-workflow/{workflow_id}")

            assert response.status_code == 200
            data = response.json()
            assert "total_executions" in data
            assert "total_errors" in data


@pytest.mark.xdist_group(name="test_observability_metrics_by_entity")
class TestMetricsByUser:
    """Tests for GET /api/v1/observability/metrics/by-user/{user_id}."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_get_metrics_by_user_returns_200(self, test_app: FastAPI) -> None:
        """
        GIVEN a user with activity exists
        WHEN GET request is made to /metrics/by-user/{user_id}
        THEN response should be 200 OK with aggregated metrics
        """
        user_id = str(uuid4())
        with patch("mcp_server_langgraph.api.v1.observability.get_observability_service") as mock_get_service:
            mock_service = AsyncMock(return_value=None)  # return_value configured below
            mock_service.get_metrics_by_user.return_value = {
                "total_requests": 100,
                "total_sessions": 5,
                "total_errors": 2,
                "avg_latency_ms": 120.0,
            }
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            response = client.get(f"/api/v1/observability/metrics/by-user/{user_id}")

            assert response.status_code == 200
            data = response.json()
            assert "total_requests" in data
            assert "total_sessions" in data


# ============================================================================
# Alerts Entity Filtering Tests
# ============================================================================


@pytest.mark.xdist_group(name="test_observability_entity_filters_alerts")
class TestAlertsWorkflowIdFilter:
    """Tests for workflow_id filtering on alerts endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_list_alerts_filter_by_workflow_id(self, test_app: FastAPI) -> None:
        """
        GIVEN alerts exist for a specific workflow
        WHEN GET request is made with workflow_id parameter
        THEN service should receive workflow_id filter
        """
        workflow_id = str(uuid4())
        with patch("mcp_server_langgraph.api.v1.observability.get_observability_service") as mock_get_service:
            mock_service = AsyncMock(return_value=None)  # return_value configured below
            mock_service.list_alerts.return_value = ([], None)
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            response = client.get(f"/api/v1/observability/alerts?workflow_id={workflow_id}")

            assert response.status_code == 200
            call_kwargs = mock_service.list_alerts.call_args.kwargs
            assert call_kwargs.get("workflow_id") == workflow_id


@pytest.mark.xdist_group(name="test_observability_entity_filters_alerts")
class TestAlertsProjectIdFilter:
    """Tests for project_id filtering on alerts endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_list_alerts_filter_by_project_id(self, test_app: FastAPI) -> None:
        """
        GIVEN alerts exist for a specific project
        WHEN GET request is made with project_id parameter
        THEN service should receive project_id filter
        """
        project_id = str(uuid4())
        with patch("mcp_server_langgraph.api.v1.observability.get_observability_service") as mock_get_service:
            mock_service = AsyncMock(return_value=None)  # return_value configured below
            mock_service.list_alerts.return_value = ([], None)
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            response = client.get(f"/api/v1/observability/alerts?project_id={project_id}")

            assert response.status_code == 200
            call_kwargs = mock_service.list_alerts.call_args.kwargs
            assert call_kwargs.get("project_id") == project_id
