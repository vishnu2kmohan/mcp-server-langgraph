"""
Unit tests for SecureConnectionConfig credential manager.

Tests TTL-cached credential retrieval from a SecretsProvider,
cache invalidation, SSL configuration, and error handling.
"""

import gc
import json
from unittest.mock import AsyncMock

import pytest
from cachetools import TTLCache

from mcp_server_langgraph.execution.sql.credential_manager import (
    CredentialRetrievalError,
    SecureConnectionConfig,
)

pytestmark = pytest.mark.unit

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_CREDENTIALS = {
    "host": "db.example.com",
    "port": 5432,
    "user": "app_user",
    "password": "secret123",
    "database": "mydb",
}


def _make_provider(return_value: str | None = None) -> AsyncMock:
    """Create a mock SecretsProvider with configurable get_secret return."""
    provider = AsyncMock()  # noqa: async-mock-config - mock secrets provider with dynamic attributes
    if return_value is None:
        return_value = json.dumps(SAMPLE_CREDENTIALS)
    provider.get_secret = AsyncMock(return_value=return_value)  # noqa: async-mock-config
    provider.set_secret = AsyncMock()  # noqa: async-mock-config
    provider.delete_secret = AsyncMock()  # noqa: async-mock-config
    return provider


@pytest.fixture
def shared_cache() -> TTLCache:
    """Create a fresh TTLCache for test isolation."""
    return TTLCache(maxsize=1000, ttl=300)


# ---------------------------------------------------------------------------
# SecureConnectionConfig - credential retrieval
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.xdist_group(name="credential_manager")
class TestSecureConnectionConfigGetCredentials:
    """Verify credential retrieval, caching, and parsing."""

    def teardown_method(self) -> None:
        gc.collect()

    @pytest.mark.asyncio
    async def test_get_credentials_returns_parsed_json(self) -> None:
        """JSON secret payload is parsed into a dict."""
        provider = _make_provider()
        cache = TTLCache(maxsize=1000, ttl=300)
        config = SecureConnectionConfig(
            secrets_provider=provider,
            dialect="postgresql",
            tenant_id="tenant-1",
            cache=cache,
        )
        creds = await config.get_credentials("/database/tenant-1", "DB_PROD")
        assert creds == SAMPLE_CREDENTIALS
        provider.get_secret.assert_awaited_once_with("/database/tenant-1/DB_PROD")

    @pytest.mark.asyncio
    async def test_get_credentials_cache_hit(self) -> None:
        """Second call returns cached value without hitting provider again."""
        provider = _make_provider()
        cache = TTLCache(maxsize=1000, ttl=300)
        config = SecureConnectionConfig(
            secrets_provider=provider,
            dialect="postgresql",
            tenant_id="tenant-1",
            cache=cache,
        )
        first = await config.get_credentials("/db", "KEY")
        second = await config.get_credentials("/db", "KEY")
        assert first == second
        # Provider should only be called once
        assert provider.get_secret.await_count == 1

    @pytest.mark.asyncio
    async def test_get_credentials_cache_miss_after_invalidation(self) -> None:
        """After cache invalidation, provider is called again."""
        provider = _make_provider()
        cache = TTLCache(maxsize=1000, ttl=300)
        config = SecureConnectionConfig(
            secrets_provider=provider,
            dialect="postgresql",
            tenant_id="tenant-1",
            cache=cache,
        )
        await config.get_credentials("/db", "KEY")
        config.invalidate_cache("tenant-1")
        await config.get_credentials("/db", "KEY")
        assert provider.get_secret.await_count == 2

    @pytest.mark.asyncio
    async def test_get_credentials_raw_connection_string_fallback(self) -> None:
        """Non-JSON secret is wrapped as connection_string with parsed URL fields."""
        raw = "postgresql://user:pass@host/db"
        provider = _make_provider(return_value=raw)
        cache = TTLCache(maxsize=1000, ttl=300)
        config = SecureConnectionConfig(
            secrets_provider=provider,
            dialect="postgresql",
            tenant_id="tenant-2",
            cache=cache,
        )
        creds = await config.get_credentials("/db", "CONN")
        # URL is parsed into structured fields for driver compatibility
        assert creds["connection_string"] == raw
        assert creds["host"] == "host"
        assert creds["username"] == "user"
        assert creds["password"] == "pass"
        assert creds["database"] == "db"

    @pytest.mark.asyncio
    async def test_get_credentials_not_found_raises(self) -> None:
        """None from provider raises CredentialRetrievalError."""
        provider = AsyncMock()  # noqa: async-mock-config - mock secrets provider
        provider.get_secret = AsyncMock(return_value=None)  # noqa: async-mock-config
        cache = TTLCache(maxsize=1000, ttl=300)
        config = SecureConnectionConfig(
            secrets_provider=provider,
            dialect="postgresql",
            tenant_id="tenant-3",
            cache=cache,
        )
        with pytest.raises(CredentialRetrievalError, match="Secret not found"):
            await config.get_credentials("/db", "MISSING")

    @pytest.mark.asyncio
    async def test_get_credentials_correct_secret_id_format(self) -> None:
        """Secret ID is constructed as '{secret_path}/{secret_key}'."""
        provider = _make_provider()
        cache = TTLCache(maxsize=1000, ttl=300)
        config = SecureConnectionConfig(
            secrets_provider=provider,
            dialect="mysql",
            tenant_id="tenant-4",
            cache=cache,
        )
        await config.get_credentials("/services/mysql", "CREDS")
        provider.get_secret.assert_awaited_once_with("/services/mysql/CREDS")

    @pytest.mark.asyncio
    async def test_get_credentials_different_tenants_separate_cache(self) -> None:
        """Different tenants maintain separate cache entries."""
        provider = _make_provider()
        cache = TTLCache(maxsize=1000, ttl=300)
        config_a = SecureConnectionConfig(
            secrets_provider=provider,
            dialect="postgresql",
            tenant_id="tenant-a",
            cache=cache,
        )
        config_b = SecureConnectionConfig(
            secrets_provider=provider,
            dialect="postgresql",
            tenant_id="tenant-b",
            cache=cache,
        )
        await config_a.get_credentials("/db", "KEY")
        await config_b.get_credentials("/db", "KEY")
        # Both tenants should trigger separate provider calls
        assert provider.get_secret.await_count == 2

    @pytest.mark.asyncio
    async def test_custom_cache_ttl(self) -> None:
        """Per-instance TTL creates a cache with that TTL."""
        provider = _make_provider()
        config = SecureConnectionConfig(
            secrets_provider=provider,
            dialect="postgresql",
            tenant_id="tenant-ttl",
            cache_ttl=60,
        )
        creds = await config.get_credentials("/db", "KEY")
        assert creds == SAMPLE_CREDENTIALS


