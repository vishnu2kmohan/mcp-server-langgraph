"""
Tests for MCP Connection Audit Logging API

TDD: Tests for audit logging of connection operations:
- Log connection CRUD operations
- Log authentication events
- Query audit logs with filtering
- Retention policies

Follows memory safety patterns for pytest-xdist.
"""

import gc
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

pytestmark = [pytest.mark.unit, pytest.mark.api]


# ============================================================================
# Mock Repository and Test Fixtures
# ============================================================================


class MockAuditLogRepository:
    """In-memory mock repository for testing audit logging."""

    def __init__(self) -> None:
        self.logs: list[dict] = []

    async def log_event(
        self,
        event_type: str,
        resource_type: str,
        resource_id: str,
        actor_id: str,
        action: str,
        details: dict | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> dict:
        """Log an audit event."""
        log_entry = {
            "id": str(uuid4()),
            "event_type": event_type,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "actor_id": actor_id,
            "action": action,
            "details": details or {},
            "ip_address": ip_address,
            "user_agent": user_agent,
            "timestamp": datetime.now(UTC),
        }
        self.logs.append(log_entry)
        return log_entry

    async def query(
        self,
        resource_type: str | None = None,
        resource_id: str | None = None,
        actor_id: str | None = None,
        event_type: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[dict], int]:
        """Query audit logs with filtering."""
        filtered = self.logs.copy()

        if resource_type:
            filtered = [log for log in filtered if log["resource_type"] == resource_type]
        if resource_id:
            filtered = [log for log in filtered if log["resource_id"] == resource_id]
        if actor_id:
            filtered = [log for log in filtered if log["actor_id"] == actor_id]
        if event_type:
            filtered = [log for log in filtered if log["event_type"] == event_type]
        if start_time:
            filtered = [log for log in filtered if log["timestamp"] >= start_time]
        if end_time:
            filtered = [log for log in filtered if log["timestamp"] <= end_time]

        total = len(filtered)
        filtered = filtered[offset : offset + limit]

        return filtered, total

    async def get_by_resource(
        self,
        resource_type: str,
        resource_id: str,
        limit: int = 20,
    ) -> list[dict]:
        """Get audit logs for a specific resource."""
        filtered = [log for log in self.logs if log["resource_type"] == resource_type and log["resource_id"] == resource_id]
        return filtered[:limit]

    async def delete_older_than(self, days: int) -> int:
        """Delete logs older than specified days."""
        cutoff = datetime.now(UTC) - timedelta(days=days)
        original_count = len(self.logs)
        self.logs = [log for log in self.logs if log["timestamp"] >= cutoff]
        return original_count - len(self.logs)


@pytest.fixture
def mock_audit_repo():
    """Create a mock audit log repository."""
    return MockAuditLogRepository()


@pytest.fixture
def app(mock_audit_repo):
    """Create a test FastAPI app with the audit router."""
    from mcp_server_langgraph.api.v1.connection_audit import audit_router
    from mcp_server_langgraph.core.dependencies import get_audit_log_repository

    app = FastAPI()
    app.include_router(audit_router)

    # Override dependencies
    app.dependency_overrides[get_audit_log_repository] = lambda: mock_audit_repo

    return app


@pytest.fixture
def client(app):
    """Create a test client."""
    return TestClient(app)


# ============================================================================
# Audit Log Event Tests
# ============================================================================


@pytest.mark.xdist_group(name="connection_audit_api")
class TestAuditLogEvent:
    """Tests for POST /connections/audit/log"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_log_connection_created(self, client, mock_audit_repo):
        """Should log connection creation event."""
        response = client.post(
            "/connections/audit/log",
            json={
                "event_type": "connection.created",
                "resource_type": "connection",
                "resource_id": "conn-123",
                "actor_id": "user-456",
                "action": "create",
                "details": {"name": "GitHub MCP", "auth_type": "oauth2"},
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["event_type"] == "connection.created"
        assert data["resource_id"] == "conn-123"
        assert len(mock_audit_repo.logs) == 1

    def test_log_connection_deleted(self, client, mock_audit_repo):
        """Should log connection deletion event."""
        response = client.post(
            "/connections/audit/log",
            json={
                "event_type": "connection.deleted",
                "resource_type": "connection",
                "resource_id": "conn-123",
                "actor_id": "user-456",
                "action": "delete",
            },
        )

        assert response.status_code == 201
        assert mock_audit_repo.logs[0]["event_type"] == "connection.deleted"

    def test_log_connection_tested(self, client, mock_audit_repo):
        """Should log connection test event."""
        response = client.post(
            "/connections/audit/log",
            json={
                "event_type": "connection.tested",
                "resource_type": "connection",
                "resource_id": "conn-123",
                "actor_id": "user-456",
                "action": "test",
                "details": {"success": True, "latency_ms": 150},
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["details"]["success"] is True

    def test_log_oauth2_authorized(self, client, mock_audit_repo):
        """Should log OAuth2 authorization event."""
        response = client.post(
            "/connections/audit/log",
            json={
                "event_type": "connection.oauth2_authorized",
                "resource_type": "connection",
                "resource_id": "conn-123",
                "actor_id": "user-456",
                "action": "authorize",
                "details": {"provider": "github", "scopes": ["repo", "user"]},
            },
        )

        assert response.status_code == 201
        assert mock_audit_repo.logs[0]["details"]["provider"] == "github"

    def test_log_bulk_delete(self, client, mock_audit_repo):
        """Should log bulk delete event."""
        response = client.post(
            "/connections/audit/log",
            json={
                "event_type": "connection.bulk_deleted",
                "resource_type": "connection",
                "resource_id": "bulk-operation",
                "actor_id": "user-456",
                "action": "bulk_delete",
                "details": {
                    "connection_ids": ["conn-1", "conn-2", "conn-3"],
                    "deleted_count": 3,
                    "failed_ids": [],
                },
            },
        )

        assert response.status_code == 201
        assert mock_audit_repo.logs[0]["details"]["deleted_count"] == 3

    def test_log_with_ip_and_user_agent(self, client, mock_audit_repo):
        """Should capture IP address and user agent."""
        response = client.post(
            "/connections/audit/log",
            json={
                "event_type": "connection.created",
                "resource_type": "connection",
                "resource_id": "conn-123",
                "actor_id": "user-456",
                "action": "create",
            },
            headers={
                "X-Forwarded-For": "192.168.1.100",
                "User-Agent": "Mozilla/5.0 Test Browser",
            },
        )

        assert response.status_code == 201
        # The API should extract these from headers
        assert mock_audit_repo.logs[0]["ip_address"] is not None

    def test_log_missing_required_fields(self, client):
        """Should reject incomplete log entry."""
        response = client.post(
            "/connections/audit/log",
            json={
                "event_type": "connection.created",
                # Missing resource_type, resource_id, actor_id, action
            },
        )

        assert response.status_code == 422


# ============================================================================
# Audit Log Query Tests
# ============================================================================


@pytest.mark.xdist_group(name="connection_audit_api")
class TestAuditLogQuery:
    """Tests for GET /connections/audit/logs"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_query_all_logs(self, client, mock_audit_repo):
        """Should return all logs with pagination."""
        import asyncio

        # Add some logs
        async def add_logs():
            for i in range(5):
                await mock_audit_repo.log_event(
                    event_type="connection.created",
                    resource_type="connection",
                    resource_id=f"conn-{i}",
                    actor_id="user-123",
                    action="create",
                )

        asyncio.run(add_logs())

        response = client.get("/connections/audit/logs")

        assert response.status_code == 200
        data = response.json()
        assert len(data["logs"]) == 5
        assert data["total"] == 5

    def test_query_by_resource_type(self, client, mock_audit_repo):
        """Should filter by resource type."""
        import asyncio

        async def add_logs():
            await mock_audit_repo.log_event(
                event_type="connection.created",
                resource_type="connection",
                resource_id="conn-1",
                actor_id="user-123",
                action="create",
            )
            await mock_audit_repo.log_event(
                event_type="template.applied",
                resource_type="template",
                resource_id="tmpl-1",
                actor_id="user-123",
                action="apply",
            )

        asyncio.run(add_logs())

        response = client.get("/connections/audit/logs?resource_type=connection")

        assert response.status_code == 200
        data = response.json()
        assert len(data["logs"]) == 1
        assert data["logs"][0]["resource_type"] == "connection"

    def test_query_by_actor(self, client, mock_audit_repo):
        """Should filter by actor ID."""
        import asyncio

        async def add_logs():
            await mock_audit_repo.log_event(
                event_type="connection.created",
                resource_type="connection",
                resource_id="conn-1",
                actor_id="user-123",
                action="create",
            )
            await mock_audit_repo.log_event(
                event_type="connection.created",
                resource_type="connection",
                resource_id="conn-2",
                actor_id="user-456",
                action="create",
            )

        asyncio.run(add_logs())

        response = client.get("/connections/audit/logs?actor_id=user-123")

        assert response.status_code == 200
        data = response.json()
        assert len(data["logs"]) == 1
        assert data["logs"][0]["actor_id"] == "user-123"

    def test_query_by_event_type(self, client, mock_audit_repo):
        """Should filter by event type."""
        import asyncio

        async def add_logs():
            await mock_audit_repo.log_event(
                event_type="connection.created",
                resource_type="connection",
                resource_id="conn-1",
                actor_id="user-123",
                action="create",
            )
            await mock_audit_repo.log_event(
                event_type="connection.deleted",
                resource_type="connection",
                resource_id="conn-2",
                actor_id="user-123",
                action="delete",
            )

        asyncio.run(add_logs())

        response = client.get("/connections/audit/logs?event_type=connection.deleted")

        assert response.status_code == 200
        data = response.json()
        assert len(data["logs"]) == 1
        assert data["logs"][0]["event_type"] == "connection.deleted"

    def test_query_with_pagination(self, client, mock_audit_repo):
        """Should support pagination."""
        import asyncio

        async def add_logs():
            for i in range(25):
                await mock_audit_repo.log_event(
                    event_type="connection.created",
                    resource_type="connection",
                    resource_id=f"conn-{i}",
                    actor_id="user-123",
                    action="create",
                )

        asyncio.run(add_logs())

        # First page
        response = client.get("/connections/audit/logs?limit=10&offset=0")
        assert response.status_code == 200
        data = response.json()
        assert len(data["logs"]) == 10
        assert data["total"] == 25

        # Second page
        response = client.get("/connections/audit/logs?limit=10&offset=10")
        data = response.json()
        assert len(data["logs"]) == 10


# ============================================================================
# Resource-Specific Audit Log Tests
# ============================================================================


@pytest.mark.xdist_group(name="connection_audit_api")
class TestResourceAuditLog:
    """Tests for GET /connections/{connection_id}/audit"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_get_connection_audit_log(self, client, mock_audit_repo):
        """Should return audit log for specific connection."""
        import asyncio

        async def add_logs():
            await mock_audit_repo.log_event(
                event_type="connection.created",
                resource_type="connection",
                resource_id="conn-123",
                actor_id="user-456",
                action="create",
            )
            await mock_audit_repo.log_event(
                event_type="connection.tested",
                resource_type="connection",
                resource_id="conn-123",
                actor_id="user-456",
                action="test",
            )
            await mock_audit_repo.log_event(
                event_type="connection.created",
                resource_type="connection",
                resource_id="conn-other",
                actor_id="user-456",
                action="create",
            )

        asyncio.run(add_logs())

        response = client.get("/connections/conn-123/audit")

        assert response.status_code == 200
        data = response.json()
        assert len(data["logs"]) == 2
        assert all(log["resource_id"] == "conn-123" for log in data["logs"])

    def test_get_empty_audit_log(self, client, mock_audit_repo):
        """Should return empty list for connection with no logs."""
        response = client.get("/connections/nonexistent/audit")

        assert response.status_code == 200
        data = response.json()
        assert len(data["logs"]) == 0


# ============================================================================
# Audit Log Retention Tests
# ============================================================================


@pytest.mark.xdist_group(name="connection_audit_api")
class TestAuditLogRetention:
    """Tests for audit log retention management."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_delete_old_logs(self, client, mock_audit_repo):
        """Should delete logs older than specified days."""
        import asyncio

        # Add old logs (mock with past timestamp)
        async def add_old_logs():
            old_time = datetime.now(UTC) - timedelta(days=100)
            for i in range(5):
                _ = await mock_audit_repo.log_event(
                    event_type="connection.created",
                    resource_type="connection",
                    resource_id=f"conn-{i}",
                    actor_id="user-123",
                    action="create",
                )
                # Manually set old timestamp
                mock_audit_repo.logs[-1]["timestamp"] = old_time

        asyncio.run(add_old_logs())

        # Add recent logs
        async def add_recent_logs():
            for i in range(3):
                await mock_audit_repo.log_event(
                    event_type="connection.created",
                    resource_type="connection",
                    resource_id=f"conn-recent-{i}",
                    actor_id="user-123",
                    action="create",
                )

        asyncio.run(add_recent_logs())

        assert len(mock_audit_repo.logs) == 8

        response = client.delete("/connections/audit/retention?days=90")

        assert response.status_code == 200
        data = response.json()
        assert data["deleted_count"] == 5
        assert len(mock_audit_repo.logs) == 3


# ============================================================================
# Audit Log Export Tests
# ============================================================================


@pytest.mark.xdist_group(name="connection_audit_api")
class TestAuditLogExport:
    """Tests for audit log export endpoints."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_export_json_format_returns_valid_response(self, client, mock_audit_repo):
        """Should export audit logs as JSON."""
        import asyncio

        async def add_logs():
            for i in range(3):
                await mock_audit_repo.log_event(
                    event_type="connection.created",
                    resource_type="connection",
                    resource_id=f"conn-{i}",
                    actor_id="user-123",
                    action="create",
                    details={"name": f"Connection {i}"},
                )

        asyncio.run(add_logs())

        response = client.get("/connections/audit/export?format=json")

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"
        assert "attachment" in response.headers.get("content-disposition", "")

        data = response.json()
        assert len(data["logs"]) == 3
        assert data["total"] == 3
        assert "exported_at" in data

    def test_export_csv_format_returns_valid_response(self, client, mock_audit_repo):
        """Should export audit logs as CSV."""
        import asyncio

        async def add_logs():
            await mock_audit_repo.log_event(
                event_type="connection.created",
                resource_type="connection",
                resource_id="conn-1",
                actor_id="user-123",
                action="create",
                details={"name": "Test Connection"},
            )

        asyncio.run(add_logs())

        response = client.get("/connections/audit/export?format=csv")

        assert response.status_code == 200
        assert "text/csv" in response.headers["content-type"]
        assert "attachment" in response.headers.get("content-disposition", "")

        # Parse CSV content
        content = response.content.decode("utf-8")
        lines = content.strip().split("\n")

        # Should have header and at least one data row
        assert len(lines) >= 2
        header = lines[0]
        assert "event_type" in header
        assert "resource_id" in header
        assert "actor_id" in header

    def test_export_with_filters(self, client, mock_audit_repo):
        """Should apply filters to export."""
        import asyncio

        async def add_logs():
            await mock_audit_repo.log_event(
                event_type="connection.created",
                resource_type="connection",
                resource_id="conn-1",
                actor_id="user-123",
                action="create",
            )
            await mock_audit_repo.log_event(
                event_type="connection.deleted",
                resource_type="connection",
                resource_id="conn-2",
                actor_id="user-456",
                action="delete",
            )

        asyncio.run(add_logs())

        response = client.get("/connections/audit/export?format=json&event_type=connection.created")

        assert response.status_code == 200
        data = response.json()
        assert len(data["logs"]) == 1
        assert data["logs"][0]["event_type"] == "connection.created"

    def test_export_with_resource_filter(self, client, mock_audit_repo):
        """Should export logs for a specific connection."""
        import asyncio

        async def add_logs():
            await mock_audit_repo.log_event(
                event_type="connection.created",
                resource_type="connection",
                resource_id="conn-123",
                actor_id="user-1",
                action="create",
            )
            await mock_audit_repo.log_event(
                event_type="connection.tested",
                resource_type="connection",
                resource_id="conn-123",
                actor_id="user-1",
                action="test",
            )
            await mock_audit_repo.log_event(
                event_type="connection.created",
                resource_type="connection",
                resource_id="conn-other",
                actor_id="user-1",
                action="create",
            )

        asyncio.run(add_logs())

        response = client.get("/connections/audit/export?format=json&resource_id=conn-123")

        assert response.status_code == 200
        data = response.json()
        assert len(data["logs"]) == 2
        assert all(log["resource_id"] == "conn-123" for log in data["logs"])

    def test_export_default_format_is_json(self, client, mock_audit_repo):
        """Should default to JSON format if not specified."""
        import asyncio

        async def add_logs():
            await mock_audit_repo.log_event(
                event_type="connection.created",
                resource_type="connection",
                resource_id="conn-1",
                actor_id="user-123",
                action="create",
            )

        asyncio.run(add_logs())

        response = client.get("/connections/audit/export")

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"

    def test_export_invalid_format(self, client, mock_audit_repo):
        """Should reject invalid export format."""
        response = client.get("/connections/audit/export?format=xml")

        assert response.status_code == 422

    def test_export_empty_logs(self, client, mock_audit_repo):
        """Should handle empty log list gracefully."""
        response = client.get("/connections/audit/export?format=json")

        assert response.status_code == 200
        data = response.json()
        assert len(data["logs"]) == 0
        assert data["total"] == 0

    def test_export_csv_empty(self, client, mock_audit_repo):
        """Should return CSV with only headers when no logs."""
        response = client.get("/connections/audit/export?format=csv")

        assert response.status_code == 200
        content = response.content.decode("utf-8")
        lines = content.strip().split("\n")
        # Should have header only
        assert len(lines) == 1
        assert "event_type" in lines[0]
