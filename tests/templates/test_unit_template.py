"""
Unit Test Template - xdist-Compatible Pattern

This template provides a cookiecutter pattern for creating unit tests that are
compatible with pytest-xdist (parallel test execution) and follow memory safety
best practices.

NOTE: This is a TEMPLATE file, not an actual test file. It contains placeholder
code with intentionally unused variables to demonstrate patterns. Copy and rename
to test_<feature>.py before using.

USAGE:
1. Copy this file to your test directory
2. Rename to test_<feature>.py
3. Replace placeholder content with your test implementation
4. Ensure all AsyncMock/MagicMock instances have explicit return_value or side_effect

MEMORY SAFETY PATTERN (3 Parts):
1. @pytest.mark.xdist_group(name="...") - Groups related tests in same worker
2. teardown_method() with gc.collect() - Forces GC after each test
3. Explicit AsyncMock configuration - Prevents truthy mock bugs

REFERENCES:
- tests/MEMORY_SAFETY_GUIDELINES.md
- tests/PYTEST_XDIST_BEST_PRACTICES.md
- tests/ASYNC_MOCK_GUIDELINES.md
- Reference implementation: tests/integration/security/test_api_key_indexed_lookup.py
"""

# ruff: noqa: F841  # Template contains intentional placeholder variables

# ============================================================================
# REQUIRED IMPORTS
# ============================================================================
import gc  # Required for memory safety (teardown_method)
import os  # Required for PYTEST_XDIST_WORKER check
from unittest.mock import AsyncMock

import pytest

# ============================================================================
# YOUR IMPORTS
# ============================================================================
# from mcp_server_langgraph.your_module import YourClass
# from tests.helpers.async_mock_helpers import configured_async_mock


# ============================================================================
# MODULE-LEVEL PYTEST MARKERS
# ============================================================================
# Apply markers to all tests in this module
pytestmark = [
    pytest.mark.unit,  # Marks all tests as unit tests
    # pytest.mark.auth,  # Add feature-specific markers as needed
    # pytest.mark.security,
]


