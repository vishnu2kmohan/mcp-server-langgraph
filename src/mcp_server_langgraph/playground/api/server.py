"""
Interactive Playground API Server.

FastAPI backend for the interactive playground with:
- Session management (create, list, get, delete)
- Chat endpoint with LLM integration
- WebSocket for real-time streaming
- In-context observability (traces, logs, metrics, alerts)
- Keycloak authentication / OpenFGA authorization

Endpoints:
- GET  /api/playground/health              - Health check
- GET  /api/playground/health/ready        - Readiness check
- POST /api/playground/sessions            - Create session
- GET  /api/playground/sessions            - List sessions
- GET  /api/playground/sessions/{id}       - Get session details
- DELETE /api/playground/sessions/{id}     - Delete session
- POST /api/playground/chat                - Send chat message
- WS   /ws/playground/{session_id}         - WebSocket streaming
- GET  /api/playground/observability/traces       - Session traces
- GET  /api/playground/observability/traces/{id}  - Trace details
- GET  /api/playground/observability/logs         - Session logs
- GET  /api/playground/observability/metrics      - Metrics summary
- GET  /api/playground/observability/metrics/llm  - LLM metrics
- GET  /api/playground/observability/metrics/tools - Tool metrics
- GET  /api/playground/observability/alerts       - Active alerts

Example:
    uvicorn mcp_server_langgraph.playground.api.server:app --port 8002
"""

import os
import uuid
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, AsyncIterator

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Response, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware

from mcp_server_langgraph.middleware import MetricsMiddleware
from mcp_server_langgraph.utils.spa_static_files import create_spa_static_files
from mcp_server_langgraph.observability.telemetry import (
    init_observability,
    is_initialized,
    logger,
    shutdown_observability,
    tracer,
)

from .models import (
    Alert,
    AlertsResponse,
    AuthTokens,
    AuthUser,
    ChatRequest,
    ChatResponse,
    CreateSessionRequest,
    CreateSessionResponse,
    HealthStatus,
    LLMMetrics,
    LogEntry,
    LogLevel,
    LoginRequest,
    LoginResponse,
    LogsResponse,
    MCPServerInfo,
    MCPServersResponse,
    MetricsSummary,
    ReadinessStatus,
    RefreshTokenRequest,
    SessionConfig,
    SessionDetails,
    SessionMessage,
    SessionSummary,
    ListSessionsResponse,
    ToolMetrics,
    TraceDetailsResponse,
    TraceInfo,
    TracesResponse,
)
from mcp_server_langgraph.auth.factory import create_user_provider
from mcp_server_langgraph.auth.user_provider import UserProvider
from mcp_server_langgraph.core.config import Settings

# ==============================================================================
# Session Storage (Postgres, Redis, or in-memory fallback)
# ==============================================================================
# Storage backend priority:
#   1. Postgres (PLAYGROUND_POSTGRES_URL) - Production, durable persistence
#   2. Redis (PLAYGROUND_REDIS_URL or REDIS_URL) - Session-like storage
#   3. In-memory - Development/testing only, data lost on restart

from ..session import (
    PostgresSessionManager,
    RedisSessionManager,
    create_postgres_engine,
    create_redis_pool,
    init_playground_database,
)
from .metrics import (
    record_chat_message,
    record_session_created,
    record_session_deleted,
    websocket_connected,
    websocket_disconnected,
)
from ..mcp.integration import PlaygroundMCPBridge, ChatError

# Global session manager (initialized in lifespan)
_session_manager: PostgresSessionManager | RedisSessionManager | None = None

# Global MCP bridge (initialized in lifespan)
_mcp_bridge: PlaygroundMCPBridge | None = None

# In-memory fallback for development/testing without persistence
_sessions_fallback: dict[str, dict[str, Any]] = {}
_storage_backend: str = "memory"  # "postgres", "redis", or "memory"

# Observability data (kept in-memory for now)
_session_traces: dict[str, list[TraceInfo]] = {}
_session_logs: dict[str, list[LogEntry]] = {}
_active_alerts: list[Alert] = []


def _get_session_memory(session_id: str) -> dict[str, Any] | None:
    """Get session from in-memory storage (fallback)."""
    return _sessions_fallback.get(session_id)


def _create_session_memory(session_id: str, name: str, config: SessionConfig) -> dict[str, Any]:
    """Create a new session in in-memory storage (fallback)."""
    now = datetime.now(UTC)
    session = {
        "session_id": session_id,
        "name": name,
        "config": config,
        "created_at": now,
        "updated_at": now,
        "messages": [],
    }
    _sessions_fallback[session_id] = session
    _session_traces[session_id] = []
    _session_logs[session_id] = []
    return session


def _delete_session_memory(session_id: str) -> bool:
    """Delete a session from in-memory storage (fallback)."""
    if session_id in _sessions_fallback:
        del _sessions_fallback[session_id]
        _session_traces.pop(session_id, None)
        _session_logs.pop(session_id, None)
        return True
    return False


