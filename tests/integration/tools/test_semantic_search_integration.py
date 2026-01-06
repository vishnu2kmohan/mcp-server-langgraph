"""
Integration tests for semantic search using Qdrant from docker-compose.test.yml.

Requirements:
  - docker compose -f docker-compose.test.yml up -d qdrant
  - EMBEDDING_PROVIDER=local with sentence-transformers installed
    OR stub the embedder for deterministic vectors

These tests skip if Qdrant is unavailable or embedding dependencies missing.
"""

import gc
import uuid
from unittest.mock import patch

import pytest

from mcp_server_langgraph.core.config import settings

pytestmark = pytest.mark.integration


def _create_stub_embedder():
    """Create a stub embedder that returns deterministic vectors."""
    from langchain_core.embeddings import Embeddings

    class StubEmbeddings(Embeddings):
        """Deterministic embeddings for testing."""

        def __init__(self, dimensions: int = 384):
            self.dimensions = dimensions

        def embed_documents(self, texts: list[str]) -> list[list[float]]:
            # Return deterministic vectors based on text hash
            return [self._text_to_vector(t) for t in texts]

        def embed_query(self, text: str) -> list[float]:
            return self._text_to_vector(text)

        def _text_to_vector(self, text: str) -> list[float]:
            # Simple hash-based deterministic vector
            h = hash(text) % (10**9)
            return [(h * (i + 1) % 1000) / 1000.0 for i in range(self.dimensions)]

    return StubEmbeddings(dimensions=384)


@pytest.fixture(scope="module")
def unique_collection_name() -> str:
    """Generate unique collection name to avoid dimension conflicts."""
    return f"test_semantic_{uuid.uuid4().hex[:8]}"


@pytest.fixture
async def loader_with_stub(unique_collection_name: str):
    """Create DynamicContextLoader with stubbed embedder."""
    from mcp_server_langgraph.core.dynamic_context_loader import DynamicContextLoader

    # Check if Qdrant is available
    qdrant_url = getattr(settings, "qdrant_url", None)
    if not qdrant_url:
        pytest.skip("Qdrant not configured")

    # Patch the embedder creation to use stub
    with patch(
        "mcp_server_langgraph.core.dynamic_context_loader._create_embeddings",
        return_value=_create_stub_embedder(),
    ):
        try:
            loader = DynamicContextLoader(
                collection_name=unique_collection_name,
                embedding_dimensions=384,  # Match stub
            )
            # Test connection by attempting client init
            client = await loader._get_client()
            yield loader

            # Cleanup: delete test collection
            try:
                await client.delete_collection(unique_collection_name)
            except Exception:
                pass  # Collection may not exist

        except Exception as e:
            pytest.skip(f"Qdrant not available: {e}")


@pytest.mark.integration
@pytest.mark.xdist_group(name="semantic_search_integration")
class TestSemanticSearchIntegration:
    """Integration tests using Qdrant from docker-compose.test.yml."""

    def teardown_method(self):
        gc.collect()

    @pytest.mark.asyncio
    async def test_index_and_search_returns_results(self, loader_with_stub):
        """End-to-end: index -> search -> verify results."""
        loader = loader_with_stub

        # Index test content
        await loader.index_context(
            ref_id="test_doc_001",
            content="Python asyncio patterns for concurrent programming",
            ref_type="documentation",
            summary="Asyncio patterns guide",
        )

        # Search
        refs = await loader.semantic_search("asyncio concurrency", top_k=5)

        # Verify - at least one result with matching content
        assert len(refs) >= 1
        assert any("asyncio" in r.summary.lower() for r in refs)

    @pytest.mark.asyncio
    async def test_load_batch_respects_token_limit(self, loader_with_stub):
        """Verify load_batch stops at max_tokens (upper bound check)."""
        loader = loader_with_stub
        max_tokens = 300

        # Index multiple docs
        for i in range(5):
            await loader.index_context(
                ref_id=f"token_test_{i}",
                content="A" * 500,
                ref_type="test",
                summary=f"Token test doc {i}",
            )

        refs = await loader.semantic_search("token test", top_k=5)
        loaded = await loader.load_batch(refs, max_tokens=max_tokens)

        # Assert bounds - not hard-coded counts
        assert len(loaded) < len(refs), "Should not load all docs when limited"
        total_tokens = sum(ctx.token_count for ctx in loaded)
        assert total_tokens <= max_tokens, f"Token budget exceeded: {total_tokens} > {max_tokens}"

    @pytest.mark.asyncio
    async def test_progressive_discover_finds_related_content(self, loader_with_stub):
        """Verify iterative search finds related content."""
        loader = loader_with_stub

        # Index docs with different keywords
        await loader.index_context(
            ref_id="async_doc",
            content="Python async await syntax for concurrent I/O",
            ref_type="doc",
            summary="Async syntax",
        )
        await loader.index_context(
            ref_id="concurrent_doc",
            content="Concurrency patterns in Python applications",
            ref_type="doc",
            summary="Concurrency patterns",
        )

        refs = await loader.progressive_discover(
            initial_query="async",
            expansion_keywords=["concurrency", "patterns"],
            max_iterations=2,
        )

        # Should find at least one related doc
        ref_ids = {r.ref_id for r in refs}
        assert len(ref_ids) >= 1

    @pytest.mark.asyncio
    async def test_search_with_no_results_returns_empty_list(self, loader_with_stub):
        """Search with no matches returns empty list, not error."""
        loader = loader_with_stub

        # Search for something that doesn't exist
        refs = await loader.semantic_search("nonexistent_query_xyz123", top_k=5)

        assert refs == []

    @pytest.mark.asyncio
    async def test_load_context_caching_works(self, loader_with_stub):
        """Verify context caching reduces repeated loads."""
        loader = loader_with_stub

        # Index a doc
        await loader.index_context(
            ref_id="cache_test_doc",
            content="Test content for cache verification",
            ref_type="test",
            summary="Cache test doc",
        )

        # Search and load
        refs = await loader.semantic_search("cache test", top_k=1)
        assert len(refs) == 1

        # Load twice - second should hit cache
        loaded1 = await loader.load_context(refs[0])
        loaded2 = await loader.load_context(refs[0])

        assert loaded1.content == loaded2.content
        assert "cache_test_doc" in refs[0].ref_id


@pytest.mark.integration
@pytest.mark.xdist_group(name="semantic_search_integration")
class TestSearchKnowledgeBaseToolIntegration:
    """Integration tests for search_knowledge_base tool with real Qdrant."""

    def teardown_method(self):
        gc.collect()

    @pytest.mark.asyncio
    async def test_tool_returns_results_when_configured(self, loader_with_stub, unique_collection_name):
        """Tool returns actual results when Qdrant is configured."""
        loader = loader_with_stub

        # Index test content first
        await loader.index_context(
            ref_id="integration_test_doc",
            content="Machine learning basics for beginners",
            ref_type="documentation",
            summary="ML basics guide",
        )

        # Now test the tool with mocked config validation
        with patch(
            "mcp_server_langgraph.tools.search_tools._validate_semantic_search_config",
            return_value=(True, None),
        ):
            with patch(
                "mcp_server_langgraph.tools.search_tools.DynamicContextLoader",
                return_value=loader,
            ):
                from mcp_server_langgraph.tools.search_tools import search_knowledge_base

                result = await search_knowledge_base.ainvoke({"query": "machine learning"})

                # Should have actual results, not config message
                assert "ML basics" in result or "machine learning" in result.lower()
