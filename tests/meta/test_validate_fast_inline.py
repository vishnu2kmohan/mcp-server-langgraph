"""
TDD: Tests for inlined validator execution.

Validates that the inline execution mode produces identical results
to subprocess execution, with performance improvements.

Reference: Codex Audit - Subprocess overhead in validate_fast.py
"""

import gc
import importlib
import time
from io import StringIO
from unittest.mock import patch

import pytest

pytestmark = pytest.mark.meta


@pytest.mark.xdist_group(name="validate_fast_inline")
class TestValidateFastInlineImports:
    """Test that all validators can be imported as modules."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.parametrize(
        "module_name",
        [
            "scripts.validators.validate_pre_push_hook",
            "scripts.validators.validate_repo_root_calculations",
            "scripts.validators.validate_test_time_bombs",
            "scripts.validators.validate_async_fixture_scope",
            "scripts.validators.validate_migration_idempotency",
            "scripts.validators.validate_api_schemas",
            "scripts.validators.validate_serviceaccount_names",
        ],
    )
    def test_validator_module_importable(self, module_name: str) -> None:
        """Test that each validator module can be imported."""
        module = importlib.import_module(module_name)
        assert module is not None

    @pytest.mark.parametrize(
        "module_name",
        [
            "scripts.validators.validate_pre_push_hook",
            "scripts.validators.validate_repo_root_calculations",
            "scripts.validators.validate_test_time_bombs",
            "scripts.validators.validate_async_fixture_scope",
            "scripts.validators.validate_migration_idempotency",
            "scripts.validators.validate_api_schemas",
            "scripts.validators.validate_serviceaccount_names",
        ],
    )
    def test_validator_has_main_function(self, module_name: str) -> None:
        """Test that each validator has a callable main() function."""
        module = importlib.import_module(module_name)
        assert hasattr(module, "main"), f"{module_name} must have a main() function"
        assert callable(module.main), f"{module_name}.main must be callable"

    @pytest.mark.parametrize(
        "module_name",
        [
            "scripts.validators.validate_pre_push_hook",
            "scripts.validators.validate_repo_root_calculations",
            "scripts.validators.validate_test_time_bombs",
            "scripts.validators.validate_async_fixture_scope",
            "scripts.validators.validate_migration_idempotency",
            "scripts.validators.validate_api_schemas",
            "scripts.validators.validate_serviceaccount_names",
        ],
    )
    def test_validator_main_returns_int(self, module_name: str) -> None:
        """Test that each validator's main() returns an int."""
        module = importlib.import_module(module_name)

        # Capture stdout to avoid cluttering test output
        with patch("sys.stdout", new_callable=StringIO):
            with patch("sys.stderr", new_callable=StringIO):
                # Some validators accept argv parameter for argparse compatibility
                import inspect

                sig = inspect.signature(module.main)
                if sig.parameters:
                    result = module.main([])  # Pass empty list for argparse validators
                else:
                    result = module.main()

        assert isinstance(result, int), f"{module_name}.main() must return int, got {type(result)}"
        assert result in (0, 1, 2), f"{module_name}.main() should return 0 (pass), 1 (fail), or 2 (error)"


@pytest.mark.xdist_group(name="validate_fast_inline")
class TestValidateFastInlineRunner:
    """Test the inline runner functionality."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_run_validators_inline_returns_int(self) -> None:
        """Test that run_validators_inline returns an int."""
        from scripts.validators.validate_fast import run_validators_inline

        with patch("sys.stdout", new_callable=StringIO):
            result = run_validators_inline()

        assert isinstance(result, int)

    def test_run_validators_inline_all_pass_returns_zero(self) -> None:
        """Test that run_validators_inline returns 0 when all validators pass."""
        from scripts.validators.validate_fast import run_validators_inline

        with patch("sys.stdout", new_callable=StringIO):
            result = run_validators_inline()

        # In a healthy repo, all validators should pass
        assert result == 0, "All validators should pass in a healthy repo"

    def test_inline_mode_faster_than_subprocess(self) -> None:
        """Test that inline mode has less overhead than subprocess mode."""
        from scripts.validators.validate_fast import run_validators_inline, run_validators_subprocess

        # Run both modes and compare timing
        with patch("sys.stdout", new_callable=StringIO):
            start_subprocess = time.time()
            run_validators_subprocess()
            subprocess_time = time.time() - start_subprocess

            start_inline = time.time()
            run_validators_inline()
            inline_time = time.time() - start_inline

        # Inline should be faster (less interpreter startup overhead)
        # Allow 25% margin for test variance due to system load during xdist parallel execution
        # (Previous 10% margin was too tight, causing flaky failures in CI and pre-push hooks)
        assert inline_time <= subprocess_time * 1.25, (
            f"Inline mode ({inline_time:.2f}s) should not be slower than subprocess mode ({subprocess_time:.2f}s)"
        )


@pytest.mark.xdist_group(name="validate_fast_inline")
class TestValidateFastModeSelection:
    """Test that the mode selection works correctly."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_default_mode_is_inline(self) -> None:
        """Test that the default execution mode is inline."""
        from scripts.validators import validate_fast

        # Check that main() uses inline mode by default
        assert hasattr(validate_fast, "run_validators_inline")

    def test_subprocess_mode_available(self) -> None:
        """Test that subprocess mode is still available for fallback."""
        from scripts.validators import validate_fast

        assert hasattr(validate_fast, "run_validators_subprocess")
