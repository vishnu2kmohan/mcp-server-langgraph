"""
E2E Integration Test: Source Citations Data Flow

Tests the complete source citations data flow:
    Native/Builtin Tool Results → SourceCitation Extraction → Message → UI

This test verifies that source citations are properly extracted from various
tool result formats and flow correctly to the frontend chat UI.

Following memory safety patterns for pytest-xdist (see CLAUDE.md).
"""

import gc
from unittest.mock import patch
from uuid import uuid4

import pytest
from langchain_core.messages import AIMessage, SystemMessage, ToolMessage

pytestmark = [
    pytest.mark.integration,
    pytest.mark.source_citations,
    pytest.mark.asyncio,
    pytest.mark.xdist_group(name="source_citations_flow_e2e"),
]


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def enable_source_citations():
    """Enable source citations feature flag for tests."""
    with patch(
        "mcp_server_langgraph.tools.source_citation._is_source_citations_enabled",
        return_value=True,
    ):
        yield


# ============================================================================
# E2E Source Citations Flow Tests
# ============================================================================


class TestAnthropicWebSearchSources:
    """
    E2E tests for extracting sources from Anthropic native web search.
    """

    def setup_method(self):
        """Reset singleton dependencies."""
        from mcp_server_langgraph.core.dependencies import reset_singleton_dependencies

        reset_singleton_dependencies()

    def teardown_method(self):
        """Force GC."""
        from mcp_server_langgraph.core.dependencies import reset_singleton_dependencies

        reset_singleton_dependencies()
        gc.collect()

    async def test_extract_from_anthropic_web_search_results(self):
        """
        E2E: Verify sources are extracted from Anthropic web_search_results.

        GIVEN: An AIMessage with Anthropic web_search_results content block
        WHEN: extract_sources_from_message is called
        THEN: Source citations are extracted correctly
        """
        from mcp_server_langgraph.tools.source_citation import extract_sources_from_message

        # Simulate Anthropic web search results
        message = AIMessage(
            content=[
                {"type": "text", "text": "Based on my search..."},
                {
                    "type": "web_search_results",
                    "results": [
                        {
                            "title": "Python Documentation",
                            "url": "https://docs.python.org/",
                            "snippet": "Welcome to Python documentation",
                        },
                        {
                            "title": "Python Tutorial",
                            "url": "https://www.python.org/tutorial/",
                            "snippet": "Learn Python step by step",
                        },
                    ],
                },
            ]
        )

        sources = extract_sources_from_message(message)

        assert len(sources) == 2
        assert sources[0].title == "Python Documentation"
        assert sources[0].url == "https://docs.python.org/"
        assert sources[0].snippet == "Welcome to Python documentation"
        assert sources[1].title == "Python Tutorial"

    async def test_extract_with_missing_snippet(self):
        """
        E2E: Verify extraction handles missing snippets.

        GIVEN: An AIMessage with web search results missing snippets
        WHEN: extract_sources_from_message is called
        THEN: Sources are extracted with None snippets
        """
        from mcp_server_langgraph.tools.source_citation import extract_sources_from_message

        message = AIMessage(
            content=[
                {
                    "type": "web_search_results",
                    "results": [
                        {
                            "title": "Example Site",
                            "url": "https://example.com/",
                            # No snippet
                        },
                    ],
                },
            ]
        )

        sources = extract_sources_from_message(message)

        assert len(sources) == 1
        assert sources[0].snippet is None


