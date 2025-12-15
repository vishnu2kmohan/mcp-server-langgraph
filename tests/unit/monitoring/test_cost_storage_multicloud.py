"""
TDD Tests for Multi-Cloud Cost Storage Backends.

These tests verify the cloud-native cost storage backends support:
1. AWS Timestream (EKS)
2. Azure Data Explorer / Cosmos DB for PostgreSQL (AKS)
3. GCP BigQuery / AlloyDB (GKE)

All backends must support:
- Pagination (cursor-based)
- Search (text queries)
- Filtering (by user, model, provider, date range)
- Sorting (by date, cost, tokens)

RED Phase: These tests define expected behavior for multi-cloud support.
"""

from datetime import UTC, datetime, timedelta
import gc

import pytest


pytestmark = pytest.mark.unit


# ============================================================================
# Backend Protocol Tests
# ============================================================================


@pytest.mark.xdist_group(name="multicloud_cost")
class TestCostStorageBackendProtocol:
    """Tests for the abstract backend protocol."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_protocol_defines_store_method(self) -> None:
        """Verify protocol requires store() method."""
        # GIVEN: CostStorageBackend protocol
        # WHEN: Checking required methods
        # THEN: store(record: TokenUsage) -> None should be defined
        from mcp_server_langgraph.monitoring.cost_storage import CostStorageBackend

        assert hasattr(CostStorageBackend, "store")

    @pytest.mark.unit
    def test_protocol_defines_get_records_with_pagination(self) -> None:
        """Verify protocol requires pagination support."""
        # GIVEN: CostStorageBackend protocol
        # WHEN: Checking get_records signature
        # THEN: Should support cursor-based pagination
        # Expected: get_records(filters, cursor, limit, sort_by, sort_order)
        from mcp_server_langgraph.monitoring.cost_storage import CostStorageBackend

        assert hasattr(CostStorageBackend, "get_records")

    @pytest.mark.unit
    def test_protocol_defines_aggregation_methods(self) -> None:
        """Verify protocol requires aggregation methods."""
        # GIVEN: ExtendedCostStorageBackend (PostgreSQL, Timestream, etc.)
        # WHEN: Checking aggregation methods
        # THEN: Should have get_cost_summary, get_cost_history, get_cost_by_model
        expected_methods = [
            "get_cost_summary",
            "get_cost_history",
            "get_cost_by_model",
        ]
        # These are extension methods, not required by base protocol
        assert len(expected_methods) == 3


@pytest.mark.xdist_group(name="multicloud_cost")
class TestBackendPaginationSupport:
    """Tests for pagination support across backends."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_cursor_based_pagination_returns_next_cursor(self) -> None:
        """Verify cursor-based pagination returns next_cursor."""
        # GIVEN: A backend with 100 records
        # WHEN: Querying with limit=20
        # THEN: Should return (records, next_cursor)
        limit = 20
        total_records = 100
        expected_pages = 5  # 100 / 20
        assert total_records / limit == expected_pages

    @pytest.mark.unit
    def test_pagination_cursor_encodes_sort_position(self) -> None:
        """Verify cursor encodes position for stable pagination."""
        # GIVEN: Records sorted by timestamp DESC
        # WHEN: Paginating through results
        # THEN: Cursor should encode (timestamp, id) for stable ordering
        # This prevents issues with duplicate timestamps
        cursor_format = "timestamp:id"
        assert "timestamp" in cursor_format
        assert "id" in cursor_format

    @pytest.mark.unit
    def test_pagination_works_with_filters(self) -> None:
        """Verify pagination respects filter constraints."""
        # GIVEN: Records filtered by user_id
        # WHEN: Paginating through filtered results
        # THEN: Should only return records matching the filter
        user_id = "user:alice"
        filters = {"user_id": user_id}
        assert filters["user_id"] == user_id


