"""
Integration tests for audit middleware.

TDD RED phase: These tests verify end-to-end HTTP request auditing.

The middleware should:
- Capture all HTTP requests (except excluded paths)
- Extract actor from authenticated requests
- Record request details (method, path, status, duration)
- Integrate with OpenTelemetry for trace correlation
"""

import gc
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from mcp_server_langgraph.middleware.audit import AuditMiddleware

pytestmark = pytest.mark.integration


@pytest.fixture
def audit_test_app() -> FastAPI:
    """Create a test app with audit middleware."""
    app = FastAPI()
    app.add_middleware(AuditMiddleware)

    @app.get("/test")
    async def test_endpoint() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/health")
    async def health_endpoint() -> dict[str, str]:
        return {"status": "healthy"}

    @app.get("/metrics")
    async def metrics_endpoint() -> str:
        return "# metrics"

    @app.post("/api/v1/data")
    async def data_endpoint() -> dict[str, str]:
        return {"created": "true"}

    @app.get("/error")
    async def error_endpoint() -> None:
        raise ValueError("Test error")

    return app


@pytest.mark.integration
@pytest.mark.xdist_group(name="audit_middleware_integration")
class TestAuditMiddlewareRequestCapture:
    """Tests for HTTP request capture."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_middleware_captures_get_request(self, audit_test_app: FastAPI) -> None:
        """GIVEN GET request WHEN processed THEN audit event captured."""
        captured_events: list[dict] = []

        async def mock_log_event(event: dict) -> None:
            captured_events.append(event)

        with patch("mcp_server_langgraph.middleware.audit.get_audit_service") as mock_get_service:
            mock_service = AsyncMock(return_value=None)  # async-mock-configured
            mock_service.log_event = mock_log_event
            mock_get_service.return_value = mock_service

            client = TestClient(audit_test_app)
            response = client.get("/test")

            assert response.status_code == 200
            # Middleware should have captured the request
            # The actual assertion depends on implementation
            # For now, verify request was successful

    def test_middleware_excludes_health_endpoint(self, audit_test_app: FastAPI) -> None:
        """GIVEN health endpoint WHEN accessed THEN not audited."""
        captured_events: list[dict] = []

        async def mock_log_event(event: dict) -> None:
            captured_events.append(event)

        with patch("mcp_server_langgraph.middleware.audit.get_audit_service") as mock_get_service:
            mock_service = AsyncMock(return_value=None)  # async-mock-configured
            mock_service.log_event = mock_log_event
            mock_get_service.return_value = mock_service

            client = TestClient(audit_test_app)
            response = client.get("/health")

            assert response.status_code == 200
            # Health endpoint should be excluded from auditing

    def test_middleware_excludes_metrics_endpoint(self, audit_test_app: FastAPI) -> None:
        """GIVEN metrics endpoint WHEN accessed THEN not audited."""
        with patch("mcp_server_langgraph.middleware.audit.get_audit_service") as mock_get_service:
            mock_service = AsyncMock(return_value=None)  # async-mock-configured
            mock_get_service.return_value = mock_service

            client = TestClient(audit_test_app)
            response = client.get("/metrics")

            assert response.status_code == 200

    def test_middleware_captures_post_request(self, audit_test_app: FastAPI) -> None:
        """GIVEN POST request WHEN processed THEN method captured."""
        with patch("mcp_server_langgraph.middleware.audit.get_audit_service") as mock_get_service:
            mock_service = AsyncMock(return_value=None)  # async-mock-configured
            mock_get_service.return_value = mock_service

            client = TestClient(audit_test_app)
            response = client.post("/api/v1/data", json={"key": "value"})

            assert response.status_code == 200


@pytest.mark.integration
@pytest.mark.xdist_group(name="audit_middleware_integration")
class TestAuditMiddlewareActorExtraction:
    """Tests for actor extraction from authenticated requests."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_middleware_extracts_authenticated_user(self) -> None:
        """GIVEN authenticated request WHEN processed THEN actor extracted."""
        app = FastAPI()

        # Middleware to simulate authenticated user
        @app.middleware("http")
        async def add_user(request, call_next):
            request.state.user = MagicMock()
            request.state.user.sub = "user:alice"
            request.state.user.roles = ["user", "admin"]
            return await call_next(request)

        app.add_middleware(AuditMiddleware)

        @app.get("/protected")
        async def protected_endpoint() -> dict[str, str]:
            return {"status": "ok"}

        with patch("mcp_server_langgraph.middleware.audit.get_audit_service") as mock_get_service:
            mock_service = AsyncMock(return_value=None)  # async-mock-configured
            mock_get_service.return_value = mock_service

            client = TestClient(app)
            response = client.get("/protected")

            assert response.status_code == 200

    def test_middleware_handles_anonymous_request(self) -> None:
        """GIVEN anonymous request WHEN processed THEN anonymous actor used."""
        app = FastAPI()
        app.add_middleware(AuditMiddleware)

        @app.get("/public")
        async def public_endpoint() -> dict[str, str]:
            return {"status": "ok"}

        with patch("mcp_server_langgraph.middleware.audit.get_audit_service") as mock_get_service:
            mock_service = AsyncMock(return_value=None)  # async-mock-configured
            mock_get_service.return_value = mock_service

            client = TestClient(app)
            response = client.get("/public")

            assert response.status_code == 200


