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
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from mcp_server_langgraph.monitoring.cost_storage import CostStorageBackend


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
