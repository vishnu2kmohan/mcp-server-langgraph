"""
Cursor-Based Pagination Unit Tests

Tests for cursor-based pagination extension per TDD methodology.
Tests written FIRST before implementation (RED phase).

Cursor-based pagination provides:
- Stable pagination through sorted result sets
- Efficient for large datasets (no OFFSET scanning)
- RFC 5988 Link header generation for API navigation
"""

import base64
import gc
import json
from datetime import datetime

import pytest


pytestmark = [
    pytest.mark.unit,
    pytest.mark.api,
]


@pytest.mark.xdist_group(name="test_cursor_pagination")
class TestCursorPaginationParams:
    """Tests for CursorPaginationParams class."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_cursor_params_default_values(self) -> None:
        """
        GIVEN no parameters provided
        WHEN CursorPaginationParams is instantiated
        THEN default values should be used
        """
        from mcp_server_langgraph.api.pagination import CursorPaginationParams

        params = CursorPaginationParams()

        assert params.cursor is None
        assert params.limit == 20
        assert params.direction == "forward"

    def test_cursor_params_with_custom_limit(self) -> None:
        """
        GIVEN a custom limit
        WHEN CursorPaginationParams is instantiated
        THEN the custom limit should be used
        """
        from mcp_server_langgraph.api.pagination import CursorPaginationParams

        params = CursorPaginationParams(limit=50)

        assert params.limit == 50

    def test_cursor_params_enforces_max_limit(self) -> None:
        """
        GIVEN a limit exceeding maximum
        WHEN CursorPaginationParams is instantiated
        THEN limit should be capped at 1000
        """
        from mcp_server_langgraph.api.pagination import CursorPaginationParams

        params = CursorPaginationParams(limit=2000)

        assert params.limit == 1000

    def test_cursor_params_accepts_valid_cursor(self) -> None:
        """
        GIVEN a valid base64-encoded cursor
        WHEN CursorPaginationParams is instantiated
        THEN the cursor should be accepted
        """
        from mcp_server_langgraph.api.pagination import CursorPaginationParams

        # Create a valid cursor (base64-encoded JSON)
        cursor_data = {"id": "item-123", "created_at": "2025-01-01T00:00:00Z"}
        cursor = base64.urlsafe_b64encode(json.dumps(cursor_data).encode()).decode()

        params = CursorPaginationParams(cursor=cursor)

        assert params.cursor == cursor

    def test_cursor_params_direction_backward(self) -> None:
        """
        GIVEN direction set to 'backward'
        WHEN CursorPaginationParams is instantiated
        THEN backward direction should be accepted
        """
        from mcp_server_langgraph.api.pagination import CursorPaginationParams

        params = CursorPaginationParams(direction="backward")

        assert params.direction == "backward"

    def test_cursor_params_decode_cursor_returns_dict(self) -> None:
        """
        GIVEN a valid base64-encoded cursor
        WHEN decode_cursor is called
        THEN it should return the decoded dictionary
        """
        from mcp_server_langgraph.api.pagination import CursorPaginationParams

        cursor_data = {"id": "item-123", "created_at": "2025-01-01T00:00:00Z"}
        cursor = base64.urlsafe_b64encode(json.dumps(cursor_data).encode()).decode()
        params = CursorPaginationParams(cursor=cursor)

        decoded = params.decode_cursor()

        assert decoded == cursor_data

    def test_cursor_params_decode_cursor_returns_none_for_no_cursor(self) -> None:
        """
        GIVEN no cursor provided
        WHEN decode_cursor is called
        THEN it should return None
        """
        from mcp_server_langgraph.api.pagination import CursorPaginationParams

        params = CursorPaginationParams()

        assert params.decode_cursor() is None


@pytest.mark.xdist_group(name="test_cursor_pagination")
class TestCursorPaginationMetadata:
    """Tests for CursorPaginationMetadata class."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_metadata_with_next_cursor(self) -> None:
        """
        GIVEN pagination with more results
        WHEN CursorPaginationMetadata is created
        THEN next_cursor should be set and has_next should be True
        """
        from mcp_server_langgraph.api.pagination import CursorPaginationMetadata

        next_cursor = base64.urlsafe_b64encode(json.dumps({"id": "item-20"}).encode()).decode()
        metadata = CursorPaginationMetadata(
            next_cursor=next_cursor,
            prev_cursor=None,
            has_next=True,
            has_prev=False,
            count=20,
        )

        assert metadata.next_cursor == next_cursor
        assert metadata.has_next is True
        assert metadata.has_prev is False

    def test_metadata_with_prev_cursor(self) -> None:
        """
        GIVEN pagination with previous results
        WHEN CursorPaginationMetadata is created
        THEN prev_cursor should be set and has_prev should be True
        """
        from mcp_server_langgraph.api.pagination import CursorPaginationMetadata

        prev_cursor = base64.urlsafe_b64encode(json.dumps({"id": "item-1"}).encode()).decode()
        metadata = CursorPaginationMetadata(
            next_cursor=None,
            prev_cursor=prev_cursor,
            has_next=False,
            has_prev=True,
            count=20,
        )

        assert metadata.prev_cursor == prev_cursor
        assert metadata.has_prev is True
        assert metadata.has_next is False

    def test_metadata_count_reflects_items_returned(self) -> None:
        """
        GIVEN a specific number of items returned
        WHEN CursorPaginationMetadata is created
        THEN count should reflect the number of items
        """
        from mcp_server_langgraph.api.pagination import CursorPaginationMetadata

        metadata = CursorPaginationMetadata(
            next_cursor=None,
            prev_cursor=None,
            has_next=False,
            has_prev=False,
            count=15,
        )

        assert metadata.count == 15


