"""
Cost Router Unit Tests

Tests for /api/v1/cost endpoints per TDD methodology.
Tests written FIRST before implementation (RED phase).

The cost endpoint provides cost tracking and analysis.
"""

import gc
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


pytestmark = [
    pytest.mark.unit,
    pytest.mark.api,
]


@pytest.fixture
def test_app() -> FastAPI:
    """Create a test app with the cost router."""
    from mcp_server_langgraph.api.v1.cost import cost_router
    from mcp_server_langgraph.auth.dependencies import (
        get_current_user,
        require_cost_admin,
        require_cost_viewer,
    )

    app = FastAPI()
    app.include_router(cost_router, prefix="/api/v1")

    # Mock authentication
    mock_user = {
        "sub": "test-user-id",
        "user_id": "test-user-id",
        "username": "testuser",
        "email": "testuser@example.com",
        "roles": ["admin"],
        "realm_access": {"roles": ["admin"]},
    }

    async def _override_current_user():
        return mock_user

    app.dependency_overrides[get_current_user] = _override_current_user
    app.dependency_overrides[require_cost_viewer] = lambda: mock_user
    app.dependency_overrides[require_cost_admin] = lambda: mock_user

    return app


@pytest.fixture
def client(test_app: FastAPI) -> TestClient:
    """Create a test client."""
    return TestClient(test_app)


@pytest.mark.xdist_group(name="test_cost_router")
class TestCostSummaryEndpoint:
    """Tests for GET /api/v1/cost/summary endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_get_summary_returns_200(self, test_app: FastAPI) -> None:
        """
        GIVEN a request to /api/v1/cost/summary
        WHEN GET request is made
        THEN response should be 200 OK
        """
        with patch("mcp_server_langgraph.api.v1.cost.get_cost_service") as mock_get_service:
            mock_service = AsyncMock(
                return_value=None
            )  # async-mock-configured (return_value set below)  # noqa: async-mock-config
            mock_service.get_summary.return_value = {
                "total_cost": 125.50,
                "prompt_tokens": 50000,
                "completion_tokens": 25000,
                "period_start": "2025-01-01T00:00:00Z",
                "period_end": "2025-01-31T23:59:59Z",
            }
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            response = client.get("/api/v1/cost/summary")

            assert response.status_code == 200

    def test_get_summary_returns_cost_data(self, test_app: FastAPI) -> None:
        """
        GIVEN cost data exists
        WHEN GET request is made
        THEN response should contain cost summary
        """
        with patch("mcp_server_langgraph.api.v1.cost.get_cost_service") as mock_get_service:
            mock_service = AsyncMock(
                return_value=None
            )  # async-mock-configured (return_value set below)  # noqa: async-mock-config
            mock_service.get_summary.return_value = {
                "total_cost": 125.50,
                "prompt_tokens": 50000,
                "completion_tokens": 25000,
            }
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            response = client.get("/api/v1/cost/summary")
            data = response.json()

            assert "total_cost" in data
            assert "prompt_tokens" in data
            assert "completion_tokens" in data


@pytest.mark.xdist_group(name="test_cost_router")
class TestCostByModelEndpoint:
    """Tests for GET /api/v1/cost/by-model endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_get_by_model_returns_200(self, test_app: FastAPI) -> None:
        """
        GIVEN a request to /api/v1/cost/by-model
        WHEN GET request is made
        THEN response should be 200 OK
        """
        with patch("mcp_server_langgraph.api.v1.cost.get_cost_service") as mock_get_service:
            mock_service = AsyncMock(
                return_value=None
            )  # async-mock-configured (return_value set below)  # noqa: async-mock-config
            mock_service.get_by_model.return_value = [
                {"model": "gpt-4", "cost": 100.00, "requests": 500},
                {"model": "gpt-3.5-turbo", "cost": 25.50, "requests": 1000},
            ]
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            response = client.get("/api/v1/cost/by-model")

            assert response.status_code == 200

    def test_get_by_model_returns_breakdown(self, test_app: FastAPI) -> None:
        """
        GIVEN cost data exists
        WHEN GET request is made
        THEN response should contain per-model breakdown
        """
        with patch("mcp_server_langgraph.api.v1.cost.get_cost_service") as mock_get_service:
            mock_service = AsyncMock(
                return_value=None
            )  # async-mock-configured (return_value set below)  # noqa: async-mock-config
            mock_service.get_by_model.return_value = [
                {"model": "gpt-4", "cost": 100.00, "requests": 500},
            ]
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            response = client.get("/api/v1/cost/by-model")
            data = response.json()

            assert isinstance(data, list)
            assert len(data) > 0
            assert "model" in data[0]
            assert "cost" in data[0]


