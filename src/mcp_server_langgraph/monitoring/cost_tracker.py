"""
Cost Metrics Collector

Tracks token usage and costs for LLM API calls with async recording,
Prometheus metrics integration, and PostgreSQL persistence.

Architecture (Phase 2.2 SRP decomposition):
- CostStorageBackend: Handles storage logic (cost_storage.py)
- CostRetentionPolicy: Handles retention/cleanup logic (cost_retention.py)
- CostMetricsCollector: Facade coordinating storage, persistence, and metrics

Example:
    >>> from mcp_server_langgraph.monitoring.cost_tracker import CostMetricsCollector
    >>> collector = CostMetricsCollector()
    >>> await collector.record_usage(
    ...     user_id="user123",
    ...     session_id="session456",
    ...     model="claude-sonnet-4-5-20250929",
    ...     provider="anthropic",
    ...     prompt_tokens=1000,
    ...     completion_tokens=500
    ... )
"""

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, UTC
from decimal import Decimal
from typing import Any, cast

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from .litellm_cost_callback import get_model_cost_from_litellm

# ==============================================================================
# Data Models
# ==============================================================================


class TokenUsage(BaseModel):
    """Token usage record for a single LLM call.

    Includes distributed tracing fields for cost attribution by session,
    workflow, and orchestrator. These fields enable correlation between
    OpenTelemetry traces and cost records.
    """

    timestamp: datetime = Field(description="When the call was made")
    user_id: str = Field(description="User who made the call")
    session_id: str = Field(description="Session identifier")
    model: str = Field(description="Model name")
    provider: str = Field(description="Provider (anthropic, openai, google)")
    prompt_tokens: int = Field(description="Number of input tokens", ge=0)
    completion_tokens: int = Field(description="Number of output tokens", ge=0)
    total_tokens: int = Field(description="Total tokens (prompt + completion)", ge=0)
    estimated_cost_usd: Decimal = Field(description="Estimated cost in USD")
    feature: str | None = Field(default=None, description="Feature that triggered the call")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    # ==========================================================================
    # Distributed Tracing Fields for Cost Attribution
    # ==========================================================================
    trace_id: str | None = Field(
        default=None,
        description="OpenTelemetry trace ID for correlating cost with execution traces",
    )
    span_id: str | None = Field(
        default=None,
        description="OpenTelemetry span ID for the specific LLM call",
    )
    workflow_id: str | None = Field(
        default=None,
        description="Workflow ID for attributing cost to specific workflows",
    )
    orchestrator_id: str | None = Field(
        default=None,
        description="Orchestrator/Agent ID for attributing cost to specific agents",
    )
    request_id: str | None = Field(
        default=None,
        description="Request tracking ID for individual request cost tracking",
    )

    # ==========================================================================
    # Organizational Hierarchy Fields for Multi-Tenant Cost Attribution
    # ==========================================================================
    organization_id: str | None = Field(
        default=None,
        description="Organization ID for multi-tenant cost attribution (e.g., 'organization:acme')",
    )
    project_id: str | None = Field(
        default=None,
        description="Project ID for project-level cost breakdown (e.g., 'project:backend')",
    )
    team_id: str | None = Field(
        default=None,
        description="Team/group ID for team-level cost attribution (e.g., 'team:platform')",
    )

    # ==========================================================================
    # Custom Cost Allocation Tags
    # ==========================================================================
    allocation_tags: dict[str, str] | None = Field(
        default=None,
        description="Custom key-value tags for cost allocation (e.g., {'environment': 'production', 'campaign': 'launch-2025'})",
    )

    model_config = ConfigDict()

    @field_serializer("estimated_cost_usd")
    def serialize_decimal(self, value: Decimal) -> str:
        """Serialize Decimal as string for JSON compatibility."""
        return str(value)

    @field_serializer("timestamp")
    def serialize_timestamp(self, value: datetime) -> str:
        """Serialize datetime as ISO 8601 string."""
        return value.isoformat()

    def __init__(self, **data: Any):
        # Calculate total_tokens if not provided
        if "total_tokens" not in data:
            data["total_tokens"] = data.get("prompt_tokens", 0) + data.get("completion_tokens", 0)
        super().__init__(**data)


# ==============================================================================
# Prometheus Metrics
# ==============================================================================

