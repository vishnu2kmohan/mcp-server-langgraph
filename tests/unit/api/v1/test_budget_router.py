"""
Budget Router Unit Tests

TDD tests for budget management API endpoints.
Tests cover:
- GET /cost/budget/status - Check budget status for current user/entity
- GET /cost/budget/{entity_id} - Get specific budget
- POST /cost/budgets - Create a new budget
- PUT /cost/budgets/{entity_type}/{entity_id} - Update a budget
- DELETE /cost/budgets/{entity_type}/{entity_id} - Delete a budget
- GET /cost/budgets - List all budgets
- GET /cost/budget/anomaly - Detect cost anomalies
- GET /cost/budget/forecast - Get cost forecast
"""

import gc
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

pytestmark = [pytest.mark.unit, pytest.mark.api]


def _create_budget_test_app() -> FastAPI:
    """Create a test app with proper auth dependency overrides."""
    from mcp_server_langgraph.api.v1.cost import cost_router
    from mcp_server_langgraph.auth.dependencies import (
        get_current_user,
        require_cost_admin,
        require_cost_viewer,
    )

    app = FastAPI()
    app.include_router(cost_router, prefix="/api/v1")

    # Mock authentication - bypass all auth checks
    mock_user: dict[str, Any] = {
        "sub": "test-user-id",
        "user_id": "test-user-id",
        "username": "testuser",
        "email": "testuser@example.com",
        "roles": ["admin"],
        "realm_access": {"roles": ["admin"]},
    }
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[require_cost_viewer] = lambda: mock_user
    app.dependency_overrides[require_cost_admin] = lambda: mock_user

    return app


# ==============================================================================
# Budget CRUD Endpoint Tests
# ==============================================================================