class TestGoogleGroundingMetadata:
    """
    E2E tests for extracting sources from Google grounding metadata.
    """

    def setup_method(self):
        """Reset singleton dependencies."""
        from mcp_server_langgraph.core.dependencies import reset_singleton_dependencies

        reset_singleton_dependencies()

    def teardown_method(self):
        """Force GC."""
        from mcp_server_langgraph.core.dependencies import reset_singleton_dependencies

        reset_singleton_dependencies()
        gc.collect()

    async def test_extract_from_google_grounding_chunks(self):
        """
        E2E: Verify sources are extracted from Google grounding_metadata.

        GIVEN: An AIMessage with Google grounding_chunks
        WHEN: extract_sources_from_message is called
        THEN: Source citations are extracted correctly
        """
        from mcp_server_langgraph.tools.source_citation import extract_sources_from_message

        message = AIMessage(
            content=[
                {"type": "text", "text": "According to sources..."},
                {
                    "type": "grounding_metadata",
                    "grounding_chunks": [
                        {
                            "web": {
                                "uri": "https://cloud.google.com/vertex-ai",
                                "title": "Vertex AI Documentation",
                            }
                        },
                        {
                            "web": {
                                "uri": "https://cloud.google.com/gemini",
                                "title": "Gemini API",
                            }
                        },
                    ],
                    "grounding_supports": [
                        {
                            "segment": {"text": "Vertex AI is Google's platform"},
                            "grounding_chunk_indices": [0],
                        },
                    ],
                },
            ]
        )

        sources = extract_sources_from_message(message)

        assert len(sources) == 2
        assert sources[0].url == "https://cloud.google.com/vertex-ai"
        assert sources[0].title == "Vertex AI Documentation"
        assert sources[0].snippet == "Vertex AI is Google's platform"


class TestOpenAIResponsesAPI:
    """
    E2E tests for extracting sources from OpenAI Responses API.
    """

    def setup_method(self):
        """Reset singleton dependencies."""
        from mcp_server_langgraph.core.dependencies import reset_singleton_dependencies

        reset_singleton_dependencies()

    def teardown_method(self):
        """Force GC."""
        from mcp_server_langgraph.core.dependencies import reset_singleton_dependencies

        reset_singleton_dependencies()
        gc.collect()

    async def test_extract_from_openai_native_output(self):
        """
        E2E: Verify sources are extracted from OpenAI native_output.

        GIVEN: An AIMessage with OpenAI Responses API native_output
        WHEN: extract_sources_from_message is called
        THEN: Source citations are extracted correctly
        """
        from mcp_server_langgraph.tools.source_citation import extract_sources_from_message

        message = AIMessage(
            content="Here's what I found...",
            additional_kwargs={
                "native_output": [
                    {
                        "type": "message",
                        "content": [
                            {
                                "type": "web_search_call",
                                "results": [
                                    {
                                        "title": "OpenAI Documentation",
                                        "url": "https://platform.openai.com/docs",
                                        "snippet": "API reference and guides",
                                    },
                                ],
                            },
                        ],
                    },
                ],
            },
        )

        sources = extract_sources_from_message(message)

        assert len(sources) == 1
        assert sources[0].url == "https://platform.openai.com/docs"
        assert sources[0].title == "OpenAI Documentation"


class TestToolMessageExtraction:
    """
    E2E tests for extracting sources from ToolMessage (builtin tools).
    """

    def setup_method(self):
        """Reset singleton dependencies."""
        from mcp_server_langgraph.core.dependencies import reset_singleton_dependencies

        reset_singleton_dependencies()

    def teardown_method(self):
        """Force GC."""
        from mcp_server_langgraph.core.dependencies import reset_singleton_dependencies

        reset_singleton_dependencies()
        gc.collect()

    async def test_extract_from_markdown_links(self):
        """
        E2E: Verify sources are extracted from markdown link format.

        GIVEN: A ToolMessage with markdown links
        WHEN: extract_sources_from_tool_message is called
        THEN: Source citations are parsed correctly
        """
        from mcp_server_langgraph.tools.source_citation import (
            extract_sources_from_tool_message,
        )

        message = ToolMessage(
            content="""[Python.org](https://www.python.org/): Official Python website
[Real Python](https://realpython.com/): Python tutorials and guides
[Stack Overflow](https://stackoverflow.com/questions/tagged/python): Community Q&A""",
            name="web_search",
            tool_call_id="call-123",
        )

        sources = extract_sources_from_tool_message(message)

        assert len(sources) == 3
        assert sources[0].title == "Python.org"
        assert sources[0].url == "https://www.python.org/"
        assert sources[0].snippet == "Official Python website"
        assert sources[2].title == "Stack Overflow"

    async def test_only_extracts_from_web_search_tool(self):
        """
        E2E: Verify extraction only happens for web_search tool.

        GIVEN: A ToolMessage from a non-web_search tool
        WHEN: extract_sources_from_tool_message is called
        THEN: No sources are extracted
        """
        from mcp_server_langgraph.tools.source_citation import (
            extract_sources_from_tool_message,
        )

        message = ToolMessage(
            content="[Some Link](https://example.com/): Example",
            name="calculator",  # Not web_search
            tool_call_id="call-456",
        )

        sources = extract_sources_from_tool_message(message)

        assert len(sources) == 0


