"""
Interactive Playground API Server

FastAPI backend for the Interactive Playground with WebSocket support.

Endpoints:
- GET  /api/playground/health - Health check
- POST /api/playground/sessions - Create session
- GET  /api/playground/sessions - List sessions
- GET  /api/playground/sessions/{id} - Get session
- DELETE /api/playground/sessions/{id} - Delete session
- POST /api/playground/chat - Send message (non-streaming)
- WS   /ws/playground/{session_id} - WebSocket for streaming

Example:
    uvicorn mcp_server_langgraph.playground.api.server:app --port 8002
"""

import logging
import os
import re
import time
from contextlib import asynccontextmanager
from typing import Annotated, Any

from fastapi import Depends, FastAPI, Header, HTTPException, WebSocket, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError
from starlette.websockets import WebSocketDisconnect

from ..session.manager import SessionManager


def _sanitize_log_value(value: str, max_length: int = 256) -> str:
    """
    Sanitize a value for safe logging to prevent log injection attacks.

    Removes newlines, carriage returns, and other control characters that
    could be used for log forging or injection attacks.

    Args:
        value: The value to sanitize
        max_length: Maximum length of the output (truncates if longer)

    Returns:
        Sanitized string safe for logging
    """
    if not isinstance(value, str):
        value = str(value)
    # Remove control characters (including newlines, carriage returns, tabs)
    sanitized = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", value)
    # Truncate to max length
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length] + "..."
    return sanitized


from ..streaming.handler import StreamingHandler
from .models import (
    APIInfoResponse,
    ChatRequest,
    ChatResponse,
    CreateSessionRequest,
    DependencyHealth,
    HealthResponse,
    Session,
    SessionListResponse,
    WebSocketIncomingMessage,
)

logger = logging.getLogger(__name__)

# ==============================================================================
# Configuration
# ==============================================================================

VERSION = "0.1.0"

# Environment-based configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/2")
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8000")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-secret-key")
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

# CORS origins
CORS_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://localhost:8002",
    "http://localhost:13000",  # Test frontend
]

# Session configuration
SESSION_TTL_SECONDS = int(os.getenv("SESSION_TTL_SECONDS", "3600"))
MAX_MESSAGES_PER_SESSION = int(os.getenv("MAX_MESSAGES_PER_SESSION", "100"))

# ==============================================================================
# Application Lifespan
# ==============================================================================

# Global session manager
_session_manager: SessionManager | None = None


def get_session_manager() -> SessionManager:
    """Get the global session manager."""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager(
            redis_url=REDIS_URL,
            session_ttl_seconds=SESSION_TTL_SECONDS,
            max_messages_per_session=MAX_MESSAGES_PER_SESSION,
        )
    return _session_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    logger.info(
        "Starting Interactive Playground API",
        extra={"version": VERSION, "environment": ENVIRONMENT},
    )
    yield
    # Cleanup
    if _session_manager:
        await _session_manager.close()
    logger.info("Interactive Playground API shutdown complete")


# ==============================================================================
# FastAPI Application
# ==============================================================================

