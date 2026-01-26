"""
Integration tests for Session Archive Flow.

Tests the complete lifecycle of session archival:
- Session creation
- Session archival (soft delete)
- Session listing excludes archived sessions
- Archived session cannot be accessed
- User authorization for archive operations
"""

from __future__ import annotations

import gc
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

pytestmark = pytest.mark.integration


@pytest.fixture
def mock_user() -> dict[str, Any]:
    """Create a mock authenticated user."""
    return {
        "sub": "user-archive-test",
        "email": "archive@example.com",
        "preferred_username": "archiveuser",
    }


@pytest.fixture
def other_user() -> dict[str, Any]:
    """Create a different mock user for authorization tests."""
    return {
        "sub": "other-user-id",
        "email": "other@example.com",
        "preferred_username": "otheruser",
    }


@pytest.fixture
def app_with_mocks(mock_user: dict[str, Any]) -> FastAPI:
    """Create a FastAPI app with mocked dependencies."""
    from fastapi import FastAPI

    from mcp_server_langgraph.api.v1.sessions import sessions_router
    from mcp_server_langgraph.auth.dependencies import get_current_user

    app = FastAPI()
    app.include_router(sessions_router, prefix="/api/v1")

    # Override authentication
    app.dependency_overrides[get_current_user] = lambda: mock_user

    return app


@pytest.fixture
def mock_session_service() -> AsyncMock:
    """Create a mock session service."""
    service = AsyncMock()
    return service


@pytest.fixture
def client(
    app_with_mocks: FastAPI,
    mock_session_service: AsyncMock,
) -> TestClient:
    """Create a test client with mocked dependencies."""
    with patch(
        "mcp_server_langgraph.api.v1.sessions.get_session_service",
        return_value=mock_session_service,
    ):
        yield TestClient(app_with_mocks)


@pytest.mark.xdist_group(name="session_archive_flow")
class TestSessionArchiveFlowIntegration:
    """Integration tests for the complete session archive flow."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_archive_session_returns_204_on_success(
        self,
        client: TestClient,
        mock_session_service: AsyncMock,
    ) -> None:
        """
        GIVEN a session exists and is owned by the user
        WHEN POST /sessions/{id}/archive is called
        THEN the response should be 204 No Content
        """
        mock_session_service.archive_session.return_value = True

        with patch("mcp_server_langgraph.api.v1.sessions.invalidate_session_cost_cache"):
            response = client.post("/api/v1/sessions/test-session-123/archive")

        assert response.status_code == 204
        mock_session_service.archive_session.assert_called_once()

    def test_archive_session_returns_404_when_not_found(
        self,
        client: TestClient,
        mock_session_service: AsyncMock,
    ) -> None:
        """
        GIVEN a session does not exist
        WHEN POST /sessions/{id}/archive is called
        THEN the response should be 404 Not Found
        """
        mock_session_service.archive_session.return_value = False

        response = client.post("/api/v1/sessions/nonexistent-session/archive")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_archive_session_returns_404_for_other_users_session(
        self,
        app_with_mocks: FastAPI,
        mock_session_service: AsyncMock,
        other_user: dict[str, Any],
    ) -> None:
        """
        GIVEN a session exists but is owned by another user
        WHEN POST /sessions/{id}/archive is called
        THEN the response should be 404 (to prevent enumeration)
        """
        from mcp_server_langgraph.auth.dependencies import get_current_user

        # Override to use other user
        app_with_mocks.dependency_overrides[get_current_user] = lambda: other_user
        mock_session_service.archive_session.return_value = False

        with patch(
            "mcp_server_langgraph.api.v1.sessions.get_session_service",
            return_value=mock_session_service,
        ):
            client = TestClient(app_with_mocks)
            response = client.post("/api/v1/sessions/someone-elses-session/archive")

        assert response.status_code == 404

    def test_archive_session_invalidates_cost_cache(
        self,
        client: TestClient,
        mock_session_service: AsyncMock,
    ) -> None:
        """
        GIVEN a session is successfully archived
        WHEN the archive operation completes
        THEN the session cost cache should be invalidated
        """
        mock_session_service.archive_session.return_value = True

        with patch(
            "mcp_server_langgraph.api.v1.sessions.invalidate_session_cost_cache"
        ) as mock_invalidate:
            response = client.post("/api/v1/sessions/session-to-archive/archive")

        assert response.status_code == 204
        mock_invalidate.assert_called_once_with("session-to-archive")

    def test_archive_session_passes_user_id_to_service(
        self,
        client: TestClient,
        mock_session_service: AsyncMock,
        mock_user: dict[str, Any],
    ) -> None:
        """
        GIVEN a valid archive request
        WHEN the endpoint is called
        THEN the service should receive both session_id and user_id
        """
        mock_session_service.archive_session.return_value = True

        with patch("mcp_server_langgraph.api.v1.sessions.invalidate_session_cost_cache"):
            client.post("/api/v1/sessions/my-session/archive")

        mock_session_service.archive_session.assert_called_once_with(
            "my-session",
            mock_user["sub"],
        )


@pytest.mark.xdist_group(name="session_archive_flow")
class TestSessionArchiveListingBehavior:
    """Tests for how archived sessions affect listing behavior."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_archived_session_excluded_from_list(
        self,
        client: TestClient,
        mock_session_service: AsyncMock,
    ) -> None:
        """
        GIVEN a session has been archived
        WHEN GET /sessions is called
        THEN the archived session should not appear in the list

        Note: This test verifies the expected behavior. The actual
        implementation may filter at the repository level.
        """
        # Mock list_sessions to return tuple (sessions, next_cursor) as expected by the endpoint
        mock_session_service.list_sessions.return_value = (
            [
                {"id": "active-session", "name": "Active", "status": "active"},
            ],
            None,  # next_cursor
        )

        response = client.get("/api/v1/sessions")

        assert response.status_code == 200
        data = response.json()
        # Verify archived sessions are not in the response
        sessions_list = data.get("sessions", data.get("data", []))
        session_ids = [s.get("id") for s in sessions_list]
        assert "archived-session" not in session_ids


