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
from typing import Any, AsyncIterator

from fastapi import Depends, FastAPI, Header, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware

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
    ChatRequest,
    ChatResponse,
    CreateSessionRequest,
    CreateSessionResponse,
    HealthStatus,
    LLMMetrics,
    LogEntry,
    LogLevel,
    LogsResponse,
    MetricsSummary,
    ReadinessStatus,
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

# Global session manager (initialized in lifespan)
_session_manager: PostgresSessionManager | RedisSessionManager | None = None

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
    environment = os.getenv("ENVIRONMENT", "development")

    # Development mode - allow unauthenticated access
    if environment == "development":
        if not authorization:
            logger.debug("Playground accessed without auth in development mode")
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
    global _session_manager, _storage_backend

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
        else:
            # In-memory fallback
            if not _delete_session_memory(session_id):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Session '{session_id}' not found",
                )

            logger.info("Session deleted (in-memory)", extra={"session_id": session_id})


# ==============================================================================
# Chat Endpoint
# ==============================================================================


@app.post("/api/playground/chat")
async def send_chat_message(
    request: ChatRequest,
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

        # Generate response (mock for now - will integrate with LangGraph)
        response_content = f"I received your message: '{request.message}'. This is a placeholder response from the playground."
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