# ---------------------------------------------------------------------------
# Cache invalidation
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.xdist_group(name="credential_manager")
class TestCacheInvalidation:
    """Verify cache invalidation by tenant and dialect."""

    def teardown_method(self) -> None:
        gc.collect()

    @pytest.mark.asyncio
    async def test_invalidate_by_tenant(self) -> None:
        """Invalidate all entries for a specific tenant."""
        provider = _make_provider()
        cache = TTLCache(maxsize=1000, ttl=300)
        config = SecureConnectionConfig(
            secrets_provider=provider,
            dialect="postgresql",
            tenant_id="tenant-inv",
            cache=cache,
        )
        await config.get_credentials("/db", "A")
        await config.get_credentials("/db", "B")
        count = config.invalidate_cache("tenant-inv")
        assert count == 2

    @pytest.mark.asyncio
    async def test_invalidate_by_tenant_and_dialect(self) -> None:
        """Invalidate only entries matching tenant AND dialect."""
        provider = _make_provider()
        cache = TTLCache(maxsize=1000, ttl=300)
        pg_config = SecureConnectionConfig(
            secrets_provider=provider,
            dialect="postgresql",
            tenant_id="tenant-dial",
            cache=cache,
        )
        mysql_config = SecureConnectionConfig(
            secrets_provider=provider,
            dialect="mysql",
            tenant_id="tenant-dial",
            cache=cache,
        )
        await pg_config.get_credentials("/db", "A")
        await mysql_config.get_credentials("/db", "A")
        count = pg_config.invalidate_cache("tenant-dial", dialect="postgresql")
        assert count == 1
        # MySQL entry should still be cached
        # Fetching it again should NOT hit the provider again
        # (provider already called twice: once for pg, once for mysql)
        await mysql_config.get_credentials("/db", "A")
        # Still only 2 calls total (pg + mysql initial), mysql was cached
        assert provider.get_secret.await_count == 2

    @pytest.mark.asyncio
    async def test_invalidate_nonexistent_tenant_returns_zero(self) -> None:
        """Invalidating a tenant with no cache entries returns 0."""
        cache = TTLCache(maxsize=1000, ttl=300)
        provider = _make_provider()
        config = SecureConnectionConfig(
            secrets_provider=provider,
            dialect="postgresql",
            tenant_id="dummy",
            cache=cache,
        )
        count = config.invalidate_cache("no-such-tenant")
        assert count == 0

    @pytest.mark.asyncio
    async def test_clear_cache_removes_all(self) -> None:
        """clear_cache removes all entries from the shared cache."""
        provider = _make_provider()
        cache = TTLCache(maxsize=1000, ttl=300)
        config_a = SecureConnectionConfig(
            secrets_provider=provider,
            dialect="postgresql",
            tenant_id="tenant-clear-a",
            cache=cache,
        )
        config_b = SecureConnectionConfig(
            secrets_provider=provider,
            dialect="mysql",
            tenant_id="tenant-clear-b",
            cache=cache,
        )
        await config_a.get_credentials("/db", "KEY")
        await config_b.get_credentials("/db", "KEY")
        config_a.clear_cache()
        # After clear, fetching should hit provider again
        await config_a.get_credentials("/db", "KEY")
        assert provider.get_secret.await_count == 3

    @pytest.mark.asyncio
    async def test_invalidate_does_not_affect_other_tenants(self) -> None:
        """Invalidating one tenant does not affect another."""
        provider = _make_provider()
        cache = TTLCache(maxsize=1000, ttl=300)
        config_keep = SecureConnectionConfig(
            secrets_provider=provider,
            dialect="postgresql",
            tenant_id="tenant-keep",
            cache=cache,
        )
        config_remove = SecureConnectionConfig(
            secrets_provider=provider,
            dialect="postgresql",
            tenant_id="tenant-remove",
            cache=cache,
        )
        await config_keep.get_credentials("/db", "KEY")
        await config_remove.get_credentials("/db", "KEY")
        config_remove.invalidate_cache("tenant-remove")
        # tenant-keep should still be cached
        await config_keep.get_credentials("/db", "KEY")
        assert provider.get_secret.await_count == 2  # only initial 2 calls

    @pytest.mark.asyncio
    async def test_shared_cache_cross_instance(self) -> None:
        """Two instances sharing the same cache see each other's entries."""
        provider = _make_provider()
        cache = TTLCache(maxsize=1000, ttl=300)
        config_a = SecureConnectionConfig(
            secrets_provider=provider,
            dialect="postgresql",
            tenant_id="tenant-shared",
            cache=cache,
        )
        config_b = SecureConnectionConfig(
            secrets_provider=provider,
            dialect="postgresql",
            tenant_id="tenant-shared",
            cache=cache,
        )
        await config_a.get_credentials("/db", "KEY")
        # config_b should see the cache entry from config_a
        await config_b.get_credentials("/db", "KEY")
        assert provider.get_secret.await_count == 1  # only 1 call, cache hit on second