@pytest.mark.xdist_group(name="test_budget_crud")
class TestBudgetCRUDEndpoints:
    """Tests for budget CRUD endpoints."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_list_budgets_returns_200(self) -> None:
        """
        GIVEN a valid request to list budgets
        WHEN calling GET /cost/budgets
        THEN it should return 200 OK with a list of budgets
        """
        app = _create_budget_test_app()

        with patch("mcp_server_langgraph.api.v1.cost.get_budget_storage") as mock_storage:
            mock_storage_instance = AsyncMock(return_value=None)  # noqa: async-mock-config
            mock_storage_instance.list_budgets = AsyncMock(return_value=[])
            mock_storage.return_value = mock_storage_instance

            client = TestClient(app)
            response = client.get("/api/v1/cost/budgets")

            assert response.status_code == 200
            assert response.json() == {"budgets": []}

    @pytest.mark.asyncio
    async def test_list_budgets_returns_all_budgets(self) -> None:
        """
        GIVEN multiple budgets exist
        WHEN calling GET /cost/budgets
        THEN it should return all budgets
        """
        from mcp_server_langgraph.monitoring.cost_budget import Budget

        app = _create_budget_test_app()

        mock_budgets = [
            Budget(
                entity_type="organization",
                entity_id="organization:acme",
                monthly_limit_usd=Decimal("10000.00"),
            ),
            Budget(
                entity_type="user",
                entity_id="user:alice",
                monthly_limit_usd=Decimal("100.00"),
            ),
        ]

        with patch("mcp_server_langgraph.api.v1.cost.get_budget_storage") as mock_storage:
            mock_storage_instance = AsyncMock(return_value=None)  # noqa: async-mock-config
            mock_storage_instance.list_budgets = AsyncMock(return_value=mock_budgets)
            mock_storage.return_value = mock_storage_instance

            client = TestClient(app)
            response = client.get("/api/v1/cost/budgets")

            assert response.status_code == 200
            data = response.json()
            assert len(data["budgets"]) == 2

    @pytest.mark.asyncio
    async def test_create_budget_returns_201(self) -> None:
        """
        GIVEN a valid budget creation request
        WHEN calling POST /cost/budgets
        THEN it should return 201 Created
        """
        app = _create_budget_test_app()

        with patch("mcp_server_langgraph.api.v1.cost.get_budget_storage") as mock_storage:
            mock_storage_instance = AsyncMock(return_value=None)  # noqa: async-mock-config
            mock_storage_instance.save_budget = AsyncMock(return_value=None)
            mock_storage_instance.get_budget = AsyncMock(return_value=None)
            mock_storage.return_value = mock_storage_instance

            client = TestClient(app)
            response = client.post(
                "/api/v1/cost/budgets",
                json={
                    "entity_type": "project",
                    "entity_id": "project:backend",
                    "monthly_limit_usd": "500.00",
                },
            )

            assert response.status_code == 201
            mock_storage_instance.save_budget.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_budget_returns_409_if_exists(self) -> None:
        """
        GIVEN a budget already exists for the entity
        WHEN calling POST /cost/budgets
        THEN it should return 409 Conflict
        """
        from mcp_server_langgraph.monitoring.cost_budget import Budget

        app = _create_budget_test_app()

        existing_budget = Budget(
            entity_type="project",
            entity_id="project:backend",
            monthly_limit_usd=Decimal("500.00"),
        )

        with patch("mcp_server_langgraph.api.v1.cost.get_budget_storage") as mock_storage:
            mock_storage_instance = AsyncMock(return_value=None)  # noqa: async-mock-config
            mock_storage_instance.get_budget = AsyncMock(return_value=existing_budget)
            mock_storage.return_value = mock_storage_instance

            client = TestClient(app)
            response = client.post(
                "/api/v1/cost/budgets",
                json={
                    "entity_type": "project",
                    "entity_id": "project:backend",
                    "monthly_limit_usd": "500.00",
                },
            )

            assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_update_budget_returns_200(self) -> None:
        """
        GIVEN an existing budget
        WHEN calling PUT /cost/budgets/{entity_type}/{entity_id}
        THEN it should return 200 OK with updated budget
        """
        from mcp_server_langgraph.monitoring.cost_budget import Budget

        app = _create_budget_test_app()

        existing_budget = Budget(
            entity_type="team",
            entity_id="team:platform",
            monthly_limit_usd=Decimal("500.00"),
        )

        with patch("mcp_server_langgraph.api.v1.cost.get_budget_storage") as mock_storage:
            mock_storage_instance = AsyncMock(return_value=None)  # noqa: async-mock-config
            mock_storage_instance.get_budget = AsyncMock(return_value=existing_budget)
            mock_storage_instance.save_budget = AsyncMock(return_value=None)
            mock_storage.return_value = mock_storage_instance

            client = TestClient(app)
            response = client.put(
                "/api/v1/cost/budgets/team/team:platform",
                json={
                    "monthly_limit_usd": "750.00",
                    "warning_threshold": 0.85,
                },
            )

            assert response.status_code == 200
            mock_storage_instance.save_budget.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_budget_returns_404_if_not_found(self) -> None:
        """
        GIVEN no budget exists for the entity
        WHEN calling PUT /cost/budgets/{entity_type}/{entity_id}
        THEN it should return 404 Not Found
        """
        app = _create_budget_test_app()

        with patch("mcp_server_langgraph.api.v1.cost.get_budget_storage") as mock_storage:
            mock_storage_instance = AsyncMock(return_value=None)  # noqa: async-mock-config
            mock_storage_instance.get_budget = AsyncMock(return_value=None)
            mock_storage.return_value = mock_storage_instance

            client = TestClient(app)
            response = client.put(
                "/api/v1/cost/budgets/team/team:nonexistent",
                json={"monthly_limit_usd": "750.00"},
            )

            assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_budget_returns_204(self) -> None:
        """
        GIVEN an existing budget
        WHEN calling DELETE /cost/budgets/{entity_type}/{entity_id}
        THEN it should return 204 No Content
        """
        app = _create_budget_test_app()

        with patch("mcp_server_langgraph.api.v1.cost.get_budget_storage") as mock_storage:
            mock_storage_instance = AsyncMock(return_value=None)  # noqa: async-mock-config
            mock_storage_instance.delete_budget = AsyncMock(return_value=True)
            mock_storage.return_value = mock_storage_instance

            client = TestClient(app)
            response = client.delete("/api/v1/cost/budgets/user/user:alice")

            assert response.status_code == 204
            mock_storage_instance.delete_budget.assert_called_once_with(entity_type="user", entity_id="user:alice")

    @pytest.mark.asyncio
    async def test_delete_budget_returns_404_if_not_found(self) -> None:
        """
        GIVEN no budget exists for the entity
        WHEN calling DELETE /cost/budgets/{entity_type}/{entity_id}
        THEN it should return 404 Not Found
        """
        app = _create_budget_test_app()

        with patch("mcp_server_langgraph.api.v1.cost.get_budget_storage") as mock_storage:
            mock_storage_instance = AsyncMock(return_value=None)  # noqa: async-mock-config
            mock_storage_instance.delete_budget = AsyncMock(return_value=False)
            mock_storage.return_value = mock_storage_instance

            client = TestClient(app)
            response = client.delete("/api/v1/cost/budgets/user/user:nonexistent")

            assert response.status_code == 404


@pytest.mark.xdist_group(name="test_budget_router")
class TestBudgetStatusEndpoint:
    """Tests for GET /cost/budget/status endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_get_budget_status_returns_200(self) -> None:
        """
        GIVEN a valid request for budget status
        WHEN calling GET /cost/budget/status
        THEN it should return 200 OK
        """
        app = _create_budget_test_app()

        with (
            patch("mcp_server_langgraph.api.v1.cost.get_budget_checker") as mock_checker,
            patch("mcp_server_langgraph.api.v1.cost.get_cost_service") as mock_service,
        ):
            # Mock the budget checker
            mock_checker_instance = MagicMock()
            mock_checker_instance.check = AsyncMock(
                return_value=MagicMock(
                    status="ok",
                    percent_used=45.5,
                    current_spend=Decimal("455.00"),
                    remaining=Decimal("545.00"),
                    message="Budget on track",
                    budget=MagicMock(
                        entity_type="user",
                        entity_id="user:test",
                        monthly_limit_usd=Decimal("1000.00"),
                    ),
                )
            )
            mock_checker.return_value = mock_checker_instance

            # Mock the cost service with AsyncMock for async methods
            mock_service_instance = MagicMock()
            mock_service_instance.get_cost_summary = AsyncMock(return_value={"total_cost": 455.00})
            mock_service_instance.get_summary = AsyncMock(return_value={"total_cost": 455.00})
            mock_service_instance.get_cost_by_organization = AsyncMock(return_value=[])
            mock_service_instance.get_cost_by_project = AsyncMock(return_value=[])
            mock_service_instance.get_cost_by_team = AsyncMock(return_value=[])
            mock_service.return_value = mock_service_instance

            client = TestClient(app)
            response = client.get(
                "/api/v1/cost/budget/status",
                params={"entity_type": "user", "entity_id": "user:test"},
            )

            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_budget_status_returns_correct_data(self) -> None:
        """
        GIVEN a valid budget status request
        WHEN calling GET /cost/budget/status
        THEN it should return budget status with all fields
        """
        app = _create_budget_test_app()

        with (
            patch("mcp_server_langgraph.api.v1.cost.get_budget_checker") as mock_checker,
            patch("mcp_server_langgraph.api.v1.cost.get_cost_service") as mock_service,
        ):
            mock_checker_instance = MagicMock()
            mock_checker_instance.check = AsyncMock(
                return_value=MagicMock(
                    status="warning",
                    percent_used=85.0,
                    current_spend=Decimal("850.00"),
                    remaining=Decimal("150.00"),
                    message="Budget warning: 85% used",
                    budget=MagicMock(
                        entity_type="organization",
                        entity_id="organization:acme",
                        monthly_limit_usd=Decimal("1000.00"),
                    ),
                )
            )
            mock_checker.return_value = mock_checker_instance

            # Mock the cost service with AsyncMock for async methods
            mock_service_instance = MagicMock()
            mock_service_instance.get_cost_summary = AsyncMock(return_value={"total_cost": 850.00})
            mock_service_instance.get_cost_by_organization = AsyncMock(return_value=[])
            mock_service_instance.get_cost_by_project = AsyncMock(return_value=[])
            mock_service_instance.get_cost_by_team = AsyncMock(return_value=[])
            mock_service.return_value = mock_service_instance

            client = TestClient(app)
            response = client.get(
                "/api/v1/cost/budget/status",
                params={"entity_type": "organization", "entity_id": "organization:acme"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "warning"
            assert data["percent_used"] == 85.0
            assert float(data["current_spend"]) == 850.0
            assert float(data["remaining"]) == 150.0


@pytest.mark.xdist_group(name="test_budget_anomaly_router")
class TestBudgetAnomalyEndpoint:
    """Tests for GET /cost/budget/anomaly endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_get_anomaly_detection_returns_200(self) -> None:
        """
        GIVEN a valid anomaly detection request
        WHEN calling GET /cost/budget/anomaly
        THEN it should return 200 OK
        """
        app = _create_budget_test_app()

        with (
            patch("mcp_server_langgraph.api.v1.cost.get_anomaly_detector") as mock_detector,
            patch("mcp_server_langgraph.api.v1.cost.get_cost_service") as mock_service,
        ):
            mock_detector_instance = MagicMock()
            mock_detector_instance.detect = AsyncMock(
                return_value=MagicMock(
                    is_anomaly=False,
                    severity="none",
                    z_score=0.5,
                    mean=Decimal("100.00"),
                    std_dev=Decimal("10.00"),
                    message="Normal spending",
                )
            )
            mock_detector.return_value = mock_detector_instance

            # Mock the cost service with AsyncMock for async methods
            mock_service_instance = MagicMock()
            mock_service_instance.get_cost_summary = AsyncMock(return_value={"total_cost": 102.00})
            mock_service_instance.get_cost_by_organization = AsyncMock(return_value=[])
            mock_service_instance.get_cost_by_project = AsyncMock(return_value=[])
            mock_service_instance.get_cost_by_team = AsyncMock(return_value=[])
            mock_service_instance.get_history = AsyncMock(
                return_value=[
                    {"date": "2025-12-21", "cost": 95.0},
                    {"date": "2025-12-22", "cost": 105.0},
                    {"date": "2025-12-23", "cost": 100.0},
                    {"date": "2025-12-24", "cost": 98.0},
                ]
            )
            mock_service.return_value = mock_service_instance

            client = TestClient(app)
            response = client.get(
                "/api/v1/cost/budget/anomaly",
                params={"entity_type": "user", "entity_id": "user:test"},
            )

            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_anomaly_detection_detects_spike(self) -> None:
        """
        GIVEN a cost spike
        WHEN calling GET /cost/budget/anomaly
        THEN it should return is_anomaly=True
        """
        app = _create_budget_test_app()

        with (
            patch("mcp_server_langgraph.api.v1.cost.get_anomaly_detector") as mock_detector,
            patch("mcp_server_langgraph.api.v1.cost.get_cost_service") as mock_service,
        ):
            mock_detector_instance = MagicMock()
            mock_detector_instance.detect = AsyncMock(
                return_value=MagicMock(
                    is_anomaly=True,
                    severity="critical",
                    z_score=4.5,
                    mean=Decimal("100.00"),
                    std_dev=Decimal("10.00"),
                    message="Critical anomaly detected",
                )
            )
            mock_detector.return_value = mock_detector_instance

            # Mock the cost service with AsyncMock for async methods
            mock_service_instance = MagicMock()
            mock_service_instance.get_cost_summary = AsyncMock(return_value={"total_cost": 350.00})
            mock_service_instance.get_cost_by_organization = AsyncMock(return_value=[])
            mock_service_instance.get_cost_by_project = AsyncMock(return_value=[])
            mock_service_instance.get_cost_by_team = AsyncMock(return_value=[])
            mock_service_instance.get_history = AsyncMock(
                return_value=[
                    {"date": "2025-12-21", "cost": 95.0},
                    {"date": "2025-12-22", "cost": 105.0},
                    {"date": "2025-12-23", "cost": 100.0},
                    {"date": "2025-12-24", "cost": 98.0},
                    {"date": "2025-12-25", "cost": 350.0},  # Spike!
                ]
            )
            mock_service.return_value = mock_service_instance

            client = TestClient(app)
            response = client.get(
                "/api/v1/cost/budget/anomaly",
                params={"entity_type": "user", "entity_id": "user:test"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["is_anomaly"] is True
            assert data["severity"] == "critical"


@pytest.mark.xdist_group(name="test_budget_forecast_router")
class TestBudgetForecastEndpoint:
    """Tests for GET /cost/budget/forecast endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_get_forecast_returns_200(self) -> None:
        """
        GIVEN a valid forecast request
        WHEN calling GET /cost/budget/forecast
        THEN it should return 200 OK
        """
        app = _create_budget_test_app()

        with (
            patch("mcp_server_langgraph.api.v1.cost.get_forecaster") as mock_forecaster,
            patch("mcp_server_langgraph.api.v1.cost.get_cost_service") as mock_service,
        ):
            mock_forecaster_instance = MagicMock()
            mock_forecaster_instance.forecast_month_end = AsyncMock(
                return_value=MagicMock(
                    projected_total=Decimal("300.00"),
                    confidence_low=Decimal("250.00"),
                    confidence_high=Decimal("350.00"),
                    trend="stable",
                    days_analyzed=10,
                    message="Projected $300 by month end",
                )
            )
            mock_forecaster.return_value = mock_forecaster_instance

            # Mock the cost service with AsyncMock for async methods
            mock_service_instance = MagicMock()
            mock_service_instance.get_cost_summary = AsyncMock(return_value={"total_cost": 100.00})
            mock_service_instance.get_cost_by_organization = AsyncMock(return_value=[])
            mock_service_instance.get_cost_by_project = AsyncMock(return_value=[])
            mock_service_instance.get_cost_by_team = AsyncMock(return_value=[])
            mock_service_instance.get_history = AsyncMock(
                return_value=[{"date": f"2025-12-{15 + i}", "cost": 10.0} for i in range(10)]
            )
            mock_service.return_value = mock_service_instance

            client = TestClient(app)
            response = client.get(
                "/api/v1/cost/budget/forecast",
                params={"entity_type": "user", "entity_id": "user:test"},
            )

            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_forecast_returns_projection_data(self) -> None:
        """
        GIVEN daily cost data
        WHEN calling GET /cost/budget/forecast
        THEN it should return projected total and trend
        """
        app = _create_budget_test_app()

        with (
            patch("mcp_server_langgraph.api.v1.cost.get_forecaster") as mock_forecaster,
            patch("mcp_server_langgraph.api.v1.cost.get_cost_service") as mock_service,
        ):
            mock_forecaster_instance = MagicMock()
            mock_forecaster_instance.forecast_month_end = AsyncMock(
                return_value=MagicMock(
                    projected_total=Decimal("450.00"),
                    confidence_low=Decimal("380.00"),
                    confidence_high=Decimal("520.00"),
                    trend="increasing",
                    days_analyzed=15,
                    message="Projected $450 by month end (increasing trend)",
                )
            )
            mock_forecaster.return_value = mock_forecaster_instance

            # Mock the cost service with AsyncMock for async methods
            mock_service_instance = MagicMock()
            mock_service_instance.get_cost_summary = AsyncMock(return_value={"total_cost": 450.00})
            mock_service_instance.get_cost_by_organization = AsyncMock(return_value=[])
            mock_service_instance.get_cost_by_project = AsyncMock(return_value=[])
            mock_service_instance.get_cost_by_team = AsyncMock(return_value=[])
            # Increasing cost trend data
            mock_service_instance.get_history = AsyncMock(
                return_value=[{"date": f"2025-12-{10 + i}", "cost": float(i * 2)} for i in range(1, 16)]
            )
            mock_service.return_value = mock_service_instance

            client = TestClient(app)
            response = client.get(
                "/api/v1/cost/budget/forecast",
                params={"entity_type": "organization", "entity_id": "organization:acme"},
            )

            assert response.status_code == 200
            data = response.json()
            assert float(data["projected_total"]) == 450.0
            assert data["trend"] == "increasing"
            assert data["days_analyzed"] == 15
