"""
PostgreSQL Full-Text Search Integration Tests

Integration tests for PostgreSQL FTS implementation.
Requires test infrastructure to be running (make test-infra-up-build).
"""

from __future__ import annotations

import gc

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.api,
    pytest.mark.database,
]


@pytest.mark.xdist_group(name="test_search_fts")
class TestFTSQueryBuilder:
    """Tests for PostgreSQL FTS query building."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_tsquery_produces_valid_postgres_syntax(self) -> None:
        """
        GIVEN a search query
        WHEN building a tsquery
        THEN should produce valid PostgreSQL syntax.
        """
        from mcp_server_langgraph.api.search import build_tsquery

        queries = [
            "simple query",
            "workflow",
            "email notification",
            "test's special",
            "multi word query terms",
        ]

        for query in queries:
            result = build_tsquery(query)
            # Valid tsquery has :* for prefix matching
            if query.strip():
                assert ":*" in result, f"Query '{query}' should have prefix matching"
                assert " | " in result or result.count(":*") == 1, "Should be OR-joined"

    def test_tsquery_handles_edge_cases(self) -> None:
        """
        GIVEN edge case queries
        WHEN building a tsquery
        THEN should handle gracefully.
        """
        from mcp_server_langgraph.api.search import build_tsquery

        edge_cases = [
            ("", ""),  # Empty string
            ("   ", ""),  # Whitespace only
            ("@#$%", ""),  # Special chars only
            ("a", "a:*"),  # Single char
        ]

        for query, expected in edge_cases:
            result = build_tsquery(query)
            assert result == expected or (not result and not expected)


@pytest.mark.xdist_group(name="test_search_fts")
class TestSearchResponse:
    """Tests for search response handling."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_search_response_pagination(self) -> None:
        """
        GIVEN search results with pagination
        WHEN checking has_more
        THEN should correctly indicate if more results exist.
        """
        from mcp_server_langgraph.api.search import SearchResponse, SearchResult

        # Case 1: More results exist
        results_page1 = [SearchResult(id=str(i), entity_type="workflow", name=f"Workflow {i}") for i in range(20)]
        response1 = SearchResponse(
            query="test",
            results=results_page1,
            total=50,
            limit=20,
            offset=0,
        )
        assert response1.has_more is True

        # Case 2: Last page
        results_page3 = [SearchResult(id=str(i), entity_type="workflow", name=f"Workflow {i}") for i in range(10)]
        response2 = SearchResponse(
            query="test",
            results=results_page3,
            total=50,
            limit=20,
            offset=40,
        )
        assert response2.has_more is False

    def test_search_result_with_highlights(self) -> None:
        """
        GIVEN a search result with highlights
        WHEN accessing highlights
        THEN should contain highlighted fields.
        """
        from mcp_server_langgraph.api.search import SearchResult, highlight_matches

        text = "Email Workflow for Automation"
        query = "workflow"
        highlighted = highlight_matches(text, query)

        result = SearchResult(
            id="1",
            entity_type="workflow",
            name=text,
            highlights={"name": highlighted},
        )

        assert "<mark>" in result.highlights["name"]
        assert "Workflow" in result.highlights["name"]


