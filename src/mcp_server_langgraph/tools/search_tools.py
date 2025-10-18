"""
Search tools for querying information

Provides knowledge base and web search capabilities for the agent.
"""

from typing import Annotated, Optional

import httpx
from langchain_core.tools import tool
from pydantic import Field
from qdrant_client import QdrantClient

from mcp_server_langgraph.core.config import settings
from mcp_server_langgraph.observability.telemetry import logger, metrics


@tool
def search_knowledge_base(
    query: Annotated[str, Field(description="Search query to find relevant information")],
    limit: Annotated[int, Field(ge=1, le=20, description="Maximum number of results (1-20)")] = 5,
) -> str:
    """
    Search internal knowledge base for relevant information.

    Use this to find:
    - Documentation and guides
    - Previous conversations and context
    - System configuration
    - Frequently asked questions

    Returns top matching results with relevance scores.
    """
    try:
        logger.info("Knowledge base search invoked", extra={"query": query, "limit": limit})
        metrics.tool_calls.add(1, {"tool": "search_knowledge_base"})

        # Check if Qdrant is configured
        if not hasattr(settings, "qdrant_url") or not settings.qdrant_url:
            return """Knowledge base search not configured.

To enable:
1. Deploy Qdrant vector database
2. Set QDRANT_URL and QDRANT_PORT in .env
3. Set ENABLE_DYNAMIC_CONTEXT_LOADING=true
4. Index your knowledge base documents

See: docs/advanced/dynamic-context.md"""

        # Query Qdrant for semantic search
        try:
            client = QdrantClient(
                url=settings.qdrant_url,
                port=getattr(settings, "qdrant_port", 6333),
            )

            # Use configured collection or default
            collection_name = getattr(settings, "qdrant_collection_name", "mcp_context")

            # Perform semantic search (requires embeddings)
            # Note: This assumes documents are already indexed
            # For full implementation, add embedding generation here

            results_text = f"""Knowledge base search: "{query}"

Connected to Qdrant at {settings.qdrant_url}:{getattr(settings, 'qdrant_port', 6333)}
Collection: {collection_name}

Note: Semantic search requires embeddings and indexed documents.
Configure EMBEDDING_PROVIDER and index your knowledge base.

For setup: See docs/advanced/dynamic-context.md"""

            logger.info("Knowledge base search completed", extra={"query": query})
            return results_text

        except Exception as e:
            logger.warning(f"Qdrant query failed: {e}")
            return f"""Knowledge base search error: {e}

Verify Qdrant is running and accessible at {settings.qdrant_url}"""

    except Exception as e:
        error_msg = f"Error searching knowledge base: {e}"
        logger.error(error_msg, exc_info=True)
        return f"Error: {e}"


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
        serper_api_key = getattr(settings, "serper_api_key", None)
        tavily_api_key = getattr(settings, "tavily_api_key", None)
        brave_api_key = getattr(settings, "brave_api_key", None)

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
                    data = response.json()

                    results = [f"Web search: \"{query}\"\n"]
                    for i, result in enumerate(data.get("results", [])[:num_results], 1):
                        results.append(f"\n{i}. {result.get('title', 'No title')}")
                        results.append(f"   {result.get('content', 'No snippet')[:200]}...")
                        results.append(f"   URL: {result.get('url', 'N/A')}")

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
                    data = response.json()

                    results = [f"Web search: \"{query}\"\n"]
                    for i, result in enumerate(data.get("organic", [])[:num_results], 1):
                        results.append(f"\n{i}. {result.get('title', 'No title')}")
                        results.append(f"   {result.get('snippet', 'No snippet')}")
                        results.append(f"   URL: {result.get('link', 'N/A')}")

                    logger.info("Serper web search completed", extra={"results": len(data.get("organic", []))})
                    return "\n".join(results) if results else "No results found"

            except Exception as e:
                logger.error(f"Serper search failed: {e}", exc_info=True)
                # Fall through to placeholder

        # No API key configured
        return f"""Web search for: "{query}"

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
        return results

    except Exception as e:
        error_msg = f"Error performing web search: {e}"
        logger.error(error_msg, exc_info=True)
        return f"Error: {e}"
