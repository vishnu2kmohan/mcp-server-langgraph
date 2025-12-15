"""Tests for token denylist functionality.

Per OWASP: "When an explicit session termination event occurs, a digest
or hash of any associated JWTs should be submitted to a denylist."

Following TDD: Write tests FIRST, then implementation.
"""

import gc
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.unit
@pytest.mark.auth
@pytest.mark.xdist_group(name="token_denylist_tests")
class TestInMemoryTokenDenylist:
    """Test InMemoryTokenDenylist implementation."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_add_and_check_denied_token(self):
        """Test adding a token to denylist and checking if denied."""
        from mcp_server_langgraph.auth.token_denylist import InMemoryTokenDenylist

        denylist = InMemoryTokenDenylist()
        jti = "test-token-id-123"
        expires_at = datetime.now(UTC) + timedelta(hours=1)

        await denylist.add(jti, expires_at)

        assert await denylist.is_denied(jti) is True

    @pytest.mark.asyncio
    async def test_non_existent_token_not_denied(self):
        """Test that non-existent token is not denied."""
        from mcp_server_langgraph.auth.token_denylist import InMemoryTokenDenylist

        denylist = InMemoryTokenDenylist()

        assert await denylist.is_denied("non-existent-token") is False

    @pytest.mark.asyncio
    async def test_expired_token_removed_from_denylist(self):
        """Test that expired tokens are automatically removed."""
        from mcp_server_langgraph.auth.token_denylist import InMemoryTokenDenylist

        denylist = InMemoryTokenDenylist()
        jti = "expired-token-id"
        # Already expired
        expires_at = datetime.now(UTC) - timedelta(seconds=1)

        await denylist.add(jti, expires_at)

        # Should not be denied because it's already expired
        assert await denylist.is_denied(jti) is False

    @pytest.mark.asyncio
    async def test_multiple_tokens_can_be_denied(self):
        """Test that multiple tokens can be added to denylist."""
        from mcp_server_langgraph.auth.token_denylist import InMemoryTokenDenylist

        denylist = InMemoryTokenDenylist()
        expires_at = datetime.now(UTC) + timedelta(hours=1)

        await denylist.add("token-1", expires_at)
        await denylist.add("token-2", expires_at)
        await denylist.add("token-3", expires_at)

        assert await denylist.is_denied("token-1") is True
        assert await denylist.is_denied("token-2") is True
        assert await denylist.is_denied("token-3") is True
        assert await denylist.is_denied("token-4") is False

    @pytest.mark.asyncio
    async def test_remove_token_from_denylist(self):
        """Test removing a token from denylist."""
        from mcp_server_langgraph.auth.token_denylist import InMemoryTokenDenylist

        denylist = InMemoryTokenDenylist()
        jti = "test-token-id"
        expires_at = datetime.now(UTC) + timedelta(hours=1)

        await denylist.add(jti, expires_at)
        assert await denylist.is_denied(jti) is True

        await denylist.remove(jti)
        assert await denylist.is_denied(jti) is False


@pytest.mark.unit
@pytest.mark.auth
@pytest.mark.xdist_group(name="token_denylist_tests")
class TestRedisTokenDenylist:
    """Test RedisTokenDenylist implementation."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.fixture
    def mock_redis(self):
        """Create mock Redis client."""
        redis = MagicMock()
        redis.setex = AsyncMock(return_value=True)
        redis.exists = AsyncMock(return_value=0)
        redis.delete = AsyncMock(return_value=1)
        return redis

    @pytest.mark.asyncio
    async def test_add_token_calls_redis_setex(self, mock_redis):
        """Test that adding token calls Redis SETEX with correct TTL."""
        from mcp_server_langgraph.auth.token_denylist import RedisTokenDenylist

        denylist = RedisTokenDenylist(mock_redis)
        jti = "test-token-id"
        expires_at = datetime.now(UTC) + timedelta(hours=1)

        await denylist.add(jti, expires_at)

        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args
        assert call_args[0][0] == "token_denylist:test-token-id"
        # TTL should be approximately 3600 seconds (1 hour)
        assert 3500 <= call_args[0][1] <= 3700
        assert call_args[0][2] == "revoked"

    @pytest.mark.asyncio
    async def test_is_denied_calls_redis_exists(self, mock_redis):
        """Test that is_denied calls Redis EXISTS."""
        from mcp_server_langgraph.auth.token_denylist import RedisTokenDenylist

        mock_redis.exists = AsyncMock(return_value=1)  # Token exists
        denylist = RedisTokenDenylist(mock_redis)

        result = await denylist.is_denied("test-token-id")

        assert result is True
        mock_redis.exists.assert_called_once_with("token_denylist:test-token-id")

    @pytest.mark.asyncio
    async def test_is_denied_returns_false_when_not_exists(self, mock_redis):
        """Test that is_denied returns False when token not in Redis."""
        from mcp_server_langgraph.auth.token_denylist import RedisTokenDenylist

        mock_redis.exists = AsyncMock(return_value=0)
        denylist = RedisTokenDenylist(mock_redis)

        result = await denylist.is_denied("non-existent-token")

        assert result is False

    @pytest.mark.asyncio
    async def test_remove_token_calls_redis_delete(self, mock_redis):
        """Test that remove calls Redis DELETE."""
        from mcp_server_langgraph.auth.token_denylist import RedisTokenDenylist

        denylist = RedisTokenDenylist(mock_redis)

        await denylist.remove("test-token-id")

        mock_redis.delete.assert_called_once_with("token_denylist:test-token-id")

    @pytest.mark.asyncio
    async def test_expired_token_not_added(self, mock_redis):
        """Test that already expired tokens are not added to denylist."""
        from mcp_server_langgraph.auth.token_denylist import RedisTokenDenylist

        denylist = RedisTokenDenylist(mock_redis)
        jti = "expired-token"
        expires_at = datetime.now(UTC) - timedelta(hours=1)  # Already expired

        await denylist.add(jti, expires_at)

        # Should not call setex for expired token
        mock_redis.setex.assert_not_called()

    @pytest.mark.asyncio
    async def test_custom_key_prefix(self, mock_redis):
        """Test that custom key prefix is used."""
        from mcp_server_langgraph.auth.token_denylist import RedisTokenDenylist

        denylist = RedisTokenDenylist(mock_redis, key_prefix="custom_prefix:")
        jti = "test-token"
        expires_at = datetime.now(UTC) + timedelta(hours=1)

        await denylist.add(jti, expires_at)

        call_args = mock_redis.setex.call_args
        assert call_args[0][0] == "custom_prefix:test-token"


@pytest.mark.unit
@pytest.mark.auth
@pytest.mark.xdist_group(name="token_denylist_tests")
class TestTokenDenylistFactory:
    """Test token denylist factory function."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_create_inmemory_denylist(self):
        """Test creating in-memory denylist."""
        from mcp_server_langgraph.auth.token_denylist import create_token_denylist

        denylist = create_token_denylist(backend="memory")

        from mcp_server_langgraph.auth.token_denylist import InMemoryTokenDenylist

        assert isinstance(denylist, InMemoryTokenDenylist)

    def test_create_redis_denylist(self):
        """Test creating Redis denylist."""
        from mcp_server_langgraph.auth.token_denylist import create_token_denylist

        mock_redis = MagicMock()
        denylist = create_token_denylist(backend="redis", redis_client=mock_redis)

        from mcp_server_langgraph.auth.token_denylist import RedisTokenDenylist

        assert isinstance(denylist, RedisTokenDenylist)

    def test_invalid_backend_raises_error(self):
        """Test that invalid backend raises ValueError."""
        from mcp_server_langgraph.auth.token_denylist import create_token_denylist

        with pytest.raises(ValueError, match="Unsupported backend"):
            create_token_denylist(backend="invalid")
