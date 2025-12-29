"""
Cost Router

Provides cost tracking and analysis under /api/v1/cost/*.

This consolidates cost functionality into a unified API.

Usage:
    GET /api/v1/cost/summary - Get cost summary
    GET /api/v1/cost/by-model - Get cost breakdown by model
    GET /api/v1/cost/history - Get cost history over time
"""

from datetime import datetime
from typing import TYPE_CHECKING, Any, Literal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from mcp_server_langgraph.monitoring.cost_budget import (
        BudgetChecker,
        CostAnomalyDetector,
        CostForecaster,
    )
    from mcp_server_langgraph.monitoring.cost_storage import CostStorageBackend

from mcp_server_langgraph.monitoring.budget_storage import get_budget_storage


cost_router = APIRouter(tags=["cost"])


# Response Models


class CostSummaryResponse(BaseModel):
    """Response model for cost summary."""

    total_cost: float = Field(description="Total cost in USD")
    prompt_tokens: int = Field(description="Total prompt tokens used")
    completion_tokens: int = Field(description="Total completion tokens used")
    total_tokens: int | None = Field(default=None, description="Total tokens used")
    period_start: str | None = Field(default=None, description="Period start date")
    period_end: str | None = Field(default=None, description="Period end date")


class ModelCostResponse(BaseModel):
    """Response model for per-model cost."""

    model: str = Field(description="Model name")
    cost: float = Field(description="Cost in USD")
    requests: int = Field(description="Number of requests")
    prompt_tokens: int | None = Field(default=None, description="Prompt tokens")
    completion_tokens: int | None = Field(default=None, description="Completion tokens")


class DailyCostResponse(BaseModel):
    """Response model for daily cost."""

    date: str = Field(description="Date (YYYY-MM-DD)")
    cost: float = Field(description="Cost in USD")
    requests: int | None = Field(default=None, description="Number of requests")


class CostRecordResponse(BaseModel):
    """Response model for individual cost record."""

    timestamp: str = Field(description="Timestamp (ISO format)")
    user_id: str = Field(description="User identifier")
    session_id: str = Field(description="Session identifier")
    model: str = Field(description="Model name")
    provider: str = Field(description="Provider name")
    prompt_tokens: int = Field(description="Prompt tokens")
    completion_tokens: int = Field(description="Completion tokens")
    total_tokens: int = Field(description="Total tokens")
    estimated_cost_usd: float = Field(description="Estimated cost in USD")
    feature: str | None = Field(default=None, description="Feature tag")
    organization_id: str | None = Field(default=None, description="Organization ID")
    project_id: str | None = Field(default=None, description="Project ID")
    team_id: str | None = Field(default=None, description="Team ID")


class PaginatedCostRecordsResponse(BaseModel):
    """Paginated response for cost records."""

    records: list[CostRecordResponse] = Field(description="List of cost records")
    next_cursor: str | None = Field(default=None, description="Cursor for next page")
    total_count: int | None = Field(default=None, description="Total record count")


class OrganizationCostResponse(BaseModel):
    """Response model for cost grouped by organization."""

    organization_id: str = Field(description="Organization identifier")
    total_cost: float = Field(description="Total cost in USD")
    total_tokens: int = Field(description="Total tokens used")
    request_count: int = Field(description="Number of requests")


class ProjectCostResponse(BaseModel):
    """Response model for cost grouped by project."""

    project_id: str = Field(description="Project identifier")
    organization_id: str | None = Field(default=None, description="Parent organization")
    total_cost: float = Field(description="Total cost in USD")
    total_tokens: int = Field(description="Total tokens used")
    request_count: int = Field(description="Number of requests")


class TeamCostResponse(BaseModel):
    """Response model for cost grouped by team."""

    team_id: str = Field(description="Team identifier")
    organization_id: str | None = Field(default=None, description="Parent organization")
    project_id: str | None = Field(default=None, description="Parent project")
    total_cost: float = Field(description="Total cost in USD")
    total_tokens: int = Field(description="Total tokens used")
    request_count: int = Field(description="Number of requests")


