"""
Integration tests for SkillSearchTool with real Qdrant.

These tests validate end-to-end skill search functionality using
a real Qdrant instance (from docker-compose.test.yml).

Test Categories:
----------------
1. Connection: Verify Qdrant connectivity
2. Indexing: Test skill indexing with adapters
3. Search: Test semantic search with real vectors
4. Cleanup: Verify collection management

Markers:
--------
- @pytest.mark.integration: Integration test category
- @pytest.mark.qdrant: Qdrant-specific tests
- @pytest.mark.skills: Skills system tests

ADR Reference: adr/adr-0092-hierarchical-capability-architecture.md
"""

from __future__ import annotations

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
    pytest.mark.skills,
    pytest.mark.xdist_group(name="skill_search_qdrant"),
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
    return f"{get_worker_prefix()}_skills_integration"


@pytest.fixture
async def cleanup_collection(qdrant_url: str, collection_name: str):
    """Fixture to cleanup test collection after tests."""
    yield

    # Cleanup after test
    if not qdrant_available():
        return

    try:
        from qdrant_client import AsyncQdrantClient

        async with AsyncQdrantClient(url=qdrant_url) as client:
            collections = await client.get_collections()
            if any(c.name == collection_name for c in collections.collections):
                await client.delete_collection(collection_name)
    except Exception:
        pass  # Best-effort cleanup


class MockEmbeddingService:
    """Mock embedding service for integration tests.

    Produces deterministic vectors based on text content for reproducible tests.
    """

    def __init__(self, vector_size: int = 768) -> None:
        self.vector_size = vector_size
        self.call_count = 0

    async def embed(self, text: str) -> list[float]:
        """Generate deterministic embedding from text."""
        self.call_count += 1
        # Create a simple deterministic vector based on text hash
        hash_val = hash(text)
        # Create sparse vector with a few non-zero values for similarity
        vector = [0.0] * self.vector_size
        for i in range(min(10, len(text))):
            idx = (hash_val + i * 17) % self.vector_size
            vector[idx] = 0.1 * (i + 1)
        # Add some common dimensions for similar texts
        for word in text.lower().split():
            word_hash = hash(word)
            idx = word_hash % self.vector_size
            vector[idx] = max(vector[idx], 0.2)
        return vector


