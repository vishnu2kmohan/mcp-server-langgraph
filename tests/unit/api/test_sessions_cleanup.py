"""
Unit tests for api/v1/sessions.py cleanup functionality.

Tests that the session service properly cleans up Redis and PostgreSQL clients.
"""

import gc
from unittest.mock import AsyncMock, MagicMock

import pytest


pytestmark = pytest.mark.unit


class TestSessionsCleanup:
    """Tests for session service cleanup functions."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_cleanup_session_service_closes_redis_client(self) -> None:
        """Test that cleanup_session_service() closes the Redis client."""
        from mcp_server_langgraph.api.v1 import sessions as sessions_module
        from mcp_server_langgraph.api.v1.sessions import cleanup_session_service

        # Save original state
        original_service = sessions_module._session_service
        original_redis = sessions_module._redis_client
        original_pg = sessions_module._postgres_engine

        # Setup mock Redis client
        mock_redis = MagicMock()
        mock_redis.aclose = AsyncMock(return_value=None)

        sessions_module._session_service = MagicMock()
        sessions_module._redis_client = mock_redis
        sessions_module._postgres_engine = None

        try:
            await cleanup_session_service()

            # Verify Redis client was closed
            mock_redis.aclose.assert_called_once()

            # Verify globals were reset
            assert sessions_module._session_service is None
            assert sessions_module._redis_client is None
        finally:
            # Restore original state
            sessions_module._session_service = original_service
            sessions_module._redis_client = original_redis
            sessions_module._postgres_engine = original_pg

    @pytest.mark.asyncio
    async def test_cleanup_session_service_disposes_postgres_engine(self) -> None:
        """Test that cleanup_session_service() disposes the PostgreSQL engine."""
        from mcp_server_langgraph.api.v1 import sessions as sessions_module
        from mcp_server_langgraph.api.v1.sessions import cleanup_session_service

        # Save original state
        original_service = sessions_module._session_service
        original_redis = sessions_module._redis_client
        original_pg = sessions_module._postgres_engine

        # Setup mock PostgreSQL engine
        mock_engine = MagicMock()
        mock_engine.dispose = AsyncMock(return_value=None)

        sessions_module._session_service = MagicMock()
        sessions_module._redis_client = None
        sessions_module._postgres_engine = mock_engine

        try:
            await cleanup_session_service()

            # Verify PostgreSQL engine was disposed
            mock_engine.dispose.assert_called_once()

            # Verify globals were reset
            assert sessions_module._session_service is None
            assert sessions_module._postgres_engine is None
        finally:
            # Restore original state
            sessions_module._session_service = original_service
            sessions_module._redis_client = original_redis
            sessions_module._postgres_engine = original_pg

    @pytest.mark.asyncio
    async def test_cleanup_session_service_handles_none_clients(self) -> None:
        """Test that cleanup_session_service() handles None clients gracefully."""
        from mcp_server_langgraph.api.v1 import sessions as sessions_module
        from mcp_server_langgraph.api.v1.sessions import cleanup_session_service

        # Save original state
        original_service = sessions_module._session_service
        original_redis = sessions_module._redis_client
        original_pg = sessions_module._postgres_engine

        # Set all to None
        sessions_module._session_service = None
        sessions_module._redis_client = None
        sessions_module._postgres_engine = None

        try:
            # Should not raise
            await cleanup_session_service()

            # Verify globals remain None
            assert sessions_module._session_service is None
            assert sessions_module._redis_client is None
            assert sessions_module._postgres_engine is None
        finally:
            # Restore original state
            sessions_module._session_service = original_service
            sessions_module._redis_client = original_redis
            sessions_module._postgres_engine = original_pg

    @pytest.mark.asyncio
    async def test_cleanup_session_service_handles_close_errors(self) -> None:
        """Test that cleanup_session_service() handles errors gracefully."""
        from mcp_server_langgraph.api.v1 import sessions as sessions_module
        from mcp_server_langgraph.api.v1.sessions import cleanup_session_service

        # Save original state
        original_service = sessions_module._session_service
        original_redis = sessions_module._redis_client
        original_pg = sessions_module._postgres_engine

        # Setup mocks that raise errors
        mock_redis = MagicMock()
        mock_redis.aclose = AsyncMock(side_effect=Exception("Redis close error"))
        mock_engine = MagicMock()
        mock_engine.dispose = AsyncMock(side_effect=Exception("Postgres dispose error"))

        sessions_module._session_service = MagicMock()
        sessions_module._redis_client = mock_redis
        sessions_module._postgres_engine = mock_engine

        try:
            # Should not raise even if closes fail
            await cleanup_session_service()

            # Verify globals were still reset despite errors
            assert sessions_module._session_service is None
            assert sessions_module._redis_client is None
            assert sessions_module._postgres_engine is None
        finally:
            # Restore original state
            sessions_module._session_service = original_service
            sessions_module._redis_client = original_redis
            sessions_module._postgres_engine = original_pg

    @pytest.mark.asyncio
    async def test_cleanup_session_service_is_idempotent(self) -> None:
        """Test that cleanup_session_service() can be called multiple times safely."""
        from mcp_server_langgraph.api.v1 import sessions as sessions_module
        from mcp_server_langgraph.api.v1.sessions import cleanup_session_service

        # Save original state
        original_service = sessions_module._session_service
        original_redis = sessions_module._redis_client
        original_pg = sessions_module._postgres_engine

        # Setup mock Redis client
        mock_redis = MagicMock()
        mock_redis.aclose = AsyncMock(return_value=None)

        sessions_module._session_service = MagicMock()
        sessions_module._redis_client = mock_redis
        sessions_module._postgres_engine = None

        try:
            # Call twice
            await cleanup_session_service()
            await cleanup_session_service()

            # Should only close once (first call sets to None)
            mock_redis.aclose.assert_called_once()
        finally:
            # Restore original state
            sessions_module._session_service = original_service
            sessions_module._redis_client = original_redis
            sessions_module._postgres_engine = original_pg