# ============================================================================
# TEST CLASS - STANDARD PATTERN
# ============================================================================
@pytest.mark.xdist_group(name="example_feature")  # REQUIRED: Group related tests
class TestExampleFeature:
    """Test suite for [FEATURE_NAME].

    Memory Safety Pattern Applied:
    - xdist_group: Groups tests in same worker to reduce mock diversity
    - teardown_method: Forces GC after each test to prevent mock accumulation
    - Configured AsyncMock: All mocks have explicit return_value/side_effect

    References:
    - Implementation: src/mcp_server_langgraph/[module]/[file].py
    - Related ADR: adr/adr-XXXX-[feature-name].md (if applicable)
    """

    def teardown_method(self):
        """Force garbage collection after each test.

        REQUIRED for memory safety with AsyncMock/MagicMock.

        AsyncMock and MagicMock objects create circular references that prevent
        garbage collection, especially in pytest-xdist workers. Explicit GC
        prevents memory accumulation across tests (observed: 217GB VIRT before
        this pattern, 1.8GB VIRT after).
        """
        gc.collect()

    # ========================================================================
    # SYNC TEST EXAMPLE
    # ========================================================================
    def test_example_sync_function(self):
        """Test example synchronous function.

        GIVEN: A specific scenario
        WHEN: An action is performed
        THEN: Expected outcome occurs
        """
        # GIVEN: Setup test data
        test_input = "example"

        # WHEN: Call function under test
        # result = your_function(test_input)

        # THEN: Assert expected outcome
        # assert result == expected_output
        pass  # TODO: Replace with actual test implementation

    # ========================================================================
    # ASYNC TEST EXAMPLE
    # ========================================================================
    @pytest.mark.asyncio
    async def test_example_async_function(self):
        """Test example asynchronous function.

        GIVEN: Mock dependencies are configured
        WHEN: Async function is called
        THEN: Expected behavior occurs
        """
        # GIVEN: Configure mocks with EXPLICIT return values
        mock_dependency = AsyncMock()
        mock_dependency.some_method.return_value = {"key": "value"}  # EXPLICIT!

        # WHEN: Call async function
        # result = await your_async_function(mock_dependency)

        # THEN: Assert expected outcome
        # assert result == expected_output
        # mock_dependency.some_method.assert_called_once()
        pass  # TODO: Replace with actual test implementation

    # ========================================================================
    # ASYNC TEST WITH MULTIPLE MOCKS
    # ========================================================================
    @pytest.mark.asyncio
    async def test_example_with_multiple_mocks(self):
        """Test function with multiple mock dependencies.

        Demonstrates proper configuration of multiple AsyncMock objects.
        """
        # GIVEN: Multiple mocks, all with EXPLICIT configuration
        mock_keycloak = AsyncMock()
        mock_keycloak.get_user.return_value = {  # EXPLICIT!
            "id": "user-123",
            "username": "testuser",
        }

        mock_redis = AsyncMock()
        mock_redis.get.return_value = None  # EXPLICIT! (cache miss)
        mock_redis.setex.return_value = True  # EXPLICIT!

        # WHEN: Call function with mocked dependencies
        # result = await your_function(keycloak=mock_keycloak, redis=mock_redis)

        # THEN: Assert expected interactions
        # mock_keycloak.get_user.assert_called_once_with("user-123")
        # mock_redis.setex.assert_called_once()
        pass  # TODO: Replace with actual test implementation

    # ========================================================================
    # ASYNC TEST WITH PATCH DECORATOR
    # ========================================================================
    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Template placeholder - replace 'your_module' with actual import path")
    async def test_example_with_patch(self):
        """Test using @patch decorator for external dependencies.

        CRITICAL: When patching async methods, use new_callable=AsyncMock

        NOTE: This test is skipped because it uses placeholder import paths.
        Copy this template to your test file and replace 'your_module' with
        the actual module path before enabling.

        Example:
            @patch("mcp_server_langgraph.auth.keycloak.KeycloakClient")
            async def test_example_with_patch(self, mock_keycloak):
                ...
        """
        # GIVEN: Configure patched dependency
        # mock_external.return_value = "mocked_value"  # EXPLICIT!

        # WHEN: Call function that uses external dependency
        # result = await your_function()

        # THEN: Assert expected outcome
        # assert result == expected_output
        # mock_external.assert_called_once()
        pass  # TODO: Replace with actual test implementation

    # ========================================================================
    # ASYNC TEST PATCHING ASYNC METHOD (CRITICAL PATTERN)
    # ========================================================================
    @pytest.mark.asyncio
    async def test_example_patching_async_method(self):
        """Test patching async methods using new_callable=AsyncMock.

        CRITICAL: Async methods MUST be patched with new_callable=AsyncMock.
        Failing to do so causes tests to hang indefinitely!
        """
        # from your_module import YourClass

        # instance = YourClass()

        # GIVEN: Patch async method with AsyncMock
        # with patch.object(
        #     instance,
        #     "async_method_name",  # Replace with actual async method
        #     new_callable=AsyncMock,  # REQUIRED for async methods!
        #     return_value=expected_value,  # EXPLICIT!
        # ) as mock_method:
        #     # WHEN: Call method that uses the async dependency
        #     result = await instance.method_under_test()
        #
        #     # THEN: Assert expected behavior
        #     assert result == expected_output
        #     mock_method.assert_called_once()
        pass  # TODO: Replace with actual test implementation

    # ========================================================================
    # AUTHORIZATION TEST EXAMPLE
    # ========================================================================
    @pytest.mark.asyncio
    async def test_example_authorization_denied(self):
        """Test that regular users are denied access.

        Demonstrates proper configuration for authorization checks that should DENY.
        """
        # GIVEN: Mock authorization service that denies access
        mock_openfga = AsyncMock()
        mock_openfga.check_permission.return_value = False  # EXPLICIT False!

        # WHEN: Regular user attempts restricted action
        # with pytest.raises(HTTPException) as exc_info:
        #     await perform_restricted_action(openfga=mock_openfga)

        # THEN: Assert 403 Forbidden
        # assert exc_info.value.status_code == 403
        pass  # TODO: Replace with actual test implementation

    # ========================================================================
    # AUTHORIZATION TEST - ADMIN ACCESS
    # ========================================================================
    @pytest.mark.asyncio
    async def test_example_authorization_granted(self):
        """Test that admin users are granted access.

        Demonstrates proper configuration for authorization checks that should ALLOW.
        """
        # GIVEN: Mock authorization service that grants access
        mock_openfga = AsyncMock()
        mock_openfga.check_permission.return_value = True  # EXPLICIT True!

        # WHEN: Admin user performs restricted action
        # result = await perform_restricted_action(openfga=mock_openfga)

        # THEN: Assert action succeeded
        # assert result.success is True
        pass  # TODO: Replace with actual test implementation

    # ========================================================================
    # ERROR HANDLING TEST EXAMPLE
    # ========================================================================
    @pytest.mark.asyncio
    async def test_example_error_handling(self):
        """Test error handling when dependency fails.

        Demonstrates using side_effect for exception testing.
        """
        # GIVEN: Mock that raises exception
        mock_service = AsyncMock()
        mock_service.some_method.side_effect = Exception(  # EXPLICIT!
            "Service unavailable"
        )

        # WHEN: Call function that should handle the error
        # with pytest.raises(Exception) as exc_info:
        #     await your_function(service=mock_service)

        # THEN: Assert error was handled appropriately
        # assert "Service unavailable" in str(exc_info.value)
        pass  # TODO: Replace with actual test implementation

    # ========================================================================
    # PARAMETRIZED TEST EXAMPLE
    # ========================================================================
    @pytest.mark.parametrize(
        "input_value,expected_output",
        [
            ("input1", "output1"),
            ("input2", "output2"),
            ("input3", "output3"),
        ],
    )
    def test_example_parametrized_returns_expected_output(self, input_value, expected_output):
        """Test with multiple input/output combinations.

        Parametrized tests run once per parameter set.
        """
        # WHEN: Call function with parameterized input
        # result = your_function(input_value)

        # THEN: Assert expected output for this parameter set
        # assert result == expected_output
        pass  # TODO: Replace with actual test implementation


