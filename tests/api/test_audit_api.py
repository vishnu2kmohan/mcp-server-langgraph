"""
Tests for Unified Audit API endpoints.

TDD RED phase: These tests define expected behavior for the audit API.

API endpoints should:
- GET /api/v1/audit/events - Query audit events with filters
- GET /api/v1/audit/events/{id} - Get specific event
- GET /api/v1/audit/integrity/verify - Verify hash chain
- GET /api/v1/audit/export - Export audit logs

All audit endpoints require authentication and admin/compliance_officer role.
"""

import gc
from typing import Any, Generator
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

pytestmark = pytest.mark.api


def _make_admin_user() -> dict[str, Any]:
    """Create admin user for authorized access."""
    return {
        "user_id": "admin-001",
        "username": "admin",
        "email": "admin@example.com",
        "roles": ["admin"],
    }


def _make_compliance_officer_user() -> dict[str, Any]:
    """Create compliance officer user for authorized access."""
    return {
        "user_id": "co-001",
        "username": "compliance_officer",
        "email": "compliance@example.com",
        "roles": ["compliance_officer"],
    }


def _make_regular_user() -> dict[str, Any]:
    """Create regular user without admin role (unauthorized)."""
    return {
        "user_id": "user-001",
        "username": "regularuser",
        "email": "user@example.com",
        "roles": ["user"],
    }


@pytest.fixture
def audit_app() -> Generator[tuple[FastAPI, AsyncMock], None, None]:
    """Create test app with mocked audit service and admin user."""
    from mcp_server_langgraph.api.v1.audit import router, set_audit_service
    from mcp_server_langgraph.auth.middleware import get_current_user

    app = FastAPI()
    app.include_router(router, prefix="/api/v1/audit")

    # Override get_current_user to return admin user (async function for xdist safety)
    async def get_admin_user() -> dict[str, Any]:
        return _make_admin_user()

    app.dependency_overrides[get_current_user] = get_admin_user

    mock_service = AsyncMock()  # async-mock-configured
    set_audit_service(mock_service)

    yield app, mock_service

    # Cleanup
    set_audit_service(None)
    app.dependency_overrides.clear()


@pytest.fixture
def audit_app_unauthorized() -> Generator[tuple[FastAPI, AsyncMock], None, None]:
    """Create test app with mocked audit service and regular user (unauthorized)."""
    from mcp_server_langgraph.api.v1.audit import router, set_audit_service
    from mcp_server_langgraph.auth.middleware import get_current_user

    app = FastAPI()
    app.include_router(router, prefix="/api/v1/audit")

    # Override get_current_user to return regular user (async function for xdist safety)
    async def get_regular_user() -> dict[str, Any]:
        return _make_regular_user()

    app.dependency_overrides[get_current_user] = get_regular_user

    mock_service = AsyncMock()  # async-mock-configured
    set_audit_service(mock_service)

    yield app, mock_service

    # Cleanup
    set_audit_service(None)
    app.dependency_overrides.clear()


@pytest.fixture
def audit_app_compliance_officer() -> Generator[tuple[FastAPI, AsyncMock], None, None]:
    """Create test app with mocked audit service and compliance officer user."""
    from mcp_server_langgraph.api.v1.audit import router, set_audit_service
    from mcp_server_langgraph.auth.middleware import get_current_user

    app = FastAPI()
    app.include_router(router, prefix="/api/v1/audit")

    # Override get_current_user to return compliance officer (async function for xdist safety)
    async def get_compliance_officer() -> dict[str, Any]:
        return _make_compliance_officer_user()

    app.dependency_overrides[get_current_user] = get_compliance_officer

    mock_service = AsyncMock()  # async-mock-configured
    set_audit_service(mock_service)

    yield app, mock_service

    # Cleanup
    set_audit_service(None)
    app.dependency_overrides.clear()


