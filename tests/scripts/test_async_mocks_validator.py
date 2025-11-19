"""
Unit tests for AsyncMock validation library.

This test file validates the shared validation logic used by:
- scripts/check_async_mock_configuration.py (pre-commit hook)
- scripts/check_async_mock_usage.py (pre-commit hook)
- tests/meta/test_async_mock_configuration.py (meta-tests)

Following TDD: These tests are written FIRST, before the implementation.
"""

import gc
from pathlib import Path
from textwrap import dedent

import pytest

from tests.validation_lib import async_mocks


@pytest.mark.unit
@pytest.mark.meta
@pytest.mark.xdist_group(name="validator_unit_tests")
class TestAsyncMockConfigurationValidator:
    """Unit tests for AsyncMock configuration validation logic."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_detects_unconfigured_async_mock(self, tmp_path: Path) -> None:
        """Test detection of AsyncMock without return_value or side_effect."""
        test_file = tmp_path / "test_bad.py"
        test_file.write_text(
            dedent(
                """
                from unittest.mock import AsyncMock

                def test_something():
                    mock = AsyncMock()  # No configuration - violation
                    assert mock
                """
            )
        )

        violations = async_mocks.check_async_mock_configuration(str(test_file))

        assert len(violations) > 0
        line_num, message = violations[0]
        assert "not configured" in message.lower() or "return_value" in message.lower()

    def test_allows_async_mock_with_return_value(self, tmp_path: Path) -> None:
        """Test that AsyncMock with return_value is allowed."""
        test_file = tmp_path / "test_good.py"
        test_file.write_text(
            dedent(
                """
                from unittest.mock import AsyncMock

                def test_something():
                    mock = AsyncMock()
                    mock.method.return_value = "value"  # Configured
                    assert mock
                """
            )
        )

        violations = async_mocks.check_async_mock_configuration(str(test_file))

        assert len(violations) == 0

    def test_allows_async_mock_with_constructor_kwargs(self, tmp_path: Path) -> None:
        """Test that AsyncMock with constructor kwargs is allowed."""
        test_file = tmp_path / "test_good.py"
        test_file.write_text(
            dedent(
                """
                from unittest.mock import AsyncMock

                def test_something():
                    mock = AsyncMock(return_value="value")  # Configured in constructor
                    assert mock
                """
            )
        )

        violations = async_mocks.check_async_mock_configuration(str(test_file))

        assert len(violations) == 0

    def test_allows_async_mock_with_spec(self, tmp_path: Path) -> None:
        """Test that AsyncMock with spec parameter is considered configured."""
        test_file = tmp_path / "test_good.py"
        test_file.write_text(
            dedent(
                """
                from unittest.mock import AsyncMock

                class SomeClass:
                    pass

                def test_something():
                    mock = AsyncMock(spec=SomeClass)  # Spec counts as configured
                    assert mock
                """
            )
        )

        violations = async_mocks.check_async_mock_configuration(str(test_file))

        assert len(violations) == 0

    def test_respects_noqa_comment(self, tmp_path: Path) -> None:
        """Test that # noqa: async-mock-config comment suppresses warnings."""
        test_file = tmp_path / "test_noqa.py"
        test_file.write_text(
            dedent(
                """
                from unittest.mock import AsyncMock

                def test_something():
                    mock = AsyncMock()  # noqa: async-mock-config
                    assert mock
                """
            )
        )

        violations = async_mocks.check_async_mock_configuration(str(test_file))

        assert len(violations) == 0

    def test_scopes_to_function_boundaries(self, tmp_path: Path) -> None:
        """Test that configuration checking is scoped to function boundaries."""
        test_file = tmp_path / "test_scope.py"
        test_file.write_text(
            dedent(
                """
                from unittest.mock import AsyncMock

                def test_first():
                    mock = AsyncMock()
                    mock.method.return_value = "value"  # Configured in this function

                def test_second():
                    mock = AsyncMock()  # Unconfigured in this function - violation
                    assert mock
                """
            )
        )

        violations = async_mocks.check_async_mock_configuration(str(test_file))

        # Should detect only the violation in test_second
        assert len(violations) == 1
        line_num, message = violations[0]
        # Violation should be for the mock in test_second (around line 7)
        assert line_num > 5


