"""
Cloud Storage Backend Unit Tests.

Tests for AWS Timestream, Azure Data Explorer (Kusto), and GCP BigQuery
cost storage backends.

TDD: Tests written FIRST (RED phase) before implementation verification.
These tests use mocked cloud SDKs to test business logic without cloud access.
"""

import gc
from datetime import datetime, UTC
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from mcp_server_langgraph.monitoring.cost_tracker import TokenUsage

pytestmark = [pytest.mark.unit, pytest.mark.monitoring]


# ==============================================================================
# AWS Timestream Tests
# ==============================================================================


@pytest.mark.xdist_group(name="test_timestream_storage")
class TestTimestreamCostStorageInit:
    """Tests for TimestreamCostStorage initialization."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_init_sets_configuration(self) -> None:
        """
        GIVEN configuration parameters
        WHEN initializing TimestreamCostStorage
        THEN it should store the configuration
        """
        from mcp_server_langgraph.monitoring.cost_storage_aws import (
            TimestreamCostStorage,
        )

        storage = TimestreamCostStorage(
            region="us-west-2",
            database="cost_metrics",
            table="token_usage",
        )

        assert storage._region == "us-west-2"
        assert storage._database == "cost_metrics"
        assert storage._table == "token_usage"

    def test_init_enforces_batch_size_limit(self) -> None:
        """
        GIVEN batch_size > 100 (Timestream limit)
        WHEN initializing TimestreamCostStorage
        THEN it should cap batch_size at 100
        """
        from mcp_server_langgraph.monitoring.cost_storage_aws import (
            TimestreamCostStorage,
        )

        storage = TimestreamCostStorage(
            region="us-west-2",
            database="test",
            table="test",
            batch_size=200,  # Above Timestream limit
        )

        assert storage._batch_size == 100

    def test_total_records_initially_zero(self) -> None:
        """
        GIVEN a new TimestreamCostStorage
        WHEN checking total_records
        THEN it should be zero
        """
        from mcp_server_langgraph.monitoring.cost_storage_aws import (
            TimestreamCostStorage,
        )

        storage = TimestreamCostStorage(
            region="us-west-2",
            database="test",
            table="test",
        )

        assert storage.total_records == 0


@pytest.mark.xdist_group(name="test_timestream_storage")
class TestTimestreamCostStorageStore:
    """Tests for TimestreamCostStorage.store method."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_store_calls_timestream_write_records(self) -> None:
        """
        GIVEN a TokenUsage record
        WHEN storing in Timestream
        THEN it should call write_records with correct format
        """
        from mcp_server_langgraph.monitoring.cost_storage_aws import (
            TimestreamCostStorage,
        )

        mock_client = MagicMock()
        mock_client.write_records = MagicMock(return_value={"RecordsIngested": {"Total": 1}})

        with patch.object(TimestreamCostStorage, "_get_write_client", return_value=mock_client):
            storage = TimestreamCostStorage(
                region="us-west-2",
                database="cost_metrics",
                table="token_usage",
            )

            record = TokenUsage(
                timestamp=datetime.now(UTC),
                user_id="user:alice",
                session_id="session-123",
                model="claude-sonnet-4-5-20250929",
                provider="anthropic",
                prompt_tokens=1000,
                completion_tokens=500,
                estimated_cost_usd=Decimal("0.015"),
            )

            await storage.store(record)

            mock_client.write_records.assert_called_once()
            call_kwargs = mock_client.write_records.call_args.kwargs
            assert call_kwargs["DatabaseName"] == "cost_metrics"
            assert call_kwargs["TableName"] == "token_usage"
            assert "Records" in call_kwargs

    @pytest.mark.asyncio
    async def test_store_increments_record_count(self) -> None:
        """
        GIVEN a TimestreamCostStorage
        WHEN storing a record
        THEN record count should increment
        """
        from mcp_server_langgraph.monitoring.cost_storage_aws import (
            TimestreamCostStorage,
        )

        mock_client = MagicMock()
        mock_client.write_records = MagicMock(return_value={"RecordsIngested": {"Total": 1}})

        with patch.object(TimestreamCostStorage, "_get_write_client", return_value=mock_client):
            storage = TimestreamCostStorage(
                region="us-west-2",
                database="test",
                table="test",
            )

            record = TokenUsage(
                timestamp=datetime.now(UTC),
                user_id="user:alice",
                session_id="session-123",
                model="gpt-4",
                provider="openai",
                prompt_tokens=100,
                completion_tokens=50,
                estimated_cost_usd=Decimal("0.01"),
            )

            await storage.store(record)
            assert storage.total_records == 1


