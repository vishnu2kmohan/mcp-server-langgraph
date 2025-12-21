"""
Interrupt API Endpoint

REST API for controlling session interrupts.
Implements Claude Agent SDK interrupt pattern via HTTP.

Endpoints:
- POST /sessions/{session_id}/interrupt - Signal interrupt
- GET /sessions/{session_id}/interrupt - Check interrupt status
- DELETE /sessions/{session_id}/interrupt - Clear interrupt
"""

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from mcp_server_langgraph.core.interrupt import get_interrupt_controller
from mcp_server_langgraph.observability.telemetry import logger


# Response models
class InterruptSignalResponse(BaseModel):
    """Response for interrupt signal operation."""

    session_id: str = Field(description="Session that was interrupted")
    interrupted: bool = Field(description="Whether interrupt was signaled")
    message: str = Field(description="Human-readable status message")


class InterruptStatusResponse(BaseModel):
    """Response for interrupt status check."""

    session_id: str = Field(description="Session ID checked")
    interrupted: bool = Field(description="Current interrupt status")


class InterruptClearResponse(BaseModel):
    """Response for interrupt clear operation."""

    session_id: str = Field(description="Session that was cleared")
    cleared: bool = Field(description="Whether interrupt was cleared")
    message: str = Field(description="Human-readable status message")


# Placeholder for auth dependency - to be replaced with actual auth
async def get_current_user() -> dict[str, Any]:
    """
    Get current authenticated user.

    This is a placeholder that should be replaced with actual
    authentication dependency injection.
    """
    return {"user_id": "anonymous"}


router = APIRouter(tags=["interrupt"])


@router.post(
    "/sessions/{session_id}/interrupt",
    response_model=InterruptSignalResponse,
    summary="Signal session interrupt",
    description="Signal that a session should stop execution. Running operations will stop at the next checkpoint.",
)
async def signal_interrupt(
    session_id: str,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> InterruptSignalResponse:
    """
    Signal interrupt for a session.

    This will cause any running operations for this session to stop
    at their next interrupt checkpoint.

    Args:
        session_id: The session ID to interrupt
        current_user: Authenticated user (injected)

    Returns:
        InterruptSignalResponse with interrupt status
    """
    controller = get_interrupt_controller()
    await controller.signal_interrupt(session_id)

    user_id = current_user.get("user_id", "unknown")
    logger.info(
        "Session interrupted via API",
        extra={
            "session_id": session_id,
            "user_id": user_id,
        },
    )

    return InterruptSignalResponse(
        session_id=session_id,
        interrupted=True,
        message=f"Session '{session_id}' has been interrupted. Running operations will stop at the next checkpoint.",
    )


@router.get(
    "/sessions/{session_id}/interrupt",
    response_model=InterruptStatusResponse,
    summary="Check interrupt status",
    description="Check whether a session is currently interrupted.",
)
async def check_interrupt(
    session_id: str,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> InterruptStatusResponse:
    """
    Check interrupt status for a session.

    Args:
        session_id: The session ID to check
        current_user: Authenticated user (injected)

    Returns:
        InterruptStatusResponse with current status
    """
    controller = get_interrupt_controller()
    is_interrupted = await controller.check_interrupted(session_id)

    return InterruptStatusResponse(
        session_id=session_id,
        interrupted=is_interrupted,
    )


@router.delete(
    "/sessions/{session_id}/interrupt",
    response_model=InterruptClearResponse,
    summary="Clear session interrupt",
    description="Clear the interrupt flag for a session, allowing it to proceed normally.",
)
async def clear_interrupt(
    session_id: str,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> InterruptClearResponse:
    """
    Clear interrupt for a session.

    This removes the interrupt flag, allowing the session to proceed
    normally on subsequent operations.

    Args:
        session_id: The session ID to clear
        current_user: Authenticated user (injected)

    Returns:
        InterruptClearResponse with clear status
    """
    controller = get_interrupt_controller()
    await controller.clear_interrupt(session_id)

    user_id = current_user.get("user_id", "unknown")
    logger.info(
        "Session interrupt cleared via API",
        extra={
            "session_id": session_id,
            "user_id": user_id,
        },
    )

    return InterruptClearResponse(
        session_id=session_id,
        cleared=True,
        message=f"Interrupt cleared for session '{session_id}'. The session can now proceed normally.",
    )
