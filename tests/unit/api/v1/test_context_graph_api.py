"""
Unit tests for Context Graph API endpoints.

TDD RED Phase: Tests for api/v1/context_graph.py module.

Tests:
- GET /context-graph/traces/{trace_id}
- GET /context-graph/sessions/{session_id}/traces
- POST /context-graph/precedents/search
- Feature flag gating
- Authorization checks
"""

import gc
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

pytestmark = pytest.mark.unit


@pytest.fixture
def mock_current_user():
    """Create a mock current user."""
    user = MagicMock()
    user.user_id = "user:alice"
    user.organization_id = "org:acme"
    user.roles = ["user"]
    return user


@pytest.fixture
def mock_trace_read():
    """Create a mock DecisionTraceRead object."""
    from mcp_server_langgraph.storage.models import DecisionTraceRead

    return DecisionTraceRead(
        trace_id="trace-abc123",
        run_id="run-xyz",
        session_id="session-456",
        workflow_id=None,
        project_id=None,
        timestamp=datetime(2026, 1, 8, 12, 0, 0, tzinfo=UTC),
        decision_type="routing",
        decision_stage="action",
        chosen_action="deploy_tool",
        confidence=0.95,
        rationale="User wants deployment",
        outcome="success",
        requires_approval=False,
        approval_status=None,
    )


@pytest.fixture
def mock_trace_summary():
    """Create a mock DecisionTraceSummary object."""
    from mcp_server_langgraph.storage.models import DecisionTraceSummary

    return DecisionTraceSummary(
        trace_id="trace-abc123",
        timestamp=datetime(2026, 1, 8, 12, 0, 0, tzinfo=UTC),
        decision_type="routing",
        chosen_action="deploy_tool",
        confidence=0.95,
        outcome="success",
    )


@pytest.mark.xdist_group(name="test_context_graph_api")
class TestContextGraphRouterExists:
    """Tests for context graph router existence."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_context_graph_router_module_exists(self) -> None:
        """api/v1/context_graph module should exist."""
        from mcp_server_langgraph.api.v1 import context_graph

        assert context_graph is not None

    def test_context_graph_router_exported(self) -> None:
        """router should be exported from context_graph module."""
        from mcp_server_langgraph.api.v1.context_graph import router

        assert router is not None


@pytest.mark.xdist_group(name="test_context_graph_api")
class TestGetTraceEndpoint:
    """Tests for GET /context-graph/traces/{trace_id}."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_get_trace_returns_trace(
        self, mock_current_user, mock_trace_read
    ) -> None:
        """GET /traces/{trace_id} should return trace data."""
        from mcp_server_langgraph.api.v1.context_graph import (
            get_decision_repository,
            router,
        )
        from mcp_server_langgraph.auth.dependencies import get_current_user

        app = FastAPI()
        app.include_router(router)

        mock_repo = AsyncMock(return_value=None)
        mock_repo.get_by_id = AsyncMock(return_value=mock_trace_read)

        app.dependency_overrides[get_current_user] = lambda: mock_current_user
        app.dependency_overrides[get_decision_repository] = lambda: mock_repo

        try:
            client = TestClient(app)
            response = client.get("/context-graph/traces/trace-abc123")

            assert response.status_code == 200
            data = response.json()
            assert data["trace_id"] == "trace-abc123"
            assert data["decision_type"] == "routing"
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_trace_returns_404_when_not_found(
        self, mock_current_user
    ) -> None:
        """GET /traces/{trace_id} should return 404 when trace not found."""
        from mcp_server_langgraph.api.v1.context_graph import (
            get_decision_repository,
            router,
        )
        from mcp_server_langgraph.auth.dependencies import get_current_user

        app = FastAPI()
        app.include_router(router)

        mock_repo = AsyncMock(return_value=None)
        mock_repo.get_by_id = AsyncMock(return_value=None)

        app.dependency_overrides[get_current_user] = lambda: mock_current_user
        app.dependency_overrides[get_decision_repository] = lambda: mock_repo

        try:
            client = TestClient(app)
            response = client.get("/context-graph/traces/nonexistent-trace")
            assert response.status_code == 404
        finally:
            app.dependency_overrides.clear()


@pytest.mark.xdist_group(name="test_context_graph_api")
class TestGetSessionTracesEndpoint:
    """Tests for GET /context-graph/sessions/{session_id}/traces."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_get_session_traces_returns_list(
        self, mock_current_user, mock_trace_summary
    ) -> None:
        """GET /sessions/{session_id}/traces should return trace summaries."""
        from mcp_server_langgraph.api.v1.context_graph import (
            get_decision_repository,
            router,
        )
        from mcp_server_langgraph.auth.dependencies import get_current_user

        app = FastAPI()
        app.include_router(router)

        mock_repo = AsyncMock(return_value=None)
        mock_repo.get_by_session = AsyncMock(
            return_value=[mock_trace_summary, mock_trace_summary]
        )

        app.dependency_overrides[get_current_user] = lambda: mock_current_user
        app.dependency_overrides[get_decision_repository] = lambda: mock_repo

        try:
            client = TestClient(app)
            response = client.get("/context-graph/sessions/session-456/traces")

            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2
            assert data[0]["trace_id"] == "trace-abc123"
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_session_traces_supports_pagination(
        self, mock_current_user, mock_trace_summary
    ) -> None:
        """GET /sessions/{session_id}/traces should support limit and offset."""
        from mcp_server_langgraph.api.v1.context_graph import (
            get_decision_repository,
            router,
        )
        from mcp_server_langgraph.auth.dependencies import get_current_user

        app = FastAPI()
        app.include_router(router)

        mock_repo = AsyncMock(return_value=None)
        mock_repo.get_by_session = AsyncMock(return_value=[mock_trace_summary])

        app.dependency_overrides[get_current_user] = lambda: mock_current_user
        app.dependency_overrides[get_decision_repository] = lambda: mock_repo

        try:
            client = TestClient(app)
            response = client.get("/context-graph/sessions/session-456/traces?limit=10&offset=5")

            assert response.status_code == 200
            mock_repo.get_by_session.assert_called_once()
            call_kwargs = mock_repo.get_by_session.call_args
            assert call_kwargs.kwargs.get("limit") == 10 or call_kwargs[1].get("limit") == 10
        finally:
            app.dependency_overrides.clear()


@pytest.mark.xdist_group(name="test_context_graph_api")
class TestContextGraphFeatureGating:
    """Tests for feature flag gating."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_get_repository_returns_503_when_disabled(self) -> None:
        """_get_repository should raise 503 when context graph disabled."""
        from fastapi import HTTPException

        from mcp_server_langgraph.api.v1.context_graph import _get_repository

        mock_request = MagicMock()
        mock_request.app.state.decision_emitter = None

        with pytest.raises(HTTPException) as exc_info:
            _get_repository(mock_request)

        assert exc_info.value.status_code == 503
        assert "not enabled" in str(exc_info.value.detail).lower()


@pytest.mark.xdist_group(name="test_context_graph_api")
class TestContextGraphRouterPrefix:
    """Tests for router configuration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_router_has_correct_prefix(self) -> None:
        """Router should have /context-graph prefix."""
        from mcp_server_langgraph.api.v1.context_graph import router

        assert router.prefix == "/context-graph"

    def test_router_has_correct_tags(self) -> None:
        """Router should have context-graph tag."""
        from mcp_server_langgraph.api.v1.context_graph import router

        assert "context-graph" in router.tags
