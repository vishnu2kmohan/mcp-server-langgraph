"""
Integration tests for Qdrant collection bootstrap functionality.

These tests validate that Qdrant collections are properly bootstrapped
during application startup, supporting both default and tenant-aware collections.

Tests require Qdrant to be running (from docker-compose.test.yml).

TDD Rationale:
--------------
E2E test failures for VectorsPage revealed that Qdrant collections weren't
being bootstrapped before tests ran. Integration tests should catch infrastructure
issues before they surface in E2E tests.

Test Categories:
----------------
1. Validation: Service connectivity checks
2. Bootstrap: Default collection creation
3. Tenant Bootstrap: Organization-scoped collections
4. Idempotency: Safe to call multiple times

Markers:
--------
- @pytest.mark.integration: Integration test category
- @pytest.mark.qdrant: Qdrant-specific tests
- @pytest.mark.vectors: Vector database tests

References:
-----------
- src/mcp_server_langgraph/core/startup_validation.py
- src/mcp_server_langgraph/api/v1/vectors.py
"""

import gc
import os
import socket

import pytest

from tests.constants import TEST_QDRANT_PORT

# Guard for optional qdrant_client dependency
pytest.importorskip("qdrant_client", reason="qdrant_client is an optional dependency for vector tests")

# Module-level marker
pytestmark = [
    pytest.mark.integration,
    pytest.mark.qdrant,
    pytest.mark.vectors,
    pytest.mark.xdist_group(name="qdrant_bootstrap"),
]


def get_worker_prefix() -> str:
    """Get worker-specific prefix for test isolation in parallel execution."""
    worker_id = os.getenv("PYTEST_XDIST_WORKER", "main")
    return f"test_{worker_id}"


def teardown_module() -> None:
    """Force GC to prevent mock accumulation in xdist workers."""
    gc.collect()


def is_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    """Check if a port is in use (service is accessible)."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(1)
        try:
            sock.connect((host, port))
            return True
        except (TimeoutError, ConnectionRefusedError, OSError):
            return False


def qdrant_available() -> bool:
    """Check if Qdrant is available for testing."""
    return is_port_in_use(TEST_QDRANT_PORT)


@pytest.fixture(autouse=True)
def teardown_gc():
    """Force GC after each test to prevent memory accumulation."""
    yield
    gc.collect()


@pytest.fixture
def qdrant_url() -> str:
    """Get Qdrant URL for testing."""
    return f"http://localhost:{TEST_QDRANT_PORT}"


@pytest.fixture
def cleanup_collections(qdrant_url: str):
    """Fixture to cleanup test collections after tests."""
    created_collections: list[str] = []
    yield created_collections

    # Cleanup after test
    if qdrant_available():
        try:
            from qdrant_client import QdrantClient

            client = QdrantClient(url=qdrant_url, timeout=5)
            for collection_name in created_collections:
                try:
                    if client.collection_exists(collection_name):
                        client.delete_collection(collection_name)
                except Exception:
                    pass  # Ignore cleanup errors
        except Exception:
            pass


# ==============================================================================
# Qdrant Connection Validation Tests
# ==============================================================================


@pytest.mark.xdist_group("test_qdrant_validation")
class TestQdrantValidation:
    """
    Integration tests for Qdrant connectivity validation.

    Tests the validate_qdrant_connection() function.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    @pytest.mark.skipif(not qdrant_available(), reason="Qdrant not available")
    async def test_validate_qdrant_connection_success(self, qdrant_url: str) -> None:
        """
        GIVEN Qdrant is running
        WHEN validate_qdrant_connection() is called
        THEN it returns success=True.
        """
        from mcp_server_langgraph.core.startup_validation import (
            validate_qdrant_connection,
        )

        result = await validate_qdrant_connection(url=qdrant_url)

        assert result.success is True
        assert result.service == "qdrant"
        assert result.error is None
        assert "Connected successfully" in (result.message or "")

    @pytest.mark.asyncio
    async def test_validate_qdrant_connection_failure(self) -> None:
        """
        GIVEN Qdrant is not reachable at the specified URL
        WHEN validate_qdrant_connection() is called
        THEN it returns success=False with error message.
        """
        from mcp_server_langgraph.core.startup_validation import (
            validate_qdrant_connection,
        )

        result = await validate_qdrant_connection(
            url="http://localhost:65535",
            timeout=1,
        )

        assert result.success is False
        assert result.service == "qdrant"
        assert result.error is not None

    @pytest.mark.asyncio
    @pytest.mark.skipif(not qdrant_available(), reason="Qdrant not available")
    async def test_validate_qdrant_returns_collection_count(self, qdrant_url: str) -> None:
        """
        GIVEN Qdrant is running with collections
        WHEN validate_qdrant_connection() is called
        THEN the message includes collection count.
        """
        from mcp_server_langgraph.core.startup_validation import (
            validate_qdrant_connection,
        )

        result = await validate_qdrant_connection(url=qdrant_url)

        assert result.success is True
        assert "collection(s)" in (result.message or "")


