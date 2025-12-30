"""
Project Connection DELETE Endpoint Tests

TDD tests for DELETE /{project_id}/connections/{connection_id} endpoint.

Requirements:
- Remove a connection from a project (does not delete the connection itself)
- Returns 204 No Content on success
- Returns 404 if project not found
- Idempotent: Returns 204 even if connection not in project
"""

import gc

import pytest
from unittest.mock import AsyncMock, MagicMock

from fastapi import status

from mcp_server_langgraph.api.v1.projects import projects_router

# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="test_remove_connection_from_project")
class TestRemoveConnectionFromProject:
    """Tests for DELETE /{project_id}/connections/{connection_id} endpoint."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.fixture
    def mock_repo(self) -> MagicMock:
        """Create a mock ProjectRepository."""
        repo = MagicMock()
        repo.remove_connection = AsyncMock(return_value=True)
        repo.get = AsyncMock(return_value={"id": "proj-123", "name": "Test"})
        return repo

    @pytest.mark.unit
    def test_remove_connection_endpoint_exists(self) -> None:
        """DELETE /{project_id}/connections/{connection_id} endpoint should exist."""
        # GIVEN the projects router
        # WHEN checking routes (with /projects prefix)
        route_paths = [route.path for route in projects_router.routes]

        # THEN the DELETE connection endpoint should exist
        assert "/projects/{project_id}/connections/{connection_id}" in route_paths

    @pytest.mark.unit
    def test_remove_connection_endpoint_method_is_delete(self) -> None:
        """The endpoint should accept DELETE method."""
        # GIVEN the projects router
        # WHEN finding the connection removal route
        for route in projects_router.routes:
            if hasattr(route, "path") and route.path == "/projects/{project_id}/connections/{connection_id}":
                # THEN it should have DELETE method
                assert "DELETE" in route.methods
                return

        # If we get here, the route doesn't exist
        pytest.fail("DELETE /projects/{project_id}/connections/{connection_id} route not found")

    @pytest.mark.unit
    def test_remove_connection_returns_204_status(self) -> None:
        """The endpoint should return 204 No Content on success."""
        # GIVEN the projects router
        # WHEN finding the connection removal route
        for route in projects_router.routes:
            if hasattr(route, "path") and route.path == "/projects/{project_id}/connections/{connection_id}":
                # THEN status code should be 204
                assert route.status_code == status.HTTP_204_NO_CONTENT
                return

        pytest.fail("DELETE /projects/{project_id}/connections/{connection_id} route not found")


@pytest.mark.xdist_group(name="test_remove_connection_integration")
class TestRemoveConnectionIntegration:
    """Integration-style unit tests for remove connection functionality."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_remove_connection_calls_repository(self) -> None:
        """The endpoint should call repository.remove_connection."""
        from mcp_server_langgraph.api.v1.projects import remove_connection_from_project

        # GIVEN a mock repository and authenticated user with editor access
        mock_repo = MagicMock()
        mock_repo.remove_connection = AsyncMock(return_value=True)
        mock_user = {"sub": "user-123", "user_id": "user-123", "username": "testuser"}

        # WHEN calling the endpoint handler
        await remove_connection_from_project(
            project_id="proj-123",
            connection_id="conn-456",
            user=mock_user,
            repo=mock_repo,
        )

        # THEN repository.remove_connection should be called
        mock_repo.remove_connection.assert_called_once_with("proj-123", "conn-456")

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_remove_connection_success_returns_none(self) -> None:
        """Successful removal should return None (204 response)."""
        from mcp_server_langgraph.api.v1.projects import remove_connection_from_project

        # GIVEN a mock repository that succeeds and authenticated user
        mock_repo = MagicMock()
        mock_repo.remove_connection = AsyncMock(return_value=True)
        mock_user = {"sub": "user-123", "user_id": "user-123", "username": "testuser"}

        # WHEN calling the endpoint handler
        result = await remove_connection_from_project(
            project_id="proj-123",
            connection_id="conn-456",
            user=mock_user,
            repo=mock_repo,
        )

        # THEN result should be None
        assert result is None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_remove_connection_project_not_found_raises_404(self) -> None:
        """Should raise 404 if project not found."""
        from fastapi import HTTPException

        from mcp_server_langgraph.api.v1.projects import remove_connection_from_project

        # GIVEN a mock repository that returns None (not found) and authenticated user
        mock_repo = MagicMock()
        mock_repo.remove_connection = AsyncMock(return_value=None)
        mock_user = {"sub": "user-123", "user_id": "user-123", "username": "testuser"}

        # WHEN calling the endpoint handler
        # THEN should raise HTTPException with 404
        with pytest.raises(HTTPException) as exc_info:
            await remove_connection_from_project(
                project_id="nonexistent-project",
                connection_id="conn-456",
                user=mock_user,
                repo=mock_repo,
            )

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_remove_connection_idempotent(self) -> None:
        """Should return success even if connection not in project (idempotent)."""
        from mcp_server_langgraph.api.v1.projects import remove_connection_from_project

        # GIVEN a mock repository that returns True and authenticated user
        mock_repo = MagicMock()
        mock_repo.remove_connection = AsyncMock(return_value=True)
        mock_user = {"sub": "user-123", "user_id": "user-123", "username": "testuser"}

        # WHEN calling the endpoint handler for a connection not in project
        result = await remove_connection_from_project(
            project_id="proj-123",
            connection_id="not-in-project",
            user=mock_user,
            repo=mock_repo,
        )

        # THEN should succeed (idempotent behavior)
        assert result is None
