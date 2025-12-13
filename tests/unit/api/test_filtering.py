"""
Filtering Helper Unit Tests

Tests for API filtering utilities per TDD methodology.
"""

import gc

import pytest


pytestmark = [
    pytest.mark.unit,
    pytest.mark.api,
]


@pytest.mark.xdist_group(name="test_filtering")
class TestFilterParams:
    """Tests for FilterParams class."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_filter_params_creation(self) -> None:
        """
        GIVEN filter criteria
        WHEN FilterParams is created
        THEN should store filters
        """
        from mcp_server_langgraph.api.filtering import FilterParams

        params = FilterParams(status="active", user_id="user123")

        assert params.status == "active"
        assert params.user_id == "user123"

    def test_filter_params_optional_fields(self) -> None:
        """
        GIVEN no filter criteria
        WHEN FilterParams is created
        THEN all fields should be None
        """
        from mcp_server_langgraph.api.filtering import FilterParams

        params = FilterParams()

        assert params.status is None
        assert params.user_id is None

    def test_apply_filters_by_status(self) -> None:
        """
        GIVEN a list of items with status
        WHEN apply_filters is called with status filter
        THEN should return filtered items
        """
        from mcp_server_langgraph.api.filtering import FilterParams, apply_filters

        items = [
            {"id": "1", "status": "active"},
            {"id": "2", "status": "inactive"},
            {"id": "3", "status": "active"},
        ]

        params = FilterParams(status="active")
        filtered = apply_filters(items, params)

        assert len(filtered) == 2
        assert all(item["status"] == "active" for item in filtered)

    def test_apply_filters_multiple_criteria(self) -> None:
        """
        GIVEN a list of items
        WHEN apply_filters is called with multiple filters
        THEN should apply all filters
        """
        from mcp_server_langgraph.api.filtering import FilterParams, apply_filters

        items = [
            {"id": "1", "status": "active", "user_id": "user1"},
            {"id": "2", "status": "active", "user_id": "user2"},
            {"id": "3", "status": "inactive", "user_id": "user1"},
        ]

        params = FilterParams(status="active", user_id="user1")
        filtered = apply_filters(items, params)

        assert len(filtered) == 1
        assert filtered[0]["id"] == "1"

    def test_apply_filters_no_criteria(self) -> None:
        """
        GIVEN no filter criteria
        WHEN apply_filters is called
        THEN should return all items
        """
        from mcp_server_langgraph.api.filtering import FilterParams, apply_filters

        items = [
            {"id": "1", "status": "active"},
            {"id": "2", "status": "inactive"},
        ]

        params = FilterParams()
        filtered = apply_filters(items, params)

        assert len(filtered) == 2
