"""
Test path helper utilities.

**Purpose:**
Provides safe, validated path helpers for referencing test files across
the test suite. Prevents file reference regressions when files are moved
or reorganized.

**OpenAI Codex Finding (2025-11-16):**
- Regression tests hard-coded paths to `tests/api/test_*.py`
- Files migrated to `tests/integration/api/` but path references not updated
- Caused FileNotFoundError and broken regression validation tests

**Solution:**
- Centralized helper function with existence validation
- Prevents directory traversal attacks
- Clear error messages for debugging
- Single source of truth for integration test paths
"""

from pathlib import Path
from typing import Union


def get_integration_test_file(relative_path: str | Path) -> Path:
    """
    Get absolute path to an integration test file with existence validation.

    **Args:**
        relative_path: Path relative to tests/integration/
            Examples: "api/test_api_keys_endpoints.py",
                     "api/test_service_principals_endpoints.py"

    **Returns:**
        Absolute Path object pointing to the integration test file

    **Raises:**
        FileNotFoundError: If the referenced file doesn't exist
        ValueError: If the path contains directory traversal attempts (..)

    **Security:**
        - Validates file exists (prevents silent failures)
        - Rejects directory traversal attempts (prevents sandbox escape)
        - Always returns absolute paths (prevents ambiguity)

    **Usage:**
        ```python
        # In regression tests:
        from tests.helpers import get_integration_test_file

        test_file = get_integration_test_file("api/test_api_keys_endpoints.py")
        assert test_file.exists()
        content = test_file.read_text()
        ```

    **Migration Guide:**
        ❌ OLD (hard-coded path):
        ```python
        test_file = Path(__file__).parent.parent / "api" / "test_api_keys_endpoints.py"
        assert test_file.exists()
        ```

        ✅ NEW (using helper):
        ```python
        from tests.helpers import get_integration_test_file

        test_file = get_integration_test_file("api/test_api_keys_endpoints.py")
        ```

    **Regression Prevention:**
        - Centralizes path logic (single place to update during migrations)
        - Existence validation catches broken references early
        - Meta-test validates all usages in regression tests
    """
    # Normalize input to string
    if isinstance(relative_path, Path):
        relative_path = str(relative_path)

    # Security: Prevent directory traversal attacks
    if ".." in relative_path:
        raise ValueError(
            f"Path contains directory traversal sequence (..), which is not allowed: {relative_path}\n"
            f"This helper is scoped to tests/integration/ only.\n"
            f"Attempted path: {relative_path}"
        )

    # Construct absolute path to integration test file
    # Base: tests/integration/ (where this helper lives in tests/helpers/)
    base_dir = Path(__file__).parent.parent / "integration"
    full_path = (base_dir / relative_path).resolve()

    # Validate: Path must exist (fail-fast on broken references)
    if not full_path.exists():
        raise FileNotFoundError(
            f"Integration test file not found: {relative_path}\n"
            f"Expected location: {full_path}\n"
            f"Integration test base: {base_dir}\n"
            f"\n"
            f"If the file was moved, update the relative_path argument.\n"
            f"If the file was deleted, update the test that references it."
        )

    # Validate: Must be a file, not a directory
    if not full_path.is_file():
        raise ValueError(f"Path exists but is not a file: {full_path}\nThis helper expects file paths, not directories.")

    # Security: Double-check the resolved path is still within integration/
    # (prevents symlink attacks that escape the sandbox)
    if not full_path.is_relative_to(base_dir):
        raise ValueError(
            f"Resolved path escapes integration test directory (possible symlink attack)\n"
            f"Requested: {relative_path}\n"
            f"Resolved: {full_path}\n"
            f"Expected base: {base_dir}"
        )

    return full_path
