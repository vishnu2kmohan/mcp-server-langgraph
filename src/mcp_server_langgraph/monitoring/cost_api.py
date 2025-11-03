"""
Cost Monitoring API

FastAPI endpoints for retrieving cost data, managing budgets, and exporting reports.

Endpoints:
- GET  /api/cost/summary - Aggregated cost summary
- GET  /api/cost/usage - Detailed usage records
- GET  /api/cost/budget/{budget_id} - Budget status
- POST /api/cost/budget - Create budget
- GET  /api/cost/trends - Time-series cost trends
- GET  /api/cost/export - Export cost data (CSV/JSON)

Example:
    uvicorn mcp_server_langgraph.monitoring.cost_api:app --reload --port 8003
"""

import csv
import io
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query, Response, status
from pydantic import BaseModel, Field

from .budget_monitor import Budget, BudgetPeriod, BudgetStatus, get_budget_monitor
from .cost_tracker import CostAggregator, get_cost_collector

# ==============================================================================
# FastAPI Application
# ==============================================================================

app = FastAPI(
    title="Cost Monitoring API",
    description="LLM cost tracking, budget monitoring, and financial analytics",
    version="1.0.0",
)


# ==============================================================================
# Request/Response Models
# ==============================================================================


class CostSummaryResponse(BaseModel):
    """Cost summary response."""

    period_start: datetime
    period_end: datetime
    total_cost_usd: str  # Decimal as string
    total_tokens: int
    request_count: int
    by_model: Dict[str, str]  # Decimal as string
    by_user: Dict[str, str]  # Decimal as string
    by_feature: Dict[str, str] = Field(default_factory=dict)

    class Config:
        json_encoders = {
            Decimal: str,
            datetime: lambda v: v.isoformat(),
        }


class UsageRecordResponse(BaseModel):
    """Usage record response."""

    timestamp: datetime
    user_id: str
    session_id: str
    model: str
    provider: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost_usd: str
    feature: Optional[str] = None

    class Config:
        json_encoders = {
            Decimal: str,
            datetime: lambda v: v.isoformat(),
        }


class CreateBudgetRequest(BaseModel):
    """Request to create a budget."""

    id: str
    name: str
    limit_usd: str  # Decimal as string
    period: BudgetPeriod
    alert_thresholds: Optional[List[str]] = None  # Decimals as strings


class TrendDataPoint(BaseModel):
    """Single data point in trend series."""

    timestamp: datetime
    value: str  # Decimal as string

    class Config:
        json_encoders = {
            Decimal: str,
            datetime: lambda v: v.isoformat(),
        }


class TrendsResponse(BaseModel):
    """Cost trends response."""

    metric: str
    period: str
    data_points: List[TrendDataPoint]


# ==============================================================================
# Endpoints
# ==============================================================================


@app.get("/")
def root() -> Dict[str, Any]:
    """API information."""
    return {
        "name": "Cost Monitoring API",
        "version": "1.0.0",
        "features": [
            "Real-time cost tracking",
            "Budget monitoring",
            "Multi-dimensional aggregation",
            "Export capabilities",
            "Trend analysis",
        ],
    }


