"""
Tests for Source Citation Extraction (TDD RED Phase).

This module tests the extraction of source citations from:
- Native web search tool results (Anthropic, Google, OpenAI)
- Builtin web_search tool results
- Tool messages with markdown link format

Citations should be extracted and attached to assistant messages
for display in the frontend chat UI.
"""

import gc

import pytest
from langchain_core.messages import AIMessage, ToolMessage

pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="source_citation_extraction")
class TestExtractSourcesFromNativeResults:
    """Tests for extracting sources from native tool results."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_extract_sources_from_anthropic_web_search_results(self) -> None:
        """Should extract sources from Anthropic web_search_results content blocks."""
        from mcp_server_langgraph.tools.source_citation import (
            SourceCitation,
            extract_sources_from_message,
        )

        # Anthropic returns web_search_results in content blocks
        response = AIMessage(
            content=[
                {"type": "text", "text": "Based on my search, here's what I found:"},
                {
                    "type": "web_search_results",
                    "results": [
                        {
                            "title": "Python Documentation",
                            "url": "https://docs.python.org/3/",
                            "snippet": "Welcome to Python 3 documentation.",
                        },
                        {
                            "title": "Real Python Tutorials",
                            "url": "https://realpython.com/",
                            "snippet": "Learn Python programming.",
                        },
                    ],
                },
            ]
        )

        sources = extract_sources_from_message(response)

        assert len(sources) == 2
        assert isinstance(sources[0], SourceCitation)
        assert sources[0].title == "Python Documentation"
        assert sources[0].url == "https://docs.python.org/3/"
        assert sources[0].snippet == "Welcome to Python 3 documentation."
        assert sources[1].title == "Real Python Tutorials"

    def test_extract_sources_from_openai_responses_api(self) -> None:
        """Should extract sources from OpenAI Responses API native_output."""
        from mcp_server_langgraph.tools.source_citation import (
            extract_sources_from_message,
        )

        # OpenAI Responses API stores results in additional_kwargs["native_output"]
        response = AIMessage(
            content="Here's what I found from my web search.",
            additional_kwargs={
                "native_output": [
                    {
                        "type": "message",
                        "content": [
                            {
                                "type": "web_search_call",
                                "id": "ws_123",
                                "results": [
                                    {
                                        "title": "OpenAI API Docs",
                                        "url": "https://platform.openai.com/docs",
                                        "snippet": "OpenAI API documentation.",
                                    },
                                ],
                            },
                        ],
                    },
                ],
            },
        )

        sources = extract_sources_from_message(response)

        assert len(sources) == 1
        assert sources[0].title == "OpenAI API Docs"
        assert sources[0].url == "https://platform.openai.com/docs"
        assert sources[0].snippet == "OpenAI API documentation."

    def test_extract_sources_from_openai_direct_web_search_call(self) -> None:
        """Should extract sources from direct web_search_call items in native_output."""
        from mcp_server_langgraph.tools.source_citation import (
            extract_sources_from_message,
        )

        response = AIMessage(
            content="Search results below.",
            additional_kwargs={
                "native_output": [
                    {
                        "type": "web_search_call",
                        "id": "ws_456",
                        "results": [
                            {
                                "title": "GitHub",
                                "url": "https://github.com",
                                "snippet": "Build software together.",
                            },
                            {
                                "title": "GitLab",
                                "url": "https://gitlab.com",
                                "snippet": "DevSecOps platform.",
                            },
                        ],
                    },
                ],
            },
        )

        sources = extract_sources_from_message(response)

        assert len(sources) == 2
        assert sources[0].title == "GitHub"
        assert sources[1].title == "GitLab"

    def test_extract_sources_returns_empty_for_no_results(self) -> None:
        """Should return empty list when no web search results."""
        from mcp_server_langgraph.tools.source_citation import (
            extract_sources_from_message,
        )

        response = AIMessage(content="Just a regular response without search.")

        sources = extract_sources_from_message(response)

        assert sources == []

    def test_extract_sources_handles_missing_fields(self) -> None:
        """Should handle missing optional fields gracefully."""
        from mcp_server_langgraph.tools.source_citation import (
            extract_sources_from_message,
        )

        response = AIMessage(
            content=[
                {
                    "type": "web_search_results",
                    "results": [
                        {
                            "title": "Minimal Result",
                            "url": "https://example.com",
                            # No snippet
                        },
                    ],
                },
            ]
        )

        sources = extract_sources_from_message(response)

        assert len(sources) == 1
        assert sources[0].title == "Minimal Result"
        assert sources[0].url == "https://example.com"
        assert sources[0].snippet is None


@pytest.mark.xdist_group(name="source_citation_extraction")
class TestExtractSourcesFromToolMessages:
    """Tests for extracting sources from ToolMessage content."""

    def teardown_method(self) -> None:
        """Force GC."""
        gc.collect()

    def test_extract_sources_from_markdown_links(self) -> None:
        """Should extract sources from markdown link format in ToolMessage."""
        from mcp_server_langgraph.tools.source_citation import (
            extract_sources_from_tool_message,
        )

        # Format used by builtin web_search and parse_native_results
        tool_msg = ToolMessage(
            content="[Python Docs](https://docs.python.org): Official documentation.\n"
            "[Real Python](https://realpython.com): Tutorials and guides.",
            tool_call_id="web_search_123",
            name="web_search",
        )

        sources = extract_sources_from_tool_message(tool_msg)

        assert len(sources) == 2
        assert sources[0].title == "Python Docs"
        assert sources[0].url == "https://docs.python.org"
        assert sources[0].snippet == "Official documentation."
        assert sources[1].title == "Real Python"
        assert sources[1].url == "https://realpython.com"
        assert sources[1].snippet == "Tutorials and guides."

    def test_extract_sources_only_for_web_search_tool(self) -> None:
        """Should only extract sources from web_search tool messages."""
        from mcp_server_langgraph.tools.source_citation import (
            extract_sources_from_tool_message,
        )

        # Non-web_search tool should return empty
        tool_msg = ToolMessage(
            content="Some calculation result: 42",
            tool_call_id="calc_123",
            name="calculator",
        )

        sources = extract_sources_from_tool_message(tool_msg)

        assert sources == []

    def test_extract_sources_handles_empty_content(self) -> None:
        """Should handle empty content gracefully."""
        from mcp_server_langgraph.tools.source_citation import (
            extract_sources_from_tool_message,
        )

        tool_msg = ToolMessage(
            content="",
            tool_call_id="web_search_empty",
            name="web_search",
        )

        sources = extract_sources_from_tool_message(tool_msg)

        assert sources == []

    def test_extract_sources_handles_malformed_markdown(self) -> None:
        """Should handle malformed markdown links gracefully."""
        from mcp_server_langgraph.tools.source_citation import (
            extract_sources_from_tool_message,
        )

        tool_msg = ToolMessage(
            content="[Broken Link(https://example.com: no closing bracket\n[Valid](https://valid.com): This one works.",
            tool_call_id="web_search_malformed",
            name="web_search",
        )

        sources = extract_sources_from_tool_message(tool_msg)

        # Should extract the valid one, skip the malformed
        assert len(sources) == 1
        assert sources[0].title == "Valid"


@pytest.mark.xdist_group(name="source_citation_extraction")
class TestSourceCitationModel:
    """Tests for SourceCitation Pydantic model."""

    def teardown_method(self) -> None:
        """Force GC."""
        gc.collect()

    def test_source_citation_required_fields(self) -> None:
        """SourceCitation should require title and url."""
        from mcp_server_langgraph.tools.source_citation import SourceCitation

        citation = SourceCitation(title="Test", url="https://example.com")

        assert citation.title == "Test"
        assert citation.url == "https://example.com"
        assert citation.snippet is None

    def test_source_citation_with_snippet(self) -> None:
        """SourceCitation should accept optional snippet."""
        from mcp_server_langgraph.tools.source_citation import SourceCitation

        citation = SourceCitation(
            title="Test",
            url="https://example.com",
            snippet="A test snippet.",
        )

        assert citation.snippet == "A test snippet."

    def test_source_citation_serialization(self) -> None:
        """SourceCitation should serialize to dict properly."""
        from mcp_server_langgraph.tools.source_citation import SourceCitation

        citation = SourceCitation(
            title="Test",
            url="https://example.com",
            snippet="Snippet text.",
        )

        data = citation.model_dump()

        assert data == {
            "title": "Test",
            "url": "https://example.com",
            "snippet": "Snippet text.",
            "relevance_score": None,
        }


@pytest.mark.xdist_group(name="source_citation_extraction")
class TestCollectSourcesFromConversation:
    """Tests for collecting sources from a conversation's messages."""

    def teardown_method(self) -> None:
        """Force GC."""
        gc.collect()

    def test_collect_sources_from_messages_list(self) -> None:
        """Should collect all sources from a list of messages."""
        from langchain_core.messages import HumanMessage

        from mcp_server_langgraph.tools.source_citation import (
            collect_sources_from_messages,
        )

        messages = [
            HumanMessage(content="What is Python?"),
            ToolMessage(
                content="[Python.org](https://python.org): Official site.",
                tool_call_id="ws_1",
                name="web_search",
            ),
            AIMessage(content="Python is a programming language."),
            ToolMessage(
                content="[Tutorial](https://tutorial.com): Learn Python.",
                tool_call_id="ws_2",
                name="web_search",
            ),
        ]

        sources = collect_sources_from_messages(messages)

        assert len(sources) == 2
        assert sources[0].title == "Python.org"
        assert sources[1].title == "Tutorial"

    def test_collect_sources_deduplicates_by_url(self) -> None:
        """Should deduplicate sources with the same URL."""
        from mcp_server_langgraph.tools.source_citation import (
            collect_sources_from_messages,
        )

        messages = [
            ToolMessage(
                content="[Python](https://python.org): First mention.",
                tool_call_id="ws_1",
                name="web_search",
            ),
            ToolMessage(
                content="[Python.org](https://python.org): Second mention.",
                tool_call_id="ws_2",
                name="web_search",
            ),
        ]

        sources = collect_sources_from_messages(messages)

        # Same URL should be deduplicated
        assert len(sources) == 1
        assert sources[0].url == "https://python.org"

    def test_collect_sources_includes_native_and_tool_results(self) -> None:
        """Should collect from both native AIMessage results and ToolMessages."""
        from mcp_server_langgraph.tools.source_citation import (
            collect_sources_from_messages,
        )

        messages = [
            # Native web search in AIMessage
            AIMessage(
                content=[
                    {
                        "type": "web_search_results",
                        "results": [
                            {
                                "title": "Native Result",
                                "url": "https://native.com",
                                "snippet": "From native tool.",
                            },
                        ],
                    },
                ]
            ),
            # Builtin web search in ToolMessage
            ToolMessage(
                content="[Builtin Result](https://builtin.com): From builtin tool.",
                tool_call_id="ws_1",
                name="web_search",
            ),
        ]

        sources = collect_sources_from_messages(messages)

        assert len(sources) == 2
        urls = {s.url for s in sources}
        assert "https://native.com" in urls
        assert "https://builtin.com" in urls
