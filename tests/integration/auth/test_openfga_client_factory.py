"""
Unit tests for OpenFGA global client getter.

TDD: Tests for get_openfga_client() and set_global_openfga_client().

Note: These tests use mocks and should be moved to tests/unit/auth/ in a future refactor.
Real integration tests for OpenFGA are in tests/integration/test_openfga_real_infrastructure.py.
"""

from __future__ import annotations

import asyncio
import gc

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.auth,
    pytest.mark.openfga,
]


@pytest.mark.xdist_group(name="openfga_factory_unit")
class TestGetOpenFGAClient:
    """Tests for get_openfga_client() global getter."""

    def teardown_method(self) -> None:
        """Reset global state and force GC."""
        from mcp_server_langgraph.auth.openfga import clear_global_openfga_client

        clear_global_openfga_client()
        gc.collect()

    @pytest.mark.asyncio
    async def test_returns_none_when_global_not_set(self) -> None:
        """
        GIVEN: No global OpenFGA client has been set
        WHEN: get_openfga_client() is called
        THEN: Returns None
        """
        from mcp_server_langgraph.auth.openfga import (
            clear_global_openfga_client,
            get_openfga_client,
        )

        # GIVEN: Global is cleared
        clear_global_openfga_client()

        # WHEN: Get client
        result = await get_openfga_client()

        # THEN: Returns None
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_client_when_global_set(self) -> None:
        """
        GIVEN: A global OpenFGA client has been set
        WHEN: get_openfga_client() is called
        THEN: Returns the same client instance
        """
        from mcp_server_langgraph.auth.openfga import (
            OpenFGAClient,
            OpenFGAConfig,
            get_openfga_client,
            set_global_openfga_client,
        )

        # GIVEN: Create and set a client
        config = OpenFGAConfig(
            api_url="http://localhost:9080",
            store_id="test-store",
            model_id="test-model",
        )
        client = OpenFGAClient(config)
        set_global_openfga_client(client)

        # WHEN: Get client
        result = await get_openfga_client()

        # THEN: Returns the same instance
        assert result is client
        assert result.store_id == "test-store"
        assert result.model_id == "test-model"

    @pytest.mark.asyncio
    async def test_returns_same_instance_across_calls(self) -> None:
        """
        GIVEN: A global OpenFGA client has been set
        WHEN: get_openfga_client() is called multiple times
        THEN: The same client instance is returned (singleton behavior)
        """
        from mcp_server_langgraph.auth.openfga import (
            OpenFGAClient,
            OpenFGAConfig,
            get_openfga_client,
            set_global_openfga_client,
        )

        # GIVEN: Create and set a client
        config = OpenFGAConfig(
            api_url="http://localhost:9080",
            store_id="test-store",
            model_id="test-model",
        )
        client = OpenFGAClient(config)
        set_global_openfga_client(client)

        # WHEN: Call multiple times
        result1 = await get_openfga_client()
        result2 = await get_openfga_client()
        result3 = await get_openfga_client()

        # THEN: All should be the same instance
        assert result1 is result2 is result3 is client

    @pytest.mark.asyncio
    async def test_clear_global_removes_client(self) -> None:
        """
        GIVEN: A global OpenFGA client has been set
        WHEN: clear_global_openfga_client() is called
        THEN: get_openfga_client() returns None
        """
        from mcp_server_langgraph.auth.openfga import (
            OpenFGAClient,
            OpenFGAConfig,
            clear_global_openfga_client,
            get_openfga_client,
            set_global_openfga_client,
        )

        # GIVEN: Create and set a client
        config = OpenFGAConfig(
            api_url="http://localhost:9080",
            store_id="test-store",
            model_id="test-model",
        )
        client = OpenFGAClient(config)
        set_global_openfga_client(client)

        # Verify it's set
        assert await get_openfga_client() is client

        # WHEN: Clear global client
        clear_global_openfga_client()

        # THEN: Returns None
        result = await get_openfga_client()
        assert result is None


@pytest.mark.xdist_group(name="openfga_factory_unit")
class TestOpenFGAClientConcurrency:
    """Tests for concurrent access to the OpenFGA global client."""

    def teardown_method(self) -> None:
        """Reset global state and force GC."""
        from mcp_server_langgraph.auth.openfga import clear_global_openfga_client

        clear_global_openfga_client()
        gc.collect()

    @pytest.mark.asyncio
    async def test_concurrent_calls_return_same_instance(self) -> None:
        """
        GIVEN: A global OpenFGA client has been set
        WHEN: Multiple concurrent calls to get_openfga_client() are made
        THEN: All calls return the same client instance (thread-safe)
        """
        from mcp_server_langgraph.auth.openfga import (
            OpenFGAClient,
            OpenFGAConfig,
            get_openfga_client,
            set_global_openfga_client,
        )

        # GIVEN: Create and set a client
        config = OpenFGAConfig(
            api_url="http://localhost:9080",
            store_id="test-store",
            model_id="test-model",
        )
        client = OpenFGAClient(config)
        set_global_openfga_client(client)

        # WHEN: Run 10 concurrent calls
        tasks = [get_openfga_client() for _ in range(10)]
        results = await asyncio.gather(*tasks)

        # THEN: All results should be the same instance
        for result in results:
            assert result is client
