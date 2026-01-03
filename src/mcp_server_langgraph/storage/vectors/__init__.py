"""
Vector Search Providers

Provider-agnostic vector search abstraction supporting:
- pgvector (PostgreSQL extension)
- Qdrant (vector database)
- InMemory (testing)

Usage:
    from mcp_server_langgraph.storage.vectors import get_vector_provider

    provider = get_vector_provider("qdrant")
    await provider.upsert("collection", "id", vector, metadata)
    results = await provider.search("collection", query_vector, limit=10)
"""

from mcp_server_langgraph.storage.vectors.base import (
    VectorSearchProvider,
    VectorSearchResult,
)
from mcp_server_langgraph.storage.vectors.factory import get_vector_provider
from mcp_server_langgraph.storage.vectors.inmemory import InMemoryVectorProvider

# Lazy imports for optional providers (avoid import errors if deps missing)
# Use: from mcp_server_langgraph.storage.vectors.pgvector_provider import PgVectorProvider
# Use: from mcp_server_langgraph.storage.vectors.qdrant_provider import QdrantVectorProvider

__all__ = [
    "VectorSearchProvider",
    "VectorSearchResult",
    "get_vector_provider",
    "InMemoryVectorProvider",
    # Optional providers (use direct import from modules):
    # "PgVectorProvider",
    # "QdrantVectorProvider",
]