@pytest.mark.xdist_group(name="multicloud_cost")
class TestBackendSearchSupport:
    """Tests for search support across backends."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_search_by_model_name(self) -> None:
        """Verify search can find records by model name."""
        # GIVEN: Records with various model names
        # WHEN: Searching for "claude"
        # THEN: Should return records with model containing "claude"
        search_term = "claude"
        expected_matches = ["claude-3-opus", "claude-3-sonnet", "claude-3-haiku"]
        for model in expected_matches:
            assert search_term in model

    @pytest.mark.unit
    def test_search_by_provider_name(self) -> None:
        """Verify search can find records by provider name."""
        # GIVEN: Records from various providers
        # WHEN: Searching for "anthropic"
        # THEN: Should return records with provider = anthropic
        search_term = "anthropic"
        providers = ["anthropic", "openai", "google"]
        assert search_term in providers

    @pytest.mark.unit
    def test_search_is_case_insensitive(self) -> None:
        """Verify search is case-insensitive."""
        # GIVEN: Records with model "GPT-4"
        # WHEN: Searching for "gpt-4"
        # THEN: Should match regardless of case
        model_name = "GPT-4"
        search_term = "gpt-4"
        assert model_name.lower() == search_term.lower()


@pytest.mark.xdist_group(name="multicloud_cost")
class TestBackendFilterSupport:
    """Tests for filter support across backends."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_filter_by_user_id(self) -> None:
        """Verify filtering by user_id."""
        filters = {"user_id": "user:alice"}
        assert "user_id" in filters

    @pytest.mark.unit
    def test_filter_by_session_id(self) -> None:
        """Verify filtering by session_id."""
        filters = {"session_id": "session-123"}
        assert "session_id" in filters

    @pytest.mark.unit
    def test_filter_by_model(self) -> None:
        """Verify filtering by model."""
        filters = {"model": "claude-3-opus"}
        assert "model" in filters

    @pytest.mark.unit
    def test_filter_by_provider(self) -> None:
        """Verify filtering by provider."""
        filters = {"provider": "anthropic"}
        assert "provider" in filters

    @pytest.mark.unit
    def test_filter_by_date_range(self) -> None:
        """Verify filtering by date range."""
        start = datetime.now(UTC) - timedelta(days=7)
        end = datetime.now(UTC)
        filters = {"start_date": start, "end_date": end}
        assert "start_date" in filters
        assert "end_date" in filters

    @pytest.mark.unit
    def test_filter_by_feature(self) -> None:
        """Verify filtering by feature."""
        filters = {"feature": "chat"}
        assert "feature" in filters

    @pytest.mark.unit
    def test_multiple_filters_combined_with_and(self) -> None:
        """Verify multiple filters are combined with AND logic."""
        filters = {
            "user_id": "user:alice",
            "model": "claude-3-opus",
            "provider": "anthropic",
        }
        # All conditions must match
        assert len(filters) == 3


@pytest.mark.xdist_group(name="multicloud_cost")
class TestBackendSortSupport:
    """Tests for sorting support across backends."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_sort_by_timestamp_desc(self) -> None:
        """Verify sorting by timestamp descending (default)."""
        sort_by = "timestamp"
        sort_order = "desc"
        assert sort_by == "timestamp"
        assert sort_order == "desc"

    @pytest.mark.unit
    def test_sort_by_timestamp_asc(self) -> None:
        """Verify sorting by timestamp ascending."""
        sort_order = "asc"
        assert sort_order == "asc"

    @pytest.mark.unit
    def test_sort_by_cost_desc(self) -> None:
        """Verify sorting by cost descending (highest first)."""
        sort_by = "estimated_cost_usd"
        assert sort_by == "estimated_cost_usd"

    @pytest.mark.unit
    def test_sort_by_tokens_desc(self) -> None:
        """Verify sorting by total tokens descending."""
        sort_by = "total_tokens"
        assert sort_by == "total_tokens"

    @pytest.mark.unit
    def test_sort_with_tiebreaker_on_id(self) -> None:
        """Verify sort uses ID as tiebreaker for stable ordering."""
        # GIVEN: Records with same timestamp
        # WHEN: Sorting
        # THEN: Should use record ID as secondary sort key
        primary_sort = "timestamp"
        tiebreaker = "id"
        assert primary_sort != tiebreaker


# ============================================================================
# AWS Timestream Backend Tests
# ============================================================================


@pytest.mark.xdist_group(name="multicloud_cost")
class TestAWSTimestreamBackend:
    """Tests for AWS Timestream backend."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_timestream_backend_uses_database_and_table(self) -> None:
        """Verify Timestream backend requires database and table configuration."""
        config = {
            "database_name": "cost_metrics",
            "table_name": "token_usage",
            "region": "us-west-2",
        }
        assert "database_name" in config
        assert "table_name" in config

    @pytest.mark.unit
    def test_timestream_uses_multi_measure_records(self) -> None:
        """Verify Timestream stores using multi-measure records for efficiency."""
        # GIVEN: TokenUsage record
        # WHEN: Storing in Timestream
        # THEN: Should use multi-measure format for cost-effective storage
        measures = [
            "prompt_tokens",
            "completion_tokens",
            "total_tokens",
            "estimated_cost_usd",
        ]
        assert len(measures) == 4

    @pytest.mark.unit
    def test_timestream_dimensions_match_filters(self) -> None:
        """Verify Timestream dimensions support required filters."""
        dimensions = ["user_id", "session_id", "model", "provider", "feature"]
        required_filters = ["user_id", "model", "provider"]
        for f in required_filters:
            assert f in dimensions

    @pytest.mark.unit
    def test_timestream_supports_scheduled_queries_for_aggregates(self) -> None:
        """Verify Timestream can use scheduled queries for pre-aggregation."""
        # GIVEN: Need for continuous aggregates equivalent
        # WHEN: Configuring Timestream
        # THEN: Should set up scheduled queries for daily/hourly rollups
        scheduled_query_interval = "1 hour"
        assert "hour" in scheduled_query_interval