@pytest.mark.xdist_group(name="test_cursor_pagination")
class TestCursorPaginatedResponse:
    """Tests for CursorPaginatedResponse class."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_response_contains_data_and_pagination(self) -> None:
        """
        GIVEN paginated data
        WHEN CursorPaginatedResponse is created
        THEN it should contain both data and pagination metadata
        """
        from mcp_server_langgraph.api.pagination import (
            CursorPaginatedResponse,
            CursorPaginationMetadata,
        )

        data = [{"id": "1", "name": "Item 1"}, {"id": "2", "name": "Item 2"}]
        metadata = CursorPaginationMetadata(
            next_cursor="next",
            prev_cursor=None,
            has_next=True,
            has_prev=False,
            count=2,
        )

        response: CursorPaginatedResponse[dict[str, str]] = CursorPaginatedResponse(
            data=data,
            pagination=metadata,
        )

        assert response.data == data
        assert response.pagination == metadata

    def test_response_generic_type_safety(self) -> None:
        """
        GIVEN typed data items
        WHEN CursorPaginatedResponse is created with generic type
        THEN the type should be preserved
        """
        from pydantic import BaseModel

        from mcp_server_langgraph.api.pagination import (
            CursorPaginatedResponse,
            CursorPaginationMetadata,
        )

        class TestItem(BaseModel):
            id: str
            name: str

        items = [TestItem(id="1", name="Test")]
        metadata = CursorPaginationMetadata(
            next_cursor=None,
            prev_cursor=None,
            has_next=False,
            has_prev=False,
            count=1,
        )

        response: CursorPaginatedResponse[TestItem] = CursorPaginatedResponse(
            data=items,
            pagination=metadata,
        )

        assert isinstance(response.data[0], TestItem)


@pytest.mark.xdist_group(name="test_cursor_pagination")
class TestCreateCursorPaginatedResponse:
    """Tests for create_cursor_paginated_response helper function."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_creates_response_with_next_cursor_when_more_items(self) -> None:
        """
        GIVEN more items exist after current page
        WHEN create_cursor_paginated_response is called
        THEN response should have next_cursor and has_next=True
        """
        from mcp_server_langgraph.api.pagination import create_cursor_paginated_response

        data = [{"id": f"item-{i}", "created_at": "2025-01-01"} for i in range(20)]

        response = create_cursor_paginated_response(
            data=data,
            limit=20,
            has_more=True,
            cursor_field="id",
        )

        assert response.pagination.has_next is True
        assert response.pagination.next_cursor is not None
        assert response.pagination.count == 20

    def test_creates_response_without_next_cursor_when_last_page(self) -> None:
        """
        GIVEN no more items after current page
        WHEN create_cursor_paginated_response is called
        THEN response should have no next_cursor and has_next=False
        """
        from mcp_server_langgraph.api.pagination import create_cursor_paginated_response

        data = [{"id": f"item-{i}", "created_at": "2025-01-01"} for i in range(10)]

        response = create_cursor_paginated_response(
            data=data,
            limit=20,
            has_more=False,
            cursor_field="id",
        )

        assert response.pagination.has_next is False
        assert response.pagination.next_cursor is None
        assert response.pagination.count == 10

    def test_creates_prev_cursor_when_not_first_page(self) -> None:
        """
        GIVEN pagination is not on first page
        WHEN create_cursor_paginated_response is called with prev_cursor_data
        THEN response should have prev_cursor and has_prev=True
        """
        from mcp_server_langgraph.api.pagination import create_cursor_paginated_response

        data = [{"id": f"item-{i}", "created_at": "2025-01-01"} for i in range(20, 40)]
        prev_cursor_data = {"id": "item-19"}

        response = create_cursor_paginated_response(
            data=data,
            limit=20,
            has_more=True,
            cursor_field="id",
            prev_cursor_data=prev_cursor_data,
        )

        assert response.pagination.has_prev is True
        assert response.pagination.prev_cursor is not None

    def test_cursor_encodes_correct_field_value(self) -> None:
        """
        GIVEN data with specific cursor field values
        WHEN create_cursor_paginated_response is called
        THEN next_cursor should encode the last item's cursor field value
        """
        from mcp_server_langgraph.api.pagination import create_cursor_paginated_response

        data = [
            {"id": "item-1", "created_at": "2025-01-01"},
            {"id": "item-2", "created_at": "2025-01-02"},
            {"id": "item-3", "created_at": "2025-01-03"},
        ]

        response = create_cursor_paginated_response(
            data=data,
            limit=20,
            has_more=True,
            cursor_field="id",
        )

        # Decode the cursor and verify it contains the last item's id
        cursor = response.pagination.next_cursor
        assert cursor is not None
        decoded = json.loads(base64.urlsafe_b64decode(cursor))
        assert decoded["id"] == "item-3"

    def test_empty_data_returns_empty_response(self) -> None:
        """
        GIVEN empty data list
        WHEN create_cursor_paginated_response is called
        THEN response should have no cursors and count=0
        """
        from mcp_server_langgraph.api.pagination import create_cursor_paginated_response

        response = create_cursor_paginated_response(
            data=[],
            limit=20,
            has_more=False,
            cursor_field="id",
        )

        assert response.data == []
        assert response.pagination.count == 0
        assert response.pagination.next_cursor is None
        assert response.pagination.prev_cursor is None


