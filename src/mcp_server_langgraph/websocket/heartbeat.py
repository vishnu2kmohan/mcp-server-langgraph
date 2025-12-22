"""
Server-Initiated Heartbeat Manager.

Manages periodic heartbeat messages for WebSocket connections to detect
dead connections that the TCP layer may not detect.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Callable, Coroutine

if TYPE_CHECKING:
    from fastapi import WebSocket

logger = logging.getLogger(__name__)


class HeartbeatManager:
    """
    Manages server-initiated heartbeat for WebSocket connections.

    Sends periodic heartbeat messages and tracks client responses to detect
    dead connections. If no pong is received within the timeout period,
    the connection is considered dead and the timeout callback is invoked.

    Usage:
        manager = HeartbeatManager(interval=30, timeout=90)
        task = await manager.start(websocket)

        # When client sends pong
        await manager.on_pong()

        # When done
        await manager.stop()
    """

    def __init__(
        self,
        interval: float = 30,
        timeout: float | None = None,
        on_timeout: Callable[[], Coroutine[Any, Any, None]] | None = None,
    ) -> None:
        """
        Initialize HeartbeatManager.

        Args:
            interval: Seconds between heartbeat messages (default: 30).
            timeout: Seconds without pong before considering connection dead.
                    Defaults to 3x interval.
            on_timeout: Async callback invoked when connection times out.
        """
        self.interval = interval
        self.timeout = timeout if timeout is not None else interval * 3
        self._on_timeout = on_timeout
        self._task: asyncio.Task[None] | None = None
        self._websocket: WebSocket | None = None
        self._last_activity = datetime.now(UTC)
        self._running = False

    @property
    def last_activity(self) -> datetime:
        """Get the timestamp of last activity (heartbeat response)."""
        return self._last_activity

    @property
    def is_alive(self) -> bool:
        """Check if connection is considered alive (within timeout window)."""
        elapsed = (datetime.now(UTC) - self._last_activity).total_seconds()
        return elapsed < self.timeout

    async def start(self, websocket: WebSocket) -> asyncio.Task[None]:
        """
        Start the heartbeat background task.

        Args:
            websocket: The WebSocket connection to send heartbeats on.

        Returns:
            The background task for the heartbeat loop.
        """
        self._websocket = websocket
        self._running = True
        self._last_activity = datetime.now(UTC)
        self._task = asyncio.create_task(self._heartbeat_loop())
        return self._task

    async def stop(self) -> None:
        """Stop the heartbeat background task."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._task = None

    async def on_pong(self) -> None:
        """
        Called when a pong response is received from the client.

        Updates the last activity timestamp to indicate the connection is alive.
        """
        self._last_activity = datetime.now(UTC)
        logger.debug("Heartbeat pong received")

    async def _heartbeat_loop(self) -> None:
        """
        Background task that sends periodic heartbeat messages.

        Checks for timeout and invokes callback if no pong received.
        """
        running = self._running
        while running:
            try:
                await asyncio.sleep(self.interval)

                # Check if stopped during sleep (could be modified by stop())
                running = self._running
                if not running:
                    break

                # Check for timeout
                if not self.is_alive:
                    logger.warning("Heartbeat timeout - no pong received")
                    if self._on_timeout:
                        await self._on_timeout()
                    break

                # Send heartbeat
                if self._websocket:
                    try:
                        await self._websocket.send_json(
                            {
                                "type": "heartbeat",
                                "timestamp": datetime.now(UTC).isoformat(),
                            }
                        )
                        logger.debug("Heartbeat sent")
                    except Exception as e:
                        logger.warning(f"Failed to send heartbeat: {e}")
                        if self._on_timeout:
                            await self._on_timeout()
                        break

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception(f"Heartbeat loop error: {e}")
                break
