"""
Pytest fixtures for time provider abstraction.

Provides virtual clock fixtures for fast test execution without real sleep().

Usage:
    def test_ttl_expiration(virtual_clock):
        cache = CacheService(l1_maxsize=100, l1_ttl=1.0)
        cache.set("key", "value")

        # Instead of time.sleep(1.5), instantly advance
        virtual_clock.advance(1.5)

        assert cache.get("key") is None  # Expired
"""

import pytest

from mcp_server_langgraph.core.time_provider import VirtualClock


@pytest.fixture
def virtual_clock() -> VirtualClock:
    """
    Provide a VirtualClock instance for instant time advancement.

    This eliminates sleep() overhead in tests that verify TTL, timeouts,
    and staleness behavior.

    Returns:
        VirtualClock instance starting at time=0.0
    """
    return VirtualClock()


@pytest.fixture
def virtual_clock_at_epoch() -> VirtualClock:
    """
    Provide a VirtualClock starting at Unix epoch (1970-01-01 00:00:00).

    Useful for tests that need realistic timestamps.

    Returns:
        VirtualClock instance starting at time=0.0 (Unix epoch)
    """
    return VirtualClock(start_time=0.0)


@pytest.fixture
def virtual_clock_at_now() -> VirtualClock:
    """
    Provide a VirtualClock starting at current real time.

    Useful for tests that need current timestamps but still want
    instant time advancement.

    Returns:
        VirtualClock instance starting at current time
    """
    import time

    return VirtualClock(start_time=time.time())
