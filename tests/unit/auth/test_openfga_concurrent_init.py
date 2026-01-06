"""
Unit tests for OpenFGA client concurrent initialization.

TDD: Tests for race condition protection in _ensure_initialized().

ISSUE: Without asyncio.Lock, concurrent calls to _ensure_initialized() can:
1. All see _initialized = False
2. Each create a new OpenFgaClient
3. Overwrite self._client without closing the old one
4. Leave aiohttp.ClientSession instances unclosed (resource leak)

This test file validates the fix using asyncio.Lock for synchronization.
"""

from __future__ import annotations

import asyncio
import gc
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

if TYPE_CHECKING:
    pass

pytestmark = [
    pytest.mark.unit,
    pytest.mark.auth,
    pytest.mark.openfga,
    pytest.mark.xdist_group(name="openfga_concurrent_init"),
]


class TestOpenFGAClientConcurrentInitialization:
    """
    Tests for concurrent initialization race condition fix.

    The issue: _ensure_initialized() without a lock allows multiple concurrent
    calls to each create a new OpenFgaClient, leaking aiohttp sessions.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_concurrent_initialization_creates_single_client(self) -> None:
        """
        GIVEN: Multiple concurrent calls to _ensure_initialized()
        WHEN: All calls execute before initialization completes
        THEN: Only ONE OpenFgaClient should be created (not multiple)

        This verifies the asyncio.Lock prevents the race condition.
        """
        from mcp_server_langgraph.auth.openfga import OpenFGAClient, OpenFGAConfig

        # Create client with minimal config (no OIDC, no store lookup needed)
        config = OpenFGAConfig(
            api_url="http://localhost:8080",
            store_id="test-store-id",  # Pre-set to skip lookup
            model_id="test-model-id",  # Pre-set to skip lookup
        )
        client = OpenFGAClient(config)

        # Track how many times OpenFgaClient constructor is called
        call_count = 0
        original_client = None

        def track_client_creation(*args, **kwargs):
            nonlocal call_count, original_client
            call_count += 1
            # Create a mock that tracks its creation
            mock_client = MagicMock()
            mock_client.close = AsyncMock(return_value=None)
            if original_client is None:
                original_client = mock_client
            return mock_client

        # Patch the OpenFgaClient constructor from the SDK
        with patch(
            "mcp_server_langgraph.auth.openfga.OpenFgaClient",
            side_effect=track_client_creation,
        ):
            # Run 10 concurrent initialization calls
            tasks = [client._ensure_initialized() for _ in range(10)]
            await asyncio.gather(*tasks)

        # THEN: Only ONE client should have been created
        assert call_count == 1, (
            f"Expected 1 OpenFgaClient creation, but got {call_count}. "
            "Race condition detected - multiple clients created concurrently."
        )

    @pytest.mark.asyncio
    async def test_concurrent_initialization_all_callers_get_same_client(self) -> None:
        """
        GIVEN: Multiple concurrent calls to check() method
        WHEN: All calls trigger _ensure_initialized()
        THEN: All callers should use the SAME underlying client

        This verifies thread-safety of the singleton pattern.
        """
        from mcp_server_langgraph.auth.openfga import OpenFGAClient, OpenFGAConfig

        config = OpenFGAConfig(
            api_url="http://localhost:8080",
            store_id="test-store-id",
            model_id="test-model-id",
        )
        client = OpenFGAClient(config)

        # Track client instances
        created_clients = []

        def track_client_creation(*args, **kwargs):
            mock_client = MagicMock()
            mock_client.close = AsyncMock(return_value=None)
            mock_client.check = AsyncMock(return_value=MagicMock(allowed=True))
            created_clients.append(mock_client)
            return mock_client

        with patch(
            "mcp_server_langgraph.auth.openfga.OpenFgaClient",
            side_effect=track_client_creation,
        ):
            # Run concurrent initializations
            await asyncio.gather(*[client._ensure_initialized() for _ in range(5)])

            # All should reference the same internal client
            # (The list should have only 1 client if lock works correctly)
            assert len(created_clients) == 1, (
                f"Expected 1 client, got {len(created_clients)}. Race condition: multiple clients were created."
            )

    @pytest.mark.asyncio
    async def test_client_closed_before_replacement_on_token_refresh(self) -> None:
        """
        GIVEN: An already-initialized client with an expiring OIDC token
        WHEN: _ensure_initialized() is called and token refresh triggers re-init
        THEN: The OLD client should be closed before creating a new one

        This prevents aiohttp.ClientSession leaks from token refresh.
        """
        from mcp_server_langgraph.auth.openfga import OpenFGAClient, OpenFGAConfig

        config = OpenFGAConfig(
            api_url="http://localhost:8080",
            store_id="test-store-id",
            model_id="test-model-id",
            oidc_client_id="test-client",
            oidc_client_secret="test-secret",
            oidc_issuer="http://keycloak:8080/realms/test",
        )
        client = OpenFGAClient(config)

        # Create a mock for the first client
        first_mock_client = MagicMock()
        first_mock_client.close = AsyncMock(return_value=None)

        second_mock_client = MagicMock()
        second_mock_client.close = AsyncMock(return_value=None)

        client_creation_count = 0

        def create_mock_client(*args, **kwargs):
            nonlocal client_creation_count
            client_creation_count += 1
            if client_creation_count == 1:
                return first_mock_client
            return second_mock_client

        with (
            patch(
                "mcp_server_langgraph.auth.openfga.OpenFgaClient",
                side_effect=create_mock_client,
            ),
            patch.object(
                client,
                "_get_oidc_access_token",
                AsyncMock(return_value="mock-token"),
            ),
        ):
            # First initialization
            await client._ensure_initialized()
            assert client._initialized is True
            assert client._client is first_mock_client

            # Simulate token expiration by setting expires_at to past
            # NOTE: Must use a real past timestamp (not 0) because _should_refresh_token()
            # returns False if _oidc_token_expires_at is falsy
            import time

            client._oidc_token_expires_at = time.time() - 3600  # 1 hour in the past

            # Second initialization should trigger token refresh
            await client._ensure_initialized()

            # THEN: First client should have been closed
            first_mock_client.close.assert_called_once()

            # And we should have the second client now
            assert client._client is second_mock_client
            assert client_creation_count == 2

    @pytest.mark.asyncio
    async def test_lock_attribute_exists_on_client(self) -> None:
        """
        GIVEN: A new OpenFGAClient instance
        WHEN: The client is created
        THEN: It should have an asyncio.Lock for initialization synchronization

        This is a structural test ensuring the lock is properly initialized.
        """
        from mcp_server_langgraph.auth.openfga import OpenFGAClient, OpenFGAConfig

        config = OpenFGAConfig(
            api_url="http://localhost:8080",
            store_id="test-store-id",
            model_id="test-model-id",
        )
        client = OpenFGAClient(config)

        # THEN: Client should have an _init_lock attribute
        assert hasattr(client, "_init_lock"), (
            "OpenFGAClient should have an _init_lock attribute for synchronizing concurrent initialization calls."
        )
        assert isinstance(client._init_lock, asyncio.Lock), "_init_lock should be an asyncio.Lock instance"

    @pytest.mark.asyncio
    @pytest.mark.timeout(5)  # Prevent infinite hangs
    async def test_initialization_is_atomic(self) -> None:
        """
        GIVEN: Multiple concurrent callers during slow initialization
        WHEN: First caller is still initializing (e.g., waiting on store lookup)
        THEN: Other callers should wait on the lock, not proceed with their own init

        This simulates a slow initialization scenario.
        """
        from mcp_server_langgraph.auth.openfga import OpenFGAClient, OpenFGAConfig

        config = OpenFGAConfig(
            api_url="http://localhost:8080",
            store_id="test-store-id",
            model_id="test-model-id",
        )
        client = OpenFGAClient(config)

        # Track order of events
        events: list[str] = []

        # NOTE: OpenFgaClient constructor is SYNCHRONOUS, so side_effect must be sync.
        # The lock protection happens at the async _ensure_initialized level.
        def track_client_constructor(*args, **kwargs):
            events.append("constructor_called")
            mock_client = MagicMock()
            mock_client.close = AsyncMock(return_value=None)
            return mock_client

        with patch(
            "mcp_server_langgraph.auth.openfga.OpenFgaClient",
            side_effect=track_client_constructor,
        ):
            # Run multiple concurrent initializations
            # The lock should serialize these, resulting in only ONE constructor call
            tasks = [client._ensure_initialized() for _ in range(5)]
            await asyncio.gather(*tasks)

        # THEN: Constructor should only be called once
        assert events.count("constructor_called") == 1, (
            f"Constructor called {events.count('constructor_called')} times. Lock should prevent concurrent initialization."
        )


class TestOpenFGAClientResourceCleanup:
    """Tests for proper resource cleanup during client lifecycle."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_close_method_closes_underlying_client(self) -> None:
        """
        GIVEN: An initialized OpenFGAClient
        WHEN: close() is called
        THEN: The underlying OpenFgaClient should be closed

        This ensures proper cleanup of aiohttp resources.
        """
        from mcp_server_langgraph.auth.openfga import OpenFGAClient, OpenFGAConfig

        config = OpenFGAConfig(
            api_url="http://localhost:8080",
            store_id="test-store-id",
            model_id="test-model-id",
        )
        client = OpenFGAClient(config)

        mock_sdk_client = MagicMock()
        mock_sdk_client.close = AsyncMock(return_value=None)

        with patch(
            "mcp_server_langgraph.auth.openfga.OpenFgaClient",
            return_value=mock_sdk_client,
        ):
            await client._ensure_initialized()
            assert client._client is mock_sdk_client

            # Close the wrapper
            await client.close()

            # THEN: SDK client should be closed
            mock_sdk_client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_reinitialization_closes_old_client(self) -> None:
        """
        GIVEN: An initialized client that needs reinitialization
        WHEN: A new client is created to replace the old one
        THEN: The old client should be properly closed first

        This prevents session leaks when client is replaced.
        """
        from mcp_server_langgraph.auth.openfga import OpenFGAClient, OpenFGAConfig

        config = OpenFGAConfig(
            api_url="http://localhost:8080",
            store_id="test-store-id",
            model_id="test-model-id",
        )
        client = OpenFGAClient(config)

        old_sdk_client = MagicMock()
        old_sdk_client.close = AsyncMock(return_value=None)

        new_sdk_client = MagicMock()
        new_sdk_client.close = AsyncMock(return_value=None)

        call_count = 0

        def create_client(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return old_sdk_client if call_count == 1 else new_sdk_client

        with patch(
            "mcp_server_langgraph.auth.openfga.OpenFgaClient",
            side_effect=create_client,
        ):
            # First initialization
            await client._ensure_initialized()
            assert client._client is old_sdk_client

            # Force re-initialization by resetting state
            client._initialized = False

            # Second initialization
            await client._ensure_initialized()

            # THEN: Old client should have been closed before replacement
            old_sdk_client.close.assert_called_once()
            assert client._client is new_sdk_client