# ---------------------------------------------------------------------------
# SSL configuration
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.xdist_group(name="credential_manager")
class TestSSLConfig:
    """Verify SSL configuration for different modes."""

    def teardown_method(self) -> None:
        gc.collect()

    def test_ssl_mode_require(self) -> None:
        """ssl_mode=require returns ssl=True, ssl_verify=False."""
        provider = _make_provider()
        config = SecureConnectionConfig(
            secrets_provider=provider,
            dialect="postgresql",
            tenant_id="ssl-test",
        )
        ssl = config.get_ssl_config("require")
        assert ssl["ssl"] is True
        assert ssl["ssl_verify"] is False

    def test_ssl_mode_disable(self) -> None:
        """ssl_mode=disable returns ssl=False only."""
        provider = _make_provider()
        config = SecureConnectionConfig(
            secrets_provider=provider,
            dialect="postgresql",
            tenant_id="ssl-test",
        )
        ssl = config.get_ssl_config("disable")
        assert ssl == {"ssl": False}

    def test_ssl_mode_verify_full(self) -> None:
        """ssl_mode=verify-full returns ssl=True, ssl_verify=True."""
        provider = _make_provider()
        config = SecureConnectionConfig(
            secrets_provider=provider,
            dialect="postgresql",
            tenant_id="ssl-test",
        )
        ssl = config.get_ssl_config("verify-full")
        assert ssl["ssl"] is True
        assert ssl["ssl_verify"] is True

    def test_ssl_mode_verify_ca(self) -> None:
        """ssl_mode=verify-ca returns ssl=True, ssl_verify=True."""
        provider = _make_provider()
        config = SecureConnectionConfig(
            secrets_provider=provider,
            dialect="postgresql",
            tenant_id="ssl-test",
        )
        ssl = config.get_ssl_config("verify-ca")
        assert ssl["ssl"] is True
        assert ssl["ssl_verify"] is True

    def test_ssl_mode_default_is_require(self) -> None:
        """Default ssl_mode is 'require'."""
        provider = _make_provider()
        config = SecureConnectionConfig(
            secrets_provider=provider,
            dialect="postgresql",
            tenant_id="ssl-test",
        )
        ssl = config.get_ssl_config()
        assert ssl["ssl"] is True
        assert ssl["ssl_verify"] is False


# ---------------------------------------------------------------------------
# CredentialRetrievalError
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.xdist_group(name="credential_manager")
class TestCredentialRetrievalError:
    """Verify exception properties."""

    def teardown_method(self) -> None:
        gc.collect()

    def test_exception_message_contains_details(self) -> None:
        """Error contains the descriptive message."""
        err = CredentialRetrievalError("Secret not found: /db/KEY")
        assert str(err) == "Secret not found: /db/KEY"

    def test_exception_inherits_from_exception(self) -> None:
        """CredentialRetrievalError is a subclass of Exception."""
        assert issubclass(CredentialRetrievalError, Exception)

    def test_exception_can_be_caught_as_exception(self) -> None:
        """Can be caught with a generic except Exception clause."""
        with pytest.raises(Exception, match="test error"):
            raise CredentialRetrievalError("test error")

    def test_exception_args_stored_correctly(self) -> None:
        """Args are stored on the exception."""
        err = CredentialRetrievalError("details here")
        assert err.args == ("details here",)
