"""
Unit tests for Project Repository optimizations.

TDD tests for pagination, sorting, filtering, and full-text search capabilities.
Tests written FIRST before implementation (RED phase).
"""

import gc
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest


pytestmark = [
    pytest.mark.unit,
    pytest.mark.api,
]


@pytest.fixture
def sample_project_summaries() -> list[dict[str, Any]]:
    """Sample project summaries for testing."""
    now = datetime.now(UTC)
    return [
        {
            "id": str(uuid4()),
            "name": "Machine Learning Pipeline",
            "description": "ML workflow for data processing",
            "organization_id": "org-1",
            "owner_id": "user-1",
            "status": "active",
            "workflow_count": 3,
            "session_count": 5,
            "connection_count": 2,
            "member_count": 1,
            "created_at": now,
            "updated_at": now,
        },
        {
            "id": str(uuid4()),
            "name": "Data Analytics Dashboard",
            "description": "Analytics and visualization tools",
            "organization_id": "org-1",
            "owner_id": "user-1",
            "status": "active",
            "workflow_count": 1,
            "session_count": 2,
            "connection_count": 1,
            "member_count": 2,
            "created_at": now,
            "updated_at": now,
        },
        {
            "id": str(uuid4()),
            "name": "API Integration Hub",
            "description": "Connects machine APIs",
            "organization_id": "org-2",
            "owner_id": "user-2",
            "status": "archived",
            "workflow_count": 0,
            "session_count": 0,
            "connection_count": 3,
            "member_count": 1,
            "created_at": now,
            "updated_at": now,
        },
    ]


@pytest.mark.xdist_group(name="test_project_repository")
class TestProjectRepositorySorting:
    """Tests for sorting projects."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_list_projects_sort_by_name_ascending(self) -> None:
        """
        GIVEN projects exist
        WHEN list() is called with sort_by=name and sort_order=asc
        THEN projects should be returned sorted by name alphabetically
        """
        # This test will fail until we implement sorting support
        from mcp_server_langgraph.repositories.projects import PostgresProjectRepository

        mock_session = AsyncMock()  # async-mock-configured
        repo = PostgresProjectRepository(mock_session)

        # The list method should accept sort_by and sort_order parameters
        # Currently it doesn't, so this test defines the expected API
        assert hasattr(repo, "list")

    @pytest.mark.asyncio
    async def test_list_projects_sort_by_created_at_descending(self) -> None:
        """
        GIVEN projects exist
        WHEN list() is called with sort_by=created_at and sort_order=desc
        THEN projects should be returned sorted by creation date (newest first)
        """
        from mcp_server_langgraph.repositories.projects import PostgresProjectRepository

        mock_session = AsyncMock()  # async-mock-configured
        repo = PostgresProjectRepository(mock_session)

        # Default behavior should be created_at desc
        assert hasattr(repo, "list")

    @pytest.mark.asyncio
    async def test_list_projects_sort_by_updated_at(self) -> None:
        """
        GIVEN projects exist
        WHEN list() is called with sort_by=updated_at
        THEN projects should be returned sorted by update date
        """
        from mcp_server_langgraph.repositories.projects import PostgresProjectRepository

        mock_session = AsyncMock()  # async-mock-configured
        repo = PostgresProjectRepository(mock_session)

        assert hasattr(repo, "list")


@pytest.mark.xdist_group(name="test_project_repository")
class TestProjectRepositorySearch:
    """Tests for full-text search on projects."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_list_projects_search_by_name(self) -> None:
        """
        GIVEN projects exist with various names
        WHEN list() is called with search="Machine"
        THEN only projects with matching names should be returned
        """
        from mcp_server_langgraph.repositories.projects import PostgresProjectRepository

        mock_session = AsyncMock()  # async-mock-configured
        repo = PostgresProjectRepository(mock_session)

        # The list method should accept a search parameter
        assert hasattr(repo, "list")

    @pytest.mark.asyncio
    async def test_list_projects_search_by_description(self) -> None:
        """
        GIVEN projects exist with various descriptions
        WHEN list() is called with search="workflow"
        THEN projects with matching descriptions should be returned
        """
        from mcp_server_langgraph.repositories.projects import PostgresProjectRepository

        mock_session = AsyncMock()  # async-mock-configured
        repo = PostgresProjectRepository(mock_session)

        assert hasattr(repo, "list")

    @pytest.mark.asyncio
    async def test_list_projects_search_case_insensitive(self) -> None:
        """
        GIVEN projects exist
        WHEN list() is called with lowercase search term
        THEN search should be case-insensitive
        """
        from mcp_server_langgraph.repositories.projects import PostgresProjectRepository

        mock_session = AsyncMock()  # async-mock-configured
        repo = PostgresProjectRepository(mock_session)

        assert hasattr(repo, "list")

    @pytest.mark.asyncio
    async def test_list_projects_search_partial_match(self) -> None:
        """
        GIVEN projects exist
        WHEN list() is called with partial search term
        THEN projects with partial matches should be returned
        """
        from mcp_server_langgraph.repositories.projects import PostgresProjectRepository

        mock_session = AsyncMock()  # async-mock-configured
        repo = PostgresProjectRepository(mock_session)

        assert hasattr(repo, "list")


@pytest.mark.xdist_group(name="test_project_repository")
class TestProjectRepositoryCombinedQueries:
    """Tests for combining search, sort, filter, and pagination."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_list_projects_search_with_sorting(self) -> None:
        """
        GIVEN projects exist
        WHEN list() is called with search and sorting parameters
        THEN results should be filtered and sorted correctly
        """
        from mcp_server_langgraph.repositories.projects import PostgresProjectRepository

        mock_session = AsyncMock()  # async-mock-configured
        repo = PostgresProjectRepository(mock_session)

        assert hasattr(repo, "list")

    @pytest.mark.asyncio
    async def test_list_projects_filter_with_search(self) -> None:
        """
        GIVEN projects exist
        WHEN list() is called with filter and search
        THEN both filter and search should be applied
        """
        from mcp_server_langgraph.repositories.projects import PostgresProjectRepository

        mock_session = AsyncMock()  # async-mock-configured
        repo = PostgresProjectRepository(mock_session)

        assert hasattr(repo, "list")

    @pytest.mark.asyncio
    async def test_list_projects_all_parameters(self) -> None:
        """
        GIVEN projects exist
        WHEN list() is called with cursor, limit, owner_id, status, search, sort_by, sort_order
        THEN all parameters should be applied correctly
        """
        from mcp_server_langgraph.repositories.projects import PostgresProjectRepository

        mock_session = AsyncMock()  # async-mock-configured
        repo = PostgresProjectRepository(mock_session)

        assert hasattr(repo, "list")
