"""
GCP BigQuery Cost Storage Backend.

Provides cost storage using Google BigQuery for GKE deployments.
BigQuery is optimized for analytics workloads with:
- Automatic table partitioning by time
- Clustering for query optimization
- Materialized views for pre-aggregation
- Native GCP IAM / Workload Identity integration

Configuration:
- GCP_PROJECT_ID: GCP project ID
- BIGQUERY_DATASET: BigQuery dataset name
- BIGQUERY_TABLE: BigQuery table name (default: token_usage)

Requires: google-cloud-bigquery (optional dependency)
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from decimal import Decimal
from typing import Any

from mcp_server_langgraph.monitoring.cost_storage import (
    CostSummary,
    DailyCost,
    ModelCost,
)
from mcp_server_langgraph.monitoring.cost_tracker import TokenUsage


class BigQueryCostStorage:
    """
    GCP BigQuery storage backend for cost metrics.

    Uses partitioned tables with clustering for efficient queries:
    - Partitioned by: timestamp (DAY granularity)
    - Clustered by: user_id, model

    Supports pagination, filtering, sorting, and aggregation queries.
    """

    def __init__(
        self,
        project_id: str,
        dataset: str,
        table: str = "token_usage",
        use_streaming: bool = True,
    ) -> None:
        """
        Initialize BigQuery storage.

        Args:
            project_id: GCP project ID
            dataset: BigQuery dataset name
            table: BigQuery table name
            use_streaming: Use streaming inserts (faster, higher cost)
        """
        self._project_id = project_id
        self._dataset = dataset
        self._table = table
        self._use_streaming = use_streaming
        self._client: Any = None
        self._record_count = 0

    def _get_client(self) -> Any:
        """Get or create BigQuery client."""
        if self._client is None:
            try:
                from google.cloud import bigquery

                self._client = bigquery.Client(project=self._project_id)
            except ImportError:
                msg = "google-cloud-bigquery is required for BigQuery backend. Install with: pip install google-cloud-bigquery"
                raise ImportError(msg) from None
        return self._client

    @property
    def _table_id(self) -> str:
        """Get fully qualified table ID."""
        return f"{self._project_id}.{self._dataset}.{self._table}"

    @property
    def total_records(self) -> int:
        """Get the total number of stored records (tracked locally)."""
        return self._record_count

    async def store(self, record: TokenUsage) -> None:
        """
        Store a token usage record in BigQuery.

        Uses streaming insert for real-time availability.

        Args:
            record: TokenUsage record to store
        """
        client = self._get_client()

        row = {
            "timestamp": record.timestamp.isoformat(),
            "user_id": record.user_id,
            "session_id": record.session_id,
            "model": record.model,
            "provider": record.provider,
            "feature": record.feature,
            "prompt_tokens": record.prompt_tokens,
            "completion_tokens": record.completion_tokens,
            "total_tokens": record.total_tokens,
            "estimated_cost_usd": float(record.estimated_cost_usd),
        }

        loop = asyncio.get_event_loop()

        if self._use_streaming:
            # Streaming insert for real-time availability
            await loop.run_in_executor(
                None,
                lambda: client.insert_rows_json(self._table_id, [row]),
            )
        else:
            # Load job for batch inserts (cheaper, but delayed availability)
            from google.cloud import bigquery

            job_config = bigquery.LoadJobConfig(
                write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
            )
            await loop.run_in_executor(
                None,
                lambda: client.load_table_from_json(
                    [row],
                    self._table_id,
                    job_config=job_config,
                ).result(),
            )

        self._record_count += 1

    async def get_records(
        self,
        filters: dict[str, Any] | None = None,
        cursor: str | None = None,
        limit: int = 100,
        sort_by: str = "timestamp",
        sort_order: str = "DESC",
    ) -> tuple[list[TokenUsage], str | None]:
        """
        Get stored records with pagination, filtering, and sorting.

        Args:
            filters: Optional filters (user_id, model, provider, start_date, end_date)
            cursor: Pagination cursor (timestamp for next page)
            limit: Maximum records to return
            sort_by: Sort field
            sort_order: Sort order (ASC, DESC)

        Returns:
            Tuple of (records, next_cursor)
        """
        client = self._get_client()

        # Build SQL query (table_id from config, not user input)
        query = f"""
            SELECT
                timestamp,
                user_id,
                session_id,
                model,
                provider,
                feature,
                prompt_tokens,
                completion_tokens,
                total_tokens,
                estimated_cost_usd
            FROM `{self._table_id}`
            WHERE 1=1
        """

        params = []

        if filters:
            if "user_id" in filters:
                query += " AND user_id = @user_id"
                params.append(("user_id", "STRING", filters["user_id"]))
            if "model" in filters:
                query += " AND model = @model"
                params.append(("model", "STRING", filters["model"]))
            if "provider" in filters:
                query += " AND provider = @provider"
                params.append(("provider", "STRING", filters["provider"]))
            if "session_id" in filters:
                query += " AND session_id = @session_id"
                params.append(("session_id", "STRING", filters["session_id"]))
            if "start_date" in filters:
                query += " AND timestamp >= @start_date"
                params.append(("start_date", "TIMESTAMP", filters["start_date"]))
            if "end_date" in filters:
                query += " AND timestamp <= @end_date"
                params.append(("end_date", "TIMESTAMP", filters["end_date"]))

        if cursor:
            if sort_order.upper() == "DESC":
                query += " AND timestamp < @cursor"
            else:
                query += " AND timestamp > @cursor"
            params.append(("cursor", "TIMESTAMP", datetime.fromisoformat(cursor)))

        query += f" ORDER BY {sort_by} {sort_order}"
        query += f" LIMIT {limit + 1}"

        # Build job config with parameters
        from google.cloud import bigquery

        job_config = bigquery.QueryJobConfig(
            query_parameters=[bigquery.ScalarQueryParameter(name, type_, value) for name, type_, value in params]
        )

        # Execute query
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: client.query(query, job_config=job_config).result(),
        )

        # Parse results
        records: list[TokenUsage] = []
        rows = list(result)

        for row in rows[:limit]:
            records.append(
                TokenUsage(
                    timestamp=row.timestamp,
                    user_id=row.user_id,
                    session_id=row.session_id,
                    model=row.model,
                    provider=row.provider,
                    feature=row.feature,
                    prompt_tokens=row.prompt_tokens,
                    completion_tokens=row.completion_tokens,
                    total_tokens=row.total_tokens,
                    estimated_cost_usd=Decimal(str(row.estimated_cost_usd)),
                )
            )

        # Determine next cursor
        next_cursor = None
        if len(rows) > limit:
            last_record = records[-1]
            next_cursor = last_record.timestamp.isoformat()

        return records, next_cursor

    async def delete_records_before(self, cutoff: datetime) -> int:
        """
        Delete records older than cutoff.

        Uses BigQuery DELETE statement (requires write permissions).

        Args:
            cutoff: Cutoff datetime

        Returns:
            Number of records deleted
        """
        client = self._get_client()

        # Count records first (table_id from config, not user input)
        count_query = f"""
            SELECT COUNT(*) as count
            FROM `{self._table_id}`
            WHERE timestamp < @cutoff
        """

        from google.cloud import bigquery

        job_config = bigquery.QueryJobConfig(query_parameters=[bigquery.ScalarQueryParameter("cutoff", "TIMESTAMP", cutoff)])

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: client.query(count_query, job_config=job_config).result(),
        )

        count: int = int(list(result)[0].count)

        # Delete records (table_id from config, not user input)
        delete_query = f"""
            DELETE FROM `{self._table_id}`
            WHERE timestamp < @cutoff
        """

        await loop.run_in_executor(
            None,
            lambda: client.query(delete_query, job_config=job_config).result(),
        )

        self._record_count = max(0, self._record_count - count)
        return count

    async def get_latest_record(self) -> TokenUsage | None:
        """
        Get the most recently stored record.

        Returns:
            Latest TokenUsage record or None if empty
        """
        records, _ = await self.get_records(limit=1, sort_order="DESC")
        return records[0] if records else None

    async def get_cost_summary(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        user_id: str | None = None,
    ) -> CostSummary:
        """
        Get aggregated cost summary.

        Args:
            start_date: Start of period
            end_date: End of period
            user_id: Optional user filter

        Returns:
            CostSummary with aggregated metrics
        """
        client = self._get_client()

        query = f"""
            SELECT
                COALESCE(SUM(estimated_cost_usd), 0) as total_cost,
                COALESCE(SUM(prompt_tokens), 0) as total_prompt_tokens,
                COALESCE(SUM(completion_tokens), 0) as total_completion_tokens,
                COALESCE(SUM(total_tokens), 0) as total_tokens,
                COUNT(*) as request_count,
                MIN(timestamp) as period_start,
                MAX(timestamp) as period_end
            FROM `{self._table_id}`
            WHERE 1=1
        """

        from google.cloud import bigquery

        params = []

        if start_date:
            query += " AND timestamp >= @start_date"
            params.append(bigquery.ScalarQueryParameter("start_date", "TIMESTAMP", start_date))
        if end_date:
            query += " AND timestamp <= @end_date"
            params.append(bigquery.ScalarQueryParameter("end_date", "TIMESTAMP", end_date))
        if user_id:
            query += " AND user_id = @user_id"
            params.append(bigquery.ScalarQueryParameter("user_id", "STRING", user_id))

        job_config = bigquery.QueryJobConfig(query_parameters=params)

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: client.query(query, job_config=job_config).result(),
        )

        rows = list(result)
        if rows:
            row = rows[0]
            return CostSummary(
                total_cost=Decimal(str(row.total_cost)),
                total_prompt_tokens=int(row.total_prompt_tokens),
                total_completion_tokens=int(row.total_completion_tokens),
                total_tokens=int(row.total_tokens),
                request_count=int(row.request_count),
                period_start=row.period_start,
                period_end=row.period_end,
            )

        return CostSummary(
            total_cost=Decimal("0"),
            total_prompt_tokens=0,
            total_completion_tokens=0,
            total_tokens=0,
            request_count=0,
        )

    async def get_cost_history(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        user_id: str | None = None,
        bucket_interval: str = "DAY",
    ) -> list[DailyCost]:
        """
        Get cost history over time using TIMESTAMP_TRUNC.

        Args:
            start_date: Start of period
            end_date: End of period
            user_id: Optional user filter
            bucket_interval: Time bucket (HOUR, DAY, WEEK)

        Returns:
            List of DailyCost entries
        """
        client = self._get_client()

        query = f"""
            SELECT
                TIMESTAMP_TRUNC(timestamp, {bucket_interval}) as bucket,
                SUM(estimated_cost_usd) as total_cost,
                SUM(total_tokens) as total_tokens,
                COUNT(*) as request_count
            FROM `{self._table_id}`
            WHERE 1=1
        """

        from google.cloud import bigquery

        params = []

        if start_date:
            query += " AND timestamp >= @start_date"
            params.append(bigquery.ScalarQueryParameter("start_date", "TIMESTAMP", start_date))
        if end_date:
            query += " AND timestamp <= @end_date"
            params.append(bigquery.ScalarQueryParameter("end_date", "TIMESTAMP", end_date))
        if user_id:
            query += " AND user_id = @user_id"
            params.append(bigquery.ScalarQueryParameter("user_id", "STRING", user_id))

        query += " GROUP BY bucket ORDER BY bucket ASC"

        job_config = bigquery.QueryJobConfig(query_parameters=params)

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: client.query(query, job_config=job_config).result(),
        )

        results: list[DailyCost] = []
        for row in result:
            results.append(
                DailyCost(
                    date=row.bucket,
                    total_cost=Decimal(str(row.total_cost)),
                    total_tokens=int(row.total_tokens),
                    request_count=int(row.request_count),
                )
            )

        return results

    async def get_cost_by_model(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        user_id: str | None = None,
    ) -> list[ModelCost]:
        """
        Get cost breakdown by model.

        Args:
            start_date: Start of period
            end_date: End of period
            user_id: Optional user filter

        Returns:
            List of ModelCost entries ordered by cost
        """
        client = self._get_client()

        query = f"""
            SELECT
                model,
                provider,
                SUM(estimated_cost_usd) as total_cost,
                SUM(prompt_tokens) as total_prompt_tokens,
                SUM(completion_tokens) as total_completion_tokens,
                COUNT(*) as request_count
            FROM `{self._table_id}`
            WHERE 1=1
        """

        from google.cloud import bigquery

        params = []

        if start_date:
            query += " AND timestamp >= @start_date"
            params.append(bigquery.ScalarQueryParameter("start_date", "TIMESTAMP", start_date))
        if end_date:
            query += " AND timestamp <= @end_date"
            params.append(bigquery.ScalarQueryParameter("end_date", "TIMESTAMP", end_date))
        if user_id:
            query += " AND user_id = @user_id"
            params.append(bigquery.ScalarQueryParameter("user_id", "STRING", user_id))

        query += " GROUP BY model, provider ORDER BY total_cost DESC"

        job_config = bigquery.QueryJobConfig(query_parameters=params)

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: client.query(query, job_config=job_config).result(),
        )

        results: list[ModelCost] = []
        for row in result:
            results.append(
                ModelCost(
                    model=row.model,
                    provider=row.provider,
                    total_cost=Decimal(str(row.total_cost)),
                    total_prompt_tokens=int(row.total_prompt_tokens),
                    total_completion_tokens=int(row.total_completion_tokens),
                    request_count=int(row.request_count),
                )
            )

        return results
