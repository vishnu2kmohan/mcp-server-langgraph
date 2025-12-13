"""
Search Helpers

Provides full-text search utilities for PostgreSQL and in-memory implementations.

Features:
- SearchParams: Query parameters with pagination
- SearchResult: Individual result with ranking and highlights
- SearchResponse: Paginated response with metadata
- build_tsquery: PostgreSQL tsquery builder
- highlight_matches: Result highlighting
- in_memory_search: Test/development search implementation

Usage:
    from mcp_server_langgraph.api.search import SearchParams, in_memory_search

    @router.get("/search")
    async def search_items(
        query: str = Query(default=""),
        limit: int = Query(default=20, le=100),
        offset: int = Query(default=0, ge=0),
    ):
        params = SearchParams(query=query, limit=limit, offset=offset)
        results = in_memory_search(items, params)
        return SearchResponse(query=query, results=results, total=len(results))
"""

from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class SearchParams(BaseModel):
    """Parameters for search operations."""

    query: str = Field(default="", description="Search query string")
    entity_type: Literal["workflow", "session", "template", "all"] | None = Field(
        default=None, description="Filter by entity type"
    )
    user_id: str | None = Field(default=None, description="Filter by user ID")
    limit: int = Field(default=20, ge=1, le=100, description="Maximum results to return")
    offset: int = Field(default=0, ge=0, description="Number of results to skip")

    @field_validator("limit", mode="before")
    @classmethod
    def cap_limit(cls, v: Any) -> int:
        """Cap limit at maximum value."""
        if isinstance(v, int):
            return min(v, 100)
        # For non-int values, let Pydantic handle conversion/validation
        return v  # type: ignore[no-any-return]


class SearchResult(BaseModel):
    """Individual search result."""

    id: str = Field(description="Entity ID")
    entity_type: str = Field(description="Type of entity (workflow, session, template)")
    name: str = Field(description="Entity name")
    description: str | None = Field(default=None, description="Entity description")
    rank: float = Field(default=0.0, description="Relevance score (0-1)")
    highlights: dict[str, str] = Field(default_factory=dict, description="Highlighted fields")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class SearchResponse(BaseModel):
    """Paginated search response."""

    query: str = Field(description="Original search query")
    results: list[SearchResult] = Field(default_factory=list, description="Search results")
    total: int = Field(description="Total number of matching results")
    limit: int = Field(description="Results per page")
    offset: int = Field(description="Current offset")

    @property
    def has_more(self) -> bool:
        """Check if there are more results to fetch."""
        return (self.offset + len(self.results)) < self.total


def build_tsquery(query: str) -> str:
    """
    Build a PostgreSQL tsquery string from a user query.

    Converts a user-friendly search query into a PostgreSQL full-text search query.
    Supports:
    - Word splitting into OR terms
    - Prefix matching with :*
    - Special character escaping

    Args:
        query: User's search query

    Returns:
        PostgreSQL tsquery string ready for use with to_tsquery()

    Examples:
        >>> build_tsquery("workflow automation")
        "workflow:* | automation:*"

        >>> build_tsquery("test's query")
        "tests:* | query:*"
    """
    if not query or not query.strip():
        return ""

    # Remove special PostgreSQL tsquery characters and normalize
    # Keep alphanumeric, spaces, and hyphens
    cleaned = re.sub(r"[^\w\s\-]", " ", query)

    # Split into words and filter empty
    words = [w.strip() for w in cleaned.split() if w.strip()]

    if not words:
        return ""

    # Build prefix-matching OR query
    # Each term gets :* for prefix matching
    terms = [f"{word.lower()}:*" for word in words]

    # Join with OR (|) for flexible matching
    return " | ".join(terms)


def highlight_matches(text: str, query: str, tag: str = "mark") -> str:
    """
    Highlight search terms in text.

    Wraps matching terms in HTML tags for display.

    Args:
        text: Original text to highlight
        query: Search query (terms to highlight)
        tag: HTML tag to use for highlighting (default: "mark")

    Returns:
        Text with matching terms wrapped in highlight tags

    Examples:
        >>> highlight_matches("Workflow automation", "workflow")
        "<mark>Workflow</mark> automation"
    """
    if not query or not query.strip():
        return text

    if not text:
        return text

    # Extract words from query
    words = [w.strip() for w in query.split() if w.strip()]

    if not words:
        return text

    result = text
    for word in words:
        if not word:
            continue
        # Case-insensitive replacement with preserved original case
        pattern = re.compile(re.escape(word), re.IGNORECASE)
        result = pattern.sub(lambda m: f"<{tag}>{m.group()}</{tag}>", result)

    return result


def in_memory_search(
    items: list[dict[str, Any]],
    params: SearchParams,
    search_fields: list[str] | None = None,
) -> list[dict[str, Any]]:
    """
    Perform in-memory search on a list of items.

    Provides a simple search implementation for testing and development.
    For production, use PostgreSQL full-text search.

    Args:
        items: List of dictionaries to search
        params: Search parameters
        search_fields: Fields to search in (default: ["name", "description"])

    Returns:
        Filtered and paginated list of matching items

    Examples:
        >>> items = [{"id": "1", "name": "Test", "description": "A test item"}]
        >>> params = SearchParams(query="test")
        >>> in_memory_search(items, params)
        [{"id": "1", "name": "Test", "description": "A test item"}]
    """
    if search_fields is None:
        search_fields = ["name", "description"]

    # If no query, return all items (paginated)
    if not params.query or not params.query.strip():
        start = params.offset
        end = start + params.limit
        return items[start:end]

    query_lower = params.query.lower()
    words = [w.strip() for w in query_lower.split() if w.strip()]

    if not words:
        start = params.offset
        end = start + params.limit
        return items[start:end]

    # Score and filter items
    scored_items: list[tuple[dict[str, Any], float]] = []

    for item in items:
        score = 0.0
        matched = False

        for field in search_fields:
            field_value = str(item.get(field, "")).lower()
            if not field_value:
                continue

            for word in words:
                if word in field_value:
                    matched = True
                    # Name matches are worth more than description matches
                    if field == "name":
                        score += 2.0
                    else:
                        score += 1.0

        if matched:
            scored_items.append((item, score))

    # Sort by score (descending)
    scored_items.sort(key=lambda x: x[1], reverse=True)

    # Extract items without scores
    results = [item for item, _ in scored_items]

    # Apply pagination
    start = params.offset
    end = start + params.limit
    return results[start:end]