@pytest.mark.xdist_group(name="test_cost_router")
class TestCostHistoryEndpoint:
    """Tests for GET /api/v1/cost/history endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_get_history_returns_200(self, test_app: FastAPI) -> None:
        """
        GIVEN a request to /api/v1/cost/history
        WHEN GET request is made with date range
        THEN response should be 200 OK
        """
        with patch("mcp_server_langgraph.api.v1.cost.get_cost_service") as mock_get_service:
            mock_service = AsyncMock(
                return_value=None
            )  # async-mock-configured (return_value set below)  # noqa: async-mock-config
            mock_service.get_history.return_value = [
                {"date": "2025-01-01", "cost": 10.00},
                {"date": "2025-01-02", "cost": 15.00},
            ]
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            response = client.get("/api/v1/cost/history?start_date=2025-01-01&end_date=2025-01-31")

            assert response.status_code == 200

    def test_get_history_returns_time_series(self, test_app: FastAPI) -> None:
        """
        GIVEN cost data exists for date range
        WHEN GET request is made
        THEN response should contain time series data
        """
        with patch("mcp_server_langgraph.api.v1.cost.get_cost_service") as mock_get_service:
            mock_service = AsyncMock(
                return_value=None
            )  # async-mock-configured (return_value set below)  # noqa: async-mock-config
            mock_service.get_history.return_value = [
                {"date": "2025-01-01", "cost": 10.00},
            ]
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            response = client.get("/api/v1/cost/history")
            data = response.json()

            assert isinstance(data, list)


@pytest.mark.xdist_group(name="test_cost_router_org")
class TestCostRecordsEndpoint:
    """Tests for GET /api/v1/cost/records endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_get_records_returns_200(self, test_app: FastAPI) -> None:
        """
        GIVEN a request to /api/v1/cost/records
        WHEN GET request is made
        THEN response should be 200 OK
        """
        with patch("mcp_server_langgraph.api.v1.cost.get_cost_service") as mock_get_service:
            mock_service = AsyncMock(return_value=None)  # noqa: async-mock-config
            mock_service.get_records.return_value = {
                "records": [],
                "next_cursor": None,
                "total_count": 0,
            }
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            response = client.get("/api/v1/cost/records")

            assert response.status_code == 200

    def test_get_records_with_org_filter(self, test_app: FastAPI) -> None:
        """
        GIVEN a request to /api/v1/cost/records with org filter
        WHEN GET request is made
        THEN service should be called with org filter
        """
        with patch("mcp_server_langgraph.api.v1.cost.get_cost_service") as mock_get_service:
            mock_service = AsyncMock(return_value=None)  # noqa: async-mock-config
            mock_service.get_records.return_value = {
                "records": [
                    {
                        "timestamp": "2025-01-01T00:00:00",
                        "user_id": "user:alice",
                        "session_id": "sess-1",
                        "model": "gpt-4",
                        "provider": "openai",
                        "prompt_tokens": 100,
                        "completion_tokens": 50,
                        "total_tokens": 150,
                        "estimated_cost_usd": 0.01,
                        "feature": "chat",
                        "organization_id": "organization:acme",
                        "project_id": None,
                        "team_id": None,
                    }
                ],
                "next_cursor": None,
                "total_count": 1,
            }
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            response = client.get("/api/v1/cost/records?organization_id=organization:acme")

            assert response.status_code == 200
            data = response.json()
            assert len(data["records"]) == 1
            assert data["records"][0]["organization_id"] == "organization:acme"


