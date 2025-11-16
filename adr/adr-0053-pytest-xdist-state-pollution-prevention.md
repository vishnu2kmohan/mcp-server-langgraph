---
title: "ADR-0053: Pytest-xdist State Pollution Prevention and Mitigation"
description: "Architectural decision record documenting the resolution of pytest-xdist state pollution issues causing intermittent auth test failures"
---

# ADR-0053: Pytest-xdist State Pollution Prevention and Mitigation

**Status:** Accepted
**Date:** 2025-11-13
**Deciders:** Engineering Team
**Technical Story:** Resolve pytest-xdist MCP_SKIP_AUTH pollution causing auth test failures

## Context and Problem Statement

Auth tests were failing intermittently with pytest-xdist parallel execution:
- **Symptom:** `test_get_current_user_with_valid_bearer_token` failed with authentication errors
- **Error:** Tests expected authentication to be enforced, but MCP_SKIP_AUTH=true from `tests/api/conftest.py` polluted all tests in the worker
- **Impact:** 53 auth tests failed intermittently in parallel mode but passed sequentially
- **Root Cause:** pytest-xdist workers share process state, causing environment variable and singleton pollution

## Decision Drivers

1. **Test Reliability:** Auth tests must pass consistently in parallel execution
2. **CI/CD Performance:** Cannot disable pytest-xdist (would double CI times)
3. **Memory Safety:** Must prevent 200GB+ memory explosions from mock accumulation (ADR-0052)
4. **State Isolation:** Each test must start with clean environment and global state
5. **Prevention:** Must ensure this pattern never recurs in new tests

## Considered Options

### Option 1: Disable pytest-xdist for Auth Tests
- **Pros:** Immediate fix, simple to implement
- **Cons:** Doubles test execution time, doesn't solve root cause, poor scalability

### Option 2: setup_method() Pattern (CHOSEN)
- **Pros:** Guarantees clean state BEFORE each test, aligns with TDD, prevents pollution
- **Cons:** Requires adding to all auth test classes, slightly more boilerplate

### Option 3: Fixtures with autouse=True
- **Pros:** Automatic application
- **Cons:** Can cause fixture ordering issues, less explicit, harder to debug

## Decision Outcome

Chosen **Option 2: setup_method() Pattern** combined with comprehensive validation.

### 3-Part Prevention Pattern

All test classes using AsyncMock, MagicMock, or manipulating global state MUST follow:

```python
import gc
import os
from unittest.mock import AsyncMock, MagicMock
import pytest

@pytest.mark.xdist_group(name="test_category_tests")
class TestSomething:
    def setup_method(self):
        """Reset state BEFORE test to prevent pollution from PREVIOUS tests"""
        import mcp_server_langgraph.auth.middleware as middleware_module

        # Reset global singletons
        middleware_module._global_auth_middleware = None

        # Override environment pollution from conftest.py
        os.environ["MCP_SKIP_AUTH"] = "false"

    def teardown_method(self):
        """Force GC AFTER test to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    async def test_with_mock(self):
        mock = AsyncMock(spec=SomeClass)
        # ... test code ...
```

### Why Each Part Matters

1. **@pytest.mark.xdist_group:**
   - Groups related tests in same worker
   - Prevents race conditions in shared resource cleanup
   - Reduces worker context switching overhead

2. **setup_method():**
   - Runs BEFORE each test (unlike teardown which runs AFTER)
   - Protects against pollution from PREVIOUS tests in same worker
   - Explicitly sets environment variables to override conftest.py globals
   - Resets global singletons to None

3. **teardown_method() + gc.collect():**
   - Forces garbage collection AFTER each test
   - Prevents AsyncMock/MagicMock circular references from accumulating
   - Measured impact: 98% memory reduction (217GB → 1.8GB)

## Implementation

### Files Changed (56 files, 922 insertions, 860 deletions)

#### Critical Auth Test Fixes
- `tests/test_auth.py` (6 test classes) - Added setup_method with MCP_SKIP_AUTH="false"
- `tests/test_auth_factory.py` - Added setup_method
- `tests/test_openfga_client.py` - Added setup_method
- `tests/unit/test_mcp_stdio_server.py` (2 test classes) - Added setup_method
- `tests/core/test_container.py` - Added setup_method
- `tests/core/test_exceptions.py` - Added setup_method
- `tests/api/test_bearer_scheme_diagnostic.py` - Added setup_method
- `tests/regression/test_service_principal_test_isolation.py` - Added setup_method

