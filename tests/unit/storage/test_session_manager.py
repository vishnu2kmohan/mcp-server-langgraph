"""Tests for RedisSessionManager TTL refresh on read.

TDD: Tests written FIRST to define behavior for refreshing Redis TTL
when a session is read via get_session().

RC5 Fix: Active sessions should not expire during long conversations.
get_session() should refresh the TTL on read to prevent session loss.

Finding 6 Fix: Uses pipeline to batch expire calls in a single round trip.
"""

from __future__ import annotations

import gc
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from mcp_server_langgraph.storage.session.manager import RedisSessionManager
from mcp_server_langgraph.storage.session.models import Session, SessionConfig

pytestmark = [
    pytest.mark.unit,
    pytest.mark.xdist_group(name="test_session_manager"),
]


def _make_session(
    session_id: str = "test-session-123",
    user_id: str = "alice",
) -> Session:
    """Create a test Session object."""
    return Session(
        session_id=session_id,
        name="Test Session",
        user_id=user_id,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        config=SessionConfig(),
        messages=[],
        status="active",
    )


def _make_mock_redis(session: Session | None = None) -> AsyncMock:
    """Create a mock Redis client with pipeline support."""
    mock_redis = AsyncMock()  # noqa: async-mock-config

    if session is not None:
        mock_redis.get = AsyncMock(return_value=session.model_dump_json())
    else:
        mock_redis.get = AsyncMock(return_value=None)

    # Pipeline mock: collect expire calls, return mock on execute
    mock_pipe = AsyncMock()  # noqa: async-mock-config
    mock_pipe.expire = AsyncMock(return_value=mock_pipe)
    mock_pipe.execute = AsyncMock(return_value=[True, True])
    mock_redis.pipeline = lambda transaction=True: mock_pipe
    mock_redis._mock_pipe = mock_pipe  # for test assertions

    return mock_redis


class TestGetSessionRefreshesTTL:
    """Tests for get_session() TTL refresh behavior (RC5 fix)."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_get_session_refreshes_ttl_via_pipeline(self) -> None:
        """GIVEN a valid session stored in Redis
        WHEN get_session is called
        THEN the session key TTL is refreshed via a pipeline
        """
        session = _make_session()
        mock_redis = _make_mock_redis(session)
        mock_pipe = mock_redis._mock_pipe

        manager = RedisSessionManager(redis_client=mock_redis, ttl_seconds=3600)
        result = await manager.get_session("test-session-123")

        assert result is not None
        assert result.session_id == "test-session-123"

        # Verify expire was called on the pipeline with session key
        expire_calls = [str(call) for call in mock_pipe.expire.call_args_list]
        assert any("session:test-session-123" in c for c in expire_calls), (
            f"Expected session key TTL refresh in pipeline, got: {expire_calls}"
        )

        # Verify pipeline was executed
        mock_pipe.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_session_refreshes_user_scoped_key_ttl(self) -> None:
        """GIVEN a session with user_id stored in Redis
        WHEN get_session is called
        THEN both session key and user-scoped key TTLs are refreshed via pipeline
        """
        session = _make_session(user_id="alice")
        mock_redis = _make_mock_redis(session)
        mock_pipe = mock_redis._mock_pipe

        manager = RedisSessionManager(redis_client=mock_redis, ttl_seconds=3600)
        result = await manager.get_session("test-session-123")

        assert result is not None

        # Verify both keys had TTL refreshed in pipeline
        expire_calls = [str(call) for call in mock_pipe.expire.call_args_list]
        session_key = "session:test-session-123"
        user_key = "session:user:alice:test-session-123"

        assert any(session_key in c for c in expire_calls), f"Expected session key TTL refresh, got calls: {expire_calls}"
        assert any(user_key in c for c in expire_calls), f"Expected user-scoped key TTL refresh, got calls: {expire_calls}"

        # Single pipeline execute call (batched)
        mock_pipe.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_session_returns_none_without_ttl_refresh(self) -> None:
        """GIVEN no session in Redis
        WHEN get_session is called
        THEN None is returned and no TTL refresh is attempted
        """
        mock_redis = _make_mock_redis(session=None)
        mock_pipe = mock_redis._mock_pipe

        manager = RedisSessionManager(redis_client=mock_redis, ttl_seconds=3600)
        result = await manager.get_session("nonexistent-session")

        assert result is None
        # Pipeline should not have been used
        mock_pipe.expire.assert_not_called()
        mock_pipe.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_session_uses_configured_ttl(self) -> None:
        """GIVEN a custom TTL configuration
        WHEN get_session refreshes TTL
        THEN the configured TTL value is used in the pipeline
        """
        session = _make_session()
        mock_redis = _make_mock_redis(session)
        mock_pipe = mock_redis._mock_pipe

        custom_ttl = 7200  # 2 hours
        manager = RedisSessionManager(redis_client=mock_redis, ttl_seconds=custom_ttl)
        await manager.get_session("test-session-123")

        # Verify the custom TTL was used in pipeline expire call
        mock_pipe.expire.assert_any_call("session:test-session-123", custom_ttl)

    @pytest.mark.asyncio
    async def test_get_session_no_user_key_refresh_when_no_user_id(self) -> None:
        """GIVEN a session without user_id
        WHEN get_session is called
        THEN only the session key TTL is refreshed via direct call (no pipeline)
        """
        session = _make_session(user_id="")
        mock_redis = _make_mock_redis(session)
        mock_pipe = mock_redis._mock_pipe

        manager = RedisSessionManager(redis_client=mock_redis, ttl_seconds=3600)
        await manager.get_session("test-session-123")

        # S5: Direct expire call (no pipeline overhead for single key)
        mock_redis.expire.assert_awaited_once_with("session:test-session-123", 3600)
        # Pipeline should NOT be used
        assert mock_pipe.expire.call_count == 0

    @pytest.mark.asyncio
    async def test_get_session_returns_session_when_ttl_refresh_fails(self) -> None:
        """GIVEN a valid session stored in Redis
        WHEN get_session is called and the TTL refresh pipeline fails
        THEN the session is still returned (Finding 5: TTL refresh is best-effort)
        """
        session = _make_session()
        mock_redis = _make_mock_redis(session)
        mock_pipe = mock_redis._mock_pipe

        # Simulate pipeline execution failure (e.g., transient Redis connectivity)
        mock_pipe.execute = AsyncMock(side_effect=Exception("Redis connection lost"))

        manager = RedisSessionManager(redis_client=mock_redis, ttl_seconds=3600)
        result = await manager.get_session("test-session-123")

        # Session should still be returned despite TTL refresh failure
        assert result is not None
        assert result.session_id == "test-session-123"
        assert result.name == "Test Session"
