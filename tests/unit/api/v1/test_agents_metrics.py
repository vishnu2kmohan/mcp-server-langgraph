"""
Unit tests for Agents Metrics API endpoint.

TDD tests for the /api/v1/agents/metrics endpoint that exposes
agent orchestration metrics from the OTEL/Prometheus backend.

Tests cover:
- Orchestrator execution metrics (count, duration, success rate)
- Subagent execution metrics
- HITL metrics (requests, decisions, response latency)
- Cost tracking metrics
- Model selection metrics
- Error handling when metrics backend unavailable
"""

import gc
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI

pytestmark = [pytest.mark.unit, pytest.mark.api]


def create_agents_test_app() -> FastAPI:
    """Create a FastAPI app with the agents router and auth mocking."""
    from mcp_server_langgraph.api.v1.agents import agents_router
    from mcp_server_langgraph.auth.dependencies import get_current_user

    app = FastAPI()
    app.include_router(agents_router, prefix="/api/v1")

    # Mock authentication
    mock_user = {
        "sub": "test-user-id",
        "user_id": "test-user-id",
        "username": "testuser",
        "email": "testuser@example.com",
        "roles": ["user"],
        "realm_access": {"roles": ["user"]},
    }

    async def _override_current_user():
        return mock_user

    app.dependency_overrides[get_current_user] = _override_current_user

    return app


# =============================================================================
# Response Model Tests
# =============================================================================


@pytest.mark.xdist_group(name="agents_metrics_models")
class TestAgentMetricsModels:
    """Test response models for agents metrics endpoint."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_orchestrator_metrics_model_exists(self) -> None:
        """Test that OrchestratorMetrics model exists."""
        from mcp_server_langgraph.api.v1.agents import OrchestratorMetrics

        assert OrchestratorMetrics is not None

    def test_orchestrator_metrics_has_required_fields(self) -> None:
        """Test OrchestratorMetrics has required fields."""
        from mcp_server_langgraph.api.v1.agents import OrchestratorMetrics

        metrics = OrchestratorMetrics(
            total_executions=100,
            successful_executions=95,
            failed_executions=5,
            avg_duration_ms=1500.0,
            p50_duration_ms=1200.0,
            p95_duration_ms=2500.0,
            p99_duration_ms=3000.0,
        )

        assert metrics.total_executions == 100
        assert metrics.successful_executions == 95
        assert metrics.failed_executions == 5
        assert metrics.avg_duration_ms == 1500.0

    def test_hitl_metrics_model_exists(self) -> None:
        """Test that HITLMetrics model exists."""
        from mcp_server_langgraph.api.v1.agents import HITLMetrics

        assert HITLMetrics is not None

    def test_hitl_metrics_has_required_fields(self) -> None:
        """Test HITLMetrics has required fields."""
        from mcp_server_langgraph.api.v1.agents import HITLMetrics

        metrics = HITLMetrics(
            total_requests=50,
            approved_count=40,
            rejected_count=8,
            pending_count=2,
            avg_response_latency_ms=5000.0,
        )

        assert metrics.total_requests == 50
        assert metrics.approved_count == 40
        assert metrics.pending_count == 2

    def test_cost_metrics_model_exists(self) -> None:
        """Test that CostMetrics model exists."""
        from mcp_server_langgraph.api.v1.agents import CostMetrics

        assert CostMetrics is not None

    def test_cost_metrics_has_required_fields(self) -> None:
        """Test CostMetrics has required fields."""
        from mcp_server_langgraph.api.v1.agents import CostMetrics

        metrics = CostMetrics(
            total_cost_usd=10.50,
            total_tokens=150000,
            avg_cost_per_request_usd=0.021,
        )

        assert metrics.total_cost_usd == 10.50
        assert metrics.total_tokens == 150000

    def test_agent_metrics_response_model_exists(self) -> None:
        """Test that AgentMetricsResponse model exists."""
        from mcp_server_langgraph.api.v1.agents import AgentMetricsResponse

        assert AgentMetricsResponse is not None

    def test_agent_metrics_response_has_all_sections(self) -> None:
        """Test AgentMetricsResponse contains all metric sections."""
        from mcp_server_langgraph.api.v1.agents import (
            AgentMetricsResponse,
            CostMetrics,
            HITLMetrics,
            OrchestratorMetrics,
        )

        response = AgentMetricsResponse(
            timestamp=datetime.now(UTC).isoformat(),
            time_range_hours=24,
            orchestrator=OrchestratorMetrics(
                total_executions=100,
                successful_executions=95,
                failed_executions=5,
                avg_duration_ms=1500.0,
            ),
            hitl=HITLMetrics(
                total_requests=50,
                approved_count=40,
                rejected_count=8,
                pending_count=2,
                avg_response_latency_ms=5000.0,
            ),
            cost=CostMetrics(
                total_cost_usd=10.50,
                total_tokens=150000,
                avg_cost_per_request_usd=0.021,
            ),
        )

        assert response.orchestrator is not None
        assert response.hitl is not None
        assert response.cost is not None
        assert response.time_range_hours == 24


# =============================================================================
# Endpoint Tests
# =============================================================================


@pytest.mark.xdist_group(name="agents_metrics_endpoint")
class TestAgentMetricsEndpoint:
    """Test /api/v1/agents/metrics endpoint."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_endpoint_registered_on_router(self) -> None:
        """Test that metrics endpoint is registered on agents_router."""
        from mcp_server_langgraph.api.v1.agents import agents_router

        routes = [r.path for r in agents_router.routes]
        assert "/metrics" in routes or "metrics" in str(routes)

    @pytest.mark.asyncio
    async def test_get_metrics_returns_success(self) -> None:
        """Test GET /api/v1/agents/metrics returns 200."""
        from fastapi.testclient import TestClient

        app = create_agents_test_app()

        with patch("mcp_server_langgraph.api.v1.agents._get_metrics_client") as mock_get_client:
            mock_client = AsyncMock(return_value=None)  # noqa: async-mock-config - configured below
            mock_client.query_instant = AsyncMock(
                return_value=MagicMock(
                    data=[MagicMock(value=100.0)],
                    result_type="vector",
                )
            )
            mock_get_client.return_value = mock_client

            client = TestClient(app)
            response = client.get("/api/v1/agents/metrics")

            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_metrics_returns_structured_response(self) -> None:
        """Test GET /api/v1/agents/metrics returns structured JSON."""
        from fastapi.testclient import TestClient

        app = create_agents_test_app()

        with patch("mcp_server_langgraph.api.v1.agents._get_metrics_client") as mock_get_client:
            mock_client = AsyncMock(return_value=None)  # noqa: async-mock-config - configured below
            mock_client.query_instant = AsyncMock(
                return_value=MagicMock(
                    data=[MagicMock(value=100.0)],
                    result_type="vector",
                )
            )
            mock_get_client.return_value = mock_client

            client = TestClient(app)
            response = client.get("/api/v1/agents/metrics")

            data = response.json()
            assert "timestamp" in data
            assert "orchestrator" in data
            assert "hitl" in data
            assert "cost" in data

    def test_metrics_endpoint_accepts_time_range_param(self) -> None:
        """Test metrics endpoint accepts time_range_hours parameter."""
        from fastapi.testclient import TestClient

        app = create_agents_test_app()

        with patch("mcp_server_langgraph.api.v1.agents._get_metrics_client") as mock_get_client:
            mock_client = AsyncMock(return_value=None)  # noqa: async-mock-config - configured below
            mock_client.query_instant = AsyncMock(
                return_value=MagicMock(
                    data=[MagicMock(value=100.0)],
                    result_type="vector",
                )
            )
            mock_get_client.return_value = mock_client

            client = TestClient(app)
            response = client.get("/api/v1/agents/metrics?time_range_hours=1")

            assert response.status_code == 200
            data = response.json()
            assert data["time_range_hours"] == 1


