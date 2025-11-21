"""
Meta-test: Validate AsyncMock configuration across all test files.

This test ensures that all AsyncMock instances have explicit return_value
or side_effect configuration to prevent authorization bypass bugs and
pytest-xdist state pollution.

Run with: pytest tests/meta/test_async_mock_configuration.py -v
"""

import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.meta


@pytest.mark.meta
@pytest.mark.unit
def test_all_async_mocks_have_return_values():
    """
    Verify all AsyncMock instances have explicit configuration.

    This test runs the check_async_mock_configuration.py script to detect
    unconfigured AsyncMock instances across the test suite.

    SECURITY: Unconfigured AsyncMock returns truthy values, causing
    authorization checks to incorrectly pass. This was the root cause
    of the SCIM security bug (commit abb04a6a).

    See: tests/ASYNC_MOCK_GUIDELINES.md for details.
    """
    # Get all test files
    tests_dir = Path(__file__).parent.parent
    test_files = list(tests_dir.rglob("test_*.py"))

    # Skip meta tests themselves
    test_files = [f for f in test_files if "meta" not in f.parts]

    if not test_files:
        pytest.skip("No test files found to check")

    # Run the AsyncMock configuration checker
    script_path = Path(__file__).parent.parent.parent / "scripts" / "check_async_mock_configuration.py"

    result = subprocess.run(
        [sys.executable, str(script_path)] + [str(f) for f in test_files], capture_output=True, text=True, timeout=60
    )

    # Collect violations for detailed error message
    violations = []
    if result.returncode != 0:
        # Parse output for violations
        for line in result.stderr.split("\n"):
            if line.strip() and not line.startswith(("❌", "📖", "See:", "")):
                violations.append(line.strip())

    # Assert no violations
    if violations:
        error_msg = (
            f"\n{'=' * 80}\n"
            f"❌ SECURITY: Found {len(violations)} unconfigured AsyncMock instances\n"
            f"{'=' * 80}\n\n"
            f"Unconfigured AsyncMock returns truthy values, causing authorization\n"
            f"checks to incorrectly pass. This is a SECURITY BUG!\n\n"
            f"Violations:\n"
        )
        for violation in violations[:20]:  # Show first 20
            error_msg += f"  {violation}\n"

        if len(violations) > 20:
            error_msg += f"\n  ... and {len(violations) - 20} more\n"

        error_msg += (
            f"\n{'=' * 80}\n"
            f"FIX: Add explicit return_value or side_effect configuration:\n"
            f"{'=' * 80}\n\n"
            f"  # For authorization checks (deny):\n"
            f"  mock_openfga = AsyncMock()\n"
            f"  mock_openfga.check_permission.return_value = False\n\n"
            f"  # For void functions:\n"
            f"  mock.write_tuples.return_value = None\n\n"
            f"  # For exceptions:\n"
            f"  mock.method.side_effect = Exception('error')\n\n"
            f"See: tests/ASYNC_MOCK_GUIDELINES.md for complete guide\n"
            f"{'=' * 80}\n"
        )

        pytest.fail(error_msg, pytrace=False)


@pytest.mark.meta
@pytest.mark.unit
def test_async_mock_guidelines_exist():
    """Verify AsyncMock guidelines documentation exists."""
    guidelines_path = Path(__file__).parent.parent / "ASYNC_MOCK_GUIDELINES.md"
    assert guidelines_path.exists(), "AsyncMock guidelines documentation missing!\n" "Expected: tests/ASYNC_MOCK_GUIDELINES.md"


@pytest.mark.meta
@pytest.mark.unit
def test_async_mock_checker_script_exists():
    """Verify AsyncMock configuration checker script exists."""
    script_path = Path(__file__).parent.parent.parent / "scripts" / "check_async_mock_configuration.py"
    assert script_path.exists(), (
        "AsyncMock configuration checker script missing!\n" "Expected: scripts/check_async_mock_configuration.py"
    )
    assert script_path.stat().st_mode & 0o111, (
        "AsyncMock configuration checker script is not executable!\n" f"Run: chmod +x {script_path}"
    )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