@pytest.mark.api
@pytest.mark.xdist_group(name="audit_api")
class TestAuditEventsEndpoint:
    """Tests for GET /api/v1/audit/events."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_list_events_returns_events(self, audit_app: tuple) -> None:
        """GIVEN audit events WHEN listing THEN returns paginated list."""
        app, mock_service = audit_app

        mock_events = [
            {
                "event_id": "evt-001",
                "timestamp": "2025-01-15T10:30:00Z",
                "category": "authentication",
                "event_type": "login_success",
                "actor": {"actor_id": "user:alice", "actor_type": "user"},
                "resource_type": "session",
                "resource_id": "sess-001",
                "action": "Login",
                "outcome": "success",
            }
        ]

        mock_service.query_events.return_value = (mock_events, 1)

        client = TestClient(app)
        response = client.get("/api/v1/audit/events")

        assert response.status_code == 200
        data = response.json()
        assert "events" in data
        assert "total" in data
        assert len(data["events"]) == 1

    def test_list_events_with_category_filter(self, audit_app: tuple) -> None:
        """GIVEN category filter WHEN listing THEN filters by category."""
        app, mock_service = audit_app
        mock_service.query_events.return_value = ([], 0)

        client = TestClient(app)
        response = client.get("/api/v1/audit/events?category=authentication")

        assert response.status_code == 200
        mock_service.query_events.assert_called_once()
        call_kwargs = mock_service.query_events.call_args[1]
        assert call_kwargs["category"] == "authentication"

    def test_list_events_with_regulation_filter(self, audit_app: tuple) -> None:
        """GIVEN regulation filter WHEN listing THEN filters by regulation."""
        app, mock_service = audit_app
        mock_service.query_events.return_value = ([], 0)

        client = TestClient(app)
        response = client.get("/api/v1/audit/events?regulation=HIPAA")

        assert response.status_code == 200
        mock_service.query_events.assert_called_once()
        call_kwargs = mock_service.query_events.call_args[1]
        assert call_kwargs["regulation"] == "HIPAA"

    def test_list_events_with_time_range(self, audit_app: tuple) -> None:
        """GIVEN time range WHEN listing THEN filters by time."""
        app, mock_service = audit_app
        mock_service.query_events.return_value = ([], 0)

        client = TestClient(app)
        response = client.get("/api/v1/audit/events?start_time=2025-01-01T00:00:00Z&end_time=2025-01-31T23:59:59Z")

        assert response.status_code == 200
        mock_service.query_events.assert_called_once()
        call_kwargs = mock_service.query_events.call_args[1]
        assert call_kwargs["start_time"] is not None
        assert call_kwargs["end_time"] is not None

    def test_list_events_with_pagination(self, audit_app: tuple) -> None:
        """GIVEN pagination params WHEN listing THEN paginates results."""
        app, mock_service = audit_app
        mock_service.query_events.return_value = ([], 100)

        client = TestClient(app)
        response = client.get("/api/v1/audit/events?page=2&page_size=20")

        assert response.status_code == 200
        mock_service.query_events.assert_called_once()
        call_kwargs = mock_service.query_events.call_args[1]
        assert call_kwargs["page"] == 2
        assert call_kwargs["page_size"] == 20


@pytest.mark.api
@pytest.mark.xdist_group(name="audit_api")
class TestAuditEventDetailEndpoint:
    """Tests for GET /api/v1/audit/events/{id}."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_get_event_returns_event(self, audit_app: tuple) -> None:
        """GIVEN event ID WHEN getting THEN returns event details."""
        app, mock_service = audit_app

        mock_event = {
            "event_id": "evt-001",
            "timestamp": "2025-01-15T10:30:00Z",
            "category": "authentication",
            "event_type": "login_success",
            "actor": {"actor_id": "user:alice", "actor_type": "user"},
            "resource_type": "session",
            "resource_id": "sess-001",
            "action": "Login",
            "outcome": "success",
            "context": {"request_id": "req-123"},
        }

        mock_service.get_event.return_value = mock_event

        client = TestClient(app)
        response = client.get("/api/v1/audit/events/evt-001")

        assert response.status_code == 200
        data = response.json()
        assert data["event_id"] == "evt-001"

    def test_get_event_not_found(self, audit_app: tuple) -> None:
        """GIVEN non-existent ID WHEN getting THEN returns 404."""
        app, mock_service = audit_app
        mock_service.get_event.return_value = None

        client = TestClient(app)
        response = client.get("/api/v1/audit/events/nonexistent")

        assert response.status_code == 404