# ==============================================================================
# Qdrant Collection Bootstrap Tests
# ==============================================================================


@pytest.mark.xdist_group("test_qdrant_bootstrap")
class TestQdrantBootstrap:
    """
    Integration tests for Qdrant collection bootstrap.

    Tests the bootstrap_qdrant_collection() function.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    @pytest.mark.skipif(not qdrant_available(), reason="Qdrant not available")
    async def test_bootstrap_creates_new_collection(self, qdrant_url: str, cleanup_collections: list[str]) -> None:
        """
        GIVEN Qdrant is running and collection doesn't exist
        WHEN bootstrap_qdrant_collection() is called
        THEN collection is created with specified configuration.
        """
        from mcp_server_langgraph.core.startup_validation import (
            bootstrap_qdrant_collection,
        )

        prefix = get_worker_prefix()
        collection_name = f"{prefix}_bootstrap_test_new"
        cleanup_collections.append(collection_name)

        result = await bootstrap_qdrant_collection(
            url=qdrant_url,
            collection_name=collection_name,
            vector_size=384,
            distance="Cosine",
        )

        assert result.success is True
        assert result.created is True
        assert result.collection_name == collection_name
        assert result.error is None

    @pytest.mark.asyncio
    @pytest.mark.skipif(not qdrant_available(), reason="Qdrant not available")
    async def test_bootstrap_is_idempotent(self, qdrant_url: str, cleanup_collections: list[str]) -> None:
        """
        GIVEN collection already exists
        WHEN bootstrap_qdrant_collection() is called again
        THEN it succeeds without creating duplicate (idempotent).
        """
        from mcp_server_langgraph.core.startup_validation import (
            bootstrap_qdrant_collection,
        )

        prefix = get_worker_prefix()
        collection_name = f"{prefix}_bootstrap_test_idempotent"
        cleanup_collections.append(collection_name)

        # First call - should create
        result1 = await bootstrap_qdrant_collection(
            url=qdrant_url,
            collection_name=collection_name,
            vector_size=384,
        )

        assert result1.success is True
        assert result1.created is True

        # Second call - should skip creation (idempotent)
        result2 = await bootstrap_qdrant_collection(
            url=qdrant_url,
            collection_name=collection_name,
            vector_size=384,
        )

        assert result2.success is True
        assert result2.created is False  # Not created again

    @pytest.mark.asyncio
    @pytest.mark.skipif(not qdrant_available(), reason="Qdrant not available")
    async def test_bootstrap_with_different_distances(self, qdrant_url: str, cleanup_collections: list[str]) -> None:
        """
        GIVEN Qdrant is running
        WHEN bootstrap_qdrant_collection() is called with different distance metrics
        THEN each collection is created correctly.
        """
        from mcp_server_langgraph.core.startup_validation import (
            bootstrap_qdrant_collection,
        )

        prefix = get_worker_prefix()

        distances = ["Cosine", "Euclidean", "Dot"]

        for distance in distances:
            collection_name = f"{prefix}_bootstrap_test_{distance.lower()}"
            cleanup_collections.append(collection_name)

            result = await bootstrap_qdrant_collection(
                url=qdrant_url,
                collection_name=collection_name,
                vector_size=256,
                distance=distance,
            )

            assert result.success is True, f"Failed for distance={distance}"
            assert result.created is True

    @pytest.mark.asyncio
    async def test_bootstrap_with_unreachable_qdrant(self) -> None:
        """
        GIVEN Qdrant is not reachable
        WHEN bootstrap_qdrant_collection() is called
        THEN it returns error without raising exception.
        """
        from mcp_server_langgraph.core.startup_validation import (
            bootstrap_qdrant_collection,
        )

        result = await bootstrap_qdrant_collection(
            url="http://localhost:65535",
            collection_name="test_unreachable",
            vector_size=384,
            timeout=1,
        )

        assert result.success is False
        assert result.created is False
        assert result.error is not None


# ==============================================================================
# Tenant-Aware Collection Bootstrap Tests
# ==============================================================================


@pytest.mark.xdist_group("test_tenant_aware_bootstrap")
class TestTenantAwareBootstrap:
    """
    Integration tests for tenant-aware collection naming.

    Tests the pattern of organization-scoped collections.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    @pytest.mark.skipif(not qdrant_available(), reason="Qdrant not available")
    async def test_bootstrap_organization_collection(self, qdrant_url: str, cleanup_collections: list[str]) -> None:
        """
        GIVEN an organization ID
        WHEN bootstrap_qdrant_collection() is called with org-prefixed name
        THEN organization-scoped collection is created.
        """
        from mcp_server_langgraph.core.startup_validation import (
            bootstrap_qdrant_collection,
        )

        prefix = get_worker_prefix()
        org_id = f"{prefix}_org_123"
        collection_name = f"org_{org_id}_vectors"
        cleanup_collections.append(collection_name)

        result = await bootstrap_qdrant_collection(
            url=qdrant_url,
            collection_name=collection_name,
            vector_size=384,
        )

        assert result.success is True
        assert result.created is True
        assert result.collection_name == collection_name

    @pytest.mark.asyncio
    @pytest.mark.skipif(not qdrant_available(), reason="Qdrant not available")
    async def test_bootstrap_project_collection(self, qdrant_url: str, cleanup_collections: list[str]) -> None:
        """
        GIVEN a project ID
        WHEN bootstrap_qdrant_collection() is called with project-prefixed name
        THEN project-scoped collection is created.
        """
        from mcp_server_langgraph.core.startup_validation import (
            bootstrap_qdrant_collection,
        )

        prefix = get_worker_prefix()
        project_id = f"{prefix}_proj_456"
        collection_name = f"project_{project_id}_vectors"
        cleanup_collections.append(collection_name)

        result = await bootstrap_qdrant_collection(
            url=qdrant_url,
            collection_name=collection_name,
            vector_size=384,
        )

        assert result.success is True
        assert result.created is True

    @pytest.mark.asyncio
    @pytest.mark.skipif(not qdrant_available(), reason="Qdrant not available")
    async def test_multiple_tenant_collections_isolated(self, qdrant_url: str, cleanup_collections: list[str]) -> None:
        """
        GIVEN multiple organizations
        WHEN each org bootstraps its collection
        THEN collections are isolated.
        """
        from qdrant_client import QdrantClient

        from mcp_server_langgraph.core.startup_validation import (
            bootstrap_qdrant_collection,
        )

        prefix = get_worker_prefix()
        org_ids = [f"{prefix}_org_A", f"{prefix}_org_B", f"{prefix}_org_C"]
        collection_names = [f"org_{org_id}_vectors" for org_id in org_ids]

        for collection_name in collection_names:
            cleanup_collections.append(collection_name)
            result = await bootstrap_qdrant_collection(
                url=qdrant_url,
                collection_name=collection_name,
                vector_size=384,
            )
            assert result.success is True

        # Verify all collections exist independently
        client = QdrantClient(url=qdrant_url, timeout=5)
        for collection_name in collection_names:
            assert client.collection_exists(collection_name) is True


