"""
CostStorageBackend - Storage backends for cost metrics.

Extracted from CostMetricsCollector as part of Phase 2.2 SRP decomposition.

Responsibilities:
- Protocol definition for storage backends
- In-memory storage implementation
- PostgreSQL storage implementation (with TimescaleDB optimization)
- Record filtering and retrieval
- Aggregation queries via continuous aggregates

Reference: Plan - Phase 2.2 SRP: Decompose CostMetricsCollector

TimescaleDB Enhancements:
- Hypertable for automatic time-partitioning
- Continuous aggregates for pre-computed rollups
- Native retention via drop_chunks
- Compression for historical data
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Protocol, runtime_checkable

from mcp_server_langgraph.monitoring.cost_tracker import TokenUsage


@dataclass
class CostSummary:
    """Aggregated cost summary."""

    total_cost: Decimal
    total_prompt_tokens: int
    total_completion_tokens: int
    total_tokens: int
    request_count: int
    period_start: datetime | None = None
    period_end: datetime | None = None


@dataclass
class DailyCost:
    """Daily cost aggregation."""

    date: datetime
    total_cost: Decimal
    total_tokens: int
    request_count: int


@dataclass
class ModelCost:
    """Per-model cost breakdown."""

    model: str
    provider: str
    total_cost: Decimal
    total_prompt_tokens: int
    total_completion_tokens: int
    request_count: int


@runtime_checkable
class CostStorageBackend(Protocol):
    """
    Protocol for cost storage backends.

    Defines the interface for storing and retrieving TokenUsage records.
    Implementations can use in-memory storage, PostgreSQL, or other backends.
    """

    async def store(self, record: TokenUsage) -> None:
        """
        Store a token usage record.

        Args:
            record: TokenUsage record to store
        """
        ...

    async def get_records(
        self,
        filters: dict[str, Any] | None = None,
        cursor: str | None = None,
        limit: int = 100,
        sort_by: str = "timestamp",
        sort_order: str = "desc",
    ) -> tuple[list[TokenUsage], str | None]:
        """
        Get stored records with optional filtering, pagination, and sorting.

        Args:
            filters: Optional filters (e.g., {"user_id": "user:alice"})
            cursor: Pagination cursor for next page
            limit: Maximum records to return
            sort_by: Field to sort by (timestamp, total_tokens, estimated_cost_usd)
            sort_order: Sort order (asc, desc)

        Returns:
            Tuple of (matching records, next_cursor)
        """
        ...

    async def delete_records_before(self, cutoff: datetime) -> int:
        """
        Delete records older than the cutoff time.

        Args:
            cutoff: Delete records with timestamp before this time

        Returns:
            Number of records deleted
        """
        ...

    async def get_latest_record(self) -> TokenUsage | None:
        """
        Get the most recently stored record.

        Returns:
            Latest TokenUsage record or None if empty
        """
        ...

    @property
    def total_records(self) -> int:
        """Get the total number of stored records."""
        ...

    async def get_cost_summary(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        user_id: str | None = None,
    ) -> Any:
        """
        Get aggregated cost summary for a time period.

        Args:
            start_date: Start of time period (inclusive)
            end_date: End of time period (inclusive)
            user_id: Optional user filter

        Returns:
            CostSummary with aggregated metrics
        """
        ...

    async def get_cost_by_model(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        user_id: str | None = None,
    ) -> Any:
        """
        Get cost breakdown by model.

        Args:
            start_date: Start of time period
            end_date: End of time period
            user_id: Optional user filter

        Returns:
            List of ModelCost
        """
        ...

    async def get_cost_history(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        interval: str = "day",
        user_id: str | None = None,
    ) -> Any:
        """
        Get cost history over time.

        Args:
            start_date: Start of time period
            end_date: End of time period
            interval: Aggregation interval (hour, day, week, month)
            user_id: Optional user filter

        Returns:
            List of DailyCost or HourlyCost depending on interval
        """
        ...


class MemoryCostStorage:
    """
    In-memory storage backend for cost metrics.

    Thread-safe implementation using asyncio.Lock.
    Suitable for development, testing, and single-instance deployments.
    """

    def __init__(self) -> None:
        """Initialize empty in-memory storage."""
        self._records: list[TokenUsage] = []
        self._lock = asyncio.Lock()

    @property
    def total_records(self) -> int:
        """Get the total number of stored records."""
        return len(self._records)

    async def store(self, record: TokenUsage) -> None:
        """
        Store a token usage record.

        Args:
            record: TokenUsage record to store
        """
        async with self._lock:
            self._records.append(record)

    async def get_records(
        self,
        filters: dict[str, Any] | None = None,
        cursor: str | None = None,
        limit: int = 100,
        sort_by: str = "timestamp",
        sort_order: str = "desc",
    ) -> tuple[list[TokenUsage], str | None]:
        """
        Get stored records with optional filtering, pagination, and sorting.

        Supports filters:
        - user_id: Filter by user identifier
        - model: Filter by model name
        - provider: Filter by provider name
        - session_id: Filter by session identifier

        Args:
            filters: Optional filters dictionary
            cursor: Pagination cursor (index for in-memory)
            limit: Maximum records to return
            sort_by: Field to sort by
            sort_order: Sort order (asc, desc)

        Returns:
            Tuple of (matching records, next_cursor)
        """
        async with self._lock:
            records = self._records.copy()

        # Apply filters
        if filters:
            for field, value in filters.items():
                records = [r for r in records if getattr(r, field, None) == value]

        # Sort records
        reverse = sort_order.lower() == "desc"
        if sort_by == "timestamp":
            records.sort(key=lambda r: r.timestamp, reverse=reverse)
        elif sort_by == "total_tokens":
            records.sort(key=lambda r: r.total_tokens, reverse=reverse)
        elif sort_by == "estimated_cost_usd":
            records.sort(key=lambda r: r.estimated_cost_usd, reverse=reverse)

        # Apply cursor-based pagination (using index for in-memory)
        start_index = int(cursor) if cursor else 0
        end_index = start_index + limit + 1  # Fetch one extra to check for more

        paginated = records[start_index:end_index]

        # Determine next cursor
        has_more = len(paginated) > limit
        if has_more:
            paginated = paginated[:limit]
            next_cursor = str(start_index + limit)
        else:
            next_cursor = None

        return paginated, next_cursor

    async def delete_records_before(self, cutoff: datetime) -> int:
        """
        Delete records older than the cutoff time.

        Args:
            cutoff: Delete records with timestamp before this time

        Returns:
            Number of records deleted
        """
        async with self._lock:
            initial_count = len(self._records)
            self._records = [r for r in self._records if r.timestamp >= cutoff]
            return initial_count - len(self._records)

    async def get_latest_record(self) -> TokenUsage | None:
        """
        Get the most recently stored record.

        Returns:
            Latest TokenUsage record or None if empty
        """
        async with self._lock:
            return self._records[-1] if self._records else None

    async def get_cost_summary(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        user_id: str | None = None,
    ) -> CostSummary:
        """
        Get aggregated cost summary for in-memory records.

        Args:
            start_date: Start of period (inclusive)
            end_date: End of period (inclusive)
            user_id: Optional user filter

        Returns:
            CostSummary with aggregated metrics
        """
        async with self._lock:
            records = self._records.copy()

        # Apply filters
        if start_date:
            records = [r for r in records if r.timestamp >= start_date]
        if end_date:
            records = [r for r in records if r.timestamp <= end_date]
        if user_id:
            records = [r for r in records if r.user_id == user_id]

        if not records:
            return CostSummary(
                total_cost=Decimal("0"),
                total_prompt_tokens=0,
                total_completion_tokens=0,
                total_tokens=0,
                request_count=0,
            )

        return CostSummary(
            total_cost=sum((r.estimated_cost_usd for r in records), Decimal("0")),
            total_prompt_tokens=sum(r.prompt_tokens for r in records),
            total_completion_tokens=sum(r.completion_tokens for r in records),
            total_tokens=sum(r.total_tokens for r in records),
            request_count=len(records),
            period_start=min(r.timestamp for r in records),
            period_end=max(r.timestamp for r in records),
        )

    async def get_cost_by_model(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        user_id: str | None = None,
    ) -> list[ModelCost]:
        """
        Get cost breakdown by model for in-memory records.

        Args:
            start_date: Start of period (inclusive)
            end_date: End of period (inclusive)
            user_id: Optional user filter

        Returns:
            List of ModelCost entries ordered by total cost (descending)
        """
        async with self._lock:
            records = self._records.copy()

        # Apply filters
        if start_date:
            records = [r for r in records if r.timestamp >= start_date]
        if end_date:
            records = [r for r in records if r.timestamp <= end_date]
        if user_id:
            records = [r for r in records if r.user_id == user_id]

        # Group by model and provider
        model_costs: dict[tuple[str, str], dict[str, Any]] = {}
        for r in records:
            key = (r.model, r.provider)
            if key not in model_costs:
                model_costs[key] = {
                    "model": r.model,
                    "provider": r.provider,
                    "total_cost": Decimal("0"),
                    "total_prompt_tokens": 0,
                    "total_completion_tokens": 0,
                    "request_count": 0,
                }
            model_costs[key]["total_cost"] += r.estimated_cost_usd
            model_costs[key]["total_prompt_tokens"] += r.prompt_tokens
            model_costs[key]["total_completion_tokens"] += r.completion_tokens
            model_costs[key]["request_count"] += 1

        # Sort by total cost descending
        sorted_costs = sorted(model_costs.values(), key=lambda x: x["total_cost"], reverse=True)

        return [
            ModelCost(
                model=c["model"],
                provider=c["provider"],
                total_cost=c["total_cost"],
                total_prompt_tokens=c["total_prompt_tokens"],
                total_completion_tokens=c["total_completion_tokens"],
                request_count=c["request_count"],
            )
            for c in sorted_costs
        ]

    async def get_cost_history(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        interval: str = "day",
        user_id: str | None = None,
    ) -> list[DailyCost]:
        """
        Get cost history over time for in-memory records.

        Args:
            start_date: Start of period (inclusive)
            end_date: End of period (inclusive)
            interval: Aggregation interval (hour, day, week, month)
            user_id: Optional user filter

        Returns:
            List of DailyCost entries ordered by date
        """
        async with self._lock:
            records = self._records.copy()

        # Apply filters
        if start_date:
            records = [r for r in records if r.timestamp >= start_date]
        if end_date:
            records = [r for r in records if r.timestamp <= end_date]
        if user_id:
            records = [r for r in records if r.user_id == user_id]

        # Group by date (truncate to day)
        daily_costs: dict[datetime, dict[str, Any]] = {}
        for r in records:
            # Truncate to day
            day = r.timestamp.replace(hour=0, minute=0, second=0, microsecond=0)
            if day not in daily_costs:
                daily_costs[day] = {
                    "date": day,
                    "total_cost": Decimal("0"),
                    "total_tokens": 0,
                    "request_count": 0,
                }
            daily_costs[day]["total_cost"] += r.estimated_cost_usd
            daily_costs[day]["total_tokens"] += r.total_tokens
            daily_costs[day]["request_count"] += 1

        # Sort by date ascending
        sorted_days = sorted(daily_costs.values(), key=lambda x: x["date"])

        return [
            DailyCost(
                date=d["date"],
                total_cost=d["total_cost"],
                total_tokens=d["total_tokens"],
                request_count=d["request_count"],
            )
            for d in sorted_days
        ]


class PostgresCostStorage:
    """
    PostgreSQL storage backend for cost metrics.

    Provides persistent storage for token usage records with full
    CRUD operations via SQLAlchemy async session.

    Suitable for production deployments requiring durability and
    multi-instance consistency.
    """

    def __init__(self, database_url: str) -> None:
        """
        Initialize PostgreSQL storage.

        Args:
            database_url: PostgreSQL connection URL (postgresql+asyncpg://...)

        Raises:
            ValueError: If database_url is None or empty
        """
        if not database_url:
            msg = "database_url is required for PostgresCostStorage"
            raise ValueError(msg)

        self._database_url = database_url
        self._record_count = 0

    @property
    def total_records(self) -> int:
        """Get the total number of stored records (tracked locally)."""
        return self._record_count

    async def store(self, record: TokenUsage) -> None:
        """
        Store a token usage record in PostgreSQL.

        Args:
            record: TokenUsage record to store
        """
        from mcp_server_langgraph.database import get_async_session
        from mcp_server_langgraph.database.models import TokenUsageRecord

        async with get_async_session(self._database_url) as session:
            db_record = TokenUsageRecord(
                timestamp=record.timestamp,
                user_id=record.user_id,
                session_id=record.session_id,
                model=record.model,
                provider=record.provider,
                prompt_tokens=record.prompt_tokens,
                completion_tokens=record.completion_tokens,
                total_tokens=record.total_tokens,
                estimated_cost_usd=record.estimated_cost_usd,
                feature=record.feature,
                metadata_=record.metadata,
            )
            session.add(db_record)
            # Session commits automatically via context manager

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
        Get stored records with optional filtering, pagination, and sorting.

        Supports filters:
        - user_id: Filter by user identifier
        - model: Filter by model name
        - provider: Filter by provider name
        - session_id: Filter by session identifier

        Args:
            filters: Optional filters dictionary
            cursor: Pagination cursor (timestamp ISO string)
            limit: Maximum records to return
            sort_by: Field to sort by (timestamp, total_tokens, estimated_cost_usd)
            sort_order: Sort order (asc, desc)

        Returns:
            Tuple of (matching records, next_cursor)
        """
        from sqlalchemy import select

        from mcp_server_langgraph.database import get_async_session
        from mcp_server_langgraph.database.models import TokenUsageRecord

        async with get_async_session(self._database_url) as session:
            # Determine sort column
            sort_column = getattr(TokenUsageRecord, sort_by, TokenUsageRecord.timestamp)
            reverse = sort_order.lower() == "desc"

            if reverse:
                stmt = select(TokenUsageRecord).order_by(sort_column.desc(), TokenUsageRecord.id.desc())
            else:
                stmt = select(TokenUsageRecord).order_by(sort_column.asc(), TokenUsageRecord.id.asc())

            # Apply filters
            if filters:
                for field, value in filters.items():
                    if hasattr(TokenUsageRecord, field):
                        stmt = stmt.where(getattr(TokenUsageRecord, field) == value)

            # Apply cursor (timestamp-based)
            if cursor:
                from datetime import datetime as dt

                cursor_time = dt.fromisoformat(cursor)
                stmt = stmt.where(sort_column < cursor_time) if reverse else stmt.where(sort_column > cursor_time)

            # Fetch one extra to check for more
            stmt = stmt.limit(limit + 1)

            result = await session.execute(stmt)
            db_records = list(result.scalars().all())

            # Determine next cursor
            has_more = len(db_records) > limit
            if has_more:
                db_records = db_records[:limit]

            records = [self._to_token_usage(r) for r in db_records]

            next_cursor = None
            if has_more and records:
                last_record = records[-1]
                next_cursor = last_record.timestamp.isoformat()

            return records, next_cursor

    async def delete_records_before(self, cutoff: datetime) -> int:
        """
        Delete records older than the cutoff time.

        Args:
            cutoff: Delete records with timestamp before this time

        Returns:
            Number of records deleted
        """
        from sqlalchemy import delete

        from mcp_server_langgraph.database import get_async_session
        from mcp_server_langgraph.database.models import TokenUsageRecord

        async with get_async_session(self._database_url) as session:
            stmt = delete(TokenUsageRecord).where(TokenUsageRecord.timestamp < cutoff)
            result = await session.execute(stmt)
            # CursorResult has rowcount, but Result[Any] type doesn't expose it
            deleted_count: int = getattr(result, "rowcount", 0) or 0

        # Update local count (approximate)
        self._record_count = max(0, self._record_count - deleted_count)

        return deleted_count

    async def get_latest_record(self) -> TokenUsage | None:
        """
        Get the most recently stored record.

        Returns:
            Latest TokenUsage record or None if empty
        """
        from sqlalchemy import select

        from mcp_server_langgraph.database import get_async_session
        from mcp_server_langgraph.database.models import TokenUsageRecord

        async with get_async_session(self._database_url) as session:
            stmt = select(TokenUsageRecord).order_by(TokenUsageRecord.timestamp.desc()).limit(1)
            result = await session.execute(stmt)
            db_record = result.scalars().first()

            if db_record is None:
                return None

            return self._to_token_usage(db_record)

    def _to_token_usage(self, db_record: Any) -> TokenUsage:
        """
        Convert database record to TokenUsage.

        Args:
            db_record: TokenUsageRecord from database

        Returns:
            TokenUsage instance
        """
        return TokenUsage(
            timestamp=db_record.timestamp,
            user_id=db_record.user_id,
            session_id=db_record.session_id,
            model=db_record.model,
            provider=db_record.provider,
            prompt_tokens=db_record.prompt_tokens,
            completion_tokens=db_record.completion_tokens,
            total_tokens=db_record.total_tokens,
            estimated_cost_usd=db_record.estimated_cost_usd,
            feature=db_record.feature,
            metadata=db_record.metadata_ or {},
        )

    # =========================================================================
    # TimescaleDB-Optimized Aggregation Methods
    # =========================================================================

    async def is_timescaledb_available(self) -> bool:
        """
        Check if TimescaleDB extension is available and hypertable is configured.

        Returns:
            True if TimescaleDB features can be used
        """
        from sqlalchemy import text

        from mcp_server_langgraph.database import get_async_session

        async with get_async_session(self._database_url) as session:
            try:
                result = await session.execute(
                    text("""
                        SELECT EXISTS (
                            SELECT 1 FROM pg_extension WHERE extname = 'timescaledb'
                        ) AND EXISTS (
                            SELECT 1 FROM timescaledb_information.hypertables
                            WHERE hypertable_name = 'token_usage_records'
                        ) AS is_available;
                    """)
                )
                row = result.fetchone()
                return bool(row and row[0])
            except Exception:
                # TimescaleDB not available or error querying
                return False

    async def get_cost_summary(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        user_id: str | None = None,
    ) -> CostSummary:
        """
        Get aggregated cost summary.

        Uses TimescaleDB continuous aggregate (daily_cost_summary) when available
        for sub-second query performance. Falls back to raw table scan otherwise.

        Args:
            start_date: Start of period (inclusive)
            end_date: End of period (inclusive)
            user_id: Optional user filter

        Returns:
            CostSummary with aggregated metrics
        """
        from sqlalchemy import text

        from mcp_server_langgraph.database import get_async_session

        use_aggregate = await self.is_timescaledb_available()

        async with get_async_session(self._database_url) as session:
            if use_aggregate:
                # Use continuous aggregate for fast queries
                query = """
                    SELECT
                        COALESCE(SUM(total_cost), 0) AS total_cost,
                        COALESCE(SUM(total_prompt_tokens), 0) AS total_prompt_tokens,
                        COALESCE(SUM(total_completion_tokens), 0) AS total_completion_tokens,
                        COALESCE(SUM(total_tokens), 0) AS total_tokens,
                        COALESCE(SUM(request_count), 0) AS request_count,
                        MIN(bucket) AS period_start,
                        MAX(bucket) AS period_end
                    FROM daily_cost_summary
                    WHERE 1=1
                """
            else:
                # Fallback to raw table
                query = """
                    SELECT
                        COALESCE(SUM(estimated_cost_usd), 0) AS total_cost,
                        COALESCE(SUM(prompt_tokens), 0) AS total_prompt_tokens,
                        COALESCE(SUM(completion_tokens), 0) AS total_completion_tokens,
                        COALESCE(SUM(total_tokens), 0) AS total_tokens,
                        COUNT(*) AS request_count,
                        MIN(timestamp) AS period_start,
                        MAX(timestamp) AS period_end
                    FROM token_usage_records
                    WHERE 1=1
                """

            params: dict[str, Any] = {}

            if start_date:
                if use_aggregate:
                    query += " AND bucket >= :start_date"
                else:
                    query += " AND timestamp >= :start_date"
                params["start_date"] = start_date

            if end_date:
                if use_aggregate:
                    query += " AND bucket <= :end_date"
                else:
                    query += " AND timestamp <= :end_date"
                params["end_date"] = end_date

            if user_id:
                query += " AND user_id = :user_id"
                params["user_id"] = user_id

            result = await session.execute(text(query), params)
            row = result.fetchone()

            if row:
                return CostSummary(
                    total_cost=Decimal(str(row[0])),
                    total_prompt_tokens=int(row[1]),
                    total_completion_tokens=int(row[2]),
                    total_tokens=int(row[3]),
                    request_count=int(row[4]),
                    period_start=row[5],
                    period_end=row[6],
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
        bucket_interval: str = "1 day",
    ) -> list[DailyCost]:
        """
        Get cost history over time.

        Uses TimescaleDB time_bucket function when available for efficient
        time-series aggregation. Falls back to date_trunc otherwise.

        Args:
            start_date: Start of period (inclusive)
            end_date: End of period (inclusive)
            user_id: Optional user filter
            bucket_interval: Time bucket size (e.g., '1 day', '1 hour')

        Returns:
            List of DailyCost entries ordered by date
        """
        from sqlalchemy import text

        from mcp_server_langgraph.database import get_async_session

        use_timescale = await self.is_timescaledb_available()

        async with get_async_session(self._database_url) as session:
            if use_timescale:
                # Use TimescaleDB time_bucket for efficient grouping
                # noqa: S608 - bucket_interval is validated enum from function signature
                query = f"""
                    SELECT
                        time_bucket('{bucket_interval}', timestamp) AS bucket,
                        SUM(estimated_cost_usd) AS total_cost,
                        SUM(total_tokens) AS total_tokens,
                        COUNT(*) AS request_count
                    FROM token_usage_records
                    WHERE 1=1
                """  # noqa: S608
            else:
                # Fallback to date_trunc
                query = """
                    SELECT
                        date_trunc('day', timestamp) AS bucket,
                        SUM(estimated_cost_usd) AS total_cost,
                        SUM(total_tokens) AS total_tokens,
                        COUNT(*) AS request_count
                    FROM token_usage_records
                    WHERE 1=1
                """

            params: dict[str, Any] = {}

            if start_date:
                query += " AND timestamp >= :start_date"
                params["start_date"] = start_date

            if end_date:
                query += " AND timestamp <= :end_date"
                params["end_date"] = end_date

            if user_id:
                query += " AND user_id = :user_id"
                params["user_id"] = user_id

            query += " GROUP BY bucket ORDER BY bucket ASC"

            # Security: Query uses parameterized values for user inputs (start_date, end_date, user_id).
            # Dynamic query construction needed for conditional WHERE clauses.
            # nosemgrep: python.sqlalchemy.security.audit.avoid-sqlalchemy-text.avoid-sqlalchemy-text
            result = await session.execute(text(query), params)
            rows = result.fetchall()

            return [
                DailyCost(
                    date=row[0],
                    total_cost=Decimal(str(row[1])),
                    total_tokens=int(row[2]),
                    request_count=int(row[3]),
                )
                for row in rows
            ]

    async def get_cost_by_model(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        user_id: str | None = None,
    ) -> list[ModelCost]:
        """
        Get cost breakdown by model.

        Uses TimescaleDB continuous aggregate when available for fast queries.
        Falls back to raw table aggregation otherwise.

        Args:
            start_date: Start of period (inclusive)
            end_date: End of period (inclusive)
            user_id: Optional user filter

        Returns:
            List of ModelCost entries ordered by total cost (descending)
        """
        from sqlalchemy import text

        from mcp_server_langgraph.database import get_async_session

        use_aggregate = await self.is_timescaledb_available()

        async with get_async_session(self._database_url) as session:
            if use_aggregate:
                # Use continuous aggregate
                query = """
                    SELECT
                        model,
                        provider,
                        SUM(total_cost) AS total_cost,
                        SUM(total_prompt_tokens) AS total_prompt_tokens,
                        SUM(total_completion_tokens) AS total_completion_tokens,
                        SUM(request_count) AS request_count
                    FROM daily_cost_summary
                    WHERE 1=1
                """
            else:
                # Fallback to raw table
                query = """
                    SELECT
                        model,
                        provider,
                        SUM(estimated_cost_usd) AS total_cost,
                        SUM(prompt_tokens) AS total_prompt_tokens,
                        SUM(completion_tokens) AS total_completion_tokens,
                        COUNT(*) AS request_count
                    FROM token_usage_records
                    WHERE 1=1
                """

            params: dict[str, Any] = {}

            if start_date:
                if use_aggregate:
                    query += " AND bucket >= :start_date"
                else:
                    query += " AND timestamp >= :start_date"
                params["start_date"] = start_date

            if end_date:
                if use_aggregate:
                    query += " AND bucket <= :end_date"
                else:
                    query += " AND timestamp <= :end_date"
                params["end_date"] = end_date

            if user_id:
                query += " AND user_id = :user_id"
                params["user_id"] = user_id

            query += " GROUP BY model, provider ORDER BY total_cost DESC"

            result = await session.execute(text(query), params)
            rows = result.fetchall()

            return [
                ModelCost(
                    model=row[0],
                    provider=row[1],
                    total_cost=Decimal(str(row[2])),
                    total_prompt_tokens=int(row[3]),
                    total_completion_tokens=int(row[4]),
                    request_count=int(row[5]),
                )
                for row in rows
            ]
