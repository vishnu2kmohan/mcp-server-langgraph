"""
Audit Middleware for HTTP request logging.

Provides automatic audit logging for all HTTP requests, supporting:
- GDPR: Track data access and modifications
- HIPAA: Log all system activity (45 CFR 164.312(b))
- SOC 2: Access controls (CC6.x) and system operations (CC7.x)
- FedRAMP: AU-2 auditable events, AU-5 audit failure handling
- EU AI Act: Capture AI operation context

This middleware:
- Intercepts all HTTP requests (except excluded paths)
- Extracts actor from request.state.user (set by auth middleware)
- Captures request details (method, path, status, duration)
- Integrates with OpenTelemetry for trace correlation
- Handles audit failures gracefully (FedRAMP AU-5)
"""

import logging
import time
from typing import TYPE_CHECKING, Any, Literal, Protocol

# Type alias for outcome literals
AuditOutcome = Literal["success", "failure", "denied", "error"]


class AuditServiceProtocol(Protocol):
    """Protocol for audit service used by middleware."""

    async def log_event(self, event: Any) -> None:
        """Log an audit event."""
        ...


from uuid import uuid4

from opentelemetry import trace
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from mcp_server_langgraph.audit.models import (
    AuditActor,
    AuditContext,
    AuditEventCategory,
    AuditEventType,
    UnifiedAuditEvent,
)

if TYPE_CHECKING:
    from starlette.types import ASGIApp

logger = logging.getLogger(__name__)

# Global audit service instance (set during app startup)
_audit_service: Any | None = None


def get_audit_service() -> Any | None:
    """
    Get the global audit service instance.

    This function is used by the middleware to access the audit service.
    The service is configured during application startup.

    Returns:
        The audit service instance, or None if not configured.
    """
    return _audit_service


def set_audit_service(service: Any) -> None:
    """
    Set the global audit service instance.

    Called during application startup to configure audit logging.

    Args:
        service: The UnifiedAuditService instance.
    """
    global _audit_service
    _audit_service = service


# Paths to exclude from audit logging (health checks, metrics)
EXCLUDED_PATHS = frozenset(
    {
        "/health",
        "/ready",
        "/live",
        "/metrics",
        "/openapi.json",
        "/docs",
        "/redoc",
    }
)


