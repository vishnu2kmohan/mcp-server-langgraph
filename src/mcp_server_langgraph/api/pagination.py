"""
Standardized Pagination Models

Provides consistent pagination across all list endpoints for production-grade APIs.

Supports both offset-based and cursor-based pagination:
- Offset-based: Traditional page/page_size pagination
- Cursor-based: Efficient pagination for large datasets using opaque cursors

Usage (Offset-based):
    ```python
    from mcp_server_langgraph.api.pagination import PaginationParams, PaginatedResponse

    @router.get("/items", response_model=PaginatedResponse[Item])
    async def list_items(pagination: PaginationParams = Depends()):
        items = await db.query().offset(pagination.offset).limit(pagination.limit).all()
        total = await db.query().count()

        return create_paginated_response(
            data=items,
            total=total,
            page=pagination.page,
            page_size=pagination.page_size
        )
    ```

Usage (Cursor-based):
    ```python
    from mcp_server_langgraph.api.pagination import (
        CursorPaginationParams,
        CursorPaginatedResponse,
        create_cursor_paginated_response,
        generate_link_header,
    )

    @router.get("/items", response_model=CursorPaginatedResponse[Item])
    async def list_items(
        pagination: CursorPaginationParams = Depends(),
        response: Response,
    ):
        cursor_data = pagination.decode_cursor()
        items = await db.query_after_cursor(cursor_data, limit=pagination.limit + 1)
        has_more = len(items) > pagination.limit
        items = items[:pagination.limit]

        result = create_cursor_paginated_response(
            data=items,
            limit=pagination.limit,
            has_more=has_more,
            cursor_field="id",
        )

        # Add RFC 5988 Link header
        link = generate_link_header(str(request.url), result.pagination)
        if link:
            response.headers["Link"] = link

        return result
    ```
"""

import base64
import json
import math
from datetime import datetime
from typing import Any, Generic, Literal, TypeVar, cast
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

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


# ==============================================================================
# Cursor-Based Pagination
# ==============================================================================
# Cursor-based pagination is more efficient for large datasets as it avoids
# OFFSET scanning. The cursor encodes the position in the result set.


class CursorPaginationParams(BaseModel):
    """
    Cursor-based pagination parameters for list endpoints.

    Cursor-based pagination is efficient for large datasets because:
    - No OFFSET scanning (constant time for any position)
    - Stable results even when data changes
    - Works well with indexed columns

    The cursor is an opaque base64-encoded string containing the position data.
    """

    cursor: str | None = Field(
        default=None,
        description="Opaque cursor from previous response (base64-encoded)",
        examples=["eyJpZCI6Iml0ZW0tMTAwIn0="],
    )
    limit: int = Field(
        default=20,
        ge=1,
        description="Maximum number of items to return (max: 1000, values above are capped)",
        examples=[20, 50, 100],
    )
    direction: Literal["forward", "backward"] = Field(
        default="forward",
        description="Pagination direction (forward or backward)",
    )

    @field_validator("limit")
    @classmethod
    def limit_max(cls, v: int) -> int:
        """Enforce maximum limit to prevent excessive queries."""
        if v > 1000:
            return 1000
        return v

    def decode_cursor(self) -> dict[str, Any] | None:
        """
        Decode the cursor string to its original dictionary form.

        Returns:
            Decoded cursor data or None if no cursor provided.
        """
        if self.cursor is None:
            return None
        return decode_cursor(self.cursor)

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"cursor": None, "limit": 20, "direction": "forward"},
                {"cursor": "eyJpZCI6Iml0ZW0tMTAwIn0=", "limit": 50, "direction": "forward"},
            ]
        }
    }


class CursorPaginationMetadata(BaseModel):
    """
    Cursor-based pagination metadata included in responses.

    Provides cursors for navigating to next/previous pages.
    """

    next_cursor: str | None = Field(
        default=None,
        description="Cursor for the next page (None if on last page)",
    )
    prev_cursor: str | None = Field(
        default=None,
        description="Cursor for the previous page (None if on first page)",
    )
    has_next: bool = Field(description="Whether there is a next page")
    has_prev: bool = Field(description="Whether there is a previous page")
    count: int = Field(ge=0, description="Number of items in current page")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "next_cursor": "eyJpZCI6Iml0ZW0tMjAifQ==",
                    "prev_cursor": None,
                    "has_next": True,
                    "has_prev": False,
                    "count": 20,
                }
            ]
        }
    }


