"""
Filtering Helpers

Provides standardized filtering parameters and utilities for API endpoints.

Usage:
    from mcp_server_langgraph.api.filtering import FilterParams, apply_filters

    @router.get("/items")
    async def list_items(
        status: str | None = Query(default=None),
        user_id: str | None = Query(default=None),
    ):
        params = FilterParams(status=status, user_id=user_id)
        items = await get_items()
        return apply_filters(items, params)
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class FilterParams(BaseModel):
    """Common filter parameters for API endpoints."""

    status: str | None = Field(default=None, description="Filter by status")
    user_id: str | None = Field(default=None, description="Filter by user ID")
    workflow_id: str | None = Field(default=None, description="Filter by workflow ID")
    name: str | None = Field(default=None, description="Filter by name (partial match)")

    def get_active_filters(self) -> dict[str, Any]:
        """Get only the filters that have values."""
        return {k: v for k, v in self.model_dump().items() if v is not None}


def apply_filters(
    items: list[dict[str, Any]],
    params: FilterParams,
) -> list[dict[str, Any]]:
    """
    Apply filters to a list of items.

    Args:
        items: List of dictionaries to filter
        params: Filter parameters

    Returns:
        Filtered list of items
    """
    if not items:
        return items

    # Get active filters
    active_filters = params.get_active_filters()
    if not active_filters:
        return items

    # Apply each filter
    filtered_items = items
    for field, value in active_filters.items():
        if field == "name":
            # Partial match for name field
            filtered_items = [item for item in filtered_items if value.lower() in str(item.get(field, "")).lower()]
        else:
            # Exact match for other fields
            filtered_items = [item for item in filtered_items if item.get(field) == value]

    return filtered_items
