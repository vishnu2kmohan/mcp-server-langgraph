"""
Tests for EmbeddingService abstraction

TDD: These tests define the contract for embedding providers.
Supports multiple backends (LiteLLM, sentence-transformers, direct API).
"""

from __future__ import annotations

import gc
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.unit

if TYPE_CHECKING:
    pass


@pytest.mark.xdist_group(name="embedding_service_base")
class TestEmbeddingServiceBase:
    """Tests for EmbeddingService abstract base class."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_embedding_service_abc_exists(self) -> None:
        """Test that EmbeddingService ABC exists."""
        from mcp_server_langgraph.llm.embeddings import EmbeddingService

        assert EmbeddingService is not None

    def test_embedding_service_has_embed_method(self) -> None:
        """Test EmbeddingService has embed method."""
        from mcp_server_langgraph.llm.embeddings import EmbeddingService

        assert hasattr(EmbeddingService, "embed")

    def test_embedding_service_has_embed_batch_method(self) -> None:
        """Test EmbeddingService has embed_batch method."""
        from mcp_server_langgraph.llm.embeddings import EmbeddingService

        assert hasattr(EmbeddingService, "embed_batch")


@pytest.mark.xdist_group(name="embedding_service_litellm")
class TestLiteLLMEmbeddingService:
    """Tests for LiteLLM-based embedding service (multi-provider)."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_litellm_service_exists(self) -> None:
        """Test that LiteLLMEmbeddingService exists."""
        from mcp_server_langgraph.llm.embeddings import LiteLLMEmbeddingService

        assert LiteLLMEmbeddingService is not None

    def test_litellm_service_implements_interface(self) -> None:
        """Test LiteLLMEmbeddingService implements EmbeddingService."""
        from mcp_server_langgraph.llm.embeddings import (
            EmbeddingService,
            LiteLLMEmbeddingService,
        )

        service = LiteLLMEmbeddingService(model="text-embedding-3-small")
        assert isinstance(service, EmbeddingService)

    def test_litellm_service_has_model_attribute(self) -> None:
        """Test LiteLLMEmbeddingService stores model name."""
        from mcp_server_langgraph.llm.embeddings import LiteLLMEmbeddingService

        service = LiteLLMEmbeddingService(model="text-embedding-3-small")
        assert service.model == "text-embedding-3-small"

    @pytest.mark.asyncio
    async def test_embed_calls_litellm(self) -> None:
        """Test embed calls litellm.aembedding."""
        from mcp_server_langgraph.llm.embeddings import LiteLLMEmbeddingService

        with patch("litellm.aembedding") as mock_aembedding:
            mock_response = MagicMock()
            mock_response.data = [MagicMock(embedding=[0.1, 0.2, 0.3])]
            mock_aembedding.return_value = mock_response

            service = LiteLLMEmbeddingService(model="text-embedding-3-small")
            result = await service.embed("test text")

            assert mock_aembedding.called
            assert result == [0.1, 0.2, 0.3]

    @pytest.mark.asyncio
    async def test_embed_batch_processes_multiple_texts(self) -> None:
        """Test embed_batch processes multiple texts."""
        from mcp_server_langgraph.llm.embeddings import LiteLLMEmbeddingService

        with patch("litellm.aembedding") as mock_aembedding:
            mock_response = MagicMock()
            mock_response.data = [
                MagicMock(embedding=[0.1, 0.2, 0.3]),
                MagicMock(embedding=[0.4, 0.5, 0.6]),
            ]
            mock_aembedding.return_value = mock_response

            service = LiteLLMEmbeddingService(model="text-embedding-3-small")
            results = await service.embed_batch(["text1", "text2"])

            assert len(results) == 2
            assert results[0] == [0.1, 0.2, 0.3]
            assert results[1] == [0.4, 0.5, 0.6]