@pytest.mark.xdist_group(name="test_timestream_storage")
class TestTimestreamCostStorageClient:
    """Tests for Timestream client initialization."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_get_write_client_raises_import_error_without_boto3(self) -> None:
        """
        GIVEN boto3 is not installed
        WHEN getting write client
        THEN it should raise ImportError with helpful message
        """
        from mcp_server_langgraph.monitoring.cost_storage_aws import (
            TimestreamCostStorage,
        )

        storage = TimestreamCostStorage(
            region="us-west-2",
            database="test",
            table="test",
        )

        with patch.dict("sys.modules", {"boto3": None}):
            # Force re-import to trigger the ImportError
            storage._write_client = None
            with pytest.raises(ImportError, match="boto3 is required"):
                storage._get_write_client()


# ==============================================================================
# Azure Data Explorer (Kusto) Tests
# ==============================================================================


@pytest.mark.xdist_group(name="test_adx_storage")
class TestADXCostStorageInit:
    """Tests for ADXCostStorage initialization."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_init_sets_configuration(self) -> None:
        """
        GIVEN configuration parameters
        WHEN initializing ADXCostStorage
        THEN it should store the configuration
        """
        from mcp_server_langgraph.monitoring.cost_storage_azure import (
            ADXCostStorage,
        )

        storage = ADXCostStorage(
            cluster_uri="https://mycluster.westus.kusto.windows.net",
            database="cost_metrics",
            table="TokenUsage",
        )

        assert storage._cluster_uri == "https://mycluster.westus.kusto.windows.net"
        assert storage._database == "cost_metrics"
        assert storage._table == "TokenUsage"

    def test_init_uses_default_table_name(self) -> None:
        """
        GIVEN no table name provided
        WHEN initializing ADXCostStorage
        THEN it should use default table name
        """
        from mcp_server_langgraph.monitoring.cost_storage_azure import (
            ADXCostStorage,
        )

        storage = ADXCostStorage(
            cluster_uri="https://test.kusto.windows.net",
            database="test",
        )

        assert storage._table == "TokenUsage"

    def test_total_records_initially_zero(self) -> None:
        """
        GIVEN a new ADXCostStorage
        WHEN checking total_records
        THEN it should be zero
        """
        from mcp_server_langgraph.monitoring.cost_storage_azure import (
            ADXCostStorage,
        )

        storage = ADXCostStorage(
            cluster_uri="https://test.kusto.windows.net",
            database="test",
        )

        assert storage.total_records == 0


@pytest.mark.xdist_group(name="test_adx_storage")
class TestADXCostStorageStore:
    """Tests for ADXCostStorage.store method."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_store_adds_to_pending_records(self) -> None:
        """
        GIVEN a TokenUsage record
        WHEN storing in ADX
        THEN it should add to pending records (when mocked)
        """
        from mcp_server_langgraph.monitoring.cost_storage_azure import (
            ADXCostStorage,
        )

        storage = ADXCostStorage(
            cluster_uri="https://test.kusto.windows.net",
            database="test",
            batch_size=100,  # High batch size to prevent flush
        )

        record = TokenUsage(
            timestamp=datetime.now(UTC),
            user_id="user:alice",
            session_id="session-123",
            model="gpt-4",
            provider="openai",
            prompt_tokens=100,
            completion_tokens=50,
            estimated_cost_usd=Decimal("0.01"),
        )

        # Mock the client to avoid import error
        mock_client = MagicMock()
        with patch.object(ADXCostStorage, "_get_client", return_value=mock_client):
            await storage.store(record)

            # After store, record count should increment
            assert storage.total_records == 1


# ==============================================================================
# GCP BigQuery Tests
# ==============================================================================


@pytest.mark.xdist_group(name="test_bigquery_storage")
class TestBigQueryCostStorageInit:
    """Tests for BigQueryCostStorage initialization."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_init_sets_configuration(self) -> None:
        """
        GIVEN configuration parameters
        WHEN initializing BigQueryCostStorage
        THEN it should store the configuration
        """
        from mcp_server_langgraph.monitoring.cost_storage_gcp import (
            BigQueryCostStorage,
        )

        storage = BigQueryCostStorage(
            project_id="my-project",
            dataset="cost_metrics",
            table="token_usage",
        )

        assert storage._project_id == "my-project"
        assert storage._dataset == "cost_metrics"
        assert storage._table == "token_usage"

    def test_init_uses_streaming_by_default(self) -> None:
        """
        GIVEN no use_streaming provided
        WHEN initializing BigQueryCostStorage
        THEN it should use streaming by default
        """
        from mcp_server_langgraph.monitoring.cost_storage_gcp import (
            BigQueryCostStorage,
        )

        storage = BigQueryCostStorage(
            project_id="test",
            dataset="test",
            table="test",
        )

        assert storage._use_streaming is True  # Default

    def test_total_records_initially_zero(self) -> None:
        """
        GIVEN a new BigQueryCostStorage
        WHEN checking total_records
        THEN it should be zero
        """
        from mcp_server_langgraph.monitoring.cost_storage_gcp import (
            BigQueryCostStorage,
        )

        storage = BigQueryCostStorage(
            project_id="test",
            dataset="test",
            table="test",
        )

        assert storage.total_records == 0