try:
    from prometheus_client import Counter

    # Real Prometheus metrics for production
    llm_token_usage = Counter(
        name="llm_token_usage_total",
        documentation="Total tokens used by LLM calls",
        labelnames=["provider", "model", "token_type"],
    )

    llm_cost = Counter(
        name="llm_cost_usd_total",
        documentation="Total estimated cost in USD (cumulative)",
        labelnames=["provider", "model"],
    )

    PROMETHEUS_AVAILABLE = True

except ImportError:
    # Fallback to mock counters if prometheus_client not available
    import warnings

    warnings.warn(
        "prometheus_client not available, using mock counters. "
        "Install prometheus-client for production metrics: pip install prometheus-client"
    )

    @dataclass
    class MockPrometheusCounter:
        """Mock Prometheus counter for testing."""

        name: str
        description: str
        labelnames: list[str]
        _values: dict[tuple[str, ...], float] = field(default_factory=lambda: defaultdict(float))

        def labels(self, **labels: str) -> "MockCounterChild":
            """Return label-specific counter."""
            label_tuple = tuple(labels.get(name, "") for name in self.labelnames)
            return MockCounterChild(self, label_tuple)

    @dataclass
    class MockCounterChild:
        """Child counter with specific labels."""

        parent: MockPrometheusCounter
        label_values: tuple[str, ...]

        def inc(self, amount: float = 1.0) -> None:
            """Increment counter."""
            self.parent._values[self.label_values] += amount

    # Mock Prometheus metrics (fallback when prometheus_client not installed)
    llm_token_usage = cast(
        Counter,
        MockPrometheusCounter(
            name="llm_token_usage_total",
            description="Total tokens used by LLM calls",
            labelnames=["provider", "model", "token_type"],
        ),
    )

    llm_cost = cast(
        Counter,
        MockPrometheusCounter(
            name="llm_cost_usd_total",
            description="Total estimated cost in USD",
            labelnames=["provider", "model"],
        ),
    )

    PROMETHEUS_AVAILABLE = False


# ==============================================================================
# Cost Metrics Collector
# ==============================================================================


