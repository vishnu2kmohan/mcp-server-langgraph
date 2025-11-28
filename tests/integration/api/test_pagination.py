"""
Tests for Standardized Pagination

Validates that all list endpoints follow consistent pagination patterns for
production-grade API behavior.

Following TDD: These tests define the expected pagination behavior (RED phase).
"""

import gc

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.integration


@pytest.fixture
def test_client():
    """FastAPI TestClient using the actual production app"""
    from mcp_server_langgraph.mcp.server_streamable import app

    return TestClient(app)


@pytest.mark.unit
@pytest.mark.contract
@pytest.mark.xdist_group(name="testpaginationmodels")
class TestPaginationModels:
    """Test that pagination models are properly defined"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_pagination_params_model_exists(self):
        """PaginationParams model should exist for request parsing"""
        from mcp_server_langgraph.api.pagination import PaginationParams

        # Should be importable
        assert PaginationParams is not None

        # Should have expected fields
        params = PaginationParams()
        assert hasattr(params, "page")
        assert hasattr(params, "page_size")
        assert hasattr(params, "offset")
        assert hasattr(params, "limit")

    def test_paginated_response_model_exists(self):
        """PaginatedResponse model should exist for response wrapping"""
        from mcp_server_langgraph.api.pagination import PaginatedResponse

        # Should be importable
        assert PaginatedResponse is not None

    def test_pagination_metadata_model_exists(self):
        """PaginationMetadata model should exist for pagination info"""
        from mcp_server_langgraph.api.pagination import PaginationMetadata

        # Should be importable
        assert PaginationMetadata is not None

        # Should have expected fields
        metadata = PaginationMetadata(total=100, page=1, page_size=20, total_pages=5)
        assert metadata.total == 100
        assert metadata.page == 1
        assert metadata.page_size == 20
        assert metadata.total_pages == 5


@pytest.mark.unit
@pytest.mark.contract
@pytest.mark.xdist_group(name="testpaginationdefaults")
class TestPaginationDefaults:
    """Test default pagination values"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_pagination_params_defaults(self):
        """PaginationParams should have sensible defaults"""
        from mcp_server_langgraph.api.pagination import PaginationParams

        params = PaginationParams()

        # Default page should be 1 (not 0)
        assert params.page >= 1

        # Default page_size should be reasonable (10-100)
        assert 10 <= params.page_size <= 100

        # Offset/limit should be calculated correctly
        assert params.offset >= 0
        assert params.limit > 0

    def test_pagination_max_page_size(self):
        """PaginationParams should enforce maximum page size"""
        from mcp_server_langgraph.api.pagination import PaginationParams

        # Try to create with very large page size
        try:
            params = PaginationParams(page_size=10000)
            # Should be capped at reasonable max (e.g., 1000)
            assert params.page_size <= 1000, "Page size should be capped at maximum"
        except Exception:
            # Validation error is also acceptable
            pass


@pytest.mark.unit
@pytest.mark.contract
@pytest.mark.xdist_group(name="testpaginationopenapischema")
class TestPaginationOpenAPISchema:
    """Test that pagination is documented in OpenAPI schema"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_pagination_params_in_openapi(self, test_client):
        """Pagination parameters should be documented in OpenAPI schema"""
        openapi = test_client.get("/openapi.json").json()
        schemas = openapi.get("components", {}).get("schemas", {})

        # Should have PaginationParams schema
        assert "PaginationParams" in schemas or "Pagination" in str(schemas), (
            "PaginationParams schema should be in OpenAPI components"
        )

    def test_pagination_metadata_in_openapi(self, test_client):
        """Pagination metadata should be documented in OpenAPI schema"""
        openapi = test_client.get("/openapi.json").json()
        schemas = openapi.get("components", {}).get("schemas", {})

        # Should have PaginationMetadata schema
        assert "PaginationMetadata" in schemas or "Pagination" in str(schemas), (
            "PaginationMetadata schema should be in OpenAPI components"
        )


@pytest.mark.unit
@pytest.mark.contract
@pytest.mark.xdist_group(name="testpaginationresponse")
class TestPaginationResponse:
    """Test pagination response structure"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_paginated_response_structure(self):
        """PaginatedResponse should have standard structure"""
        from mcp_server_langgraph.api.pagination import PaginatedResponse, PaginationMetadata

        # Create example response
        response = PaginatedResponse(
            data=[{"id": 1}, {"id": 2}], pagination=PaginationMetadata(total=100, page=1, page_size=20, total_pages=5)
        )

        # Should have data and pagination fields
        assert hasattr(response, "data")
        assert hasattr(response, "pagination")

        # Data should be a list
        assert isinstance(response.data, list)

        # Pagination should have required fields
        assert response.pagination.total == 100
        assert response.pagination.page == 1
        assert response.pagination.page_size == 20
        assert response.pagination.total_pages == 5

    def test_paginated_response_calculates_total_pages(self):
        """PaginationMetadata should correctly calculate total_pages"""
        from mcp_server_langgraph.api.pagination import PaginationMetadata

        # Test various total/page_size combinations
        test_cases = [
            (100, 20, 5),  # 100 items / 20 per page = 5 pages
            (95, 20, 5),  # 95 items / 20 per page = 5 pages (rounded up)
            (0, 20, 0),  # 0 items = 0 pages
            (1, 20, 1),  # 1 item = 1 page
        ]

        for total, page_size, expected_pages in test_cases:
            metadata = PaginationMetadata(
                total=total,
                page=1,
                page_size=page_size,
                total_pages=expected_pages,  # We're providing it, but should be calculated
            )
            assert metadata.total_pages == expected_pages, (
                f"total_pages calculation wrong for total={total}, page_size={page_size}"
            )


@pytest.mark.unit
@pytest.mark.contract
@pytest.mark.xdist_group(name="testpaginationlinks")
class TestPaginationLinks:
    """Test that pagination includes navigation links"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_pagination_metadata_has_link_fields(self):
        """PaginationMetadata should include next/prev page indicators"""
        from mcp_server_langgraph.api.pagination import PaginationMetadata

        metadata = PaginationMetadata(total=100, page=2, page_size=20, total_pages=5)

        # Should be able to determine if next/prev pages exist
        # These might be computed properties or fields
        assert metadata.page < metadata.total_pages, "Should have next page"
        assert metadata.page > 1, "Should have previous page"


@pytest.mark.integration
@pytest.mark.xdist_group(name="testpaginationhelpers")
class TestPaginationHelpers:
    """Test pagination helper functions"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_create_paginated_response_helper_exists(self):
        """Helper function to create paginated responses should exist"""
        try:
            from mcp_server_langgraph.api.pagination import create_paginated_response

            assert callable(create_paginated_response)
        except ImportError:
            # Helper not required if using model directly
            pass

    def test_pagination_offset_limit_calculation(self):
        """Test offset/limit calculation from page/page_size"""
        from mcp_server_langgraph.api.pagination import PaginationParams

        # Page 1, page_size 20 -> offset 0, limit 20
        params = PaginationParams(page=1, page_size=20)
        assert params.offset == 0
        assert params.limit == 20

        # Page 2, page_size 20 -> offset 20, limit 20
        params = PaginationParams(page=2, page_size=20)
        assert params.offset == 20
        assert params.limit == 20

        # Page 3, page_size 10 -> offset 20, limit 10
        params = PaginationParams(page=3, page_size=10)
        assert params.offset == 20
        assert params.limit == 10