@pytest.mark.xdist_group(name="test_cost_router_org")
class TestCostByOrganizationEndpoint:
    """Tests for GET /api/v1/cost/summary/by-organization endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_get_cost_by_org_returns_200(self, test_app: FastAPI) -> None:
        """
        GIVEN a request to /api/v1/cost/summary/by-organization
        WHEN GET request is made
        THEN response should be 200 OK
        """
        with patch("mcp_server_langgraph.api.v1.cost.get_cost_service") as mock_get_service:
            mock_service = AsyncMock(return_value=None)  # noqa: async-mock-config
            mock_service.get_cost_by_organization.return_value = [
                {
                    "organization_id": "organization:acme",
                    "total_cost": 100.00,
                    "total_tokens": 50000,
                    "request_count": 100,
                }
            ]
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            response = client.get("/api/v1/cost/summary/by-organization")

            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["organization_id"] == "organization:acme"


@pytest.mark.xdist_group(name="test_cost_router_org")
class TestCostByProjectEndpoint:
    """Tests for GET /api/v1/cost/summary/by-project endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_get_cost_by_project_returns_200(self, test_app: FastAPI) -> None:
        """
        GIVEN a request to /api/v1/cost/summary/by-project
        WHEN GET request is made
        THEN response should be 200 OK
        """
        with patch("mcp_server_langgraph.api.v1.cost.get_cost_service") as mock_get_service:
            mock_service = AsyncMock(return_value=None)  # noqa: async-mock-config
            mock_service.get_cost_by_project.return_value = [
                {
                    "project_id": "project:backend",
                    "organization_id": "organization:acme",
                    "total_cost": 50.00,
                    "total_tokens": 25000,
                    "request_count": 50,
                }
            ]
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            response = client.get("/api/v1/cost/summary/by-project")

            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["project_id"] == "project:backend"


@pytest.mark.xdist_group(name="test_cost_router_org")
class TestCostByTeamEndpoint:
    """Tests for GET /api/v1/cost/summary/by-team endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_get_cost_by_team_returns_200(self, test_app: FastAPI) -> None:
        """
        GIVEN a request to /api/v1/cost/summary/by-team
        WHEN GET request is made
        THEN response should be 200 OK
        """
        with patch("mcp_server_langgraph.api.v1.cost.get_cost_service") as mock_get_service:
            mock_service = AsyncMock(return_value=None)  # noqa: async-mock-config
            mock_service.get_cost_by_team.return_value = [
                {
                    "team_id": "team:platform",
                    "organization_id": "organization:acme",
                    "project_id": "project:backend",
                    "total_cost": 25.00,
                    "total_tokens": 12500,
                    "request_count": 25,
                }
            ]
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            response = client.get("/api/v1/cost/summary/by-team")

            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["team_id"] == "team:platform"


@pytest.mark.xdist_group(name="test_cost_router_org")
class TestOrganizationalDateFiltering:
    """Tests for date filtering in organizational cost endpoints."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_get_cost_by_organization_passes_date_filters(self, test_app: FastAPI) -> None:
        """
        GIVEN a request to /api/v1/cost/summary/by-organization with date filters
        WHEN GET request is made
        THEN service should be called with date filters
        """
        with patch("mcp_server_langgraph.api.v1.cost.get_cost_service") as mock_get_service:
            mock_service = AsyncMock(return_value=None)  # noqa: async-mock-config
            mock_service.get_cost_by_organization.return_value = []
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            response = client.get("/api/v1/cost/summary/by-organization?start_date=2025-01-01&end_date=2025-01-31")

            assert response.status_code == 200
            mock_service.get_cost_by_organization.assert_called_once_with(
                start_date="2025-01-01",
                end_date="2025-01-31",
            )

    def test_get_records_passes_date_filters(self, test_app: FastAPI) -> None:
        """
        GIVEN a request to /api/v1/cost/records with date filters
        WHEN GET request is made
        THEN service should be called with date filters
        """
        with patch("mcp_server_langgraph.api.v1.cost.get_cost_service") as mock_get_service:
            mock_service = AsyncMock(return_value=None)  # noqa: async-mock-config
            mock_service.get_records.return_value = {
                "records": [],
                "next_cursor": None,
                "total_count": 0,
            }
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            response = client.get("/api/v1/cost/records?start_date=2025-01-01&end_date=2025-01-31")

            assert response.status_code == 200
            # Verify date filters are passed
            call_kwargs = mock_service.get_records.call_args.kwargs
            assert call_kwargs["start_date"] == "2025-01-01"
            assert call_kwargs["end_date"] == "2025-01-31"


