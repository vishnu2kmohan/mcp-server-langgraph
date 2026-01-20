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

if TYPE_CHECKING:
    from mcp_server_langgraph.skills.search import (
        EmbeddingServiceProtocol,
        VectorProviderProtocol,
    )

# Router for unified tools API
tools_router = APIRouter(prefix="/tools", tags=["Tools"])

# Type alias for authenticated user dependency
CurrentUser = Annotated[dict[str, Any], Depends(get_current_user)]

# Source type for tool origin
ToolSource = Literal["builtin", "mcp"]

# =============================================================================
# Category Mapping for Built-in Tools
# =============================================================================

# Map tool names to categories
TOOL_CATEGORY_MAP: dict[str, str] = {
    # Calculator tools
    "calculator": "calculator",
    "add": "calculator",
    "subtract": "calculator",
    "multiply": "calculator",
    "divide": "calculator",
    # Search tools
    "search_knowledge_base": "search",
    "web_search": "search",
    "explore_knowledge_iteratively": "search",
    # Filesystem tools (read-only)
    "read_file": "filesystem",
    "list_directory": "filesystem",
    "search_files": "filesystem",
    # File mutation tools
    "edit_file": "filesystem",
    "write_file": "filesystem",
    # Code execution tools
    "execute_bash": "code_execution",
    "execute_python": "code_execution",
    # Web tools
    "web_fetch": "web",
    # Visual tools
    "capture_screenshot": "visual",
    # Computer use tools
    "navigate": "computer_use",
    "go_back": "computer_use",
    "go_forward": "computer_use",
    "mouse_click": "computer_use",
    "mouse_move": "computer_use",
    "mouse_drag": "computer_use",
    "keyboard_type": "computer_use",
    "keyboard_press": "computer_use",
    "scroll": "computer_use",
    "select_option": "computer_use",
    "fill_form": "computer_use",
    "get_element_info": "computer_use",
    "get_screen_info": "computer_use",
}

# Tools that require sandbox environment (high-risk operations)
SANDBOX_REQUIRED_TOOLS: frozenset[str] = frozenset(
    {
        "execute_bash",
        "execute_python",
        "edit_file",
        "write_file",
        "web_fetch",
        "navigate",
        "go_back",
        "go_forward",
        "mouse_click",
        "mouse_move",
        "mouse_drag",
        "keyboard_type",
        "keyboard_press",
        "scroll",
        "select_option",
        "fill_form",
        "get_element_info",
        "get_screen_info",
        "capture_screenshot",
    }
)


# =============================================================================
# Response Models
# =============================================================================


class UnifiedToolResponse(BaseModel):
    """Unified tool response combining built-in and MCP tools."""

    name: str = Field(..., description="Tool name (qualified name for MCP tools)")
    display_name: str = Field(..., description="Human-readable display name")
    description: str = Field(..., description="Tool description")
    source: ToolSource = Field(..., description="Tool source: 'builtin' or 'mcp'")
    server_name: str | None = Field(None, description="MCP server name (MCP tools only)")
    category: str | None = Field(None, description="Tool category for grouping")
    input_schema: dict[str, Any] = Field(default_factory=dict, description="JSON Schema for parameters")
    requires_sandbox: bool = Field(default=False, description="Whether tool requires sandbox environment")


class UnifiedToolsListResponse(BaseModel):
    """Response for listing all tools."""

    tools: list[UnifiedToolResponse] = Field(..., description="List of unified tools")
    builtin_count: int = Field(..., description="Number of built-in tools")
    mcp_count: int = Field(..., description="Number of MCP tools")
    total_count: int = Field(..., description="Total number of tools")


# =============================================================================
# Helper Functions
# =============================================================================


def _get_tool_category(tool_name: str) -> str | None:
    """Get the category for a tool by name."""
    return TOOL_CATEGORY_MAP.get(tool_name)


def _get_display_name(tool_name: str) -> str:
    """Convert tool name to human-readable display name."""
    # Convert snake_case to Title Case
    return tool_name.replace("_", " ").title()


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
        name=tool_name,
        display_name=_get_display_name(tool_name),
        description=tool.description or "",
        source="builtin",
        server_name=None,
        category=category,
        input_schema=input_schema,
        requires_sandbox=tool_name in SANDBOX_REQUIRED_TOOLS,
    )


def _mcp_tool_to_response(tool: dict[str, Any]) -> UnifiedToolResponse:
    """Convert an MCP tool dict to UnifiedToolResponse."""
    qualified_name = tool.get("qualified_name", "")
    server_name = tool.get("server_name")

    return UnifiedToolResponse(
        name=qualified_name,
        display_name=_get_display_name(tool.get("name", qualified_name)),
        description=tool.get("description", ""),
        source="mcp",
        server_name=server_name,
        category=None,  # MCP tools don't have predefined categories
        input_schema=tool.get("input_schema", {}),
        requires_sandbox=False,  # MCP tools are externally managed
    )


# =============================================================================
# Endpoints
# =============================================================================


@tools_router.get(
    "",
    summary="List all available tools",
    description="Get unified list of built-in and MCP tools for manual selection",
    response_model=UnifiedToolsListResponse,
)
async def list_tools(
    current_user: CurrentUser,
    source: Literal["all", "builtin", "mcp"] | None = None,
    category: str | None = None,
    search: str | None = None,
) -> UnifiedToolsListResponse:
    """List all tools (built-in + MCP) available for manual selection.

    Requires user authentication.

    Args:
        source: Filter by source ('all', 'builtin', 'mcp')
        category: Filter by tool category
        search: Search term for filtering by name/description

    Returns:
        Unified list of tools with counts
    """
    tools: list[UnifiedToolResponse] = []
    builtin_count = 0
    mcp_count = 0

    # Get built-in tools if not filtered to MCP only
    if source in (None, "all", "builtin"):
        builtin_tools = get_all_tools()
        for bt in builtin_tools:
            tool_response = _builtin_tool_to_response(bt)

            # Apply category filter
            if category and tool_response.category != category:
                continue

            tools.append(tool_response)
            builtin_count += 1

    # Get MCP tools if not filtered to builtin only
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

    # Apply search filter
    if search:
        tools = [t for t in tools if _tool_matches_search(t, search)]
        # Recount after filtering
        builtin_count = sum(1 for t in tools if t.source == "builtin")
        mcp_count = sum(1 for t in tools if t.source == "mcp")

    return UnifiedToolsListResponse(
        tools=tools,
        builtin_count=builtin_count,
        mcp_count=mcp_count,
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
