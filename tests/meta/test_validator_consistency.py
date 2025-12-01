"""
Validator Consistency Integration Tests.

This meta-test ensures that validation scripts produce identical results to the
shared validation library. This guarantees consistency between:
- Pre-commit hook script execution
- Direct library function calls
- Meta-test invocations

CRITICAL: These tests catch divergence between script wrappers and library implementation.

Following TDD: These tests validate the architecture we built in 3 phases.
"""

import gc
import subprocess
import sys
from pathlib import Path
from textwrap import dedent

import pytest

from tests.validation_lib import async_mocks, memory_safety
import scripts.validators.validate_ids as test_ids

pytestmark = pytest.mark.meta


@pytest.mark.meta
@pytest.mark.meta
@pytest.mark.xdist_group(name="validator_consistency")
class TestValidatorConsistency:
    """Ensure scripts and library produce identical results."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.fixture
    def project_root(self) -> Path:
        """Get the project root directory."""
        return Path(__file__).parent.parent.parent

    # Memory Safety Validator

    def test_memory_safety_script_matches_library_on_violation(self, tmp_path: Path, project_root: Path) -> None:
        """Test that memory safety script and library produce identical results for violations."""
        test_file = tmp_path / "test_bad.py"
        test_file.write_text(
            dedent(
                """
                from unittest.mock import AsyncMock

                class TestSomething:
                    def test_method(self):
                        mock = AsyncMock()  # Violation - no xdist_group
                        assert mock
                """
            )
        )

        # Run library function
        lib_violations = memory_safety.check_file(str(test_file))

        # Run script
        script_path = project_root / "scripts" / "validators" / "check_test_memory_safety.py"
        result = subprocess.run([sys.executable, str(script_path), str(test_file)], capture_output=True, text=True, timeout=30)

        # Both should detect violations
        assert len(lib_violations) > 0, "Library should detect violations"
        assert result.returncode == 1, "Script should return exit code 1"
        assert "missing @pytest.mark.xdist_group" in result.stdout or "missing @pytest.mark.xdist_group" in result.stderr

    def test_memory_safety_script_matches_library_on_valid(self, tmp_path: Path, project_root: Path) -> None:
        """Test that memory safety script and library agree on valid files."""
        test_file = tmp_path / "test_good.py"
        test_file.write_text(
            dedent(
                """
                import gc
                from unittest.mock import AsyncMock
                import pytest

                @pytest.mark.xdist_group(name="test_group")
                class TestSomething:
                    def teardown_method(self):
                        gc.collect()

                    def test_method(self):
                        mock = AsyncMock()
                        assert mock
                """
            )
        )

        # Run library function
        lib_violations = memory_safety.check_file(str(test_file))

        # Run script
        script_path = project_root / "scripts" / "validators" / "check_test_memory_safety.py"
        result = subprocess.run([sys.executable, str(script_path), str(test_file)], capture_output=True, text=True, timeout=30)

        # Both should pass
        assert len(lib_violations) == 0, "Library should find no violations"
        assert result.returncode == 0, "Script should return exit code 0"
        assert "No violations found" in result.stdout

    # Test IDs Validator

    def test_test_ids_script_matches_library_on_violation(self, tmp_path: Path, project_root: Path) -> None:
        """Test that test IDs script and library produce identical results for violations."""
        test_file = tmp_path / "test_bad.py"
        test_file.write_text(
            dedent(
                """
                def test_something():
                    user_id = "user:alice"  # Hardcoded violation
                    assert user_id
                """
            )
        )

        # Run library function
        lib_violations = test_ids.find_hardcoded_ids(test_file)

        # Run script
        script_path = project_root / "scripts" / "validators" / "validate_test_ids.py"
        result = subprocess.run([sys.executable, str(script_path), str(test_file)], capture_output=True, text=True, timeout=30)

        # Both should detect violations
        assert len(lib_violations) > 0, "Library should detect violations"
        assert result.returncode == 1, "Script should return exit code 1"
        assert "user:alice" in result.stderr

    def test_test_ids_script_matches_library_on_valid(self, tmp_path: Path, project_root: Path) -> None:
        """Test that test IDs script and library agree on valid files."""
        test_file = tmp_path / "test_good.py"
        test_file.write_text(
            dedent(
                """
                from tests.conftest import get_user_id

                def test_something():
                    user_id = get_user_id()  # Worker-safe
                    assert user_id
                """
            )
        )

        # Run library function
        lib_violations = test_ids.find_hardcoded_ids(test_file)

        # Run script
        script_path = project_root / "scripts" / "validators" / "validate_test_ids.py"
        result = subprocess.run([sys.executable, str(script_path), str(test_file)], capture_output=True, text=True, timeout=30)

        # Both should pass
        assert len(lib_violations) == 0, "Library should find no violations"
        assert result.returncode == 0, "Script should return exit code 0"

    # AsyncMock Configuration Validator

    def test_async_mock_config_script_matches_library_on_violation(self, tmp_path: Path, project_root: Path) -> None:
        """Test that AsyncMock config script and library produce identical results for violations."""
        test_file = tmp_path / "test_bad.py"
        test_file.write_text(
            dedent(
                """
                from unittest.mock import AsyncMock

                def test_something():
                    mock = AsyncMock()  # Unconfigured violation
                    assert mock
                """
            )
        )

        # Run library function
        lib_issues = async_mocks.check_async_mock_configuration(str(test_file))

        # Run script
        script_path = project_root / "scripts" / "validators" / "check_async_mock_configuration.py"
        result = subprocess.run([sys.executable, str(script_path), str(test_file)], capture_output=True, text=True, timeout=30)

        # Both should detect issues
        assert len(lib_issues) > 0, "Library should detect issues"
        assert result.returncode == 1, "Script should return exit code 1"
        assert "not configured" in result.stderr or "AsyncMock" in result.stderr

    def test_async_mock_config_script_matches_library_on_valid(self, tmp_path: Path, project_root: Path) -> None:
        """Test that AsyncMock config script and library agree on valid files."""
        test_file = tmp_path / "test_good.py"
        test_file.write_text(
            dedent(
                """
                from unittest.mock import AsyncMock

                def test_something():
                    mock = AsyncMock(return_value="value")  # Configured
                    assert mock
                """
            )
        )

        # Run library function
        lib_issues = async_mocks.check_async_mock_configuration(str(test_file))

        # Run script
        script_path = project_root / "scripts" / "validators" / "check_async_mock_configuration.py"
        result = subprocess.run([sys.executable, str(script_path), str(test_file)], capture_output=True, text=True, timeout=30)

        # Both should pass
        assert len(lib_issues) == 0, "Library should find no issues"
        assert result.returncode == 0, "Script should return exit code 0"

    # AsyncMock Usage Validator

    def test_async_mock_usage_script_matches_library_on_violation(self, tmp_path: Path, project_root: Path) -> None:
        """Test that AsyncMock usage script and library produce identical results for violations."""
        test_file = tmp_path / "test_bad.py"
        test_file.write_text(
            dedent(
                """
                from unittest.mock import patch

                def test_something():
                    with patch.object(obj, "async_method"):  # Missing AsyncMock
                        pass
                """
            )
        )

        # Run library function
        lib_issues = async_mocks.check_async_mock_usage(str(test_file))

        # Run script
        script_path = project_root / "scripts" / "validators" / "check_async_mock_usage.py"
        result = subprocess.run([sys.executable, str(script_path), str(test_file)], capture_output=True, text=True, timeout=30)

        # Both should detect issues
        assert len(lib_issues) > 0, "Library should detect issues"
        assert result.returncode == 1, "Script should return exit code 1"
        assert "async" in result.stdout.lower() or "AsyncMock" in result.stdout

    def test_async_mock_usage_script_matches_library_on_valid(self, tmp_path: Path, project_root: Path) -> None:
        """Test that AsyncMock usage script and library agree on valid files."""
        test_file = tmp_path / "test_good.py"
        test_file.write_text(
            dedent(
                """
                from unittest.mock import patch, AsyncMock

                def test_something():
                    with patch.object(obj, "async_method", new_callable=AsyncMock):
                        pass
                """
            )
        )

        # Run library function
        lib_issues = async_mocks.check_async_mock_usage(str(test_file))

        # Run script
        script_path = project_root / "scripts" / "validators" / "check_async_mock_usage.py"
        result = subprocess.run([sys.executable, str(script_path), str(test_file)], capture_output=True, text=True, timeout=30)

        # Both should pass
        assert len(lib_issues) == 0, "Library should find no issues"
        assert result.returncode == 0, "Script should return exit code 0"


@pytest.mark.meta
@pytest.mark.meta
@pytest.mark.xdist_group(name="validator_consistency")
class TestValidationLibraryVersion:
    """Test that validation library has proper versioning."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_validation_lib_has_version(self) -> None:
        """Test that validation_lib package has __version__."""
        from tests.validation_lib import __version__

        assert __version__ is not None
        assert isinstance(__version__, str)
        assert len(__version__) > 0

    def test_validation_lib_version_is_semantic(self) -> None:
        """Test that validation_lib version follows semantic versioning."""
        from tests.validation_lib import __version__

        # Should be in format: MAJOR.MINOR.PATCH
        parts = __version__.split(".")
        assert len(parts) == 3, f"Version should have 3 parts, got: {__version__}"

        for part in parts:
            assert part.isdigit(), f"Version part should be numeric, got: {part}"


