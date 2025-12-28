"""
MCP WebSocket Lifecycle Management.

This module provides lifecycle management for MCP WebSocket connections,
including startup, shutdown, and periodic cleanup tasks.

Migrated from: api.v1.mcp_websocket
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from mcp_server_langgraph.mcp.websocket.connection_manager import get_connection_manager
from mcp_server_langgraph.mcp.websocket.streaming import streaming_metrics_collector

logger = logging.getLogger(__name__)

# Cleanup intervals
IDLE_CLEANUP_INTERVAL = 60


async def cleanup_idle_connections(manager: Any) -> int:
    """
    Close idle connections that have exceeded the timeout.

    Args:
        manager: The connection manager to clean up.

    Returns:
        Number of connections closed.
    """
    idle_sessions = manager.get_idle_connections()
    closed_count = 0

    for session_id in idle_sessions:
        if session_id in manager._connections:
            conn_info = manager._connections[session_id]
            try:
                await conn_info.websocket.close(
                    code=4000,
                    reason="Connection idle timeout",
                )
                logger.info(
                    f"Closed idle connection: {session_id}",
                    extra={"session_id": session_id, "user_id": conn_info.user_id},
                )
            except Exception as e:
                logger.warning(
                    f"Error closing idle connection {session_id}: {e}",
                    extra={"session_id": session_id, "error": str(e)},
                )
            finally:
                manager.disconnect(session_id)
                closed_count += 1

    return closed_count


async def graceful_shutdown(manager: Any) -> None:
    """
    Gracefully close all WebSocket connections.

    Uses WebSocket close code 1001 (Going Away) to indicate server shutdown.

    Args:
        manager: The connection manager to shut down.
    """
    # Get all session IDs (copy to avoid modification during iteration)
    session_ids = list(manager._connections.keys())

    for session_id in session_ids:
        if session_id in manager._connections:
            conn_info = manager._connections[session_id]
            try:
                await conn_info.websocket.close(
                    code=1001,
                    reason="Server shutting down",
                )
                logger.info(
                    f"Gracefully closed connection: {session_id}",
                    extra={"session_id": session_id, "user_id": conn_info.user_id},
                )
            except Exception as e:
                logger.warning(
                    f"Error closing connection {session_id} during shutdown: {e}",
                    extra={"session_id": session_id, "error": str(e)},
                )
            finally:
                manager.disconnect(session_id)


class MCPWebSocketLifecycleManager:
    """
    Manages MCP WebSocket lifecycle for integration with FastAPI app.

    Provides startup/shutdown methods that can be called from the main
    app lifespan to start background tasks and handle graceful shutdown.

    Usage:
        manager = get_mcp_lifecycle_manager()
        await manager.startup()  # In app lifespan startup
        await manager.shutdown()  # In app lifespan shutdown
    """

    def __init__(
        self,
        cleanup_interval: float = IDLE_CLEANUP_INTERVAL,
        metrics_cleanup_interval: float = 300,  # 5 minutes default
        streaming_enabled: bool = True,
        max_age_seconds: float = 3600,  # 1 hour default
    ) -> None:
        """
        Initialize the lifecycle manager.

        Args:
            cleanup_interval: Interval in seconds between idle connection cleanup runs.
            metrics_cleanup_interval: Interval in seconds between stream metrics cleanup runs.
            streaming_enabled: Whether streaming is enabled. If False, cleanup tasks won't start.
            max_age_seconds: Maximum age in seconds for completed streams before cleanup.
        """
        self.cleanup_interval = cleanup_interval
        self.metrics_cleanup_interval = metrics_cleanup_interval
        self.streaming_enabled = streaming_enabled
        self.max_age_seconds = max_age_seconds
        self.cleanup_task: asyncio.Task[None] | None = None
        self.metrics_cleanup_task: asyncio.Task[None] | None = None
        self._started = False

    async def startup(self) -> None:
        """
        Start MCP WebSocket lifecycle management.

        Starts the idle connection cleanup and stream metrics cleanup background tasks.
        Idempotent - safe to call multiple times.

        If streaming_enabled is False, skips starting cleanup tasks.
        """
        if self._started:
            logger.debug("MCP WebSocket lifecycle already started")
            return

        # Skip starting cleanup tasks if streaming is disabled
        if not self.streaming_enabled:
            logger.info("Streaming disabled, skipping cleanup task startup")
            self._started = True
            return

        connection_manager = get_connection_manager()

        # Start idle cleanup task with custom interval
        async def _cleanup_loop() -> None:
            while True:
                try:
                    await asyncio.sleep(self.cleanup_interval)
                    closed = await cleanup_idle_connections(connection_manager)
                    if closed > 0:
                        logger.info(f"Idle cleanup: closed {closed} connections")
                except asyncio.CancelledError:
                    logger.info("Idle cleanup task cancelled")
                    break
                except Exception:
                    logger.exception("Error in idle cleanup task")

        # Start metrics cleanup task
        async def _metrics_cleanup_loop() -> None:
            while True:
                try:
                    await asyncio.sleep(self.metrics_cleanup_interval)
                    removed = await self.cleanup_stream_metrics()
                    if removed > 0:
                        logger.info(f"Metrics cleanup: removed {removed} old streams")
                except asyncio.CancelledError:
                    logger.info("Metrics cleanup task cancelled")
                    break
                except Exception:
                    logger.exception("Error in metrics cleanup task")

        self.cleanup_task = asyncio.create_task(_cleanup_loop())
        self.metrics_cleanup_task = asyncio.create_task(_metrics_cleanup_loop())
        self._started = True
        logger.info("MCP WebSocket lifecycle started, cleanup tasks running")

    async def shutdown(self) -> None:
        """
        Stop MCP WebSocket lifecycle management.

        Cancels cleanup tasks, cleans up all stream metrics, and calls graceful shutdown.
        Idempotent - safe to call multiple times.
        """
        if not self._started:
            logger.debug("MCP WebSocket lifecycle not started, skipping shutdown")
            return

        # Cancel idle cleanup task
        if self.cleanup_task and not self.cleanup_task.done():
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass

        # Cancel metrics cleanup task
        if self.metrics_cleanup_task and not self.metrics_cleanup_task.done():
            self.metrics_cleanup_task.cancel()
            try:
                await self.metrics_cleanup_task
            except asyncio.CancelledError:
                pass

        # Clean up all completed stream metrics on shutdown
        await self.cleanup_stream_metrics(max_age_seconds=0)

        # Graceful shutdown
        connection_manager = get_connection_manager()
        await graceful_shutdown(connection_manager)

        self._started = False
        logger.info("MCP WebSocket lifecycle shutdown complete")

    async def cleanup_stream_metrics(self, max_age_seconds: float | None = None) -> int:
        """
        Clean up old stream metrics from the global streaming_metrics_collector.

        Removes completed streams older than max_age_seconds to prevent memory growth.
        Active streams are never removed.

        Args:
            max_age_seconds: Maximum age in seconds for completed streams.
                            Defaults to self.max_age_seconds if not provided.

        Returns:
            Number of streams removed.
        """
        age = max_age_seconds if max_age_seconds is not None else self.max_age_seconds
        removed = streaming_metrics_collector.cleanup_old_streams(age)
        if removed > 0:
            logger.debug(f"Cleaned up {removed} old stream metrics")
        return removed


# Global lifecycle manager singleton
_lifecycle_manager: MCPWebSocketLifecycleManager | None = None


def get_mcp_lifecycle_manager() -> MCPWebSocketLifecycleManager:
    """
    Get the global MCP WebSocket lifecycle manager singleton.

    Returns:
        The global MCPWebSocketLifecycleManager instance.
    """
    global _lifecycle_manager
    if _lifecycle_manager is None:
        _lifecycle_manager = MCPWebSocketLifecycleManager()
    return _lifecycle_manager


def set_mcp_lifecycle_manager(manager: MCPWebSocketLifecycleManager) -> None:
    """
    Set the global MCP WebSocket lifecycle manager singleton.

    Used by bootstrap to inject a configured manager.

    Args:
        manager: The lifecycle manager instance to set as global singleton.
    """
    global _lifecycle_manager
    _lifecycle_manager = manager


def create_mcp_lifecycle_manager(
    streaming_settings: Any | None = None,
) -> MCPWebSocketLifecycleManager:
    """
    Create a new MCPWebSocketLifecycleManager with optional StreamingSettings.

    Factory function that allows configuration injection for lifecycle manager.
    Does NOT modify the global singleton.

    Args:
        streaming_settings: Optional StreamingSettings instance with cleanup intervals.

    Returns:
        A new MCPWebSocketLifecycleManager instance with configured intervals.
    """
    if streaming_settings is None:
        return MCPWebSocketLifecycleManager()

    return MCPWebSocketLifecycleManager(
        cleanup_interval=streaming_settings.streaming_idle_cleanup_interval,
        metrics_cleanup_interval=streaming_settings.streaming_metrics_cleanup_interval,
        streaming_enabled=streaming_settings.streaming_enabled,
        max_age_seconds=streaming_settings.streaming_max_age_seconds,
    )