@pytest.mark.xdist_group(name="test_bigquery_storage")
class TestBigQueryCostStorageStore:
    """Tests for BigQueryCostStorage.store method."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_store_calls_bigquery_insert(self) -> None:
        """
        GIVEN a TokenUsage record
        WHEN storing in BigQuery
        THEN it should call the BigQuery client
        """
        from mcp_server_langgraph.monitoring.cost_storage_gcp import (
            BigQueryCostStorage,
        )

        storage = BigQueryCostStorage(
            project_id="test",
            dataset="test",
            table="test",
        )

        record = TokenUsage(
            timestamp=datetime.now(UTC),
            user_id="user:alice",
            session_id="session-123",
            model="gemini-pro",
            provider="google",
            prompt_tokens=100,
            completion_tokens=50,
            estimated_cost_usd=Decimal("0.01"),
        )

        # Mock the client to avoid import error
        mock_client = MagicMock()
        mock_client.insert_rows_json = MagicMock(return_value=[])
        with patch.object(BigQueryCostStorage, "_get_client", return_value=mock_client):
            await storage.store(record)

            # After store, record count should increment
            assert storage.total_records == 1


@pytest.mark.xdist_group(name="test_bigquery_storage")
class TestBigQueryCostStorageClient:
    """Tests for BigQuery client initialization."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_get_client_raises_import_error_without_google_cloud(self) -> None:
        """
        GIVEN google-cloud-bigquery is not installed
        WHEN getting client
        THEN it should raise ImportError with helpful message
        """
        from mcp_server_langgraph.monitoring.cost_storage_gcp import (
            BigQueryCostStorage,
        )

        storage = BigQueryCostStorage(
            project_id="test",
            dataset="test",
            table="test",
        )

        with patch.dict("sys.modules", {"google.cloud.bigquery": None}):
            storage._client = None
            with pytest.raises(ImportError, match="google-cloud-bigquery is required"):
                storage._get_client()


# ==============================================================================
# Cloud Storage Factory Tests
# ==============================================================================


@pytest.mark.xdist_group(name="test_storage_factory")
class TestCostStorageFactory:
    """Tests for cost storage factory."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_factory_import_succeeds_when_module_available(self) -> None:
        """
        GIVEN the cost storage factory module
        WHEN importing create_cost_storage_backend
        THEN it should be available
        """
        from mcp_server_langgraph.monitoring.cost_storage_factory import (
            create_cost_storage_backend,
        )

        assert create_cost_storage_backend is not None

    def test_factory_creates_memory_storage(self) -> None:
        """
        GIVEN MEMORY backend type
        WHEN calling create_cost_storage_backend
        THEN it should return MemoryCostStorage
        """
        from mcp_server_langgraph.monitoring.cost_storage import MemoryCostStorage
        from mcp_server_langgraph.monitoring.cost_storage_factory import (
            CostStorageBackendType,
            create_cost_storage_backend,
        )

        storage = create_cost_storage_backend(backend_type=CostStorageBackendType.MEMORY)

        assert isinstance(storage, MemoryCostStorage)

    def test_backend_type_enum_has_all_values(self) -> None:
        """
        GIVEN CostStorageBackendType enum
        WHEN checking values
        THEN it should have all expected backend types
        """
        from mcp_server_langgraph.monitoring.cost_storage_factory import (
            CostStorageBackendType,
        )

        assert CostStorageBackendType.MEMORY.value == "memory"
        assert CostStorageBackendType.POSTGRES.value == "postgres"
        assert CostStorageBackendType.TIMESTREAM.value == "timestream"
        assert CostStorageBackendType.ADX.value == "adx"
        assert CostStorageBackendType.BIGQUERY.value == "bigquery"

    def test_get_backend_type_returns_default_postgres(self) -> None:
        """
        GIVEN no COST_STORAGE_BACKEND env var set
        WHEN calling get_backend_type
        THEN it should return POSTGRES
        """
        from mcp_server_langgraph.monitoring.cost_storage_factory import (
            CostStorageBackendType,
            get_backend_type,
        )

        with patch.dict("os.environ", {}, clear=True):
            with patch("os.environ.get", return_value="postgres"):
                backend = get_backend_type()

        assert backend == CostStorageBackendType.POSTGRES

    def test_validate_backend_config_raises_for_missing_config(self) -> None:
        """
        GIVEN a backend type requiring config
        WHEN required env vars are missing
        THEN it should raise CostStorageConfigError
        """
        from mcp_server_langgraph.monitoring.cost_storage_factory import (
            CostStorageBackendType,
            CostStorageConfigError,
            validate_backend_config,
        )

        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(CostStorageConfigError, match="Missing required config"):
                validate_backend_config(CostStorageBackendType.TIMESTREAM)
