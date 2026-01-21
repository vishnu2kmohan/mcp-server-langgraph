"""
Unified Tools API

Provides endpoints to list and search available tools (built-in + MCP).
Supports manual tool selection in the chat input by exposing all tools
that can be selected by the user.

Built-in tools are sourced from the tools module (get_all_tools).
MCP tools are sourced from the CachedUnifiedRegistry.

Usage:
    GET /api/v1/tools - List all available tools
    GET /api/v1/tools?source=builtin - List only built-in tools
    GET /api/v1/tools?source=mcp - List only MCP tools
    GET /api/v1/tools?category=search - Filter by category
    GET /api/v1/tools?search=query - Search tools by name/description
    POST /api/v1/tools/semantic-search - Vector-based semantic search (feature flagged)
"""

from typing import TYPE_CHECKING, Annotated, Any, Literal, cast

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from mcp_server_langgraph.auth.dependencies import get_current_user
from mcp_server_langgraph.core.feature_flags import feature_flags
from mcp_server_langgraph.observability.telemetry import logger
from mcp_server_langgraph.tools import get_all_tools
from mcp_server_langgraph.tools.constants import (
    SANDBOX_REQUIRED_TOOLS,
    TOOL_CATEGORY_MAP,
    get_display_name as _get_display_name,
    get_tool_category as _get_tool_category,
    tool_requires_sandbox,
)

if TYPE_CHECKING:
    from mcp_server_langgraph.skills.search import (
        EmbeddingServiceProtocol,
        VectorProviderProtocol,
    )

# Router for unified tools API
tools_router = APIRouter(prefix="/tools", tags=["Tools"])

# Type alias for authenticated user dependency
CurrentUser = Annotated[dict[str, Any], Depends(get_current_user)]

# Source type for tool origin (v7: added "native" for LLM provider tools)
ToolSource = Literal["builtin", "mcp", "native"]


# =============================================================================
# Response Models
# =============================================================================


class UnifiedToolResponse(BaseModel):
    """Unified tool response combining built-in, MCP, and native tools."""

    # v7: Add tool_id as unique identifier for selection
    tool_id: str = Field(..., description="Unique tool identifier (source:name)")
    name: str = Field(..., description="Tool name (qualified name for MCP tools)")
    display_name: str = Field(..., description="Human-readable display name")
    description: str = Field(..., description="Tool description")
    source: ToolSource = Field(..., description="Tool source: 'builtin', 'mcp', or 'native'")
    server_name: str | None = Field(None, description="MCP server name (MCP tools only)")
    # v7: Add provider field for native tools
    provider: str | None = Field(None, description="Native tool provider (anthropic, google)")
    category: str | None = Field(None, description="Tool category for grouping")
    input_schema: dict[str, Any] = Field(default_factory=dict, description="JSON Schema for parameters")
    requires_sandbox: bool = Field(default=False, description="Whether tool requires sandbox environment")


class UnifiedToolsListResponse(BaseModel):
    """Response for listing all tools."""

    tools: list[UnifiedToolResponse] = Field(..., description="List of unified tools")
    builtin_count: int = Field(..., description="Number of built-in tools")
    mcp_count: int = Field(..., description="Number of MCP tools")
    # v7: Add native_count for native LLM provider tools
    native_count: int = Field(default=0, description="Number of native LLM provider tools")
    total_count: int = Field(..., description="Total number of tools")


# =============================================================================
# Helper Functions
# =============================================================================


def _tool_matches_search(tool: UnifiedToolResponse, search: str) -> bool:
    """Check if a tool matches a search term."""
    search_lower = search.lower()
    return (
        search_lower in tool.name.lower()
        or search_lower in tool.display_name.lower()
        or search_lower in tool.description.lower()
        or (tool.category is not None and search_lower in tool.category.lower())
    )


def _builtin_tool_to_response(tool: Any) -> UnifiedToolResponse:
    """Convert a LangChain BaseTool to UnifiedToolResponse."""
    tool_name = tool.name
    category = _get_tool_category(tool_name)

    # Extract input schema if available
    input_schema: dict[str, Any] = {}
    if hasattr(tool, "args_schema") and tool.args_schema is not None:
        try:
            input_schema = tool.args_schema.model_json_schema()
        except Exception:
            pass

    return UnifiedToolResponse(
        # v7: Add tool_id in format "builtin:{name}"
        tool_id=f"builtin:{tool_name}",
        name=tool_name,
        display_name=_get_display_name(tool_name),
        description=tool.description or "",
        source="builtin",
        server_name=None,
        provider=None,  # v7: No provider for builtin tools
        category=category,
        input_schema=input_schema,
        requires_sandbox=tool_name in SANDBOX_REQUIRED_TOOLS,
    )