class CursorPaginatedResponse(BaseModel, Generic[T]):
    """
    Standardized cursor-paginated response wrapper.

    Generic type allows type-safe responses for any data type.
    """

    data: list[T] = Field(description="Array of items for the current page")
    pagination: CursorPaginationMetadata = Field(description="Cursor pagination metadata")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "data": [{"id": "1", "name": "Item 1"}, {"id": "2", "name": "Item 2"}],
                    "pagination": {
                        "next_cursor": "eyJpZCI6IjIifQ==",
                        "prev_cursor": None,
                        "has_next": True,
                        "has_prev": False,
                        "count": 2,
                    },
                }
            ]
        }
    }


def encode_cursor(data: dict[str, Any]) -> str:
    """
    Encode cursor data to a base64 string.

    Args:
        data: Dictionary containing cursor position data.

    Returns:
        Base64-encoded cursor string.

    Example:
        >>> encode_cursor({"id": "item-123"})
        'eyJpZCI6Iml0ZW0tMTIzIn0='
    """

    def json_serializer(obj: Any) -> str:
        """Custom JSON serializer for datetime objects."""
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

    json_str = json.dumps(data, default=json_serializer)
    return base64.urlsafe_b64encode(json_str.encode()).decode()


def decode_cursor(cursor: str | None) -> dict[str, Any] | None:
    """
    Decode a base64 cursor string to its original dictionary form.

    Args:
        cursor: Base64-encoded cursor string or None.

    Returns:
        Decoded dictionary or None if cursor is None.

    Raises:
        ValueError: If the cursor is malformed.

    Example:
        >>> decode_cursor('eyJpZCI6Iml0ZW0tMTIzIn0=')
        {'id': 'item-123'}
    """
    if cursor is None:
        return None

    try:
        json_str = base64.urlsafe_b64decode(cursor).decode()
        return cast(dict[str, Any], json.loads(json_str))
    except (ValueError, json.JSONDecodeError) as e:
        raise ValueError(f"Invalid cursor: {e}") from e


def create_cursor_paginated_response(
    data: list[Any],
    limit: int,
    has_more: bool,
    cursor_field: str,
    prev_cursor_data: dict[str, Any] | None = None,
) -> CursorPaginatedResponse[Any]:
    """
    Helper function to create cursor-paginated responses.

    Args:
        data: List of items for current page (as dicts or Pydantic models).
        limit: The limit that was used for the query.
        has_more: Whether there are more items after this page.
        cursor_field: The field name to use for cursor generation.
        prev_cursor_data: Optional cursor data for the previous page.

    Returns:
        CursorPaginatedResponse with data and cursor metadata.

    Example:
        ```python
        items = await db.query_after_cursor(cursor, limit=limit + 1)
        has_more = len(items) > limit
        items = items[:limit]

        return create_cursor_paginated_response(
            data=items,
            limit=limit,
            has_more=has_more,
            cursor_field="id",
        )
        ```
    """
    # Generate next cursor from last item
    next_cursor = None
    if has_more and data:
        last_item = data[-1]
        # Handle both dict and Pydantic model
        if hasattr(last_item, "model_dump"):
            last_item = last_item.model_dump()
        elif hasattr(last_item, "__dict__"):
            last_item = dict(last_item.__dict__)

        if cursor_field in last_item:
            next_cursor = encode_cursor({cursor_field: last_item[cursor_field]})

    # Generate prev cursor
    prev_cursor = None
    if prev_cursor_data:
        prev_cursor = encode_cursor(prev_cursor_data)

    metadata = CursorPaginationMetadata(
        next_cursor=next_cursor,
        prev_cursor=prev_cursor,
        has_next=has_more,
        has_prev=prev_cursor_data is not None,
        count=len(data),
    )

    return CursorPaginatedResponse(data=data, pagination=metadata)


def generate_link_header(base_url: str, metadata: CursorPaginationMetadata) -> str:
    """
    Generate RFC 5988 Link header for cursor pagination.

    Args:
        base_url: The base URL for the endpoint (may include query params).
        metadata: Cursor pagination metadata.

    Returns:
        RFC 5988 compliant Link header string, or empty string if no links.

    Example:
        >>> metadata = CursorPaginationMetadata(next_cursor="abc", ...)
        >>> generate_link_header("https://api.example.com/items", metadata)
        '<https://api.example.com/items?cursor=abc>; rel="next"'
    """
    links = []

    def build_url(cursor: str) -> str:
        """Build URL with cursor parameter, preserving existing query params."""
        parsed = urlparse(base_url)
        query_params = parse_qs(parsed.query)
        query_params["cursor"] = [cursor]
        new_query = urlencode(query_params, doseq=True)
        return urlunparse(parsed._replace(query=new_query))

    if metadata.has_next and metadata.next_cursor:
        url = build_url(metadata.next_cursor)
        links.append(f'<{url}>; rel="next"')

    if metadata.has_prev and metadata.prev_cursor:
        url = build_url(metadata.prev_cursor)
        links.append(f'<{url}>; rel="prev"')

    return ", ".join(links)