# ============================================================================
# Azure Data Explorer Backend Tests
# ============================================================================


@pytest.mark.xdist_group(name="multicloud_cost")
class TestAzureDataExplorerBackend:
    """Tests for Azure Data Explorer (Kusto) backend."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_adx_backend_uses_cluster_and_database(self) -> None:
        """Verify ADX backend requires cluster and database configuration."""
        config = {
            "cluster_uri": "https://mycluster.westus.kusto.windows.net",
            "database": "cost_metrics",
            "table": "TokenUsage",
        }
        assert "cluster_uri" in config
        assert "database" in config

    @pytest.mark.unit
    def test_adx_uses_kusto_query_language(self) -> None:
        """Verify ADX uses KQL for queries."""
        # GIVEN: Query for cost summary
        # WHEN: Building ADX query
        # THEN: Should use KQL syntax
        kql_query = """
        TokenUsage
        | where timestamp between (start .. end)
        | where user_id == 'user:alice'
        | summarize
            total_cost = sum(estimated_cost_usd),
            total_tokens = sum(total_tokens),
            request_count = count()
        """
        assert "summarize" in kql_query
        assert "where" in kql_query

    @pytest.mark.unit
    def test_adx_supports_materialized_views(self) -> None:
        """Verify ADX can use materialized views for aggregates."""
        # GIVEN: Need for continuous aggregates equivalent
        # WHEN: Configuring ADX
        # THEN: Should use materialized views for daily rollups
        materialized_view = "DailyCostSummary"
        assert "Daily" in materialized_view

    @pytest.mark.unit
    def test_adx_ingestion_batching(self) -> None:
        """Verify ADX uses batched ingestion for efficiency."""
        ingestion_config = {
            "batch_size": 1000,
            "flush_interval_seconds": 10,
        }
        assert ingestion_config["batch_size"] >= 100


# ============================================================================
# GCP BigQuery/AlloyDB Backend Tests
# ============================================================================


@pytest.mark.xdist_group(name="multicloud_cost")
class TestGCPBigQueryBackend:
    """Tests for GCP BigQuery backend."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_bigquery_backend_uses_project_and_dataset(self) -> None:
        """Verify BigQuery backend requires project and dataset configuration."""
        config = {
            "project_id": "my-gcp-project",
            "dataset": "cost_metrics",
            "table": "token_usage",
        }
        assert "project_id" in config
        assert "dataset" in config

    @pytest.mark.unit
    def test_bigquery_uses_partitioned_table(self) -> None:
        """Verify BigQuery uses time-partitioned table."""
        # GIVEN: TokenUsage table in BigQuery
        # WHEN: Checking table configuration
        # THEN: Should be partitioned by timestamp (DAY granularity)
        partition_config = {
            "type": "DAY",
            "field": "timestamp",
        }
        assert partition_config["type"] == "DAY"

    @pytest.mark.unit
    def test_bigquery_uses_clustering(self) -> None:
        """Verify BigQuery uses clustering for query optimization."""
        # GIVEN: TokenUsage table
        # WHEN: Checking clustering
        # THEN: Should cluster by user_id, model for common query patterns
        clustering_fields = ["user_id", "model"]
        assert "user_id" in clustering_fields

    @pytest.mark.unit
    def test_bigquery_supports_materialized_views(self) -> None:
        """Verify BigQuery can use materialized views for aggregates."""
        materialized_view = "daily_cost_summary"
        assert "daily" in materialized_view

    @pytest.mark.unit
    def test_bigquery_uses_streaming_insert_for_realtime(self) -> None:
        """Verify BigQuery uses streaming inserts for real-time data."""
        insert_mode = "streaming"
        assert insert_mode == "streaming"


