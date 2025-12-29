"""
WebSocket Base Class.

Provides standardized WebSocket infrastructure for all endpoints including:
- Connection lifecycle management
- Authentication (JWT/Keycloak)
- Authorization (OpenFGA ReBAC)
- Message handling with standard envelope
- Ping/pong handling
- Error handling
- OpenTelemetry tracing
- Message timeout enforcement
- Metrics collection

Usage:
    class MyWebSocket(WebSocketBase):
        async def handle_message(self, message: MessageEnvelope) -> MessageEnvelope | None:
            # Handle custom message types
            if message.type == "my_action":
                return MessageEnvelope(type="my_response", payload={"ok": True})
            return None

    @router.websocket("/my-endpoint")
    async def my_endpoint(websocket: WebSocket):
        ws = MyWebSocket(config=WebSocketConfig(endpoint_name="my-endpoint"))
        await ws.run(websocket)
"""

from __future__ import annotations

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from fastapi import WebSocket
from opentelemetry import trace
from starlette.websockets import WebSocketDisconnect, WebSocketState

from mcp_server_langgraph.websocket.authz import WebSocketAuthorizationMiddleware
from mcp_server_langgraph.websocket.exceptions import (
    AuthenticationError,
    AuthorizationError,
    ProtocolVersionError,
    TokenExpiredError,
)
from mcp_server_langgraph.websocket.protocols import validate_protocol_version
from mcp_server_langgraph.websocket.token_validation import is_token_expired
from mcp_server_langgraph.websocket.heartbeat import HeartbeatManager
from mcp_server_langgraph.websocket.types import (
    AuthUser,
    ConnectionState,
    MessageEnvelope,
    MessageType,
    WebSocketConfig,
)

if TYPE_CHECKING:
    from mcp_server_langgraph.websocket.metrics import WebSocketMetrics

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


def get_auth_middleware_from_websocket(websocket: WebSocket) -> Any:
    """
    Get the authentication middleware from WebSocket app state (DI pattern).

    This is the preferred way to access auth middleware in WebSocket handlers.
    It uses proper dependency injection via app.state instead of deprecated
    global state pattern.

    Args:
        websocket: The WebSocket connection.

    Returns:
        AuthMiddleware instance or None if not configured.
    """
    from mcp_server_langgraph.auth.dependencies import (
        get_auth_middleware_from_websocket as _get,
    )

    return _get(websocket)