# Service Interface


class CostService:
    """Interface for cost operations. Implemented by CostServiceImpl."""

    async def get_summary(self, start_date: str | None = None, end_date: str | None = None) -> dict[str, Any]:
        """Get cost summary. Returns summary data."""
        raise NotImplementedError

    async def get_by_model(self, start_date: str | None = None, end_date: str | None = None) -> list[dict[str, Any]]:
        """Get cost breakdown by model. Returns per-model data."""
        raise NotImplementedError

    async def get_history(self, start_date: str | None = None, end_date: str | None = None) -> list[dict[str, Any]]:
        """Get cost history over time. Returns time series data."""
        raise NotImplementedError

    async def get_records(
        self,
        cursor: str | None = None,
        limit: int = 50,
        sort_by: str = "timestamp",
        sort_order: str = "desc",
        organization_id: str | None = None,
        project_id: str | None = None,
        team_id: str | None = None,
        user_id: str | None = None,
        model: str | None = None,
        provider: str | None = None,
        session_id: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> dict[str, Any]:
        """Get paginated cost records with optional filters."""
        raise NotImplementedError

    async def get_cost_by_organization(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get cost grouped by organization."""
        raise NotImplementedError

    async def get_cost_by_project(
        self,
        organization_id: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get cost grouped by project."""
        raise NotImplementedError

    async def get_cost_by_team(
        self,
        organization_id: str | None = None,
        project_id: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get cost grouped by team."""
        raise NotImplementedError


class CostServiceImpl(CostService):
    """
    Implementation of CostService that wraps CostStorageBackend.

    Connects the API layer to the cost tracking storage layer.
    Handles date string parsing and Decimal -> float conversion.
    """

    def __init__(self, storage: "CostStorageBackend | None" = None) -> None:
        """
        Initialize with a storage backend.

        Args:
            storage: CostStorageBackend instance. If None, uses factory default.
        """
        self._storage = storage

    @property
    def storage(self) -> "CostStorageBackend":
        """Get the storage backend, lazily initializing if needed."""
        if self._storage is None:
            from mcp_server_langgraph.monitoring.cost_storage_factory import (
                get_cost_storage_backend,
            )

            self._storage = get_cost_storage_backend()
        return self._storage

    def _parse_date(self, date_str: str | None) -> datetime | None:
        """Parse YYYY-MM-DD date string to datetime."""
        if date_str is None:
            return None
        return datetime.strptime(date_str, "%Y-%m-%d")

    async def get_summary(self, start_date: str | None = None, end_date: str | None = None) -> dict[str, Any]:
        """
        Get cost summary from storage.

        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format

        Returns:
            Dict matching CostSummaryResponse fields
        """
        start_dt = self._parse_date(start_date)
        end_dt = self._parse_date(end_date)

        # PostgresCostStorage has get_cost_summary method
        summary = await self.storage.get_cost_summary(start_date=start_dt, end_date=end_dt)

        return {
            "total_cost": float(summary.total_cost),
            "prompt_tokens": summary.total_prompt_tokens,
            "completion_tokens": summary.total_completion_tokens,
            "total_tokens": summary.total_tokens,
            "period_start": summary.period_start.isoformat() if summary.period_start else None,
            "period_end": summary.period_end.isoformat() if summary.period_end else None,
        }

    async def get_by_model(self, start_date: str | None = None, end_date: str | None = None) -> list[dict[str, Any]]:
        """
        Get cost breakdown by model from storage.

        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format

        Returns:
            List of dicts matching ModelCostResponse fields
        """
        start_dt = self._parse_date(start_date)
        end_dt = self._parse_date(end_date)

        # PostgresCostStorage has get_cost_by_model method
        model_costs = await self.storage.get_cost_by_model(start_date=start_dt, end_date=end_dt)

        return [
            {
                "model": mc.model,
                "cost": float(mc.total_cost),
                "requests": mc.request_count,
                "prompt_tokens": mc.total_prompt_tokens,
                "completion_tokens": mc.total_completion_tokens,
            }
            for mc in model_costs
        ]

    async def get_history(self, start_date: str | None = None, end_date: str | None = None) -> list[dict[str, Any]]:
        """
        Get cost history over time from storage.

        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format

        Returns:
            List of dicts matching DailyCostResponse fields
        """
        start_dt = self._parse_date(start_date)
        end_dt = self._parse_date(end_date)

        # PostgresCostStorage has get_cost_history method
        daily_costs = await self.storage.get_cost_history(start_date=start_dt, end_date=end_dt)

        return [
            {
                "date": dc.date.strftime("%Y-%m-%d"),
                "cost": float(dc.total_cost),
                "requests": dc.request_count,
            }
            for dc in daily_costs
        ]

    async def get_records(
        self,
        cursor: str | None = None,
        limit: int = 50,
        sort_by: str = "timestamp",
        sort_order: str = "desc",
        organization_id: str | None = None,
        project_id: str | None = None,
        team_id: str | None = None,
        user_id: str | None = None,
        model: str | None = None,
        provider: str | None = None,
        session_id: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> dict[str, Any]:
        """
        Get paginated cost records with optional filters.

        Supports filtering by organizational hierarchy and other dimensions.

        Returns:
            Dict with records, next_cursor, and total_count
        """
        # Build filters dict
        filters: dict[str, Any] = {}

        if organization_id:
            filters["organization_id"] = organization_id
        if project_id:
            filters["project_id"] = project_id
        if team_id:
            filters["team_id"] = team_id
        if user_id:
            filters["user_id"] = user_id
        if model:
            filters["model"] = model
        if provider:
            filters["provider"] = provider
        if session_id:
            filters["session_id"] = session_id

        # Get records from storage
        records, next_cursor = await self.storage.get_records(
            filters=filters if filters else None,
            cursor=cursor,
            limit=limit,
            sort_by=sort_by,
            sort_order=sort_order,
        )

        return {
            "records": [
                {
                    "timestamp": r.timestamp.isoformat(),
                    "user_id": r.user_id,
                    "session_id": r.session_id,
                    "model": r.model,
                    "provider": r.provider,
                    "prompt_tokens": r.prompt_tokens,
                    "completion_tokens": r.completion_tokens,
                    "total_tokens": r.total_tokens,
                    "estimated_cost_usd": float(r.estimated_cost_usd),
                    "feature": r.feature,
                    "organization_id": r.organization_id,
                    "project_id": r.project_id,
                    "team_id": r.team_id,
                }
                for r in records
            ],
            "next_cursor": next_cursor,
            "total_count": self.storage.total_records,
        }

    async def get_cost_by_organization(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Get cost grouped by organization.

        Uses database-level aggregation for efficiency.
        """
        # Parse date strings to datetime if provided
        start_dt = self._parse_date(start_date) if start_date else None
        end_dt = self._parse_date(end_date) if end_date else None

        # Use storage layer's database-level aggregation
        results = await self.storage.get_cost_by_organization(
            start_date=start_dt,
            end_date=end_dt,
        )

        return [
            {
                "organization_id": r.organization_id,
                "total_cost": float(r.total_cost),
                "total_tokens": r.total_tokens,
                "request_count": r.request_count,
            }
            for r in results
        ]

    async def get_cost_by_project(
        self,
        organization_id: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Get cost grouped by project.

        Uses database-level aggregation for efficiency.
        Optionally filter by organization first.
        """
        # Parse date strings to datetime if provided
        start_dt = self._parse_date(start_date) if start_date else None
        end_dt = self._parse_date(end_date) if end_date else None

        # Use storage layer's database-level aggregation
        results = await self.storage.get_cost_by_project(
            organization_id=organization_id,
            start_date=start_dt,
            end_date=end_dt,
        )

        return [
            {
                "project_id": r.project_id,
                "organization_id": r.organization_id,
                "total_cost": float(r.total_cost),
                "total_tokens": r.total_tokens,
                "request_count": r.request_count,
            }
            for r in results
        ]

    async def get_cost_by_team(
        self,
        organization_id: str | None = None,
        project_id: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Get cost grouped by team.

        Uses database-level aggregation for efficiency.
        Optionally filter by organization and/or project first.
        """
        # Parse date strings to datetime if provided
        start_dt = self._parse_date(start_date) if start_date else None
        end_dt = self._parse_date(end_date) if end_date else None

        # Use storage layer's database-level aggregation
        results = await self.storage.get_cost_by_team(
            organization_id=organization_id,
            project_id=project_id,
            start_date=start_dt,
            end_date=end_dt,
        )

        return [
            {
                "team_id": r.team_id,
                "organization_id": r.organization_id,
                "project_id": r.project_id,
                "total_cost": float(r.total_cost),
                "total_tokens": r.total_tokens,
                "request_count": r.request_count,
            }
            for r in results
        ]


# Service singleton
_cost_service: CostService | None = None


def get_cost_service() -> CostService:
    """Get the cost service instance (returns CostServiceImpl)."""
    global _cost_service
    if _cost_service is None:
        _cost_service = CostServiceImpl()
    return _cost_service


def set_cost_service(service: CostService) -> None:
    """Set the cost service instance (for testing/DI)."""
    global _cost_service
    _cost_service = service


def reset_cost_service() -> None:
    """Reset the cost service singleton (for testing)."""
    global _cost_service
    _cost_service = None


# Endpoints


@cost_router.get("/cost/summary")
async def get_summary(
    start_date: str | None = Query(default=None, description="Start date (YYYY-MM-DD)"),
    end_date: str | None = Query(default=None, description="End date (YYYY-MM-DD)"),
) -> CostSummaryResponse:
    """
    Get cost summary.

    Returns total cost and token usage for the specified period.
    """
    service = get_cost_service()
    summary = await service.get_summary(start_date=start_date, end_date=end_date)

    return CostSummaryResponse(**summary)


@cost_router.get("/cost/by-model")
async def get_by_model(
    start_date: str | None = Query(default=None, description="Start date (YYYY-MM-DD)"),
    end_date: str | None = Query(default=None, description="End date (YYYY-MM-DD)"),
) -> list[ModelCostResponse]:
    """
    Get cost breakdown by model.

    Returns cost and usage for each model used.
    """
    service = get_cost_service()
    by_model = await service.get_by_model(start_date=start_date, end_date=end_date)

    return [ModelCostResponse(**m) for m in by_model]


@cost_router.get("/cost/history")
async def get_history(
    start_date: str | None = Query(default=None, description="Start date (YYYY-MM-DD)"),
    end_date: str | None = Query(default=None, description="End date (YYYY-MM-DD)"),
) -> list[DailyCostResponse]:
    """
    Get cost history over time.

    Returns daily cost data for the specified period.
    """
    service = get_cost_service()
    history = await service.get_history(start_date=start_date, end_date=end_date)

    return [DailyCostResponse(**d) for d in history]


@cost_router.get("/cost/records")
async def get_records(
    cursor: str | None = Query(default=None, description="Pagination cursor"),
    limit: int = Query(default=50, ge=1, le=1000, description="Records per page"),
    sort_by: str = Query(default="timestamp", description="Sort field: timestamp|total_tokens|estimated_cost_usd"),
    sort_order: str = Query(default="desc", description="Sort order: asc|desc"),
    organization_id: str | None = Query(default=None, description="Filter by organization"),
    project_id: str | None = Query(default=None, description="Filter by project"),
    team_id: str | None = Query(default=None, description="Filter by team"),
    user_id: str | None = Query(default=None, description="Filter by user"),
    model: str | None = Query(default=None, description="Filter by model"),
    provider: str | None = Query(default=None, description="Filter by provider"),
    session_id: str | None = Query(default=None, description="Filter by session"),
    start_date: str | None = Query(default=None, description="Start date (YYYY-MM-DD)"),
    end_date: str | None = Query(default=None, description="End date (YYYY-MM-DD)"),
) -> PaginatedCostRecordsResponse:
    """
    Get paginated cost records with filtering.

    Supports filtering by organizational hierarchy and other dimensions.
    Returns paginated results with cursor for next page.
    """
    service = get_cost_service()
    result = await service.get_records(
        cursor=cursor,
        limit=limit,
        sort_by=sort_by,
        sort_order=sort_order,
        organization_id=organization_id,
        project_id=project_id,
        team_id=team_id,
        user_id=user_id,
        model=model,
        provider=provider,
        session_id=session_id,
        start_date=start_date,
        end_date=end_date,
    )

    return PaginatedCostRecordsResponse(
        records=[CostRecordResponse(**r) for r in result["records"]],
        next_cursor=result["next_cursor"],
        total_count=result["total_count"],
    )


@cost_router.get("/cost/summary/by-organization")
async def get_cost_by_organization(
    start_date: str | None = Query(default=None, description="Start date (YYYY-MM-DD)"),
    end_date: str | None = Query(default=None, description="End date (YYYY-MM-DD)"),
) -> list[OrganizationCostResponse]:
    """
    Get cost summary grouped by organization.

    Returns cost aggregated by organization_id.
    """
    service = get_cost_service()
    result = await service.get_cost_by_organization(start_date=start_date, end_date=end_date)

    return [OrganizationCostResponse(**r) for r in result]


@cost_router.get("/cost/summary/by-project")
async def get_cost_by_project(
    organization_id: str | None = Query(default=None, description="Filter by organization"),
    start_date: str | None = Query(default=None, description="Start date (YYYY-MM-DD)"),
    end_date: str | None = Query(default=None, description="End date (YYYY-MM-DD)"),
) -> list[ProjectCostResponse]:
    """
    Get cost summary grouped by project.

    Optionally filter by organization first.
    """
    service = get_cost_service()
    result = await service.get_cost_by_project(
        organization_id=organization_id,
        start_date=start_date,
        end_date=end_date,
    )

    return [ProjectCostResponse(**r) for r in result]


@cost_router.get("/cost/summary/by-team")
async def get_cost_by_team(
    organization_id: str | None = Query(default=None, description="Filter by organization"),
    project_id: str | None = Query(default=None, description="Filter by project"),
    start_date: str | None = Query(default=None, description="Start date (YYYY-MM-DD)"),
    end_date: str | None = Query(default=None, description="End date (YYYY-MM-DD)"),
) -> list[TeamCostResponse]:
    """
    Get cost summary grouped by team.

    Optionally filter by organization and/or project.
    """
    service = get_cost_service()
    result = await service.get_cost_by_team(
        organization_id=organization_id,
        project_id=project_id,
        start_date=start_date,
        end_date=end_date,
    )

    return [TeamCostResponse(**r) for r in result]


# ==============================================================================
# Budget Management Endpoints
# ==============================================================================


class BudgetStatusResponse(BaseModel):
    """Response model for budget status check."""

    status: str = Field(description="Budget status: ok, warning, critical, exceeded")
    percent_used: float = Field(description="Percentage of budget used")
    current_spend: float = Field(description="Current spend in USD")
    remaining: float = Field(description="Remaining budget in USD")
    monthly_limit: float = Field(description="Monthly budget limit in USD")
    entity_type: str = Field(description="Entity type: organization, project, team, user")
    entity_id: str = Field(description="Entity identifier")
    message: str = Field(description="Human-readable status message")


class AnomalyDetectionResponse(BaseModel):
    """Response model for cost anomaly detection."""

    is_anomaly: bool = Field(description="Whether an anomaly was detected")
    severity: str = Field(description="Severity: none, warning, critical")
    z_score: float = Field(description="Z-score (standard deviations from mean)")
    mean: float = Field(description="Historical mean cost")
    std_dev: float = Field(description="Historical standard deviation")
    message: str = Field(description="Human-readable explanation")


class ForecastResponse(BaseModel):
    """Response model for cost forecast."""

    projected_total: float = Field(description="Projected total spend for the period")
    confidence_low: float = Field(description="Lower bound of confidence interval")
    confidence_high: float = Field(description="Upper bound of confidence interval")
    trend: str = Field(description="Trend direction: increasing, decreasing, stable")
    days_analyzed: int = Field(description="Number of days of data analyzed")
    message: str = Field(description="Human-readable forecast summary")


# ==============================================================================
# Budget CRUD Request/Response Models
# ==============================================================================


class BudgetCreateRequest(BaseModel):
    """Request model for creating a budget."""

    entity_type: Literal["organization", "project", "team", "user"] = Field(
        description="Entity type: organization, project, team, user"
    )
    entity_id: str = Field(description="Entity identifier")
    monthly_limit_usd: str = Field(description="Monthly budget limit in USD")
    warning_threshold: float = Field(default=0.80, description="Warning threshold (0.0-1.0)")
    critical_threshold: float = Field(default=1.0, description="Critical threshold (0.0-1.0)")
    name: str | None = Field(default=None, description="Human-readable budget name")
    description: str | None = Field(default=None, description="Budget description")


class BudgetUpdateRequest(BaseModel):
    """Request model for updating a budget."""

    monthly_limit_usd: str | None = Field(default=None, description="Monthly budget limit in USD")
    warning_threshold: float | None = Field(default=None, description="Warning threshold (0.0-1.0)")
    critical_threshold: float | None = Field(default=None, description="Critical threshold (0.0-1.0)")
    name: str | None = Field(default=None, description="Human-readable budget name")
    description: str | None = Field(default=None, description="Budget description")


class BudgetResponse(BaseModel):
    """Response model for a single budget."""

    entity_type: str = Field(description="Entity type")
    entity_id: str = Field(description="Entity identifier")
    monthly_limit_usd: str = Field(description="Monthly budget limit in USD")
    warning_threshold: float = Field(description="Warning threshold")
    critical_threshold: float = Field(description="Critical threshold")
    name: str | None = Field(default=None, description="Budget name")
    description: str | None = Field(default=None, description="Budget description")


class BudgetListResponse(BaseModel):
    """Response model for budget list."""

    budgets: list[BudgetResponse] = Field(description="List of budgets")


def get_budget_checker() -> "BudgetChecker":
    """Get the singleton BudgetChecker instance."""
    from mcp_server_langgraph.monitoring.cost_budget import get_budget_checker as _get

    return _get()


def get_anomaly_detector() -> "CostAnomalyDetector":
    """Get the singleton CostAnomalyDetector instance."""
    from mcp_server_langgraph.monitoring.cost_budget import get_anomaly_detector as _get

    return _get()


def get_forecaster() -> "CostForecaster":
    """Get the singleton CostForecaster instance."""
    from mcp_server_langgraph.monitoring.cost_budget import get_forecaster as _get

    return _get()


@cost_router.get("/cost/budget/status")
async def get_budget_status(
    entity_type: Literal["organization", "project", "team", "user"] = Query(
        ..., description="Entity type: organization, project, team, user"
    ),
    entity_id: str = Query(..., description="Entity identifier"),
) -> BudgetStatusResponse:
    """
    Get budget status for an entity.

    Checks current spend against budget thresholds and returns status.
    """
    from decimal import Decimal

    from mcp_server_langgraph.monitoring.cost_budget import Budget

    # Get current month's spend for the entity
    service = get_cost_service()

    # Calculate current month's date range
    from datetime import datetime

    now = datetime.now()
    month_start = now.replace(day=1).strftime("%Y-%m-%d")
    month_end = now.strftime("%Y-%m-%d")

    # Get total cost for entity this month
    if entity_type == "organization":
        costs = await service.get_cost_by_organization(start_date=month_start, end_date=month_end)
        entity_costs = [c for c in costs if c.get("organization_id") == entity_id]
    elif entity_type == "project":
        costs = await service.get_cost_by_project(start_date=month_start, end_date=month_end)
        entity_costs = [c for c in costs if c.get("project_id") == entity_id]
    elif entity_type == "team":
        costs = await service.get_cost_by_team(start_date=month_start, end_date=month_end)
        entity_costs = [c for c in costs if c.get("team_id") == entity_id]
    else:
        # Default: user level, use summary endpoint
        summary = await service.get_summary()
        entity_costs = [{"total_cost": summary.get("total_cost", 0)}]

    current_spend = Decimal(str(sum(c.get("total_cost", 0) for c in entity_costs)))

    # Load budget from storage, fall back to default if not found
    storage = get_budget_storage()
    stored_budget = await storage.get_budget(
        entity_type=entity_type,
        entity_id=entity_id,
    )

    if stored_budget is not None:
        budget = stored_budget
    else:
        # Fall back to default budget for new entities
        budget = Budget(
            entity_type=entity_type,
            entity_id=entity_id,
            monthly_limit_usd=Decimal("1000.00"),  # Default limit
        )

    # Check budget status
    checker = get_budget_checker()
    status = await checker.check(budget, current_spend)

    return BudgetStatusResponse(
        status=status.status,
        percent_used=status.percent_used,
        current_spend=float(status.current_spend),
        remaining=float(status.remaining),
        monthly_limit=float(budget.monthly_limit_usd),
        entity_type=entity_type,
        entity_id=entity_id,
        message=status.message,
    )


@cost_router.get("/cost/budget/anomaly")
async def detect_cost_anomaly(
    entity_type: Literal["organization", "project", "team", "user"] = Query(
        ..., description="Entity type: organization, project, team, user"
    ),
    entity_id: str = Query(..., description="Entity identifier"),
    days: int = Query(7, ge=3, le=30, description="Days of history to analyze"),
) -> AnomalyDetectionResponse:
    """
    Detect cost anomalies for an entity.

    Uses statistical methods (Z-score) to identify unusual spending patterns
    compared to historical data.
    """
    from decimal import Decimal
    from datetime import datetime, timedelta

    # Get historical daily costs
    service = get_cost_service()

    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    history = await service.get_history(
        start_date=start_date.strftime("%Y-%m-%d"),
        end_date=end_date.strftime("%Y-%m-%d"),
    )

    # Get historical values and current value
    historical_values = [Decimal(str(h.get("cost", 0))) for h in history[:-1]]
    current_value = Decimal(str(history[-1].get("cost", 0))) if history else Decimal("0")

    # Detect anomaly
    detector = get_anomaly_detector()
    result = await detector.detect(current_value, historical_values)

    return AnomalyDetectionResponse(
        is_anomaly=result.is_anomaly,
        severity=result.severity,
        z_score=result.z_score,
        mean=float(result.mean),
        std_dev=float(result.std_dev),
        message=result.message,
    )


@cost_router.get("/cost/budget/forecast")
async def get_cost_forecast(
    entity_type: Literal["organization", "project", "team", "user"] = Query(
        ..., description="Entity type: organization, project, team, user"
    ),
    entity_id: str = Query(..., description="Entity identifier"),
) -> ForecastResponse:
    """
    Get cost forecast for an entity.

    Projects end-of-month spend based on current usage trends.
    """
    from decimal import Decimal
    from datetime import datetime
    import calendar

    now = datetime.now()
    days_in_month = calendar.monthrange(now.year, now.month)[1]

    # Get daily costs for current month
    service = get_cost_service()
    month_start = now.replace(day=1).strftime("%Y-%m-%d")
    today = now.strftime("%Y-%m-%d")

    history = await service.get_history(
        start_date=month_start,
        end_date=today,
    )

    daily_values = [Decimal(str(h.get("cost", 0))) for h in history]

    # Get forecast
    forecaster = get_forecaster()
    forecast = await forecaster.forecast_month_end(daily_values, days_in_month)

    return ForecastResponse(
        projected_total=float(forecast.projected_total),
        confidence_low=float(forecast.confidence_low),
        confidence_high=float(forecast.confidence_high),
        trend=forecast.trend,
        days_analyzed=forecast.days_analyzed,
        message=forecast.message,
    )


# ==============================================================================
# Budget CRUD Endpoints
# ==============================================================================


@cost_router.get("/cost/budgets")
async def list_budgets(
    entity_type: Literal["organization", "project", "team", "user"] | None = Query(
        default=None, description="Filter by entity type"
    ),
) -> BudgetListResponse:
    """
    List all budgets.

    Optionally filter by entity type.
    """
    storage = get_budget_storage()
    budgets = await storage.list_budgets(entity_type=entity_type)

    return BudgetListResponse(
        budgets=[
            BudgetResponse(
                entity_type=b.entity_type,
                entity_id=b.entity_id,
                monthly_limit_usd=str(b.monthly_limit_usd),
                warning_threshold=b.warning_threshold,
                critical_threshold=b.critical_threshold,
                name=b.name,
                description=b.description,
            )
            for b in budgets
        ]
    )


@cost_router.post("/cost/budgets", status_code=201)
async def create_budget(request: BudgetCreateRequest) -> BudgetResponse:
    """
    Create a new budget.

    Returns 409 Conflict if a budget already exists for the entity.
    """
    from decimal import Decimal

    from mcp_server_langgraph.monitoring.cost_budget import Budget

    storage = get_budget_storage()

    # Check if budget already exists
    existing = await storage.get_budget(
        entity_type=request.entity_type,
        entity_id=request.entity_id,
    )
    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail=f"Budget already exists for {request.entity_type}:{request.entity_id}",
        )

    # Create and save budget
    budget = Budget(
        entity_type=request.entity_type,
        entity_id=request.entity_id,
        monthly_limit_usd=Decimal(request.monthly_limit_usd),
        warning_threshold=request.warning_threshold,
        critical_threshold=request.critical_threshold,
        name=request.name,
        description=request.description,
    )
    await storage.save_budget(budget)

    return BudgetResponse(
        entity_type=budget.entity_type,
        entity_id=budget.entity_id,
        monthly_limit_usd=str(budget.monthly_limit_usd),
        warning_threshold=budget.warning_threshold,
        critical_threshold=budget.critical_threshold,
        name=budget.name,
        description=budget.description,
    )


@cost_router.put("/cost/budgets/{entity_type}/{entity_id}")
async def update_budget(
    entity_type: Literal["organization", "project", "team", "user"],
    entity_id: str,
    request: BudgetUpdateRequest,
) -> BudgetResponse:
    """
    Update an existing budget.

    Returns 404 Not Found if the budget doesn't exist.
    """
    from decimal import Decimal

    storage = get_budget_storage()

    # Get existing budget
    existing = await storage.get_budget(
        entity_type=entity_type,
        entity_id=entity_id,
    )
    if existing is None:
        raise HTTPException(
            status_code=404,
            detail=f"Budget not found for {entity_type}:{entity_id}",
        )

    # Update fields
    if request.monthly_limit_usd is not None:
        existing.monthly_limit_usd = Decimal(request.monthly_limit_usd)
    if request.warning_threshold is not None:
        existing.warning_threshold = request.warning_threshold
    if request.critical_threshold is not None:
        existing.critical_threshold = request.critical_threshold
    if request.name is not None:
        existing.name = request.name
    if request.description is not None:
        existing.description = request.description

    await storage.save_budget(existing)

    return BudgetResponse(
        entity_type=existing.entity_type,
        entity_id=existing.entity_id,
        monthly_limit_usd=str(existing.monthly_limit_usd),
        warning_threshold=existing.warning_threshold,
        critical_threshold=existing.critical_threshold,
        name=existing.name,
        description=existing.description,
    )


@cost_router.delete("/cost/budgets/{entity_type}/{entity_id}", status_code=204)
async def delete_budget(
    entity_type: Literal["organization", "project", "team", "user"],
    entity_id: str,
) -> None:
    """
    Delete a budget.

    Returns 404 Not Found if the budget doesn't exist.
    """
    storage = get_budget_storage()
    deleted = await storage.delete_budget(
        entity_type=entity_type,
        entity_id=entity_id,
    )

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail=f"Budget not found for {entity_type}:{entity_id}",
        )