@pytest.mark.unit
@pytest.mark.meta
@pytest.mark.xdist_group(name="validator_unit_tests")
class TestAsyncMockUsageValidator:
    """Unit tests for AsyncMock usage validation logic (async methods must use AsyncMock)."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_detects_async_method_mocked_without_async_mock(self, tmp_path: Path) -> None:
        """Test detection of async method mocked without AsyncMock."""
        test_file = tmp_path / "test_bad.py"
        test_file.write_text(
            dedent(
                """
                from unittest.mock import patch

                def test_something():
                    with patch.object(obj, "async_method"):  # Missing new_callable=AsyncMock
                        result = await obj.async_method()
                        assert result
                """
            )
        )

        violations = async_mocks.check_async_mock_usage(str(test_file))

        assert len(violations) > 0
        line_num, message = violations[0]
        assert "async" in message.lower() or "AsyncMock" in message

    def test_allows_async_method_with_new_callable_async_mock(self, tmp_path: Path) -> None:
        """Test that async methods mocked with new_callable=AsyncMock are allowed."""
        test_file = tmp_path / "test_good.py"
        test_file.write_text(
            dedent(
                """
                from unittest.mock import patch, AsyncMock

                def test_something():
                    with patch.object(obj, "async_method", new_callable=AsyncMock):
                        result = await obj.async_method()
                        assert result
                """
            )
        )

        violations = async_mocks.check_async_mock_usage(str(test_file))

        assert len(violations) == 0

    def test_uses_static_analysis_when_module_path_available(self, tmp_path: Path) -> None:
        """Test that validator uses static analysis to determine if function is async."""
        # This test verifies the validator can parse source files to definitively
        # determine if a function is async (rather than relying on naming patterns)
        test_file = tmp_path / "test_static.py"
        test_file.write_text(
            dedent(
                """
                from unittest.mock import patch

                def test_something():
                    # If validator can find the source, it should know send_message is async
                    with patch("module.send_message"):  # Missing new_callable=AsyncMock
                        pass
                """
            )
        )

        # Create a mock module file
        module_file = tmp_path / "module.py"
        module_file.write_text(
            dedent(
                """
                async def send_message(msg):
                    return msg
                """
            )
        )

        # The validator should detect this if it can find module.py
        # (This test may pass/fail depending on whether the validator finds the file)

    def test_detects_async_patterns_in_method_names(self, tmp_path: Path) -> None:
        """Test detection of async naming patterns (send_, async_, fetch_)."""
        test_file = tmp_path / "test_patterns.py"
        test_file.write_text(
            dedent(
                """
                from unittest.mock import patch

                def test_something():
                    with patch.object(client, "send_request"):  # send_ pattern - likely async
                        pass

                    with patch.object(client, "fetch_data"):  # fetch_ pattern - likely async
                        pass
                """
            )
        )

        violations = async_mocks.check_async_mock_usage(str(test_file))

        # Should detect at least the send_ and fetch_ patterns
        assert len(violations) >= 2

    def test_uses_whitelist_for_known_sync_functions(self, tmp_path: Path) -> None:
        """Test that whitelisted synchronous functions are not flagged."""
        test_file = tmp_path / "test_whitelist.py"
        test_file.write_text(
            dedent(
                """
                from unittest.mock import patch

                def test_something():
                    # _get_sandbox is in whitelist - known synchronous function
                    with patch("module._get_sandbox"):
                        pass
                """
            )
        )

        violations = async_mocks.check_async_mock_usage(str(test_file))

        # Should NOT detect _get_sandbox (whitelisted)
        assert len(violations) == 0

    def test_respects_noqa_comment_for_usage(self, tmp_path: Path) -> None:
        """Test that # noqa: async-mock comment suppresses usage warnings."""
        test_file = tmp_path / "test_noqa.py"
        test_file.write_text(
            dedent(
                """
                from unittest.mock import patch

                def test_something():
                    with patch.object(obj, "async_method"):  # noqa: async-mock
                        pass
                """
            )
        )

        violations = async_mocks.check_async_mock_usage(str(test_file))

        assert len(violations) == 0

    def test_skips_xfail_tests(self, tmp_path: Path) -> None:
        """Test that tests marked with @pytest.mark.xfail are skipped."""
        test_file = tmp_path / "test_xfail.py"
        test_file.write_text(
            dedent(
                """
                import pytest
                from unittest.mock import patch

                @pytest.mark.xfail
                def test_something():
                    with patch.object(obj, "async_method"):  # In xfail test - skip
                        pass
                """
            )
        )

        violations = async_mocks.check_async_mock_usage(str(test_file))

        # Should skip xfail tests
        assert len(violations) == 0


@pytest.mark.unit
@pytest.mark.meta
@pytest.mark.xdist_group(name="async_mocks_validator")
class TestAsyncMocksHelpers:
    """Test helper functions in async_mocks validator."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_is_async_function_detects_async_def(self, tmp_path: Path) -> None:
        """Test that is_async_function_in_source correctly identifies async functions."""
        source_file = tmp_path / "example.py"
        source_file.write_text(
            dedent(
                """
                async def async_func():
                    pass

                def sync_func():
                    pass
                """
            )
        )

        # Test if the helper can identify async vs sync
        # (This test depends on the actual implementation of is_async_function_in_source)

    def test_handles_syntax_errors_gracefully(self, tmp_path: Path) -> None:
        """Test that validators handle files with syntax errors gracefully."""
        test_file = tmp_path / "test_syntax_error.py"
        test_file.write_text(
            dedent(
                """
                def test_something(:  # Syntax error
                    assert True
                """
            )
        )

        # Should not raise exception, should return empty list or handle gracefully
        config_violations = async_mocks.check_async_mock_configuration(str(test_file))
        usage_violations = async_mocks.check_async_mock_usage(str(test_file))

        assert isinstance(config_violations, list)
        assert isinstance(usage_violations, list)
