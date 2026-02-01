"""
Source Citation Extraction.

This module extracts source citations from:
- Native web search tool results (Anthropic, Google, OpenAI)
- Builtin web_search tool results (markdown link format)
- Tool messages in the conversation
- Knowledge base context references

Citations are attached to assistant messages for display in the frontend chat UI.

Usage:
    from mcp_server_langgraph.tools.source_citation import (
        SourceCitation,
        extract_sources_from_message,
        extract_sources_from_tool_message,
        collect_sources_from_messages,
        extract_sources_from_kb_context,
        group_sources_by_domain,
        dedupe_by_domain,
        sort_sources_by_relevance,
    )

    # From an AIMessage with native web search results
    sources = extract_sources_from_message(ai_message)

    # From a ToolMessage with markdown links
    sources = extract_sources_from_tool_message(tool_message)

    # From a list of messages (deduplicates by URL)
    sources = collect_sources_from_messages(messages)

    # From KB context messages
    sources = extract_sources_from_kb_context(context_messages)
"""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

from langchain_core.messages import AIMessage, BaseMessage, SystemMessage, ToolMessage
from pydantic import BaseModel, Field


class SourceCitation(BaseModel):
    """A source citation extracted from web search results.

    Attributes:
        title: The title of the source
        url: The URL of the source
        snippet: Optional snippet/description from the source
        relevance_score: Optional relevance score (0.0 to 1.0) for ranking
    """

    title: str = Field(description="Source title")
    url: str = Field(description="Source URL")
    snippet: str | None = Field(default=None, description="Relevant snippet from source")
    relevance_score: float | None = Field(default=None, description="Relevance score for ranking (0.0 to 1.0)")

    def truncated_snippet(self, max_length: int = 150) -> str | None:
        """Return snippet truncated to max_length with ellipsis.

        Args:
            max_length: Maximum length before truncation

        Returns:
            Truncated snippet with "..." suffix, or None if no snippet
        """
        if self.snippet is None:
            return None

        if len(self.snippet) <= max_length:
            return self.snippet

        return self.snippet[:max_length] + "..."


# Regex pattern to extract markdown links: [Title](URL): Snippet
# Matches: [Title](https://example.com): Optional snippet text
# Also matches: [Title](https://example.com) without snippet
# Note: Title and URL cannot contain newlines to avoid matching across lines
MARKDOWN_LINK_PATTERN = re.compile(r"\[([^\]\n]+)\]\(([^)\n]+)\)(?::\s*([^\n]+))?(?:\n|$)")


def _is_source_citations_enabled() -> bool:
    """Check if source citations feature flag is enabled.

    Returns:
        True if FF_ENABLE_SOURCE_CITATIONS is enabled
    """
    from mcp_server_langgraph.core.feature_flags import feature_flags

    return feature_flags.enable_source_citations


def extract_sources_from_message(message: AIMessage) -> list[SourceCitation]:
    """Extract source citations from an AIMessage.

    Handles:
    - Anthropic web_search_results in content blocks
    - OpenAI Responses API native_output with web_search_call
    - Google grounded search results (grounding_metadata)

    Args:
        message: AIMessage potentially containing web search results

    Returns:
        List of SourceCitation objects extracted from the message
    """
    sources: list[SourceCitation] = []

    # Check additional_kwargs for OpenAI Responses API output
    native_output = message.additional_kwargs.get("native_output")
    if native_output:
        sources.extend(_extract_from_openai_native_output(native_output))

    # Check content blocks for Anthropic/Google results
    if isinstance(message.content, list):
        for block in message.content:
            if not isinstance(block, dict):
                continue

            block_type = block.get("type")

            # Anthropic web_search_results
            if block_type == "web_search_results":
                results = block.get("results", [])
                for result in results:
                    if isinstance(result, dict) and result.get("url"):
                        sources.append(
                            SourceCitation(
                                title=result.get("title", ""),
                                url=result.get("url", ""),
                                snippet=result.get("snippet"),
                            )
                        )

            # Google grounding_metadata
            elif block_type == "grounding_metadata":
                sources.extend(_extract_from_google_grounding(block))

    return sources