@pytest.mark.xdist_group(name="embedding_service_inmemory")
class TestInMemoryEmbeddingService:
    """Tests for InMemoryEmbeddingService (testing implementation)."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_inmemory_service_exists(self) -> None:
        """Test that InMemoryEmbeddingService exists."""
        from mcp_server_langgraph.llm.embeddings import InMemoryEmbeddingService

        assert InMemoryEmbeddingService is not None

    def test_inmemory_service_implements_interface(self) -> None:
        """Test InMemoryEmbeddingService implements EmbeddingService."""
        from mcp_server_langgraph.llm.embeddings import (
            EmbeddingService,
            InMemoryEmbeddingService,
        )

        service = InMemoryEmbeddingService(dimensions=768)
        assert isinstance(service, EmbeddingService)

    @pytest.mark.asyncio
    async def test_embed_returns_vector_of_correct_size(self) -> None:
        """Test embed returns a vector of specified dimensions."""
        from mcp_server_langgraph.llm.embeddings import InMemoryEmbeddingService

        service = InMemoryEmbeddingService(dimensions=768)
        result = await service.embed("test text")

        assert len(result) == 768
        # Should be floats
        assert all(isinstance(v, float) for v in result)

    @pytest.mark.asyncio
    async def test_embed_is_deterministic_for_same_input(self) -> None:
        """Test embed returns same result for same input."""
        from mcp_server_langgraph.llm.embeddings import InMemoryEmbeddingService

        service = InMemoryEmbeddingService(dimensions=768)
        result1 = await service.embed("test text")
        result2 = await service.embed("test text")

        assert result1 == result2

    @pytest.mark.asyncio
    async def test_embed_returns_different_vectors_for_different_inputs(self) -> None:
        """Test embed returns different results for different inputs."""
        from mcp_server_langgraph.llm.embeddings import InMemoryEmbeddingService

        service = InMemoryEmbeddingService(dimensions=768)
        result1 = await service.embed("hello world")
        result2 = await service.embed("goodbye world")

        assert result1 != result2

    @pytest.mark.asyncio
    async def test_embed_batch_returns_list_of_vectors(self) -> None:
        """Test embed_batch returns list of vectors."""
        from mcp_server_langgraph.llm.embeddings import InMemoryEmbeddingService

        service = InMemoryEmbeddingService(dimensions=768)
        results = await service.embed_batch(["text1", "text2", "text3"])

        assert len(results) == 3
        assert all(len(v) == 768 for v in results)


@pytest.mark.xdist_group(name="embedding_service_factory")
class TestEmbeddingServiceFactory:
    """Tests for get_embedding_service factory function."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_factory_function_exists(self) -> None:
        """Test that get_embedding_service factory exists."""
        from mcp_server_langgraph.llm.embeddings import get_embedding_service

        assert callable(get_embedding_service)

    def test_factory_returns_embedding_service(self) -> None:
        """Test factory returns an EmbeddingService instance."""
        from mcp_server_langgraph.llm.embeddings import (
            EmbeddingService,
            get_embedding_service,
        )

        service = get_embedding_service()
        assert isinstance(service, EmbeddingService)

    def test_factory_returns_inmemory_for_testing(self) -> None:
        """Test factory returns InMemory when no provider available."""
        from mcp_server_langgraph.llm.embeddings import (
            InMemoryEmbeddingService,
            get_embedding_service,
        )

        # Without any API keys, should fallback to InMemory
        with patch.dict("os.environ", {}, clear=False):
            with patch(
                "mcp_server_langgraph.llm.embeddings._has_litellm_embedding_config",
                return_value=False,
            ):
                service = get_embedding_service()
                assert isinstance(service, InMemoryEmbeddingService)

    def test_factory_returns_litellm_when_configured(self) -> None:
        """Test factory returns LiteLLM when API keys available."""
        from mcp_server_langgraph.llm.embeddings import (
            LiteLLMEmbeddingService,
            get_embedding_service,
        )

        with patch(
            "mcp_server_langgraph.llm.embeddings._has_litellm_embedding_config",
            return_value=True,
        ):
            with patch(
                "mcp_server_langgraph.llm.embeddings._get_default_embedding_model",
                return_value="text-embedding-3-small",
            ):
                service = get_embedding_service()
                assert isinstance(service, LiteLLMEmbeddingService)
