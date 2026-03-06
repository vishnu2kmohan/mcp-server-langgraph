"""
Sorting Helper Unit Tests

Tests for API sorting utilities per TDD methodology.
"""

import gc

import pytest


pytestmark = [
    pytest.mark.unit,
    pytest.mark.api,
]


class TestSortingParams:
    """Tests for SortingParams class."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_sorting_params_default_values(self) -> None:
        """
        GIVEN no parameters
        WHEN SortingParams is created
        THEN should have default values
        """
        from mcp_server_langgraph.api.sorting import SortingParams

        params = SortingParams()

        assert params.sort_by == "created_at"
        assert params.sort_order == "desc"

    def test_sorting_params_custom_values(self) -> None:
        """
        GIVEN custom parameters
        WHEN SortingParams is created
        THEN should have custom values
        """
        from mcp_server_langgraph.api.sorting import SortingParams

        params = SortingParams(sort_by="name", sort_order="asc")

        assert params.sort_by == "name"
        assert params.sort_order == "asc"

    def test_sorting_params_validates_order(self) -> None:
        """
        GIVEN invalid sort order
        WHEN SortingParams is created
        THEN should raise validation error
        """
        from pydantic import ValidationError

        from mcp_server_langgraph.api.sorting import SortingParams

        with pytest.raises(ValidationError):
            SortingParams(sort_order="invalid")

    def test_apply_sorting_to_list(self) -> None:
        """
        GIVEN a list of dicts with sortable fields
        WHEN apply_sorting is called
        THEN should return sorted list
        """
        from mcp_server_langgraph.api.sorting import SortingParams, apply_sorting

        items = [
            {"name": "Zebra", "created_at": "2025-01-01"},
            {"name": "Alpha", "created_at": "2025-01-03"},
            {"name": "Beta", "created_at": "2025-01-02"},
        ]

        params = SortingParams(sort_by="name", sort_order="asc")
        sorted_items = apply_sorting(items, params)

        assert sorted_items[0]["name"] == "Alpha"
        assert sorted_items[1]["name"] == "Beta"
        assert sorted_items[2]["name"] == "Zebra"

    def test_apply_sorting_descending(self) -> None:
        """
        GIVEN a list of items
        WHEN apply_sorting is called with desc order
        THEN should return reverse sorted list
        """
        from mcp_server_langgraph.api.sorting import SortingParams, apply_sorting

        items = [
            {"name": "Alpha"},
            {"name": "Beta"},
            {"name": "Zebra"},
        ]

        params = SortingParams(sort_by="name", sort_order="desc")
        sorted_items = apply_sorting(items, params)

        assert sorted_items[0]["name"] == "Zebra"
        assert sorted_items[2]["name"] == "Alpha"