@pytest.mark.api
@pytest.mark.xdist_group(name="audit_api")
class TestAuditIntegrityEndpoint:
    """Tests for GET /api/v1/audit/integrity/verify."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_verify_integrity_returns_result(self, audit_app: tuple) -> None:
        """GIVEN time range WHEN verifying THEN returns integrity result."""
        app, mock_service = audit_app

        mock_report = {
            "start_time": "2025-01-01T00:00:00Z",
            "end_time": "2025-01-31T23:59:59Z",
            "events_verified": 1000,
            "chain_valid": True,
            "errors": [],
            "verification_time": 0.5,
        }

        mock_service.get_integrity_report.return_value = mock_report

        client = TestClient(app)
        response = client.get("/api/v1/audit/integrity/verify?start_time=2025-01-01T00:00:00Z&end_time=2025-01-31T23:59:59Z")

        assert response.status_code == 200
        data = response.json()
        assert data["chain_valid"] is True
        assert data["events_verified"] == 1000

    def test_verify_integrity_detects_tampering(self, audit_app: tuple) -> None:
        """GIVEN tampered chain WHEN verifying THEN reports errors."""
        app, mock_service = audit_app

        mock_report = {
            "start_time": "2025-01-01T00:00:00Z",
            "end_time": "2025-01-31T23:59:59Z",
            "events_verified": 1000,
            "chain_valid": False,
            "errors": ["Hash mismatch at position 500"],
            "verification_time": 0.8,
        }

        mock_service.get_integrity_report.return_value = mock_report

        client = TestClient(app)
        response = client.get("/api/v1/audit/integrity/verify?start_time=2025-01-01T00:00:00Z&end_time=2025-01-31T23:59:59Z")

        assert response.status_code == 200
        data = response.json()
        assert data["chain_valid"] is False
        assert len(data["errors"]) > 0


@pytest.mark.api
@pytest.mark.xdist_group(name="audit_api")
class TestAuditExportEndpoint:
    """Tests for GET /api/v1/audit/export."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_export_json_format_returns_valid_json(self, audit_app: tuple) -> None:
        """GIVEN JSON format WHEN exporting THEN returns JSON file."""
        app, mock_service = audit_app

        mock_events = [
            {
                "event_id": "evt-001",
                "timestamp": "2025-01-15T10:30:00Z",
                "category": "authentication",
            }
        ]

        mock_service.export_events.return_value = mock_events

        client = TestClient(app)
        response = client.get("/api/v1/audit/export?format=json&start_time=2025-01-01T00:00:00Z&end_time=2025-01-31T23:59:59Z")

        assert response.status_code == 200
        assert "application/json" in response.headers["content-type"]

    def test_export_csv_format_returns_valid_csv(self, audit_app: tuple) -> None:
        """GIVEN CSV format WHEN exporting THEN returns CSV file."""
        app, mock_service = audit_app

        mock_csv = "event_id,timestamp,category\nevt-001,2025-01-15T10:30:00Z,authentication\n"
        mock_service.export_events_csv.return_value = mock_csv

        client = TestClient(app)
        response = client.get("/api/v1/audit/export?format=csv&start_time=2025-01-01T00:00:00Z&end_time=2025-01-31T23:59:59Z")

        assert response.status_code == 200
        assert "text/csv" in response.headers["content-type"]

    def test_export_requires_time_range(self, audit_app: tuple) -> None:
        """GIVEN no time range WHEN exporting THEN returns 422."""
        app, mock_service = audit_app

        client = TestClient(app)
        response = client.get("/api/v1/audit/export?format=json")

        assert response.status_code == 422  # Validation error


