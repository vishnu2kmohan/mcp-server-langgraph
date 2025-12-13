"""
Sorting Helpers

Provides standardized sorting parameters and utilities for API endpoints.

Usage:
    from mcp_server_langgraph.api.sorting import SortingParams, apply_sorting

    @router.get("/items")
    async def list_items(
        sort_by: str = Query(default="created_at"),
        sort_order: Literal["asc", "desc"] = Query(default="desc"),
    ):
        params = SortingParams(sort_by=sort_by, sort_order=sort_order)
        items = await get_items()
        return apply_sorting(items, params)
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class SortingParams(BaseModel):
    """Parameters for sorting API results."""

    sort_by: str = Field(
        default="created_at",
        description="Field to sort by",
    )
    sort_order: Literal["asc", "desc"] = Field(
        default="desc",
        description="Sort order (asc or desc)",
    )

    def is_ascending(self) -> bool:
        """Check if sort order is ascending."""
        return self.sort_order == "asc"


def apply_sorting(
    items: list[dict[str, Any]],
    params: SortingParams,
) -> list[dict[str, Any]]:
    """
    Apply sorting to a list of items.

    Args:
        items: List of dictionaries to sort
        params: Sorting parameters

    Returns:
        Sorted list of items
    """
    if not items:
        return items

    # Check if sort field exists in items
    sort_field = params.sort_by
    if sort_field not in items[0]:
        # Fall back to not sorting if field doesn't exist
        return items

    # Sort the items
    sorted_items = sorted(
        items,
        key=lambda x: x.get(sort_field) or "",
        reverse=not params.is_ascending(),
    )

    return sorted_items
