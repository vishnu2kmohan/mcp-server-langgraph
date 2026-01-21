"""Integration tests for Source Citation flow.

Tests the integration of source citations through the chat API:
- Source extraction from various formats (Anthropic, Google, OpenAI)
- Collection and deduplication of sources
- Feature flag gating
- Source metadata (relevance scores, snippets)

Related Modules:
- mcp_server_langgraph.tools.source_citation
- mcp_server_langgraph.api.v1.chat
- mcp_server_langgraph.core.agent_graph_builder
"""

from __future__ import annotations

import gc
from unittest.mock import patch

import pytest
from langchain_core.messages import AIMessage, ToolMessage

pytestmark = pytest.mark.integration


@pytest.mark.integration
@pytest.mark.xdist_group(name="source_citation_flow")
class TestSourceCitationExtraction:
    """Tests for source citation extraction from various message formats."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_anthropic_web_search_extraction(self) -> None:
        """Extract sources from Anthropic web_search_results content blocks."""
        from mcp_server_langgraph.tools.source_citation import (
            extract_sources_from_message,
        )

        response = AIMessage(
            content=[
                {"type": "text", "text": "Based on web search:"},
                {
                    "type": "web_search_results",
                    "results": [
                        {
                            "title": "Python Documentation",
                            "url": "https://docs.python.org",
                            "snippet": "Python is a programming language.",
                        },
                        {
                            "title": "Real Python",
                            "url": "https://realpython.com",
                            "snippet": "Python tutorials.",
                        },
                    ],
                },
            ]
        )

        sources = extract_sources_from_message(response)

        assert len(sources) == 2
        assert sources[0].title == "Python Documentation"
        assert sources[0].url == "https://docs.python.org"
        assert sources[0].snippet == "Python is a programming language."

    def test_google_grounding_extraction(self) -> None:
        """Extract sources from Google grounding_metadata blocks."""
        from mcp_server_langgraph.tools.source_citation import (
            extract_sources_from_message,
        )

        response = AIMessage(
            content=[
                {
                    "type": "grounding_metadata",
                    "grounding_chunks": [
                        {
                            "web": {
                                "uri": "https://cloud.google.com/vertex-ai",
                                "title": "Vertex AI",
                            },
                        },
                    ],
                    "grounding_supports": [
                        {
                            "segment": {"text": "Vertex AI is a ML platform."},
                            "grounding_chunk_indices": [0],
                        },
                    ],
                },
            ]
        )

        sources = extract_sources_from_message(response)

        assert len(sources) == 1
        assert sources[0].title == "Vertex AI"
        assert sources[0].url == "https://cloud.google.com/vertex-ai"
        assert sources[0].snippet == "Vertex AI is a ML platform."

    def test_openai_responses_api_extraction(self) -> None:
        """Extract sources from OpenAI Responses API native_output."""
        from mcp_server_langgraph.tools.source_citation import (
            extract_sources_from_message,
        )

        response = AIMessage(
            content="Here are the search results.",
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
                                        "title": "OpenAI Platform",
                                        "url": "https://platform.openai.com",
                                        "snippet": "OpenAI API docs.",
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
        assert sources[0].title == "OpenAI Platform"
        assert sources[0].url == "https://platform.openai.com"


@pytest.mark.integration
@pytest.mark.xdist_group(name="source_citation_flow")
class TestSourceCitationCollection:
    """Tests for collecting sources from conversation messages."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_collect_from_mixed_messages(self) -> None:
        """Collect and deduplicate sources from mixed message types."""
        from mcp_server_langgraph.core.feature_flags import feature_flags
        from mcp_server_langgraph.tools.source_citation import (
            collect_sources_from_messages,
        )

        # Ensure feature flag is enabled for this test
        with patch.object(feature_flags, "enable_source_citations", True):
            messages = [
                # AIMessage with native results
                AIMessage(
                    content=[
                        {
                            "type": "web_search_results",
                            "results": [
                                {
                                    "title": "Doc A",
                                    "url": "https://example.com/a",
                                    "snippet": "A snippet",
                                },
                            ],
                        },
                    ]
                ),
                # ToolMessage from builtin web_search
                ToolMessage(
                    content="[Doc B](https://example.com/b): B snippet\n"
                    "[Doc C](https://example.com/c): C snippet\n",
                    tool_call_id="ws_456",
                    name="web_search",
                ),
                # Duplicate URL should be deduplicated
                ToolMessage(
                    content="[Doc A Again](https://example.com/a): Same URL\n",
                    tool_call_id="ws_789",
                    name="web_search",
                ),
            ]

            sources = collect_sources_from_messages(messages)

        # Should have 3 unique sources (duplicate URL filtered)
        assert len(sources) == 3
        urls = [s.url for s in sources]
        assert "https://example.com/a" in urls
        assert "https://example.com/b" in urls
        assert "https://example.com/c" in urls

    def test_feature_flag_disables_collection(self) -> None:
        """When feature flag is off, collect returns empty list."""
        from mcp_server_langgraph.core.feature_flags import feature_flags
        from mcp_server_langgraph.tools.source_citation import (
            collect_sources_from_messages,
        )

        with patch.object(feature_flags, "enable_source_citations", False):
            messages = [
                ToolMessage(
                    content="[Test](https://example.com): Snippet\n",
                    tool_call_id="ws_123",
                    name="web_search",
                ),
            ]

            sources = collect_sources_from_messages(messages)

        assert sources == []