@pytest.mark.api
@pytest.mark.xdist_group(name="audit_api")
class TestAuditRetentionEndpoint:
    """Tests for /api/v1/audit/retention endpoints."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_get_retention_status(self, audit_app: tuple) -> None:
        """GIVEN audit events WHEN getting status THEN returns per-regulation counts."""
        app, mock_service = audit_app

        mock_status = {
            "GDPR": {"total": 1000, "expiring_soon": 50},
            "HIPAA": {"total": 500, "expiring_soon": 10},
        }

        mock_service.get_retention_status.return_value = mock_status

        client = TestClient(app)
        response = client.get("/api/v1/audit/retention/status")

        assert response.status_code == 200
        data = response.json()
        assert "GDPR" in data
        assert data["GDPR"]["total"] == 1000

    def test_apply_retention_policy(self, audit_app: tuple) -> None:
        """GIVEN regulation WHEN applying retention THEN deletes expired."""
        app, mock_service = audit_app
        mock_service.apply_retention_policy.return_value = 100

        client = TestClient(app)
        response = client.post("/api/v1/audit/retention/apply?regulation=EU_AI_ACT")

        assert response.status_code == 200
        data = response.json()
        assert data["deleted_count"] == 100


@pytest.mark.api
@pytest.mark.xdist_group(name="audit_api")
class TestAuditEndpointAuthorization:
    """Tests for audit API authorization.

    SECURITY: All audit endpoints require admin or compliance_officer role.
    This ensures audit logs are only accessible by authorized personnel.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_list_events_forbidden_without_admin_role(self, audit_app_unauthorized: tuple) -> None:
        """GIVEN regular user WHEN listing events THEN returns 403."""
        app, mock_service = audit_app_unauthorized

        client = TestClient(app)
        response = client.get("/api/v1/audit/events")

        assert response.status_code == 403
        assert "Admin or compliance officer role required" in response.json()["detail"]

    def test_get_event_forbidden_without_admin_role(self, audit_app_unauthorized: tuple) -> None:
        """GIVEN regular user WHEN getting event THEN returns 403."""
        app, mock_service = audit_app_unauthorized

        client = TestClient(app)
        response = client.get("/api/v1/audit/events/evt-001")

        assert response.status_code == 403

    def test_verify_integrity_forbidden_without_admin_role(self, audit_app_unauthorized: tuple) -> None:
        """GIVEN regular user WHEN verifying integrity THEN returns 403."""
        app, mock_service = audit_app_unauthorized

        client = TestClient(app)
        response = client.get("/api/v1/audit/integrity/verify?start_time=2025-01-01T00:00:00Z&end_time=2025-01-31T23:59:59Z")

        assert response.status_code == 403

    def test_export_forbidden_without_admin_role(self, audit_app_unauthorized: tuple) -> None:
        """GIVEN regular user WHEN exporting THEN returns 403."""
        app, mock_service = audit_app_unauthorized

        client = TestClient(app)
        response = client.get("/api/v1/audit/export?format=json&start_time=2025-01-01T00:00:00Z&end_time=2025-01-31T23:59:59Z")

        assert response.status_code == 403

    def test_retention_status_forbidden_without_admin_role(self, audit_app_unauthorized: tuple) -> None:
        """GIVEN regular user WHEN getting retention status THEN returns 403."""
        app, mock_service = audit_app_unauthorized

        client = TestClient(app)
        response = client.get("/api/v1/audit/retention/status")

        assert response.status_code == 403

    def test_apply_retention_forbidden_without_admin_role(self, audit_app_unauthorized: tuple) -> None:
        """GIVEN regular user WHEN applying retention THEN returns 403."""
        app, mock_service = audit_app_unauthorized

        client = TestClient(app)
        response = client.post("/api/v1/audit/retention/apply?regulation=GDPR")

        assert response.status_code == 403

    def test_compliance_officer_can_list_events(self, audit_app_compliance_officer: tuple) -> None:
        """GIVEN compliance_officer role WHEN listing events THEN allowed."""
        app, mock_service = audit_app_compliance_officer
        mock_service.query_events.return_value = ([], 0)

        client = TestClient(app)
        response = client.get("/api/v1/audit/events")

        assert response.status_code == 200

    def test_compliance_officer_can_export(self, audit_app_compliance_officer: tuple) -> None:
        """GIVEN compliance_officer role WHEN exporting THEN allowed."""
        app, mock_service = audit_app_compliance_officer
        mock_service.export_events.return_value = []

        client = TestClient(app)
        response = client.get("/api/v1/audit/export?format=json&start_time=2025-01-01T00:00:00Z&end_time=2025-01-31T23:59:59Z")

        assert response.status_code == 200

    def test_compliance_officer_can_verify_integrity(self, audit_app_compliance_officer: tuple) -> None:
        """GIVEN compliance_officer role WHEN verifying integrity THEN allowed."""
        app, mock_service = audit_app_compliance_officer
        mock_service.get_integrity_report.return_value = {
            "start_time": "2025-01-01T00:00:00Z",
            "end_time": "2025-01-31T23:59:59Z",
            "events_verified": 100,
            "chain_valid": True,
            "errors": [],
            "verification_time": 0.1,
        }

        client = TestClient(app)
        response = client.get("/api/v1/audit/integrity/verify?start_time=2025-01-01T00:00:00Z&end_time=2025-01-31T23:59:59Z")

        assert response.status_code == 200
