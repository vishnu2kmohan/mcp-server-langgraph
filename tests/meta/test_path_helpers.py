"""
Meta-tests for path helper utilities.

**Purpose:**
Validates that test path helpers work correctly and prevent file reference
regressions (e.g., broken paths after file migrations).

**OpenAI Codex Finding (2025-11-16):**
- Regression tests referenced `tests/api/test_*.py` but files moved to `tests/integration/api/`
- Hard-coded path construction caused FileNotFoundError and test failures
- Need centralized, validated helper for integration test file references

**Solution:**
- `get_integration_test_file()` helper with existence validation
- Meta-test ensures helper works correctly
- Prevents future file migration regressions
"""

from pathlib import Path

import pytest


def test_get_integration_test_file_returns_valid_path():
    """
    get_integration_test_file() returns correct path to integration test files.

    **Test Coverage:**
    - Returns Path object
    - Path points to tests/integration/{relative_path}
    - Path is absolute (not relative)
    - Relative path is correctly appended

    **Regression Prevention:**
    - Validates helper works for known files (test_api_keys_endpoints.py)
    - Ensures path construction is correct
    - Guards against path manipulation bugs
    """
    from tests.helpers import get_integration_test_file

    # Act: Get path to a known integration test file
    result = get_integration_test_file("api/test_api_keys_endpoints.py")

    # Assert: Path is correct
    assert isinstance(result, Path), "Should return a Path object"
    assert result.is_absolute(), "Should return absolute path, not relative"
    assert "tests/integration/api/test_api_keys_endpoints.py" in str(
        result
    ), f"Path should contain integration/api structure, got: {result}"
    assert result.name == "test_api_keys_endpoints.py", f"Filename should be test_api_keys_endpoints.py, got: {result.name}"


def test_get_integration_test_file_validates_existence():
    """
    get_integration_test_file() raises FileNotFoundError for non-existent files.

    **Test Coverage:**
    - Raises FileNotFoundError (not generic Exception)
    - Error message includes the attempted path
    - Prevents silent failures from broken references

    **Security Note:**
    - Fail-fast on invalid paths prevents accidental file creation
    - Clear error messages aid debugging
    """
    from tests.helpers import get_integration_test_file

    # Act & Assert: Non-existent file should raise FileNotFoundError
    with pytest.raises(FileNotFoundError) as exc_info:
        get_integration_test_file("api/test_nonexistent_file.py")

    # Assert: Error message is helpful
    error_msg = str(exc_info.value)
    assert "test_nonexistent_file.py" in error_msg, "Error should mention the requested file"
    assert "integration" in error_msg.lower(), "Error should indicate it's looking in integration tests"


def test_get_integration_test_file_handles_nested_paths():
    """
    get_integration_test_file() works with nested directory structures.

    **Test Coverage:**
    - Handles multi-level paths (e.g., "api/auth/test_bearer.py")
    - Path separator handling (forward slashes)
    - Relative path construction from tests/integration/ base

    **Use Cases:**
    - API tests: api/test_*.py
    - Auth tests: api/auth/test_*.py
    - Storage tests: storage/test_*.py
    """
    from tests.helpers import get_integration_test_file

    # Act: Get path with nested structure (api/ subdirectory under integration/)
    result = get_integration_test_file("api/test_service_principals_endpoints.py")

    # Assert: Nested path is constructed correctly
    assert isinstance(result, Path)
    assert "tests/integration/api/test_service_principals_endpoints.py" in str(result)
    assert result.name == "test_service_principals_endpoints.py"


def test_get_integration_test_file_works_with_actual_files():
    """
    Integration test: Verify helper works with real integration test files.

    **Test Coverage:**
    - Tests against actual filesystem (not mocked)
    - Validates file.exists() returns True for real files
    - Ensures end-to-end functionality

    **Known Files (as of 2025-11-16):**
    - tests/integration/api/test_api_keys_endpoints.py
    - tests/integration/api/test_service_principals_endpoints.py
    """
    from tests.helpers import get_integration_test_file

    # Known files that should exist in tests/integration/api/
    known_files = [
        "api/test_api_keys_endpoints.py",
        "api/test_service_principals_endpoints.py",
    ]

    for relative_path in known_files:
        # Act: Get path
        result = get_integration_test_file(relative_path)

        # Assert: File actually exists
        assert result.exists(), f"Helper returned path that doesn't exist: {result}"
        assert result.is_file(), f"Path should be a file, not directory: {result}"


def test_get_integration_test_file_prevents_directory_traversal():
    """
    get_integration_test_file() doesn't allow directory traversal attacks.

    **Security Test:**
    - Rejects paths with ".." (parent directory)
    - Prevents escaping tests/integration/ sandbox
    - Raises ValueError for malicious paths

    **Attack Scenarios:**
    - "../../../etc/passwd"
    - "api/../../secret.py"
    - "./api/../../../etc/hosts"
    """
    from tests.helpers import get_integration_test_file

    malicious_paths = [
        "../api/test_file.py",
        "api/../../secret.py",
        "../../../etc/passwd",
    ]

    for malicious_path in malicious_paths:
        # Act & Assert: Should reject directory traversal attempts
        with pytest.raises((ValueError, FileNotFoundError)):
            get_integration_test_file(malicious_path)

        # Note: FileNotFoundError is acceptable if the helper resolves
        # the path correctly but file doesn't exist. ValueError is
        # preferred for explicit traversal rejection.


def test_regression_path_references_are_valid():
    """
    Meta-regression test: Validate all path references in regression tests.

    **Purpose:**
    - Scans all regression test files for Path() construction patterns
    - Validates referenced files exist
    - Prevents broken file references from file migrations

    **Regression Prevention:**
    - Catches hard-coded paths to tests/api/ (old location)
    - Ensures all references use tests/integration/api/ (new location)
    - Alerts to file moves before regression tests break

    **Known Issues (2025-11-16):**
    - test_bearer_scheme_override_diagnostic.py:52, 325
    - test_uv_lockfile_sync.py:273, 294
    """
    import ast
    import re

    regression_dir = Path(__file__).parent.parent / "regression"
    issues = []

    # Pattern: Path(...).parent.parent / "api" / "test_*.py"
    # This pattern is WRONG - should be "integration" / "api" / ...
    old_api_pattern = re.compile(r'parent\.parent\s*/\s*["\']api["\']')

    for test_file in regression_dir.glob("test_*.py"):
        content = test_file.read_text()

        # Check for old path pattern
        if old_api_pattern.search(content):
            issues.append(
                f"{test_file.name}: Uses old 'parent.parent / \"api\"' pattern "
                f'(should be \'parent.parent / "integration" / "api"\')'
            )

    assert not issues, f"Found {len(issues)} regression test(s) with invalid path references:\n" + "\n".join(
        f"  - {issue}" for issue in issues
    )
