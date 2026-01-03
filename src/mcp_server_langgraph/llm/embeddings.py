"""
Embedding Service Abstraction

Provides a unified interface for generating text embeddings
across different providers (LiteLLM, sentence-transformers, etc).

Implementations:
- LiteLLMEmbeddingService: Multi-provider via LiteLLM (OpenAI, Vertex AI, etc)
- InMemoryEmbeddingService: Deterministic testing implementation

Usage:
    from mcp_server_langgraph.llm.embeddings import get_embedding_service

    service = get_embedding_service()
    embedding = await service.embed("Hello world")
    embeddings = await service.embed_batch(["text1", "text2"])
"""

from __future__ import annotations

import hashlib
import logging
import os
from abc import ABC, abstractmethod
from typing import Any

logger = logging.getLogger(__name__)


class EmbeddingService(ABC):
    """Abstract base class for embedding services.

    Provides a unified interface for generating text embeddings.
    Implementations may use different backends (LiteLLM, direct APIs, etc).
    """

    @abstractmethod
    async def embed(self, text: str) -> list[float]:
        """Generate embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            List of floats representing the embedding vector
        """
        pass

    @abstractmethod
    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors (one per input text)
        """
        pass


class LiteLLMEmbeddingService(EmbeddingService):
    """LiteLLM-based embedding service.

    Uses LiteLLM for multi-provider embedding support
    (OpenAI, Google Vertex AI, Azure, etc).
    """

    def __init__(
        self,
        model: str = "text-embedding-3-small",
        dimensions: int | None = None,
    ) -> None:
        """Initialize LiteLLM embedding service.

        Args:
            model: LiteLLM model identifier for embeddings
            dimensions: Optional embedding dimensions (if model supports)
        """
        self.model = model
        self.dimensions = dimensions

    async def embed(self, text: str) -> list[float]:
        """Generate embedding using LiteLLM.

        Args:
            text: Text to embed

        Returns:
            Embedding vector
        """
        import litellm

        kwargs: dict[str, Any] = {
            "model": self.model,
            "input": [text],
        }
        if self.dimensions:
            kwargs["dimensions"] = self.dimensions

        response = await litellm.aembedding(**kwargs)
        return list(response.data[0].embedding)

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts using LiteLLM.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        if not texts:
            return []

        import litellm

        kwargs: dict[str, Any] = {
            "model": self.model,
            "input": texts,
        }
        if self.dimensions:
            kwargs["dimensions"] = self.dimensions

        response = await litellm.aembedding(**kwargs)
        return [item.embedding for item in response.data]


class InMemoryEmbeddingService(EmbeddingService):
    """In-memory embedding service for testing.

    Generates deterministic embeddings based on text hash.
    Does not require any external dependencies.
    """

    def __init__(self, dimensions: int = 768) -> None:
        """Initialize in-memory embedding service.

        Args:
            dimensions: Size of embedding vectors to generate
        """
        self.dimensions = dimensions

    async def embed(self, text: str) -> list[float]:
        """Generate deterministic embedding from text hash.

        Args:
            text: Text to embed

        Returns:
            Embedding vector (deterministic based on text content)
        """
        return self._hash_to_vector(text)

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        return [self._hash_to_vector(text) for text in texts]

    def _hash_to_vector(self, text: str) -> list[float]:
        """Convert text to deterministic vector via hashing.

        Creates a reproducible embedding by using SHA-256 hash
        and distributing bytes across the vector dimensions.

        Args:
            text: Text to convert

        Returns:
            Deterministic float vector
        """
        # Use SHA-256 for deterministic hashing
        hash_bytes = hashlib.sha256(text.encode("utf-8")).digest()

        # Extend hash to cover all dimensions
        extended_hash = hash_bytes
        while len(extended_hash) < self.dimensions:
            # Hash the extended hash to get more bytes
            extended_hash += hashlib.sha256(extended_hash).digest()

        # Convert bytes to floats in range [-1, 1]
        vector = []
        for i in range(self.dimensions):
            byte_val = extended_hash[i]
            # Map 0-255 to -1.0 to 1.0
            float_val = (byte_val / 127.5) - 1.0
            vector.append(float_val)

        return vector


def _has_litellm_embedding_config() -> bool:
    """Check if LiteLLM embedding is configured.

    Returns:
        True if any embedding API key is available
    """
    # Check for common embedding API keys
    api_keys = [
        "OPENAI_API_KEY",
        "GOOGLE_API_KEY",
        "VERTEX_AI_PROJECT",
        "AZURE_API_KEY",
        "COHERE_API_KEY",
    ]
    return any(os.environ.get(key) for key in api_keys)


def _get_default_embedding_model() -> str:
    """Get default embedding model based on available config.

    Returns:
        Model identifier for LiteLLM
    """
    if os.environ.get("OPENAI_API_KEY"):
        return "text-embedding-3-small"
    if os.environ.get("GOOGLE_API_KEY") or os.environ.get("VERTEX_AI_PROJECT"):
        return "vertex_ai/text-embedding-005"
    if os.environ.get("COHERE_API_KEY"):
        return "cohere/embed-english-v3.0"
    # Default to OpenAI format (will fail without key)
    return "text-embedding-3-small"


def get_embedding_service(
    model: str | None = None,
    dimensions: int = 768,
) -> EmbeddingService:
    """Get an embedding service instance.

    Factory function that returns the appropriate embedding service
    based on available configuration.

    Args:
        model: Optional model override
        dimensions: Embedding dimensions (for InMemory fallback)

    Returns:
        EmbeddingService instance
    """
    # If model explicitly provided, use LiteLLM
    if model:
        return LiteLLMEmbeddingService(model=model, dimensions=dimensions)

    # Auto-detect based on environment
    if _has_litellm_embedding_config():
        default_model = _get_default_embedding_model()
        logger.debug(
            "Using LiteLLM embedding service",
            extra={"model": default_model},
        )
        return LiteLLMEmbeddingService(model=default_model, dimensions=dimensions)

    # Fallback to in-memory for testing
    logger.debug(
        "Using InMemory embedding service (no API keys configured)",
        extra={"dimensions": dimensions},
    )
    return InMemoryEmbeddingService(dimensions=dimensions)
