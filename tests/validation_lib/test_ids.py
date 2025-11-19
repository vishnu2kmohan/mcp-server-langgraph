"""
Test ID Pollution Prevention Validation.

This module provides validation to ensure integration test files use worker-safe ID
helpers instead of hardcoded IDs to prevent pytest-xdist state pollution.

CRITICAL: Hardcoded IDs like "user:alice" or "apikey_test123" in integration tests
cause state pollution in pytest-xdist parallel execution, leading to flaky tests
and intermittent failures when multiple workers access shared databases.

Scope:
- ✅ VALIDATES: Integration tests that interact with real databases/services
- ⏭️  SKIPS: Unit tests with InMemory backends (no pollution risk - separate memory space per worker)
- ⏭️  SKIPS: Mock configurations in unit tests (isolated from external state)
- ⏭️  SKIPS: Assertion validations of response formats

Why unit tests with InMemory backends are safe:
- InMemory stores use Python dictionaries (no shared database)
- Each pytest-xdist worker has separate memory space
- No state pollution possible between workers
- Hardcoded IDs are fine for testing data model validation logic

Worker-safe helper usage (for integration tests):
    from tests.conftest import get_user_id, get_api_key_id

    @pytest.mark.integration
    def test_something(db_session):
        user_id = get_user_id()  # ✅ Worker-safe
        apikey_id = get_api_key_id()  # ✅ Worker-safe

Version: 1.0.0
See: tests/conftest.py for worker-safe ID helper implementations
See: adr/adr-0058-pytest-xdist-state-pollution-prevention.md for architecture decision
"""

import re
import sys
from pathlib import Path
from typing import List, Tuple

# Patterns that indicate hardcoded IDs (violations)
HARDCODED_ID_PATTERNS = [
    # User IDs in OpenFGA format
    (r'"user:[a-zA-Z0-9_-]+"', "Hardcoded user ID in quotes"),
    (r"'user:[a-zA-Z0-9_-]+'", "Hardcoded user ID in quotes"),
    # API key IDs
    (r'"apikey_[a-zA-Z0-9_-]+"', "Hardcoded API key ID in quotes"),
    (r"'apikey_[a-zA-Z0-9_-]+'", "Hardcoded API key ID in quotes"),
]

# Patterns that indicate legitimate usage (allowed)
LEGITIMATE_PATTERNS = [
    # OpenFGA format assertions with explicit comment
    r'assert.*"user:[a-zA-Z0-9_-]+".*#.*OpenFGA format',
    r"assert.*'user:[a-zA-Z0-9_-]+'.*#.*OpenFGA format",
    # OpenFGA format documentation comments (even without assert on same line)
    r'#.*OpenFGA format.*"user:[a-zA-Z0-9_-]+"',
    r"#.*OpenFGA format.*'user:[a-zA-Z0-9_-]+'",
    r'"user:[a-zA-Z0-9_-]+".*#.*OpenFGA format',
    r"'user:[a-zA-Z0-9_-]+'.*#.*OpenFGA format",
    # Docstring examples
    r'""".*user:[a-zA-Z0-9_-]+.*"""',
    r"'''.*user:[a-zA-Z0-9_-]+.*'''",
    # Comments (documentation)
    r"#.*user:[a-zA-Z0-9_-]+",
    r"#.*apikey_[a-zA-Z0-9_-]+",
    # Mock/AsyncMock configurations (unit test isolation)
    r'Mock\(.*["\']user:[a-zA-Z0-9_-]+',
    r'AsyncMock\(.*["\']user:[a-zA-Z0-9_-]+',
    r'Mock\(.*["\']apikey_[a-zA-Z0-9_-]+',
    r'AsyncMock\(.*["\']apikey_[a-zA-Z0-9_-]+',
    r'return_value\s*=.*["\']user:[a-zA-Z0-9_-]+',
    r'return_value\s*=.*["\']apikey_[a-zA-Z0-9_-]+',
    r'\.return_value\s*=.*["\']user:[a-zA-Z0-9_-]+',
    r'\.return_value\s*=.*["\']apikey_[a-zA-Z0-9_-]+',
    # Assertion right-hand side (validating response format, not creating records)
    r'assert\s+\w+\s*==\s*["\']user:[a-zA-Z0-9_-]+["\']',
    r'assert\s+\w+\s*==\s*["\']apikey_[a-zA-Z0-9_-]+["\']',
    r'assert\s+.*\[.*\]\s*==\s*["\']user:[a-zA-Z0-9_-]+["\']',
    r'assert\s+.*\[.*\]\s*==\s*["\']apikey_[a-zA-Z0-9_-]+["\']',
]

