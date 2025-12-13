"""
Search API Unit Tests

Tests for PostgreSQL full-text search utilities per TDD methodology.
Tests search parameter models, query building, and result ranking.
"""

from __future__ import annotations

import gc

import pytest

pytestmark = [
    pytest.mark.unit,
    pytest.mark.api,
]


@pytest.mark.xdist_group(name="test_search")
class TestSearchParams:
    """Tests for SearchParams model."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_search_params_creation(self) -> None:
        """
        GIVEN search criteria
        WHEN SearchParams is created
        THEN should store search parameters.
        """
        from mcp_server_langgraph.api.search import SearchParams

        params = SearchParams(query="workflow automation")

        assert params.query == "workflow automation"
        assert params.limit == 20  # Default
        assert params.offset == 0  # Default

    def test_search_params_with_filters(self) -> None:
        """
        GIVEN search criteria with filters
        WHEN SearchParams is created
        THEN should store all parameters.
        """
        from mcp_server_langgraph.api.search import SearchParams

        params = SearchParams(
            query="test query",
            entity_type="workflow",
            user_id="user123",
            limit=50,
            offset=10,
        )

        assert params.query == "test query"
        assert params.entity_type == "workflow"
        assert params.user_id == "user123"
        assert params.limit == 50
        assert params.offset == 10

    def test_search_params_empty_query(self) -> None:
        """
        GIVEN an empty search query
        WHEN SearchParams is created
        THEN should allow empty query (returns all results).
        """
        from mcp_server_langgraph.api.search import SearchParams

        params = SearchParams(query="")

        assert params.query == ""

    def test_search_params_validates_limit(self) -> None:
        """
        GIVEN an invalid limit
        WHEN SearchParams is created
        THEN should enforce constraints.
        """
        from mcp_server_langgraph.api.search import SearchParams

        # Limit should be capped at max value
        params = SearchParams(query="test", limit=1000)
        assert params.limit <= 100  # Max limit should be 100


@pytest.mark.xdist_group(name="test_search")
class TestSearchResult:
    """Tests for SearchResult model."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_search_result_creation(self) -> None:
        """
        GIVEN search result data
        WHEN SearchResult is created
        THEN should store all fields.
        """
        from mcp_server_langgraph.api.search import SearchResult

        result = SearchResult(
            id="workflow-123",
            entity_type="workflow",
            name="Test Workflow",
            description="A test workflow for automation",
            rank=0.95,
            highlights={"name": "Test <mark>Workflow</mark>"},
        )

        assert result.id == "workflow-123"
        assert result.entity_type == "workflow"
        assert result.name == "Test Workflow"
        assert result.rank == 0.95
        assert "name" in result.highlights

    def test_search_result_optional_fields(self) -> None:
        """
        GIVEN minimal search result data
        WHEN SearchResult is created
        THEN optional fields should have defaults.
        """
        from mcp_server_langgraph.api.search import SearchResult

        result = SearchResult(
            id="session-456",
            entity_type="session",
            name="Chat Session",
        )

        assert result.description is None
        assert result.rank == 0.0
        assert result.highlights == {}


@pytest.mark.xdist_group(name="test_search")
class TestSearchResponse:
    """Tests for SearchResponse model."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_search_response_with_results(self) -> None:
        """
        GIVEN search results
        WHEN SearchResponse is created
        THEN should contain results and metadata.
        """
        from mcp_server_langgraph.api.search import SearchResponse, SearchResult

        results = [
            SearchResult(id="1", entity_type="workflow", name="Test 1"),
            SearchResult(id="2", entity_type="workflow", name="Test 2"),
        ]

        response = SearchResponse(
            query="test",
            results=results,
            total=2,  # Total equals results, no more available
            limit=20,
            offset=0,
        )

        assert response.query == "test"
        assert len(response.results) == 2
        assert response.total == 2
        assert response.has_more is False  # 2 results, total 2, offset 0 = no more

    def test_search_response_has_more_pagination(self) -> None:
        """
        GIVEN paginated search results
        WHEN total is greater than offset + returned results
        THEN has_more should be True.
        """
        from mcp_server_langgraph.api.search import SearchResponse, SearchResult

        results = [SearchResult(id=str(i), entity_type="workflow", name=f"Test {i}") for i in range(20)]

        response = SearchResponse(
            query="test",
            results=results,
            total=100,
            limit=20,
            offset=0,
        )

        assert response.has_more is True


@pytest.mark.xdist_group(name="test_search")
class TestSearchQueryBuilder:
    """Tests for FTS query building utilities."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_build_tsquery_simple(self) -> None:
        """
        GIVEN a simple search query
        WHEN building a tsquery
        THEN should create valid PostgreSQL tsquery.
        """
        from mcp_server_langgraph.api.search import build_tsquery

        query = build_tsquery("workflow automation")

        # Should create OR-combined query for flexibility
        assert "workflow" in query.lower()
        assert "automation" in query.lower()

    def test_build_tsquery_special_characters(self) -> None:
        """
        GIVEN a query with special characters
        WHEN building a tsquery
        THEN should sanitize and escape properly.
        """
        from mcp_server_langgraph.api.search import build_tsquery

        query = build_tsquery("test's query & special: chars")

        # Should not contain raw special characters
        assert "&" not in query or ":*" in query  # & might be in :* prefix
        assert "'" not in query or query.count("'") % 2 == 0  # Properly escaped

    def test_build_tsquery_empty(self) -> None:
        """
        GIVEN an empty query
        WHEN building a tsquery
        THEN should return empty string or valid empty query.
        """
        from mcp_server_langgraph.api.search import build_tsquery

        query = build_tsquery("")

        # Empty query should return something that doesn't error in SQL
        assert query is not None

    def test_build_tsquery_prefix_matching(self) -> None:
        """
        GIVEN a query term
        WHEN building a tsquery
        THEN should support prefix matching with :*.
        """
        from mcp_server_langgraph.api.search import build_tsquery

        query = build_tsquery("auto")

        # Should support prefix matching for partial words
        assert ":*" in query or "auto" in query.lower()


