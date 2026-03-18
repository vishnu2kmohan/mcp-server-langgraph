"""
Search tools for querying information

Provides knowledge base and web search capabilities for the agent.
"""

from typing import Annotated

import httpx
from langchain_core.tools import tool
from pydantic import Field

from mcp_server_langgraph.core.config import settings
from mcp_server_langgraph.core.constants import MESSAGE_PREVIEW_LENGTH
from mcp_server_langgraph.observability.telemetry import logger, metrics


# Supported embedding providers
SUPPORTED_PROVIDERS = {"google_vertex", "google", "openai", "local", "huggingface"}


def _validate_semantic_search_config() -> tuple[bool, str | None]:
    """
    Validate configuration for semantic search.

    Returns:
        (is_valid, error_guidance) - If invalid, error_guidance contains setup instructions.
    """
    # Core Qdrant settings
    qdrant_url = getattr(settings, "qdrant_url", None)

    if not qdrant_url:
        return False, _build_qdrant_guidance()

    # Embedding settings
    provider = getattr(settings, "embedding_provider", None)
    model_name = getattr(settings, "embedding_model_name", None)
    dimensions = getattr(settings, "embedding_dimensions", None)

    if not provider or not model_name or not dimensions:
        return False, _build_embedding_guidance(provider)

    # Validate provider is supported
    if provider not in SUPPORTED_PROVIDERS:
        return False, _build_unsupported_provider_guidance(provider)

    # Provider-specific validation
    if provider == "google_vertex":
        # Uses ADC - no explicit key needed, but check for langchain_google_vertexai
        try:
            import langchain_google_vertexai  # noqa: F401
        except ImportError:
            return False, _build_google_vertex_guidance()

    elif provider == "google":
        if not getattr(settings, "google_api_key", None):
            return False, _build_google_api_guidance()

    elif provider == "openai":
        if not getattr(settings, "openai_api_key", None):
            return False, _build_openai_guidance()

    elif provider == "local":
        try:
            import sentence_transformers  # noqa: F401
        except ImportError:
            return False, _build_local_guidance()

    elif provider == "huggingface":
        try:
            import langchain_huggingface  # noqa: F401
        except ImportError:
            return False, _build_huggingface_guidance()

    return True, None


def _build_qdrant_guidance() -> str:
    return """Knowledge base search not configured: Qdrant not available.

Required environment variables:
  QDRANT_URL=localhost (or http://qdrant:6333 in Docker)
  QDRANT_PORT=6333
  QDRANT_COLLECTION_NAME=agent_studio_context
  ENABLE_DYNAMIC_CONTEXT_LOADING=true

See: .env.example"""


def _build_embedding_guidance(provider: str | None) -> str:
    return f"""Knowledge base search not configured: Embedding provider incomplete.

Current provider: {provider or "not set"}

Required environment variables:
  EMBEDDING_PROVIDER=google_vertex | google | openai | local | huggingface
  EMBEDDING_MODEL_NAME=<model-name>
  EMBEDDING_DIMENSIONS=<dimensions>

Provider examples:
  google_vertex: text-embedding-005 (768)
  google: models/text-embedding-004 (768)
  openai: text-embedding-3-small (1536)
  local: all-MiniLM-L6-v2 (384)
  huggingface: sentence-transformers/all-mpnet-base-v2 (768)"""


def _build_google_vertex_guidance() -> str:
    return """Knowledge base search not configured: langchain-google-vertexai not installed.

EMBEDDING_PROVIDER=google_vertex requires:
  uv add langchain-google-vertexai

Then configure:
  EMBEDDING_MODEL_NAME=text-embedding-005
  EMBEDDING_DIMENSIONS=768

Auth: Uses GCP Application Default Credentials (ADC).
  - GKE: Uses Workload Identity Federation automatically
  - Local: Run `gcloud auth application-default login`"""


def _build_google_api_guidance() -> str:
    return """Knowledge base search not configured: Missing Google API key.

EMBEDDING_PROVIDER=google requires:
  GOOGLE_API_KEY=your-api-key

Get your key at: https://aistudio.google.com/apikey

Then configure:
  EMBEDDING_MODEL_NAME=models/text-embedding-004
  EMBEDDING_DIMENSIONS=768"""


def _build_openai_guidance() -> str:
    return """Knowledge base search not configured: Missing OpenAI API key.

EMBEDDING_PROVIDER=openai requires:
  OPENAI_API_KEY=your-api-key

Get your key at: https://platform.openai.com/api-keys

Then configure:
  EMBEDDING_MODEL_NAME=text-embedding-3-small
  EMBEDDING_DIMENSIONS=1536"""


def _build_local_guidance() -> str:
    return """Knowledge base search not configured: sentence-transformers not installed.

EMBEDDING_PROVIDER=local requires:
  uv add sentence-transformers

Then configure:
  EMBEDDING_MODEL_NAME=all-MiniLM-L6-v2
  EMBEDDING_DIMENSIONS=384"""


