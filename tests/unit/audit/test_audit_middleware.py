"""
Tests for audit middleware.

TDD RED phase: These tests define expected behavior for HTTP request auditing.

The middleware should:
- Capture all HTTP requests (except excluded paths)
- Extract actor from request.state.user
- Extract OpenTelemetry trace/span IDs
- Log request details (method, path, status, duration)
- Handle audit failures gracefully (FedRAMP AU-5)
"""

import gc
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.requests import Request
from starlette.responses import Response

pytestmark = pytest.mark.unit


@pytest.mark.unit
@pytest.mark.xdist_group(name="audit_middleware")
class TestAuditMiddlewareExclusions:
    """Tests for path exclusion patterns."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_health_endpoint_excluded(self) -> None:
        """GIVEN AuditMiddleware WHEN /health is requested THEN not audited."""
        from mcp_server_langgraph.middleware.audit import AuditMiddleware

        middleware = AuditMiddleware(app=MagicMock())
        assert middleware.should_exclude_path("/health")

    def test_metrics_endpoint_excluded(self) -> None:
        """GIVEN AuditMiddleware WHEN /metrics is requested THEN not audited."""
        from mcp_server_langgraph.middleware.audit import AuditMiddleware

        middleware = AuditMiddleware(app=MagicMock())
        assert middleware.should_exclude_path("/metrics")

    def test_readiness_endpoint_excluded(self) -> None:
        """GIVEN AuditMiddleware WHEN /ready is requested THEN not audited."""
        from mcp_server_langgraph.middleware.audit import AuditMiddleware

        middleware = AuditMiddleware(app=MagicMock())
        assert middleware.should_exclude_path("/ready")

    def test_liveness_endpoint_excluded(self) -> None:
        """GIVEN AuditMiddleware WHEN /live is requested THEN not audited."""
        from mcp_server_langgraph.middleware.audit import AuditMiddleware

        middleware = AuditMiddleware(app=MagicMock())
        assert middleware.should_exclude_path("/live")

    def test_api_endpoint_not_excluded(self) -> None:
        """GIVEN AuditMiddleware WHEN /api/v1/workflows is requested THEN audited."""
        from mcp_server_langgraph.middleware.audit import AuditMiddleware

        middleware = AuditMiddleware(app=MagicMock())
        assert not middleware.should_exclude_path("/api/v1/workflows")


@pytest.mark.unit
@pytest.mark.xdist_group(name="audit_middleware")
class TestAuditMiddlewareEventExtraction:
    """Tests for extracting audit event data from requests."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_extract_actor_from_request_state(self) -> None:
        """GIVEN request with user state WHEN extracting actor THEN returns actor info."""
        from mcp_server_langgraph.middleware.audit import AuditMiddleware

        middleware = AuditMiddleware(app=MagicMock())

        # Create mock request with user state
        request = MagicMock(spec=Request)
        request.state.user = {
            "sub": "user:alice",
            "preferred_username": "alice",
            "email": "alice@example.com",
            "realm_access": {"roles": ["editor", "viewer"]},
        }

        actor = middleware.extract_actor(request)

        assert actor.actor_id == "user:alice"
        assert actor.actor_type == "user"
        assert actor.username == "alice"
        assert actor.email == "alice@example.com"

    def test_extract_actor_anonymous(self) -> None:
        """GIVEN request without user state WHEN extracting actor THEN returns anonymous."""
        from mcp_server_langgraph.middleware.audit import AuditMiddleware

        middleware = AuditMiddleware(app=MagicMock())

        request = MagicMock(spec=Request)
        request.state = MagicMock()
        del request.state.user  # No user attribute

        actor = middleware.extract_actor(request)

        assert actor.actor_id == "anonymous"
        assert actor.actor_type == "user"

    def test_extract_ip_address(self) -> None:
        """GIVEN request with client IP WHEN extracting context THEN IP captured."""
        from mcp_server_langgraph.middleware.audit import AuditMiddleware

        middleware = AuditMiddleware(app=MagicMock())

        request = MagicMock(spec=Request)
        request.headers.get = MagicMock(return_value=None)  # No X-Forwarded-For
        request.client.host = "192.168.1.100"

        ip = middleware.extract_ip_address(request)

        assert ip == "192.168.1.100"

    def test_extract_ip_from_x_forwarded_for(self) -> None:
        """GIVEN request with X-Forwarded-For WHEN extracting IP THEN first IP returned."""
        from mcp_server_langgraph.middleware.audit import AuditMiddleware

        middleware = AuditMiddleware(app=MagicMock())

        request = MagicMock(spec=Request)
        request.headers.get = MagicMock(
            side_effect=lambda h, default=None: "10.0.0.1, 192.168.1.1" if h.lower() == "x-forwarded-for" else None
        )
        request.client.host = "127.0.0.1"

        ip = middleware.extract_ip_address(request)

        assert ip == "10.0.0.1"


