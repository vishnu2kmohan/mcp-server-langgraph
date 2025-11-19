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
- test_ids: Test ID pollution prevention validation
- async_mocks: AsyncMock configuration and usage validation

Version History:
- 1.0.0 (2025-11-18): Initial release
  * memory_safety validator
  * test_ids validator
  * async_mocks validator (configuration + usage)
  * 46 comprehensive unit tests
  * TDD implementation

Version: 1.0.0
"""

__version__ = "1.0.0"

# Import modules for convenient access
from tests.validation_lib import async_mocks, memory_safety, test_ids

__all__ = [
    "__version__",
    "memory_safety",
    "test_ids",
    "async_mocks",
]