@app.get("/api/cost/summary", response_model=CostSummaryResponse)
async def get_cost_summary(
    period: str = Query("month", description="Time period (day, week, month)"),
    group_by: Optional[str] = Query(None, description="Group by dimension (model, user, feature)"),
) -> CostSummaryResponse:
    """
    Get aggregated cost summary.

    Args:
        period: Time period (day, week, month)
        group_by: Optional grouping dimension

    Returns:
        Aggregated cost summary

    Example:
        GET /api/cost/summary?period=month&group_by=model
    """
    collector = get_cost_collector()
    aggregator = CostAggregator()

    # Get records for period
    records = await collector.get_records(period=period)

    # Calculate totals
    total_cost = sum((r.estimated_cost_usd for r in records), Decimal("0"))
    total_tokens = sum(r.total_tokens for r in records)
    request_count = len(records)

    # Aggregate by dimensions
    record_dicts = [
        {
            "model": r.model,
            "user_id": r.user_id,
            "feature": r.feature,
            "cost": r.estimated_cost_usd,
        }
        for r in records
    ]

    by_model = await aggregator.aggregate_by_model(record_dicts)
    by_user = await aggregator.aggregate_by_user(record_dicts)
    by_feature = await aggregator.aggregate_by_feature(record_dicts)

    # Calculate period dates
    now = datetime.now(timezone.utc)
    if period == "day":
        period_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "week":
        period_start = now - timedelta(days=7)
    else:  # month
        period_start = now - timedelta(days=30)

    return CostSummaryResponse(
        period_start=period_start,
        period_end=now,
        total_cost_usd=str(total_cost),
        total_tokens=total_tokens,
        request_count=request_count,
        by_model={k: str(v) for k, v in by_model.items()},
        by_user={k: str(v) for k, v in by_user.items()},
        by_feature={k: str(v) for k, v in by_feature.items()},
    )


@app.get("/api/cost/usage", response_model=List[UsageRecordResponse])
async def get_usage_records(
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    model: Optional[str] = Query(None, description="Filter by model"),
    start: Optional[datetime] = Query(None, description="Start datetime"),
    end: Optional[datetime] = Query(None, description="End datetime"),
    limit: int = Query(100, description="Max records to return", ge=1, le=1000),
) -> List[UsageRecordResponse]:
    """
    Get detailed usage records.

    Args:
        user_id: Filter by user (optional)
        model: Filter by model (optional)
        start: Start datetime (optional)
        end: End datetime (optional)
        limit: Maximum records

    Returns:
        List of usage records

    Example:
        GET /api/cost/usage?user_id=user123&limit=50
    """
    collector = get_cost_collector()

    # Get records
    records = await collector.get_records(user_id=user_id, model=model)

    # Apply date filters
    if start:
        records = [r for r in records if r.timestamp >= start]
    if end:
        records = [r for r in records if r.timestamp <= end]

    # Limit results
    records = records[:limit]

    return [
        UsageRecordResponse(
            timestamp=r.timestamp,
            user_id=r.user_id,
            session_id=r.session_id,
            model=r.model,
            provider=r.provider,
            prompt_tokens=r.prompt_tokens,
            completion_tokens=r.completion_tokens,
            total_tokens=r.total_tokens,
            estimated_cost_usd=str(r.estimated_cost_usd),
            feature=r.feature,
        )
        for r in records
    ]


@app.get("/api/cost/budget/{budget_id}", response_model=BudgetStatus)
async def get_budget_status(budget_id: str) -> BudgetStatus:
    """
    Get budget status.

    Args:
        budget_id: Budget identifier

    Returns:
        Current budget status with utilization

    Example:
        GET /api/cost/budget/dev_team_monthly
    """
    monitor = get_budget_monitor()
    budget_status = await monitor.get_budget_status(budget_id)

    if not budget_status:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Budget '{budget_id}' not found",
        )

    return budget_status


@app.post("/api/cost/budget", response_model=Budget, status_code=status.HTTP_201_CREATED)
async def create_budget(request: CreateBudgetRequest) -> Budget:
    """
    Create a new budget.

    Args:
        request: Budget creation request

    Returns:
        Created budget

    Example:
        POST /api/cost/budget
        {
            "id": "dev_monthly",
            "name": "Development Team - Monthly",
            "limit_usd": "1000.00",
            "period": "monthly",
            "alert_thresholds": ["0.75", "0.90"]
        }
    """
    monitor = get_budget_monitor()

    # Convert string decimals to Decimal
    limit_usd = Decimal(request.limit_usd)
    alert_thresholds = [Decimal(t) for t in request.alert_thresholds] if request.alert_thresholds else None

    budget = await monitor.create_budget(
        id=request.id,
        name=request.name,
        limit_usd=limit_usd,
        period=request.period,
        alert_thresholds=alert_thresholds,
    )

    return budget