# ============================================================================
# PERFORMANCE TEST EXAMPLE (SKIPPED IN PARALLEL MODE)
# ============================================================================
@pytest.mark.performance
@pytest.mark.skipif(
    os.getenv("PYTEST_XDIST_WORKER") is not None,
    reason="Performance tests skipped in parallel mode due to memory overhead",
)
@pytest.mark.xdist_group(name="example_performance")
class TestExamplePerformance:
    """Performance tests for [FEATURE_NAME].

    Performance tests are skipped in parallel mode (pytest -n auto) because:
    1. Performance measurements are invalid with parallel execution
    2. Large mock datasets amplify memory consumption (observed: 42GB+ RES)
    3. These tests are better run serially: pytest -k performance --no-cov
    """

    def teardown_method(self):
        """Force GC to prevent mock accumulation."""
        gc.collect()

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        os.getenv("PYTEST_XDIST_WORKER") is not None,
        reason="Performance tests skipped in parallel mode due to memory overhead",
    )
    async def test_example_performance_with_large_dataset(self):
        """Test performance with large dataset.

        This test is automatically skipped when running pytest -n auto.
        Run separately: pytest tests/ -k performance --no-cov
        """
        # GIVEN: Large dataset
        large_dataset_size = 1000

        # WHEN: Process large dataset
        # start_time = time.time()
        # result = await process_large_dataset(size=large_dataset_size)
        # duration = time.time() - start_time

        # THEN: Assert performance requirements
        # assert duration < 1.0  # Should complete in < 1 second
        # assert result.processed_count == large_dataset_size
        pass  # TODO: Replace with actual test implementation


# ============================================================================
# CHECKLIST FOR USING THIS TEMPLATE
# ============================================================================
"""
BEFORE COMMITTING YOUR TEST:

Memory Safety (REQUIRED):
- [ ] All test classes have @pytest.mark.xdist_group(name="...")
- [ ] All test classes have teardown_method() with gc.collect()
- [ ] All AsyncMock/MagicMock have explicit return_value or side_effect
- [ ] Performance tests have @pytest.mark.skipif for PYTEST_XDIST_WORKER

Test Quality:
- [ ] Tests follow GIVEN-WHEN-THEN structure
- [ ] Test names describe what is being tested and expected outcome
- [ ] Appropriate pytest markers applied (unit, integration, etc.)
- [ ] Authorization tests use explicit True/False (never rely on truthy mocks)
- [ ] Async methods patched with new_callable=AsyncMock

Documentation:
- [ ] Test docstrings explain what is being tested
- [ ] Complex test logic has explanatory comments
- [ ] References to related ADRs or security findings included

Validation:
- [ ] Run: pytest tests/your_test.py -v
- [ ] Run: pytest tests/your_test.py -n auto (parallel execution)
- [ ] Run: python scripts/validation/check_test_memory_safety.py
- [ ] Run: python scripts/validation/check_async_mock_usage.py

REFERENCES:
- Memory Safety: tests/MEMORY_SAFETY_GUIDELINES.md
- pytest-xdist: tests/PYTEST_XDIST_BEST_PRACTICES.md
- AsyncMock: tests/ASYNC_MOCK_GUIDELINES.md
- TDD Standards: ~/.claude/CLAUDE.md
"""