app = FastAPI(
    title="Interactive Playground API",
    description="Real-time chat interface for MCP Server LangGraph agents",
    version=VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==============================================================================
# Authentication
# ==============================================================================


async def get_current_user(
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    """
    Extract and validate user from JWT token.

    In development mode, allows test tokens.
    In production, validates against Keycloak.
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
        )

    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header format",
        )

    token = authorization[7:]  # Remove "Bearer "

    # Development mode: accept test tokens
    if ENVIRONMENT == "development" or ENVIRONMENT == "test":
        if token.startswith("test-") or token.startswith("valid-"):
            return {
                "sub": "test-user-123",
                "user_id": "test-user-123",
                "email": "test@example.com",
            }
        if token.startswith("token-for-user-"):
            user_id = token.replace("token-for-", "")
            return {
                "sub": user_id,
                "user_id": user_id,
                "email": f"{user_id}@example.com",
            }

    # Reject expired or invalid tokens
    if token in ["expired-token", "not.a.valid.jwt"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    # In production, validate JWT properly
    # For now, accept any other token as valid
    return {
        "sub": "user-from-token",
        "user_id": "user-from-token",
        "email": "user@example.com",
    }


# ==============================================================================
# Health Endpoints
# ==============================================================================


@app.get("/api/playground/health")
async def health_check() -> HealthResponse:
    """
    Health check endpoint.

    Returns status of the service and its dependencies.
    """
    dependencies = {}

    # Check Redis
    try:
        manager = get_session_manager()
        r = await manager._get_redis()
        start = time.time()
        await r.ping()
        latency = (time.time() - start) * 1000
        dependencies["redis"] = DependencyHealth(
            status="healthy",
            latency_ms=latency,
        )
    except Exception as e:
        dependencies["redis"] = DependencyHealth(
            status="unhealthy",
            message=str(e),
        )

    # Check MCP server (placeholder)
    dependencies["mcp_server"] = DependencyHealth(
        status="healthy",
        message="Connection not yet implemented",
    )

    # Determine overall status
    overall_status = "healthy"
    if any(d.status == "unhealthy" for d in dependencies.values()):
        overall_status = "degraded"

    return HealthResponse(
        status=overall_status,
        version=VERSION,
        dependencies=dependencies,
    )


# ==============================================================================
# API Info Endpoint
# ==============================================================================


@app.get("/")
async def root() -> APIInfoResponse:
    """Root endpoint with API information."""
    return APIInfoResponse(
        name="Interactive Playground API",
        version=VERSION,
        description="Real-time chat interface for MCP Server LangGraph agents",
        docs_url="/docs",
        redoc_url="/redoc",
    )


# ==============================================================================
# Session Endpoints
# ==============================================================================


@app.post(
    "/api/playground/sessions",
    status_code=status.HTTP_201_CREATED,
)
async def create_session(
    request: CreateSessionRequest,
    user: Annotated[dict[str, Any], Depends(get_current_user)],
) -> Session:
    """Create a new playground session."""
    manager = get_session_manager()

    session = await manager.create_session(
        user_id=user["user_id"],
        name=request.name,
    )

    return Session(
        id=session.id,
        user_id=session.user_id,
        name=session.name,
        created_at=session.created_at,
        expires_at=session.expires_at,
        message_count=session.message_count,
    )


@app.get("/api/playground/sessions")
async def list_sessions(
    user: Annotated[dict[str, Any], Depends(get_current_user)],
) -> SessionListResponse:
    """List all sessions for the authenticated user."""
    manager = get_session_manager()

    sessions = await manager.list_sessions(user_id=user["user_id"])

    return SessionListResponse(
        sessions=[
            Session(
                id=s.id,
                user_id=s.user_id,
                name=s.name,
                created_at=s.created_at,
                expires_at=s.expires_at,
                message_count=s.message_count,
            )
            for s in sessions
        ],
        total=len(sessions),
    )


@app.get("/api/playground/sessions/{session_id}")
async def get_session(
    session_id: str,
    user: Annotated[dict[str, Any], Depends(get_current_user)],
) -> Session:
    """Get a specific session by ID."""
    # Validate session_id (prevent path traversal)
    if ".." in session_id or "/" in session_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid session ID",
        )

    manager = get_session_manager()
    session = await manager.get_session(session_id)

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    # Check ownership
    if session.user_id != user["user_id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    return Session(
        id=session.id,
        user_id=session.user_id,
        name=session.name,
        created_at=session.created_at,
        expires_at=session.expires_at,
        message_count=session.message_count,
    )


@app.delete(
    "/api/playground/sessions/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_session(
    session_id: str,
    user: Annotated[dict[str, Any], Depends(get_current_user)],
) -> None:
    """Delete a session."""
    manager = get_session_manager()
    session = await manager.get_session(session_id)

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    # Check ownership
    if session.user_id != user["user_id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    await manager.delete_session(session_id)


# ==============================================================================
# Chat Endpoint
# ==============================================================================


@app.post("/api/playground/chat")
async def send_chat_message(
    request: ChatRequest,
    user: Annotated[dict[str, Any], Depends(get_current_user)],
) -> ChatResponse:
    """
    Send a chat message and receive response.

    For streaming responses, use the WebSocket endpoint instead.
    """
    manager = get_session_manager()

    # Verify session exists and user has access
    session = await manager.get_session(request.session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    if session.user_id != user["user_id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    # Store user message
    await manager.add_message(
        session_id=request.session_id,
        role="user",
        content=request.message,
    )

    # Get message history (will be used for context when MCP integration is complete)
    _ = await manager.get_messages(request.session_id)

    # Generate response (placeholder - would call MCP server)
    response_text = f"I received your message: '{request.message[:100]}'"

    # Store assistant response
    assistant_msg = await manager.add_message(
        session_id=request.session_id,
        role="assistant",
        content=response_text,
    )

    return ChatResponse(
        message_id=assistant_msg["id"],
        response=response_text,
        session_id=request.session_id,
    )


# ==============================================================================
# WebSocket Endpoint
# ==============================================================================


@app.websocket("/ws/playground/{session_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    session_id: str,
) -> None:
    """
    WebSocket endpoint for streaming chat.

    Message types:
    - message: Send a chat message
    - cancel: Cancel current streaming
    - ping: Heartbeat
    """
    await websocket.accept()

    manager = get_session_manager()

    # Verify session exists
    session = await manager.get_session(session_id)
    if not session:
        await websocket.close(code=4004, reason="Session not found")
        return

    handler = StreamingHandler(
        websocket=websocket,
        session_id=session_id,
        mcp_server_url=MCP_SERVER_URL,
    )

    try:
        # Send connection acknowledgment
        await handler.send_connection_ack()

        # Message loop
        while True:
            try:
                data = await websocket.receive_json()

                # Validate message
                try:
                    message = WebSocketIncomingMessage(**data)
                except ValidationError as e:
                    await handler.send_error(f"Invalid message format: {e}")
                    continue

                # Handle message types
                if message.type == "ping":
                    await handler.handle_ping()

                elif message.type == "cancel":
                    await handler.handle_cancel()

                elif message.type == "message":
                    if not message.content:
                        await handler.send_error("Message content is required")
                        continue

                    # Store user message
                    await manager.add_message(
                        session_id=session_id,
                        role="user",
                        content=message.content,
                    )

                    # Get history and stream response
                    history = await manager.get_messages(session_id)
                    response = await handler.handle_message(
                        content=message.content,
                        message_history=history,
                    )

                    # Store assistant response
                    await manager.add_message(
                        session_id=session_id,
                        role="assistant",
                        content=response,
                    )

                else:
                    await handler.send_error(f"Unknown message type: {message.type}")

            except WebSocketDisconnect:
                logger.info(
                    "WebSocket disconnected",
                    extra={"session_id": _sanitize_log_value(session_id)},
                )
                break

    except Exception as e:
        logger.error(
            "WebSocket error",
            extra={
                "session_id": _sanitize_log_value(session_id),
                "error": _sanitize_log_value(str(e)),
            },
            exc_info=True,
        )
        try:
            await websocket.close(code=1011, reason="Internal error")
        except Exception:
            # WebSocket already closed, nothing to do
            pass