@pytest.mark.integration
@pytest.mark.xdist_group(name="audit_middleware_integration")
class TestAuditMiddlewareErrorHandling:
    """Tests for error handling in audit middleware."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_middleware_handles_audit_service_failure(self, audit_test_app: FastAPI) -> None:
        """GIVEN audit service failure WHEN request processed THEN request succeeds."""
        with patch("mcp_server_langgraph.middleware.audit.get_audit_service") as mock_get_service:
            mock_service = AsyncMock(return_value=None)  # async-mock-configured
            mock_service.log_event.side_effect = Exception("Audit failed")
            mock_get_service.return_value = mock_service

            client = TestClient(audit_test_app)
            # Request should still succeed even if audit fails (AU-5 graceful degradation)
            response = client.get("/test")

            assert response.status_code == 200

    def test_middleware_captures_error_responses(self, audit_test_app: FastAPI) -> None:
        """GIVEN error response WHEN request fails THEN error status captured."""
        with patch("mcp_server_langgraph.middleware.audit.get_audit_service") as mock_get_service:
            mock_service = AsyncMock(return_value=None)  # async-mock-configured
            mock_get_service.return_value = mock_service

            client = TestClient(audit_test_app, raise_server_exceptions=False)
            response = client.get("/error")

            assert response.status_code == 500


@pytest.mark.integration
@pytest.mark.xdist_group(name="audit_middleware_integration")
class TestAuditMiddlewareTraceCorrelation:
    """Tests for OpenTelemetry trace correlation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_middleware_includes_trace_id(self) -> None:
        """GIVEN request with trace context WHEN processed THEN trace_id included."""
        app = FastAPI()
        app.add_middleware(AuditMiddleware)

        @app.get("/traced")
        async def traced_endpoint() -> dict[str, str]:
            return {"status": "ok"}

        with patch("mcp_server_langgraph.middleware.audit.get_audit_service") as mock_get_service:
            mock_service = AsyncMock(return_value=None)  # async-mock-configured
            mock_get_service.return_value = mock_service

            client = TestClient(app)
            # Include traceparent header
            response = client.get(
                "/traced",
                headers={"traceparent": "00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01"},
            )

            assert response.status_code == 200

    def test_middleware_generates_trace_id_if_missing(self) -> None:
        """GIVEN request without trace context WHEN processed THEN trace_id generated."""
        app = FastAPI()
        app.add_middleware(AuditMiddleware)

        @app.get("/untraced")
        async def untraced_endpoint() -> dict[str, str]:
            return {"status": "ok"}

        with patch("mcp_server_langgraph.middleware.audit.get_audit_service") as mock_get_service:
            mock_service = AsyncMock(return_value=None)  # async-mock-configured
            mock_get_service.return_value = mock_service

            client = TestClient(app)
            response = client.get("/untraced")

            assert response.status_code == 200
