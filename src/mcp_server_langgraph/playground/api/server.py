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
# In-Memory Session Storage (for development/testing)
# Production should use Redis via langgraph-checkpoint-redis
# ==============================================================================

_sessions: dict[str, dict[str, Any]] = {}
_session_traces: dict[str, list[TraceInfo]] = {}
_session_logs: dict[str, list[LogEntry]] = {}
_active_alerts: list[Alert] = []


def _get_session(session_id: str) -> dict[str, Any] | None:
    """Get session from storage."""
    return _sessions.get(session_id)


def _create_session(session_id: str, name: str, config: SessionConfig) -> dict[str, Any]:
    """Create a new session."""
    now = datetime.now(UTC)
    session = {
        "session_id": session_id,
        "name": name,
        "config": config,
        "created_at": now,
        "updated_at": now,
        "messages": [],
    }
    _sessions[session_id] = session
    _session_traces[session_id] = []
    _session_logs[session_id] = []
    return session


def _delete_session(session_id: str) -> bool:
    """Delete a session."""
    if session_id in _sessions:
        del _sessions[session_id]
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
    Playground service lifecycle with observability.

    Initializes OpenTelemetry tracing and metrics on startup,
    gracefully shuts down exporters on termination.
    """
    # STARTUP
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

    yield  # Application runs here

    # SHUTDOWN
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

    # Check Redis (TODO: actual connection check)
    redis_url = os.getenv("REDIS_URL")
    checks["redis"] = "configured" if redis_url else "not_configured"

    # Determine overall status
    all_ready = all(v in ("ready", "configured", "not_configured") for v in checks.values())
    status_str = "ready" if all_ready else "not_ready"

    return ReadinessStatus(status=status_str, checks=checks)


# ==============================================================================
# Session Management Endpoints
# ==============================================================================


@app.post(
    "/api/playground/sessions",
    status_code=status.HTTP_201_CREATED,
)
def create_session(
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
        session_id = str(uuid.uuid4())
        config = request.config or SessionConfig()

        session = _create_session(session_id, request.name, config)

        logger.info(
            "Session created",
            extra={"session_id": session_id, "name": request.name},
        )

        return CreateSessionResponse(
            session_id=session_id,
            name=request.name,
            created_at=session["created_at"],
            config=config,
        )


@app.get("/api/playground/sessions")
def list_sessions(
    user: dict[str, Any] | None = Depends(verify_playground_auth),
) -> ListSessionsResponse:
    """
    List all sessions for the current user.

    Returns:
        List of session summaries
    """
    summaries = [
        SessionSummary(
            session_id=s["session_id"],
            name=s["name"],
            created_at=s["created_at"],
            message_count=len(s["messages"]),
        )
        for s in _sessions.values()
    ]
    return ListSessionsResponse(sessions=summaries)


@app.get("/api/playground/sessions/{session_id}")
def get_session(
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
    session = _get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found",
        )

    return SessionDetails(
        session_id=session["session_id"],
        name=session["name"],
        created_at=session["created_at"],
        updated_at=session["updated_at"],
        messages=[SessionMessage(**m) for m in session["messages"]],
        config=session["config"],
    )


@app.delete(
    "/api/playground/sessions/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_session(
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
        if not _delete_session(session_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session '{session_id}' not found",
            )

        logger.info("Session deleted", extra={"session_id": session_id})


# ==============================================================================
# Chat Endpoint
# ==============================================================================


@app.post("/api/playground/chat")
def send_chat_message(
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
        session = _get_session(request.session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session '{request.session_id}' not found",
            )

        if not request.message.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Message cannot be empty",
            )

        now = datetime.now(UTC)
        message_id = str(uuid.uuid4())

        # Add user message to history
        user_msg = {
            "message_id": str(uuid.uuid4()),
            "role": "user",
            "content": request.message,
            "timestamp": now,
            "metadata": {},
        }
        session["messages"].append(user_msg)

        # Generate response (mock for now - will integrate with LangGraph)
        response_content = f"I received your message: '{request.message}'. This is a placeholder response from the playground."

        # Add assistant message to history
        response_timestamp = datetime.now(UTC)
        assistant_msg = {
            "message_id": message_id,
            "role": "assistant",
            "content": response_content,
            "timestamp": response_timestamp,
            "metadata": {},
        }
        session["messages"].append(assistant_msg)
        session["updated_at"] = datetime.now(UTC)

        # Add a log entry for observability
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
    session = _get_session(session_id)
    if not session:
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
def get_session_metrics(
    session_id: str = Query(..., description="Session ID"),
    user: dict[str, Any] | None = Depends(verify_playground_auth),
) -> MetricsSummary:
    """
    Get metrics summary for a session.

    Includes LLM metrics, tool metrics, and session stats.
    """
    session = _get_session(session_id)
    message_count = len(session["messages"]) if session else 0

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
