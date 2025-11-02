"""
Cost Metrics Collector

Tracks token usage and costs for LLM API calls with async recording,
Prometheus metrics integration, and PostgreSQL persistence.

Example:
    >>> from mcp_server_langgraph.monitoring.cost_tracker import CostMetricsCollector
    >>> collector = CostMetricsCollector()
    >>> await collector.record_usage(
    ...     user_id="user123",
    ...     session_id="session456",
    ...     model="claude-3-5-sonnet-20241022",
    ...     provider="anthropic",
    ...     prompt_tokens=1000,
    ...     completion_tokens=500
    ... )
"""

import asyncio
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from .pricing import calculate_cost

# ==============================================================================
# Data Models
# ==============================================================================


class TokenUsage(BaseModel):
    """Token usage record for a single LLM call."""

    timestamp: datetime = Field(description="When the call was made")
    user_id: str = Field(description="User who made the call")
    session_id: str = Field(description="Session identifier")
    model: str = Field(description="Model name")
    provider: str = Field(description="Provider (anthropic, openai, google)")
    prompt_tokens: int = Field(description="Number of input tokens", ge=0)
    completion_tokens: int = Field(description="Number of output tokens", ge=0)
    total_tokens: int = Field(description="Total tokens (prompt + completion)", ge=0)
    estimated_cost_usd: Decimal = Field(description="Estimated cost in USD")
    feature: Optional[str] = Field(default=None, description="Feature that triggered the call")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    class Config:
        json_encoders = {
            Decimal: str,  # Encode Decimal as string in JSON
            datetime: lambda v: v.isoformat(),
        }

    def __init__(self, **data: Any):
        # Calculate total_tokens if not provided
        if "total_tokens" not in data:
            data["total_tokens"] = data.get("prompt_tokens", 0) + data.get("completion_tokens", 0)
        super().__init__(**data)


# ==============================================================================
# Prometheus Metrics (Mock for now - will use real prometheus_client)
# ==============================================================================


@dataclass
class MockPrometheusCounter:
    """Mock Prometheus counter for testing."""

    name: str
    description: str
    labelnames: List[str]
    _values: Dict[tuple, float] = field(default_factory=lambda: defaultdict(float))

    def labels(self, **labels):
        """Return label-specific counter."""
        label_tuple = tuple(labels.get(name, "") for name in self.labelnames)
        return MockCounterChild(self, label_tuple)


@dataclass
class MockCounterChild:
    """Child counter with specific labels."""

    parent: MockPrometheusCounter
    label_values: tuple

    def inc(self, amount: float = 1.0):
        """Increment counter."""
        self.parent._values[self.label_values] += amount


# Mock Prometheus metrics (replace with real prometheus_client in production)
llm_token_usage = MockPrometheusCounter(
    name="llm_token_usage_total",
    description="Total tokens used by LLM calls",
    labelnames=["provider", "model", "token_type"],
)

llm_cost = MockPrometheusCounter(
    name="llm_cost_usd_total",
    description="Total estimated cost in USD",
    labelnames=["provider", "model"],
)


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
    - In-memory storage (TODO: Add PostgreSQL persistence)
    """

    def __init__(self):
        """Initialize the cost metrics collector."""
        self._records: List[TokenUsage] = []
        self._lock = asyncio.Lock()

    @property
    def total_records(self) -> int:
        """Get total number of records."""
        return len(self._records)

    async def record_usage(
        self,
        timestamp: datetime,
        user_id: str,
        session_id: str,
        model: str,
        provider: str,
        prompt_tokens: int,
        completion_tokens: int,
        estimated_cost_usd: Optional[Decimal] = None,
        feature: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
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

        Returns:
            TokenUsage record

        Example:
            >>> collector = CostMetricsCollector()
            >>> usage = await collector.record_usage(
            ...     timestamp=datetime.now(timezone.utc),
            ...     user_id="user123",
            ...     session_id="session456",
            ...     model="claude-3-5-sonnet-20241022",
            ...     provider="anthropic",
            ...     prompt_tokens=1000,
            ...     completion_tokens=500
            ... )
        """
        # Calculate cost if not provided
        if estimated_cost_usd is None:
            estimated_cost_usd = calculate_cost(
                model=model,
                provider=provider,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
            )

        # Create usage record
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
        )

        # Store record (thread-safe)
        async with self._lock:
            self._records.append(usage)

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

    async def get_latest_record(self) -> Optional[TokenUsage]:
        """Get the most recent usage record."""
        async with self._lock:
            return self._records[-1] if self._records else None

    async def get_records(
        self,
        period: str = "day",
        user_id: Optional[str] = None,
        model: Optional[str] = None,
    ) -> List[TokenUsage]:
        """
        Get usage records with optional filtering.

        Args:
            period: Time period ("day", "week", "month")
            user_id: Filter by user (optional)
            model: Filter by model (optional)

        Returns:
            List of TokenUsage records
        """
        async with self._lock:
            records = self._records.copy()

        # Apply filters
        if user_id:
            records = [r for r in records if r.user_id == user_id]

        if model:
            records = [r for r in records if r.model == model]

        # TODO: Apply time period filter

        return records

    async def get_total_cost(
        self,
        user_id: Optional[str] = None,
        period: Optional[str] = None,
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

    async def aggregate_by_model(self, records: List[Dict[str, Any]]) -> Dict[str, Decimal]:
        """
        Aggregate costs by model.

        Args:
            records: List of cost records

        Returns:
            Dict mapping model names to total costs
        """
        aggregated: Dict[str, Decimal] = defaultdict(lambda: Decimal("0"))

        for record in records:
            model = record["model"]
            cost = record["cost"] if isinstance(record["cost"], Decimal) else Decimal(str(record["cost"]))
            aggregated[model] += cost

        return dict(aggregated)

    async def aggregate_by_user(self, records: List[Dict[str, Any]]) -> Dict[str, Decimal]:
        """
        Aggregate costs by user.

        Args:
            records: List of cost records

        Returns:
            Dict mapping user IDs to total costs
        """
        aggregated: Dict[str, Decimal] = defaultdict(lambda: Decimal("0"))

        for record in records:
            user_id = record["user_id"]
            cost = record["cost"] if isinstance(record["cost"], Decimal) else Decimal(str(record["cost"]))
            aggregated[user_id] += cost

        return dict(aggregated)

    async def aggregate_by_feature(self, records: List[Dict[str, Any]]) -> Dict[str, Decimal]:
        """
        Aggregate costs by feature.

        Args:
            records: List of cost records

        Returns:
            Dict mapping feature names to total costs
        """
        aggregated: Dict[str, Decimal] = defaultdict(lambda: Decimal("0"))

        for record in records:
            feature = record.get("feature", "unknown")
            cost = record["cost"] if isinstance(record["cost"], Decimal) else Decimal(str(record["cost"]))
            aggregated[feature] += cost

        return dict(aggregated)

    async def calculate_total(self, records: List[Dict[str, Any]]) -> Decimal:
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

_collector_instance: Optional[CostMetricsCollector] = None


def get_cost_collector() -> CostMetricsCollector:
    """Get or create singleton cost collector instance."""
    global _collector_instance
    if _collector_instance is None:
        _collector_instance = CostMetricsCollector()
    return _collector_instance