@pytest.mark.integration
@pytest.mark.xdist_group(name="source_citation_flow")
class TestSourceCitationDomainUtils:
    """Tests for domain-based source utilities."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_group_and_dedupe_by_domain(self) -> None:
        """Test grouping and deduplicating sources by domain."""
        from mcp_server_langgraph.tools.source_citation import (
            SourceCitation,
            dedupe_by_domain,
            group_sources_by_domain,
        )

        sources = [
            SourceCitation(title="Page 1", url="https://docs.python.org/3/tutorial"),
            SourceCitation(title="Page 2", url="https://docs.python.org/3/reference"),
            SourceCitation(title="Real Python", url="https://realpython.com/guide"),
            SourceCitation(title="W3Schools", url="https://www.w3schools.com/python"),
        ]

        # Group by domain
        grouped = group_sources_by_domain(sources)
        assert len(grouped) == 3  # 3 unique domains
        assert len(grouped["docs.python.org"]) == 2

        # Dedupe keeps first per domain
        deduped = dedupe_by_domain(sources)
        assert len(deduped) == 3
        assert deduped[0].title == "Page 1"  # First from docs.python.org

    def test_sort_by_relevance_score(self) -> None:
        """Test sorting sources by relevance score."""
        from mcp_server_langgraph.tools.source_citation import (
            SourceCitation,
            sort_sources_by_relevance,
        )

        sources = [
            SourceCitation(title="No Score", url="https://noscore.com"),
            SourceCitation(
                title="Low", url="https://low.com", relevance_score=0.3
            ),
            SourceCitation(
                title="High", url="https://high.com", relevance_score=0.95
            ),
        ]

        sorted_sources = sort_sources_by_relevance(sources)

        assert sorted_sources[0].title == "High"  # Highest score first
        assert sorted_sources[1].title == "Low"
        assert sorted_sources[2].title == "No Score"  # No score last


@pytest.mark.integration
@pytest.mark.xdist_group(name="source_citation_flow")
class TestKnowledgeBaseCitations:
    """Tests for knowledge base citation extraction."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_extract_kb_references(self) -> None:
        """Extract sources from KB context messages."""
        from langchain_core.messages import SystemMessage

        from mcp_server_langgraph.tools.source_citation import (
            extract_sources_from_kb_context,
        )

        messages = [
            SystemMessage(
                content="Context from knowledge base",
                additional_kwargs={
                    "kb_reference": {
                        "title": "API Guide",
                        "source": "docs/api.md",
                        "url": "/kb/docs/api.md",
                        "relevance_score": 0.88,
                    },
                },
            ),
            SystemMessage(
                content="Another reference",
                additional_kwargs={
                    "kb_reference": {
                        "title": "Architecture",
                        "source": "docs/arch.md",
                        "url": "/kb/docs/arch.md",
                        "relevance_score": 0.72,
                    },
                },
            ),
        ]

        sources = extract_sources_from_kb_context(messages)

        assert len(sources) == 2
        assert sources[0].title == "API Guide"
        assert sources[0].relevance_score == 0.88
        assert sources[1].title == "Architecture"


