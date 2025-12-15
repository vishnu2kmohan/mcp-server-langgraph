"""
Azure Data Explorer (Kusto) Cost Storage Backend.

Provides cost storage using Azure Data Explorer for AKS deployments.
ADX is optimized for log and time-series analytics with:
- Kusto Query Language (KQL) for powerful queries
- Materialized views for pre-aggregation
- Native Azure AD integration
- High ingestion rates

Configuration:
- ADX_CLUSTER_URI: Cluster URI (e.g., https://mycluster.westus.kusto.windows.net)
- ADX_DATABASE: Database name
- ADX_TABLE: Table name (default: TokenUsage)

Requires: azure-kusto-data, azure-kusto-ingest (optional dependencies)
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


class ADXCostStorage:
    """
    Azure Data Explorer storage backend for cost metrics.

    Uses KQL for queries with:
    - Dimensions: user_id, session_id, model, provider, feature
    - Measures: prompt_tokens, completion_tokens, total_tokens, estimated_cost_usd

    Supports pagination, filtering, sorting, and aggregation queries.
    """

    def __init__(
        self,
        cluster_uri: str,
        database: str,
        table: str = "TokenUsage",
        batch_size: int = 1000,
        flush_interval_seconds: int = 10,
    ) -> None:
        """
        Initialize Azure Data Explorer storage.

        Args:
            cluster_uri: ADX cluster URI
            database: ADX database name
            table: ADX table name
            batch_size: Batch size for ingestion
            flush_interval_seconds: Flush interval for batched ingestion
        """
        self._cluster_uri = cluster_uri
        self._database = database
        self._table = table
        self._batch_size = batch_size
        self._flush_interval = flush_interval_seconds
        self._client: Any = None
        self._ingest_client: Any = None
        self._record_count = 0
        self._pending_records: list[TokenUsage] = []

    def _get_client(self) -> Any:
        """Get or create ADX query client."""
        if self._client is None:
            try:
                from azure.kusto.data import KustoClient, KustoConnectionStringBuilder
                from azure.identity import DefaultAzureCredential

                # Use DefaultAzureCredential for managed identity / workload identity
                credential = DefaultAzureCredential()
                kcsb = KustoConnectionStringBuilder.with_azure_token_credential(
                    self._cluster_uri,
                    credential,
                )
                self._client = KustoClient(kcsb)
            except ImportError:
                msg = "azure-kusto-data is required for ADX backend. Install with: pip install azure-kusto-data azure-identity"
                raise ImportError(msg) from None
        return self._client

    def _get_ingest_client(self) -> Any:
        """Get or create ADX ingest client."""
        if self._ingest_client is None:
            try:
                from azure.kusto.ingest import QueuedIngestClient
                from azure.kusto.data import KustoConnectionStringBuilder
                from azure.identity import DefaultAzureCredential

                credential = DefaultAzureCredential()
                # Ingest URI is different from query URI
                ingest_uri = self._cluster_uri.replace("https://", "https://ingest-")
                kcsb = KustoConnectionStringBuilder.with_azure_token_credential(
                    ingest_uri,
                    credential,
                )
                self._ingest_client = QueuedIngestClient(kcsb)
            except ImportError:
                msg = (
                    "azure-kusto-ingest is required for ADX backend. "
                    "Install with: pip install azure-kusto-ingest azure-identity"
                )
                raise ImportError(msg) from None
        return self._ingest_client

    @property
    def total_records(self) -> int:
        """Get the total number of stored records (tracked locally)."""
        return self._record_count

    async def store(self, record: TokenUsage) -> None:
        """
        Store a token usage record in ADX.

        Uses batched ingestion for efficiency.

        Args:
            record: TokenUsage record to store
        """
        # For immediate writes, use streaming ingestion
        # For batched writes, use queued ingestion
        client = self._get_client()

        # Build ingestion data as CSV row
        csv_data = ",".join(
            [
                record.timestamp.isoformat(),
                record.user_id,
                record.session_id,
                record.model,
                record.provider,
                record.feature or "",
                str(record.prompt_tokens),
                str(record.completion_tokens),
                str(record.total_tokens),
                str(record.estimated_cost_usd),
            ]
        )

        # Execute inline ingestion using .ingest inline command
        ingest_command = f"""
            .ingest inline into table {self._table} <|
            {csv_data}
        """

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: client.execute_mgmt(self._database, ingest_command),
        )

        self._record_count += 1

    async def get_records(
        self,
        filters: dict[str, Any] | None = None,
        cursor: str | None = None,
        limit: int = 100,
        sort_by: str = "timestamp",
        sort_order: str = "desc",
    ) -> tuple[list[TokenUsage], str | None]:
        """
        Get stored records with pagination, filtering, and sorting.

        Args:
            filters: Optional filters (user_id, model, provider, start_date, end_date)
            cursor: Pagination cursor (timestamp for next page)
            limit: Maximum records to return
            sort_by: Sort field
            sort_order: Sort order (asc, desc)

        Returns:
            Tuple of (records, next_cursor)
        """
        client = self._get_client()

        # Build KQL query
        query = f"""
            {self._table}
        """

        where_clauses = []

        if filters:
            if "user_id" in filters:
                where_clauses.append(f"user_id == '{filters['user_id']}'")
            if "model" in filters:
                where_clauses.append(f"model == '{filters['model']}'")
            if "provider" in filters:
                where_clauses.append(f"provider == '{filters['provider']}'")
            if "session_id" in filters:
                where_clauses.append(f"session_id == '{filters['session_id']}'")
            if "start_date" in filters:
                ts = filters["start_date"].isoformat()
                where_clauses.append(f"timestamp >= datetime({ts})")
            if "end_date" in filters:
                ts = filters["end_date"].isoformat()
                where_clauses.append(f"timestamp <= datetime({ts})")

        if cursor:
            if sort_order == "desc":
                where_clauses.append(f"timestamp < datetime({cursor})")
            else:
                where_clauses.append(f"timestamp > datetime({cursor})")

        if where_clauses:
            query += " | where " + " and ".join(where_clauses)

        query += f" | order by {sort_by} {sort_order}"
        query += f" | take {limit + 1}"

        # Execute query
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: client.execute_query(self._database, query),
        )

        # Parse results
        records: list[TokenUsage] = []
        primary_results = response.primary_results[0] if response.primary_results else None

        if primary_results:
            for row in list(primary_results)[:limit]:
                records.append(
                    TokenUsage(
                        timestamp=row["timestamp"],
                        user_id=row["user_id"],
                        session_id=row["session_id"],
                        model=row["model"],
                        provider=row["provider"],
                        feature=row.get("feature"),
                        prompt_tokens=int(row["prompt_tokens"]),
                        completion_tokens=int(row["completion_tokens"]),
                        total_tokens=int(row["total_tokens"]),
                        estimated_cost_usd=Decimal(str(row["estimated_cost_usd"])),
                    )
                )

            # Determine next cursor
            all_rows = list(primary_results)
            next_cursor = None
            if len(all_rows) > limit:
                last_record = records[-1]
                next_cursor = last_record.timestamp.isoformat()

            return records, next_cursor

        return [], None

    async def delete_records_before(self, cutoff: datetime) -> int:
        """
        Delete records older than cutoff.

        Note: ADX uses soft-delete and retention policies.
        Use .delete command for immediate purge (requires admin).

        Args:
            cutoff: Cutoff datetime

        Returns:
            Number of records marked for deletion
        """
        client = self._get_client()

        # Count records to be deleted
        count_query = f"""
            {self._table}
            | where timestamp < datetime({cutoff.isoformat()})
            | count
        """

        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: client.execute_query(self._database, count_query),
        )

        count = 0
        if response.primary_results:
            count = list(response.primary_results[0])[0]["Count"]

        # Soft delete using .delete command
        delete_command = f"""
            .delete table {self._table} records <|
            {self._table}
            | where timestamp < datetime({cutoff.isoformat()})
        """

        await loop.run_in_executor(
            None,
            lambda: client.execute_mgmt(self._database, delete_command),
        )

        self._record_count = max(0, self._record_count - count)
        return count

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
        Get aggregated cost summary using KQL summarize.

        Args:
            start_date: Start of period
            end_date: End of period
            user_id: Optional user filter

        Returns:
            CostSummary with aggregated metrics
        """
        client = self._get_client()

        query = f"{self._table}"

        where_clauses = []
        if start_date:
            where_clauses.append(f"timestamp >= datetime({start_date.isoformat()})")
        if end_date:
            where_clauses.append(f"timestamp <= datetime({end_date.isoformat()})")
        if user_id:
            where_clauses.append(f"user_id == '{user_id}'")

        if where_clauses:
            query += " | where " + " and ".join(where_clauses)

        query += """
            | summarize
                total_cost = sum(estimated_cost_usd),
                total_prompt_tokens = sum(prompt_tokens),
                total_completion_tokens = sum(completion_tokens),
                total_tokens = sum(total_tokens),
                request_count = count(),
                period_start = min(timestamp),
                period_end = max(timestamp)
        """

        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: client.execute_query(self._database, query),
        )

        if response.primary_results:
            rows = list(response.primary_results[0])
            if rows:
                row = rows[0]
                return CostSummary(
                    total_cost=Decimal(str(row["total_cost"] or 0)),
                    total_prompt_tokens=int(row["total_prompt_tokens"] or 0),
                    total_completion_tokens=int(row["total_completion_tokens"] or 0),
                    total_tokens=int(row["total_tokens"] or 0),
                    request_count=int(row["request_count"] or 0),
                    period_start=row.get("period_start"),
                    period_end=row.get("period_end"),
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
        Get cost history over time using KQL bin function.

        Args:
            start_date: Start of period
            end_date: End of period
            user_id: Optional user filter
            bucket_interval: Time bucket (1h, 1d, 7d)

        Returns:
            List of DailyCost entries
        """
        client = self._get_client()

        query = f"{self._table}"

        where_clauses = []
        if start_date:
            where_clauses.append(f"timestamp >= datetime({start_date.isoformat()})")
        if end_date:
            where_clauses.append(f"timestamp <= datetime({end_date.isoformat()})")
        if user_id:
            where_clauses.append(f"user_id == '{user_id}'")

        if where_clauses:
            query += " | where " + " and ".join(where_clauses)

        query += f"""
            | summarize
                total_cost = sum(estimated_cost_usd),
                total_tokens = sum(total_tokens),
                request_count = count()
            by bin(timestamp, {bucket_interval})
            | order by timestamp asc
        """

        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: client.execute_query(self._database, query),
        )

        results: list[DailyCost] = []
        if response.primary_results:
            for row in response.primary_results[0]:
                results.append(
                    DailyCost(
                        date=row["timestamp"],
                        total_cost=Decimal(str(row["total_cost"])),
                        total_tokens=int(row["total_tokens"]),
                        request_count=int(row["request_count"]),
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
        Get cost breakdown by model using KQL summarize.

        Args:
            start_date: Start of period
            end_date: End of period
            user_id: Optional user filter

        Returns:
            List of ModelCost entries ordered by cost
        """
        client = self._get_client()

        query = f"{self._table}"

        where_clauses = []
        if start_date:
            where_clauses.append(f"timestamp >= datetime({start_date.isoformat()})")
        if end_date:
            where_clauses.append(f"timestamp <= datetime({end_date.isoformat()})")
        if user_id:
            where_clauses.append(f"user_id == '{user_id}'")

        if where_clauses:
            query += " | where " + " and ".join(where_clauses)

        query += """
            | summarize
                total_cost = sum(estimated_cost_usd),
                total_prompt_tokens = sum(prompt_tokens),
                total_completion_tokens = sum(completion_tokens),
                request_count = count()
            by model, provider
            | order by total_cost desc
        """

        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: client.execute_query(self._database, query),
        )

        results: list[ModelCost] = []
        if response.primary_results:
            for row in response.primary_results[0]:
                results.append(
                    ModelCost(
                        model=row["model"],
                        provider=row["provider"],
                        total_cost=Decimal(str(row["total_cost"])),
                        total_prompt_tokens=int(row["total_prompt_tokens"]),
                        total_completion_tokens=int(row["total_completion_tokens"]),
                        request_count=int(row["request_count"]),
                    )
                )

        return results