class CostMetricsCollector:
    """
    Collects and persists LLM cost metrics.

    Features:
    - Async recording to avoid blocking API calls
    - Automatic cost calculation
    - Prometheus metrics integration
    - PostgreSQL persistence with retention policy
    - In-memory fallback when database unavailable

    Architecture (Phase 2.2 SRP):
    - Delegates storage to CostStorageBackend (MemoryCostStorage)
    - Delegates retention to CostRetentionPolicy
    """

    def __init__(
        self,
        database_url: str | None = None,
        retention_days: int = 90,
        enable_persistence: bool = True,
        storage_backend: str | None = None,
    ) -> None:
        """
        Initialize the cost metrics collector.

        Args:
            database_url: PostgreSQL connection URL (postgresql+asyncpg://...)
                         If None, uses in-memory storage only
            retention_days: Number of days to retain records (default: 90)
            enable_persistence: Whether to enable PostgreSQL persistence
            storage_backend: Storage backend type ("memory" or "postgres")
                            If None, uses COST_STORAGE_BACKEND from config
        """
        # Phase 2.2 SRP: Delegate to specialized services
        from mcp_server_langgraph.monitoring.cost_retention import CostRetentionPolicy
        from mcp_server_langgraph.monitoring.cost_storage_factory import (
            get_cost_storage_backend,
        )

        # CRITICAL FIX: Use the shared storage backend from the factory
        # This ensures CostMetricsCollector and CostServiceImpl use the same storage instance.
        # Previously, the collector created its own MemoryCostStorage which caused cost recordings
        # to be invisible to the cost API endpoints (they used a different storage instance).
        #
        # The storage_backend and database_url parameters are now deprecated (kept for backwards
        # compatibility but ignored). Configuration should be done via environment variables:
        # - COST_STORAGE_BACKEND: "memory" or "postgres"
        # - DATABASE_URL: PostgreSQL connection string (for postgres backend)
        self._storage = get_cost_storage_backend()
        self._retention_policy = CostRetentionPolicy(retention_days=retention_days)
        self._database_url = database_url
        self._retention_days = retention_days
        self._enable_persistence = enable_persistence and database_url is not None

    @property
    def total_records(self) -> int:
        """Get total number of records."""
        # Phase 2.2 SRP: Delegate to storage
        return self._storage.total_records

    async def record_usage(
        self,
        timestamp: datetime,
        user_id: str,
        session_id: str,
        model: str,
        provider: str,
        prompt_tokens: int,
        completion_tokens: int,
        estimated_cost_usd: Decimal | None = None,
        feature: str | None = None,
        metadata: dict[str, Any] | None = None,
        # Distributed tracing fields for cost attribution
        trace_id: str | None = None,
        span_id: str | None = None,
        workflow_id: str | None = None,
        orchestrator_id: str | None = None,
        request_id: str | None = None,
        # Organizational hierarchy for multi-tenant cost attribution
        organization_id: str | None = None,
        project_id: str | None = None,
        team_id: str | None = None,
        # Custom cost allocation tags
        allocation_tags: dict[str, str] | None = None,
    ) -> TokenUsage:
        """
        Record token usage for an LLM call.

        Args:
            timestamp: When the call was made
            user_id: User identifier
            session_id: Session identifier
            model: Model name
            provider: Provider name
            prompt_tokens: Input token count
            completion_tokens: Output token count
            estimated_cost_usd: Pre-calculated cost (optional)
            feature: Feature name (optional)
            metadata: Additional metadata (optional)
            trace_id: OpenTelemetry trace ID for cost-trace correlation (optional)
            span_id: OpenTelemetry span ID for the LLM call (optional)
            workflow_id: Workflow ID for cost attribution (optional)
            orchestrator_id: Orchestrator/Agent ID for cost attribution (optional)
            request_id: Request tracking ID (optional)
            organization_id: Organization ID for multi-tenant cost attribution (optional)
            project_id: Project ID for project-level cost breakdown (optional)
            team_id: Team/group ID for team-level cost attribution (optional)
            allocation_tags: Custom key-value tags for cost allocation (optional)

        Returns:
            TokenUsage record

        Example:
            >>> collector = CostMetricsCollector()
            >>> usage = await collector.record_usage(
            ...     timestamp=datetime.now(timezone.utc),
            ...     user_id="user123",
            ...     session_id="session456",
            ...     model="claude-sonnet-4-5-20250929",
            ...     provider="anthropic",
            ...     prompt_tokens=1000,
            ...     completion_tokens=500,
            ...     trace_id="abc123",  # For OpenTelemetry correlation
            ...     workflow_id="workflow-789",  # For workflow cost attribution
            ... )
        """
        # Calculate cost if not provided using LiteLLM's pricing data
        if estimated_cost_usd is None:
            estimated_cost_usd = get_model_cost_from_litellm(
                model=model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
            )

        # Create usage record with distributed tracing fields
        usage = TokenUsage(
            timestamp=timestamp,
            user_id=user_id,
            session_id=session_id,
            model=model,
            provider=provider,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            estimated_cost_usd=estimated_cost_usd,
            feature=feature,
            metadata=metadata or {},
            # Distributed tracing fields
            trace_id=trace_id,
            span_id=span_id,
            workflow_id=workflow_id,
            orchestrator_id=orchestrator_id,
            request_id=request_id,
            # Organizational hierarchy
            organization_id=organization_id,
            project_id=project_id,
            team_id=team_id,
            # Custom allocation tags
            allocation_tags=allocation_tags,
        )

        # Phase 2.2 SRP: Delegate storage to storage backend
        await self._storage.store(usage)

        # Persist to PostgreSQL if enabled
        if self._enable_persistence:
            try:
                await self._persist_to_database(usage)
            except Exception as e:
                # Log error but don't fail the recording
                import logging

                logger = logging.getLogger(__name__)
                logger.exception(f"Failed to persist usage record to database: {e}")

        # Update Prometheus metrics
        llm_token_usage.labels(
            provider=provider,
            model=model,
            token_type="input",
        ).inc(prompt_tokens)

        llm_token_usage.labels(
            provider=provider,
            model=model,
            token_type="output",
        ).inc(completion_tokens)

        llm_cost.labels(
            provider=provider,
            model=model,
        ).inc(float(estimated_cost_usd))

        return usage

    async def _persist_to_database(self, usage: TokenUsage) -> None:
        """
        Persist usage record to PostgreSQL.

        Args:
            usage: TokenUsage record to persist
        """
        if not self._database_url:
            return

        from mcp_server_langgraph.database import get_async_session
        from mcp_server_langgraph.database.models import TokenUsageRecord

        async with get_async_session(self._database_url) as session:
            # Create database record
            db_record = TokenUsageRecord(
                timestamp=usage.timestamp,
                user_id=usage.user_id,
                session_id=usage.session_id,
                model=usage.model,
                provider=usage.provider,
                prompt_tokens=usage.prompt_tokens,
                completion_tokens=usage.completion_tokens,
                total_tokens=usage.total_tokens,
                estimated_cost_usd=usage.estimated_cost_usd,
                feature=usage.feature,
                metadata_=usage.metadata,
                # Organizational hierarchy for cost attribution
                organization_id=usage.organization_id,
                project_id=usage.project_id,
                team_id=usage.team_id,
            )

            session.add(db_record)
            # Session commits automatically via context manager

    async def cleanup_old_records(self) -> int:
        """
        Remove records older than retention period.

        This method removes both in-memory and PostgreSQL records that exceed
        the configured retention period (default: 90 days).

        Phase 2.2 SRP: Delegates in-memory cleanup to CostRetentionPolicy.

        Returns:
            Number of records deleted

        Example:
            >>> collector = CostMetricsCollector(database_url="...", retention_days=90)
            >>> deleted = await collector.cleanup_old_records()
            >>> print(f"Deleted {deleted} old records")
        """
        from datetime import timedelta

        # Phase 2.2 SRP: Delegate in-memory cleanup to retention policy
        deleted_count = await self._retention_policy.cleanup(self._storage)

        # Clean up PostgreSQL records
        if self._enable_persistence:
            try:
                from sqlalchemy import delete

                from mcp_server_langgraph.database import get_async_session
                from mcp_server_langgraph.database.models import TokenUsageRecord

                # Type guard: _database_url is guaranteed non-None when _enable_persistence is True
                assert self._database_url is not None, "database_url must be set when persistence is enabled"

                cutoff_time = datetime.now(UTC) - timedelta(days=self._retention_days)
                async with get_async_session(self._database_url) as session:
                    stmt = delete(TokenUsageRecord).where(TokenUsageRecord.timestamp < cutoff_time)
                    result = await session.execute(stmt)
                    db_deleted = result.rowcount or 0  # type: ignore[attr-defined]
                    deleted_count += db_deleted

                    import logging

                    logger = logging.getLogger(__name__)
                    logger.info(
                        f"Cleaned up {db_deleted} database records older than {self._retention_days} days "
                        f"(cutoff: {cutoff_time.isoformat()})"
                    )
            except Exception as e:
                import logging

                logger = logging.getLogger(__name__)
                logger.exception(f"Failed to cleanup database records: {e}")

        return deleted_count

    async def get_latest_record(self) -> TokenUsage | None:
        """Get the most recent usage record."""
        # Phase 2.2 SRP: Delegate to storage
        return await self._storage.get_latest_record()

    async def get_records(
        self,
        period: str = "day",
        user_id: str | None = None,
        model: str | None = None,
    ) -> list[TokenUsage]:
        """
        Get usage records with optional filtering.

        Phase 2.2 SRP: Delegates to storage backend for filtering.

        Args:
            period: Time period ("day", "week", "month")
            user_id: Filter by user (optional)
            model: Filter by model (optional)

        Returns:
            List of TokenUsage records
        """
        # Phase 2.2 SRP: Build filters and delegate to storage
        filters: dict[str, str] = {}
        if user_id:
            filters["user_id"] = user_id
        if model:
            filters["model"] = model

        # Storage now returns tuple (records, next_cursor)
        records, _ = await self._storage.get_records(filters=filters if filters else None)

        # Apply time period filter
        records = self._filter_by_period(records, period)

        return records

    def _filter_by_period(
        self,
        records: list[TokenUsage],
        period: str,
    ) -> list[TokenUsage]:
        """
        Filter records by time period.

        Args:
            records: List of TokenUsage records
            period: Time period ("day", "week", "month")

        Returns:
            Filtered records within the specified time period
        """
        from datetime import datetime, timedelta

        now = datetime.now(UTC)

        # Calculate cutoff time based on period
        if period == "day":
            cutoff = now - timedelta(days=1)
        elif period == "week":
            cutoff = now - timedelta(days=7)
        elif period == "month":
            cutoff = now - timedelta(days=30)
        else:
            # Unknown period, return all records
            return records

        # Filter records by timestamp
        return [r for r in records if r.timestamp >= cutoff]

    async def get_total_cost(
        self,
        user_id: str | None = None,
        period: str | None = None,
    ) -> Decimal:
        """
        Calculate total cost with optional filters.

        Args:
            user_id: Filter by user (optional)
            period: Time period (optional)

        Returns:
            Total cost in USD
        """
        records = await self.get_records(period=period or "day", user_id=user_id)
        return sum((r.estimated_cost_usd for r in records), Decimal("0"))