def _mcp_tool_to_response(tool: dict[str, Any]) -> UnifiedToolResponse:
    """Convert an MCP tool dict to UnifiedToolResponse."""
    qualified_name = tool.get("qualified_name", "")
    server_name = tool.get("server_name")

    return UnifiedToolResponse(
        # v7: Add tool_id in format "mcp:{qualified_name}"
        tool_id=f"mcp:{qualified_name}",
        name=qualified_name,
        display_name=_get_display_name(tool.get("name", qualified_name)),
        description=tool.get("description", ""),
        source="mcp",
        server_name=server_name,
        provider=None,  # v7: No provider for MCP tools
        category=None,  # MCP tools don't have predefined categories
        input_schema=tool.get("input_schema", {}),
        requires_sandbox=False,  # MCP tools are externally managed
    )


def _native_tool_to_response(
    name: str,
    provider: str,
    provider_type: str,
    description: str,
) -> UnifiedToolResponse:
    """Convert a native tool definition to UnifiedToolResponse.

    v7: Native tools are LLM provider-specific tools like Anthropic's web_search
    or Google's grounded search that are executed by the provider directly.
    """
    return UnifiedToolResponse(
        tool_id=f"native:{name}",
        name=name,
        display_name=f"{name.replace('_', ' ').title()} (Native)",
        description=description,
        source="native",
        server_name=None,
        provider=provider,
        category="native",
        input_schema={},  # Native tools have provider-managed schemas
        requires_sandbox=False,  # Native tools run in provider's environment
    )


def _get_native_tools() -> list[UnifiedToolResponse]:
    """Get list of available native tools based on feature flags.

    v7: Native tools are conditionally included based on feature flags.
    """
    native_tools: list[UnifiedToolResponse] = []

    try:
        from mcp_server_langgraph.tools.native_registry import NATIVE_TOOLS

        for (name, provider), defn in NATIVE_TOOLS.items():
            # Check provider-specific flags
            if provider == "anthropic":
                if name == "web_search" and feature_flags.anthropic_native_web_search_enabled:
                    native_tools.append(
                        _native_tool_to_response(
                            name=defn.name,
                            provider=defn.provider,
                            provider_type=defn.provider_type,
                            description=defn.description,
                        )
                    )
                elif name == "code_execution" and feature_flags.anthropic_native_code_execution_enabled:
                    native_tools.append(
                        _native_tool_to_response(
                            name=defn.name,
                            provider=defn.provider,
                            provider_type=defn.provider_type,
                            description=defn.description,
                        )
                    )
            elif provider == "google":
                if name == "web_search" and feature_flags.google_native_search_enabled:
                    native_tools.append(
                        _native_tool_to_response(
                            name=defn.name,
                            provider=defn.provider,
                            provider_type=defn.provider_type,
                            description=defn.description,
                        )
                    )
    except ImportError:
        logger.warning("Native registry not available")

    return native_tools


# =============================================================================
# Endpoints
# =============================================================================


@tools_router.get(
    "",
    summary="List all available tools",
    description="Get unified list of built-in, MCP, and native tools for manual selection",
    response_model=UnifiedToolsListResponse,
)
async def list_tools(
    current_user: CurrentUser,
    source: Literal["all", "builtin", "mcp", "native"] | None = None,
    category: str | None = None,
    search: str | None = None,
) -> UnifiedToolsListResponse:
    """List all tools (built-in + MCP + native) available for manual selection.

    v7: Added native LLM provider tools support.

    Requires user authentication.

    Args:
        source: Filter by source ('all', 'builtin', 'mcp', 'native')
        category: Filter by tool category
        search: Search term for filtering by name/description

    Returns:
        Unified list of tools with counts
    """
    tools: list[UnifiedToolResponse] = []
    builtin_count = 0
    mcp_count = 0
    native_count = 0

    # Get built-in tools if not filtered to MCP or native only
    if source in (None, "all", "builtin"):
        builtin_tools = get_all_tools()
        for bt in builtin_tools:
            tool_response = _builtin_tool_to_response(bt)

            # Apply category filter
            if category and tool_response.category != category:
                continue

            tools.append(tool_response)
            builtin_count += 1

    # Get MCP tools if not filtered to builtin or native only
    if source in (None, "all", "mcp"):
        try:
            from mcp_server_langgraph.mcp.client.cached_unified_registry import (
                get_cached_unified_registry,
            )

            cached_registry = get_cached_unified_registry()
            mcp_tools = await cached_registry.get_tools()

            for mt in mcp_tools:
                tool_response = _mcp_tool_to_response(mt)

                # Apply category filter (MCP tools have no category, skip if filtering)
                if category:
                    continue

                tools.append(tool_response)
                mcp_count += 1
        except Exception:
            # If MCP registry is not available, just return builtin tools
            pass

    # v7: Get native tools if enabled and not filtered to builtin or mcp only
    if source in (None, "all", "native") and feature_flags.native_tools_enabled:
        native_tools = _get_native_tools()
        for nt in native_tools:
            # Apply category filter
            if category and nt.category != category:
                continue

            tools.append(nt)
            native_count += 1

    # Apply search filter
    if search:
        tools = [t for t in tools if _tool_matches_search(t, search)]
        # Recount after filtering
        builtin_count = sum(1 for t in tools if t.source == "builtin")
        mcp_count = sum(1 for t in tools if t.source == "mcp")
        native_count = sum(1 for t in tools if t.source == "native")

    return UnifiedToolsListResponse(
        tools=tools,
        builtin_count=builtin_count,
        mcp_count=mcp_count,
        native_count=native_count,
        total_count=len(tools),
    )