# ==============================================================================
# Collection Configuration Tests
# ==============================================================================


@pytest.mark.xdist_group("test_qdrant_collection_configuration")
class TestQdrantCollectionConfiguration:
    """
    Tests for verifying collection configuration after bootstrap.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    @pytest.mark.skipif(not qdrant_available(), reason="Qdrant not available")
    async def test_bootstrap_creates_correct_vector_config(self, qdrant_url: str, cleanup_collections: list[str]) -> None:
        """
        GIVEN specific vector configuration
        WHEN bootstrap_qdrant_collection() is called
        THEN collection has correct vector configuration.
        """
        from qdrant_client import QdrantClient

        from mcp_server_langgraph.core.startup_validation import (
            bootstrap_qdrant_collection,
        )

        prefix = get_worker_prefix()
        collection_name = f"{prefix}_config_test"
        cleanup_collections.append(collection_name)

        vector_size = 512

        result = await bootstrap_qdrant_collection(
            url=qdrant_url,
            collection_name=collection_name,
            vector_size=vector_size,
            distance="Euclidean",
        )

        assert result.success is True

        # Verify configuration via Qdrant client
        client = QdrantClient(url=qdrant_url, timeout=5)
        collection_info = client.get_collection(collection_name)

        # Check vector size matches
        vectors_config = collection_info.config.params.vectors
        # Handle both single vector config and named vectors config
        if hasattr(vectors_config, "size"):
            assert vectors_config.size == vector_size
        else:
            # Default vector config
            default_config = vectors_config.get("")  # type: ignore[union-attr]
            if default_config:
                assert default_config.size == vector_size


# ==============================================================================
# Default Collection Bootstrap Tests
# ==============================================================================


@pytest.mark.xdist_group("test_default_collection_bootstrap")
class TestDefaultCollectionBootstrap:
    """
    Tests for default collection bootstrap behavior.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    @pytest.mark.skipif(not qdrant_available(), reason="Qdrant not available")
    async def test_default_collection_name(self, qdrant_url: str) -> None:
        """
        GIVEN default bootstrap parameters
        WHEN bootstrap_qdrant_collection() is called with defaults
        THEN 'agent_studio_context' collection is created.
        """
        from mcp_server_langgraph.core.startup_validation import (
            bootstrap_qdrant_collection,
        )

        # Note: Using default collection name from the function signature
        result = await bootstrap_qdrant_collection(url=qdrant_url)

        assert result.success is True
        assert result.collection_name == "agent_studio_context"

    @pytest.mark.asyncio
    @pytest.mark.skipif(not qdrant_available(), reason="Qdrant not available")
    async def test_default_vector_size(self, qdrant_url: str, cleanup_collections: list[str]) -> None:
        """
        GIVEN no explicit vector size
        WHEN bootstrap_qdrant_collection() is called
        THEN default vector size (384 for MiniLM) is used.
        """
        from qdrant_client import QdrantClient

        from mcp_server_langgraph.core.startup_validation import (
            bootstrap_qdrant_collection,
        )

        prefix = get_worker_prefix()
        collection_name = f"{prefix}_default_size_test"
        cleanup_collections.append(collection_name)

        result = await bootstrap_qdrant_collection(
            url=qdrant_url,
            collection_name=collection_name,
            # vector_size defaults to 384
        )

        assert result.success is True

        # Verify default size
        client = QdrantClient(url=qdrant_url, timeout=5)
        collection_info = client.get_collection(collection_name)
        vectors_config = collection_info.config.params.vectors

        if hasattr(vectors_config, "size"):
            assert vectors_config.size == 384  # Default MiniLM size