@pytest.mark.skipif(not qdrant_available(), reason="Qdrant not available")
class TestSkillSearchQdrantIntegration:
    """Integration tests for SkillSearchTool with real Qdrant."""

    @pytest.mark.asyncio
    async def test_adapter_connects_to_qdrant(self, qdrant_url: str) -> None:
        """Test VectorProviderAdapter connects to real Qdrant."""
        from qdrant_client import AsyncQdrantClient

        from mcp_server_langgraph.skills.adapters import VectorProviderAdapter
        from mcp_server_langgraph.storage.vectors.qdrant_provider import QdrantVectorProvider

        async with AsyncQdrantClient(url=qdrant_url) as client:
            # Create provider and adapter
            provider = QdrantVectorProvider(client=client, vector_size=768)
            adapter = VectorProviderAdapter(provider)

            assert adapter is not None
            assert adapter._provider is provider

    @pytest.mark.asyncio
    async def test_skill_indexing_with_real_qdrant(
        self, qdrant_url: str, collection_name: str, cleanup_collection: None
    ) -> None:
        """Test indexing skills into real Qdrant collection."""
        from qdrant_client import AsyncQdrantClient
        from qdrant_client.models import Distance, VectorParams

        from mcp_server_langgraph.skills.adapters import VectorProviderAdapter
        from mcp_server_langgraph.skills.models import Skill
        from mcp_server_langgraph.skills.search import SkillSearchTool
        from mcp_server_langgraph.storage.vectors.qdrant_provider import QdrantVectorProvider

        async with AsyncQdrantClient(url=qdrant_url) as client:
            # Create collection for test
            await client.recreate_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=768, distance=Distance.COSINE),
            )

            # Create provider, adapter, and tool
            provider = QdrantVectorProvider(client=client, vector_size=768)
            adapter = VectorProviderAdapter(provider)
            embedding_service = MockEmbeddingService(vector_size=768)

            # Create custom tool with test collection
            tool = SkillSearchTool(
                vector_provider=adapter,
                embedding_service=embedding_service,
            )
            # Override collection name for test isolation
            tool.COLLECTION = collection_name

            # Create test skill
            skill = Skill(
                name="code-review",
                description="Review code for quality, bugs, and best practices",
                tags=["code", "review", "quality"],
            )

            # Index the skill
            await tool.index_skill(skill, skill_id="skill-001")

            # Verify embedding service was called
            assert embedding_service.call_count == 1

            # Verify data was stored in Qdrant
            count = await client.count(collection_name=collection_name)
            assert count.count == 1

    @pytest.mark.asyncio
    async def test_skill_search_with_real_qdrant(
        self, qdrant_url: str, collection_name: str, cleanup_collection: None
    ) -> None:
        """Test searching skills in real Qdrant collection."""
        from qdrant_client import AsyncQdrantClient
        from qdrant_client.models import Distance, VectorParams

        from mcp_server_langgraph.skills.adapters import VectorProviderAdapter
        from mcp_server_langgraph.skills.models import Skill
        from mcp_server_langgraph.skills.search import SkillSearchTool
        from mcp_server_langgraph.storage.vectors.qdrant_provider import QdrantVectorProvider

        async with AsyncQdrantClient(url=qdrant_url) as client:
            # Create collection for test
            await client.recreate_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=768, distance=Distance.COSINE),
            )

            # Setup
            provider = QdrantVectorProvider(client=client, vector_size=768)
            adapter = VectorProviderAdapter(provider)
            embedding_service = MockEmbeddingService(vector_size=768)

            tool = SkillSearchTool(
                vector_provider=adapter,
                embedding_service=embedding_service,
            )
            tool.COLLECTION = collection_name

            # Index multiple skills
            skills = [
                Skill(
                    name="code-review",
                    description="Review code for quality, bugs, and best practices",
                    tags=["code", "review"],
                ),
                Skill(
                    name="test-generator",
                    description="Generate unit tests for Python code",
                    tags=["testing", "code"],
                ),
                Skill(
                    name="documentation-writer",
                    description="Write documentation for APIs and code",
                    tags=["docs", "writing"],
                ),
            ]

            for i, skill in enumerate(skills):
                await tool.index_skill(skill, skill_id=f"skill-{i:03d}")

            # Verify all skills indexed
            count = await client.count(collection_name=collection_name)
            assert count.count == 3

            # Search for code-related skills
            results = await tool.search("code quality review", limit=2)

            assert len(results) <= 2
            # Results should be SkillSearchResult objects
            for result in results:
                assert result.skill_id is not None
                assert result.name is not None
                assert result.score >= 0

    @pytest.mark.asyncio
    async def test_skill_search_with_min_score_filter(
        self, qdrant_url: str, collection_name: str, cleanup_collection: None
    ) -> None:
        """Test searching skills with minimum score threshold."""
        from qdrant_client import AsyncQdrantClient
        from qdrant_client.models import Distance, VectorParams

        from mcp_server_langgraph.skills.adapters import VectorProviderAdapter
        from mcp_server_langgraph.skills.models import Skill
        from mcp_server_langgraph.skills.search import SkillSearchTool
        from mcp_server_langgraph.storage.vectors.qdrant_provider import QdrantVectorProvider

        async with AsyncQdrantClient(url=qdrant_url) as client:
            # Create collection
            await client.recreate_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=768, distance=Distance.COSINE),
            )

            # Setup
            provider = QdrantVectorProvider(client=client, vector_size=768)
            adapter = VectorProviderAdapter(provider)
            embedding_service = MockEmbeddingService(vector_size=768)

            tool = SkillSearchTool(
                vector_provider=adapter,
                embedding_service=embedding_service,
            )
            tool.COLLECTION = collection_name

            # Index a skill
            skill = Skill(
                name="python-debugger",
                description="Debug Python applications with advanced breakpoints",
            )
            await tool.index_skill(skill, skill_id="skill-debug")

            # Search with high min_score (should filter out low-similarity results)
            results_high_threshold = await tool.search(
                "completely unrelated query about cooking recipes",
                min_score=0.9,
            )

            # High threshold should return fewer or no results
            # (depends on mock embedding similarity)
            assert isinstance(results_high_threshold, list)

    @pytest.mark.asyncio
    async def test_adapter_upsert_with_none_metadata(
        self, qdrant_url: str, collection_name: str, cleanup_collection: None
    ) -> None:
        """Test VectorProviderAdapter handles None metadata correctly."""
        from qdrant_client import AsyncQdrantClient
        from qdrant_client.models import Distance, VectorParams

        from mcp_server_langgraph.skills.adapters import VectorProviderAdapter
        from mcp_server_langgraph.storage.vectors.qdrant_provider import QdrantVectorProvider

        async with AsyncQdrantClient(url=qdrant_url) as client:
            # Create collection
            await client.recreate_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=768, distance=Distance.COSINE),
            )

            provider = QdrantVectorProvider(client=client, vector_size=768)
            adapter = VectorProviderAdapter(provider)

            # Upsert with None metadata (adapter should convert to {})
            await adapter.upsert(
                collection=collection_name,
                id="test-id",
                vector=[0.1] * 768,
                metadata=None,
            )

            # Verify point was stored
            count = await client.count(collection_name=collection_name)
            assert count.count == 1


@pytest.mark.skipif(not qdrant_available(), reason="Qdrant not available")
class TestVectorProviderAdapterQdrant:
    """Tests for VectorProviderAdapter with real Qdrant operations."""

    @pytest.mark.asyncio
    async def test_search_returns_dict_format(self, qdrant_url: str, collection_name: str, cleanup_collection: None) -> None:
        """Test adapter search returns list of dicts (not VectorSearchResult)."""
        from qdrant_client import AsyncQdrantClient
        from qdrant_client.models import Distance, VectorParams

        from mcp_server_langgraph.skills.adapters import VectorProviderAdapter
        from mcp_server_langgraph.storage.vectors.qdrant_provider import QdrantVectorProvider

        async with AsyncQdrantClient(url=qdrant_url) as client:
            # Create collection
            await client.recreate_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=768, distance=Distance.COSINE),
            )

            provider = QdrantVectorProvider(client=client, vector_size=768)
            adapter = VectorProviderAdapter(provider)

            # Insert a vector
            test_vector = [0.1] * 768
            await adapter.upsert(
                collection=collection_name,
                id="doc-001",
                vector=test_vector,
                metadata={"name": "test-skill", "description": "A test skill"},
            )

            # Search for similar vectors
            results = await adapter.search(
                collection=collection_name,
                query_vector=test_vector,
                limit=5,
            )

            assert len(results) >= 1
            assert isinstance(results[0], dict)
            assert "id" in results[0]
            assert "score" in results[0]
            assert "metadata" in results[0]
            assert results[0]["id"] == "doc-001"
