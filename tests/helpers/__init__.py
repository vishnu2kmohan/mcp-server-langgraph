"""
Test helper utilities and fixtures.

This package provides reusable test utilities, mock factories, and fixtures
to support consistent, safe, and maintainable test authoring.

Modules:
    async_mock_helpers: Safe AsyncMock factory functions (security-critical)
    path_helpers: Validated path helpers for integration test file references
                  and robust repository root detection

Usage:
    from tests.helpers.async_mock_helpers import (
        configured_async_mock,
        configured_async_mock_deny,
        configured_async_mock_raise,
    )
    from tests.helpers.path_helpers import get_integration_test_file, get_repo_root

    # PREFERRED for REPO_ROOT:
    from tests.helpers.path_helpers import get_repo_root
    REPO_ROOT = get_repo_root()  # Works regardless of file location
"""

# Re-export commonly used helpers for convenience
from tests.helpers.async_mock_helpers import configured_async_mock, configured_async_mock_deny, configured_async_mock_raise
from tests.helpers.path_helpers import get_integration_test_file, get_repo_root

__all__ = [
    "configured_async_mock",
    "configured_async_mock_deny",
    "configured_async_mock_raise",
    "get_integration_test_file",
    "get_repo_root",
]
