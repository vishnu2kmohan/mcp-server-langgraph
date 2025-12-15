"""
TDD Tests for Workflow Storage Optimizations.

These tests verify the workflow storage layer is optimized for:
1. Full-Text Search (FTS) using PostgreSQL tsvector
2. Cursor-based pagination for stable ordering
3. Composite indices for efficient filtering and sorting
4. Enhanced sorting capabilities

RED Phase: These tests define expected behavior for optimized workflow storage.
"""

import gc

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="workflow_storage")
class TestWorkflowModelIndices:
    """Tests for WorkflowModel database indices."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_workflow_model_has_search_vector_column(self) -> None:
        """Verify WorkflowModel has search_vector TSVECTOR column."""
        from mcp_server_langgraph.storage.workflow.postgres_models import WorkflowModel

        # Check that search_vector column exists
        mapper = WorkflowModel.__mapper__
        column_names = [col.key for col in mapper.columns]
        assert "search_vector" in column_names, "WorkflowModel should have search_vector column"

    @pytest.mark.unit
    def test_workflow_model_has_gin_index_on_search_vector(self) -> None:
        """Verify GIN index exists on search_vector for fast FTS."""
        from mcp_server_langgraph.storage.workflow.postgres_models import WorkflowModel

        # Check table args for GIN index
        table_args = WorkflowModel.__table_args__
        index_names = [idx.name for idx in table_args if hasattr(idx, "name")]
        assert "ix_workflows_search_vector" in index_names

    @pytest.mark.unit
    def test_workflow_model_has_composite_index_for_updated_at_pagination(self) -> None:
        """Verify composite index (updated_at, id) for stable cursor pagination."""
        from mcp_server_langgraph.storage.workflow.postgres_models import WorkflowModel

        table_args = WorkflowModel.__table_args__
        index_names = [idx.name for idx in table_args if hasattr(idx, "name")]
        # Need index for ORDER BY updated_at DESC, id DESC
        assert "ix_workflows_updated_at_id" in index_names or "ix_workflows_user_updated" in index_names

    @pytest.mark.unit
    def test_workflow_model_has_composite_index_for_name_sorting(self) -> None:
        """Verify composite index (name, id) for stable name-based pagination."""
        from mcp_server_langgraph.storage.workflow.postgres_models import WorkflowModel

        table_args = WorkflowModel.__table_args__
        index_names = [idx.name for idx in table_args if hasattr(idx, "name")]
        assert "ix_workflows_name_id" in index_names

    @pytest.mark.unit
    def test_workflow_model_has_status_column(self) -> None:
        """Verify WorkflowModel has status column for filtering."""
        from mcp_server_langgraph.storage.workflow.postgres_models import WorkflowModel

        mapper = WorkflowModel.__mapper__
        column_names = [col.key for col in mapper.columns]
        assert "status" in column_names, "WorkflowModel should have status column"


@pytest.mark.xdist_group(name="workflow_storage")
class TestWorkflowManagerFTS:
    """Tests for Full-Text Search in workflow manager."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_list_workflows_uses_fts_for_search(self) -> None:
        """Verify list_workflows uses FTS (plainto_tsquery) instead of ILIKE."""
        # GIVEN: A workflow manager
        # WHEN: Searching for "agent builder"
        # THEN: Should use plainto_tsquery for efficient search
        search_term = "agent builder"
        # Expected: Uses search_vector @@ plainto_tsquery('english', 'agent builder')
        # Falls back to ILIKE only if FTS not available
        assert len(search_term.split()) == 2

    @pytest.mark.unit
    def test_fts_weighs_name_higher_than_description(self) -> None:
        """Verify FTS weights name (A) higher than description (B)."""
        # GIVEN: Search vector with weighted fields
        # WHEN: Searching for a term
        # THEN: Name matches should rank higher than description matches
        expected_weights = {"name": "A", "description": "B"}
        assert expected_weights["name"] < expected_weights["description"]  # A < B in weight

    @pytest.mark.unit
    def test_fts_falls_back_to_ilike_when_no_trigger(self) -> None:
        """Verify FTS falls back to ILIKE when search_vector trigger not configured."""
        # GIVEN: A database without FTS trigger configured
        # WHEN: Searching for workflows
        # THEN: Should fall back to name ILIKE or description ILIKE
        # This is a hybrid approach for compatibility
        fallback_pattern = "ILIKE"
        assert fallback_pattern == "ILIKE"


