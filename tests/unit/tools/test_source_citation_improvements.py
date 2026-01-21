"""
Tests for Source Citation Improvements (TDD RED Phase).

This module tests:
1. Google Native Search format support
2. Knowledge Base citation extraction
3. Feature flag gating
4. Snippet truncation
5. Deduplication by domain
6. Source ranking by relevance
"""

import gc

import pytest
from langchain_core.messages import AIMessage, ToolMessage

pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="source_citation_improvements")
class TestGoogleNativeSearchFormat:
    """Tests for Google grounded search result extraction."""

    def teardown_method(self) -> None:
        """Force GC."""
        gc.collect()

    def test_extract_sources_from_google_grounding_metadata(self) -> None:
        """Should extract sources from Google grounding_metadata blocks."""
        from mcp_server_langgraph.tools.source_citation import (
            extract_sources_from_message,
        )

        # Google Vertex AI returns grounding metadata
        response = AIMessage(
            content=[
                {"type": "text", "text": "Based on search results:"},
                {
                    "type": "grounding_metadata",
                    "grounding_chunks": [
                        {
                            "web": {
                                "uri": "https://cloud.google.com/vertex-ai",
                                "title": "Vertex AI Documentation",
                            },
                        },
                        {
                            "web": {
                                "uri": "https://ai.google.dev",
                                "title": "Google AI for Developers",
                            },
                        },
                    ],
                    "grounding_supports": [
                        {
                            "segment": {"text": "Vertex AI is Google's ML platform."},
                            "grounding_chunk_indices": [0],
                        },
                    ],
                },
            ]
        )

        sources = extract_sources_from_message(response)

        assert len(sources) == 2
        assert sources[0].title == "Vertex AI Documentation"
        assert sources[0].url == "https://cloud.google.com/vertex-ai"
        assert sources[1].title == "Google AI for Developers"

    def test_extract_sources_from_google_search_entry_point(self) -> None:
        """Should extract sources from Google search_entry_point format."""
        from mcp_server_langgraph.tools.source_citation import (
            extract_sources_from_message,
        )

        response = AIMessage(
            content=[
                {
                    "type": "grounding_metadata",
                    "search_entry_point": {
                        "rendered_content": "Search results",
                    },
                    "grounding_chunks": [
                        {
                            "web": {
                                "uri": "https://example.com/result",
                                "title": "Example Result",
                            },
                        },
                    ],
                },
            ]
        )

        sources = extract_sources_from_message(response)

        assert len(sources) == 1
        assert sources[0].url == "https://example.com/result"

    def test_google_grounding_with_snippet_from_supports(self) -> None:
        """Should use grounding_supports text as snippet when available."""
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
                                "uri": "https://docs.python.org",
                                "title": "Python Docs",
                            },
                        },
                    ],
                    "grounding_supports": [
                        {
                            "segment": {"text": "Python is a programming language."},
                            "grounding_chunk_indices": [0],
                        },
                    ],
                },
            ]
        )

        sources = extract_sources_from_message(response)

        assert len(sources) == 1
        assert sources[0].snippet == "Python is a programming language."


@pytest.mark.xdist_group(name="source_citation_improvements")
class TestKnowledgeBaseCitations:
    """Tests for knowledge base reference extraction."""

    def teardown_method(self) -> None:
        """Force GC."""
        gc.collect()

    def test_extract_sources_from_kb_context_message(self) -> None:
        """Should extract sources from KB context system messages."""
        from langchain_core.messages import SystemMessage

        from mcp_server_langgraph.tools.source_citation import (
            extract_sources_from_kb_context,
        )

        # KB context messages have reference metadata
        context_msg = SystemMessage(
            content="Reference from knowledge base:\n\nContent here...",
            additional_kwargs={
                "kb_reference": {
                    "title": "API Documentation",
                    "source": "docs/api.md",
                    "url": "/kb/docs/api.md",
                    "relevance_score": 0.92,
                },
            },
        )

        sources = extract_sources_from_kb_context([context_msg])

        assert len(sources) == 1
        assert sources[0].title == "API Documentation"
        assert sources[0].url == "/kb/docs/api.md"

    def test_extract_multiple_kb_references(self) -> None:
        """Should extract multiple KB references from context messages."""
        from langchain_core.messages import SystemMessage

        from mcp_server_langgraph.tools.source_citation import (
            extract_sources_from_kb_context,
        )

        messages = [
            SystemMessage(
                content="First reference",
                additional_kwargs={
                    "kb_reference": {
                        "title": "Doc 1",
                        "source": "doc1.md",
                        "url": "/kb/doc1.md",
                    },
                },
            ),
            SystemMessage(
                content="Second reference",
                additional_kwargs={
                    "kb_reference": {
                        "title": "Doc 2",
                        "source": "doc2.md",
                        "url": "/kb/doc2.md",
                    },
                },
            ),
        ]

        sources = extract_sources_from_kb_context(messages)

        assert len(sources) == 2


