"""
AWS Timestream Cost Storage Backend.

Provides cost storage using Amazon Timestream for EKS deployments.
Timestream is optimized for time-series data with:
- Automatic data tiering (memory -> magnetic)
- Built-in time-series functions
- Scheduled queries for aggregations
- Native AWS IAM integration

Configuration:
- AWS_REGION: AWS region (e.g., us-west-2)
- TIMESTREAM_DATABASE: Timestream database name
- TIMESTREAM_TABLE: Timestream table name

Requires: boto3 (optional dependency)
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


class TimestreamCostStorage:
    """
    AWS Timestream storage backend for cost metrics.

    Uses multi-measure records for efficient storage:
    - Dimensions: user_id, session_id, model, provider, feature
    - Measures: prompt_tokens, completion_tokens, total_tokens, estimated_cost_usd

    Supports pagination, filtering, sorting, and aggregation queries.
    """

    def __init__(
        self,
        region: str,
        database: str,
        table: str,
        batch_size: int = 100,
    ) -> None:
        """
        Initialize Timestream storage.

        Args:
            region: AWS region
            database: Timestream database name
            table: Timestream table name
            batch_size: Batch size for writes (max 100)
        """
        self._region = region
        self._database = database
        self._table = table
        self._batch_size = min(batch_size, 100)  # Timestream limit
        self._write_client: Any = None
        self._query_client: Any = None
        self._record_count = 0

    def _get_write_client(self) -> Any:
        """Get or create Timestream write client."""
        if self._write_client is None:
            try:
                import boto3

                self._write_client = boto3.client(
                    "timestream-write",
                    region_name=self._region,
                )
            except ImportError:
                msg = "boto3 is required for Timestream backend. Install with: pip install boto3"
                raise ImportError(msg) from None
        return self._write_client

    def _get_query_client(self) -> Any:
        """Get or create Timestream query client."""
        if self._query_client is None:
            try:
                import boto3

                self._query_client = boto3.client(
                    "timestream-query",
                    region_name=self._region,
                )
            except ImportError:
                msg = "boto3 is required for Timestream backend. Install with: pip install boto3"
                raise ImportError(msg) from None
        return self._query_client

    @property
    def total_records(self) -> int:
        """Get the total number of stored records (tracked locally)."""
        return self._record_count

    async def store(self, record: TokenUsage) -> None:
        """
        Store a token usage record in Timestream.

        Uses multi-measure record format for efficiency.

        Args:
            record: TokenUsage record to store
        """
        client = self._get_write_client()

        # Build dimensions
        dimensions = [
            {"Name": "user_id", "Value": record.user_id},
            {"Name": "session_id", "Value": record.session_id},
            {"Name": "model", "Value": record.model},
            {"Name": "provider", "Value": record.provider},
        ]

        if record.feature:
            dimensions.append({"Name": "feature", "Value": record.feature})

        # Build multi-measure record
        timestream_record = {
            "Dimensions": dimensions,
            "MeasureName": "token_usage",
            "MeasureValueType": "MULTI",
            "MeasureValues": [
                {
                    "Name": "prompt_tokens",
                    "Value": str(record.prompt_tokens),
                    "Type": "BIGINT",
                },
                {
                    "Name": "completion_tokens",
                    "Value": str(record.completion_tokens),
                    "Type": "BIGINT",
                },
                {
                    "Name": "total_tokens",
                    "Value": str(record.total_tokens),
                    "Type": "BIGINT",
                },
                {
                    "Name": "estimated_cost_usd",
                    "Value": str(record.estimated_cost_usd),
                    "Type": "DOUBLE",
                },
            ],
            "Time": str(int(record.timestamp.timestamp() * 1000)),
            "TimeUnit": "MILLISECONDS",
        }

        # Write to Timestream (run in executor for async)
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: client.write_records(
                DatabaseName=self._database,
                TableName=self._table,
                Records=[timestream_record],
            ),
        )

        self._record_count += 1

    async def get_records(
        self,
        filters: dict[str, Any] | None = None,
        cursor: str | None = None,
        limit: int = 100,
        sort_by: str = "time",
        sort_order: str = "desc",
    ) -> tuple[list[TokenUsage], str | None]:
        """
        Get stored records with pagination, filtering, and sorting.

        Args:
            filters: Optional filters (user_id, model, provider, start_date, end_date)
            cursor: Pagination cursor (timestamp for next page)
            limit: Maximum records to return
            sort_by: Sort field (time, estimated_cost_usd, total_tokens)
            sort_order: Sort order (asc, desc)

        Returns:
            Tuple of (records, next_cursor)
        """
        client = self._get_query_client()

        # Build query (database/table from config, not user input)
        query = f"""
            SELECT
                time,
                user_id,
                session_id,
                model,
                provider,
                feature,
                prompt_tokens,
                completion_tokens,
                total_tokens,
                estimated_cost_usd
            FROM "{self._database}"."{self._table}"
            WHERE 1=1
        """  # noqa: S608

        if filters:
            if "user_id" in filters:
                query += f" AND user_id = '{filters['user_id']}'"
            if "model" in filters:
                query += f" AND model = '{filters['model']}'"
            if "provider" in filters:
                query += f" AND provider = '{filters['provider']}'"
            if "session_id" in filters:
                query += f" AND session_id = '{filters['session_id']}'"
            if "start_date" in filters:
                ts = int(filters["start_date"].timestamp() * 1000)
                query += f" AND time >= from_milliseconds({ts})"
            if "end_date" in filters:
                ts = int(filters["end_date"].timestamp() * 1000)
                query += f" AND time <= from_milliseconds({ts})"

        if cursor:
            # Cursor is timestamp in milliseconds
            if sort_order == "desc":
                query += f" AND time < from_milliseconds({cursor})"
            else:
                query += f" AND time > from_milliseconds({cursor})"

        query += f" ORDER BY {sort_by} {sort_order.upper()}"
        query += f" LIMIT {limit + 1}"

        # Execute query
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: client.query(QueryString=query),
        )

        # Parse results
        records: list[TokenUsage] = []
        rows = response.get("Rows", [])

        for row in rows[:limit]:
            data = row.get("Data", [])
            records.append(
                TokenUsage(
                    timestamp=datetime.fromisoformat(data[0]["ScalarValue"].replace(" ", "T")),
                    user_id=data[1]["ScalarValue"],
                    session_id=data[2]["ScalarValue"],
                    model=data[3]["ScalarValue"],
                    provider=data[4]["ScalarValue"],
                    feature=data[5].get("ScalarValue"),
                    prompt_tokens=int(data[6]["ScalarValue"]),
                    completion_tokens=int(data[7]["ScalarValue"]),
                    total_tokens=int(data[8]["ScalarValue"]),
                    estimated_cost_usd=Decimal(data[9]["ScalarValue"]),
                )
            )

        # Determine next cursor
        next_cursor = None
        if len(rows) > limit:
            last_record = records[-1]
            next_cursor = str(int(last_record.timestamp.timestamp() * 1000))

        return records, next_cursor

    async def delete_records_before(self, cutoff: datetime) -> int:
        """
        Delete records older than cutoff.

        Note: Timestream doesn't support DELETE. Use data retention policies instead.
        This method returns 0 - use Timestream retention policies for cleanup.

        Args:
            cutoff: Cutoff datetime (not used - Timestream uses retention policies)

        Returns:
            0 (Timestream uses automatic retention)
        """
        # Timestream uses retention policies, not DELETE
        # Configure retention when creating the table:
        # - Memory store retention: 1-8766 hours (default: 12 hours)
        # - Magnetic store retention: 1 day to 73000 days
        return 0

    async def get_latest_record(self) -> TokenUsage | None:
        """
        Get the most recently stored record.

        Returns:
            Latest TokenUsage record or None if empty
        """
        records, _ = await self.get_records(limit=1, sort_order="desc")
        return records[0] if records else None

    async def get_cost_summary(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        user_id: str | None = None,
    ) -> CostSummary:
        """
        Get aggregated cost summary using Timestream aggregation.

        Args:
            start_date: Start of period
            end_date: End of period
            user_id: Optional user filter

        Returns:
            CostSummary with aggregated metrics
        """
        client = self._get_query_client()

        query = f"""
            SELECT
                SUM(estimated_cost_usd) as total_cost,
                SUM(prompt_tokens) as total_prompt_tokens,
                SUM(completion_tokens) as total_completion_tokens,
                SUM(total_tokens) as total_tokens,
                COUNT(*) as request_count,
                MIN(time) as period_start,
                MAX(time) as period_end
            FROM "{self._database}"."{self._table}"
            WHERE 1=1
        """  # noqa: S608 - database/table from config

        if start_date:
            ts = int(start_date.timestamp() * 1000)
            query += f" AND time >= from_milliseconds({ts})"
        if end_date:
            ts = int(end_date.timestamp() * 1000)
            query += f" AND time <= from_milliseconds({ts})"
        if user_id:
            query += f" AND user_id = '{user_id}'"

        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: client.query(QueryString=query),
        )

        rows = response.get("Rows", [])
        if rows:
            data = rows[0].get("Data", [])
            return CostSummary(
                total_cost=Decimal(data[0].get("ScalarValue", "0")),
                total_prompt_tokens=int(data[1].get("ScalarValue", "0")),
                total_completion_tokens=int(data[2].get("ScalarValue", "0")),
                total_tokens=int(data[3].get("ScalarValue", "0")),
                request_count=int(data[4].get("ScalarValue", "0")),
                period_start=datetime.fromisoformat(data[5].get("ScalarValue", "").replace(" ", "T"))
                if data[5].get("ScalarValue")
                else None,
                period_end=datetime.fromisoformat(data[6].get("ScalarValue", "").replace(" ", "T"))
                if data[6].get("ScalarValue")
                else None,
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
        bucket_interval: str = "1d",
    ) -> list[DailyCost]:
        """
        Get cost history over time using Timestream bin function.

        Args:
            start_date: Start of period
            end_date: End of period
            user_id: Optional user filter
            bucket_interval: Time bucket (1h, 1d, 7d)

        Returns:
            List of DailyCost entries
        """
        client = self._get_query_client()

        query = f"""
            SELECT
                bin(time, {bucket_interval}) as bucket,
                SUM(estimated_cost_usd) as total_cost,
                SUM(total_tokens) as total_tokens,
                COUNT(*) as request_count
            FROM "{self._database}"."{self._table}"
            WHERE 1=1
        """  # noqa: S608 - database/table from config

        if start_date:
            ts = int(start_date.timestamp() * 1000)
            query += f" AND time >= from_milliseconds({ts})"
        if end_date:
            ts = int(end_date.timestamp() * 1000)
            query += f" AND time <= from_milliseconds({ts})"
        if user_id:
            query += f" AND user_id = '{user_id}'"

        query += " GROUP BY bin(time, " + bucket_interval + ") ORDER BY bucket ASC"

        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: client.query(QueryString=query),
        )

        results: list[DailyCost] = []
        for row in response.get("Rows", []):
            data = row.get("Data", [])
            results.append(
                DailyCost(
                    date=datetime.fromisoformat(data[0]["ScalarValue"].replace(" ", "T")),
                    total_cost=Decimal(data[1]["ScalarValue"]),
                    total_tokens=int(data[2]["ScalarValue"]),
                    request_count=int(data[3]["ScalarValue"]),
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
        client = self._get_query_client()

        query = f"""
            SELECT
                model,
                provider,
                SUM(estimated_cost_usd) as total_cost,
                SUM(prompt_tokens) as total_prompt_tokens,
                SUM(completion_tokens) as total_completion_tokens,
                COUNT(*) as request_count
            FROM "{self._database}"."{self._table}"
            WHERE 1=1
        """  # noqa: S608 - database/table from config

        if start_date:
            ts = int(start_date.timestamp() * 1000)
            query += f" AND time >= from_milliseconds({ts})"
        if end_date:
            ts = int(end_date.timestamp() * 1000)
            query += f" AND time <= from_milliseconds({ts})"
        if user_id:
            query += f" AND user_id = '{user_id}'"

        query += " GROUP BY model, provider ORDER BY total_cost DESC"

        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: client.query(QueryString=query),
        )

        results: list[ModelCost] = []
        for row in response.get("Rows", []):
            data = row.get("Data", [])
            results.append(
                ModelCost(
                    model=data[0]["ScalarValue"],
                    provider=data[1]["ScalarValue"],
                    total_cost=Decimal(data[2]["ScalarValue"]),
                    total_prompt_tokens=int(data[3]["ScalarValue"]),
                    total_completion_tokens=int(data[4]["ScalarValue"]),
                    request_count=int(data[5]["ScalarValue"]),
                )
            )

        return results
