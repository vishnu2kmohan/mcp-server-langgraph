---
description: Execute the comprehensive test suite for the MCP Server LangGraph project.
---
# Run Complete Test Suite

Execute the comprehensive test suite for the MCP Server LangGraph project.

## Test Execution

Run all test types in sequence:

1. **Unit Tests** (fast, no external dependencies)
   ```bash
   make test-unit
   ```

2. **Integration Tests** (requires infrastructure)
   ```bash
   make test-integration
   ```

3. **Property-Based Tests** (Hypothesis edge case discovery)
   ```bash
   make test-property
   ```

4. **Contract Tests** (MCP protocol compliance)
   ```bash
   make test-contract
   ```

5. **Regression Tests** (performance monitoring)
   ```bash
   make test-regression
   ```

## Coverage Analysis

Generate and display comprehensive coverage report:
```bash
make test-coverage
```

## Summary

Provide a summary of:
- Total tests passed/failed
- Code coverage percentage
- Any test failures with file references
- Recommendations for next steps
