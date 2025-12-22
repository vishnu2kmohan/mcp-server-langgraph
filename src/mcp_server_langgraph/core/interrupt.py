"""
Interrupt Controller for graceful cancellation of agent operations.

This module implements the Claude Agent SDK interrupt pattern:
- signal_interrupt(session_id): Signal that a session should stop
- check_interrupted(session_id): Check if session was interrupted
- clear_interrupt(session_id): Clear interrupt flag for reuse

Thread-safe implementation using asyncio locks.
"""

from __future__ import annotations

import asyncio
import functools
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

T = TypeVar("T")


class InterruptedOperationError(Exception):
    """Exception raised when an operation is interrupted.

    Attributes:
        session_id: The ID of the session that was interrupted.
    """

    def __init__(self, session_id: str) -> None:
        """Initialize the exception.

        Args:
            session_id: The ID of the session that was interrupted.
        """
        self.session_id = session_id
        super().__init__(f"Operation interrupted for session {session_id}")


class InterruptController:
    """Thread-safe interrupt signaling for agent operations.

    This controller provides a way to signal interruption to long-running
    agent operations, allowing them to gracefully stop execution.

    Example:
        controller = InterruptController()

        # In cancellation handler
        await controller.signal_interrupt("session-123")

        # In agent operation loop
        if await controller.check_interrupted("session-123"):
            # Cleanup and return early
            pass

        # Or raise immediately
        await controller.raise_if_interrupted("session-123")
    """

    def __init__(self) -> None:
        """Initialize the interrupt controller."""
        self._interrupted: dict[str, bool] = {}
        self._lock = asyncio.Lock()

    async def signal_interrupt(self, session_id: str) -> bool:
        """Signal that a session should stop execution.

        Args:
            session_id: The ID of the session to interrupt.

        Returns:
            True if the signal was successfully set.
        """
        async with self._lock:
            self._interrupted[session_id] = True
        return True

    async def check_interrupted(self, session_id: str) -> bool:
        """Check if a session has been interrupted.

        Args:
            session_id: The ID of the session to check.

        Returns:
            True if the session has been interrupted, False otherwise.
        """
        async with self._lock:
            return self._interrupted.get(session_id, False)

    async def clear_interrupt(self, session_id: str) -> None:
        """Clear the interrupt flag for a session.

        This allows the session to be reused after an interrupt.

        Args:
            session_id: The ID of the session to clear.
        """
        async with self._lock:
            self._interrupted.pop(session_id, None)

    async def raise_if_interrupted(self, session_id: str) -> None:
        """Raise an exception if the session is interrupted.

        This is a convenience method for checking and raising in one call.

        Args:
            session_id: The ID of the session to check.

        Raises:
            InterruptedOperationError: If the session has been interrupted.
        """
        if await self.check_interrupted(session_id):
            raise InterruptedOperationError(session_id)


# Singleton instance
_interrupt_controller: InterruptController | None = None
_singleton_lock: asyncio.Lock = asyncio.Lock()


def get_interrupt_controller() -> InterruptController:
    """Get the singleton InterruptController instance.

    Returns:
        The shared InterruptController instance.
    """
    global _interrupt_controller
    if _interrupt_controller is None:
        _interrupt_controller = InterruptController()
    return _interrupt_controller


def reset_interrupt_controller() -> None:
    """Reset the singleton InterruptController.

    This is primarily useful for testing to ensure a clean state.
    """
    global _interrupt_controller
    _interrupt_controller = None


def _default_session_id_extractor(state: dict[str, Any]) -> str:
    """Extract session_id from state using default key.

    Args:
        state: The state dictionary.

    Returns:
        The session_id, or "unknown" if not found.
    """
    session_id = state.get("session_id", "unknown")
    return str(session_id)


def interrupt_aware_node(
    controller: InterruptController,
    session_id_extractor: Callable[[dict[str, Any]], str] | None = None,
) -> Callable[[Callable[[dict[str, Any]], Awaitable[T]]], Callable[[dict[str, Any]], Awaitable[T]]]:
    """Decorator to make a node function interrupt-aware.

    This decorator wraps an async node function to check for interrupts
    before execution. If the session is interrupted, it raises
    InterruptedOperationError without executing the function body.

    Args:
        controller: The InterruptController instance to use.
        session_id_extractor: Optional function to extract session_id from state.
                              Defaults to looking for "session_id" key.

    Returns:
        A decorator that wraps the node function.

    Example:
        controller = InterruptController()

        @interrupt_aware_node(controller)
        async def my_node(state: dict) -> dict:
            # This will only execute if session is not interrupted
            return {"result": "success"}
    """
    extractor = session_id_extractor or _default_session_id_extractor

    def decorator(
        func: Callable[[dict[str, Any]], Awaitable[T]],
    ) -> Callable[[dict[str, Any]], Awaitable[T]]:
        @functools.wraps(func)
        async def wrapper(state: dict[str, Any]) -> T:
            session_id = extractor(state)

            # Check for interrupt before execution
            await controller.raise_if_interrupted(session_id)

            # Execute the wrapped function
            return await func(state)

        return wrapper

    return decorator
