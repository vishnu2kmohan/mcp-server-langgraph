"""
Time manipulation fixtures for test suite.

This module provides fixtures for:
- Freezing time for deterministic timestamp testing
- Eliminating time-dependent test flakiness

Extracted from tests/conftest.py to improve maintainability.
See: Testing Strategy Remediation Plan - Phase 3.4
"""

import pytest

# Check if freezegun is available (optional dependency)
try:
    from freezegun import freeze_time

    FREEZEGUN_AVAILABLE = True
except ImportError:
    FREEZEGUN_AVAILABLE = False


@pytest.fixture
def frozen_time():
    """
    Freeze time for deterministic timestamp testing.

    All datetime.now(), time.time(), etc. calls will return the fixed time.
    This eliminates test flakiness caused by time-dependent assertions.

    Usage:
        @pytest.mark.usefixtures("frozen_time")
        def test_timestamps():
            # datetime.now() will always return 2024-01-01T00:00:00Z
            assert datetime.now(timezone.utc).isoformat() == "2024-01-01T00:00:00+00:00"
    """
    if not FREEZEGUN_AVAILABLE:
        pytest.skip("freezegun not installed - required for time-freezing tests. Install with: pip install freezegun")

    with freeze_time("2024-01-01 00:00:00", tz_offset=0):
        yield


@pytest.fixture
def virtual_clock():
    """
    Fixture providing a VirtualClock instance for testing time-dependent logic.
    Allows deterministic control over time without relying on system clock.
    """
    try:
        from mcp_server_langgraph.core.time_provider import VirtualClock

        return VirtualClock()
    except ImportError:
        # Fallback mock if core module not available
        class MockVirtualClock:
            def time(self):
                return 0.0

            def sleep(self, seconds):
                pass

        return MockVirtualClock()