@app.get("/api/cost/trends", response_model=TrendsResponse)
async def get_cost_trends(
    metric: str = Query("total_cost", description="Metric to track (total_cost, token_usage)"),
    period: str = Query("7d", description="Time period (7d, 30d, 90d)"),
) -> TrendsResponse:
    """
    Get cost trends over time.

    Args:
        metric: Metric to track
        period: Time period

    Returns:
        Time-series trend data

    Example:
        GET /api/cost/trends?metric=total_cost&period=30d
    """
    # Mock trend data for now
    # TODO: Implement real trend calculation from time-series data

    now = datetime.now(timezone.utc)
    days = int(period.replace("d", ""))

    data_points = []
    for i in range(days):
        timestamp = now - timedelta(days=days - i)
        # Mock value - replace with actual data
        value = Decimal("10.50") + Decimal(str(i * 0.5))

        data_points.append(
            TrendDataPoint(
                timestamp=timestamp,
                value=str(value),
            )
        )

    return TrendsResponse(
        metric=metric,
        period=period,
        data_points=data_points,
    )


@app.get("/api/cost/export")
async def export_cost_data(
    format: str = Query("csv", description="Export format (csv, json)"),
    period: str = Query("month", description="Time period"),
) -> Response:
    """
    Export cost data.

    Args:
        format: Export format (csv or json)
        period: Time period

    Returns:
        Cost data in requested format

    Example:
        GET /api/cost/export?format=csv&period=month
    """
    collector = get_cost_collector()
    records = await collector.get_records(period=period)

    if format == "csv":
        # Generate CSV
        output = io.StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow(
            [
                "timestamp",
                "user_id",
                "session_id",
                "model",
                "provider",
                "prompt_tokens",
                "completion_tokens",
                "total_tokens",
                "cost_usd",
                "feature",
            ]
        )

        # Data
        for r in records:
            writer.writerow(
                [
                    r.timestamp.isoformat(),
                    r.user_id,
                    r.session_id,
                    r.model,
                    r.provider,
                    r.prompt_tokens,
                    r.completion_tokens,
                    r.total_tokens,
                    str(r.estimated_cost_usd),
                    r.feature or "",
                ]
            )

        csv_content = output.getvalue()
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="cost_export_{period}.csv"'},
        )

    elif format == "json":
        # Generate JSON
        import json

        records_dict = [
            {
                "timestamp": r.timestamp.isoformat(),
                "user_id": r.user_id,
                "session_id": r.session_id,
                "model": r.model,
                "provider": r.provider,
                "prompt_tokens": r.prompt_tokens,
                "completion_tokens": r.completion_tokens,
                "total_tokens": r.total_tokens,
                "cost_usd": str(r.estimated_cost_usd),
                "feature": r.feature,
            }
            for r in records
        ]

        return Response(
            content=json.dumps(records_dict, indent=2),
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="cost_export_{period}.json"'},
        )

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported format: {format}",
        )


# ==============================================================================
# Health Check
# ==============================================================================


@app.get("/health")
def health_check() -> Dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy", "service": "cost-monitoring-api"}


# ==============================================================================
# Run Server
# ==============================================================================

if __name__ == "__main__":
    import uvicorn

    print("=" * 80)
    print("💰 Cost Monitoring API")
    print("=" * 80)
    print("\nStarting server...")
    print("\n📍 Endpoints:")
    print("   • Summary:  GET http://localhost:8003/api/cost/summary")
    print("   • Usage:    GET http://localhost:8003/api/cost/usage")
    print("   • Budget:   GET http://localhost:8003/api/cost/budget/{id}")
    print("   • Create:   POST http://localhost:8003/api/cost/budget")
    print("   • Trends:   GET http://localhost:8003/api/cost/trends")
    print("   • Export:   GET http://localhost:8003/api/cost/export")
    print("   • Docs:     http://localhost:8003/docs")
    print("=" * 80)
    print()

    uvicorn.run(app, host="0.0.0.0", port=8003, reload=True)  # nosec B104