@pytest.mark.meta
@pytest.mark.meta
@pytest.mark.xdist_group(name="validator_consistency")
class TestValidationLibraryExports:
    """Test that validation library properly exports modules."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_can_import_memory_safety(self) -> None:
        """Test that memory_safety can be imported from validation_lib."""
        from tests.validation_lib import memory_safety

        assert memory_safety is not None
        assert hasattr(memory_safety, "check_file")
        assert hasattr(memory_safety, "find_test_files")
        assert hasattr(memory_safety, "print_violations")

    def test_can_import_test_ids(self) -> None:
        """Test that test_ids can be imported from validation_lib."""
        from scripts.validators import validate_ids as test_ids

        assert test_ids is not None
        assert hasattr(test_ids, "find_hardcoded_ids")
        assert hasattr(test_ids, "validate_test_file")
        assert hasattr(test_ids, "is_file_exempt")

    def test_can_import_async_mocks(self) -> None:
        """Test that async_mocks can be imported from validation_lib."""
        from tests.validation_lib import async_mocks

        assert async_mocks is not None
        assert hasattr(async_mocks, "check_async_mock_configuration")
        assert hasattr(async_mocks, "check_async_mock_usage")


@pytest.mark.meta
@pytest.mark.xdist_group(name="validator_consistency")
class TestValidatorLocation:
    """Test that validators are in the canonical location."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.fixture
    def project_root(self) -> Path:
        """Get the project root directory."""
        return Path(__file__).parent.parent.parent

    def test_all_validators_in_canonical_location(self, project_root: Path) -> None:
        """Ensure no validators exist outside scripts/validators/.

        All check_*.py and validate_*.py scripts should be in the canonical
        location scripts/validators/ for discoverability and consistent
        invocation patterns.

        Reference: Codex Audit - Validator location fragmentation
        """
        legacy_locations = [
            project_root / ".githooks",
        ]
        for loc in legacy_locations:
            if loc.exists():
                py_files = list(loc.glob("*.py"))
                # Allow __init__.py and helper modules, but no validators
                validators = [
                    f for f in py_files if f.stem.startswith(("check_", "validate_")) or "validation" in f.stem.lower()
                ]
                assert not validators, (
                    f"Found validators in legacy location {loc}: {[f.name for f in validators]}. "
                    "Move to scripts/validators/ for consistency."
                )

    def test_pre_commit_hooks_location_allowed(self, project_root: Path) -> None:
        """Allow check_*.py in .pre-commit-hooks/ as they are pre-commit entry points.

        The .pre-commit-hooks/ directory is allowed to contain check_*.py scripts
        because they serve as entry points for external pre-commit consumers.
        """
        pre_commit_hooks = project_root / ".pre-commit-hooks"
        if pre_commit_hooks.exists():
            py_files = list(pre_commit_hooks.glob("*.py"))
            # These are intentionally here for external consumption
            allowed_scripts = [
                "check_subprocess_timeout.py",
                "check_banned_imports.py",
            ]
            for f in py_files:
                if f.stem.startswith("check_"):
                    assert f.name in allowed_scripts, (
                        f"Unexpected check script in .pre-commit-hooks/: {f.name}. "
                        "Add to allowed_scripts if intentional, or move to scripts/validators/."
                    )