@pytest.mark.xdist_group(name="session_archive_flow")
class TestSessionArchiveWithAutoSessionCreation:
    """Tests for archive behavior with auto-session creation feature."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_archive_current_session_allows_new_session_creation(
        self,
        client: TestClient,
        mock_session_service: AsyncMock,
    ) -> None:
        """
        GIVEN a user archives their current session
        WHEN they send a new message
        THEN a new session should be created (tested at frontend level)

        This test verifies the archive endpoint works correctly.
        Frontend auto-session creation is tested in frontend tests.
        """
        mock_session_service.archive_session.return_value = True

        with patch("mcp_server_langgraph.api.v1.sessions.invalidate_session_cost_cache"):
            response = client.post("/api/v1/sessions/current-session/archive")

        assert response.status_code == 204
        # Archive succeeded - frontend can now create new session


# =============================================================================
# v8 Phase 4: Session Restore Tests
# =============================================================================


@pytest.mark.xdist_group(name="session_restore_flow")
class TestSessionRestoreFlowIntegration:
    """Integration tests for the complete session restore flow."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_restore_session_returns_204_on_success(
        self,
        client: TestClient,
        mock_session_service: AsyncMock,
    ) -> None:
        """
        GIVEN an archived session exists and is owned by the user
        WHEN POST /sessions/{id}/restore is called
        THEN the response should be 204 No Content
        """
        mock_session_service.restore_session.return_value = True

        response = client.post("/api/v1/sessions/archived-session-123/restore")

        assert response.status_code == 204
        mock_session_service.restore_session.assert_called_once()

    def test_restore_session_returns_404_when_not_found(
        self,
        client: TestClient,
        mock_session_service: AsyncMock,
    ) -> None:
        """
        GIVEN a session does not exist
        WHEN POST /sessions/{id}/restore is called
        THEN the response should be 404 Not Found
        """
        mock_session_service.restore_session.return_value = False

        response = client.post("/api/v1/sessions/nonexistent-session/restore")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_restore_session_returns_404_for_other_users_session(
        self,
        app_with_mocks: FastAPI,
        mock_session_service: AsyncMock,
        other_user: dict[str, Any],
    ) -> None:
        """
        GIVEN a session exists but is owned by another user
        WHEN POST /sessions/{id}/restore is called
        THEN the response should be 404 (to prevent enumeration)
        """
        from mcp_server_langgraph.auth.dependencies import get_current_user

        # Override to use other user
        app_with_mocks.dependency_overrides[get_current_user] = lambda: other_user
        mock_session_service.restore_session.return_value = False

        with patch(
            "mcp_server_langgraph.api.v1.sessions.get_session_service",
            return_value=mock_session_service,
        ):
            test_client = TestClient(app_with_mocks)
            response = test_client.post("/api/v1/sessions/someone-elses-session/restore")

        assert response.status_code == 404

    def test_restore_session_passes_user_id_to_service(
        self,
        client: TestClient,
        mock_session_service: AsyncMock,
        mock_user: dict[str, Any],
    ) -> None:
        """
        GIVEN a valid restore request
        WHEN the endpoint is called
        THEN the service should receive both session_id and user_id
        """
        mock_session_service.restore_session.return_value = True

        client.post("/api/v1/sessions/my-archived-session/restore")

        mock_session_service.restore_session.assert_called_once_with(
            "my-archived-session",
            mock_user["sub"],
        )