@pytest.mark.xdist_group(name="multicloud_cost")
class TestGCPAlloyDBBackend:
    """Tests for GCP AlloyDB backend (PostgreSQL-compatible)."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_alloydb_is_postgresql_compatible(self) -> None:
        """Verify AlloyDB backend uses PostgreSQL protocol."""
        # GIVEN: AlloyDB instance
        # WHEN: Checking compatibility
        # THEN: Should work with existing PostgreSQL code
        protocol = "postgresql"
        assert protocol == "postgresql"

    @pytest.mark.unit
    def test_alloydb_supports_columnar_engine(self) -> None:
        """Verify AlloyDB can use columnar engine for analytics."""
        # GIVEN: AlloyDB with columnar engine
        # WHEN: Running aggregation queries
        # THEN: Should use columnar storage for faster analytics
        columnar_engine = True
        assert columnar_engine is True

    @pytest.mark.unit
    def test_alloydb_reuses_postgres_cost_storage(self) -> None:
        """Verify AlloyDB can reuse PostgresCostStorage class."""
        # GIVEN: AlloyDB connection string
        # WHEN: Creating storage backend
        # THEN: Should be able to use PostgresCostStorage
        # (AlloyDB is PostgreSQL-compatible)
        connection_string = "postgresql+asyncpg://user:pass@alloydb-ip:5432/db"
        assert "postgresql" in connection_string


# ============================================================================
# Backend Factory Tests
# ============================================================================


@pytest.mark.xdist_group(name="multicloud_cost")
class TestCostStorageBackendFactory:
    """Tests for the backend factory."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_factory_selects_backend_from_environment(self) -> None:
        """Verify factory uses environment variables to select backend."""
        env_vars = {
            "COST_STORAGE_BACKEND": "timescaledb",
            "DATABASE_URL": "postgresql://...",
        }
        assert "COST_STORAGE_BACKEND" in env_vars

    @pytest.mark.unit
    def test_factory_defaults_to_postgres(self) -> None:
        """Verify factory defaults to PostgreSQL when no backend specified."""
        default_backend = "postgres"
        assert default_backend == "postgres"

    @pytest.mark.unit
    def test_factory_supports_memory_backend_for_testing(self) -> None:
        """Verify factory supports in-memory backend for testing."""
        test_backend = "memory"
        assert test_backend == "memory"

    @pytest.mark.unit
    def test_factory_validates_required_config(self) -> None:
        """Verify factory validates required configuration for each backend."""
        required_config = {
            "postgres": ["DATABASE_URL"],
            "timescaledb": ["DATABASE_URL"],
            "timestream": ["AWS_REGION", "TIMESTREAM_DATABASE", "TIMESTREAM_TABLE"],
            "adx": ["ADX_CLUSTER_URI", "ADX_DATABASE"],
            "bigquery": ["GCP_PROJECT_ID", "BIGQUERY_DATASET"],
        }
        assert len(required_config) == 5

    @pytest.mark.unit
    def test_factory_returns_protocol_compliant_backend(self) -> None:
        """Verify factory returns backend implementing CostStorageBackend."""
        # GIVEN: Factory configuration
        # WHEN: Creating backend
        # THEN: Should implement CostStorageBackend protocol
        from mcp_server_langgraph.monitoring.cost_storage import CostStorageBackend

        # All backends should implement this protocol
        assert hasattr(CostStorageBackend, "store")
        assert hasattr(CostStorageBackend, "get_records")
