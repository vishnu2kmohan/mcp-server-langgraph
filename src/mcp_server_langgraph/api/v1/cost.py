"""
Cost Router

Provides cost tracking and analysis under /api/v1/cost/*.

This consolidates cost functionality into a unified API.

Usage:
    GET /api/v1/cost/summary - Get cost summary
    GET /api/v1/cost/by-model - Get cost breakdown by model
    GET /api/v1/cost/history - Get cost history over time
"""

from typing import Any

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field


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
    """Interface for cost operations. Implemented by monitoring layer."""

    async def get_summary(self, start_date: str | None = None, end_date: str | None = None) -> dict[str, Any]:
        """Get cost summary. Returns summary data."""
        raise NotImplementedError

    async def get_by_model(self, start_date: str | None = None, end_date: str | None = None) -> list[dict[str, Any]]:
        """Get cost breakdown by model. Returns per-model data."""
        raise NotImplementedError

    async def get_history(self, start_date: str | None = None, end_date: str | None = None) -> list[dict[str, Any]]:
        """Get cost history over time. Returns time series data."""
        raise NotImplementedError


# Service singleton
_cost_service: CostService | None = None


def get_cost_service() -> CostService:
    """Get the cost service instance."""
    global _cost_service
    if _cost_service is None:
        _cost_service = CostService()
    return _cost_service


def set_cost_service(service: CostService) -> None:
    """Set the cost service instance (for testing/DI)."""
    global _cost_service
    _cost_service = service


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