# =============================================================================
# Error Handling Tests
# =============================================================================


@pytest.mark.xdist_group(name="agents_metrics_errors")
class TestAgentMetricsErrorHandling:
    """Test error handling for agents metrics endpoint."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    async def test_returns_503_when_metrics_backend_unavailable(self) -> None:
        """Test endpoint returns 503 when metrics backend is unavailable."""
        from fastapi.testclient import TestClient

        app = create_agents_test_app()

        with patch("mcp_server_langgraph.api.v1.agents._get_metrics_client") as mock_get_client:
            mock_get_client.return_value = None

            client = TestClient(app)
            response = client.get("/api/v1/agents/metrics")

            assert response.status_code == 503

    @pytest.mark.asyncio
    async def test_returns_partial_metrics_on_query_failure(self) -> None:
        """Test endpoint returns partial metrics if some queries fail."""
        from fastapi.testclient import TestClient

        app = create_agents_test_app()

        with patch("mcp_server_langgraph.api.v1.agents._get_metrics_client") as mock_get_client:
            mock_client = AsyncMock(return_value=None)  # noqa: async-mock-config - configured below
            # First query succeeds, second fails
            mock_client.query_instant = AsyncMock(
                side_effect=[
                    MagicMock(data=[MagicMock(value=100.0)], result_type="vector"),
                    Exception("Query timeout"),
                    MagicMock(data=[MagicMock(value=50.0)], result_type="vector"),
                ]
            )
            mock_get_client.return_value = mock_client

            client = TestClient(app)
            response = client.get("/api/v1/agents/metrics")

            # Should still return 200 with partial data
            assert response.status_code == 200


# =============================================================================
# PromQL Query Tests
# =============================================================================


@pytest.mark.xdist_group(name="agents_metrics_queries")
class TestAgentMetricsQueries:
    """Test PromQL queries for agents metrics."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_orchestrator_metrics_queries_defined(self) -> None:
        """Test that orchestrator PromQL queries are defined."""
        from mcp_server_langgraph.api.v1.agents import ORCHESTRATOR_METRICS_QUERIES

        assert "total_executions" in ORCHESTRATOR_METRICS_QUERIES
        assert "successful_executions" in ORCHESTRATOR_METRICS_QUERIES
        assert "avg_duration_ms" in ORCHESTRATOR_METRICS_QUERIES

    def test_hitl_metrics_queries_defined(self) -> None:
        """Test that HITL PromQL queries are defined."""
        from mcp_server_langgraph.api.v1.agents import HITL_METRICS_QUERIES

        assert "total_requests" in HITL_METRICS_QUERIES
        assert "approved_count" in HITL_METRICS_QUERIES
        assert "pending_count" in HITL_METRICS_QUERIES

    def test_cost_metrics_queries_defined(self) -> None:
        """Test that cost PromQL queries are defined."""
        from mcp_server_langgraph.api.v1.agents import COST_METRICS_QUERIES

        assert "total_cost_usd" in COST_METRICS_QUERIES
        assert "total_tokens" in COST_METRICS_QUERIES