# =============================================================================
# Semantic Search Models
# =============================================================================


class SemanticToolSearchRequest(BaseModel):
    """Request body for semantic tool search."""

    query: str = Field(..., min_length=1, description="Natural language search query")
    limit: int = Field(default=10, ge=1, le=50, description="Maximum number of results")
    min_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Minimum similarity score")


class SemanticToolSearchResult(BaseModel):
    """A single semantic search result."""

    tool_id: str = Field(..., description="Unique tool identifier")
    name: str = Field(..., description="Tool name")
    description: str = Field(..., description="Tool description")
    score: float = Field(..., ge=0.0, le=1.0, description="Similarity score (0-1)")
    category: str | None = Field(None, description="Tool category")


class SemanticToolSearchResponse(BaseModel):
    """Response for semantic tool search."""

    query: str = Field(..., description="Original search query")
    results: list[SemanticToolSearchResult] = Field(..., description="Search results ordered by score")
    total_results: int = Field(..., description="Number of results returned")


# =============================================================================
# Semantic Search Provider Functions
# =============================================================================


def get_vector_provider() -> "VectorProviderProtocol":
    """Get the vector provider for semantic search.

    Returns:
        Vector provider instance (Qdrant, pgvector, or in-memory)

    Raises:
        HTTPException: If vector provider is not available
    """
    try:
        from mcp_server_langgraph.storage.vectors import get_vector_provider as _get_provider

        provider = _get_provider()
        if provider is None:
            raise HTTPException(
                status_code=503,
                detail="Vector provider not available. Ensure Qdrant or pgvector is configured.",
            )
        # Cast: VectorSearchProvider implements VectorProviderProtocol semantically
        return cast("VectorProviderProtocol", provider)
    except ImportError as e:
        logger.warning(f"Vector provider import failed: {e}")
        raise HTTPException(
            status_code=503,
            detail="Vector storage not configured",
        ) from e


def get_embedding_service() -> "EmbeddingServiceProtocol":
    """Get the embedding service for generating query vectors.

    Returns:
        Embedding service instance

    Raises:
        HTTPException: If embedding service is not available
    """
    try:
        from mcp_server_langgraph.llm.embeddings import get_embedding_service as _get_service

        service = _get_service()
        if service is None:
            raise HTTPException(
                status_code=503,
                detail="Embedding service not available. Ensure LLM provider is configured.",
            )
        return service
    except ImportError as e:
        logger.warning(f"Embedding service import failed: {e}")
        raise HTTPException(
            status_code=503,
            detail="Embedding service not configured",
        ) from e


# =============================================================================
# Semantic Search Endpoint
# =============================================================================


@tools_router.post(
    "/semantic-search",
    summary="Semantic tool search",
    description="Find tools using natural language query via vector similarity search",
    response_model=SemanticToolSearchResponse,
)
async def semantic_search_tools(
    request: SemanticToolSearchRequest,
    current_user: CurrentUser,
) -> SemanticToolSearchResponse:
    """Search for tools using semantic similarity.

    This endpoint uses vector embeddings to find tools that semantically
    match the user's natural language query. Requires the
    enable_semantic_tool_search feature flag to be enabled.

    Args:
        request: Search request with query and options
        current_user: Authenticated user

    Returns:
        Semantic search results with similarity scores

    Raises:
        HTTPException: 404 if feature not enabled, 503 if services unavailable
    """
    # Check feature flag
    if not feature_flags.enable_semantic_tool_search:
        raise HTTPException(
            status_code=404,
            detail="Semantic tool search is not enabled. Set FF_ENABLE_SEMANTIC_TOOL_SEARCH=true to activate.",
        )

    # Get services
    vector_provider = get_vector_provider()
    embedding_service = get_embedding_service()

    # Generate query embedding
    query_vector = await embedding_service.embed(request.query)

    # Search vector store
    raw_results = await vector_provider.search(
        collection="tools",
        query_vector=query_vector,
        limit=request.limit,
        min_score=request.min_score,
    )

    # Transform results to response model
    results = [
        SemanticToolSearchResult(
            tool_id=r.get("id", ""),
            name=r.get("metadata", {}).get("name", ""),
            description=r.get("metadata", {}).get("description", ""),
            score=r.get("score", 0.0),
            category=r.get("metadata", {}).get("category"),
        )
        for r in raw_results
    ]

    logger.info(
        f"Semantic tool search for '{request.query[:50]}...' returned {len(results)} results",
        extra={
            "user_id": current_user.get("sub", "unknown"),
            "query": request.query[:100],
            "result_count": len(results),
        },
    )

    return SemanticToolSearchResponse(
        query=request.query,
        results=results,
        total_results=len(results),
    )