class TestKnowledgeBaseSources:
    """
    E2E tests for extracting sources from KB context.
    """

    def setup_method(self):
        """Reset singleton dependencies."""
        from mcp_server_langgraph.core.dependencies import reset_singleton_dependencies

        reset_singleton_dependencies()

    def teardown_method(self):
        """Force GC."""
        from mcp_server_langgraph.core.dependencies import reset_singleton_dependencies

        reset_singleton_dependencies()
        gc.collect()

    async def test_extract_from_kb_context(self):
        """
        E2E: Verify sources are extracted from KB context messages.

        GIVEN: SystemMessages with kb_reference metadata
        WHEN: extract_sources_from_kb_context is called
        THEN: Source citations are extracted with relevance scores
        """
        from mcp_server_langgraph.tools.source_citation import (
            extract_sources_from_kb_context,
        )

        messages = [
            SystemMessage(
                content="Context from KB document...",
                additional_kwargs={
                    "kb_reference": {
                        "title": "API Design Guidelines",
                        "url": "https://internal.docs/api-guidelines",
                        "source": "kb://docs/api-guidelines.md",
                        "relevance_score": 0.95,
                    }
                },
            ),
            SystemMessage(
                content="Another context...",
                additional_kwargs={
                    "kb_reference": {
                        "title": "Architecture Overview",
                        "source": "kb://docs/architecture.md",  # No URL, use source
                        "relevance_score": 0.82,
                    }
                },
            ),
        ]

        sources = extract_sources_from_kb_context(messages)

        assert len(sources) == 2
        assert sources[0].title == "API Design Guidelines"
        assert sources[0].url == "https://internal.docs/api-guidelines"
        assert sources[0].relevance_score == 0.95
        assert sources[1].url == "kb://docs/architecture.md"


class TestSourceCollectionAndDeduplication:
    """
    E2E tests for collecting and deduplicating sources.
    """

    def setup_method(self):
        """Reset singleton dependencies."""
        from mcp_server_langgraph.core.dependencies import reset_singleton_dependencies

        reset_singleton_dependencies()

    def teardown_method(self):
        """Force GC."""
        from mcp_server_langgraph.core.dependencies import reset_singleton_dependencies

        reset_singleton_dependencies()
        gc.collect()

    async def test_collect_from_mixed_messages(self, enable_source_citations):
        """
        E2E: Verify sources are collected from multiple message types.

        GIVEN: A list of mixed message types
        WHEN: collect_sources_from_messages is called
        THEN: All sources are collected and deduplicated
        """
        from mcp_server_langgraph.tools.source_citation import (
            collect_sources_from_messages,
        )

        messages = [
            AIMessage(
                content=[
                    {
                        "type": "web_search_results",
                        "results": [
                            {
                                "title": "Python Docs",
                                "url": "https://docs.python.org/",
                                "snippet": "Python documentation",
                            },
                        ],
                    },
                ]
            ),
            ToolMessage(
                content="[Python Docs](https://docs.python.org/): Same URL again",  # Duplicate
                name="web_search",
                tool_call_id="call-1",
            ),
            ToolMessage(
                content="[Real Python](https://realpython.com/): Unique source",
                name="web_search",
                tool_call_id="call-2",
            ),
        ]

        sources = collect_sources_from_messages(messages)

        # Should have 2 unique sources (duplicate URL removed)
        assert len(sources) == 2
        urls = {s.url for s in sources}
        assert "https://docs.python.org/" in urls
        assert "https://realpython.com/" in urls

    async def test_dedupe_by_domain(self):
        """
        E2E: Verify sources are deduplicated by domain.

        GIVEN: Multiple sources from the same domain
        WHEN: dedupe_by_domain is called
        THEN: Only first source per domain is kept
        """
        from mcp_server_langgraph.tools.source_citation import (
            SourceCitation,
            dedupe_by_domain,
        )

        sources = [
            SourceCitation(title="Page 1", url="https://example.com/page1"),
            SourceCitation(title="Page 2", url="https://example.com/page2"),
            SourceCitation(title="Other Site", url="https://other.com/page"),
            SourceCitation(title="Page 3", url="https://example.com/page3"),
        ]

        deduped = dedupe_by_domain(sources)

        assert len(deduped) == 2
        assert deduped[0].title == "Page 1"  # First from example.com
        assert deduped[1].title == "Other Site"  # First from other.com

    async def test_sort_by_relevance(self):
        """
        E2E: Verify sources are sorted by relevance score.

        GIVEN: Sources with various relevance scores
        WHEN: sort_sources_by_relevance is called
        THEN: Sources are sorted descending by relevance
        """
        from mcp_server_langgraph.tools.source_citation import (
            SourceCitation,
            sort_sources_by_relevance,
        )

        sources = [
            SourceCitation(title="Low", url="https://low.com/", relevance_score=0.3),
            SourceCitation(title="No Score", url="https://noscore.com/"),
            SourceCitation(title="High", url="https://high.com/", relevance_score=0.9),
            SourceCitation(title="Medium", url="https://medium.com/", relevance_score=0.6),
        ]

        sorted_sources = sort_sources_by_relevance(sources)

        assert sorted_sources[0].title == "High"  # 0.9
        assert sorted_sources[1].title == "Medium"  # 0.6
        assert sorted_sources[2].title == "Low"  # 0.3
        assert sorted_sources[3].title == "No Score"  # None (last)