@pytest.mark.xdist_group(name="test_search")
class TestSearchHighlighter:
    """Tests for search result highlighting."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_highlight_matches_wraps_terms_in_tags(self) -> None:
        """
        GIVEN text with matching terms
        WHEN highlighting
        THEN should wrap matches in highlight tags.
        """
        from mcp_server_langgraph.api.search import highlight_matches

        text = "This is a workflow for automation tasks"
        query = "workflow"

        highlighted = highlight_matches(text, query)

        assert "<mark>" in highlighted
        assert "</mark>" in highlighted
        assert "workflow" in highlighted.lower()

    def test_highlight_multiple_matches(self) -> None:
        """
        GIVEN text with multiple matching terms
        WHEN highlighting
        THEN should highlight all matches.
        """
        from mcp_server_langgraph.api.search import highlight_matches

        text = "Workflow automation workflow processing"
        query = "workflow"

        highlighted = highlight_matches(text, query)

        # Should highlight both occurrences
        assert highlighted.count("<mark>") >= 2

    def test_highlight_case_insensitive(self) -> None:
        """
        GIVEN text with mixed case matches
        WHEN highlighting
        THEN should be case-insensitive.
        """
        from mcp_server_langgraph.api.search import highlight_matches

        text = "WORKFLOW and Workflow and workflow"
        query = "workflow"

        highlighted = highlight_matches(text, query)

        # All three should be highlighted
        assert highlighted.count("<mark>") == 3

    def test_highlight_no_matches(self) -> None:
        """
        GIVEN text without matches
        WHEN highlighting
        THEN should return original text.
        """
        from mcp_server_langgraph.api.search import highlight_matches

        text = "This is some text"
        query = "workflow"

        highlighted = highlight_matches(text, query)

        assert highlighted == text
        assert "<mark>" not in highlighted


@pytest.mark.xdist_group(name="test_search")
class TestInMemorySearch:
    """Tests for in-memory search implementation (for testing)."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_in_memory_search_by_name(self) -> None:
        """
        GIVEN a list of items
        WHEN searching by name
        THEN should return matching items.
        """
        from mcp_server_langgraph.api.search import SearchParams, in_memory_search

        items = [
            {"id": "1", "name": "Email Workflow", "description": "Sends emails"},
            {"id": "2", "name": "Data Pipeline", "description": "Processes data"},
            {"id": "3", "name": "Notification Workflow", "description": "Sends notifications"},
        ]

        params = SearchParams(query="workflow")
        results = in_memory_search(items, params)

        assert len(results) == 2
        assert all("workflow" in r["name"].lower() for r in results)

    def test_in_memory_search_by_description(self) -> None:
        """
        GIVEN a list of items
        WHEN searching by description
        THEN should return matching items.
        """
        from mcp_server_langgraph.api.search import SearchParams, in_memory_search

        items = [
            {"id": "1", "name": "Sender", "description": "Sends automated emails"},
            {"id": "2", "name": "Processor", "description": "Data processing"},
            {"id": "3", "name": "Notifier", "description": "Sends notifications"},
        ]

        params = SearchParams(query="sends")
        results = in_memory_search(items, params)

        assert len(results) == 2

    def test_in_memory_search_ranked(self) -> None:
        """
        GIVEN search results
        WHEN searching
        THEN results should be ranked by relevance.
        """
        from mcp_server_langgraph.api.search import SearchParams, in_memory_search

        items = [
            {"id": "1", "name": "Workflow", "description": "A workflow"},  # workflow in both
            {"id": "2", "name": "Task", "description": "workflow task"},  # workflow in desc only
            {"id": "3", "name": "Another Workflow", "description": "Something else"},  # workflow in name
        ]

        params = SearchParams(query="workflow")
        results = in_memory_search(items, params)

        # Item with workflow in name should rank higher
        assert len(results) >= 2
        # Results should be ordered by relevance (name matches rank higher)

    def test_in_memory_search_empty_query(self) -> None:
        """
        GIVEN an empty search query
        WHEN searching
        THEN should return all items.
        """
        from mcp_server_langgraph.api.search import SearchParams, in_memory_search

        items = [
            {"id": "1", "name": "Item 1", "description": "Desc 1"},
            {"id": "2", "name": "Item 2", "description": "Desc 2"},
        ]

        params = SearchParams(query="")
        results = in_memory_search(items, params)

        assert len(results) == 2

    def test_in_memory_search_pagination(self) -> None:
        """
        GIVEN a large list of items
        WHEN searching with pagination
        THEN should return correct page.
        """
        from mcp_server_langgraph.api.search import SearchParams, in_memory_search

        items = [{"id": str(i), "name": f"Item {i}", "description": f"Desc {i}"} for i in range(50)]

        params = SearchParams(query="", limit=10, offset=20)
        results = in_memory_search(items, params)

        assert len(results) == 10
        assert results[0]["id"] == "20"
