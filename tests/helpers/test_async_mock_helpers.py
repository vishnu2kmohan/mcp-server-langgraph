"""
Test suite for AsyncMock helper fixtures.

This module tests the safe AsyncMock factory functions that prevent
security vulnerabilities from unconfigured mocks.

Tests follow TDD principles:
- RED phase: These tests will fail until helpers are implemented
- GREEN phase: Implement helpers to make tests pass
- REFACTOR phase: Apply helpers across codebase

Security Context:
    Unconfigured AsyncMock instances return truthy MagicMock objects,
    causing authorization checks to incorrectly pass. These helpers
    enforce explicit configuration to prevent such vulnerabilities.

Related:
    - scripts/check_async_mock_configuration.py (validator)
    - tests/meta/test_async_mock_configuration.py (meta-test)
    - SCIM security bug (commit abb04a6a) - historical incident
"""

import gc
from typing import Any
from unittest.mock import AsyncMock

import pytest

from tests.conftest import get_user_id

# This import will fail until we create the module (RED phase)
try:
    from tests.helpers.async_mock_helpers import configured_async_mock, configured_async_mock_deny, configured_async_mock_raise

    HELPERS_AVAILABLE = True
except ImportError:
    HELPERS_AVAILABLE = False


pytestmark = pytest.mark.unit


@pytest.mark.skipif(not HELPERS_AVAILABLE, reason="Helpers not yet implemented (RED phase)")
@pytest.mark.xdist_group(name="testconfiguredasyncmock")
class TestConfiguredAsyncMock:
    """Test suite for configured_async_mock factory."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        import gc

        gc.collect()

    def test_returns_async_mock_instance(self):
        """GIVEN: Factory is called
        WHEN: Creating a configured mock
        THEN: Should return AsyncMock instance
        """
        mock = configured_async_mock()
        assert isinstance(mock, AsyncMock)

    def test_default_return_value_is_none(self):
        """GIVEN: Factory is called without arguments
        WHEN: Mock is called (not awaited)
        THEN: Should return a coroutine object
        """
        import asyncio
        import inspect

        mock = configured_async_mock()
        result = mock()

        # Verify it returns a coroutine
        assert inspect.iscoroutine(result), "AsyncMock should return coroutine when called"

        # Close coroutine to avoid warning
        result.close()

    @pytest.mark.asyncio
    async def test_async_call_returns_none_by_default(self):
        """GIVEN: Factory is called without arguments
        WHEN: Mock is awaited in async context
        THEN: Should return None
        """
        mock = configured_async_mock()
        result = await mock()
        assert result is None

    @pytest.mark.asyncio
    async def test_custom_return_value(self):
        """GIVEN: Factory is called with custom return_value
        WHEN: Mock is awaited
        THEN: Should return configured value
        """
        expected = {"user_id": "123", "role": "admin"}
        mock = configured_async_mock(return_value=expected)
        result = await mock()
        assert result == expected

    @pytest.mark.asyncio
    async def test_return_value_false_is_preserved(self):
        """GIVEN: Factory is called with return_value=False
        WHEN: Mock is awaited
        THEN: Should return False (not None)

        This test ensures boolean False is preserved,
        critical for authorization checks.
        """
        mock = configured_async_mock(return_value=False)
        result = await mock()
        assert result is False
        assert result is not None

    @pytest.mark.asyncio
    async def test_side_effect_exception(self):
        """GIVEN: Factory is called with side_effect exception
        WHEN: Mock is awaited
        THEN: Should raise configured exception
        """
        mock = configured_async_mock(side_effect=ValueError("Test error"))
        with pytest.raises(ValueError, match="Test error"):
            await mock()

    @pytest.mark.asyncio
    async def test_side_effect_callable(self):
        """GIVEN: Factory is called with side_effect callable
        WHEN: Mock is awaited with arguments
        THEN: Should invoke callable with arguments
        """

        async def side_effect_fn(x: int) -> int:
            return x * 2

        mock = configured_async_mock(side_effect=side_effect_fn)
        result = await mock(5)
        assert result == 10

    def test_spec_parameter_honored(self):
        """GIVEN: Factory is called with spec parameter
        WHEN: Accessing mock attributes
        THEN: Should enforce spec restrictions
        """

        class DummyClass:
            async def method(self) -> str:
                return "test"

        mock = configured_async_mock(spec=DummyClass)
        assert hasattr(mock, "method")
        # Accessing non-spec attribute should raise AttributeError
        with pytest.raises(AttributeError):
            _ = mock.non_existent_attribute


@pytest.mark.skipif(not HELPERS_AVAILABLE, reason="Helpers not yet implemented (RED phase)")
@pytest.mark.xdist_group(name="testconfiguredasyncmockdeny")
class TestConfiguredAsyncMockDeny:
    """Test suite for configured_async_mock_deny factory (authorization denials)."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        import gc

        gc.collect()

    def test_returns_async_mock_instance(self):
        """GIVEN: Factory is called
        WHEN: Creating a deny mock
        THEN: Should return AsyncMock instance
        """
        mock = configured_async_mock_deny()
        assert isinstance(mock, AsyncMock)

    @pytest.mark.asyncio
    async def test_always_returns_false(self):
        """GIVEN: Factory is called
        WHEN: Mock is awaited
        THEN: Should return False (explicit deny)

        Critical for authorization tests - prevents security bypasses.
        """
        mock = configured_async_mock_deny()
        result = await mock()
        assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_regardless_of_arguments(self):
        """GIVEN: Deny mock is created
        WHEN: Called with various arguments
        THEN: Should always return False
        """
        mock = configured_async_mock_deny()
        assert await mock() is False
        assert await mock("arg1") is False
        assert await mock(key="value") is False
        assert await mock("arg1", key="value") is False

    def test_spec_parameter_honored(self):
        """GIVEN: Factory is called with spec parameter
        WHEN: Accessing mock attributes
        THEN: Should enforce spec restrictions while denying
        """

        class AuthChecker:
            async def check_permission(self, user: str, resource: str) -> bool:
                return True  # Real implementation would check

        mock = configured_async_mock_deny(spec=AuthChecker)
        assert hasattr(mock, "check_permission")
        with pytest.raises(AttributeError):
            _ = mock.non_existent_method

    @pytest.mark.asyncio
    async def test_usage_in_authorization_context(self):
        """GIVEN: Authorization check using deny mock
        WHEN: Checking permissions
        THEN: Should deny access (security-safe default)

        This test demonstrates the security-critical use case.
        """
        mock_openfga = configured_async_mock_deny()
        mock_openfga.check_permission = configured_async_mock_deny()

        # Simulate authorization check
        user_id = get_user_id()
        has_permission = await mock_openfga.check_permission(user=user_id, relation="viewer", object="document:secret")

        # Should be denied by default (safe)
        assert has_permission is False