def _build_huggingface_guidance() -> str:
    return """Knowledge base search not configured: langchain-huggingface not installed.

EMBEDDING_PROVIDER=huggingface requires:
  uv add langchain-huggingface

Then configure:
  EMBEDDING_MODEL_NAME=sentence-transformers/all-mpnet-base-v2
  EMBEDDING_DIMENSIONS=768

Optional (for private models):
  HF_TOKEN=your-huggingface-token"""


def _build_unsupported_provider_guidance(provider: str) -> str:
    return f"""Knowledge base search not configured: Unsupported embedding provider.

Current provider: {provider}

Supported providers:
  - google_vertex: GCP Vertex AI (ADC auth)
  - google: Google AI Studio (GOOGLE_API_KEY)
  - openai: OpenAI (OPENAI_API_KEY)
  - local: sentence-transformers (no auth)
  - huggingface: HuggingFace (optional HF_TOKEN)

Set EMBEDDING_PROVIDER to one of the above."""


def _format_references(refs: list) -> str:
    """Format references as concise markdown summaries."""
    if not refs:
        return "No results found."

    lines = [f"Found {len(refs)} result(s):\n"]
    for i, ref in enumerate(refs, 1):
        score = f"{ref.relevance_score:.2f}" if ref.relevance_score else "N/A"
        lines.append(f"{i}. **{ref.summary}** (score: {score})")
        lines.append(f"   Type: {ref.ref_type} | ID: {ref.ref_id}")

    lines.append("\n💡 Set `load_full_content=True` to retrieve full content")
    return "\n".join(lines)


def _format_loaded_contexts(loaded: list) -> str:
    """Format loaded contexts as compact text."""
    if not loaded:
        return "No content loaded."

    total_tokens = sum(ctx.token_count for ctx in loaded)
    lines = [f"Loaded {len(loaded)} context(s) ({total_tokens} tokens):\n"]

    for ctx in loaded:
        ref = ctx.reference
        lines.append(f"### {ref.summary} ({ref.ref_type})")
        lines.append(f'<context id="{ref.ref_id}">\n{ctx.content}\n</context>\n')

    return "\n".join(lines)


@tool
async def search_knowledge_base(
    query: Annotated[str, Field(description="Search query to find relevant information")],
    limit: Annotated[int, Field(ge=1, le=20, description="Maximum results (1-20)")] = 5,
    load_full_content: Annotated[bool, Field(description="Load full content (more tokens) or just summaries")] = False,
) -> str:
    """
    Search internal knowledge base using semantic similarity.

    Returns relevance-ranked results. By default returns concise summaries.
    Set load_full_content=True for complete content (uses more tokens).

    Use this to find:
    - Documentation and guides
    - Previous conversations and context
    - System configuration
    - Frequently asked questions
    """
    try:
        logger.info("Knowledge base search invoked", extra={"query": query, "limit": limit})
        metrics.tool_calls.add(1, {"tool": "search_knowledge_base"})

        # 1. Validate config
        is_valid, guidance = _validate_semantic_search_config()
        if not is_valid:
            return guidance  # type: ignore[return-value]

        # 2. Search using DynamicContextLoader
        from mcp_server_langgraph.core.dynamic_context_loader import DynamicContextLoader

        loader = DynamicContextLoader()
        refs = await loader.semantic_search(query, top_k=limit)

        # 3. Format (progressive disclosure)
        max_tokens = getattr(settings, "dynamic_context_max_tokens", 2000)
        if load_full_content:
            loaded = await loader.load_batch(refs, max_tokens=max_tokens)
            result = _format_loaded_contexts(loaded)
        else:
            result = _format_references(refs)

        logger.info(
            "Knowledge base search completed",
            extra={"query": query, "results": len(refs), "load_full": load_full_content},
        )
        return result

    except Exception as e:
        error_msg = f"Search error: {e}"
        logger.error(f"Semantic search failed: {e}", exc_info=True)
        return error_msg