class TestSourceCitationModel:
    """
    E2E tests for SourceCitation model functionality.
    """

    def setup_method(self):
        """Reset singleton dependencies."""
        from mcp_server_langgraph.core.dependencies import reset_singleton_dependencies

        reset_singleton_dependencies()

    def teardown_method(self):
        """Force GC."""
        from mcp_server_langgraph.core.dependencies import reset_singleton_dependencies

        reset_singleton_dependencies()
        gc.collect()

    async def test_truncated_snippet(self):
        """
        E2E: Verify snippet truncation works correctly.

        GIVEN: A source with a long snippet
        WHEN: truncated_snippet is called
        THEN: Snippet is truncated with ellipsis
        """
        from mcp_server_langgraph.tools.source_citation import SourceCitation

        long_snippet = "A" * 200  # 200 characters
        source = SourceCitation(
            title="Test",
            url="https://test.com/",
            snippet=long_snippet,
        )

        truncated = source.truncated_snippet(max_length=50)

        assert truncated is not None
        assert len(truncated) == 53  # 50 + "..."
        assert truncated.endswith("...")

    async def test_truncated_snippet_short_text(self):
        """
        E2E: Verify short snippets are not truncated.

        GIVEN: A source with a short snippet
        WHEN: truncated_snippet is called
        THEN: Snippet is returned unchanged
        """
        from mcp_server_langgraph.tools.source_citation import SourceCitation

        source = SourceCitation(
            title="Test",
            url="https://test.com/",
            snippet="Short snippet",
        )

        truncated = source.truncated_snippet(max_length=100)

        assert truncated == "Short snippet"

    async def test_extract_domain(self):
        """
        E2E: Verify domain extraction from URLs.

        GIVEN: Various URLs
        WHEN: extract_domain is called
        THEN: Domain is extracted correctly
        """
        from mcp_server_langgraph.tools.source_citation import extract_domain

        assert extract_domain("https://www.example.com/path/to/page") == "www.example.com"
        assert extract_domain("https://docs.python.org/3/library/") == "docs.python.org"
        assert extract_domain("http://localhost:8080/api") == "localhost"

    async def test_group_sources_by_domain(self):
        """
        E2E: Verify sources are grouped by domain.

        GIVEN: Multiple sources from different domains
        WHEN: group_sources_by_domain is called
        THEN: Sources are correctly grouped
        """
        from mcp_server_langgraph.tools.source_citation import (
            SourceCitation,
            group_sources_by_domain,
        )

        sources = [
            SourceCitation(title="Docs 1", url="https://docs.python.org/3/"),
            SourceCitation(title="Docs 2", url="https://docs.python.org/2/"),
            SourceCitation(title="PyPI", url="https://pypi.org/project/requests/"),
        ]

        grouped = group_sources_by_domain(sources)

        assert len(grouped) == 2
        assert len(grouped["docs.python.org"]) == 2
        assert len(grouped["pypi.org"]) == 1