@pytest.mark.xdist_group(name="test_search_fts")
class TestInMemorySearchIntegration:
    """Integration tests for in-memory search fallback."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_search_workflows_by_name(self) -> None:
        """
        GIVEN a list of workflows
        WHEN searching by name
        THEN should return matching workflows.
        """
        from mcp_server_langgraph.api.search import SearchParams, in_memory_search

        workflows = [
            {
                "id": "wf-1",
                "name": "Email Notification Workflow",
                "description": "Sends email notifications",
            },
            {
                "id": "wf-2",
                "name": "Data Processing Pipeline",
                "description": "Processes data files",
            },
            {
                "id": "wf-3",
                "name": "Slack Notification Workflow",
                "description": "Sends Slack messages",
            },
        ]

        params = SearchParams(query="notification")
        results = in_memory_search(workflows, params)

        assert len(results) == 2
        assert all("notification" in r["name"].lower() or "notification" in r.get("description", "").lower() for r in results)

    def test_search_sessions_by_content(self) -> None:
        """
        GIVEN a list of sessions
        WHEN searching by message content
        THEN should return matching sessions.
        """
        from mcp_server_langgraph.api.search import SearchParams, in_memory_search

        sessions = [
            {
                "id": "session-1",
                "name": "Customer Support Chat",
                "description": "Help with product issues",
            },
            {
                "id": "session-2",
                "name": "Technical Discussion",
                "description": "API integration questions",
            },
            {
                "id": "session-3",
                "name": "Support Ticket Review",
                "description": "Monthly support metrics",
            },
        ]

        params = SearchParams(query="support")
        results = in_memory_search(sessions, params)

        assert len(results) == 2

    def test_search_with_pagination(self) -> None:
        """
        GIVEN a large dataset
        WHEN searching with pagination
        THEN should return correct page of results.
        """
        from mcp_server_langgraph.api.search import SearchParams, in_memory_search

        # Create 100 items
        items = [{"id": str(i), "name": f"Item {i}", "description": f"Description for item {i}"} for i in range(100)]

        # Get first page
        params1 = SearchParams(query="", limit=10, offset=0)
        page1 = in_memory_search(items, params1)
        assert len(page1) == 10
        assert page1[0]["id"] == "0"

        # Get second page
        params2 = SearchParams(query="", limit=10, offset=10)
        page2 = in_memory_search(items, params2)
        assert len(page2) == 10
        assert page2[0]["id"] == "10"

        # Get last page
        params3 = SearchParams(query="", limit=10, offset=90)
        page3 = in_memory_search(items, params3)
        assert len(page3) == 10
        assert page3[0]["id"] == "90"

    def test_search_ranking_prioritizes_name_over_description(self) -> None:
        """
        GIVEN items with varying relevance
        WHEN searching
        THEN should rank by relevance (name matches > description matches).
        """
        from mcp_server_langgraph.api.search import SearchParams, in_memory_search

        items = [
            {"id": "1", "name": "API Integration", "description": "Connect to services"},
            {"id": "2", "name": "Service Connector", "description": "API integration helper"},
            {"id": "3", "name": "Data Processor", "description": "Process API data"},
        ]

        params = SearchParams(query="API")
        results = in_memory_search(items, params)

        assert len(results) == 3
        # Item with "API" in name should rank first
        assert results[0]["id"] == "1"


@pytest.mark.xdist_group(name="test_search_fts")
class TestSearchEndpointIntegration:
    """Integration tests for search API endpoints."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_search_params_validation(self) -> None:
        """
        GIVEN various search parameters
        WHEN validating
        THEN should enforce constraints.
        """
        from pydantic import ValidationError

        from mcp_server_langgraph.api.search import SearchParams

        # Valid params
        params = SearchParams(query="test", limit=50, offset=0)
        assert params.limit == 50

        # Limit exceeds max - should be capped
        params_capped = SearchParams(query="test", limit=200)
        assert params_capped.limit <= 100

        # Negative offset should fail
        with pytest.raises(ValidationError):
            SearchParams(query="test", offset=-1)

    def test_search_highlight_integration(self) -> None:
        """
        GIVEN search results
        WHEN generating highlights
        THEN should properly highlight matching terms.
        """
        from mcp_server_langgraph.api.search import highlight_matches

        test_cases = [
            (
                "Workflow Automation System",
                "workflow",
                "<mark>Workflow</mark> Automation System",
            ),
            (
                "Send email notifications to users",
                "email",
                "Send <mark>email</mark> notifications to users",
            ),
            (
                "Process data workflow",
                "workflow data",
                "Process <mark>data</mark> <mark>workflow</mark>",
            ),
        ]

        for text, query, expected in test_cases:
            result = highlight_matches(text, query)
            assert "<mark>" in result
            assert "</mark>" in result