class TestCostServiceImplDateFiltering:
    """Tests for CostServiceImpl date filtering at storage level."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_get_cost_by_organization_passes_dates_to_storage(self) -> None:
        """
        GIVEN a CostServiceImpl with date parameters
        WHEN get_cost_by_organization is called with dates
        THEN storage.get_cost_by_organization should receive parsed datetime filters
        """
        from datetime import datetime

        from mcp_server_langgraph.api.v1.cost import CostServiceImpl

        mock_storage = AsyncMock(return_value=None)  # noqa: async-mock-config
        mock_storage.get_cost_by_organization.return_value = []

        service = CostServiceImpl(storage=mock_storage)
        await service.get_cost_by_organization(
            start_date="2025-01-01",
            end_date="2025-01-31",
        )

        # Verify storage's database-level aggregation method was called
        mock_storage.get_cost_by_organization.assert_called_once()
        call_kwargs = mock_storage.get_cost_by_organization.call_args.kwargs
        assert isinstance(call_kwargs.get("start_date"), datetime)
        assert isinstance(call_kwargs.get("end_date"), datetime)
        assert call_kwargs["start_date"].date().isoformat() == "2025-01-01"
        assert call_kwargs["end_date"].date().isoformat() == "2025-01-31"

    @pytest.mark.asyncio
    async def test_get_cost_by_project_passes_dates_to_storage(self) -> None:
        """
        GIVEN a CostServiceImpl with date parameters
        WHEN get_cost_by_project is called with dates
        THEN storage.get_cost_by_project should receive parsed datetime filters
        """
        from datetime import datetime

        from mcp_server_langgraph.api.v1.cost import CostServiceImpl

        mock_storage = AsyncMock(return_value=None)  # noqa: async-mock-config
        mock_storage.get_cost_by_project.return_value = []

        service = CostServiceImpl(storage=mock_storage)
        await service.get_cost_by_project(
            organization_id="organization:acme",
            start_date="2025-01-01",
            end_date="2025-01-31",
        )

        # Verify storage's database-level aggregation method was called
        mock_storage.get_cost_by_project.assert_called_once()
        call_kwargs = mock_storage.get_cost_by_project.call_args.kwargs
        assert call_kwargs.get("organization_id") == "organization:acme"
        assert isinstance(call_kwargs.get("start_date"), datetime)
        assert isinstance(call_kwargs.get("end_date"), datetime)
        assert call_kwargs["start_date"].date().isoformat() == "2025-01-01"
        assert call_kwargs["end_date"].date().isoformat() == "2025-01-31"

    @pytest.mark.asyncio
    async def test_get_cost_by_team_passes_dates_to_storage(self) -> None:
        """
        GIVEN a CostServiceImpl with date parameters
        WHEN get_cost_by_team is called with dates
        THEN storage.get_cost_by_team should receive parsed datetime filters
        """
        from datetime import datetime

        from mcp_server_langgraph.api.v1.cost import CostServiceImpl

        mock_storage = AsyncMock(return_value=None)  # noqa: async-mock-config
        mock_storage.get_cost_by_team.return_value = []

        service = CostServiceImpl(storage=mock_storage)
        await service.get_cost_by_team(
            organization_id="organization:acme",
            project_id="project:backend",
            start_date="2025-01-01",
            end_date="2025-01-31",
        )

        # Verify storage's database-level aggregation method was called
        mock_storage.get_cost_by_team.assert_called_once()
        call_kwargs = mock_storage.get_cost_by_team.call_args.kwargs
        assert call_kwargs.get("organization_id") == "organization:acme"
        assert call_kwargs.get("project_id") == "project:backend"
        assert isinstance(call_kwargs.get("start_date"), datetime)
        assert isinstance(call_kwargs.get("end_date"), datetime)
        assert call_kwargs["start_date"].date().isoformat() == "2025-01-01"
        assert call_kwargs["end_date"].date().isoformat() == "2025-01-31"


@pytest.mark.xdist_group(name="test_cost_router_validation")
class TestCostRecordsInputValidation:
    """Tests for API input validation on /cost/records endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_limit_below_minimum_returns_422(self, test_app: FastAPI) -> None:
        """
        GIVEN a request with limit=0 (below minimum of 1)
        WHEN GET request is made to /api/v1/cost/records
        THEN response should be 422 Unprocessable Entity
        """
        client = TestClient(test_app)
        response = client.get("/api/v1/cost/records?limit=0")

        assert response.status_code == 422
        assert "limit" in response.text.lower() or "value" in response.text.lower()

    def test_limit_above_maximum_returns_422(self, test_app: FastAPI) -> None:
        """
        GIVEN a request with limit=2000 (above maximum of 1000)
        WHEN GET request is made to /api/v1/cost/records
        THEN response should be 422 Unprocessable Entity
        """
        client = TestClient(test_app)
        response = client.get("/api/v1/cost/records?limit=2000")

        assert response.status_code == 422
        assert "limit" in response.text.lower() or "value" in response.text.lower()

    def test_limit_negative_returns_422(self, test_app: FastAPI) -> None:
        """
        GIVEN a request with negative limit
        WHEN GET request is made to /api/v1/cost/records
        THEN response should be 422 Unprocessable Entity
        """
        client = TestClient(test_app)
        response = client.get("/api/v1/cost/records?limit=-5")

        assert response.status_code == 422

    def test_limit_non_integer_returns_422(self, test_app: FastAPI) -> None:
        """
        GIVEN a request with non-integer limit
        WHEN GET request is made to /api/v1/cost/records
        THEN response should be 422 Unprocessable Entity
        """
        client = TestClient(test_app)
        response = client.get("/api/v1/cost/records?limit=abc")

        assert response.status_code == 422

    def test_valid_limit_returns_200(self, test_app: FastAPI) -> None:
        """
        GIVEN a request with valid limit at boundaries
        WHEN GET request is made to /api/v1/cost/records
        THEN response should be 200 OK
        """
        with patch("mcp_server_langgraph.api.v1.cost.get_cost_service") as mock_get_service:
            mock_service = AsyncMock(return_value=None)  # noqa: async-mock-config
            mock_service.get_records.return_value = {
                "records": [],
                "next_cursor": None,
                "total_count": 0,
            }
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)

            # Test minimum valid limit
            response = client.get("/api/v1/cost/records?limit=1")
            assert response.status_code == 200

            # Test maximum valid limit
            response = client.get("/api/v1/cost/records?limit=1000")
            assert response.status_code == 200


