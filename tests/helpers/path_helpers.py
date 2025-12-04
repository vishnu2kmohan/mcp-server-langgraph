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

**REPO_ROOT Pattern Standardization (2025-12-04):**
- Added get_repo_root() to eliminate fragile Path(__file__).parent chains
- Detects repo root by looking for marker files (.git, pyproject.toml)
- Works regardless of how deep the calling file is in the directory tree
- Prevents breakage when test files are moved between directories
"""

from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def get_repo_root() -> Path:
    """
    Get the repository root directory reliably regardless of call site location.

    This function finds the repository root by searching upward for marker files
    (.git directory or pyproject.toml). This eliminates the fragile pattern of
    chaining .parent calls which breaks when files are moved.

    **Returns:**
        Path: Absolute path to the repository root

    **Raises:**
        RuntimeError: If repository root cannot be found

    **Why This Exists:**
        The pattern `Path(__file__).parent.parent.parent` is fragile:
        - It must be updated every time a file is moved to a different depth
        - CI failures occur silently when the path calculation is wrong
        - Each test file duplicates the calculation, causing maintenance burden

    **Usage:**
        ```python
        # ❌ OLD (fragile - breaks when file moves):
        REPO_ROOT = Path(__file__).parent.parent.parent

        # ✅ NEW (robust - works regardless of file location):
        from tests.helpers.path_helpers import get_repo_root
        REPO_ROOT = get_repo_root()
        ```

    **Marker Files Checked (in order):**
        1. .git directory - definitive repository marker
        2. pyproject.toml - project configuration file

    **Performance:**
        - Result is cached using @lru_cache
        - Subsequent calls return immediately without filesystem traversal
        - Safe to call from module level (will be evaluated once at import)

    **Security:**
        - Returns resolved (absolute) path
        - Cannot escape beyond filesystem root
    """
    # Start from this file's directory and walk upward
    current = Path(__file__).resolve().parent

    while current != current.parent:  # Stop at filesystem root
        # Check for repository markers
        if (current / ".git").is_dir():
            return current
        if (current / "pyproject.toml").is_file():
            return current
        current = current.parent

    # If we reach the filesystem root, raise an error
    raise RuntimeError(
        "Cannot find repository root. No .git directory or pyproject.toml found.\n"
        f"Started search from: {Path(__file__).resolve().parent}\n"
        "This should not happen in normal usage."
    )


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
    # Use get_repo_root() to avoid fragile .parent chain
    base_dir = get_repo_root() / "tests" / "integration"
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