class AuditMiddleware(BaseHTTPMiddleware):
    """
    HTTP middleware for automatic audit logging.

    Captures all HTTP requests and logs them as audit events,
    supporting regulatory compliance requirements.
    """

    def __init__(self, app: "ASGIApp", audit_service: AuditServiceProtocol | None = None) -> None:
        """
        Initialize audit middleware.

        Args:
            app: The ASGI application to wrap.
            audit_service: Optional audit service for persisting events.
                          If None, events are logged but not persisted.
        """
        super().__init__(app)
        self.audit_service = audit_service

    def should_exclude_path(self, path: str) -> bool:
        """
        Check if a path should be excluded from auditing.

        Args:
            path: The request path to check.

        Returns:
            True if the path should be excluded, False otherwise.
        """
        # Exact match
        if path in EXCLUDED_PATHS:
            return True

        # Prefix match for health check variations
        return bool(path.startswith("/health/") or path.startswith("/metrics/"))

    def extract_actor(self, request: Request) -> AuditActor:
        """
        Extract actor information from request state.

        The auth middleware sets request.state.user with JWT claims.

        Args:
            request: The Starlette request object.

        Returns:
            AuditActor with user information or anonymous actor.
        """
        try:
            user = getattr(request.state, "user", None)
            if user is None:
                return AuditActor(
                    actor_id="anonymous",
                    actor_type="user",
                )

            # Extract from JWT claims
            actor_id = user.get("sub", "anonymous")
            username = user.get("preferred_username")
            email = user.get("email")

            # Extract roles from realm_access or resource_access
            roles: list[str] = []
            realm_access = user.get("realm_access", {})
            if realm_access:
                roles = realm_access.get("roles", [])

            # Determine actor type (typed as literal for AuditActor)
            actor_type: Literal["user", "service", "system"] = "service" if actor_id.startswith("service:") else "user"

            return AuditActor(
                actor_id=actor_id,
                actor_type=actor_type,
                username=username,
                email=email,
                roles=roles,
            )
        except Exception:
            # Fallback to anonymous on any error
            return AuditActor(
                actor_id="anonymous",
                actor_type="user",
            )

    def extract_ip_address(self, request: Request) -> str | None:
        """
        Extract client IP address from request.

        Checks X-Forwarded-For header first (for proxied requests),
        then falls back to direct client IP.

        Args:
            request: The Starlette request object.

        Returns:
            Client IP address or None.
        """
        try:
            # Check X-Forwarded-For header (first IP is original client)
            forwarded = request.headers.get("x-forwarded-for")
            if forwarded:
                # Take first IP from comma-separated list
                return forwarded.split(",")[0].strip()

            # Fall back to direct client IP
            if request.client:
                return request.client.host

            return None
        except Exception:
            return None

    def extract_trace_info(self) -> tuple[str | None, str | None]:
        """
        Extract OpenTelemetry trace and span IDs.

        Returns:
            Tuple of (trace_id, span_id) or (None, None) if no active span.
        """
        try:
            span = trace.get_current_span()
            context = span.get_span_context()

            if context.is_valid:
                # Format as hex strings
                trace_id = format(context.trace_id, "032x")
                span_id = format(context.span_id, "016x")
                return trace_id, span_id

            return None, None
        except Exception:
            return None, None

    def determine_category(self, method: str) -> AuditEventCategory:
        """
        Determine event category based on HTTP method.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE, etc.)

        Returns:
            Appropriate AuditEventCategory.
        """
        if method in ("POST", "PUT", "PATCH", "DELETE"):
            return AuditEventCategory.DATA_MODIFICATION
        return AuditEventCategory.DATA_ACCESS

    def determine_event_type(self, method: str) -> AuditEventType:
        """
        Determine event type based on HTTP method.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE, etc.)

        Returns:
            Appropriate AuditEventType.
        """
        method_to_event = {
            "GET": AuditEventType.DATA_READ,
            "POST": AuditEventType.DATA_CREATE,
            "PUT": AuditEventType.DATA_UPDATE,
            "PATCH": AuditEventType.DATA_UPDATE,
            "DELETE": AuditEventType.DATA_DELETE,
        }
        return method_to_event.get(method, AuditEventType.DATA_READ)

    def determine_outcome(self, status_code: int) -> AuditOutcome:
        """
        Determine event outcome based on HTTP status code.

        Args:
            status_code: HTTP response status code.

        Returns:
            Outcome string: "success", "failure", "denied", or "error".
        """
        if 200 <= status_code < 300:
            return "success"
        if status_code in (401, 403):
            return "denied"
        if status_code >= 500:
            return "error"
        return "failure"

    def create_audit_event(
        self,
        request: Request,
        response: Response,
        duration_ms: float,
    ) -> UnifiedAuditEvent:
        """
        Create a unified audit event from request/response.

        Args:
            request: The Starlette request object.
            response: The Starlette response object.
            duration_ms: Request duration in milliseconds.

        Returns:
            Complete UnifiedAuditEvent ready for logging.
        """
        # Extract actor
        actor = self.extract_actor(request)

        # Extract trace info
        trace_id, span_id = self.extract_trace_info()

        # Extract request context
        ip_address = self.extract_ip_address(request)
        user_agent = request.headers.get("user-agent")

        # Create context
        context = AuditContext(
            request_id=str(uuid4()),
            trace_id=trace_id,
            span_id=span_id,
            ip_address=ip_address,
            user_agent=user_agent,
            http_method=request.method,
            http_path=request.url.path,
            http_status=response.status_code,
        )

        # Determine category and outcome
        category = self.determine_category(request.method)
        event_type = self.determine_event_type(request.method)
        outcome = self.determine_outcome(response.status_code)

        # Create event
        return UnifiedAuditEvent(
            category=category,
            event_type=event_type,
            actor=actor,
            resource_type="http",
            resource_id=request.url.path,
            action=f"{request.method} {request.url.path}",
            outcome=outcome,
            context=context,
            details={
                "duration_ms": duration_ms,
                "query_params": dict(request.query_params),
            },
        )

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """
        Process HTTP request and log audit event.

        Args:
            request: The incoming request.
            call_next: The next middleware or route handler.

        Returns:
            The response from the route handler.
        """
        # Skip excluded paths
        if self.should_exclude_path(request.url.path):
            return await call_next(request)

        # Record start time
        start_time = time.perf_counter()

        # Process request
        try:
            response = await call_next(request)
        except Exception as e:
            # Log error and re-raise
            duration_ms = (time.perf_counter() - start_time) * 1000

            try:
                # Create error audit event
                actor = self.extract_actor(request)
                trace_id, span_id = self.extract_trace_info()

                context = AuditContext(
                    request_id=str(uuid4()),
                    trace_id=trace_id,
                    span_id=span_id,
                    ip_address=self.extract_ip_address(request),
                    user_agent=request.headers.get("user-agent"),
                    http_method=request.method,
                    http_path=request.url.path,
                    http_status=500,
                )

                event = UnifiedAuditEvent(
                    category=self.determine_category(request.method),
                    event_type=self.determine_event_type(request.method),
                    actor=actor,
                    resource_type="http",
                    resource_id=request.url.path,
                    action=f"{request.method} {request.url.path}",
                    outcome="error",
                    context=context,
                    details={
                        "duration_ms": duration_ms,
                        "error": str(e),
                    },
                )

                logger.warning(
                    "HTTP request error audited",
                    extra={"audit_event": event.model_dump()},
                )

                # Persist if audit service available
                if self.audit_service:
                    try:
                        await self.audit_service.log_event(event)
                    except Exception as audit_error:
                        # FedRAMP AU-5: Log audit failure but don't block request
                        logger.exception(
                            "Audit logging failed (FedRAMP AU-5)",
                            extra={"error": str(audit_error)},
                        )
            except Exception as audit_error:
                logger.exception(
                    "Failed to create error audit event",
                    extra={"error": str(audit_error)},
                )

            raise

        # Calculate duration
        duration_ms = (time.perf_counter() - start_time) * 1000

        # Create and log audit event
        try:
            event = self.create_audit_event(request, response, duration_ms)

            logger.debug(
                "HTTP request audited",
                extra={"audit_event": event.model_dump()},
            )

            # Persist if audit service available
            if self.audit_service:
                try:
                    await self.audit_service.log_event(event)
                except Exception as audit_error:
                    # FedRAMP AU-5: Log audit failure but don't block request
                    logger.exception(
                        "Audit logging failed (FedRAMP AU-5)",
                        extra={"error": str(audit_error)},
                    )
        except Exception as audit_error:
            # FedRAMP AU-5: Log audit failure but don't block request
            logger.exception(
                "Failed to create audit event (FedRAMP AU-5)",
                extra={"error": str(audit_error)},
            )

        return response