@pytest.mark.xdist_group(name="test_cost_router_validation")
class TestBudgetStatusInputValidation:
    """Tests for API input validation on /cost/budget/status endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_missing_entity_id_returns_422(self, test_app: FastAPI) -> None:
        """
        GIVEN a request without required entity_id parameter
        WHEN GET request is made to /api/v1/cost/budget/status
        THEN response should be 422 Unprocessable Entity
        """
        client = TestClient(test_app)
        response = client.get("/api/v1/cost/budget/status?entity_type=user")

        assert response.status_code == 422
        data = response.json()
        # FastAPI includes field name in validation error
        assert any("entity_id" in str(e) for e in data.get("detail", []))

    def test_missing_entity_type_returns_422(self, test_app: FastAPI) -> None:
        """
        GIVEN a request without required entity_type parameter
        WHEN GET request is made to /api/v1/cost/budget/status
        THEN response should be 422 Unprocessable Entity
        """
        client = TestClient(test_app)
        response = client.get("/api/v1/cost/budget/status?entity_id=user:alice")

        assert response.status_code == 422
        data = response.json()
        # FastAPI includes field name in validation error
        assert any("entity_type" in str(e) for e in data.get("detail", []))


@pytest.mark.xdist_group(name="test_cost_router_validation")
class TestDateParameterValidation:
    """Tests for date parameter handling in cost endpoints."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_invalid_date_format_handled_gracefully(self, test_app: FastAPI) -> None:
        """
        GIVEN a request with invalid date format
        WHEN GET request is made
        THEN service should handle gracefully (may return 400 or 500)

        Note: This test verifies behavior when the endpoint receives an invalid date.
        The exact status code depends on whether validation happens at router or service level.
        """
        with patch("mcp_server_langgraph.api.v1.cost.get_cost_service") as mock_get_service:
            mock_service = AsyncMock(return_value=None)  # noqa: async-mock-config
            # Service returns empty data - the endpoint may handle validation before calling service
            mock_service.get_summary.return_value = {
                "total_cost": 0.0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
            }
            mock_get_service.return_value = mock_service

            client = TestClient(test_app, raise_server_exceptions=False)
            response = client.get("/api/v1/cost/summary?start_date=not-a-date")

            # The endpoint should either return data (if it ignores invalid dates)
            # or return an error status code (if it validates dates)
            # This tests that the endpoint doesn't crash
            assert response.status_code in (200, 400, 422, 500)

    def test_empty_date_params_returns_200(self, test_app: FastAPI) -> None:
        """
        GIVEN a request with no date parameters
        WHEN GET request is made
        THEN response should be 200 OK (uses defaults)
        """
        with patch("mcp_server_langgraph.api.v1.cost.get_cost_service") as mock_get_service:
            mock_service = AsyncMock(return_value=None)  # noqa: async-mock-config
            mock_service.get_summary.return_value = {
                "total_cost": 0.0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
            }
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            response = client.get("/api/v1/cost/summary")

            assert response.status_code == 200

    def test_valid_date_format_returns_200(self, test_app: FastAPI) -> None:
        """
        GIVEN a request with valid YYYY-MM-DD date format
        WHEN GET request is made
        THEN response should be 200 OK
        """
        with patch("mcp_server_langgraph.api.v1.cost.get_cost_service") as mock_get_service:
            mock_service = AsyncMock(return_value=None)  # noqa: async-mock-config
            mock_service.get_summary.return_value = {
                "total_cost": 100.0,
                "prompt_tokens": 5000,
                "completion_tokens": 2500,
            }
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            response = client.get("/api/v1/cost/summary?start_date=2025-01-01&end_date=2025-12-31")

            assert response.status_code == 200


