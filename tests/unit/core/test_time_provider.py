"""
Unit tests for core/time_provider.py.

Tests time provider abstraction for production and testing use cases.
Follows TDD principles and memory safety patterns for pytest-xdist.
"""

import gc

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="time_provider")
class TestRealTimeProvider:
    """Test RealTimeProvider class."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_time_returns_float(self):
        """Test that time() returns a float."""
        from mcp_server_langgraph.core.time_provider import RealTimeProvider

        provider = RealTimeProvider()
        result = provider.time()

        assert isinstance(result, float)
        assert result > 0

    @pytest.mark.unit
    def test_monotonic_returns_float(self):
        """Test that monotonic() returns a float."""
        from mcp_server_langgraph.core.time_provider import RealTimeProvider

        provider = RealTimeProvider()
        result = provider.monotonic()

        assert isinstance(result, float)
        assert result >= 0

    @pytest.mark.unit
    def test_monotonic_increases_over_time(self):
        """Test that monotonic() returns increasing values."""
        from mcp_server_langgraph.core.time_provider import RealTimeProvider

        provider = RealTimeProvider()
        first = provider.monotonic()
        second = provider.monotonic()

        assert second >= first


@pytest.mark.xdist_group(name="time_provider")
class TestVirtualClock:
    """Test VirtualClock class for testing."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_initial_time_is_zero_by_default(self):
        """Test that initial time is 0 by default."""
        from mcp_server_langgraph.core.time_provider import VirtualClock

        clock = VirtualClock()

        assert clock.time() == 0.0

    @pytest.mark.unit
    def test_initial_time_can_be_customized(self):
        """Test that initial time can be set."""
        from mcp_server_langgraph.core.time_provider import VirtualClock

        clock = VirtualClock(start_time=100.0)

        assert clock.time() == 100.0

    @pytest.mark.unit
    def test_sleep_advances_time_instantly(self):
        """Test that sleep advances time without actual waiting."""
        from mcp_server_langgraph.core.time_provider import VirtualClock

        clock = VirtualClock()
        clock.sleep(10.0)

        assert clock.time() == 10.0

    @pytest.mark.unit
    def test_sleep_accumulates_time(self):
        """Test that multiple sleeps accumulate time."""
        from mcp_server_langgraph.core.time_provider import VirtualClock

        clock = VirtualClock()
        clock.sleep(5.0)
        clock.sleep(3.0)
        clock.sleep(2.0)

        assert clock.time() == 10.0

    @pytest.mark.unit
    def test_sleep_rejects_negative_duration(self):
        """Test that negative sleep duration raises ValueError."""
        from mcp_server_langgraph.core.time_provider import VirtualClock

        clock = VirtualClock()

        with pytest.raises(ValueError, match="non-negative"):
            clock.sleep(-1.0)

    @pytest.mark.unit
    def test_monotonic_equals_time(self):
        """Test that monotonic() returns same value as time()."""
        from mcp_server_langgraph.core.time_provider import VirtualClock

        clock = VirtualClock(start_time=50.0)

        assert clock.monotonic() == clock.time()

    @pytest.mark.unit
    def test_advance_increases_time(self):
        """Test that advance() increases time."""
        from mcp_server_langgraph.core.time_provider import VirtualClock

        clock = VirtualClock()
        clock.advance(25.0)

        assert clock.time() == 25.0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_async_sleep_advances_time(self):
        """Test that async_sleep advances time."""
        from mcp_server_langgraph.core.time_provider import VirtualClock

        clock = VirtualClock()
        await clock.async_sleep(15.0)

        assert clock.time() == 15.0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_async_sleep_rejects_negative_duration(self):
        """Test that async_sleep rejects negative duration."""
        from mcp_server_langgraph.core.time_provider import VirtualClock

        clock = VirtualClock()

        with pytest.raises(ValueError, match="non-negative"):
            await clock.async_sleep(-5.0)


@pytest.mark.xdist_group(name="time_provider")
class TestGetDefaultTimeProvider:
    """Test get_default_time_provider function."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_returns_real_time_provider(self):
        """Test that get_default_time_provider returns RealTimeProvider."""
        from mcp_server_langgraph.core.time_provider import (
            RealTimeProvider,
            get_default_time_provider,
        )

        provider = get_default_time_provider()

        assert isinstance(provider, RealTimeProvider)

    @pytest.mark.unit
    def test_returns_same_instance(self):
        """Test that get_default_time_provider returns singleton."""
        from mcp_server_langgraph.core.time_provider import get_default_time_provider

        first = get_default_time_provider()
        second = get_default_time_provider()

        assert first is second
