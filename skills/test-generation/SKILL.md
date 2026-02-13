---
name: test-generation
description: Generate comprehensive test suites using TDD principles. Use when creating test scaffolding, test stubs, or full test implementations.
allowed-tools:
- Read
- Glob
- Grep
- Write
compatibility: Requires pytest>=8.0.0. No network access needed.
metadata:
  version: 1.0.0
  category: devops
  author: Emergence AI
  dependencies:
  - pytest>=8.0.0
  sandbox_config:
    network: none
    filesystem: readonly
---
# Test Generation Skill

Generate comprehensive test suites following Test-Driven Development (TDD) principles.

## Capabilities

- **Unit Test Generation**: Create isolated unit tests
- **Integration Tests**: Generate integration test cases
- **Edge Case Coverage**: Identify and test edge cases
- **Mock Generation**: Create appropriate mocks and fixtures

## Usage Examples

- "Generate unit tests for this function"
- "Create integration tests for this API endpoint"
- "Write edge case tests for this validator"

## Guidelines

1. Follow TDD principles (Red-Green-Refactor)
2. Aim for high code coverage
3. Test one behavior per test
4. Use descriptive test names

## Output Format

```python
# Tests for: [module/function]

import pytest

class TestFunctionName:
    """Tests for function_name."""

    def test_basic_case(self):
        """Test basic functionality."""
        # Arrange
        # Act
        # Assert

    def test_edge_case(self):
        """Test edge case behavior."""
        # ...
```