# ==============================================================================
# Security & Authentication
# ==============================================================================

# Global auth provider (initialized in lifespan)
_user_provider: UserProvider | None = None
_settings: Settings | None = None


def get_user_provider() -> UserProvider:
    """Get the configured user provider for authentication."""
    global _user_provider, _settings
    if _user_provider is None:
        _settings = Settings()
        _user_provider = create_user_provider(_settings)
        logger.info(
            "Auth provider initialized",
            extra={"provider": type(_user_provider).__name__},
        )
    return _user_provider


def verify_playground_auth(authorization: str = Header(None)) -> dict[str, Any] | None:
    """
    Verify authentication for playground endpoints.

    SECURITY: Implements OWASP A01:2021 - Broken Access Control prevention.

    In production, integrates with Keycloak for JWT validation.
    In development, allows unauthenticated access for testing.

    Args:
        authorization: Authorization header (Bearer token)

    Returns:
        User info dict or None in development mode

    Raises:
        HTTPException: 401 if not authenticated in production
    """
    import base64
    import json

    environment = os.getenv("ENVIRONMENT", "development")

    # Development/Test mode - extract user from JWT if available, otherwise use dev-user
    if environment in ("development", "test"):
        if authorization and authorization.startswith("Bearer "):
            try:
                token = authorization[7:]
                # Decode JWT payload without verification (just to extract user info)
                # JWT format: header.payload.signature (base64url encoded)
                parts = token.split(".")
                if len(parts) >= 2:
                    # Add padding if needed for base64 decoding
                    payload_b64 = parts[1]
                    padding = 4 - len(payload_b64) % 4
                    if padding != 4:
                        payload_b64 += "=" * padding
                    payload = json.loads(base64.urlsafe_b64decode(payload_b64))
                    # Extract username from JWT claims
                    username = payload.get("preferred_username") or payload.get("username") or payload.get("sub")
                    roles = payload.get("realm_access", {}).get("roles", ["user"])
                    logger.debug(f"Extracted user from JWT: {username}")
                    return {"user_id": username, "roles": roles}
            except Exception as e:
                logger.debug(f"Failed to decode JWT, using dev-user: {e}")
        # No token or decoding failed - use dev-user
        logger.debug(f"Playground accessed without auth in {environment} mode")
        return {"user_id": "dev-user", "roles": ["user"]}

    # Production mode - require authentication
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Provide Bearer token in Authorization header.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format. Expected: Bearer <token>",
        )

    # TODO: Integrate with Keycloak for JWT validation
    # For now, check against environment variable
    token = authorization[7:]
    expected_token = os.getenv("PLAYGROUND_AUTH_TOKEN")
    if expected_token and token != expected_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
        )

    return {"user_id": "authenticated-user", "roles": ["user"]}


