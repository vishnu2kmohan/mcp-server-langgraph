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
- fixtures: Fixture organization and configuration validation

Version: 1.0.0
"""

__version__ = "1.0.0"

__all__ = [
    "memory_safety",
    "test_ids",
    "async_mocks",
    "fixtures",
]
