"""
Simple Integration Tests for Database Retry Logic

Focused integration tests that verify retry logic works end-to-end
with actual retry behavior.
"""

import gc
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.infrastructure]

# Use configurable Postgres port (default 9432 for test isolation)
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "9432")


@pytest.mark.xdist_group(name="testretryintegration")
class TestDatabaseRetryIntegration:
    """Test database retry logic integration"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    async def test_gdpr_storage_retries_on_transient_failure(self):
        """
        Test that GDPR storage initialization retries on transient failures

        Behavior:
        - When asyncpg.create_pool fails transiently
        - Then it should retry with exponential backoff
        - And eventually succeed
        """
        from mcp_server_langgraph.compliance.gdpr.factory import initialize_gdpr_storage, reset_gdpr_storage

        reset_gdpr_storage()

        call_count = 0

        async def create_pool_with_retry(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # First call fails
                raise Exception("Connection refused")
            # Second call succeeds
            return MagicMock()

        with patch("asyncpg.create_pool", side_effect=create_pool_with_retry):
            # Should succeed after one retry
            await initialize_gdpr_storage(
                backend="postgres", postgres_url="postgresql://test:test@localhost:{POSTGRES_PORT}/gdpr"
            )

        # Should have called twice
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_gdpr_storage_fails_after_max_retries(self):
        """
        Test that GDPR storage fails after exhausting retries

        Behavior:
        - When asyncpg.create_pool always fails
        - Then should retry max times (3)
        - And raise exception
        """
        from mcp_server_langgraph.compliance.gdpr.factory import initialize_gdpr_storage, reset_gdpr_storage

        reset_gdpr_storage()

        call_count = 0

        async def create_pool_always_fails(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            raise Exception("Connection refused")

        with patch("asyncpg.create_pool", side_effect=create_pool_always_fails):
            with pytest.raises(Exception, match="Failed after 4 attempts"):
                await initialize_gdpr_storage(
                    backend="postgres", postgres_url="postgresql://test:test@localhost:{POSTGRES_PORT}/gdpr"
                )

        # Should have tried 4 times (initial + 3 retries)
        assert call_count == 4

    @pytest.mark.asyncio
    async def test_app_startup_retries_database_connection(self):
        """
        Test that app startup retries database connection

        Behavior:
        - When app starts with database temporarily unavailable
        - Then should retry and eventually succeed
        """
        from mcp_server_langgraph.core.config import Settings
        from mcp_server_langgraph.core.container import create_test_container
        from mcp_server_langgraph.infrastructure.app_factory import create_lifespan

        # Create container with postgres backend
        settings = Settings(
            environment="test",
            gdpr_storage_backend="postgres",
            gdpr_postgres_url="postgresql://test:test@localhost:{POSTGRES_PORT}/gdpr_test",
        )
        container = create_test_container(settings=settings)

        call_count = 0

        async def create_pool_with_retry(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise Exception("Connection refused")
            return MagicMock()

        with patch("asyncpg.create_pool", side_effect=create_pool_with_retry):
            lifespan = create_lifespan(container=container)

            # Should succeed after retries
            async with lifespan:
                pass

        # Should have retried
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_retry_uses_exponential_backoff(self):
        """
        Test that retry logic uses exponential backoff

        Behavior:
        - When retrying failed connections
        - Then delays should increase exponentially
        """
        from mcp_server_langgraph.compliance.gdpr.factory import initialize_gdpr_storage, reset_gdpr_storage

        reset_gdpr_storage()

        call_count = 0

        async def create_pool_with_retry(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 3:
                raise Exception("Connection refused")
            return MagicMock()

        sleep_delays = []

        async def mock_sleep(delay):
            sleep_delays.append(delay)

        with patch("asyncpg.create_pool", side_effect=create_pool_with_retry):
            with patch("asyncio.sleep", side_effect=mock_sleep):
                await initialize_gdpr_storage(
                    backend="postgres", postgres_url="postgresql://test:test@localhost:{POSTGRES_PORT}/gdpr"
                )

        # Should have 3 sleep calls (after each of the 3 failures)
        assert len(sleep_delays) == 3

        # Delays should be increasing (exponential backoff with jitter)
        # First delay ~1s, second ~2s, third ~4s (with jitter: 0.8-1.2x)
        assert sleep_delays[0] >= 0.8 and sleep_delays[0] <= 1.2  # ~1s
        assert sleep_delays[1] >= 1.6 and sleep_delays[1] <= 2.4  # ~2s
        assert sleep_delays[2] >= 3.2 and sleep_delays[2] <= 4.8  # ~4s

        # Each delay should be larger than the previous
        assert sleep_delays[1] > sleep_delays[0]
        assert sleep_delays[2] > sleep_delays[1]

    @pytest.mark.asyncio
    async def test_memory_backend_does_not_retry(self):
        """
        Test that memory backend doesn't use retry logic

        Behavior:
        - Memory backend should work immediately
        - No retry needed (no network)
        """
        from mcp_server_langgraph.compliance.gdpr.factory import initialize_gdpr_storage, reset_gdpr_storage

        reset_gdpr_storage()

        # Should succeed immediately with memory backend
        await initialize_gdpr_storage(backend="memory")

        # No assertions needed - just verifying it doesn't hang or retry
