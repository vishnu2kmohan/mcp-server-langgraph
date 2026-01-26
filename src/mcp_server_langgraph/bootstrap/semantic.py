"""
Semantic Index Bootstrap Module.

Provides initialization for semantic search components:
- SemanticIndexManager singleton
- Embedder configuration
- Qdrant client connection
- Authorization cache warming
- Startup tool indexing

Follows existing pattern from bootstrap/context_graph.py.

Reference: ADR-0099 Semantic Tool Selection
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from mcp_server_langgraph.core.dependencies import (
    set_message_index_manager,
    set_semantic_index_manager,
)
from mcp_server_langgraph.core.feature_flags import feature_flags
from mcp_server_langgraph.observability.telemetry import logger
from mcp_server_langgraph.tools import get_all_tools
from mcp_server_langgraph.tools.semantic_index import ToolCategory, ToolIndexEntry

if TYPE_CHECKING:
    from langchain_core.tools import BaseTool

    from mcp_server_langgraph.core.config import Settings
    from mcp_server_langgraph.core.semantic_index_manager import SemanticIndexManager


@dataclass
class SemanticState:
    """Semantic index component state.

    Holds references to initialized semantic search components
    and provides cleanup method for graceful shutdown.
    """

    manager: "SemanticIndexManager | None" = None
    qdrant_client: Any = None  # AsyncQdrantClient

    async def cleanup(self) -> None:
        """Cleanup semantic resources.

        Closes Qdrant client connection.
        """
        if self.qdrant_client is not None:
            try:
                await self.qdrant_client.close()
                logger.debug("Qdrant client closed")
            except Exception as e:
                logger.debug("Qdrant client cleanup failed: %s", e)


def _is_semantic_search_enabled() -> bool:
    """Check if any semantic search feature is enabled.

    Returns:
        True if at least one semantic search feature is enabled
    """
    return (
        feature_flags.enable_semantic_tool_search
        or feature_flags.enable_semantic_skill_search
        or feature_flags.enable_semantic_memory_search
        or feature_flags.enable_message_embedding  # v8: Message embedding for session similarity
    )


def _tool_to_index_entry(tool: "BaseTool") -> ToolIndexEntry:
    """Convert a BaseTool to a ToolIndexEntry for semantic indexing.

    Args:
        tool: LangChain BaseTool instance

    Returns:
        ToolIndexEntry ready for indexing
    """
    return ToolIndexEntry(
        tool_id=f"tool:{tool.name}",
        name=tool.name,
        description=tool.description or "",
        category=ToolCategory.OTHER.value,  # Default category
    )


async def init_semantic(settings: "Settings") -> SemanticState | None:
    """Initialize semantic index if any semantic search feature is enabled.

    Creates and wires all semantic search components:
    - Embedder based on embedding_provider setting
    - Qdrant client connection
    - SemanticIndexManager singleton
    - Cache warming with configured entries

    Args:
        settings: Application settings

    Returns:
        SemanticState if enabled, None if disabled
    """
    if not _is_semantic_search_enabled():
        logger.debug("Semantic search disabled (no feature flags enabled)")
        return None

    # Import dependencies here to avoid circular imports and startup cost when disabled
    from qdrant_client import AsyncQdrantClient

    from mcp_server_langgraph.core.dynamic_context_loader import _create_embeddings
    from mcp_server_langgraph.core.semantic_index_manager import SemanticIndexManager

    # Create embedder using LangChain Embeddings interface
    embedder = _create_embeddings(
        provider=settings.embedding_provider,
        model_name=settings.embedding_model_name,
    )

    # Create Qdrant client
    qdrant_client = AsyncQdrantClient(
        host=settings.qdrant_url,
        port=settings.qdrant_port,
    )

    # Create SemanticIndexManager
    manager = SemanticIndexManager(
        embedder=embedder,
        qdrant_client=qdrant_client,
        collection_name=settings.qdrant_collection_name,
        vector_size=settings.embedding_dimensions,
    )

    # Register singleton for DI access
    set_semantic_index_manager(manager)

    # Ensure collection exists
    try:
        await manager.ensure_collection()
    except Exception as e:
        logger.warning(f"Failed to ensure Qdrant collection: {e}")
        # Continue without collection - will fail on first search

    # Warm authorization cache if entries configured
    if settings.auth_cache_warm_entries:
        try:
            warmed = await manager.warm_cache(settings.auth_cache_warm_entries)
            logger.info(f"Semantic authorization cache warmed: {warmed} entries")
        except Exception as e:
            logger.warning(f"Failed to warm authorization cache: {e}")

    # Index all available tools at startup when tool search is enabled
    if feature_flags.enable_semantic_tool_search:
        try:
            tools = get_all_tools()
            if tools:
                tool_entries = [_tool_to_index_entry(t) for t in tools]
                await manager.index_tools_batch(tool_entries)
                logger.info(
                    f"Semantic index: indexed {len(tool_entries)} tools at startup",
                    extra={"tool_count": len(tools)},
                )
        except Exception as e:
            # Fail-open: continue even if indexing fails
            logger.warning(f"Failed to index tools at startup: {e}")

    # v8: Initialize message index for session similarity when enabled
    if feature_flags.enable_message_embedding:
        try:
            from mcp_server_langgraph.core.message_semantic_index import (
                MessageSemanticIndexManager,
            )

            message_index_manager = MessageSemanticIndexManager(
                qdrant_client=qdrant_client,
                embedder=embedder,
                vector_size=settings.embedding_dimensions,
            )

            # Ensure message_index collection exists
            await message_index_manager.ensure_collection()

            # Register singleton for DI access
            set_message_index_manager(message_index_manager)

            logger.info(
                "Message semantic index initialized",
                extra={"collection_name": MessageSemanticIndexManager.COLLECTION_NAME},
            )
        except Exception as e:
            logger.warning(f"Failed to initialize message semantic index: {e}")
            # Continue without message index - session similarity will be unavailable

    logger.info(
        "Semantic index initialized",
        extra={
            "embedding_provider": settings.embedding_provider,
            "collection_name": settings.qdrant_collection_name,
            "features": {
                "tool_search": feature_flags.enable_semantic_tool_search,
                "skill_search": feature_flags.enable_semantic_skill_search,
                "memory_search": feature_flags.enable_semantic_memory_search,
                "message_embedding": feature_flags.enable_message_embedding,  # v8
            },
        },
    )

    return SemanticState(
        manager=manager,
        qdrant_client=qdrant_client,
    )


__all__ = [
    "SemanticState",
    "init_semantic",
]