@pytest.mark.xdist_group(name="test_cursor_pagination")
class TestEncodeCursor:
    """Tests for encode_cursor helper function."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_encodes_dict_to_base64_string(self) -> None:
        """
        GIVEN a dictionary with cursor data
        WHEN encode_cursor is called
        THEN it should return a base64-encoded string
        """
        from mcp_server_langgraph.api.pagination import encode_cursor

        cursor_data = {"id": "item-123", "created_at": "2025-01-01T00:00:00Z"}

        cursor = encode_cursor(cursor_data)

        # Verify it's a valid base64 string that decodes to original data
        decoded = json.loads(base64.urlsafe_b64decode(cursor))
        assert decoded == cursor_data

    def test_encodes_datetime_to_iso_format(self) -> None:
        """
        GIVEN a dictionary with datetime value
        WHEN encode_cursor is called
        THEN datetime should be serialized to ISO format
        """
        from mcp_server_langgraph.api.pagination import encode_cursor

        dt = datetime(2025, 1, 1, 12, 30, 45)
        cursor_data = {"id": "item-123", "created_at": dt}

        cursor = encode_cursor(cursor_data)

        decoded = json.loads(base64.urlsafe_b64decode(cursor))
        assert decoded["created_at"] == "2025-01-01T12:30:45"


@pytest.mark.xdist_group(name="test_cursor_pagination")
class TestDecodeCursor:
    """Tests for decode_cursor helper function."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_decodes_valid_cursor_string(self) -> None:
        """
        GIVEN a valid base64-encoded cursor
        WHEN decode_cursor is called
        THEN it should return the original dictionary
        """
        from mcp_server_langgraph.api.pagination import decode_cursor

        original = {"id": "item-123", "created_at": "2025-01-01T00:00:00Z"}
        cursor = base64.urlsafe_b64encode(json.dumps(original).encode()).decode()

        decoded = decode_cursor(cursor)

        assert decoded == original

    def test_decode_cursor_returns_none_for_none_input(self) -> None:
        """
        GIVEN None as input
        WHEN decode_cursor is called
        THEN it should return None
        """
        from mcp_server_langgraph.api.pagination import decode_cursor

        assert decode_cursor(None) is None

    def test_decode_cursor_raises_for_invalid_base64(self) -> None:
        """
        GIVEN an invalid base64 string
        WHEN decode_cursor is called
        THEN it should raise ValueError
        """
        from mcp_server_langgraph.api.pagination import decode_cursor

        with pytest.raises(ValueError, match="Invalid cursor"):
            decode_cursor("not-valid-base64!!!")

    def test_decode_cursor_raises_for_invalid_json(self) -> None:
        """
        GIVEN a valid base64 string that decodes to invalid JSON
        WHEN decode_cursor is called
        THEN it should raise ValueError
        """
        from mcp_server_langgraph.api.pagination import decode_cursor

        invalid_json = base64.urlsafe_b64encode(b"not valid json").decode()

        with pytest.raises(ValueError, match="Invalid cursor"):
            decode_cursor(invalid_json)