@tool
async def explore_knowledge_iteratively(
    initial_query: Annotated[str, Field(description="Starting search query")],
    expansion_terms: Annotated[list[str] | None, Field(description="Terms to expand search in later iterations")] = None,
    max_iterations: Annotated[int, Field(ge=1, le=5, description="Search iterations (1-5)")] = 3,
    load_full_content: Annotated[bool, Field()] = False,
) -> str:
    """
    Progressively discover knowledge through iterative refinement.

    Use when initial search doesn't find enough results or you need
    to explore related topics. Returns deduplicated, aggregated results.
    """
    try:
        logger.info(
            "Iterative knowledge exploration invoked",
            extra={"query": initial_query, "iterations": max_iterations},
        )
        metrics.tool_calls.add(1, {"tool": "explore_knowledge_iteratively"})

        is_valid, guidance = _validate_semantic_search_config()
        if not is_valid:
            return guidance  # type: ignore[return-value]

        from mcp_server_langgraph.core.dynamic_context_loader import DynamicContextLoader

        loader = DynamicContextLoader()
        refs = await loader.progressive_discover(
            initial_query=initial_query,
            max_iterations=max_iterations,
            expansion_keywords=expansion_terms,
        )

        max_tokens = getattr(settings, "dynamic_context_max_tokens", 2000)
        if load_full_content:
            loaded = await loader.load_batch(refs, max_tokens=max_tokens)
            result = _format_loaded_contexts(loaded)
        else:
            result = _format_references(refs)

        logger.info(
            "Iterative exploration completed",
            extra={"query": initial_query, "results": len(refs)},
        )
        return result

    except Exception as e:
        error_msg = f"Search error: {e}"
        logger.error(f"Progressive search failed: {e}", exc_info=True)
        return error_msg


@tool
async def web_search(
    query: Annotated[str, Field(description="Search query for web search")],
    num_results: Annotated[int, Field(ge=1, le=10, description="Number of results to return (1-10)")] = 5,
) -> str:
    """
    Search the web for current information.

    Use this to find:
    - Current events and news
    - External documentation
    - Public information not in knowledge base
    - Real-time data

    Returns titles, snippets, and URLs of top results.

    IMPORTANT: This tool requires web search API integration.
    Currently returns placeholder results.
    """
    try:
        logger.info("Web search invoked", extra={"query": query, "num_results": num_results})
        metrics.tool_calls.add(1, {"tool": "web_search"})

        # Check for configured web search API key
        # Note: Brave Search API support can be added when needed
        serper_api_key = getattr(settings, "serper_api_key", None)
        tavily_api_key = getattr(settings, "tavily_api_key", None)

        # Try Tavily API (recommended for AI applications)
        if tavily_api_key:
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        "https://api.tavily.com/search",
                        json={"api_key": tavily_api_key, "query": query, "max_results": num_results},
                        timeout=30.0,
                    )
                    response.raise_for_status()
                    # Note: httpx Response.json() is NOT async
                    data = response.json()

                    results = [f'Web search: "{query}"\n']
                    for i, result_item in enumerate(data.get("results", [])[:num_results], 1):
                        results.append(f"\n{i}. {result_item.get('title', 'No title')}")
                        results.append(f"   {result_item.get('content', 'No snippet')[:MESSAGE_PREVIEW_LENGTH]}...")
                        results.append(f"   URL: {result_item.get('url', 'N/A')}")

                    logger.info("Tavily web search completed", extra={"results": len(data.get("results", []))})
                    return "\n".join(results) if results else "No results found"

            except Exception as e:
                logger.error(f"Tavily search failed: {e}", exc_info=True)
                # Fall through to other providers or placeholder

        # Try Serper API
        elif serper_api_key:
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        "https://google.serper.dev/search",
                        json={"q": query, "num": num_results},
                        headers={"X-API-KEY": serper_api_key, "Content-Type": "application/json"},
                        timeout=30.0,
                    )
                    response.raise_for_status()
                    # Note: httpx Response.json() is NOT async
                    data = response.json()

                    results = [f'Web search: "{query}"\n']
                    for i, result_item in enumerate(data.get("organic", [])[:num_results], 1):
                        results.append(f"\n{i}. {result_item.get('title', 'No title')}")
                        results.append(f"   {result_item.get('snippet', 'No snippet')}")
                        results.append(f"   URL: {result_item.get('link', 'N/A')}")

                    logger.info("Serper web search completed", extra={"results": len(data.get("organic", []))})
                    return "\n".join(results) if results else "No results found"

            except Exception as e:
                logger.error(f"Serper search failed: {e}", exc_info=True)
                # Fall through to placeholder

        # No API key configured
        config_message = f"""Web search for: "{query}"

❌ Web search API not configured.

To enable web search, add one of these API keys to .env:

**Option 1: Tavily (Recommended for AI)**
- Get key: https://tavily.com/
- Add to .env: TAVILY_API_KEY=your-key
- Best for: AI-optimized search results

**Option 2: Serper (Google Search)**
- Get key: https://serper.dev/
- Add to .env: SERPER_API_KEY=your-key
- Best for: Google search results

**Option 3: Brave Search**
- Get key: https://brave.com/search/api/
- Add to .env: BRAVE_API_KEY=your-key
- Best for: Privacy-focused search

After configuration, this tool will return real web search results."""

        logger.info("Web search completed (no API key)", extra={"query": query})
        return config_message

    except Exception as e:
        error_msg = f"Error performing web search: {e}"
        logger.error(error_msg, exc_info=True)
        return f"Error: {e}"