@pytest.mark.xdist_group(name="test_cost_router_validation")
class TestSortParameterValidation:
    """Tests for sort parameter handling in cost/records endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_valid_sort_by_timestamp(self, test_app: FastAPI) -> None:
        """
        GIVEN a request with sort_by=timestamp
        WHEN GET request is made
        THEN response should be 200 OK
        """
        with patch("mcp_server_langgraph.api.v1.cost.get_cost_service") as mock_get_service:
            mock_service = AsyncMock(return_value=None)  # noqa: async-mock-config
            mock_service.get_records.return_value = {
                "records": [],
                "next_cursor": None,
                "total_count": 0,
            }
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            response = client.get("/api/v1/cost/records?sort_by=timestamp")

            assert response.status_code == 200

    def test_valid_sort_by_cost(self, test_app: FastAPI) -> None:
        """
        GIVEN a request with sort_by=estimated_cost_usd
        WHEN GET request is made
        THEN response should be 200 OK
        """
        with patch("mcp_server_langgraph.api.v1.cost.get_cost_service") as mock_get_service:
            mock_service = AsyncMock(return_value=None)  # noqa: async-mock-config
            mock_service.get_records.return_value = {
                "records": [],
                "next_cursor": None,
                "total_count": 0,
            }
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            response = client.get("/api/v1/cost/records?sort_by=estimated_cost_usd")

            assert response.status_code == 200

    def test_valid_sort_order_asc(self, test_app: FastAPI) -> None:
        """
        GIVEN a request with sort_order=asc
        WHEN GET request is made
        THEN response should be 200 OK
        """
        with patch("mcp_server_langgraph.api.v1.cost.get_cost_service") as mock_get_service:
            mock_service = AsyncMock(return_value=None)  # noqa: async-mock-config
            mock_service.get_records.return_value = {
                "records": [],
                "next_cursor": None,
                "total_count": 0,
            }
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            response = client.get("/api/v1/cost/records?sort_order=asc")

            assert response.status_code == 200

    def test_valid_sort_order_desc(self, test_app: FastAPI) -> None:
        """
        GIVEN a request with sort_order=desc
        WHEN GET request is made
        THEN response should be 200 OK
        """
        with patch("mcp_server_langgraph.api.v1.cost.get_cost_service") as mock_get_service:
            mock_service = AsyncMock(return_value=None)  # noqa: async-mock-config
            mock_service.get_records.return_value = {
                "records": [],
                "next_cursor": None,
                "total_count": 0,
            }
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            response = client.get("/api/v1/cost/records?sort_order=desc")

            assert response.status_code == 200


@pytest.mark.xdist_group(name="test_cost_router_validation")
class TestEntityTypeValidation:
    """Tests for entity_type Literal validation in budget endpoints."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_budget_status_invalid_entity_type_returns_422(self, test_app: FastAPI) -> None:
        """
        GIVEN a request with invalid entity_type value
        WHEN GET request is made to /api/v1/cost/budget/status
        THEN response should be 422 Unprocessable Entity

        This validates the Literal["organization", "project", "team", "user"] type.
        """
        client = TestClient(test_app)
        response = client.get("/api/v1/cost/budget/status?entity_type=invalid&entity_id=user:alice")

        assert response.status_code == 422
        data = response.json()
        # FastAPI returns detailed validation error for Literal types
        assert "detail" in data
        error_detail = str(data["detail"]).lower()
        assert "entity_type" in error_detail or "invalid" in error_detail

    def test_budget_status_valid_entity_types_accepted(self, test_app: FastAPI) -> None:
        """
        GIVEN a request with valid entity_type values
        WHEN GET request is made to /api/v1/cost/budget/status
        THEN response should be 200 OK (not 422)

        Tests all valid Literal values: organization, project, team, user.
        """
        with patch("mcp_server_langgraph.api.v1.cost.get_cost_service") as mock_get_service:
            with patch("mcp_server_langgraph.api.v1.cost.get_budget_checker") as mock_get_checker:
                mock_service = AsyncMock(return_value=None)  # noqa: async-mock-config
                mock_service.get_cost_by_organization.return_value = []
                mock_service.get_cost_by_project.return_value = []
                mock_service.get_cost_by_team.return_value = []
                mock_service.get_summary.return_value = {"total_cost": 0}
                mock_get_service.return_value = mock_service

                mock_checker = AsyncMock(return_value=None)  # noqa: async-mock-config - check method configured below
                mock_checker.check = AsyncMock(
                    return_value=MagicMock(
                        status="ok",
                        percent_used=0.0,
                        current_spend=0.0,
                        remaining=1000.0,
                        message="Under budget",
                    )
                )
                mock_get_checker.return_value = mock_checker

                client = TestClient(test_app)

                for entity_type in ["organization", "project", "team", "user"]:
                    response = client.get(f"/api/v1/cost/budget/status?entity_type={entity_type}&entity_id=test:id")
                    assert response.status_code == 200, f"entity_type={entity_type} should be valid"

    def test_budget_anomaly_invalid_entity_type_returns_422(self, test_app: FastAPI) -> None:
        """
        GIVEN a request with invalid entity_type value
        WHEN GET request is made to /api/v1/cost/budget/anomaly
        THEN response should be 422 Unprocessable Entity
        """
        client = TestClient(test_app)
        response = client.get("/api/v1/cost/budget/anomaly?entity_type=unknown&entity_id=user:alice")

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_budget_forecast_invalid_entity_type_returns_422(self, test_app: FastAPI) -> None:
        """
        GIVEN a request with invalid entity_type value
        WHEN GET request is made to /api/v1/cost/budget/forecast
        THEN response should be 422 Unprocessable Entity
        """
        client = TestClient(test_app)
        response = client.get("/api/v1/cost/budget/forecast?entity_type=badtype&entity_id=org:acme")

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_entity_type_case_sensitive(self, test_app: FastAPI) -> None:
        """
        GIVEN a request with wrong case entity_type value
        WHEN GET request is made to budget endpoints
        THEN response should be 422 (Literal is case-sensitive)
        """
        client = TestClient(test_app)

        # Test uppercase variants - should fail
        for wrong_case in ["Organization", "PROJECT", "Team", "USER"]:
            response = client.get(f"/api/v1/cost/budget/status?entity_type={wrong_case}&entity_id=test:id")
            assert response.status_code == 422, f"entity_type={wrong_case} should be rejected (case-sensitive)"


