"""
Integration tests for SemanticIndexManager with real Qdrant.

These tests validate end-to-end semantic indexing and search functionality
using a real Qdrant instance (from docker-compose.test.yml).

Test Categories:
----------------
1. Connection: Verify Qdrant connectivity and collection management
2. Tool Indexing: Test tool indexing with embeddings
3. Skill Indexing: Test skill indexing with embeddings
4. Memory Indexing: Test memory indexing with embeddings
5. Search: Test semantic search with real vectors
6. Multi-Tenant: Test tenant isolation

Markers:
--------
- @pytest.mark.integration: Integration test category
- @pytest.mark.qdrant: Qdrant-specific tests
- @: ADR-0099 semantic tool selection tests

ADR Reference: adr/adr-0099-semantic-tool-selection.md
"""

from __future__ import annotations

import gc
import os
import socket
import time
import uuid

import pytest

from tests.conftest import get_user_id
from tests.constants import TEST_QDRANT_PORT

# Guard for optional qdrant_client dependency
pytest.importorskip("qdrant_client", reason="qdrant_client is an optional dependency for vector tests")

# Module-level marker
pytestmark = [
    pytest.mark.integration,
    pytest.mark.qdrant,
    pytest.mark.semantic_search,
    pytest.mark.xdist_group(name="semantic_index_manager_qdrant"),
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
def collection_name() -> str:
    """Get unique collection name for test isolation."""
    return f"{get_worker_prefix()}_semantic_index_{int(time.time() * 1000)}"


@pytest.fixture
async def cleanup_collection(qdrant_url: str, collection_name: str):
    """Fixture to cleanup test collection after tests."""
    yield

    # Cleanup after test
    if not qdrant_available():
        return

    try:
        from qdrant_client import AsyncQdrantClient

        client = AsyncQdrantClient(url=qdrant_url)
        try:
            collections = await client.get_collections()
            if any(c.name == collection_name for c in collections.collections):
                await client.delete_collection(collection_name)
        finally:
            await client.close()
    except Exception:
        pass  # Best-effort cleanup


class MockEmbeddingService:
    """Mock embedding service for integration tests.

    Produces deterministic vectors based on text content for reproducible tests.
    Uses 384 dimensions to match DEFAULT_VECTOR_SIZE in SemanticIndexManager.
    """

    def __init__(self, vector_size: int = 384) -> None:
        self.vector_size = vector_size
        self.call_count = 0

    def embed_query(self, text: str) -> list[float]:
        """Generate deterministic embedding from query text."""
        self.call_count += 1
        return self._generate_embedding(text)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Generate deterministic embeddings for multiple documents."""
        return [self._generate_embedding(text) for text in texts]

    def _generate_embedding(self, text: str) -> list[float]:
        """Generate a deterministic vector based on text hash."""
        # Create sparse vector with non-zero values for similarity
        hash_val = hash(text)
        vector = [0.0] * self.vector_size
        for i in range(min(10, len(text))):
            idx = (hash_val + i * 17) % self.vector_size
            vector[idx] = 0.1 * (i + 1)
        # Add common dimensions for similar texts based on words
        for word in text.lower().split():
            word_hash = hash(word)
            idx = word_hash % self.vector_size
            vector[idx] = max(vector[idx], 0.2)
        return vector


@pytest.fixture
def mock_embedder() -> MockEmbeddingService:
    """Create mock embedding service."""
    return MockEmbeddingService(vector_size=384)


@pytest.fixture(autouse=True)
def mock_openfga_authorization():
    """Mock OpenFGA authorization to allow all access for integration tests.

    Integration tests focus on Qdrant functionality, not authorization.
    Authorization is tested separately in test_semantic_index_authorization.py.
    """
    from unittest.mock import AsyncMock, patch

    mock_client = AsyncMock(spec=True)
    mock_client.check_permission = AsyncMock(return_value=True)

    with patch(
        "mcp_server_langgraph.core.semantic_index_manager.get_openfga_client",
        return_value=mock_client,
    ):
        yield mock_client


@pytest.mark.xdist_group("test_semantic_index_manager_connection")
@pytest.mark.skipif(not qdrant_available(), reason="Qdrant not available")
class TestSemanticIndexManagerConnection:
    """Tests for SemanticIndexManager Qdrant connectivity."""

    @pytest.mark.asyncio
    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        import gc

        gc.collect()

    async def test_manager_connects_to_qdrant(
        self, qdrant_url: str, collection_name: str, mock_embedder: MockEmbeddingService, cleanup_collection: None
    ) -> None:
        """Test SemanticIndexManager connects to real Qdrant."""
        from qdrant_client import AsyncQdrantClient

        from mcp_server_langgraph.core.semantic_index_manager import SemanticIndexManager

        client = AsyncQdrantClient(url=qdrant_url)
        try:
            manager = SemanticIndexManager(
                embedder=mock_embedder,
                qdrant_client=client,
                collection_name=collection_name,
                vector_size=384,
            )

            assert manager is not None
            assert manager.collection_name == collection_name
            assert manager.vector_size == 384
        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_ensure_collection_creates_collection(
        self, qdrant_url: str, collection_name: str, mock_embedder: MockEmbeddingService, cleanup_collection: None
    ) -> None:
        """Test ensure_collection creates collection if it doesn't exist."""
        from qdrant_client import AsyncQdrantClient

        from mcp_server_langgraph.core.semantic_index_manager import SemanticIndexManager

        client = AsyncQdrantClient(url=qdrant_url)
        try:
            manager = SemanticIndexManager(
                embedder=mock_embedder,
                qdrant_client=client,
                collection_name=collection_name,
                vector_size=384,
            )

            # Collection should not exist yet
            collections = await client.get_collections()
            assert collection_name not in {c.name for c in collections.collections}

            # Create collection
            await manager.ensure_collection()

            # Collection should now exist
            collections = await client.get_collections()
            assert collection_name in {c.name for c in collections.collections}
        finally:
            await client.close()


@pytest.mark.xdist_group("test_semantic_index_manager_tool_indexing")
@pytest.mark.skipif(not qdrant_available(), reason="Qdrant not available")
class TestSemanticIndexManagerToolIndexing:
    """Tests for SemanticIndexManager tool indexing with real Qdrant."""

    @pytest.mark.asyncio
    async def test_index_single_tool(
        self, qdrant_url: str, collection_name: str, mock_embedder: MockEmbeddingService, cleanup_collection: None
    ) -> None:
        """Test indexing a single tool into Qdrant."""
        from qdrant_client import AsyncQdrantClient

        from mcp_server_langgraph.core.semantic_index_manager import SemanticIndexManager
        from mcp_server_langgraph.tools.semantic_index import ToolCategory, ToolIndexEntry

        client = AsyncQdrantClient(url=qdrant_url)
        try:
            manager = SemanticIndexManager(
                embedder=mock_embedder,
                qdrant_client=client,
                collection_name=collection_name,
                vector_size=384,
            )

            await manager.ensure_collection()

            # Create and index tool
            tool_entry = ToolIndexEntry(
                tool_id=f"builtin:test-{uuid.uuid4().hex[:8]}",
                name="calculator",
                description="Perform mathematical calculations with precision",
                category=ToolCategory.CALCULATOR,
            )

            await manager.index_tool(tool_entry)

            # Verify embedding service was called
            assert mock_embedder.call_count == 1

            # Verify tool was stored in Qdrant
            count = await client.count(collection_name=collection_name)
            assert count.count == 1
        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_index_tools_batch(
        self, qdrant_url: str, collection_name: str, mock_embedder: MockEmbeddingService, cleanup_collection: None
    ) -> None:
        """Test batch indexing multiple tools."""
        from qdrant_client import AsyncQdrantClient

        from mcp_server_langgraph.core.semantic_index_manager import SemanticIndexManager
        from mcp_server_langgraph.tools.semantic_index import ToolCategory, ToolIndexEntry

        client = AsyncQdrantClient(url=qdrant_url)
        try:
            manager = SemanticIndexManager(
                embedder=mock_embedder,
                qdrant_client=client,
                collection_name=collection_name,
                vector_size=384,
            )

            await manager.ensure_collection()

            # Create multiple tools
            tools = [
                ToolIndexEntry(
                    tool_id=f"builtin:test-{uuid.uuid4().hex[:8]}",
                    name=f"tool_{i}",
                    description=f"Description for tool {i}",
                    category=ToolCategory.OTHER,
                )
                for i in range(5)
            ]

            await manager.index_tools_batch(tools)

            # Verify all tools were stored
            count = await client.count(collection_name=collection_name)
            assert count.count == 5
        finally:
            await client.close()

    def teardown_method(self):
        """Clean up after each test."""
        import gc

        gc.collect()


@pytest.mark.xdist_group("test_semantic_index_manager_tool_search")
@pytest.mark.skipif(not qdrant_available(), reason="Qdrant not available")
class TestSemanticIndexManagerToolSearch:
    """Tests for SemanticIndexManager tool search with real Qdrant."""

    @pytest.mark.asyncio
    async def test_search_tools_returns_relevant_results(
        self, qdrant_url: str, collection_name: str, mock_embedder: MockEmbeddingService, cleanup_collection: None
    ) -> None:
        """Test searching tools returns semantically relevant results."""
        from qdrant_client import AsyncQdrantClient

        from mcp_server_langgraph.core.semantic_index_manager import SemanticIndexManager
        from mcp_server_langgraph.tools.semantic_index import ToolCategory, ToolIndexEntry

        client = AsyncQdrantClient(url=qdrant_url)
        try:
            manager = SemanticIndexManager(
                embedder=mock_embedder,
                qdrant_client=client,
                collection_name=collection_name,
                vector_size=384,
            )

            await manager.ensure_collection()

            # Index diverse tools
            tools = [
                ToolIndexEntry(
                    tool_id=f"builtin:test-{uuid.uuid4().hex[:8]}",
                    name="calculator",
                    description="Perform mathematical calculations and arithmetic",
                    category=ToolCategory.CALCULATOR,
                ),
                ToolIndexEntry(
                    tool_id=f"builtin:test-{uuid.uuid4().hex[:8]}",
                    name="web_search",
                    description="Search the web for information",
                    category=ToolCategory.SEARCH,
                ),
                ToolIndexEntry(
                    tool_id=f"builtin:test-{uuid.uuid4().hex[:8]}",
                    name="file_reader",
                    description="Read and parse file contents",
                    category=ToolCategory.FILESYSTEM,
                ),
            ]

            await manager.index_tools_batch(tools)

            # Search for calculator-related query (user_id required for authorization)
            results = await manager.search_tools(
                query="calculate the sum of numbers",
                user_id=get_user_id("alice"),
                limit=3,
                min_score=0.0,  # Low threshold to get results with mock embedder
            )

            # Should return results
            assert len(results) > 0
            # All results should be ToolIndexEntry
            for result in results:
                assert hasattr(result, "tool_id")
                assert hasattr(result, "name")
        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_search_tools_with_category_filter(
        self, qdrant_url: str, collection_name: str, mock_embedder: MockEmbeddingService, cleanup_collection: None
    ) -> None:
        """Test searching tools with category filter."""
        from qdrant_client import AsyncQdrantClient

        from mcp_server_langgraph.core.semantic_index_manager import SemanticIndexManager
        from mcp_server_langgraph.tools.semantic_index import ToolCategory, ToolIndexEntry

        client = AsyncQdrantClient(url=qdrant_url)
        try:
            manager = SemanticIndexManager(
                embedder=mock_embedder,
                qdrant_client=client,
                collection_name=collection_name,
                vector_size=384,
            )

            await manager.ensure_collection()

            # Index tools with different categories
            tools = [
                ToolIndexEntry(
                    tool_id=f"builtin:test-{uuid.uuid4().hex[:8]}",
                    name="calculator_basic",
                    description="Basic arithmetic operations",
                    category=ToolCategory.CALCULATOR,
                ),
                ToolIndexEntry(
                    tool_id=f"builtin:test-{uuid.uuid4().hex[:8]}",
                    name="calculator_scientific",
                    description="Scientific calculations with functions",
                    category=ToolCategory.CALCULATOR,
                ),
                ToolIndexEntry(
                    tool_id=f"builtin:test-{uuid.uuid4().hex[:8]}",
                    name="web_browser",
                    description="Browse the web",
                    category=ToolCategory.WEB,
                ),
            ]

            await manager.index_tools_batch(tools)

            # Search with category filter (user_id required for authorization)
            # Query uses words from indexed content for mock embedder similarity
            results = await manager.search_tools(
                query="calculator basic arithmetic",
                user_id=get_user_id("alice"),
                category=ToolCategory.CALCULATOR,
                limit=10,
                min_score=0.0,
            )

            # All results should be calculator category
            assert len(results) >= 1
            for result in results:
                assert result.category == ToolCategory.CALCULATOR
        finally:
            await client.close()

    def teardown_method(self):
        """Clean up after each test."""
        import gc

        gc.collect()


@pytest.mark.xdist_group("test_semantic_index_manager_skill_indexing")
@pytest.mark.skipif(not qdrant_available(), reason="Qdrant not available")
class TestSemanticIndexManagerSkillIndexing:
    """Tests for SemanticIndexManager skill indexing with real Qdrant."""

    @pytest.mark.asyncio
    async def test_index_single_skill(
        self, qdrant_url: str, collection_name: str, mock_embedder: MockEmbeddingService, cleanup_collection: None
    ) -> None:
        """Test indexing a single skill into Qdrant."""
        from qdrant_client import AsyncQdrantClient

        from mcp_server_langgraph.core.semantic_index_manager import SemanticIndexManager
        from mcp_server_langgraph.tools.semantic_index import SkillCategory, SkillIndexEntry

        client = AsyncQdrantClient(url=qdrant_url)
        try:
            manager = SemanticIndexManager(
                embedder=mock_embedder,
                qdrant_client=client,
                collection_name=collection_name,
                vector_size=384,
            )

            await manager.ensure_collection()

            # Create and index skill (use UUID for Qdrant compatibility)
            skill_entry = SkillIndexEntry(
                skill_id=str(uuid.uuid4()),
                name="code-review",
                description="Review code for quality, bugs, and best practices",
                category=SkillCategory.DEVELOPMENT,
            )

            await manager.index_skill(skill_entry)

            # Verify skill was stored
            count = await client.count(collection_name=collection_name)
            assert count.count == 1
        finally:
            await client.close()

    def teardown_method(self):
        """Clean up after each test."""
        import gc

        gc.collect()


@pytest.mark.xdist_group("test_semantic_index_manager_skill_search")
@pytest.mark.skipif(not qdrant_available(), reason="Qdrant not available")
class TestSemanticIndexManagerSkillSearch:
    """Tests for SemanticIndexManager skill search with real Qdrant."""

    @pytest.mark.asyncio
    async def test_search_skills_returns_results(
        self, qdrant_url: str, collection_name: str, mock_embedder: MockEmbeddingService, cleanup_collection: None
    ) -> None:
        """Test searching skills returns results."""
        from qdrant_client import AsyncQdrantClient

        from mcp_server_langgraph.core.semantic_index_manager import SemanticIndexManager
        from mcp_server_langgraph.tools.semantic_index import SkillCategory, SkillIndexEntry

        client = AsyncQdrantClient(url=qdrant_url)
        try:
            manager = SemanticIndexManager(
                embedder=mock_embedder,
                qdrant_client=client,
                collection_name=collection_name,
                vector_size=384,
            )

            await manager.ensure_collection()

            # Index skills (use UUIDs for Qdrant compatibility)
            skills = [
                SkillIndexEntry(
                    skill_id=str(uuid.uuid4()),
                    name="code-review",
                    description="Review code for quality and bugs",
                    category=SkillCategory.DEVELOPMENT,
                ),
                SkillIndexEntry(
                    skill_id=str(uuid.uuid4()),
                    name="test-generator",
                    description="Generate unit tests for code",
                    category=SkillCategory.TESTING,
                ),
            ]

            for skill in skills:
                await manager.index_skill(skill)

            # Search for skills (user_id required for authorization)
            results = await manager.search_skills(
                query="review code quality",
                user_id=get_user_id("alice"),
                limit=5,
                min_score=0.0,
            )

            assert len(results) > 0
            for result in results:
                assert hasattr(result, "skill_id")
                assert hasattr(result, "name")
        finally:
            await client.close()

    def teardown_method(self):
        """Clean up after each test."""
        import gc

        gc.collect()


@pytest.mark.xdist_group("test_semantic_index_manager_memory_indexing")
@pytest.mark.skipif(not qdrant_available(), reason="Qdrant not available")
class TestSemanticIndexManagerMemoryIndexing:
    """Tests for SemanticIndexManager memory indexing with real Qdrant."""

    @pytest.mark.asyncio
    async def test_index_single_memory(
        self, qdrant_url: str, collection_name: str, mock_embedder: MockEmbeddingService, cleanup_collection: None
    ) -> None:
        """Test indexing a single memory into Qdrant."""
        from qdrant_client import AsyncQdrantClient

        from mcp_server_langgraph.core.semantic_index_manager import SemanticIndexManager
        from mcp_server_langgraph.tools.semantic_index import MemoryIndexEntry, MemoryType

        client = AsyncQdrantClient(url=qdrant_url)
        try:
            manager = SemanticIndexManager(
                embedder=mock_embedder,
                qdrant_client=client,
                collection_name=collection_name,
                vector_size=384,
            )

            await manager.ensure_collection()

            # Create and index memory (use UUID for Qdrant compatibility)
            memory_entry = MemoryIndexEntry(
                memory_id=str(uuid.uuid4()),
                content="User prefers dark mode for all interfaces",
                memory_type=MemoryType.PREFERENCE,
                user_id="user-123",
            )

            await manager.index_memory(memory_entry)

            # Verify memory was stored
            count = await client.count(collection_name=collection_name)
            assert count.count == 1
        finally:
            await client.close()

    def teardown_method(self):
        """Clean up after each test."""
        import gc

        gc.collect()


@pytest.mark.xdist_group("test_semantic_index_manager_memory_search")
@pytest.mark.skipif(not qdrant_available(), reason="Qdrant not available")
class TestSemanticIndexManagerMemorySearch:
    """Tests for SemanticIndexManager memory search with real Qdrant."""

    @pytest.mark.asyncio
    async def test_search_memories_returns_results(
        self, qdrant_url: str, collection_name: str, mock_embedder: MockEmbeddingService, cleanup_collection: None
    ) -> None:
        """Test searching memories returns results."""
        from qdrant_client import AsyncQdrantClient

        from mcp_server_langgraph.core.semantic_index_manager import SemanticIndexManager
        from mcp_server_langgraph.tools.semantic_index import MemoryIndexEntry, MemoryType

        client = AsyncQdrantClient(url=qdrant_url)
        try:
            manager = SemanticIndexManager(
                embedder=mock_embedder,
                qdrant_client=client,
                collection_name=collection_name,
                vector_size=384,
            )

            await manager.ensure_collection()

            # Index memories (use UUIDs for Qdrant compatibility)
            memories = [
                MemoryIndexEntry(
                    memory_id=str(uuid.uuid4()),
                    content="User prefers Python for development",
                    memory_type=MemoryType.PREFERENCE,
                    user_id="user-123",
                ),
                MemoryIndexEntry(
                    memory_id=str(uuid.uuid4()),
                    content="Previous discussion about API design",
                    memory_type=MemoryType.CONTEXT,
                    user_id="user-123",
                ),
            ]

            for memory in memories:
                await manager.index_memory(memory)

            # Search for memories (current_user_id and search_user_id required for authorization)
            results = await manager.search_memories(
                query="user preferences for programming",
                current_user_id="user-123",  # User making the request
                search_user_id="user-123",  # Searching own memories
                limit=5,
                min_score=0.0,
            )

            assert len(results) > 0
            for result in results:
                assert hasattr(result, "memory_id")
                assert hasattr(result, "content")
        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_search_memories_with_user_filter(
        self, qdrant_url: str, collection_name: str, mock_embedder: MockEmbeddingService, cleanup_collection: None
    ) -> None:
        """Test searching memories with user_id filter."""
        from qdrant_client import AsyncQdrantClient

        from mcp_server_langgraph.core.semantic_index_manager import SemanticIndexManager
        from mcp_server_langgraph.tools.semantic_index import MemoryIndexEntry, MemoryType

        client = AsyncQdrantClient(url=qdrant_url)
        try:
            manager = SemanticIndexManager(
                embedder=mock_embedder,
                qdrant_client=client,
                collection_name=collection_name,
                vector_size=384,
            )

            await manager.ensure_collection()

            # Index memories for different users (use UUIDs for Qdrant compatibility)
            memories = [
                MemoryIndexEntry(
                    memory_id=str(uuid.uuid4()),
                    content="User 1 prefers Python",
                    memory_type=MemoryType.PREFERENCE,
                    user_id="user-001",
                ),
                MemoryIndexEntry(
                    memory_id=str(uuid.uuid4()),
                    content="User 2 prefers JavaScript",
                    memory_type=MemoryType.PREFERENCE,
                    user_id="user-002",
                ),
            ]

            for memory in memories:
                await manager.index_memory(memory)

            # Search with user_id filter (current_user_id and search_user_id for authorization)
            # Query uses words from indexed content for mock embedder similarity
            results = await manager.search_memories(
                query="User 1 prefers Python language",
                current_user_id="user-001",  # User making the request
                search_user_id="user-001",  # Searching own memories
                limit=10,
                min_score=0.0,
            )

            # All results should be for user-001 (filtered by search_user_id)
            assert len(results) >= 1
            for result in results:
                assert result.user_id == "user-001"
        finally:
            await client.close()

    def teardown_method(self):
        """Clean up after each test."""
        import gc

        gc.collect()


@pytest.mark.xdist_group("test_semantic_index_manager_multi_tenant")
@pytest.mark.skipif(not qdrant_available(), reason="Qdrant not available")
class TestSemanticIndexManagerMultiTenant:
    """Tests for SemanticIndexManager multi-tenant isolation with real Qdrant."""

    @pytest.mark.asyncio
    async def test_tool_search_respects_tenant_isolation(
        self, qdrant_url: str, collection_name: str, mock_embedder: MockEmbeddingService, cleanup_collection: None
    ) -> None:
        """Test that tool search respects tenant_id isolation."""
        from qdrant_client import AsyncQdrantClient

        from mcp_server_langgraph.core.semantic_index_manager import SemanticIndexManager
        from mcp_server_langgraph.tools.semantic_index import ToolCategory, ToolIndexEntry

        client = AsyncQdrantClient(url=qdrant_url)
        try:
            manager = SemanticIndexManager(
                embedder=mock_embedder,
                qdrant_client=client,
                collection_name=collection_name,
                vector_size=384,
            )

            await manager.ensure_collection()

            # Index tools for different tenants
            tools = [
                ToolIndexEntry(
                    tool_id=f"builtin:test-{uuid.uuid4().hex[:8]}",
                    name="tenant1_calculator",
                    description="Calculator for tenant 1",
                    category=ToolCategory.CALCULATOR,
                    tenant_id="tenant-001",
                ),
                ToolIndexEntry(
                    tool_id=f"builtin:test-{uuid.uuid4().hex[:8]}",
                    name="tenant2_calculator",
                    description="Calculator for tenant 2",
                    category=ToolCategory.CALCULATOR,
                    tenant_id="tenant-002",
                ),
            ]

            await manager.index_tools_batch(tools)

            # Search with tenant filter (user_id required for authorization)
            results = await manager.search_tools(
                query="calculator",
                user_id=get_user_id("alice"),
                tenant_id="tenant-001",
                limit=10,
                min_score=0.0,
            )

            # All results should be for tenant-001
            assert len(results) >= 1
            for result in results:
                assert result.tenant_id == "tenant-001"
        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_memory_search_respects_tenant_isolation(
        self, qdrant_url: str, collection_name: str, mock_embedder: MockEmbeddingService, cleanup_collection: None
    ) -> None:
        """Test that memory search respects tenant_id isolation."""
        from qdrant_client import AsyncQdrantClient

        from mcp_server_langgraph.core.semantic_index_manager import SemanticIndexManager
        from mcp_server_langgraph.tools.semantic_index import MemoryIndexEntry, MemoryType

        client = AsyncQdrantClient(url=qdrant_url)
        try:
            manager = SemanticIndexManager(
                embedder=mock_embedder,
                qdrant_client=client,
                collection_name=collection_name,
                vector_size=384,
            )

            await manager.ensure_collection()

            # Index memories for different tenants (use UUIDs for Qdrant compatibility)
            # Note: user_id is required for search_memories filtering
            memories = [
                MemoryIndexEntry(
                    memory_id=str(uuid.uuid4()),
                    content="Tenant 1 context information",
                    memory_type=MemoryType.CONTEXT,
                    tenant_id="tenant-001",
                    user_id=get_user_id("alice"),  # Required for search filter
                ),
                MemoryIndexEntry(
                    memory_id=str(uuid.uuid4()),
                    content="Tenant 2 context information",
                    memory_type=MemoryType.CONTEXT,
                    tenant_id="tenant-002",
                    user_id=get_user_id("alice"),  # Same user, different tenant
                ),
            ]

            for memory in memories:
                await manager.index_memory(memory)

            # Search with tenant filter (current_user_id and search_user_id for authorization)
            results = await manager.search_memories(
                query="context information",
                current_user_id=get_user_id("alice"),  # User making the request
                search_user_id=get_user_id("alice"),  # User's memories (same for own search)
                tenant_id="tenant-001",
                limit=10,
                min_score=0.0,
            )

            # All results should be for tenant-001
            assert len(results) >= 1
            for result in results:
                assert result.tenant_id == "tenant-001"
        finally:
            await client.close()

    def teardown_method(self):
        """Clean up after each test."""
        import gc

        gc.collect()