# ==============================================================================
# Cost Aggregator
# ==============================================================================


class CostAggregator:
    """
    Aggregates cost data by multiple dimensions.

    Provides:
    - Cost by model
    - Cost by user
    - Cost by feature
    - Total cost calculation
    """

    async def _aggregate_by_field(self, records: list[dict[str, Any]], field: str) -> dict[str, Decimal]:
        """
        Generic aggregation by any field.

        Args:
            records: List of cost records
            field: Field name to aggregate by

        Returns:
            Dictionary mapping field values to total costs
        """
        aggregated: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
        for record in records:
            key = record.get(field, "unknown")
            cost = record.get("cost", Decimal("0"))
            if isinstance(cost, str):
                cost = Decimal(cost)
            elif not isinstance(cost, Decimal):
                cost = Decimal(str(cost))
            aggregated[key] += cost
        return dict(aggregated)

    async def aggregate_by_model(self, records: list[dict[str, Any]]) -> dict[str, Decimal]:
        """
        Aggregate costs by model.

        Args:
            records: List of cost records

        Returns:
            Dict mapping model names to total costs
        """
        return await self._aggregate_by_field(records, "model")

    async def aggregate_by_user(self, records: list[dict[str, Any]]) -> dict[str, Decimal]:
        """
        Aggregate costs by user.

        Args:
            records: List of cost records

        Returns:
            Dict mapping user IDs to total costs
        """
        return await self._aggregate_by_field(records, "user_id")

    async def aggregate_by_feature(self, records: list[dict[str, Any]]) -> dict[str, Decimal]:
        """
        Aggregate costs by feature.

        Args:
            records: List of cost records

        Returns:
            Dict mapping feature names to total costs
        """
        return await self._aggregate_by_field(records, "feature")

    async def calculate_total(self, records: list[dict[str, Any]]) -> Decimal:
        """
        Calculate total cost across all records.

        Args:
            records: List of cost records

        Returns:
            Total cost in USD
        """
        total = Decimal("0")

        for record in records:
            cost = record["cost"] if isinstance(record["cost"], Decimal) else Decimal(str(record["cost"]))
            total += cost

        return total


