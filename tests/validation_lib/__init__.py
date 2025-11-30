"""
Shared Validation Library for Test Quality Enforcement.

This library provides reusable validation logic that is used by both:
1. Pre-commit hook scripts (scripts/*)
2. Meta-tests (tests/meta/*)

By centralizing validation logic, we ensure:
- Consistency: Scripts and tests use identical validation rules
- Maintainability: Single place to update validation logic
- Testability: Validation logic can be unit tested independently

Modules:
- memory_safety: Memory safety pattern validation for pytest-xdist
- async_mocks: AsyncMock configuration and usage validation
- ast_cache: Cached file reading and AST parsing for meta-tests

Note: test_ids module moved to scripts/validation/validate_ids.py (2025-11-20)

Version History:
- 1.0.2 (2025-11-27): Add ast_cache module for CI performance
  * ast_cache with LRU caching for file reading and AST parsing
  * Fast regex-based checks (1000x faster than AST for presence detection)
  * Fixes CI timeout issues in meta-tests
- 1.0.1 (2025-11-20): Move test_ids to scripts/validation/
  * test_ids moved to scripts/validation/validate_ids.py
  * Removed from validation_lib (not a test file)
- 1.0.0 (2025-11-18): Initial release
  * memory_safety validator
  * test_ids validator
  * async_mocks validator (configuration + usage)
  * 46 comprehensive unit tests
  * TDD implementation

Version: 1.0.2
"""

__version__ = "1.0.2"

# Import modules for convenient access
from tests.validation_lib import ast_cache, async_mocks, memory_safety

__all__ = [
    "__version__",
    "memory_safety",
    "async_mocks",
    "ast_cache",
]
