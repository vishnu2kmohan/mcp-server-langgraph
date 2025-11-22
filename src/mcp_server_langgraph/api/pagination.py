"""
Standardized Pagination Models

Provides consistent pagination across all list endpoints for production-grade APIs.

Usage:
    ```python
    from mcp_server_langgraph.api.pagination import PaginationParams, PaginatedResponse

    @router.get("/items", response_model=PaginatedResponse[Item])
    async def list_items(pagination: PaginationParams = Depends()):
        # Use pagination.offset and pagination.limit for queries
        items = await db.query().offset(pagination.offset).limit(pagination.limit).all()
        total = await db.query().count()

        return create_paginated_response(
            data=items,
            total=total,
            page=pagination.page,
            page_size=pagination.page_size
        )
    ```
"""

import math
from typing import Generic, TypeVar

from pydantic import BaseModel, Field, computed_field, field_validator

# Generic type for paginated data
T = TypeVar("T")


class PaginationParams(BaseModel):
    """
    Pagination parameters for list endpoints

    Supports both page-based and offset-based pagination:
    - Page-based: page + page_size
    - Offset-based: offset + limit

    Page-based is automatically converted to offset/limit for database queries.
    """

    page: int = Field(default=1, ge=1, description="Page number (1-indexed)", examples=[1, 2, 10])
    page_size: int = Field(
        default=20, ge=1, le=1000, description="Number of items per page (max: 1000)", examples=[20, 50, 100]
    )

    @field_validator("page_size")
    @classmethod
    def limit_page_size(cls, v: int) -> int:
        """Enforce maximum page size to prevent excessive queries"""
        if v > 1000:
            return 1000
        return v

    @computed_field  # type: ignore[prop-decorator]
    @property
    def offset(self) -> int:
        """Calculate offset from page and page_size (for database queries)"""
        return (self.page - 1) * self.page_size

    @computed_field  # type: ignore[prop-decorator]
    @property
    def limit(self) -> int:
        """Alias for page_size (for database queries)"""
        return self.page_size

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"page": 1, "page_size": 20, "offset": 0, "limit": 20},
                {"page": 3, "page_size": 50, "offset": 100, "limit": 50},
            ]
        }
    }


class PaginationMetadata(BaseModel):
    """
    Pagination metadata included in responses

    Provides information for clients to navigate pages.
    """

    total: int = Field(description="Total number of items across all pages", examples=[100, 1000])
    page: int = Field(ge=1, description="Current page number (1-indexed)", examples=[1, 2, 10])
    page_size: int = Field(ge=1, description="Number of items per page", examples=[20, 50, 100])
    total_pages: int = Field(ge=0, description="Total number of pages", examples=[5, 20, 100])

    @computed_field  # type: ignore[prop-decorator]
    @property
    def has_next(self) -> bool:
        """Whether there is a next page"""
        return self.page < self.total_pages

    @computed_field  # type: ignore[prop-decorator]
    @property
    def has_prev(self) -> bool:
        """Whether there is a previous page"""
        return self.page > 1

    @computed_field  # type: ignore[prop-decorator]
    @property
    def next_page(self) -> int | None:
        """Next page number (None if on last page)"""
        return self.page + 1 if self.has_next else None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def prev_page(self) -> int | None:
        """Previous page number (None if on first page)"""
        return self.page - 1 if self.has_prev else None

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "total": 100,
                    "page": 2,
                    "page_size": 20,
                    "total_pages": 5,
                    "has_next": True,
                    "has_prev": True,
                    "next_page": 3,
                    "prev_page": 1,
                }
            ]
        }
    }


class PaginatedResponse(BaseModel, Generic[T]):
    """
    Standardized paginated response wrapper

    Generic type allows type-safe responses for any data type.

    Example:
        PaginatedResponse[APIKeyResponse] for API keys
        PaginatedResponse[UserResponse] for users
    """

    data: list[T] = Field(description="Array of items for the current page")
    pagination: PaginationMetadata = Field(description="Pagination metadata for navigation")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "data": [{"id": "1", "name": "Item 1"}, {"id": "2", "name": "Item 2"}],
                    "pagination": {
                        "total": 100,
                        "page": 1,
                        "page_size": 20,
                        "total_pages": 5,
                        "has_next": True,
                        "has_prev": False,
                        "next_page": 2,
                        "prev_page": None,
                    },
                }
            ]
        }
    }


def create_paginated_response(data: list[T], total: int, page: int, page_size: int) -> PaginatedResponse[T]:
    """
    Helper function to create paginated responses

    Args:
        data: List of items for current page
        total: Total number of items across all pages
        page: Current page number (1-indexed)
        page_size: Number of items per page

    Returns:
        PaginatedResponse with data and pagination metadata

    Example:
        ```python
        items = await db.query().offset(offset).limit(limit).all()
        total = await db.query().count()

        return create_paginated_response(
            data=items,
            total=total,
            page=page,
            page_size=page_size
        )
        ```
    """
    total_pages = math.ceil(total / page_size) if total > 0 else 0

    return PaginatedResponse(
        data=data, pagination=PaginationMetadata(total=total, page=page, page_size=page_size, total_pages=total_pages)
    )