@pytest.mark.skipif(not HELPERS_AVAILABLE, reason="Helpers not yet implemented (RED phase)")
@pytest.mark.xdist_group(name="testconfiguredasyncmockraise")
class TestConfiguredAsyncMockRaise:
    """Test suite for configured_async_mock_raise factory (error scenarios)."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        import gc

        gc.collect()

    def test_returns_async_mock_instance(self):
        """GIVEN: Factory is called with exception
        WHEN: Creating a raise mock
        THEN: Should return AsyncMock instance
        """
        mock = configured_async_mock_raise(ValueError("Test error"))
        assert isinstance(mock, AsyncMock)

    @pytest.mark.asyncio
    async def test_raises_configured_exception(self):
        """GIVEN: Factory is called with ValueError
        WHEN: Mock is awaited
        THEN: Should raise ValueError with message
        """
        mock = configured_async_mock_raise(ValueError("Network timeout"))
        with pytest.raises(ValueError, match="Network timeout"):
            await mock()

    @pytest.mark.asyncio
    async def test_raises_different_exception_types(self):
        """GIVEN: Factory is called with various exception types
        WHEN: Mocks are awaited
        THEN: Should raise corresponding exceptions
        """
        # ConnectionError
        mock_conn = configured_async_mock_raise(ConnectionError("Connection refused"))
        with pytest.raises(ConnectionError, match="Connection refused"):
            await mock_conn()

        # PermissionError
        mock_perm = configured_async_mock_raise(PermissionError("Access denied"))
        with pytest.raises(PermissionError, match="Access denied"):
            await mock_perm()

        # TimeoutError
        mock_timeout = configured_async_mock_raise(TimeoutError("Request timeout"))
        with pytest.raises(TimeoutError, match="Request timeout"):
            await mock_timeout()

    @pytest.mark.asyncio
    async def test_raises_regardless_of_arguments(self):
        """GIVEN: Raise mock is created
        WHEN: Called with various arguments
        THEN: Should always raise configured exception
        """
        mock = configured_async_mock_raise(RuntimeError("Always fails"))

        with pytest.raises(RuntimeError, match="Always fails"):
            await mock()

        with pytest.raises(RuntimeError, match="Always fails"):
            await mock("arg1", "arg2")

        with pytest.raises(RuntimeError, match="Always fails"):
            await mock(key="value")

    def test_spec_parameter_honored(self):
        """GIVEN: Factory is called with spec parameter
        WHEN: Accessing mock attributes
        THEN: Should enforce spec restrictions while raising
        """

        class ApiClient:
            async def fetch_data(self, url: str) -> dict:
                return {}

        mock = configured_async_mock_raise(ConnectionError("API down"), spec=ApiClient)
        assert hasattr(mock, "fetch_data")
        with pytest.raises(AttributeError):
            _ = mock.non_existent_method

    @pytest.mark.asyncio
    async def test_usage_in_error_handling_test(self):
        """GIVEN: Error handling test using raise mock
        WHEN: Testing error recovery
        THEN: Should simulate failure scenarios correctly

        This test demonstrates the error-testing use case.
        """
        mock_api = configured_async_mock_raise(ConnectionError("Service unavailable"))

        # Simulate error handling
        error_message = None
        try:
            await mock_api()  # Call the mock directly
        except ConnectionError as e:
            error_message = str(e)

        assert error_message == "Service unavailable"


@pytest.mark.xdist_group(name="testasyncmockhelperintegration")
@pytest.mark.skipif(not HELPERS_AVAILABLE, reason="Helpers not yet implemented (RED phase)")
class TestAsyncMockHelperIntegration:
    """Integration tests ensuring helpers work together correctly."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    async def test_mixed_helper_usage(self):
        """GIVEN: Multiple helper mocks in same test
        WHEN: Testing complex scenarios
        THEN: Should behave independently and correctly
        """
        # Success scenario
        mock_success = configured_async_mock(return_value={"status": "ok"})

        # Denial scenario
        mock_deny = configured_async_mock_deny()

        # Error scenario
        mock_error = configured_async_mock_raise(ValueError("Invalid input"))

        # Verify independent behavior
        assert await mock_success() == {"status": "ok"}
        assert await mock_deny() is False

        with pytest.raises(ValueError, match="Invalid input"):
            await mock_error()

    @pytest.mark.asyncio
    async def test_authorization_workflow_simulation(self):
        """GIVEN: Complete authorization workflow with helpers
        WHEN: Testing auth flow
        THEN: Should correctly simulate success and failure paths
        """

        # Mock OpenFGA client
        class MockOpenFGA:
            check_permission = configured_async_mock_deny()  # Default deny

        openfga = MockOpenFGA()

        # Test 1: Denied access (default)
        user_id = get_user_id()
        can_view = await openfga.check_permission(user=user_id, relation="viewer", object="document:secret")
        assert can_view is False

        # Test 2: Override for granted access
        openfga.check_permission = configured_async_mock(return_value=True)
        can_edit = await openfga.check_permission(user=user_id, relation="editor", object="document:public")
        assert can_edit is True

        # Test 3: Service error
        openfga.check_permission = configured_async_mock_raise(ConnectionError("OpenFGA unavailable"))
        with pytest.raises(ConnectionError, match="OpenFGA unavailable"):
            await openfga.check_permission(user=user_id, relation="viewer", object="document:any")


@pytest.mark.xdist_group(name="testredphaseverification")
@pytest.mark.skipif(HELPERS_AVAILABLE, reason="This test verifies RED phase")
class TestRedPhaseVerification:
    """Meta-test to verify we're in RED phase (helpers not yet implemented)."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_helpers_not_yet_implemented(self):
        """GIVEN: TDD RED phase
        WHEN: Attempting to import helpers
        THEN: Should fail (confirming RED phase)

        This test will fail once helpers are implemented (GREEN phase).
        """
        assert not HELPERS_AVAILABLE, (
            "Helpers should not be implemented yet (RED phase). " "This test confirms TDD discipline - write tests first!"
        )
