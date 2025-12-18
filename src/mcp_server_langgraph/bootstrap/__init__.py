"""
Bootstrap Package for Application Lifespan Initialization.

This package provides modular, testable initialization for app startup.
Each module handles a specific concern:

- observability: Logging, tracing, metrics (sync init, runs first)
- security: Auth middleware, OpenFGA client (async init)
- storage: Audit service, compliance service, schedulers (async init)
- http: HTTP client pool for external requests (async init)

Usage in app.py:
    from mcp_server_langgraph.bootstrap import bootstrap_all

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        state = await bootstrap_all(settings)
        app.state.openfga_client = state.security.openfga_client
        app.state.http_client_manager = state.http.http_client_manager
        app.state.audit_service = state.storage.audit_service
        yield
        await state.cleanup()

Benefits over monolithic lifespan:
- Testable: Each module can be tested in isolation
- Parallel-safe: No global singletons
- Fail-fast: Errors at startup, not runtime
- Maintainable: Clear separation of concerns
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcp_server_langgraph.core.config import Settings

from mcp_server_langgraph.bootstrap.observability import (
    TelemetryState,
    init_observability,
)
from mcp_server_langgraph.bootstrap.security import (
    SecurityState,
    init_auth,
)
from mcp_server_langgraph.bootstrap.storage import (
    StorageState,
    init_storage,
)
from mcp_server_langgraph.bootstrap.http import (
    HttpState,
    init_http_client,
)
from mcp_server_langgraph.bootstrap.websocket import (
    WebSocketState,
    init_websocket_lifecycle,
)
from mcp_server_langgraph.core.config.streaming import StreamingSettings


@dataclass
class AppState:
    """
    Combined application state from all bootstrap phases.

    Holds references to all initialized components and provides
    a unified cleanup method.
    """

    telemetry: TelemetryState | None = None
    security: SecurityState | None = None
    storage: StorageState | None = None
    http: HttpState | None = None
    websocket: WebSocketState | None = None

    async def cleanup(self) -> None:
        """
        Cleanup all components in reverse initialization order.

        This should be called during app shutdown to release resources.
        """
        # Cleanup in reverse order of initialization
        if self.websocket:
            await self.websocket.cleanup()

        if self.http:
            await self.http.cleanup()

        if self.storage:
            await self.storage.cleanup()

        if self.security:
            await self.security.cleanup()

        # Telemetry cleanup (if any) - usually no-op


async def bootstrap_all(settings: "Settings") -> AppState:
    """
    Bootstrap all application components.

    Initializes components in dependency order:
    1. Observability (sync, needed for logging)
    2. Security (async, OpenFGA, auth middleware)
    3. Storage (async, audit, compliance)
    4. HTTP (async, connection pool)

    Args:
        settings: Application settings

    Returns:
        AppState with all initialized components

    Example:
        async with bootstrap_all(settings) as state:
            app.state.openfga_client = state.security.openfga_client
            yield
    """
    # Phase 1: Observability (sync, needed first for logging)
    telemetry = init_observability(settings)

    # Phase 2: Security (async, OpenFGA initialization)
    security = await init_auth(settings)

    # Phase 3: Storage (async, audit service, schedulers)
    storage = await init_storage(settings)

    # Phase 4: HTTP client pool (async)
    http = await init_http_client(settings)

    # Phase 5: WebSocket lifecycle (async, cleanup tasks)
    # Extract streaming settings from main settings
    streaming_settings = StreamingSettings(
        streaming_enabled=settings.streaming_enabled,
        streaming_idle_cleanup_interval=settings.streaming_idle_cleanup_interval,
        streaming_metrics_cleanup_interval=settings.streaming_metrics_cleanup_interval,
        streaming_max_age_seconds=settings.streaming_max_age_seconds,
        streaming_max_chunk_size=settings.streaming_max_chunk_size,
        streaming_max_notifications_per_second=settings.streaming_max_notifications_per_second,
        # Security limits (previously hardcoded)
        streaming_max_connections_per_user=settings.streaming_max_connections_per_user,
        streaming_max_message_size=settings.streaming_max_message_size,
        streaming_max_messages_per_minute=settings.streaming_max_messages_per_minute,
        streaming_idle_timeout_seconds=settings.streaming_idle_timeout_seconds,
    )
    websocket = await init_websocket_lifecycle(streaming_settings=streaming_settings)

    return AppState(
        telemetry=telemetry,
        security=security,
        storage=storage,
        http=http,
        websocket=websocket,
    )


__all__ = [
    "AppState",
    "bootstrap_all",
    "TelemetryState",
    "SecurityState",
    "StorageState",
    "HttpState",
    "WebSocketState",
    "init_observability",
    "init_auth",
    "init_storage",
    "init_http_client",
    "init_websocket_lifecycle",
]