@pytest.mark.xdist_group(name="test_cursor_pagination")
class TestGenerateLinkHeader:
    """Tests for RFC 5988 Link header generation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_generates_next_link_when_has_next(self) -> None:
        """
        GIVEN pagination with next cursor
        WHEN generate_link_header is called
        THEN Link header should contain 'next' relation
        """
        from mcp_server_langgraph.api.pagination import (
            CursorPaginationMetadata,
            generate_link_header,
        )

        metadata = CursorPaginationMetadata(
            next_cursor="abc123",
            prev_cursor=None,
            has_next=True,
            has_prev=False,
            count=20,
        )

        link = generate_link_header(
            base_url="https://api.example.com/items",
            metadata=metadata,
        )

        assert 'rel="next"' in link
        assert "cursor=abc123" in link

    def test_generates_prev_link_when_has_prev(self) -> None:
        """
        GIVEN pagination with previous cursor
        WHEN generate_link_header is called
        THEN Link header should contain 'prev' relation
        """
        from mcp_server_langgraph.api.pagination import (
            CursorPaginationMetadata,
            generate_link_header,
        )

        metadata = CursorPaginationMetadata(
            next_cursor=None,
            prev_cursor="xyz789",
            has_next=False,
            has_prev=True,
            count=20,
        )

        link = generate_link_header(
            base_url="https://api.example.com/items",
            metadata=metadata,
        )

        assert 'rel="prev"' in link
        assert "cursor=xyz789" in link

    def test_generates_both_links_when_in_middle(self) -> None:
        """
        GIVEN pagination in the middle of results
        WHEN generate_link_header is called
        THEN Link header should contain both 'next' and 'prev' relations
        """
        from mcp_server_langgraph.api.pagination import (
            CursorPaginationMetadata,
            generate_link_header,
        )

        metadata = CursorPaginationMetadata(
            next_cursor="next123",
            prev_cursor="prev789",
            has_next=True,
            has_prev=True,
            count=20,
        )

        link = generate_link_header(
            base_url="https://api.example.com/items",
            metadata=metadata,
        )

        assert 'rel="next"' in link
        assert 'rel="prev"' in link
        assert "cursor=next123" in link
        assert "cursor=prev789" in link

    def test_returns_empty_string_when_no_pagination(self) -> None:
        """
        GIVEN pagination with no next or prev
        WHEN generate_link_header is called
        THEN should return empty string
        """
        from mcp_server_langgraph.api.pagination import (
            CursorPaginationMetadata,
            generate_link_header,
        )

        metadata = CursorPaginationMetadata(
            next_cursor=None,
            prev_cursor=None,
            has_next=False,
            has_prev=False,
            count=5,
        )

        link = generate_link_header(
            base_url="https://api.example.com/items",
            metadata=metadata,
        )

        assert link == ""

    def test_preserves_existing_query_params(self) -> None:
        """
        GIVEN a base URL with existing query parameters
        WHEN generate_link_header is called
        THEN existing params should be preserved in links
        """
        from mcp_server_langgraph.api.pagination import (
            CursorPaginationMetadata,
            generate_link_header,
        )

        metadata = CursorPaginationMetadata(
            next_cursor="abc123",
            prev_cursor=None,
            has_next=True,
            has_prev=False,
            count=20,
        )

        link = generate_link_header(
            base_url="https://api.example.com/items?status=active&limit=20",
            metadata=metadata,
        )

        assert "status=active" in link
        assert "limit=20" in link
        assert "cursor=abc123" in link

    def test_link_format_follows_rfc5988(self) -> None:
        """
        GIVEN valid pagination metadata
        WHEN generate_link_header is called
        THEN Link header should follow RFC 5988 format
        """
        from mcp_server_langgraph.api.pagination import (
            CursorPaginationMetadata,
            generate_link_header,
        )

        metadata = CursorPaginationMetadata(
            next_cursor="abc123",
            prev_cursor=None,
            has_next=True,
            has_prev=False,
            count=20,
        )

        link = generate_link_header(
            base_url="https://api.example.com/items",
            metadata=metadata,
        )

        # RFC 5988 format: <URL>; rel="relation"
        assert link.startswith("<")
        assert ">;" in link
        assert 'rel="next"' in link
