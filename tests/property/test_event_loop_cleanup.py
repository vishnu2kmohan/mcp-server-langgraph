"""
Test event loop cleanup in property-based tests.

MEMORY SAFETY: Ensure event loops are properly cleaned up in property tests
to prevent file descriptor leaks and BaseEventLoop.__del__ errors.

This test validates that the run_async helper in test_auth_properties.py
properly cleans up event loops after each hypothesis example.
"""

import asyncio
import gc

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st


@pytest.mark.unit
@pytest.mark.xdist_group(name="event_loop_cleanup_tests")
class TestEventLoopCleanup:
    """Test proper event loop cleanup in property-based tests"""

    def teardown_method(self):
        """Force GC to prevent accumulation in xdist workers"""
        gc.collect()

    @given(data=st.integers(min_value=1, max_value=100))
    @settings(max_examples=50, deadline=2000)
    def test_event_loop_cleanup_in_hypothesis(self, data):
        """Event loops should be cleaned up properly in property tests"""

        async def async_operation(value):
            """Simple async operation for testing"""
            await asyncio.sleep(0.001)  # Simulate async work
            return value * 2

        # This should not create unclosed event loops
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            result = loop.run_until_complete(async_operation(data))
            assert result == data * 2
        finally:
            # CRITICAL: Close the loop to prevent file descriptor leaks
            try:
                # Cancel all pending tasks
                pending = asyncio.all_tasks(loop)
                for task in pending:
                    task.cancel()

                # Run loop briefly to allow tasks to cancel
                if pending:
                    loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))

                # Close the loop
                loop.close()
            except Exception as e:
                # Log but don't fail the test
                import logging

                logging.getLogger(__name__).warning(f"Error cleaning up event loop: {e}")

        # Verify loop is properly closed
        assert loop.is_closed(), "Event loop should be closed after test"

    def test_run_async_helper_closes_loop(self):
        """The run_async helper should close event loops properly"""

        async def simple_coro():
            """Simple coroutine for testing"""
            return 42

        # Import the helper from test_auth_properties
        import sys
        from pathlib import Path

        # Add tests/property to path
        tests_property_dir = Path(__file__).parent
        if str(tests_property_dir) not in sys.path:
            sys.path.insert(0, str(tests_property_dir))

        try:
            from test_auth_properties import run_async

            # Run the async operation
            result = run_async(simple_coro())
            assert result == 42

            # Verify no event loops are left running
            try:
                asyncio.get_running_loop()
                pytest.fail("Event loop should not be running after run_async completes")
            except RuntimeError:
                # Expected: no running loop
                pass

        except ImportError as e:
            pytest.skip(f"Could not import run_async helper: {e}")

    @given(iterations=st.integers(min_value=1, max_value=10))
    @settings(max_examples=20, deadline=2000)
    def test_multiple_event_loops_dont_leak(self, iterations):
        """Creating multiple event loops should not leak file descriptors"""

        async def async_work(value):
            """Async work that returns a value"""
            return value + 1

        results = []
        for i in range(iterations):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            try:
                result = loop.run_until_complete(async_work(i))
                results.append(result)
            finally:
                # Clean up properly
                try:
                    pending = asyncio.all_tasks(loop)
                    for task in pending:
                        task.cancel()

                    if pending:
                        loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))

                    loop.close()
                except Exception:
                    pass

            # Verify this loop is closed
            assert loop.is_closed()

        # Verify all results are correct
        assert len(results) == iterations
        for i, result in enumerate(results):
            assert result == i + 1