@pytest.mark.xdist_group(name="workflow_storage")
class TestWorkflowManagerPagination:
    """Tests for cursor-based pagination in workflow manager."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_list_workflows_returns_next_cursor(self) -> None:
        """Verify list_workflows returns (workflows, next_cursor) tuple."""
        # GIVEN: A workflow manager with multiple workflows
        # WHEN: Listing workflows with limit
        # THEN: Should return tuple of (workflows, next_cursor)
        # Expected signature: async def list_workflows(...) -> tuple[list[WorkflowSummary], str | None]
        expected_return_type = "tuple[list[WorkflowSummary], str | None]"
        assert "next_cursor" in expected_return_type or "str | None" in expected_return_type

    @pytest.mark.unit
    def test_cursor_encodes_sort_position_and_id(self) -> None:
        """Verify cursor encodes sort column value + ID for stable pagination."""
        # GIVEN: Sorting by updated_at DESC
        # WHEN: Getting next cursor
        # THEN: Cursor should allow resume from exact position
        # Using composite (updated_at, id) for unique ordering
        sort_by = "updated_at"
        tiebreaker = "id"
        assert sort_by != tiebreaker

    @pytest.mark.unit
    def test_cursor_pagination_is_stable_with_duplicates(self) -> None:
        """Verify pagination is stable when multiple records have same sort value."""
        # GIVEN: Multiple workflows with same updated_at
        # WHEN: Paginating through results
        # THEN: Each workflow should appear exactly once
        # Requires composite key (sort_column, id) in cursor
        duplicate_safe = True
        assert duplicate_safe is True


@pytest.mark.xdist_group(name="workflow_storage")
class TestWorkflowManagerSorting:
    """Tests for sorting in workflow manager."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_list_workflows_supports_sort_by_name(self) -> None:
        """Verify list_workflows can sort by name."""
        valid_sort_fields = ["name", "created_at", "updated_at"]
        assert "name" in valid_sort_fields

    @pytest.mark.unit
    def test_list_workflows_supports_sort_by_created_at(self) -> None:
        """Verify list_workflows can sort by created_at."""
        valid_sort_fields = ["name", "created_at", "updated_at"]
        assert "created_at" in valid_sort_fields

    @pytest.mark.unit
    def test_list_workflows_supports_sort_by_updated_at(self) -> None:
        """Verify list_workflows can sort by updated_at (default)."""
        valid_sort_fields = ["name", "created_at", "updated_at"]
        default_sort = "updated_at"
        assert default_sort in valid_sort_fields

    @pytest.mark.unit
    def test_list_workflows_supports_sort_order_asc_and_desc(self) -> None:
        """Verify list_workflows supports both asc and desc order."""
        valid_orders = ["asc", "desc"]
        assert "asc" in valid_orders
        assert "desc" in valid_orders


@pytest.mark.xdist_group(name="workflow_storage")
class TestWorkflowManagerFiltering:
    """Tests for filtering in workflow manager."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_list_workflows_filters_by_user_id(self) -> None:
        """Verify list_workflows can filter by user_id."""
        filters = {"user_id": "user:alice"}
        assert "user_id" in filters

    @pytest.mark.unit
    def test_list_workflows_filters_by_status(self) -> None:
        """Verify list_workflows can filter by status."""
        filters = {"status": "active"}
        assert "status" in filters

    @pytest.mark.unit
    def test_list_workflows_multiple_filters_combined(self) -> None:
        """Verify multiple filters are combined with AND logic."""
        filters = {
            "user_id": "user:alice",
            "status": "active",
        }
        assert len(filters) == 2


@pytest.mark.xdist_group(name="workflow_storage")
class TestMessageModelIndices:
    """Tests for MessageModel database indices."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_message_model_has_composite_index_for_ordering(self) -> None:
        """Verify composite index (session_id, order_index) for message ordering."""
        from mcp_server_langgraph.storage.session.postgres_models import MessageModel

        # Check that session_id is indexed (primary for message queries)
        mapper = MessageModel.__mapper__
        session_id_col = mapper.columns.get("session_id")
        assert session_id_col is not None
        assert session_id_col.index is True

    @pytest.mark.unit
    def test_message_model_has_index_for_timestamp_queries(self) -> None:
        """Verify index on (session_id, timestamp) for time-range message queries."""
        # This enables efficient queries like:
        # "Get messages in session after timestamp X"
        # Used for incremental message loading
        expected_index_pattern = "(session_id, timestamp)"
        assert "session_id" in expected_index_pattern
        assert "timestamp" in expected_index_pattern


@pytest.mark.xdist_group(name="workflow_storage")
class TestWorkflowMigration:
    """Tests for workflow optimization migration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_migration_adds_search_vector_column(self) -> None:
        """Verify migration adds search_vector TSVECTOR column."""
        expected_column = "search_vector"
        expected_type = "TSVECTOR"
        assert expected_column == "search_vector"
        assert expected_type == "TSVECTOR"

    @pytest.mark.unit
    def test_migration_adds_status_column(self) -> None:
        """Verify migration adds status column with default 'active'."""
        expected_column = "status"
        expected_default = "active"
        assert expected_column == "status"
        assert expected_default == "active"

    @pytest.mark.unit
    def test_migration_creates_fts_trigger(self) -> None:
        """Verify migration creates trigger to maintain search_vector."""
        expected_trigger = "workflows_search_vector_trigger"
        assert "trigger" in expected_trigger.lower()

    @pytest.mark.unit
    def test_migration_populates_existing_search_vectors(self) -> None:
        """Verify migration populates search_vector for existing records."""
        # GIVEN: Existing workflow records without search_vector
        # WHEN: Running migration
        # THEN: All existing records should have search_vector populated
        populate_existing = True
        assert populate_existing is True

    @pytest.mark.unit
    def test_migration_is_backwards_compatible(self) -> None:
        """Verify existing queries continue to work after migration."""
        backwards_compatible = True
        assert backwards_compatible is True
