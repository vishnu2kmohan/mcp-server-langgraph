"""
Tests for Admin Router

TDD tests for GET /api/v1/admin/audit-logs endpoint.
This endpoint returns paginated audit log entries for admin users.

PYTEST-XDIST FIX (2025-12-15):
==============================
- Removed module-level import of InMemoryAuditLogRepository to avoid
  triggering database-related imports at test collection time.
- Use plain AsyncMock without spec to avoid import side effects.
- Also override get_db_session dependency to prevent any database connection
  attempts during xdist parallel execution.
- Patch get_session_maker at module level to prevent any connection attempts.
"""

import gc
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# TYPE_CHECKING only imports for IDE/mypy - not at runtime
if TYPE_CHECKING:
    pass

pytestmark = pytest.mark.unit


# NOTE: Database singletons are reset by the central
# reset_dependency_singletons fixture in tests/conftest.py


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_admin_router")
class TestAdminAuditLogsEndpoint:
    """Tests for GET /api/v1/admin/audit-logs endpoint."""

    _session_maker_patcher: patch  # type: ignore[type-arg]

    def setup_method(self) -> None:
        """Reset database singletons and patch session maker before each test."""
        import sys

        # Reset database session singletons to prevent pollution from other tests
        if "mcp_server_langgraph.database.session" in sys.modules:
            import mcp_server_langgraph.database.session as session_module

            session_module._engine = None
            session_module._async_session_maker = None

        # Patch get_session_maker at the source (database.session module) to prevent
        # ANY database connection attempts. This is critical for xdist isolation where
        # other tests may have set DATABASE_URL.
        self._session_maker_patcher = patch(
            "mcp_server_langgraph.database.session.get_session_maker",
            side_effect=lambda *a, **kw: MagicMock(),
        )
        self._session_maker_patcher.start()

    def teardown_method(self) -> None:
        """Force GC and reset singletons to prevent mock accumulation in xdist workers."""
        import sys

        # Stop the session maker patcher
        self._session_maker_patcher.stop()

        # Reset database singletons after each test
        if "mcp_server_langgraph.database.session" in sys.modules:
            import mcp_server_langgraph.database.session as session_module

            session_module._engine = None
            session_module._async_session_maker = None

        gc.collect()

    def _create_mock_repository(self, items: list[dict] | None = None, total: int = 0) -> AsyncMock:
        """Create a mock repository that returns the specified items."""
        # Use plain AsyncMock without spec to avoid importing database-related modules
        mock_repo = AsyncMock(return_value=None)  # async-mock-configured (return_value set below)  # noqa: async-mock-config
        mock_repo.query.return_value = (items or [], total)
        return mock_repo

    def _create_app_and_client(self, mock_repository: AsyncMock) -> TestClient:
        """
        Create a FastAPI app with overridden dependency and return test client.

        PYTEST-XDIST FIX (2025-12-15):
        ==============================
        Use FastAPI's dependency_overrides with the exact same function object
        that the router uses. Import get_audit_log_repository from core.dependencies
        (where admin.py imports it from) to ensure function object identity matches.

        Key insight: FastAPI's Depends() captures the function object at import time.
        We must use the same object as the override key.

        AUTH UPDATE (2025-12-29):
        ========================
        Admin endpoints now require authentication via require_admin dependency.
        We mock this to return an admin user for testing.
        """
        from mcp_server_langgraph.api.v1.admin import admin_router
        from mcp_server_langgraph.auth.dependencies import require_admin
        from mcp_server_langgraph.core.dependencies import get_audit_log_repository

        app = FastAPI()
        app.include_router(admin_router, prefix="/api/v1")

        # Override using the exact same function object from core.dependencies
        # This is the correct approach - FastAPI uses function identity for lookups
        app.dependency_overrides[get_audit_log_repository] = lambda: mock_repository

        # Mock admin authentication - return a mock admin user
        mock_admin_user = {
            "sub": "admin-user-id",
            "user_id": "admin-user-id",
            "username": "admin",
            "roles": ["admin"],
            "realm_access": {"roles": ["admin"]},
        }
        app.dependency_overrides[require_admin] = lambda: mock_admin_user

        return TestClient(app)

    def test_get_audit_logs_returns_200(self) -> None:
        """GET /api/v1/admin/audit-logs should return 200 with paginated data."""
        mock_repo = self._create_mock_repository(items=[], total=0)
        client = self._create_app_and_client(mock_repo)
        response = client.get("/api/v1/admin/audit-logs")

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    def test_get_audit_logs_returns_paginated_response(self) -> None:
        """GET /api/v1/admin/audit-logs should return properly paginated response."""
        # Repository returns data in its schema (actor_id, datetime timestamp)
        mock_logs = [
            {
                "id": "log-1",
                "action": "create",
                "actor_id": "user-123",  # Repository uses actor_id
                "event_type": "create",
                "resource_type": "workflow",
                "resource_id": "wf-456",
                "timestamp": datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC),
                "ip_address": "192.168.1.1",
                "details": {"key": "value"},
            },
            {
                "id": "log-2",
                "action": "update",
                "actor_id": "user-123",
                "event_type": "update",
                "resource_type": "session",
                "resource_id": "sess-789",
                "timestamp": datetime(2024, 1, 15, 11, 0, 0, tzinfo=UTC),
                "ip_address": None,
                "details": None,
            },
        ]

        mock_repo = self._create_mock_repository(items=mock_logs, total=2)
        client = self._create_app_and_client(mock_repo)
        response = client.get("/api/v1/admin/audit-logs")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        assert data["total"] == 2
        assert data["items"][0]["id"] == "log-1"
        assert data["items"][0]["action"] == "create"
        # Verify schema mapping: actor_id -> user_id
        assert data["items"][0]["user_id"] == "user-123"
        assert data["items"][1]["id"] == "log-2"

    def test_get_audit_logs_with_limit_param(self) -> None:
        """GET /api/v1/admin/audit-logs should respect limit parameter."""
        mock_repo = self._create_mock_repository(items=[], total=0)
        client = self._create_app_and_client(mock_repo)
        response = client.get("/api/v1/admin/audit-logs?limit=10")

        assert response.status_code == 200
        mock_repo.query.assert_called_once()
        call_kwargs = mock_repo.query.call_args[1]
        assert call_kwargs.get("limit") == 10

    def test_get_audit_logs_with_cursor_param(self) -> None:
        """GET /api/v1/admin/audit-logs should respect cursor parameter (as offset)."""
        mock_repo = self._create_mock_repository(items=[], total=0)
        client = self._create_app_and_client(mock_repo)
        response = client.get("/api/v1/admin/audit-logs?cursor=10")

        assert response.status_code == 200
        mock_repo.query.assert_called_once()
        call_kwargs = mock_repo.query.call_args[1]
        # Cursor is parsed as offset
        assert call_kwargs.get("offset") == 10

    def test_get_audit_logs_with_user_id_filter(self) -> None:
        """GET /api/v1/admin/audit-logs should filter by user_id (mapped to actor_id)."""
        mock_repo = self._create_mock_repository(items=[], total=0)
        client = self._create_app_and_client(mock_repo)
        response = client.get("/api/v1/admin/audit-logs?user_id=user-123")

        assert response.status_code == 200
        mock_repo.query.assert_called_once()
        call_kwargs = mock_repo.query.call_args[1]
        # API user_id -> repository actor_id
        assert call_kwargs.get("actor_id") == "user-123"

    def test_get_audit_logs_with_action_filter(self) -> None:
        """GET /api/v1/admin/audit-logs should filter by action (mapped to event_type)."""
        mock_repo = self._create_mock_repository(items=[], total=0)
        client = self._create_app_and_client(mock_repo)
        response = client.get("/api/v1/admin/audit-logs?action=delete")

        assert response.status_code == 200
        mock_repo.query.assert_called_once()
        call_kwargs = mock_repo.query.call_args[1]
        # API action -> repository event_type
        assert call_kwargs.get("event_type") == "delete"

    def test_get_audit_logs_with_resource_type_filter(self) -> None:
        """GET /api/v1/admin/audit-logs should filter by resource_type."""
        mock_repo = self._create_mock_repository(items=[], total=0)
        client = self._create_app_and_client(mock_repo)
        response = client.get("/api/v1/admin/audit-logs?resource_type=workflow")

        assert response.status_code == 200
        mock_repo.query.assert_called_once()
        call_kwargs = mock_repo.query.call_args[1]
        assert call_kwargs.get("resource_type") == "workflow"

    def test_get_audit_logs_with_time_range_filter(self) -> None:
        """GET /api/v1/admin/audit-logs should filter by time range."""
        mock_repo = self._create_mock_repository(items=[], total=0)
        client = self._create_app_and_client(mock_repo)
        response = client.get("/api/v1/admin/audit-logs?start_time=2024-01-01T00:00:00Z&end_time=2024-01-31T23:59:59Z")

        assert response.status_code == 200
        mock_repo.query.assert_called_once()
        call_kwargs = mock_repo.query.call_args[1]
        # Times are parsed to datetime objects
        assert call_kwargs.get("start_time") == datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
        assert call_kwargs.get("end_time") == datetime(2024, 1, 31, 23, 59, 59, tzinfo=UTC)

    def test_get_audit_logs_with_sorting(self) -> None:
        """GET /api/v1/admin/audit-logs should accept sorting params (currently unused)."""
        mock_repo = self._create_mock_repository(items=[], total=0)
        client = self._create_app_and_client(mock_repo)
        response = client.get("/api/v1/admin/audit-logs?sort_by=timestamp&sort_order=desc")

        assert response.status_code == 200
        # Repository always sorts by timestamp desc, but we verify params are accepted
        mock_repo.query.assert_called_once()

    def test_get_audit_logs_default_limit(self) -> None:
        """GET /api/v1/admin/audit-logs should use default limit of 50."""
        mock_repo = self._create_mock_repository(items=[], total=0)
        client = self._create_app_and_client(mock_repo)
        response = client.get("/api/v1/admin/audit-logs")

        assert response.status_code == 200
        mock_repo.query.assert_called_once()
        call_kwargs = mock_repo.query.call_args[1]
        assert call_kwargs.get("limit") == 50


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_admin_router")
class TestAuditLogResponseModels:
    """Tests for audit log response models."""

    _session_maker_patcher: patch  # type: ignore[type-arg]

    def setup_method(self) -> None:
        """Reset database singletons and patch session maker before each test."""
        import sys

        # Reset database session singletons to prevent pollution from other tests
        if "mcp_server_langgraph.database.session" in sys.modules:
            import mcp_server_langgraph.database.session as session_module

            session_module._engine = None
            session_module._async_session_maker = None

        # Patch get_session_maker at the source to prevent ANY database connection attempts
        self._session_maker_patcher = patch(
            "mcp_server_langgraph.database.session.get_session_maker",
            side_effect=lambda *a, **kw: MagicMock(),
        )
        self._session_maker_patcher.start()

    def teardown_method(self) -> None:
        """Force GC and reset singletons to prevent mock accumulation in xdist workers."""
        import sys

        # Stop the patcher
        self._session_maker_patcher.stop()

        # Reset database singletons after each test
        if "mcp_server_langgraph.database.session" in sys.modules:
            import mcp_server_langgraph.database.session as session_module

            session_module._engine = None
            session_module._async_session_maker = None

        gc.collect()

    def test_audit_log_entry_model(self) -> None:
        """AuditLogEntry model should validate required fields."""
        from mcp_server_langgraph.api.v1.admin import AuditLogEntry

        entry = AuditLogEntry(
            id="log-1",
            action="create",
            user_id="user-123",
            resource_type="workflow",
            resource_id="wf-456",
            timestamp="2024-01-15T10:30:00Z",
        )

        assert entry.id == "log-1"
        assert entry.action == "create"
        assert entry.user_id == "user-123"
        assert entry.resource_type == "workflow"
        assert entry.resource_id == "wf-456"
        assert entry.timestamp == "2024-01-15T10:30:00Z"
        assert entry.user_email is None
        assert entry.ip_address is None
        assert entry.details is None

    def test_audit_log_entry_with_optional_fields(self) -> None:
        """AuditLogEntry should accept optional fields."""
        from mcp_server_langgraph.api.v1.admin import AuditLogEntry

        entry = AuditLogEntry(
            id="log-1",
            action="create",
            user_id="user-123",
            user_email="user@example.com",
            resource_type="workflow",
            resource_id="wf-456",
            timestamp="2024-01-15T10:30:00Z",
            ip_address="192.168.1.1",
            details={"old_value": "foo", "new_value": "bar"},
        )

        assert entry.user_email == "user@example.com"
        assert entry.ip_address == "192.168.1.1"
        assert entry.details == {"old_value": "foo", "new_value": "bar"}

    def test_paginated_audit_log_response(self) -> None:
        """PaginatedAuditLogResponse should contain items and total."""
        from mcp_server_langgraph.api.v1.admin import AuditLogEntry, PaginatedAuditLogResponse

        response = PaginatedAuditLogResponse(
            items=[
                AuditLogEntry(
                    id="log-1",
                    action="create",
                    user_id="user-123",
                    resource_type="workflow",
                    resource_id="wf-456",
                    timestamp="2024-01-15T10:30:00Z",
                )
            ],
            total=1,
            next_cursor=None,
        )

        assert len(response.items) == 1
        assert response.total == 1
        assert response.next_cursor is None

    def test_paginated_response_with_cursor(self) -> None:
        """PaginatedAuditLogResponse should support next_cursor for pagination."""
        from mcp_server_langgraph.api.v1.admin import PaginatedAuditLogResponse

        response = PaginatedAuditLogResponse(
            items=[],
            total=100,
            next_cursor="cursor-abc123",
        )

        assert response.next_cursor == "cursor-abc123"