def _extract_from_google_grounding(block: dict[str, Any]) -> list[SourceCitation]:
    """Extract sources from Google grounding_metadata block.

    Google Vertex AI returns grounding information in this format:
    - grounding_chunks: List of web sources with uri and title
    - grounding_supports: Text segments with indices to chunks

    Args:
        block: A grounding_metadata block

    Returns:
        List of SourceCitation objects
    """
    sources: list[SourceCitation] = []

    grounding_chunks = block.get("grounding_chunks", [])
    grounding_supports = block.get("grounding_supports", [])

    # Build map of chunk index to support text (for snippets)
    chunk_snippets: dict[int, str] = {}
    for support in grounding_supports:
        if isinstance(support, dict):
            segment = support.get("segment", {})
            text = segment.get("text", "") if isinstance(segment, dict) else ""
            indices = support.get("grounding_chunk_indices", [])
            for idx in indices:
                if isinstance(idx, int) and text:
                    chunk_snippets[idx] = text

    # Extract sources from grounding chunks
    for i, chunk in enumerate(grounding_chunks):
        if not isinstance(chunk, dict):
            continue

        web = chunk.get("web", {})
        if isinstance(web, dict):
            uri = web.get("uri", "")
            title = web.get("title", "")

            if uri:
                sources.append(
                    SourceCitation(
                        title=title or uri,
                        url=uri,
                        snippet=chunk_snippets.get(i),
                    )
                )

    return sources


def _extract_from_openai_native_output(native_output: list[Any]) -> list[SourceCitation]:
    """Extract sources from OpenAI Responses API native_output.

    Args:
        native_output: List of output items from Responses API

    Returns:
        List of SourceCitation objects
    """
    sources: list[SourceCitation] = []

    for item in native_output:
        if not isinstance(item, dict):
            continue

        item_type = item.get("type")

        # OpenAI message with content blocks
        if item_type == "message":
            for block in item.get("content", []):
                if isinstance(block, dict) and block.get("type") == "web_search_call":
                    sources.extend(_extract_from_web_search_call(block))

        # Direct web_search_call items (top-level)
        elif item_type == "web_search_call":
            sources.extend(_extract_from_web_search_call(item))

    return sources


def _extract_from_web_search_call(block: dict[str, Any]) -> list[SourceCitation]:
    """Extract sources from a web_search_call block.

    Args:
        block: A web_search_call block containing results

    Returns:
        List of SourceCitation objects
    """
    sources: list[SourceCitation] = []
    results = block.get("results", [])

    for result in results:
        if isinstance(result, dict) and result.get("url"):
            sources.append(
                SourceCitation(
                    title=result.get("title", ""),
                    url=result.get("url", ""),
                    snippet=result.get("snippet"),
                )
            )

    return sources


def extract_sources_from_tool_message(message: ToolMessage) -> list[SourceCitation]:
    """Extract source citations from a ToolMessage.

    Parses markdown link format used by builtin web_search and parse_native_results:
    [Title](URL): Snippet text

    Only extracts from web_search tool messages.

    Args:
        message: ToolMessage potentially containing web search results

    Returns:
        List of SourceCitation objects extracted from the message
    """
    sources: list[SourceCitation] = []

    # Only extract from web_search tool
    if message.name != "web_search":
        return sources

    content = message.content
    if not content or not isinstance(content, str):
        return sources

    # Parse markdown links
    matches = MARKDOWN_LINK_PATTERN.findall(content)
    for match in matches:
        title, url, snippet = match
        if url:  # Must have URL
            sources.append(
                SourceCitation(
                    title=title.strip(),
                    url=url.strip(),
                    snippet=snippet.strip() if snippet else None,
                )
            )

    return sources


def extract_sources_from_kb_context(messages: list[BaseMessage]) -> list[SourceCitation]:
    """Extract source citations from knowledge base context messages.

    KB context messages store reference metadata in additional_kwargs["kb_reference"].

    Args:
        messages: List of context messages (typically SystemMessages)

    Returns:
        List of SourceCitation objects from KB references
    """
    sources: list[SourceCitation] = []

    for message in messages:
        if not isinstance(message, SystemMessage):
            continue

        kb_ref = message.additional_kwargs.get("kb_reference")
        if not isinstance(kb_ref, dict):
            continue

        url = kb_ref.get("url", "")
        if not url:
            # Fall back to source path
            url = kb_ref.get("source", "")

        if url:
            sources.append(
                SourceCitation(
                    title=kb_ref.get("title", "KB Reference"),
                    url=url,
                    snippet=None,
                    relevance_score=kb_ref.get("relevance_score"),
                )
            )

    return sources