@pytest.mark.xdist_group(name="source_citation_improvements")
class TestFeatureFlagGating:
    """Tests for FF_ENABLE_SOURCE_CITATIONS feature flag."""

    def teardown_method(self) -> None:
        """Force GC."""
        gc.collect()

    def test_feature_flag_exists(self) -> None:
        """FF_ENABLE_SOURCE_CITATIONS should exist in FeatureFlags."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert hasattr(flags, "enable_source_citations")

    def test_feature_flag_default_true(self) -> None:
        """Source citations should be enabled by default."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert flags.enable_source_citations is True

    def test_feature_flag_env_var(self, monkeypatch) -> None:
        """FF_ENABLE_SOURCE_CITATIONS env var should control flag."""
        monkeypatch.setenv("FF_ENABLE_SOURCE_CITATIONS", "false")

        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert flags.enable_source_citations is False

    def test_collect_sources_respects_feature_flag(self, monkeypatch) -> None:
        """collect_sources_from_messages should return empty when disabled."""
        from mcp_server_langgraph.core.feature_flags import feature_flags
        from mcp_server_langgraph.tools.source_citation import (
            collect_sources_from_messages,
        )

        # Mock the singleton's attribute directly
        monkeypatch.setattr(feature_flags, "enable_source_citations", False)

        messages = [
            ToolMessage(
                content="[Result](https://example.com): Snippet",
                tool_call_id="ws_1",
                name="web_search",
            ),
        ]

        sources = collect_sources_from_messages(messages)

        # When feature flag is off, should return empty
        # (Implementation checks feature_flags.enable_source_citations)
        assert sources == []


@pytest.mark.xdist_group(name="source_citation_improvements")
class TestSnippetTruncation:
    """Tests for snippet length truncation."""

    def teardown_method(self) -> None:
        """Force GC."""
        gc.collect()

    def test_truncate_long_snippet(self) -> None:
        """Should truncate snippets longer than max length."""
        from mcp_server_langgraph.tools.source_citation import SourceCitation

        long_snippet = "A" * 200  # 200 characters

        citation = SourceCitation(
            title="Test",
            url="https://example.com",
            snippet=long_snippet,
        )

        # Truncated snippet should be max 150 chars + ellipsis
        truncated = citation.truncated_snippet(max_length=150)
        assert len(truncated) <= 153  # 150 + "..."
        assert truncated.endswith("...")

    def test_short_snippet_not_truncated(self) -> None:
        """Should not truncate snippets within limit."""
        from mcp_server_langgraph.tools.source_citation import SourceCitation

        short_snippet = "A short snippet"

        citation = SourceCitation(
            title="Test",
            url="https://example.com",
            snippet=short_snippet,
        )

        truncated = citation.truncated_snippet(max_length=150)
        assert truncated == short_snippet
        assert not truncated.endswith("...")

    def test_none_snippet_returns_none(self) -> None:
        """Should return None for None snippet."""
        from mcp_server_langgraph.tools.source_citation import SourceCitation

        citation = SourceCitation(
            title="Test",
            url="https://example.com",
            snippet=None,
        )

        truncated = citation.truncated_snippet(max_length=150)
        assert truncated is None