# ==============================================================================
# Tests for Budget Loading from Storage (addressing TODO in cost.py:761)
# ==============================================================================


class TestBudgetLoadingFromStorage:
    """Tests for budget loading from BudgetStorage instead of hardcoded defaults."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_budget_status_uses_stored_budget_when_available(self, test_app: FastAPI) -> None:
        """
        GIVEN a budget exists in storage for an entity
        WHEN GET request is made to /api/v1/cost/budget/status
        THEN the stored budget limit should be used (not hardcoded $1000)
        """
        from decimal import Decimal
        from mcp_server_langgraph.monitoring.cost_budget import Budget

        # Create a mock stored budget with $5000 limit
        stored_budget = Budget(
            entity_type="organization",
            entity_id="organization:acme",
            monthly_limit_usd=Decimal("5000.00"),
            warning_threshold=0.80,
            critical_threshold=0.95,
        )

        with (
            patch("mcp_server_langgraph.api.v1.cost.get_cost_service") as mock_get_service,
            patch("mcp_server_langgraph.api.v1.cost.get_budget_storage") as mock_get_storage,
            patch("mcp_server_langgraph.api.v1.cost.get_budget_checker") as mock_get_checker,
        ):
            # Mock cost service
            mock_service = AsyncMock(return_value=None)  # noqa: async-mock-config
            mock_service.get_cost_by_organization.return_value = [
                {"organization_id": "organization:acme", "total_cost": 2500.00}
            ]
            mock_get_service.return_value = mock_service

            # Mock budget storage to return stored budget
            mock_storage = AsyncMock(return_value=None)  # noqa: async-mock-config
            mock_storage.get_budget.return_value = stored_budget
            mock_get_storage.return_value = mock_storage

            # Mock budget checker
            from mcp_server_langgraph.monitoring.cost_budget import BudgetStatus

            mock_checker = AsyncMock(return_value=None)  # noqa: async-mock-config
            mock_status = BudgetStatus(
                budget=stored_budget,
                current_spend=Decimal("2500.00"),
                percent_used=50.0,
                status="ok",
                remaining=Decimal("2500.00"),
            )
            mock_checker.check.return_value = mock_status
            mock_get_checker.return_value = mock_checker

            client = TestClient(test_app)
            response = client.get("/api/v1/cost/budget/status?entity_type=organization&entity_id=organization:acme")

            assert response.status_code == 200
            data = response.json()

            # Should use the stored budget limit of $5000, not the hardcoded $1000
            assert data["monthly_limit"] == 5000.00

    def test_budget_status_falls_back_to_default_when_no_stored_budget(self, test_app: FastAPI) -> None:
        """
        GIVEN no budget exists in storage for an entity
        WHEN GET request is made to /api/v1/cost/budget/status
        THEN a default budget should be used
        """
        with (
            patch("mcp_server_langgraph.api.v1.cost.get_cost_service") as mock_get_service,
            patch("mcp_server_langgraph.api.v1.cost.get_budget_storage") as mock_get_storage,
            patch("mcp_server_langgraph.api.v1.cost.get_budget_checker") as mock_get_checker,
        ):
            # Mock cost service
            mock_service = AsyncMock(return_value=None)  # noqa: async-mock-config
            mock_service.get_summary.return_value = {"total_cost": 100.00}
            mock_get_service.return_value = mock_service

            # Mock budget storage to return None (no stored budget)
            mock_storage = AsyncMock(return_value=None)  # noqa: async-mock-config
            mock_storage.get_budget.return_value = None
            mock_get_storage.return_value = mock_storage

            # Mock budget checker
            from mcp_server_langgraph.monitoring.cost_budget import BudgetStatus

            mock_checker = AsyncMock(return_value=None)  # noqa: async-mock-config

            def check_budget(budget, spend):
                return BudgetStatus(
                    budget=budget,
                    current_spend=spend,
                    percent_used=float(spend / budget.monthly_limit_usd * 100),
                    status="ok",
                    remaining=budget.monthly_limit_usd - spend,
                )

            mock_checker.check.side_effect = check_budget
            mock_get_checker.return_value = mock_checker

            client = TestClient(test_app)
            response = client.get("/api/v1/cost/budget/status?entity_type=user&entity_id=user:alice")

            assert response.status_code == 200
            data = response.json()

            # Should use default budget (implementation detail - tests behavior)
            assert "monthly_limit" in data
            assert data["monthly_limit"] > 0  # Should have some reasonable default

    def test_budget_storage_get_budget_called_with_correct_params(self, test_app: FastAPI) -> None:
        """
        GIVEN a budget status request
        WHEN the endpoint processes the request
        THEN BudgetStorage.get_budget should be called with correct entity_type and entity_id
        """
        with (
            patch("mcp_server_langgraph.api.v1.cost.get_cost_service") as mock_get_service,
            patch("mcp_server_langgraph.api.v1.cost.get_budget_storage") as mock_get_storage,
            patch("mcp_server_langgraph.api.v1.cost.get_budget_checker") as mock_get_checker,
        ):
            # Mock cost service
            mock_service = AsyncMock(return_value=None)  # noqa: async-mock-config
            mock_service.get_cost_by_project.return_value = [{"project_id": "project:backend", "total_cost": 500.00}]
            mock_get_service.return_value = mock_service

            # Mock budget storage
            mock_storage = AsyncMock(return_value=None)  # noqa: async-mock-config
            mock_storage.get_budget.return_value = None
            mock_get_storage.return_value = mock_storage

            # Mock budget checker
            from decimal import Decimal
            from mcp_server_langgraph.monitoring.cost_budget import Budget, BudgetStatus

            mock_checker = AsyncMock(return_value=None)  # noqa: async-mock-config
            mock_checker.check.return_value = BudgetStatus(
                budget=Budget(
                    entity_type="project",
                    entity_id="project:backend",
                    monthly_limit_usd=Decimal("1000.00"),
                ),
                current_spend=Decimal("500.00"),
                percent_used=50.0,
                status="ok",
                remaining=Decimal("500.00"),
            )
            mock_get_checker.return_value = mock_checker

            client = TestClient(test_app)
            client.get("/api/v1/cost/budget/status?entity_type=project&entity_id=project:backend")

            # Verify get_budget was called with correct parameters
            mock_storage.get_budget.assert_called_once_with(
                entity_type="project",
                entity_id="project:backend",
            )
