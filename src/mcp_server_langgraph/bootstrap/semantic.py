"""
Semantic Index Bootstrap Module.

Provides initialization for semantic search components:
- SemanticIndexManager singleton (init_semantic_manager)
- Tool indexing from unified registry (index_all_tools)
- Embedder configuration
- Qdrant client connection
- Authorization cache warming

Split Architecture (v26):
- init_semantic_manager(): Creates manager, registers singleton (Phase 8)
- index_all_tools(): Indexes tools from registry (per-entrypoint, after MCP sync)

Reference: ADR-0099 Semantic Tool Selection
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from mcp_server_langgraph.core.dependencies import (
    get_semantic_index_manager,
    set_message_index_manager,
    set_semantic_index_manager,
)
from mcp_server_langgraph.core.feature_flags import feature_flags
from mcp_server_langgraph.observability.telemetry import logger

if TYPE_CHECKING:
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


async def init_semantic_manager(settings: "Settings") -> SemanticState | None:
    """Initialize SemanticIndexManager and register singleton (Phase 8).

    Creates and wires semantic search components:
    - Embedder based on embedding_provider setting
    - Qdrant client connection
    - SemanticIndexManager singleton
    - Cache warming with configured entries

    Does NOT index tools - that happens via index_all_tools() after MCP sync.

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

    # Create SemanticIndexManager with settings injection (v26)
    manager = SemanticIndexManager(
        embedder=embedder,
        qdrant_client=qdrant_client,
        collection_name=settings.qdrant_collection_name,
        vector_size=settings.embedding_dimensions,
        settings=settings,  # v26: DI for environment detection
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
        "Semantic index manager initialized",
        extra={
            "embedding_provider": settings.embedding_provider,
            "collection_name": settings.qdrant_collection_name,
            "features": {
                "tool_search": feature_flags.enable_semantic_tool_search,
                "skill_search": feature_flags.enable_semantic_skill_search,
                "memory_search": feature_flags.enable_semantic_memory_search,
                "message_embedding": feature_flags.enable_message_embedding,
            },
        },
    )

    return SemanticState(
        manager=manager,
        qdrant_client=qdrant_client,
    )


async def index_all_tools() -> None:
    """Index all tools from unified registry.

    MUST be called AFTER sync_mcp_tools() to include MCP tools.
    Uses get_semantic_index_manager() singleton.

    v26 Semantics:
    - Skips native tools (source='native') - they have tool_id=None by design
    - Raises ValueError for non-native tools with missing tool_id (fail-fast)
    - Raises ValueError for non-native tools with missing tool (fail-fast)
    - Uses ToolIndexEntry.from_langchain_tool() factory method

    Raises:
        ValueError: If non-native tool has tool_id=None or tool=None
    """
    if not feature_flags.enable_semantic_tool_search:
        logger.debug("Semantic tool search disabled, skipping indexing")
        return

    manager = get_semantic_index_manager()
    if manager is None:
        logger.debug("Semantic indexing disabled - no manager")
        return

    from mcp_server_langgraph.tools.semantic_index import ToolIndexEntry
    from mcp_server_langgraph.tools.unified_registry import get_tool_registry

    registry = get_tool_registry()
    tool_entries: list[ToolIndexEntry] = []

    for reg in registry.get_all():
        # v26: Skip native tools (expected to have tool_id=None)
        if reg.source == "native":
            continue

        # v26: Fail-fast for non-native tools with missing tool_id
        if reg.tool_id is None:
            raise ValueError(
                f"Non-native tool '{reg.name}' (source={reg.source}) has tool_id=None. "
                f"This indicates a data integrity bug in the registry."
            )

        # v26: Fail-fast for non-native tools with missing BaseTool
        if reg.tool is None:
            raise ValueError(
                f"Non-native tool '{reg.name}' (source={reg.source}) has tool=None. "
                f"This indicates a data integrity bug in the registry."
            )

        # Create index entry using factory method
        entry = ToolIndexEntry.from_langchain_tool(
            reg.tool,
            tool_id=reg.tool_id,  # Use RegisteredTool.tool_id directly
        )
        tool_entries.append(entry)

    if tool_entries:
        try:
            await manager.index_tools_batch(tool_entries)
            logger.info(f"Indexed {len(tool_entries)} tools for semantic search")
        except Exception as e:
            # Fail-open: continue even if indexing fails
            logger.warning(f"Failed to index tools at startup: {e}")


# Backwards compatibility alias
async def init_semantic(settings: "Settings") -> SemanticState | None:
    """Backwards compatible wrapper for init_semantic_manager.

    Deprecated: Use init_semantic_manager() + index_all_tools() instead.
    This exists for backwards compatibility with existing callers.

    Note: This version does NOT index tools. Callers should explicitly
    call index_all_tools() after MCP sync.
    """
    return await init_semantic_manager(settings)


__all__ = [
    "SemanticState",
    "index_all_tools",
    "init_semantic",
    "init_semantic_manager",
]