@pytest.mark.xdist_group(name="source_citation_improvements")
class TestDedupeByDomain:
    """Tests for domain-based deduplication."""

    def teardown_method(self) -> None:
        """Force GC."""
        gc.collect()

    def test_group_sources_by_domain(self) -> None:
        """Should group sources by their domain."""
        from mcp_server_langgraph.tools.source_citation import (
            SourceCitation,
            group_sources_by_domain,
        )

        sources = [
            SourceCitation(title="Page 1", url="https://docs.python.org/tutorial"),
            SourceCitation(title="Page 2", url="https://docs.python.org/reference"),
            SourceCitation(title="Real Python", url="https://realpython.com/guide"),
        ]

        grouped = group_sources_by_domain(sources)

        assert len(grouped) == 2  # Two domains
        assert "docs.python.org" in grouped
        assert "realpython.com" in grouped
        assert len(grouped["docs.python.org"]) == 2
        assert len(grouped["realpython.com"]) == 1

    def test_dedupe_keep_first_per_domain(self) -> None:
        """Should keep only first source per domain when deduping."""
        from mcp_server_langgraph.tools.source_citation import (
            SourceCitation,
            dedupe_by_domain,
        )

        sources = [
            SourceCitation(title="First", url="https://example.com/page1"),
            SourceCitation(title="Second", url="https://example.com/page2"),
            SourceCitation(title="Other", url="https://other.com/page"),
        ]

        deduped = dedupe_by_domain(sources)

        assert len(deduped) == 2
        assert deduped[0].title == "First"  # First from example.com
        assert deduped[1].title == "Other"  # First from other.com

    def test_extract_domain_from_url(self) -> None:
        """Should correctly extract domain from various URL formats."""
        from mcp_server_langgraph.tools.source_citation import extract_domain

        assert extract_domain("https://example.com/path") == "example.com"
        assert extract_domain("http://sub.example.com/path") == "sub.example.com"
        assert extract_domain("https://example.com:8080/path") == "example.com"
        assert extract_domain("invalid-url") == "invalid-url"


@pytest.mark.xdist_group(name="source_citation_improvements")
class TestSourceRanking:
    """Tests for source ranking by relevance."""

    def teardown_method(self) -> None:
        """Force GC."""
        gc.collect()

    def test_sort_sources_by_relevance_score(self) -> None:
        """Should sort sources by relevance_score descending."""
        from mcp_server_langgraph.tools.source_citation import (
            SourceCitation,
            sort_sources_by_relevance,
        )

        sources = [
            SourceCitation(
                title="Low",
                url="https://low.com",
                relevance_score=0.3,
            ),
            SourceCitation(
                title="High",
                url="https://high.com",
                relevance_score=0.9,
            ),
            SourceCitation(
                title="Medium",
                url="https://medium.com",
                relevance_score=0.6,
            ),
        ]

        sorted_sources = sort_sources_by_relevance(sources)

        assert sorted_sources[0].title == "High"
        assert sorted_sources[1].title == "Medium"
        assert sorted_sources[2].title == "Low"

    def test_sources_without_score_sorted_last(self) -> None:
        """Sources without relevance_score should be sorted last."""
        from mcp_server_langgraph.tools.source_citation import (
            SourceCitation,
            sort_sources_by_relevance,
        )

        sources = [
            SourceCitation(title="No Score", url="https://noscore.com"),
            SourceCitation(
                title="Has Score",
                url="https://hasscore.com",
                relevance_score=0.5,
            ),
        ]

        sorted_sources = sort_sources_by_relevance(sources)

        assert sorted_sources[0].title == "Has Score"
        assert sorted_sources[1].title == "No Score"

    def test_source_citation_has_relevance_score_field(self) -> None:
        """SourceCitation should have optional relevance_score field."""
        from mcp_server_langgraph.tools.source_citation import SourceCitation

        # Without score
        citation1 = SourceCitation(title="Test", url="https://example.com")
        assert citation1.relevance_score is None

        # With score
        citation2 = SourceCitation(
            title="Test",
            url="https://example.com",
            relevance_score=0.85,
        )
        assert citation2.relevance_score == 0.85