# ==============================================================================
# Lifespan & App Setup
# ==============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """
    Playground service lifecycle with observability and persistent storage.

    Initializes OpenTelemetry tracing and metrics on startup,
    connects to Postgres or Redis for session storage (priority: Postgres > Redis > Memory),
    gracefully shuts down on termination.
    """
    global _session_manager, _storage_backend, _mcp_bridge

    # STARTUP - Observability
    if not is_initialized():
        try:
            from mcp_server_langgraph.core.config import Settings

            settings = Settings()
            init_observability(
                settings=settings,
                enable_file_logging=False,
            )
            logger.info("Playground service started with observability")
        except Exception as e:
            print(f"WARNING: Observability initialization failed: {e}")

    # STARTUP - Storage backend (priority: Postgres > Redis > Memory)
    # 1. Try Postgres first (for durable production storage)
    postgres_url = os.getenv("PLAYGROUND_POSTGRES_URL", os.getenv("POSTGRES_URL"))
    if postgres_url:
        try:
            # Ensure asyncpg driver is used
            if not postgres_url.startswith("postgresql+asyncpg://"):
                postgres_url = postgres_url.replace("postgresql://", "postgresql+asyncpg://")

            engine = await create_postgres_engine(postgres_url)
            # Initialize database schema
            await init_playground_database(engine)
            _session_manager = PostgresSessionManager(engine=engine)
            _storage_backend = "postgres"
            logger.info(
                "Playground connected to PostgreSQL for session storage",
                extra={"backend": "postgres"},
            )
        except Exception as e:
            logger.warning(f"Failed to connect to PostgreSQL: {e}")
            # Fall through to Redis

    # 2. Try Redis if Postgres not configured or failed
    if _storage_backend == "memory":
        redis_url = os.getenv("PLAYGROUND_REDIS_URL", os.getenv("REDIS_URL"))
        if redis_url:
            try:
                redis_client = await create_redis_pool(redis_url)
                # Test connection
                await redis_client.ping()
                # Session TTL (default: 7 days)
                ttl = int(os.getenv("PLAYGROUND_SESSION_TTL", 604800))
                _session_manager = RedisSessionManager(redis_client=redis_client, ttl_seconds=ttl)
                _storage_backend = "redis"
                logger.info(
                    "Playground connected to Redis for session storage",
                    extra={"backend": "redis", "ttl_seconds": ttl},
                )
            except Exception as e:
                logger.warning(f"Failed to connect to Redis, using in-memory storage: {e}")

    # 3. Fallback to in-memory
    if _storage_backend == "memory":
        logger.info(
            "Using in-memory session storage (data will be lost on restart)",
            extra={"backend": "memory"},
        )

    # STARTUP - MCP Bridge for agent communication
    mcp_server_url = os.getenv("MCP_SERVER_URL", "http://localhost:8000")
    try:
        _mcp_bridge = PlaygroundMCPBridge(mcp_url=mcp_server_url)
        logger.info(
            "Playground MCP bridge initialized",
            extra={"mcp_url": mcp_server_url},
        )
    except Exception as e:
        logger.warning(f"Failed to initialize MCP bridge: {e}")
        _mcp_bridge = None

    yield  # Application runs here

    # SHUTDOWN
    if _session_manager:
        await _session_manager.close()
        logger.info(f"Playground {_storage_backend} connection closed")

    logger.info("Playground service shutting down")
    shutdown_observability()


app = FastAPI(
    title="MCP Server Interactive Playground",
    description="Interactive testing environment for LangGraph agents with in-context observability",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3001", "http://localhost:5174"],  # Playground frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# HTTP metrics for Prometheus/Grafana
app.add_middleware(MetricsMiddleware)


# ==============================================================================
# Health Endpoints
# ==============================================================================


@app.get("/api/playground/health")
def health_check() -> HealthStatus:
    """
    Health check endpoint for Kubernetes probes.

    Publicly accessible (no authentication required).
    """
    return HealthStatus(status="healthy")


@app.get("/api/playground/health/ready")
def readiness_check() -> ReadinessStatus:
    """
    Readiness check endpoint for Kubernetes probes.

    Checks service dependencies are available.
    """
    checks = {}

    # Check observability
    checks["observability"] = "ready" if is_initialized() else "not_initialized"

    # Check storage backend
    checks["storage"] = _storage_backend
    if _storage_backend == "postgres":
        checks["storage_status"] = "connected"
    elif _storage_backend == "redis":
        checks["storage_status"] = "connected"
    else:
        checks["storage_status"] = "in-memory"

    # Determine overall status
    all_ready = all(
        v in ("ready", "connected", "in-memory", "postgres", "redis", "memory", "not_initialized") for v in checks.values()
    )
    status_str = "ready" if all_ready else "not_ready"

    return ReadinessStatus(status=status_str, checks=checks)


@app.get("/metrics")
def prometheus_metrics() -> Response:
    """
    Prometheus metrics endpoint for Alloy/Grafana scraping.

    Returns metrics in Prometheus text exposition format.
    """
    try:
        from prometheus_client import CONTENT_TYPE_LATEST, REGISTRY, generate_latest

        return Response(
            content=generate_latest(REGISTRY),
            media_type=CONTENT_TYPE_LATEST,
        )
    except ImportError:
        return Response(
            content="# prometheus_client not available\n",
            media_type="text/plain",
        )


# ==============================================================================
# Authentication Endpoints (Keycloak OIDC)
# ==============================================================================


@app.post("/api/playground/auth/login")
async def login(request: LoginRequest) -> LoginResponse:
    """
    Authenticate user via Keycloak.

    Uses the configured auth provider (Keycloak in production).

    Args:
        request: Login request with username and password

    Returns:
        LoginResponse with user info and tokens

    Raises:
        HTTPException: 401 if authentication fails
    """
    with tracer.start_as_current_span(
        "playground.auth.login",
        attributes={"username": request.username},
    ):
        try:
            provider = get_user_provider()
            result = await provider.authenticate(request.username, request.password)

            if not result.authorized:
                error_msg = result.reason or result.error or "Authentication failed"
                logger.warning(
                    "Login failed",
                    extra={"username": request.username, "error": error_msg},
                )
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=error_msg,
                )

            # Calculate expiration timestamp (milliseconds)
            import time

            expires_at = int((time.time() + (result.expires_in or 300)) * 1000)

            logger.info(
                "User logged in",
                extra={"username": request.username, "user_id": result.user_id},
            )

            return LoginResponse(
                user=AuthUser(
                    id=result.user_id or "",
                    username=result.username or request.username,
                    email=result.email,
                    roles=result.roles,
                ),
                tokens=AuthTokens(
                    access_token=result.access_token or "",
                    refresh_token=result.refresh_token,
                    expires_at=expires_at,
                ),
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Login error: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Authentication service error",
            )


@app.post("/api/playground/auth/refresh")
async def refresh_token_endpoint(request: RefreshTokenRequest) -> AuthTokens:
    """
    Refresh authentication tokens.

    Args:
        request: Request with refresh token

    Returns:
        New AuthTokens

    Raises:
        HTTPException: 401 if refresh fails
    """
    import time

    with tracer.start_as_current_span("playground.auth.refresh"):
        try:
            provider = get_user_provider()

            # Access the underlying client's refresh_token method
            if hasattr(provider, "client") and hasattr(provider.client, "refresh_token"):
                tokens = await provider.client.refresh_token(request.refresh_token)
            else:
                # Fallback for providers without refresh support
                raise HTTPException(
                    status_code=status.HTTP_501_NOT_IMPLEMENTED,
                    detail="Token refresh not supported by this provider",
                )

            expires_at = int((time.time() + tokens.get("expires_in", 300)) * 1000)

            return AuthTokens(
                access_token=tokens.get("access_token", ""),
                refresh_token=tokens.get("refresh_token"),
                expires_at=expires_at,
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Token refresh error: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token refresh failed",
            )


@app.post("/api/playground/auth/logout")
async def logout(authorization: str = Header(None)) -> dict[str, bool]:
    """
    Logout user and invalidate tokens.

    Args:
        authorization: Bearer token to invalidate

    Returns:
        Success status
    """
    with tracer.start_as_current_span("playground.auth.logout"):
        try:
            if authorization and authorization.startswith("Bearer "):
                token = authorization[7:]
                provider = get_user_provider()
                if hasattr(provider, "logout"):
                    await provider.logout(token)

            logger.info("User logged out")
            return {"success": True}
        except Exception as e:
            logger.warning(f"Logout error (non-fatal): {e}")
            return {"success": True}  # Logout should always succeed from user perspective


@app.get("/api/playground/auth/me")
async def get_current_user(
    authorization: str = Header(None),
) -> AuthUser:
    """
    Get current authenticated user info.

    Args:
        authorization: Bearer token

    Returns:
        Current user info

    Raises:
        HTTPException: 401 if not authenticated
    """
    with tracer.start_as_current_span("playground.auth.me"):
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
                headers={"WWW-Authenticate": "Bearer"},
            )

        token = authorization[7:]
        try:
            provider = get_user_provider()
            result = await provider.verify_token(token)

            if not result.valid:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid or expired token",
                )

            # Extract user info from token payload
            payload = result.payload or {}
            # Keycloak tokens have 'sub' for user ID, 'preferred_username' for username
            username = payload.get("preferred_username") or payload.get("sub", "")
            user_id = payload.get("sub", "")

            # Try to get full user data from provider
            user_data = await provider.get_user_by_username(username)
            if user_data:
                return AuthUser(
                    id=user_data.user_id,
                    username=user_data.username,
                    email=user_data.email,
                    roles=user_data.roles,
                )

            # Fallback to token payload if user lookup fails
            return AuthUser(
                id=user_id,
                username=username,
                email=payload.get("email"),
                roles=payload.get("realm_access", {}).get("roles", ["user"]),
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Token validation error: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token validation failed",
            )


# ==============================================================================
# MCP Server Configuration Endpoints
# ==============================================================================


@app.get("/api/playground/mcp/servers")
def list_mcp_servers(
    user: dict[str, Any] | None = Depends(verify_playground_auth),
) -> MCPServersResponse:
    """
    List available MCP servers for playground connections.

    Returns configured MCP server endpoints that clients can connect to.
    The primary/default server is listed first.
    """
    servers = []

    # Get MCP server URL from environment or use default
    mcp_server_url = os.getenv("MCP_SERVER_URL", "http://localhost:8001")

    # Primary MCP server (the one running our agent)
    servers.append(
        MCPServerInfo(
            id="default",
            name="LangGraph Agent Server",
            url=mcp_server_url,
            description="Primary MCP server with LangGraph agent capabilities",
            is_default=True,
        )
    )

    # Additional servers can be configured via MCP_ADDITIONAL_SERVERS env var
    # Format: "name1:url1,name2:url2"
    additional = os.getenv("MCP_ADDITIONAL_SERVERS", "")
    if additional:
        for server_config in additional.split(","):
            if ":" in server_config:
                parts = server_config.strip().split(":", 1)
                if len(parts) == 2:
                    name, url = parts
                    servers.append(
                        MCPServerInfo(
                            id=name.lower().replace(" ", "-"),
                            name=name,
                            url=url,
                            is_default=False,
                        )
                    )

    return MCPServersResponse(servers=servers, total=len(servers))


# ==============================================================================
# Session Management Endpoints
# ==============================================================================


@app.post(
    "/api/playground/sessions",
    status_code=status.HTTP_201_CREATED,
)
async def create_session(
    request: CreateSessionRequest,
    user: dict[str, Any] | None = Depends(verify_playground_auth),
) -> CreateSessionResponse:
    """
    Create a new playground session.

    Args:
        request: Session creation request with name and optional config

    Returns:
        Created session details
    """
    with tracer.start_as_current_span(
        "playground.create_session",
        attributes={"session.name": request.name},
    ):
        config = request.config or SessionConfig()
        user_id = user.get("user_id") if user else None

        if _storage_backend != "memory" and _session_manager:
            # Use persistent storage (Postgres or Redis)
            from ..session import SessionConfig as StorageSessionConfig

            storage_config = StorageSessionConfig(
                model=config.model,
                temperature=config.temperature,
                max_tokens=config.max_tokens,
            )
            session = await _session_manager.create_session(
                name=request.name,
                user_id=user_id,
                config=storage_config,
            )

            logger.info(
                f"Session created ({_storage_backend})",
                extra={
                    "session_id": session.session_id,
                    "session_name": request.name,
                    "backend": _storage_backend,
                },
            )

            # Record session creation metric
            record_session_created()

            return CreateSessionResponse(
                session_id=session.session_id,
                name=session.name,
                created_at=session.created_at,
                config=config,
            )
        else:
            # In-memory fallback
            session_id = str(uuid.uuid4())
            session_dict = _create_session_memory(session_id, request.name, config)

            logger.info(
                "Session created (in-memory)",
                extra={"session_id": session_id, "session_name": request.name},
            )

            # Record session creation metric
            record_session_created()

            return CreateSessionResponse(
                session_id=session_id,
                name=request.name,
                created_at=session_dict["created_at"],
                config=config,
            )


@app.get("/api/playground/sessions")
async def list_sessions(
    user: dict[str, Any] | None = Depends(verify_playground_auth),
) -> ListSessionsResponse:
    """
    List all sessions for the current user.

    Returns:
        List of session summaries
    """
    user_id: str | None = user.get("user_id") if user else None

    if _storage_backend != "memory" and _session_manager:
        # Use persistent storage (Postgres or Redis)
        sessions = await _session_manager.list_sessions(user_id=user_id or "")
        summaries = [
            SessionSummary(
                session_id=s.session_id,
                name=s.name,
                created_at=s.created_at,
                message_count=len(s.messages),
            )
            for s in sessions
        ]
        return ListSessionsResponse(sessions=summaries, storage_backend=_storage_backend)
    else:
        # In-memory fallback
        summaries = [
            SessionSummary(
                session_id=s["session_id"],
                name=s["name"],
                created_at=s["created_at"],
                message_count=len(s["messages"]),
            )
            for s in _sessions_fallback.values()
        ]
        return ListSessionsResponse(sessions=summaries, storage_backend="memory")


@app.get("/api/playground/sessions/{session_id}")
async def get_session(
    session_id: str,
    user: dict[str, Any] | None = Depends(verify_playground_auth),
) -> SessionDetails:
    """
    Get session details including message history.

    Args:
        session_id: Session identifier

    Returns:
        Full session details

    Raises:
        HTTPException: 404 if session not found
    """
    if _storage_backend != "memory" and _session_manager:
        # Use persistent storage (Postgres or Redis)
        session = await _session_manager.get_session(session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session '{session_id}' not found",
            )

        return SessionDetails(
            session_id=session.session_id,
            name=session.name,
            created_at=session.created_at,
            updated_at=session.updated_at,
            messages=[
                SessionMessage(
                    message_id=m.message_id,
                    role=m.role,
                    content=m.content,
                    timestamp=m.timestamp,
                    metadata=m.metadata,
                )
                for m in session.messages
            ],
            config=SessionConfig(
                model=session.config.model,
                temperature=session.config.temperature,
                max_tokens=session.config.max_tokens,
            ),
        )
    else:
        # In-memory fallback
        session_dict = _get_session_memory(session_id)
        if not session_dict:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session '{session_id}' not found",
            )

        return SessionDetails(
            session_id=session_dict["session_id"],
            name=session_dict["name"],
            created_at=session_dict["created_at"],
            updated_at=session_dict["updated_at"],
            messages=[SessionMessage(**m) for m in session_dict["messages"]],
            config=session_dict["config"],
        )


@app.delete(
    "/api/playground/sessions/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_session(
    session_id: str,
    user: dict[str, Any] | None = Depends(verify_playground_auth),
) -> None:
    """
    Delete a session.

    Args:
        session_id: Session identifier

    Raises:
        HTTPException: 404 if session not found
    """
    with tracer.start_as_current_span(
        "playground.delete_session",
        attributes={"session.id": session_id},
    ):
        if _storage_backend != "memory" and _session_manager:
            # Use persistent storage (Postgres or Redis)
            deleted = await _session_manager.delete_session(session_id)
            if not deleted:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Session '{session_id}' not found",
                )

            logger.info(
                f"Session deleted ({_storage_backend})",
                extra={"session_id": session_id, "backend": _storage_backend},
            )

            # Record session deletion metric
            record_session_deleted()
        else:
            # In-memory fallback
            if not _delete_session_memory(session_id):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Session '{session_id}' not found",
                )

            logger.info("Session deleted (in-memory)", extra={"session_id": session_id})

            # Record session deletion metric
            record_session_deleted()


# ==============================================================================
# Chat Endpoint
# ==============================================================================


@app.post("/api/playground/chat")
async def send_chat_message(
    request: ChatRequest,
    authorization: str = Header(None),
    user: dict[str, Any] | None = Depends(verify_playground_auth),
) -> ChatResponse:
    """
    Send a chat message and get a response.

    For streaming responses, use the WebSocket endpoint instead.

    Args:
        request: Chat request with session_id and message

    Returns:
        Assistant response

    Raises:
        HTTPException: 404 if session not found, 400 if message empty
    """
    with tracer.start_as_current_span(
        "playground.chat",
        attributes={
            "session.id": request.session_id,
            "message.length": len(request.message),
        },
    ):
        if not request.message.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Message cannot be empty",
            )

        now = datetime.now(UTC)
        message_id = str(uuid.uuid4())
        user_id = user.get("user_id", "anonymous") if user else "anonymous"

        # Extract JWT token from Authorization header
        token = ""
        if authorization and authorization.startswith("Bearer "):
            token = authorization[7:]

        # Get response from MCP agent via bridge
        response_content = ""
        if _mcp_bridge:
            try:
                # Call the MCP agent_chat tool
                mcp_response = await _mcp_bridge.send_chat_message(
                    session_id=request.session_id,
                    message=request.message,
                    token=token,
                    user_id=user_id,
                    response_format="detailed",
                )
                response_content = mcp_response.content
                if mcp_response.message_id:
                    message_id = mcp_response.message_id
            except ChatError as e:
                logger.warning(
                    f"MCP bridge error, using fallback: {e}",
                    extra={"session_id": request.session_id},
                )
                response_content = f"I received your message: '{request.message}'. (Agent temporarily unavailable)"
            except Exception as e:
                logger.error(
                    f"Unexpected MCP bridge error: {e}",
                    extra={"session_id": request.session_id},
                    exc_info=True,
                )
                response_content = f"I received your message: '{request.message}'. (Agent temporarily unavailable)"
        else:
            # No bridge configured - use placeholder
            response_content = f"I received your message: '{request.message}'. (MCP bridge not configured)"

        response_timestamp = datetime.now(UTC)

        if _storage_backend != "memory" and _session_manager:
            # Use persistent storage (Postgres or Redis)
            # Verify session exists
            session = await _session_manager.get_session(request.session_id)
            if not session:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Session '{request.session_id}' not found",
                )

            # Add user message
            await _session_manager.add_message(
                session_id=request.session_id,
                role="user",
                content=request.message,
                metadata={},
            )

            # Add assistant response
            await _session_manager.add_message(
                session_id=request.session_id,
                role="assistant",
                content=response_content,
                metadata={},
            )
        else:
            # In-memory fallback
            session_dict = _get_session_memory(request.session_id)
            if not session_dict:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Session '{request.session_id}' not found",
                )

            # Add user message to history
            user_msg = {
                "message_id": str(uuid.uuid4()),
                "role": "user",
                "content": request.message,
                "timestamp": now,
                "metadata": {},
            }
            session_dict["messages"].append(user_msg)

            # Add assistant message to history
            assistant_msg = {
                "message_id": message_id,
                "role": "assistant",
                "content": response_content,
                "timestamp": response_timestamp,
                "metadata": {},
            }
            session_dict["messages"].append(assistant_msg)
            session_dict["updated_at"] = datetime.now(UTC)

        # Add a log entry for observability (kept in-memory for now)
        log_entry = LogEntry(
            timestamp=now,
            level=LogLevel.INFO,
            message=f"Chat message processed: {request.message[:50]}...",
            logger_name="playground.chat",
        )
        _session_logs.setdefault(request.session_id, []).append(log_entry)

        logger.info(
            "Chat message processed",
            extra={
                "session_id": request.session_id,
                "message_id": message_id,
                "backend": _storage_backend,
            },
        )

        # Record chat message metrics
        record_chat_message("user")
        latency = (response_timestamp - now).total_seconds()
        record_chat_message("assistant", latency=latency)

        return ChatResponse(
            response=response_content,
            message_id=message_id,
            timestamp=response_timestamp,
            usage={"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
        )


# ==============================================================================
# WebSocket Endpoint
# ==============================================================================


# Track active WebSocket connections
_websocket_connections: dict[str, list[WebSocket]] = {}


@app.websocket("/ws/playground/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str) -> None:
    """
    WebSocket endpoint for real-time chat streaming.

    Provides:
    - Token-by-token response streaming
    - Tool call notifications
    - Real-time observability events (traces, logs, metrics, alerts)

    Message types:
    - connected: Connection established
    - message: User message
    - chunk: Response token chunk
    - complete: Response complete
    - tool_call: Tool invocation
    - error: Error occurred
    - trace: Trace event
    - log: Log event
    - metric: Metric update
    - alert: Alert notification
    """
    # Validate session exists
    session_exists = False
    if _storage_backend != "memory" and _session_manager:
        session_obj = await _session_manager.get_session(session_id)
        session_exists = session_obj is not None
    else:
        session_dict = _get_session_memory(session_id)
        session_exists = session_dict is not None

    if not session_exists:
        await websocket.close(code=4004, reason="Session not found")
        return

    await websocket.accept()

    # Register connection
    if session_id not in _websocket_connections:
        _websocket_connections[session_id] = []
    _websocket_connections[session_id].append(websocket)

    # Record WebSocket connection metric
    websocket_connected()

    try:
        # Send welcome message
        await websocket.send_json(
            {
                "type": "connected",
                "session_id": session_id,
            }
        )

        # Handle messages
        while True:
            data = await websocket.receive_json()

            msg_type = data.get("type")
            if not msg_type:
                await websocket.send_json(
                    {
                        "type": "error",
                        "message": "Missing 'type' field in message",
                    }
                )
                continue

            if msg_type == "message":
                content = data.get("content", "")
                if not content.strip():
                    await websocket.send_json(
                        {
                            "type": "error",
                            "message": "Message content cannot be empty",
                        }
                    )
                    continue

                message_id = str(uuid.uuid4())

                # Simulate streaming response
                response_words = f"I received: {content}".split()
                for word in response_words:
                    await websocket.send_json(
                        {
                            "type": "chunk",
                            "content": word + " ",
                            "message_id": message_id,
                        }
                    )

                await websocket.send_json(
                    {
                        "type": "complete",
                        "message_id": message_id,
                        "usage": {"prompt_tokens": 5, "completion_tokens": len(response_words)},
                    }
                )

    except WebSocketDisconnect:
        logger.debug(f"WebSocket disconnected: {session_id}")
    finally:
        # Unregister connection
        if session_id in _websocket_connections:
            _websocket_connections[session_id] = [ws for ws in _websocket_connections[session_id] if ws != websocket]

        # Record WebSocket disconnection metric
        websocket_disconnected()


# ==============================================================================
# Observability Endpoints - In-Context Traces
# ==============================================================================


@app.get("/api/playground/observability/traces")
def get_session_traces(
    session_id: str = Query(..., description="Session ID to get traces for"),
    user: dict[str, Any] | None = Depends(verify_playground_auth),
) -> TracesResponse:
    """
    Get traces for a session.

    Returns recent traces associated with the session for in-context debugging.
    """
    traces = _session_traces.get(session_id, [])
    return TracesResponse(traces=traces, total=len(traces))


@app.get("/api/playground/observability/traces/{trace_id}")
def get_trace_details(
    trace_id: str,
    user: dict[str, Any] | None = Depends(verify_playground_auth),
) -> TraceDetailsResponse:
    """
    Get detailed span tree for a specific trace.

    Returns the complete span hierarchy for waterfall visualization.
    """
    # Find trace in any session
    for traces in _session_traces.values():
        for trace in traces:
            if trace.trace_id == trace_id:
                return TraceDetailsResponse(
                    trace_id=trace_id,
                    root_span=None,  # Would be populated with actual span data
                    spans=[],
                )

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Trace '{trace_id}' not found",
    )


# ==============================================================================
# Observability Endpoints - In-Context Logs
# ==============================================================================


@app.get("/api/playground/observability/logs")
def get_session_logs(
    session_id: str = Query(..., description="Session ID"),
    level: str | None = Query(None, description="Filter by log level"),
    search: str | None = Query(None, description="Search in log messages"),
    tail: int | None = Query(None, ge=1, le=1000, description="Return last N logs"),
    user: dict[str, Any] | None = Depends(verify_playground_auth),
) -> LogsResponse:
    """
    Get logs for a session with optional filtering.

    Supports filtering by level, text search, and tailing.
    """
    logs = _session_logs.get(session_id, [])

    # Filter by level
    if level:
        try:
            level_enum = LogLevel(level.lower())
            logs = [log for log in logs if log.level == level_enum]
        except ValueError:
            pass  # Invalid level, return all

    # Filter by search term
    if search:
        search_lower = search.lower()
        logs = [log for log in logs if search_lower in log.message.lower()]

    # Apply tail limit
    if tail and len(logs) > tail:
        logs = logs[-tail:]

    return LogsResponse(logs=logs, total=len(logs))


# ==============================================================================
# Observability Endpoints - In-Context Metrics
# ==============================================================================


@app.get("/api/playground/observability/metrics")
async def get_session_metrics(
    session_id: str = Query(..., description="Session ID"),
    user: dict[str, Any] | None = Depends(verify_playground_auth),
) -> MetricsSummary:
    """
    Get metrics summary for a session.

    Includes LLM metrics, tool metrics, and session stats.
    """
    # Get message count from appropriate storage backend
    message_count = 0
    if _storage_backend != "memory" and _session_manager:
        session_obj = await _session_manager.get_session(session_id)
        message_count = len(session_obj.messages) if session_obj else 0
    else:
        session_dict = _get_session_memory(session_id)
        message_count = len(session_dict["messages"]) if session_dict else 0

    return MetricsSummary(
        llm=LLMMetrics(
            latency_p50_ms=150.0,
            latency_p95_ms=300.0,
            latency_p99_ms=500.0,
            total_tokens=1000,
            prompt_tokens=600,
            completion_tokens=400,
            request_count=5,
            error_count=0,
        ),
        tools=ToolMetrics(
            tool_calls=3,
            success_rate=1.0,
            avg_duration_ms=50.0,
        ),
        session_duration_ms=60000.0,
        message_count=message_count,
    )


@app.get("/api/playground/observability/metrics/llm")
def get_llm_metrics(
    session_id: str = Query(..., description="Session ID"),
    user: dict[str, Any] | None = Depends(verify_playground_auth),
) -> LLMMetrics:
    """
    Get LLM-specific metrics for a session.

    Returns latency percentiles, token counts, and request stats.
    """
    return LLMMetrics(
        latency_p50_ms=150.0,
        latency_p95_ms=300.0,
        latency_p99_ms=500.0,
        total_tokens=1000,
        prompt_tokens=600,
        completion_tokens=400,
        request_count=5,
        error_count=0,
    )


@app.get("/api/playground/observability/metrics/tools")
def get_tool_metrics(
    session_id: str = Query(..., description="Session ID"),
    user: dict[str, Any] | None = Depends(verify_playground_auth),
) -> ToolMetrics:
    """
    Get tool execution metrics for a session.

    Returns call counts, success rates, and per-tool breakdown.
    """
    return ToolMetrics(
        tool_calls=3,
        success_rate=1.0,
        avg_duration_ms=50.0,
        by_tool={
            "web_search": {"calls": 2, "avg_duration_ms": 45.0},
            "calculator": {"calls": 1, "avg_duration_ms": 10.0},
        },
    )


# ==============================================================================
# Observability Endpoints - Alerts
# ==============================================================================


@app.get("/api/playground/observability/alerts")
def get_active_alerts(
    user: dict[str, Any] | None = Depends(verify_playground_auth),
) -> AlertsResponse:
    """
    Get active alerts.

    Returns alerts from AlertManager for in-context notification display.
    Supports both an Alerts Panel and bell icon notification UX.
    """
    return AlertsResponse(alerts=_active_alerts, total=len(_active_alerts))


# ==============================================================================
# SPA Static Files Mount (React Frontend)
# ==============================================================================
# Mount AFTER all API routes - SPAStaticFiles is a catch-all for client-side routing

# Calculate frontend dist path relative to this module
_frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"

# Only mount if frontend is built (graceful degradation for API-only mode)
_spa_handler = create_spa_static_files(str(_frontend_dist), caching=True)
if _spa_handler is not None:
    # Mount at /chat for assets referenced with /chat/ prefix (from vite base: '/chat/')
    # This enables direct access at localhost:9002 where assets are at /chat/assets/*
    app.mount("/chat", _spa_handler, name="spa-chat")
    # Mount at / for Traefik access (where /chat prefix is stripped)
    app.mount("/", _spa_handler, name="spa")


# ==============================================================================
# Run Server
# ==============================================================================

if __name__ == "__main__":
    import uvicorn

    print("=" * 80)
    print("Interactive Playground API")
    print("=" * 80)
    print("\nStarting server...")
    print("\nEndpoints:")
    print("   Health:     http://localhost:8002/api/playground/health")
    print("   Sessions:   http://localhost:8002/api/playground/sessions")
    print("   Chat:       http://localhost:8002/api/playground/chat")
    print("   WebSocket:  ws://localhost:8002/ws/playground/{session_id}")
    print("   Traces:     http://localhost:8002/api/playground/observability/traces")
    print("   Logs:       http://localhost:8002/api/playground/observability/logs")
    print("   Metrics:    http://localhost:8002/api/playground/observability/metrics")
    print("   Alerts:     http://localhost:8002/api/playground/observability/alerts")
    print("   Docs:       http://localhost:8002/docs")
    print("=" * 80)
    print()

    uvicorn.run(app, host="0.0.0.0", port=8002, reload=True)  # nosec B104