@pytest.mark.unit
@pytest.mark.xdist_group(name="audit_middleware")
class TestAuditMiddlewareEventCreation:
    """Tests for creating audit events from requests/responses."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_create_audit_event(self) -> None:
        """GIVEN request and response WHEN creating audit event THEN event is complete."""
        from mcp_server_langgraph.audit.models import AuditEventCategory, AuditEventType
        from mcp_server_langgraph.middleware.audit import AuditMiddleware

        middleware = AuditMiddleware(app=MagicMock())

        request = MagicMock(spec=Request)
        request.method = "POST"
        request.url.path = "/api/v1/workflows"
        request.client.host = "192.168.1.100"
        request.headers = {"user-agent": "Mozilla/5.0"}
        request.state = MagicMock()
        del request.state.user

        response = MagicMock(spec=Response)
        response.status_code = 201

        event = middleware.create_audit_event(
            request=request,
            response=response,
            duration_ms=150.5,
        )

        assert event.category == AuditEventCategory.DATA_MODIFICATION
        assert event.event_type == AuditEventType.DATA_CREATE
        assert event.context.http_method == "POST"
        assert event.context.http_path == "/api/v1/workflows"
        assert event.context.http_status == 201
        assert event.outcome == "success"

    def test_determine_category_from_method(self) -> None:
        """GIVEN HTTP method WHEN determining category THEN correct category returned."""
        from mcp_server_langgraph.audit.models import AuditEventCategory
        from mcp_server_langgraph.middleware.audit import AuditMiddleware

        middleware = AuditMiddleware(app=MagicMock())

        assert middleware.determine_category("GET") == AuditEventCategory.DATA_ACCESS
        assert middleware.determine_category("POST") == AuditEventCategory.DATA_MODIFICATION
        assert middleware.determine_category("PUT") == AuditEventCategory.DATA_MODIFICATION
        assert middleware.determine_category("PATCH") == AuditEventCategory.DATA_MODIFICATION
        assert middleware.determine_category("DELETE") == AuditEventCategory.DATA_MODIFICATION

    def test_determine_outcome_from_status(self) -> None:
        """GIVEN HTTP status WHEN determining outcome THEN correct outcome returned."""
        from mcp_server_langgraph.middleware.audit import AuditMiddleware

        middleware = AuditMiddleware(app=MagicMock())

        assert middleware.determine_outcome(200) == "success"
        assert middleware.determine_outcome(201) == "success"
        assert middleware.determine_outcome(204) == "success"
        assert middleware.determine_outcome(400) == "failure"
        assert middleware.determine_outcome(401) == "denied"
        assert middleware.determine_outcome(403) == "denied"
        assert middleware.determine_outcome(404) == "failure"
        assert middleware.determine_outcome(500) == "error"


@pytest.mark.unit
@pytest.mark.xdist_group(name="audit_middleware")
class TestAuditMiddlewareOpenTelemetry:
    """Tests for OpenTelemetry integration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_extract_trace_id(self) -> None:
        """GIVEN active span WHEN extracting trace info THEN trace_id captured."""
        from mcp_server_langgraph.middleware.audit import AuditMiddleware

        middleware = AuditMiddleware(app=MagicMock())

        with patch("mcp_server_langgraph.middleware.audit.trace.get_current_span") as mock_get_span:
            mock_span = MagicMock()
            mock_context = MagicMock()
            mock_context.trace_id = 0x1234567890ABCDEF1234567890ABCDEF
            mock_context.span_id = 0xABCDEF1234567890
            mock_context.is_valid = True
            mock_span.get_span_context.return_value = mock_context
            mock_get_span.return_value = mock_span

            trace_id, span_id = middleware.extract_trace_info()

            assert trace_id is not None
            assert span_id is not None

    def test_extract_trace_id_no_span(self) -> None:
        """GIVEN no active span WHEN extracting trace info THEN returns None."""
        from mcp_server_langgraph.middleware.audit import AuditMiddleware

        middleware = AuditMiddleware(app=MagicMock())

        with patch("mcp_server_langgraph.middleware.audit.trace.get_current_span") as mock_get_span:
            mock_span = MagicMock()
            mock_context = MagicMock()
            mock_context.is_valid = False
            mock_span.get_span_context.return_value = mock_context
            mock_get_span.return_value = mock_span

            trace_id, span_id = middleware.extract_trace_info()

            assert trace_id is None
            assert span_id is None


@pytest.mark.unit
@pytest.mark.xdist_group(name="audit_middleware")
class TestAuditMiddlewareErrorHandling:
    """Tests for error handling (FedRAMP AU-5)."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_audit_failure_does_not_block_request(self) -> None:
        """GIVEN audit storage failure WHEN request processed THEN request succeeds."""
        from mcp_server_langgraph.middleware.audit import AuditMiddleware

        # Create middleware with failing audit service
        app = AsyncMock(return_value=None)  # async-mock-configured (return_value set below)
        app.return_value = Response(status_code=200)

        middleware = AuditMiddleware(app=app)
        middleware.audit_service = MagicMock()
        middleware.audit_service.log_event = AsyncMock(side_effect=Exception("Database unavailable"))

        request = MagicMock(spec=Request)
        request.method = "GET"
        request.url.path = "/api/v1/workflows"
        request.client.host = "192.168.1.100"
        request.headers = {}
        request.state = MagicMock()
        del request.state.user

        # Request should still succeed despite audit failure
        call_next = AsyncMock(return_value=Response(status_code=200))
        response = await middleware.dispatch(request, call_next)

        assert response.status_code == 200
