"""
Tests for CostServiceImpl.

TDD: These tests are written FIRST to define the expected behavior
of CostServiceImpl, which wraps CostStorageBackend.

Tests verify:
1. get_summary() delegates to storage.get_cost_summary()
2. get_by_model() delegates to storage.get_cost_by_model()
3. get_history() delegates to storage.get_cost_history()
4. Date string parsing (YYYY-MM-DD -> datetime)
5. Decimal -> float conversion for JSON serialization
"""

from __future__ import annotations

import gc
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest

pytestmark = pytest.mark.unit

if TYPE_CHECKING:
    from mcp_server_langgraph.monitoring.cost_storage import (
        CostSummary,
        DailyCost,
        ModelCost,
    )


class TestCostServiceImpl:
    """Test suite for CostServiceImpl."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.fixture
    def mock_storage(self) -> MagicMock:
        """Create a mock CostStorageBackend."""
        storage = MagicMock()
        storage.get_cost_summary = AsyncMock(return_value=None)  # async-mock-configured  # noqa: async-mock-config
        storage.get_cost_by_model = AsyncMock(return_value=None)  # async-mock-configured  # noqa: async-mock-config
        storage.get_cost_history = AsyncMock(return_value=None)  # async-mock-configured  # noqa: async-mock-config
        return storage

    @pytest.fixture
    def sample_cost_summary(self) -> CostSummary:
        """Create a sample CostSummary for testing."""
        from mcp_server_langgraph.monitoring.cost_storage import CostSummary

        return CostSummary(
            total_cost=Decimal("123.45"),
            total_prompt_tokens=10000,
            total_completion_tokens=5000,
            total_tokens=15000,
            request_count=100,
            period_start=datetime(2025, 1, 1, 0, 0, 0),
            period_end=datetime(2025, 1, 31, 23, 59, 59),
        )

    @pytest.fixture
    def sample_model_costs(self) -> list[ModelCost]:
        """Create sample ModelCost list for testing."""
        from mcp_server_langgraph.monitoring.cost_storage import ModelCost

        return [
            ModelCost(
                model="gpt-4",
                provider="openai",
                total_cost=Decimal("100.00"),
                total_prompt_tokens=8000,
                total_completion_tokens=4000,
                request_count=50,
            ),
            ModelCost(
                model="claude-3-opus",
                provider="anthropic",
                total_cost=Decimal("23.45"),
                total_prompt_tokens=2000,
                total_completion_tokens=1000,
                request_count=50,
            ),
        ]

    @pytest.fixture
    def sample_daily_costs(self) -> list[DailyCost]:
        """Create sample DailyCost list for testing."""
        from mcp_server_langgraph.monitoring.cost_storage import DailyCost

        return [
            DailyCost(
                date=datetime(2025, 1, 1),
                total_cost=Decimal("50.00"),
                total_tokens=5000,
                request_count=30,
            ),
            DailyCost(
                date=datetime(2025, 1, 2),
                total_cost=Decimal("73.45"),
                total_tokens=10000,
                request_count=70,
            ),
        ]

    # =========================================================================
    # get_summary() tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_get_summary_delegates_to_storage(
        self,
        mock_storage: MagicMock,
        sample_cost_summary: CostSummary,
    ) -> None:
        """GIVEN a CostServiceImpl with storage
        WHEN get_summary() is called
        THEN it delegates to storage.get_cost_summary()
        """
        from mcp_server_langgraph.api.v1.cost import CostServiceImpl

        mock_storage.get_cost_summary.return_value = sample_cost_summary
        service = CostServiceImpl(storage=mock_storage)

        result = await service.get_summary()

        mock_storage.get_cost_summary.assert_called_once()
        assert result is not None

    @pytest.mark.asyncio
    async def test_get_summary_parses_date_strings(
        self,
        mock_storage: MagicMock,
        sample_cost_summary: CostSummary,
    ) -> None:
        """GIVEN date strings in YYYY-MM-DD format
        WHEN get_summary() is called
        THEN it parses them to datetime objects for storage
        """
        from mcp_server_langgraph.api.v1.cost import CostServiceImpl

        mock_storage.get_cost_summary.return_value = sample_cost_summary
        service = CostServiceImpl(storage=mock_storage)

        await service.get_summary(start_date="2025-01-01", end_date="2025-01-31")

        call_kwargs = mock_storage.get_cost_summary.call_args.kwargs
        assert call_kwargs["start_date"] == datetime(2025, 1, 1)
        assert call_kwargs["end_date"] == datetime(2025, 1, 31)

    @pytest.mark.asyncio
    async def test_get_summary_returns_dict_with_float_cost(
        self,
        mock_storage: MagicMock,
        sample_cost_summary: CostSummary,
    ) -> None:
        """GIVEN a CostSummary with Decimal cost
        WHEN get_summary() is called
        THEN it returns a dict with float cost (JSON-serializable)
        """
        from mcp_server_langgraph.api.v1.cost import CostServiceImpl

        mock_storage.get_cost_summary.return_value = sample_cost_summary
        service = CostServiceImpl(storage=mock_storage)

        result = await service.get_summary()

        assert isinstance(result["total_cost"], float)
        assert result["total_cost"] == 123.45
        assert result["prompt_tokens"] == 10000
        assert result["completion_tokens"] == 5000
        assert result["total_tokens"] == 15000

    @pytest.mark.asyncio
    async def test_get_summary_handles_none_dates(
        self,
        mock_storage: MagicMock,
        sample_cost_summary: CostSummary,
    ) -> None:
        """GIVEN no date parameters
        WHEN get_summary() is called
        THEN it passes None to storage
        """
        from mcp_server_langgraph.api.v1.cost import CostServiceImpl

        mock_storage.get_cost_summary.return_value = sample_cost_summary
        service = CostServiceImpl(storage=mock_storage)

        await service.get_summary()

        call_kwargs = mock_storage.get_cost_summary.call_args.kwargs
        assert call_kwargs["start_date"] is None
        assert call_kwargs["end_date"] is None

    # =========================================================================
    # get_by_model() tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_get_by_model_delegates_to_storage(
        self,
        mock_storage: MagicMock,
        sample_model_costs: list[ModelCost],
    ) -> None:
        """GIVEN a CostServiceImpl with storage
        WHEN get_by_model() is called
        THEN it delegates to storage.get_cost_by_model()
        """
        from mcp_server_langgraph.api.v1.cost import CostServiceImpl

        mock_storage.get_cost_by_model.return_value = sample_model_costs
        service = CostServiceImpl(storage=mock_storage)

        result = await service.get_by_model()

        mock_storage.get_cost_by_model.assert_called_once()
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_get_by_model_returns_list_of_dicts(
        self,
        mock_storage: MagicMock,
        sample_model_costs: list[ModelCost],
    ) -> None:
        """GIVEN ModelCost list from storage
        WHEN get_by_model() is called
        THEN it returns list of dicts matching ModelCostResponse
        """
        from mcp_server_langgraph.api.v1.cost import CostServiceImpl

        mock_storage.get_cost_by_model.return_value = sample_model_costs
        service = CostServiceImpl(storage=mock_storage)

        result = await service.get_by_model()

        assert result[0]["model"] == "gpt-4"
        assert result[0]["cost"] == 100.0  # Decimal -> float
        assert result[0]["requests"] == 50
        assert result[0]["prompt_tokens"] == 8000
        assert result[0]["completion_tokens"] == 4000

    @pytest.mark.asyncio
    async def test_get_by_model_parses_date_strings(
        self,
        mock_storage: MagicMock,
        sample_model_costs: list[ModelCost],
    ) -> None:
        """GIVEN date strings in YYYY-MM-DD format
        WHEN get_by_model() is called
        THEN it parses them to datetime objects
        """
        from mcp_server_langgraph.api.v1.cost import CostServiceImpl

        mock_storage.get_cost_by_model.return_value = sample_model_costs
        service = CostServiceImpl(storage=mock_storage)

        await service.get_by_model(start_date="2025-01-01", end_date="2025-01-31")

        call_kwargs = mock_storage.get_cost_by_model.call_args.kwargs
        assert call_kwargs["start_date"] == datetime(2025, 1, 1)
        assert call_kwargs["end_date"] == datetime(2025, 1, 31)

    # =========================================================================
    # get_history() tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_get_history_delegates_to_storage(
        self,
        mock_storage: MagicMock,
        sample_daily_costs: list[DailyCost],
    ) -> None:
        """GIVEN a CostServiceImpl with storage
        WHEN get_history() is called
        THEN it delegates to storage.get_cost_history()
        """
        from mcp_server_langgraph.api.v1.cost import CostServiceImpl

        mock_storage.get_cost_history.return_value = sample_daily_costs
        service = CostServiceImpl(storage=mock_storage)

        result = await service.get_history()

        mock_storage.get_cost_history.assert_called_once()
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_get_history_returns_list_of_dicts(
        self,
        mock_storage: MagicMock,
        sample_daily_costs: list[DailyCost],
    ) -> None:
        """GIVEN DailyCost list from storage
        WHEN get_history() is called
        THEN it returns list of dicts matching DailyCostResponse
        """
        from mcp_server_langgraph.api.v1.cost import CostServiceImpl

        mock_storage.get_cost_history.return_value = sample_daily_costs
        service = CostServiceImpl(storage=mock_storage)

        result = await service.get_history()

        assert result[0]["date"] == "2025-01-01"  # datetime -> string
        assert result[0]["cost"] == 50.0  # Decimal -> float
        assert result[0]["requests"] == 30

    @pytest.mark.asyncio
    async def test_get_history_parses_date_strings(
        self,
        mock_storage: MagicMock,
        sample_daily_costs: list[DailyCost],
    ) -> None:
        """GIVEN date strings in YYYY-MM-DD format
        WHEN get_history() is called
        THEN it parses them to datetime objects
        """
        from mcp_server_langgraph.api.v1.cost import CostServiceImpl

        mock_storage.get_cost_history.return_value = sample_daily_costs
        service = CostServiceImpl(storage=mock_storage)

        await service.get_history(start_date="2025-01-01", end_date="2025-01-31")

        call_kwargs = mock_storage.get_cost_history.call_args.kwargs
        assert call_kwargs["start_date"] == datetime(2025, 1, 1)
        assert call_kwargs["end_date"] == datetime(2025, 1, 31)

    # =========================================================================
    # get_cost_service() integration tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_get_cost_service_returns_impl(self) -> None:
        """GIVEN the cost service getter
        WHEN get_cost_service() is called
        THEN it returns a CostServiceImpl (not the stub CostService)
        """
        from mcp_server_langgraph.api.v1.cost import CostServiceImpl, get_cost_service

        service = get_cost_service()

        # This is the key assertion - we must get an impl, not stub
        assert isinstance(service, CostServiceImpl)

    @pytest.mark.asyncio
    async def test_cost_service_impl_does_not_raise_not_implemented(
        self,
        mock_storage: MagicMock,
        sample_cost_summary: CostSummary,
        sample_model_costs: list[ModelCost],
        sample_daily_costs: list[DailyCost],
    ) -> None:
        """GIVEN a CostServiceImpl
        WHEN any method is called
        THEN it does NOT raise NotImplementedError
        """
        from mcp_server_langgraph.api.v1.cost import CostServiceImpl

        mock_storage.get_cost_summary.return_value = sample_cost_summary
        mock_storage.get_cost_by_model.return_value = sample_model_costs
        mock_storage.get_cost_history.return_value = sample_daily_costs

        service = CostServiceImpl(storage=mock_storage)

        # These should NOT raise NotImplementedError
        await service.get_summary()
        await service.get_by_model()
        await service.get_history()