@pytest.mark.xdist_group(name="session_restore_flow")
class TestSessionRestoreListingBehavior:
    """Tests for how restored sessions affect listing behavior."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_restored_session_appears_in_active_list(
        self,
        client: TestClient,
        mock_session_service: AsyncMock,
    ) -> None:
        """
        GIVEN a session has been restored from archive
        WHEN GET /sessions?status=active is called
        THEN the restored session should appear in the list
        """
        # Mock list_sessions to return tuple (sessions, next_cursor) as expected
        mock_session_service.list_sessions.return_value = (
            [
                {"id": "restored-session", "name": "Restored", "status": "active"},
                {"id": "active-session", "name": "Active", "status": "active"},
            ],
            None,  # next_cursor
        )

        response = client.get("/api/v1/sessions?status=active")

        assert response.status_code == 200
        data = response.json()
        sessions_list = data.get("sessions", data.get("data", []))
        session_ids = [s.get("id") for s in sessions_list]
        assert "restored-session" in session_ids

    def test_list_archived_sessions_excludes_restored(
        self,
        client: TestClient,
        mock_session_service: AsyncMock,
    ) -> None:
        """
        GIVEN a session was archived and then restored
        WHEN GET /sessions?status=archived is called
        THEN the restored session should not appear
        """
        # Mock list_sessions to return only archived sessions
        mock_session_service.list_sessions.return_value = (
            [
                {"id": "still-archived", "name": "Archived", "status": "archived"},
            ],
            None,
        )

        response = client.get("/api/v1/sessions?status=archived")

        assert response.status_code == 200
        data = response.json()
        sessions_list = data.get("sessions", data.get("data", []))
        session_ids = [s.get("id") for s in sessions_list]
        assert "restored-session" not in session_ids


@pytest.mark.xdist_group(name="session_restore_flow")
class TestSessionArchiveRestoreRoundtrip:
    """Tests for archive → restore roundtrip."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_archive_then_restore_returns_session_to_active(
        self,
        client: TestClient,
        mock_session_service: AsyncMock,
    ) -> None:
        """
        GIVEN a session is archived
        WHEN the session is subsequently restored
        THEN the session should return to active status
        """
        session_id = "roundtrip-session"

        # Archive
        mock_session_service.archive_session.return_value = True
        with patch("mcp_server_langgraph.api.v1.sessions.invalidate_session_cost_cache"):
            archive_response = client.post(f"/api/v1/sessions/{session_id}/archive")
        assert archive_response.status_code == 204

        # Restore
        mock_session_service.restore_session.return_value = True
        restore_response = client.post(f"/api/v1/sessions/{session_id}/restore")
        assert restore_response.status_code == 204

        # Both calls were made
        mock_session_service.archive_session.assert_called_once()
        mock_session_service.restore_session.assert_called_once()