def collect_sources_from_messages(messages: list[BaseMessage]) -> list[SourceCitation]:
    """Collect all source citations from a list of messages.

    Extracts sources from AIMessages (native results), ToolMessages
    (builtin results), and SystemMessages (KB context), deduplicating by URL.

    Respects FF_ENABLE_SOURCE_CITATIONS feature flag.

    Args:
        messages: List of messages to extract sources from

    Returns:
        Deduplicated list of SourceCitation objects, empty if feature disabled
    """
    # Check feature flag
    if not _is_source_citations_enabled():
        return []

    sources: list[SourceCitation] = []
    seen_urls: set[str] = set()

    for message in messages:
        extracted: list[SourceCitation] = []

        if isinstance(message, AIMessage):
            extracted = extract_sources_from_message(message)
        elif isinstance(message, ToolMessage):
            extracted = extract_sources_from_tool_message(message)
        elif isinstance(message, SystemMessage):
            # Check for KB reference
            if message.additional_kwargs.get("kb_reference"):
                extracted = extract_sources_from_kb_context([message])

        # Deduplicate by URL
        for source in extracted:
            if source.url not in seen_urls:
                seen_urls.add(source.url)
                sources.append(source)

    return sources


def extract_domain(url: str) -> str:
    """Extract domain from a URL.

    Args:
        url: The URL to extract domain from

    Returns:
        The domain (netloc) or the original string if parsing fails
    """
    try:
        parsed = urlparse(url)
        if parsed.netloc:
            # Remove port if present
            return parsed.netloc.split(":")[0]
        return url
    except Exception:
        return url


def group_sources_by_domain(sources: list[SourceCitation]) -> dict[str, list[SourceCitation]]:
    """Group sources by their domain.

    Args:
        sources: List of source citations

    Returns:
        Dictionary mapping domain to list of sources from that domain
    """
    grouped: dict[str, list[SourceCitation]] = {}

    for source in sources:
        domain = extract_domain(source.url)
        if domain not in grouped:
            grouped[domain] = []
        grouped[domain].append(source)

    return grouped


def dedupe_by_domain(sources: list[SourceCitation]) -> list[SourceCitation]:
    """Deduplicate sources keeping only first per domain.

    Preserves order - keeps the first source encountered for each domain.

    Args:
        sources: List of source citations

    Returns:
        List with at most one source per domain
    """
    seen_domains: set[str] = set()
    result: list[SourceCitation] = []

    for source in sources:
        domain = extract_domain(source.url)
        if domain not in seen_domains:
            seen_domains.add(domain)
            result.append(source)

    return result


def sort_sources_by_relevance(sources: list[SourceCitation]) -> list[SourceCitation]:
    """Sort sources by relevance_score descending.

    Sources without a relevance_score are sorted last.

    Args:
        sources: List of source citations

    Returns:
        Sorted list with highest relevance first
    """

    def sort_key(source: SourceCitation) -> tuple[int, float]:
        # Sources with score sort first (0), without sort last (1)
        # Within each group, sort by score descending (negate for desc)
        if source.relevance_score is not None:
            return (0, -source.relevance_score)
        return (1, 0.0)

    return sorted(sources, key=sort_key)


# =============================================================================
# Alias Functions for API Consistency
# =============================================================================


def extract_source_citations(message: AIMessage) -> list[dict[str, Any]]:
    """Extract source citations from an AIMessage as dictionaries.

    This is an alias for extract_sources_from_message that returns
    dictionaries instead of SourceCitation objects for easier JSON
    serialization.

    Args:
        message: AIMessage potentially containing web search results

    Returns:
        List of source citation dictionaries
    """
    sources = extract_sources_from_message(message)
    return [source.model_dump() for source in sources]


def deduplicate_sources_by_domain(
    sources: list[SourceCitation],
) -> list[SourceCitation]:
    """Deduplicate sources keeping only first per domain.

    Alias for dedupe_by_domain with a more descriptive name.

    Args:
        sources: List of source citations

    Returns:
        List with at most one source per domain
    """
    return dedupe_by_domain(sources)