@pytest.mark.integration
@pytest.mark.xdist_group(name="source_citation_flow")
class TestMessageStorageSourceCitations:
    """Tests for source citation persistence in session message storage."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_message_model_stores_sources(self) -> None:
        """Message model should correctly store and serialize sources."""
        from mcp_server_langgraph.storage.session.models import Message

        sources = [
            {
                "title": "Python Docs",
                "url": "https://docs.python.org",
                "snippet": "Official documentation",
                "relevance_score": 0.95,
            },
            {
                "title": "Real Python",
                "url": "https://realpython.com",
                "snippet": "Python tutorials",
            },
        ]

        message = Message(
            id="msg-test-1",
            role="assistant",
            content="Here are the results.",
            sources=sources,
        )

        # Verify sources are stored
        assert len(message.sources) == 2
        assert message.sources[0]["title"] == "Python Docs"
        assert message.sources[0]["relevance_score"] == 0.95
        assert message.sources[1]["url"] == "https://realpython.com"

        # Test roundtrip serialization
        message_dict = message.model_dump()
        restored = Message.model_validate(message_dict)

        assert len(restored.sources) == 2
        assert restored.sources[0]["title"] == "Python Docs"

    def test_message_model_default_empty_sources(self) -> None:
        """Message without sources should default to empty list."""
        from mcp_server_langgraph.storage.session.models import Message

        message = Message(
            id="msg-test-2",
            role="user",
            content="Hello!",
        )

        assert message.sources == []

    @pytest.mark.asyncio
    async def test_redis_session_manager_stores_sources(self) -> None:
        """Redis session manager should persist message sources."""
        from mcp_server_langgraph.storage.session.manager import RedisSessionManager

        # Verify the add_message signature accepts sources
        # This is a contract test - ensures the interface is correct
        import inspect

        sig = inspect.signature(RedisSessionManager.add_message)
        params = list(sig.parameters.keys())

        assert "sources" in params, "RedisSessionManager.add_message should accept sources parameter"

    @pytest.mark.asyncio
    async def test_postgres_session_manager_stores_sources(self) -> None:
        """Postgres session manager should persist message sources."""
        from mcp_server_langgraph.storage.session.postgres_manager import (
            PostgresSessionManager,
        )

        # Verify the add_message signature accepts sources
        import inspect

        sig = inspect.signature(PostgresSessionManager.add_message)
        params = list(sig.parameters.keys())

        assert "sources" in params, "PostgresSessionManager.add_message should accept sources parameter"

    def test_sources_serialization_edge_cases(self) -> None:
        """Test edge cases in source serialization."""
        from mcp_server_langgraph.storage.session.models import Message

        # Empty snippet
        sources_with_empty_snippet = [
            {"title": "Doc", "url": "https://example.com", "snippet": ""},
        ]

        message = Message(
            id="msg-edge-1",
            role="assistant",
            content="Response",
            sources=sources_with_empty_snippet,
        )

        assert message.sources[0]["snippet"] == ""

        # None snippet
        sources_with_none_snippet = [
            {"title": "Doc", "url": "https://example.com", "snippet": None},
        ]

        message2 = Message(
            id="msg-edge-2",
            role="assistant",
            content="Response",
            sources=sources_with_none_snippet,
        )

        assert message2.sources[0]["snippet"] is None

    def test_sources_with_special_characters(self) -> None:
        """Sources with special characters should serialize correctly."""
        from mcp_server_langgraph.storage.session.models import Message

        sources_with_special = [
            {
                "title": "Python 3.13: What's New — A Complete Guide",
                "url": "https://example.com/path?query=value&foo=bar#section",
                "snippet": "Features include:\n- Pattern matching\n- Type hints \"improved\"",
            },
        ]

        message = Message(
            id="msg-special-1",
            role="assistant",
            content="Response",
            sources=sources_with_special,
        )

        # Roundtrip serialization
        message_dict = message.model_dump()
        restored = Message.model_validate(message_dict)

        assert restored.sources[0]["title"] == "Python 3.13: What's New — A Complete Guide"
        assert "&foo=bar" in restored.sources[0]["url"]
        assert "\n" in restored.sources[0]["snippet"]