# Files that are allowed to have hardcoded IDs (special cases)
EXEMPT_FILES = [
    "conftest.py",  # Has docstrings and sample fixtures with example IDs
    "worker_safe_ids.py",  # Utility module with docstrings showing anti-patterns and solutions
    "test_id_pollution_prevention.py",  # Meta-test that tests this validation script
    "test_openfga_client.py",  # Unit tests for OpenFGA client library interface (uses mocked data)
    "api_fixtures.py",  # Shared fixtures with docstrings showing example ID patterns
    # Regression tests (documentation/pattern examples - not production tests)
    "test_pytest_xdist_isolation.py",  # Documents FastAPI dependency override patterns
    "test_bearer_scheme_isolation.py",  # Documents bearer_scheme singleton isolation patterns
    "test_fastapi_auth_override_sanity.py",  # Documents TDD backstop pattern for auth overrides
]


def is_file_exempt(file_path: Path) -> bool:
    """
    Check if file is exempt from validation (special cases like conftest.py, meta-tests).

    Args:
        file_path: Path to file to check

    Returns:
        True if file is exempt, False otherwise
    """
    return any(exempt in str(file_path) for exempt in EXEMPT_FILES)


def is_unit_test_with_inmemory(file_path: Path) -> bool:
    """
    Check if file is a unit test that uses InMemory backends.

    Unit tests with InMemory backends (dictionaries) cannot cause pytest-xdist pollution
    because each worker has separate memory space. Therefore, hardcoded IDs are safe
    in these tests - they're testing data model validation logic, not database operations.

    Args:
        file_path: Path to test file to check

    Returns:
        True if file is a unit test with InMemory backend, False otherwise
    """
    try:
        content = file_path.read_text(encoding="utf-8")

        # Check for unit test markers
        has_unit_marker = "@pytest.mark.unit" in content or "pytest.mark.unit" in content

        # Check for InMemory backend usage
        inmemory_patterns = [
            "InMemoryUserProfileStore",
            "InMemoryAuthStore",
            "InMemoryAPIKeyStore",
            "InMemoryCheckpointSaver",
            "InMemory",  # Generic InMemory pattern
            "HIPAAControls",  # Uses in-memory dict for emergency grants
            "MemorySaver",  # LangGraph in-memory checkpointer
            "TestClient",  # FastAPI in-memory test client (no real server)
            "AsyncMock",  # Unit tests with mocked external dependencies
            "from unittest.mock import",  # Unit tests using mocks
        ]
        uses_inmemory = any(pattern in content for pattern in inmemory_patterns)

        # If it's marked as unit test AND uses InMemory backends, it's safe
        return has_unit_marker and uses_inmemory

    except Exception:
        return False


def is_legitimate_usage(line: str) -> bool:
    """
    Check if line contains legitimate ID usage (e.g., docstrings, comments, assertions).

    Legitimate uses include:
    - Docstring examples explaining ID formats
    - Comments documenting expected formats
    - Assertions checking OpenFGA format (with # OpenFGA format comment)
    - Mock/AsyncMock return_value configurations

    Args:
        line: Line of code to check

    Returns:
        True if usage is legitimate (allowed), False otherwise
    """
    for pattern in LEGITIMATE_PATTERNS:
        if re.search(pattern, line):
            return True
    return False


def find_hardcoded_ids(file_path: Path) -> List[Tuple[int, str, str]]:
    """
    Find hardcoded ID patterns in a test file.

    Args:
        file_path: Path to test file to validate

    Returns:
        List of violations: [(line_number, line_content, violation_description), ...]
    """
    violations = []

    try:
        content = file_path.read_text(encoding="utf-8")
        lines = content.splitlines()

        for line_num, line in enumerate(lines, start=1):
            # Skip legitimate usage (docstrings, comments, documented assertions)
            if is_legitimate_usage(line):
                continue

            # Check for hardcoded ID patterns
            for pattern, description in HARDCODED_ID_PATTERNS:
                if re.search(pattern, line):
                    violations.append((line_num, line.strip(), description))

    except Exception as e:
        print(f"❌ Error reading {file_path}: {e}", file=sys.stderr)
        sys.exit(1)

    return violations


def check_worker_safe_usage(file_path: Path) -> bool:
    """
    Check if file uses worker-safe ID helpers.

    This is informational only - not required if file doesn't use IDs at all.

    Args:
        file_path: Path to test file

    Returns:
        True if file uses worker-safe helpers, False otherwise
    """
    try:
        content = file_path.read_text(encoding="utf-8")

        worker_safe_patterns = [
            r"from tests\.conftest import.*get_user_id",
            r"from tests\.conftest import.*get_api_key_id",
            r"get_user_id\(\)",
            r"get_api_key_id\(\)",
        ]

        for pattern in worker_safe_patterns:
            if re.search(pattern, content):
                return True

    except Exception:
        pass

    return False


def validate_test_file(file_path: Path) -> bool:
    """
    Validate a single test file for hardcoded IDs.

    Args:
        file_path: Path to test file to validate

    Returns:
        True if validation passes (no hardcoded IDs), False otherwise
    """
    # Skip exempt files (conftest.py, meta-tests)
    if is_file_exempt(file_path):
        return True

    # Skip unit tests with InMemory backends (no database pollution possible)
    if is_unit_test_with_inmemory(file_path):
        return True

    violations = find_hardcoded_ids(file_path)

    if violations:
        return False

    # Validation passed
    return True