# ==============================================================================
# Singleton Instance
# ==============================================================================

_collector_instance: CostMetricsCollector | None = None


def get_cost_collector() -> CostMetricsCollector:
    """Get or create singleton cost collector instance."""
    global _collector_instance
    if _collector_instance is None:
        _collector_instance = CostMetricsCollector()
    return _collector_instance


def _reset_cost_collector() -> None:
    """Reset the singleton collector instance (for testing only)."""
    global _collector_instance
    _collector_instance = None


# ==============================================================================
# Redis Session Cost Cache Integration
# ==============================================================================


async def update_session_cost_cache(
    session_id: str,
    cost: float,
    tokens: int,
) -> None:
    """
    Update the Redis session cost cache.

    This function is called after cost recording to update the WebSocket
    cost tracking cache, enabling real-time cost visibility in the UI.

    Args:
        session_id: Session identifier.
        cost: Cost in USD to add.
        tokens: Token count to add.
    """
    from mcp_server_langgraph.websocket.services.cost_tracking import (
        get_websocket_cost_service,
    )

    try:
        service = get_websocket_cost_service()
        await service.update_session_cost_async(
            session_id=session_id,
            cost=cost,
            tokens=tokens,
        )
    except Exception as e:
        # Don't let cache update failures affect cost recording
        import logging

        logger = logging.getLogger(__name__)
        logger.warning(
            f"Failed to update session cost cache for {session_id}: {e}",
            extra={"session_id": session_id, "error": str(e)},
        )


async def invalidate_session_cost_cache(session_id: str) -> None:
    """
    Invalidate the Redis session cost cache for a deleted session.

    This function should be called when a session is deleted to ensure
    stale cost data is not returned by the WebSocket cost tracking endpoint.

    Args:
        session_id: Session identifier.
    """
    from mcp_server_langgraph.websocket.services.cost_tracking import (
        get_websocket_cost_service,
    )

    try:
        service = get_websocket_cost_service()
        await service.invalidate_session_cost(session_id)
    except Exception as e:
        # Don't let cache invalidation failures affect session deletion
        import logging

        logger = logging.getLogger(__name__)
        logger.warning(
            f"Failed to invalidate session cost cache for {session_id}: {e}",
            extra={"session_id": session_id, "error": str(e)},
        )