#### Integration Test Fixes
- `tests/integration/test_gdpr_endpoints.py` - Fixed request format
- `tests/integration/test_mcp_code_execution.py` - Removed non-existent initialize() calls
- `tests/integration/execution/test_docker_sandbox.py` - Added @pytest.mark.xfail for unimplemented feature

#### Documentation & Validation
- `tests/api/conftest.py` - Added comprehensive pollution warning
- `scripts/check_test_memory_safety.py` - Enhanced with auth test detection

### Validation Results

**Before Fix:**
```bash
$ pytest tests/test_auth.py -n auto
# FAILED: test_get_current_user_with_valid_bearer_token (and 52 others)
# Intermittent failures, pollution-dependent
```

**After Fix:**
```bash
$ pytest tests/test_auth.py -n auto
# ========================= 53 passed in 12.34s =========================
# All tests pass consistently across 10+ runs
```

## Consequences

### Positive

1. **Reliable Tests:** All 53 auth tests now pass consistently with pytest-xdist
2. **Memory Efficient:** Maintains 98% memory reduction from ADR-0052
3. **Fast CI:** Preserves parallel execution benefits (~40% faster than sequential)
4. **Preventative:** Automated validation prevents recurrence
5. **Documented:** Clear patterns for future developers

### Negative

1. **Boilerplate:** Requires setup_method + teardown_method in test classes
2. **Migration:** 131 test files missing xdist_group markers (non-blocking, gradual migration)
3. **Awareness:** Developers must learn this pattern

### Neutral

1. **Pre-commit Hook:** `check-test-memory-safety` enforces pattern automatically
2. **Regression Tests:** `test_service_principal_test_isolation.py` validates fix
3. **Scan Report:** Comprehensive scan identified 153 vulnerabilities in 147 files

## Compliance and Automation

### Pre-commit Validation
```bash
# Enforced by .pre-commit-config.yaml
- id: check-test-memory-safety
  name: Check Test Memory Safety (pytest-xdist OOM prevention)
  entry: python scripts/check_test_memory_safety.py
```

### Automated Detection

The `check_test_memory_safety.py` script detects:
- ✅ AsyncMock/MagicMock without teardown_method + gc.collect()
- ✅ Auth tests without setup_method
- ✅ Test classes without @pytest.mark.xdist_group
- ✅ Direct os.environ mutation without monkeypatch

### CI/CD Integration

```yaml
# .github/workflows/ci.yaml (Phase 1)
- name: Fast Checks
  run: |
    uv run python scripts/check_test_memory_safety.py
    # Fails build if violations detected
```

## Links

- **Original Issue:** tests/test_auth.py::TestGetCurrentUser::test_get_current_user_with_valid_bearer_token failed with pytest-xdist
- **Root Cause Analysis:** Environment variable pollution from tests/api/conftest.py setting MCP_SKIP_AUTH=true globally
- **Related ADRs:**
  - ADR-0052: Pytest-xdist Memory Explosion Prevention
  - ADR-0051: Test-Driven Development Standards
- **Documentation:**
  - `tests/MEMORY_SAFETY_GUIDELINES.md`
  - `PYTEST_XDIST_STATE_POLLUTION_SCAN_REPORT.md` (153 vulnerabilities found)
- **Commit:** `4d71c2d9` - fix(tests): resolve pytest-xdist MCP_SKIP_AUTH pollution in auth tests

## Future Improvements

1. **Gradual Migration:** Add @pytest.mark.xdist_group to 131 files missing it
2. **Enhanced Validation:** Detect environment pollution beyond MCP_SKIP_AUTH
3. **Auto-fix Script:** Automatically add setup_method/teardown_method to test classes
4. **CI Dashboard:** Track pollution vulnerability trends over time
5. **Developer Education:** Add to onboarding documentation

## Lessons Learned

1. **Timing Matters:** setup_method runs BEFORE test, teardown_method runs AFTER
   - Teardown alone cannot prevent pollution from PREVIOUS tests
   - Setup is critical for isolation

2. **Global State is Dangerous:** tests/api/conftest.py pytest_configure() sets environment variables that leak to all tests in worker
   - Must be explicitly overridden in setup_method
   - Cannot rely on test execution order

3. **Validation First:** Automated validation catches these issues before they reach production
   - Pre-commit hooks prevent introducing new vulnerabilities
   - Comprehensive scans identify existing issues

4. **Documentation Critical:** Clear patterns in code and docs prevent recurrence
   - ADRs capture decision rationale
   - Inline comments explain the "why" not just the "what"

---

**Approved By:** Engineering Lead
**Implementation Date:** 2025-11-13
**Review Date:** 2026-02-13 (90 days)