class WebSocketBase(ABC):
    """
    Abstract base class for WebSocket endpoints.

    Provides standardized infrastructure for:
    - Connection lifecycle (connect, authenticate, authorize, message loop, disconnect)
    - JWT authentication with Keycloak
    - OpenFGA authorization (ReBAC)
    - Standard message envelope handling
    - Ping/pong handling
    - Graceful error handling

    Subclasses must implement handle_message() for custom message types.
    Optional lifecycle hooks: on_connect(), on_disconnect(), on_error().
    """

    def __init__(
        self,
        config: WebSocketConfig,
        metrics: WebSocketMetrics | None = None,
    ) -> None:
        """
        Initialize WebSocket handler.

        Args:
            config: WebSocket configuration.
            metrics: Optional metrics collector for observability.
        """
        self.config = config
        self._state = ConnectionState.CONNECTING
        self._websocket: WebSocket | None = None
        self._user: AuthUser | None = None
        self._metrics = metrics
        self._message_timeout = config.message_timeout

        # Token validation for active connections
        self._auth_token: str | None = None
        self._validation_task: asyncio.Task[None] | None = None

        # Initialize rate limiter (Redis or in-memory based on feature flag)
        self._rate_limiter = self._create_rate_limiter()

        # Server-initiated heartbeat manager
        self._heartbeat: HeartbeatManager | None = None
        if config.heartbeat_interval > 0:
            self._heartbeat = HeartbeatManager(
                interval=config.heartbeat_interval,
                timeout=config.heartbeat_timeout,
            )

    def _create_rate_limiter(self) -> Any:
        """
        Create appropriate rate limiter based on feature flags.

        Returns Redis-backed rate limiter when enable_distributed_rate_limiting
        is True, otherwise returns in-memory rate limiter.

        Returns:
            Rate limiter instance.
        """
        from mcp_server_langgraph.websocket.rate_limiter import (
            get_websocket_rate_limiter,
        )

        return get_websocket_rate_limiter(messages_per_minute=self.config.rate_limit_per_minute)

    @property
    def state(self) -> ConnectionState:
        """Get current connection state."""
        return self._state

    @property
    def websocket(self) -> WebSocket | None:
        """Get the WebSocket connection."""
        return self._websocket

    @property
    def user(self) -> AuthUser | None:
        """Get the authenticated user."""
        return self._user

    @abstractmethod
    async def handle_message(self, message: MessageEnvelope) -> MessageEnvelope | None:
        """
        Handle an incoming WebSocket message.

        Subclasses must implement this method to handle custom message types.
        Reserved types (ping, subscribe, unsubscribe) are handled by the base class.

        Args:
            message: The incoming message envelope.

        Returns:
            Optional response message, or None if no response needed.
        """
        ...

    async def on_connect(self, user: AuthUser) -> None:  # noqa: B027
        """
        Called after successful authentication and authorization.

        Override this method to perform setup when connection is established.
        This is an optional hook - the default implementation does nothing.

        Args:
            user: The authenticated user.
        """

    async def on_disconnect(self) -> None:  # noqa: B027
        """
        Called when connection is closed (normal or error).

        Override this method to perform cleanup when connection ends.
        This is an optional hook - the default implementation does nothing.
        """

    async def on_error(self, error: Exception) -> None:  # noqa: B027
        """
        Called when an error occurs during message processing.

        Override this method to handle errors.
        This is an optional hook - the default implementation does nothing.

        Args:
            error: The exception that occurred.
        """
        pass

    async def run(self, websocket: WebSocket) -> None:
        """
        Main entry point for WebSocket connection handling.

        Handles the full lifecycle:
        1. Accept connection
        2. Authenticate user
        3. Authorize access
        4. Enter message loop
        5. Handle disconnect

        Args:
            websocket: The FastAPI WebSocket connection.
        """
        self._websocket = websocket
        self._state = ConnectionState.CONNECTING

        # Create tracing span for the entire connection
        span_name = f"websocket.{self.config.endpoint_name}"
        with tracer.start_as_current_span(span_name) as span:
            span.set_attribute("ws.endpoint", self.config.endpoint_name)

            try:
                # Accept the connection
                await websocket.accept()
                self._state = ConnectionState.CONNECTED

                # Record connection in metrics
                if self._metrics:
                    self._metrics.record_connection()

                # Validate protocol version if enabled
                if self.config.validate_protocol_version:
                    client_version = websocket.query_params.get("v")
                    is_valid, error_msg = validate_protocol_version(client_version)
                    if not is_valid:
                        if self._metrics:
                            self._metrics.record_connection_rejected(reason="protocol_version_mismatch")
                        logger.warning(
                            f"Protocol version mismatch: {error_msg}",
                            extra={
                                "endpoint": self.config.endpoint_name,
                                "client_version": client_version,
                            },
                        )
                        await self._close_with_error(
                            websocket,
                            ProtocolVersionError(
                                message=error_msg,
                                client_version=client_version,
                            ),
                        )
                        return

                # Authenticate
                self._state = ConnectionState.AUTHENTICATING
                user = await self._authenticate(websocket)
                if user is None:
                    if self._metrics:
                        self._metrics.record_connection_rejected(reason="auth_failed")
                    await self._close_with_error(
                        websocket,
                        AuthenticationError("Authentication required"),
                    )
                    return
                self._user = user
                span.set_attribute("ws.user_id", user.id)

                # Authorize
                if self.config.authz_resource_type:
                    authorized = await self._authorize(user)
                    if not authorized:
                        if self._metrics:
                            self._metrics.record_connection_rejected(reason="authz_denied")
                        await self._close_with_error(
                            websocket,
                            AuthorizationError("Authorization denied"),
                        )
                        return
                self._state = ConnectionState.AUTHORIZED

                # Call on_connect hook
                await self.on_connect(user)

                # Start server-initiated heartbeat if configured
                if self._heartbeat:
                    await self._heartbeat.start(websocket)
                    logger.debug(
                        f"Heartbeat started for {self.config.endpoint_name}",
                        extra={"interval": self.config.heartbeat_interval},
                    )

                # Start periodic token validation if configured and token available
                if self._auth_token and self.config.token_validation_interval > 0:
                    self._validation_task = asyncio.create_task(self._validate_token_periodically(websocket))
                    logger.debug(
                        f"Token validation started for {self.config.endpoint_name}",
                        extra={"interval": self.config.token_validation_interval},
                    )

                # Enter message loop
                await self._message_loop(websocket)

            except WebSocketDisconnect:
                logger.debug(f"WebSocket disconnected: {self.config.endpoint_name}")
            except Exception as e:
                logger.warning(f"WebSocket error: {e}", exc_info=True)
                span.record_exception(e)
                if self._metrics:
                    self._metrics.record_error(error_type=type(e).__name__)
                await self.on_error(e)
            finally:
                self._state = ConnectionState.DISCONNECTING

                # Cancel token validation task if running
                if self._validation_task is not None:
                    self._validation_task.cancel()
                    try:
                        await self._validation_task
                    except asyncio.CancelledError:
                        pass
                    self._validation_task = None
                    logger.debug(f"Token validation stopped for {self.config.endpoint_name}")

                # Stop heartbeat if running
                if self._heartbeat:
                    await self._heartbeat.stop()
                    logger.debug(f"Heartbeat stopped for {self.config.endpoint_name}")

                await self.on_disconnect()
                self._state = ConnectionState.DISCONNECTED

                # Record disconnect in metrics
                if self._metrics:
                    self._metrics.record_disconnect()

                # Close if still connected
                if (
                    self._websocket
                    and hasattr(self._websocket, "client_state")
                    and self._websocket.client_state == WebSocketState.CONNECTED
                ):
                    try:
                        await self._websocket.close()
                    except Exception:
                        pass

    async def _authenticate(self, websocket: WebSocket) -> AuthUser | None:
        """
        Authenticate the WebSocket connection.

        Extracts JWT token from query params or Authorization header,
        validates using AuthMiddleware, and returns user data.

        Args:
            websocket: The WebSocket connection.

        Returns:
            AuthUser if authenticated, None otherwise.
        """
        if not self.config.require_auth:
            # Return anonymous user when auth is disabled
            return AuthUser(
                id="anonymous",
                username="anonymous",
                roles=[],
            )

        # Extract token from query params (takes precedence)
        token = websocket.query_params.get("token")

        # Fallback to Authorization header
        if not token:
            auth_header = websocket.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                token = auth_header[7:]

        if not token:
            logger.debug("WebSocket auth failed: no token provided")
            return None

        try:
            auth_middleware = get_auth_middleware_from_websocket(websocket)
            if auth_middleware is None:
                logger.warning("WebSocket auth failed: auth middleware not initialized")
                return None
            result = await auth_middleware.verify_token(token)

            if not result.valid or not result.payload:
                logger.warning(
                    "WebSocket auth failed: token verification failed",
                    extra={"error": getattr(result, "error", None)},
                )
                return None

            user = AuthUser.from_jwt_payload(result.payload)
            # Store token for periodic validation during connection
            self._auth_token = token
            logger.debug(
                f"WebSocket auth success: user={user.id}",
                extra={"endpoint": self.config.endpoint_name},
            )
            return user

        except Exception as e:
            logger.warning(f"WebSocket auth error: {e}")
            return None

    async def _authorize(self, user: AuthUser) -> bool:
        """
        Authorize the WebSocket connection using OpenFGA.

        Args:
            user: The authenticated user.

        Returns:
            True if authorized, False otherwise.
        """
        if not self.config.authz_resource_type:
            return True

        authz = WebSocketAuthorizationMiddleware(
            resource_type=self.config.authz_resource_type,
            resource_id=self.config.authz_resource_id,
            required_relation=self.config.authz_required_relation,
            fail_closed=self.config.authz_fail_closed,
        )

        return await authz.authorize_connection(user.id)

    async def _validate_token_periodically(self, websocket: WebSocket) -> None:
        """
        Periodically validate the authentication token.

        If the token expires during the connection, closes the WebSocket
        with code 4010 (TokenExpiredError) to allow clients to refresh
        and reconnect.

        Args:
            websocket: The WebSocket connection to close if token expires.
        """
        try:
            while True:
                await asyncio.sleep(self.config.token_validation_interval)

                if self._auth_token is None:
                    break

                if is_token_expired(self._auth_token):
                    user_id = self._user.id if self._user else "unknown"
                    logger.warning(
                        f"Token expired for WebSocket: {self.config.endpoint_name}",
                        extra={"user_id": user_id},
                    )
                    # Record token expiration metric for observability
                    if self._metrics:
                        self._metrics.record_token_expired(user_id=user_id)
                    await self._close_with_error(websocket, TokenExpiredError())
                    break
        except asyncio.CancelledError:
            # Normal cancellation during disconnect
            raise
        except Exception as e:
            logger.warning(f"Error in token validation task: {e}")

    async def _message_loop(self, websocket: WebSocket) -> None:
        """
        Main message receive/handle loop.

        Args:
            websocket: The WebSocket connection.
        """
        while True:
            try:
                data = await websocket.receive_json()
                start_time = time.monotonic()
                message = MessageEnvelope.from_dict(data)

                # Handle reserved message types
                if message.type == MessageType.PING.value:
                    await self._send_pong(websocket, message)
                    continue

                # Handle heartbeat response (pong from client in response to server heartbeat)
                if message.type == MessageType.PONG.value:
                    if self._heartbeat:
                        await self._heartbeat.on_pong()
                    continue

                # Check rate limit for non-system messages
                if not await self._check_rate_limit():
                    # Get rate limit info for error response
                    rate_limit_info = await self._get_rate_limit_info()
                    await self._send_error(
                        websocket,
                        "Rate limit exceeded",
                        code="rate_limit_exceeded",
                        correlation_id=message.id,
                        rate_limit_info=rate_limit_info,
                    )
                    if self._metrics:
                        self._metrics.record_rate_limit_exceeded(user_id=self._user.id if self._user else "unknown")
                    continue

                # Handle custom message types with timeout and tracing
                with tracer.start_as_current_span(f"websocket.message.{message.type}") as span:
                    span.set_attribute("ws.message.type", message.type)
                    if message.id:
                        span.set_attribute("ws.message.id", message.id)

                    try:
                        # Apply message timeout
                        response = await asyncio.wait_for(
                            self.handle_message(message),
                            timeout=self._message_timeout,
                        )
                        if response:
                            await self._send_message(websocket, response)

                        # Record latency
                        latency = time.monotonic() - start_time
                        if self._metrics:
                            self._metrics.record_message_latency(
                                message_type=message.type,
                                latency_seconds=latency,
                            )

                    except TimeoutError:
                        span.set_attribute("ws.message.timeout", True)
                        logger.warning(
                            f"Message handling timed out after {self._message_timeout}s",
                            extra={"message_type": message.type},
                        )
                        if self._metrics:
                            self._metrics.record_error(error_type="timeout")
                        await self._send_error(
                            websocket,
                            f"Message processing timed out after {self._message_timeout}s",
                            code="timeout",
                            correlation_id=message.id,
                        )

            except WebSocketDisconnect:
                raise
            except ValueError as e:
                # JSON decode error
                logger.warning(f"Invalid JSON received: {e}")
                await self._send_error(websocket, str(e), code="invalid_json")
            except Exception as e:
                logger.warning(f"Error processing message: {e}")
                if self._metrics:
                    self._metrics.record_error(error_type=type(e).__name__)
                await self.on_error(e)
                await self._send_error(websocket, str(e), code="processing_error")

    async def _send_message(self, websocket: WebSocket, message: MessageEnvelope) -> None:
        """
        Send a message to the client.

        Args:
            websocket: The WebSocket connection.
            message: The message to send.
        """
        # Add timestamp if not present
        if message.timestamp is None:
            message.timestamp = datetime.now(UTC)
        await websocket.send_json(message.to_dict())

    async def _send_pong(self, websocket: WebSocket, ping_message: MessageEnvelope) -> None:
        """
        Send a pong response.

        Args:
            websocket: The WebSocket connection.
            ping_message: The ping message received.
        """
        pong = MessageEnvelope(
            type=MessageType.PONG.value,
            id=ping_message.id,
            timestamp=datetime.now(UTC),
        )
        await websocket.send_json(pong.to_dict())

    async def _send_error(
        self,
        websocket: WebSocket,
        message: str,
        code: str = "error",
        correlation_id: str | None = None,
        rate_limit_info: Any | None = None,
    ) -> None:
        """
        Send an error response.

        Args:
            websocket: The WebSocket connection.
            message: Error message.
            code: Error code.
            correlation_id: Optional correlation ID from request.
            rate_limit_info: Optional rate limit info to include in response.
        """
        payload: dict[str, Any] = {"code": code, "message": message}

        # Include rate limit info if provided
        if rate_limit_info is not None:
            payload["rate_limit"] = rate_limit_info.to_dict()

        error = MessageEnvelope(
            type=MessageType.ERROR.value,
            payload=payload,
            id=correlation_id,
            timestamp=datetime.now(UTC),
        )
        try:
            await websocket.send_json(error.to_dict())
        except Exception:
            pass  # Connection may be closed

    async def _close_with_error(
        self,
        websocket: WebSocket,
        error: Exception,
    ) -> None:
        """
        Close connection with error code.

        Args:
            websocket: The WebSocket connection.
            error: The error that caused the close.
        """
        from mcp_server_langgraph.websocket.exceptions import WebSocketError

        if isinstance(error, WebSocketError):
            code = error.code
            reason = error.reason
        else:
            code = 4000
            reason = str(error)

        try:
            await websocket.close(code=code, reason=reason)
        except Exception:
            pass

    async def send(self, message: MessageEnvelope) -> None:
        """
        Send a message to the connected client.

        Convenience method for sending messages outside the message loop.

        Args:
            message: The message to send.
        """
        if self._websocket is None:
            raise RuntimeError("WebSocket not connected")
        await self._send_message(self._websocket, message)

    async def _check_rate_limit(self) -> bool:
        """
        Check if the current user is within rate limits.

        Uses the configured rate limiter (Redis or in-memory) to check
        if the user has exceeded their message quota.

        Returns:
            True if within limits, False if exceeded.
        """
        if self._rate_limiter is None:
            return True  # No rate limiting configured

        if self._user is None:
            return True  # No user context, allow (fail-open)

        try:
            # Rate limiter may be sync (in-memory) or async (Redis)
            result = self._rate_limiter.check_message(self._user.id)
            # Handle both sync and async rate limiters
            if hasattr(result, "__await__"):
                result = await result
            return bool(result)
        except Exception as e:
            logger.warning(
                f"Rate limit check failed: {e}",
                extra={"user_id": self._user.id if self._user else "unknown"},
            )
            # Fail-open: allow message if rate limiter fails
            return True

    async def _get_rate_limit_info(self) -> Any:
        """
        Get rate limit info for the current user.

        Returns rate limit information including limit, remaining, and retry_after
        for inclusion in rate limit error responses.

        Returns:
            RateLimitInfo object or None if rate limiter not configured.
        """
        if self._rate_limiter is None:
            return None

        user_id = self._user.id if self._user else None

        try:
            # Rate limiter may be sync or async
            info = self._rate_limiter.get_rate_limit_info(user_id)
            # Handle both sync and async rate limiters
            if hasattr(info, "__await__"):
                info = await info
            return info
        except Exception as e:
            logger.warning(
                f"Failed to get rate limit info: {e}",
                extra={"user_id": user_id or "unknown"},
            )
            return None
