"""
Tests for Audit Event WebSocket Streaming.

TDD RED phase: These tests define expected behavior for real-time
audit event streaming via WebSocket.

The WebSocket endpoint should:
- Stream audit events in real-time
- Support filtering by category, regulation, actor
- Require authentication
- Require admin/compliance_officer role
- Handle connection lifecycle properly
"""

import gc
from typing import Any, Generator
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI

pytestmark = pytest.mark.api


def _make_admin_user() -> dict[str, Any]:
    """Create admin user for authorized access."""
    return {
        "user_id": "admin-001",
        "username": "admin",
        "email": "admin@example.com",
        "roles": ["admin"],
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
def audit_ws_app() -> Generator[tuple[FastAPI, AsyncMock], None, None]:
    """Create test app with mocked audit service and admin user."""
    from mcp_server_langgraph.api.v1.audit_websocket import (
        router,
        set_audit_event_broadcaster,
    )
    from mcp_server_langgraph.auth.middleware import get_current_user

    app = FastAPI()
    app.include_router(router, prefix="/api/v1/audit")

    # Override get_current_user to return admin user (async function for xdist safety)
    async def get_admin_user() -> dict[str, Any]:
        return _make_admin_user()

    app.dependency_overrides[get_current_user] = get_admin_user

    mock_broadcaster = AsyncMock()  # async-mock-configured
    set_audit_event_broadcaster(mock_broadcaster)

    yield app, mock_broadcaster

    # Cleanup
    set_audit_event_broadcaster(None)
    app.dependency_overrides.clear()


@pytest.fixture
def audit_ws_app_unauthorized() -> Generator[tuple[FastAPI, AsyncMock], None, None]:
    """Create test app with regular user (unauthorized)."""
    from mcp_server_langgraph.api.v1.audit_websocket import (
        router,
        set_audit_event_broadcaster,
    )
    from mcp_server_langgraph.auth.middleware import get_current_user

    app = FastAPI()
    app.include_router(router, prefix="/api/v1/audit")

    # Override get_current_user to return regular user (async function for xdist safety)
    async def get_regular_user() -> dict[str, Any]:
        return _make_regular_user()

    app.dependency_overrides[get_current_user] = get_regular_user

    mock_broadcaster = AsyncMock()  # async-mock-configured
    set_audit_event_broadcaster(mock_broadcaster)

    yield app, mock_broadcaster

    # Cleanup
    set_audit_event_broadcaster(None)
    app.dependency_overrides.clear()


@pytest.mark.api
@pytest.mark.xdist_group(name="audit_websocket")
class TestAuditWebSocketEndpoint:
    """Tests for /api/v1/audit/stream WebSocket endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_websocket_endpoint_exists(self, audit_ws_app: tuple) -> None:
        """
        GIVEN FastAPI app with audit WebSocket router
        WHEN checking routes
        THEN WebSocket endpoint exists.
        """
        app, _ = audit_ws_app

        routes = [route.path for route in app.routes]
        assert "/api/v1/audit/stream" in routes


@pytest.mark.api
@pytest.mark.xdist_group(name="audit_websocket")
class TestAuditEventBroadcaster:
    """Tests for AuditEventBroadcaster."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_broadcaster_add_subscriber(self) -> None:
        """
        GIVEN a broadcaster
        WHEN adding a subscriber
        THEN subscriber is registered.
        """
        from mcp_server_langgraph.audit.broadcast import AuditEventBroadcaster

        broadcaster = AuditEventBroadcaster()
        mock_ws = AsyncMock()  # async-mock-configured

        await broadcaster.subscribe(mock_ws)

        assert broadcaster.subscriber_count == 1

    @pytest.mark.asyncio
    async def test_broadcaster_remove_subscriber(self) -> None:
        """
        GIVEN a broadcaster with subscriber
        WHEN removing subscriber
        THEN subscriber is unregistered.
        """
        from mcp_server_langgraph.audit.broadcast import AuditEventBroadcaster

        broadcaster = AuditEventBroadcaster()
        mock_ws = AsyncMock()  # async-mock-configured

        await broadcaster.subscribe(mock_ws)
        await broadcaster.unsubscribe(mock_ws)

        assert broadcaster.subscriber_count == 0

    @pytest.mark.asyncio
    async def test_broadcaster_broadcast_event(self) -> None:
        """
        GIVEN subscribers
        WHEN broadcasting event
        THEN all subscribers receive event.
        """
        from mcp_server_langgraph.audit.broadcast import AuditEventBroadcaster

        broadcaster = AuditEventBroadcaster()
        mock_ws1 = AsyncMock()  # async-mock-configured
        mock_ws2 = AsyncMock()  # async-mock-configured

        await broadcaster.subscribe(mock_ws1)
        await broadcaster.subscribe(mock_ws2)

        event = {"event_id": "evt-001", "category": "authentication"}
        await broadcaster.broadcast(event)

        mock_ws1.send_json.assert_called_once_with(event)
        mock_ws2.send_json.assert_called_once_with(event)

    @pytest.mark.asyncio
    async def test_broadcaster_handles_disconnected_subscriber(self) -> None:
        """
        GIVEN a subscriber that disconnects
        WHEN broadcasting
        THEN handles error gracefully and removes subscriber.
        """
        from mcp_server_langgraph.audit.broadcast import AuditEventBroadcaster

        broadcaster = AuditEventBroadcaster()
        mock_ws = AsyncMock()  # async-mock-configured
        mock_ws.send_json.side_effect = Exception("Connection closed")

        await broadcaster.subscribe(mock_ws)
        event = {"event_id": "evt-001"}

        # Should not raise
        await broadcaster.broadcast(event)

        # Subscriber should be removed after failed send
        assert broadcaster.subscriber_count == 0


@pytest.mark.api
@pytest.mark.xdist_group(name="audit_websocket")
class TestAuditEventFilter:
    """Tests for audit event filtering."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_filter_by_category(self) -> None:
        """
        GIVEN an event filter with category
        WHEN checking event
        THEN filters correctly.
        """
        from mcp_server_langgraph.audit.broadcast import AuditEventFilter

        filter_ = AuditEventFilter(categories=["authentication"])

        auth_event = {"category": "authentication", "event_id": "1"}
        data_event = {"category": "data_access", "event_id": "2"}

        assert filter_.matches(auth_event) is True
        assert filter_.matches(data_event) is False

    def test_filter_by_regulation(self) -> None:
        """
        GIVEN an event filter with regulation
        WHEN checking event
        THEN filters correctly.
        """
        from mcp_server_langgraph.audit.broadcast import AuditEventFilter

        filter_ = AuditEventFilter(regulations=["HIPAA"])

        hipaa_event = {"regulation_tags": ["HIPAA"], "event_id": "1"}
        gdpr_event = {"regulation_tags": ["GDPR"], "event_id": "2"}
        no_tag_event = {"event_id": "3"}

        assert filter_.matches(hipaa_event) is True
        assert filter_.matches(gdpr_event) is False
        assert filter_.matches(no_tag_event) is False

    def test_filter_by_multiple_criteria(self) -> None:
        """
        GIVEN an event filter with multiple criteria
        WHEN checking event
        THEN must match all criteria.
        """
        from mcp_server_langgraph.audit.broadcast import AuditEventFilter

        filter_ = AuditEventFilter(
            categories=["security"],
            regulations=["FedRAMP"],
        )

        matching_event = {
            "category": "security",
            "regulation_tags": ["FedRAMP"],
            "event_id": "1",
        }
        partial_match = {
            "category": "security",
            "regulation_tags": ["GDPR"],
            "event_id": "2",
        }

        assert filter_.matches(matching_event) is True
        assert filter_.matches(partial_match) is False

    def test_empty_filter_matches_all(self) -> None:
        """
        GIVEN an empty filter
        WHEN checking any event
        THEN matches all events.
        """
        from mcp_server_langgraph.audit.broadcast import AuditEventFilter

        filter_ = AuditEventFilter()

        event = {"category": "any", "event_id": "1"}

        assert filter_.matches(event) is True


@pytest.mark.api
@pytest.mark.xdist_group(name="audit_websocket")
class TestAuditServiceIntegration:
    """Tests for audit service integration with broadcaster."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_audit_service_emits_to_broadcaster(self) -> None:
        """
        GIVEN audit service with broadcaster attached
        WHEN logging an event
        THEN event is broadcast to subscribers.
        """
        from mcp_server_langgraph.audit.broadcast import AuditEventBroadcaster
        from mcp_server_langgraph.audit.service import UnifiedAuditService
        from mcp_server_langgraph.audit.repository import InMemoryUnifiedAuditRepository
        from mcp_server_langgraph.audit.models import (
            UnifiedAuditEvent,
            AuditActor,
            AuditContext,
            AuditEventCategory,
            AuditEventType,
        )

        broadcaster = AuditEventBroadcaster()
        mock_ws = AsyncMock()  # async-mock-configured
        await broadcaster.subscribe(mock_ws)

        repository = InMemoryUnifiedAuditRepository()
        service = UnifiedAuditService(
            repository=repository,
            integrity_secret="test-secret",
            broadcaster=broadcaster,
        )

        # Create an audit event
        event = UnifiedAuditEvent(
            category=AuditEventCategory.AUTHENTICATION,
            event_type=AuditEventType.LOGIN_SUCCESS,
            actor=AuditActor(actor_id="user:alice", actor_type="user"),  # ✅ Safe: InMemory backend
            context=AuditContext(request_id="req-001"),
            resource_type="session",
            resource_id="sess-001",
            action="Login",
            outcome="success",
        )

        # Log the event
        await service.log_event(event)

        # Verify broadcast was called
        assert mock_ws.send_json.called
