# Pytest-xdist State Pollution Prevention Guide

**Last Updated:** 2025-11-13
**Status:** Required for all new tests
**Enforcement:** Pre-commit hook + CI/CD validation

---

## Quick Reference: Required Pattern

**ALL test classes using AsyncMock, MagicMock, or manipulating global state MUST follow this pattern:**

```python
import gc
import os
from unittest.mock import AsyncMock, MagicMock
import pytest

@pytest.mark.xdist_group(name="your_test_category_tests")
class TestYourFeature:
    def setup_method(self):
        """Reset state BEFORE test to prevent pollution from previous tests."""
        import mcp_server_langgraph.auth.middleware as middleware_module

        # Reset global singletons
        middleware_module._global_auth_middleware = None

        # Override environment pollution (if manipulating env vars)
        os.environ["MCP_SKIP_AUTH"] = "false"

    def teardown_method(self):
        """Force GC AFTER test to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_your_feature(self):
        mock = AsyncMock(spec=YourClass)
        # ... test code ...
```

---

## Why This Matters

### Problem 1: Memory Explosion (ADR-0052)
**Without teardown_method + gc.collect():**
- AsyncMock/MagicMock creates circular references
- pytest-xdist workers cannot garbage collect
- Memory grows to 217GB VIRT, 42GB RES
- Tests slow down, eventually OOM kills

**With teardown_method + gc.collect():**
- Explicit GC after each test
- Memory stays at 1.8GB VIRT, 856MB RES
- **98% memory reduction, 40% faster tests**

### Problem 2: State Pollution (ADR-0053)
**Without setup_method:**
- Environment variables leak from previous tests
- Global singletons (like `_global_auth_middleware`) persist
- Tests pass sequentially, fail in parallel
- Intermittent, hard-to-debug failures

**With setup_method:**
- Clean state BEFORE each test
- Explicit reset of environment and globals
- Consistent behavior sequential or parallel
- **All 53 auth tests now pass reliably**

### Problem 3: Worker Isolation Violations
**Without @pytest.mark.xdist_group:**
- Related tests split across different workers
- Race conditions in shared resource cleanup
- Inconsistent test behavior
- Test flakiness

**With @pytest.mark.xdist_group:**
- Related tests run in same worker
- Predictable resource cleanup order
- Consistent test behavior
- Reliable parallel execution

---

## When to Use Each Pattern

### 1. Use @pytest.mark.xdist_group Always

**Required for:**
- ALL test classes (prevents worker splitting)

**Pattern:**
```python
@pytest.mark.xdist_group(name="descriptive_test_category_tests")
class TestSomething:
    pass
```

**Naming Convention:**
- Auth tests: `auth_tests`, `jwt_tests`, `bearer_tests`
- API tests: `api_endpoints_tests`, `api_versioning_tests`
- Integration: `integration_gdpr_tests`, `integration_mcp_tests`
- Unit: `unit_calculator_tests`, `unit_storage_tests`

### 2. Use setup_method() When

**Required for:**
- Tests manipulating environment variables
- Tests manipulating global singletons
- Auth tests (always, due to conftest.py pollution)
- Tests that depend on clean initial state

**Pattern:**
```python
def setup_method(self):
    """Reset state BEFORE test to prevent pollution."""
    import os
    import mcp_server_langgraph.auth.middleware as middleware_module

    # Reset singletons
    middleware_module._global_auth_middleware = None

    # Reset environment
    os.environ["MCP_SKIP_AUTH"] = "false"
```

### 3. Use teardown_method() When

**Required for:**
- Tests using AsyncMock
- Tests using MagicMock
- Tests using @patch decorators
- Tests creating many mock objects

**Pattern:**
```python
def teardown_method(self):
    """Force GC to prevent mock accumulation."""
    import gc
    gc.collect()
```

---

## Common Patterns by Test Type

### Auth Tests

**ALWAYS use all 3 parts** (pollution from tests/api/conftest.py):

```python
@pytest.mark.auth
@pytest.mark.xdist_group(name="auth_tests")
class TestAuthentication:
    def setup_method(self):
        """Reset state BEFORE test to prevent MCP_SKIP_AUTH pollution."""
        import os
        import mcp_server_langgraph.auth.middleware as middleware_module

        middleware_module._global_auth_middleware = None
        os.environ["MCP_SKIP_AUTH"] = "false"

    def teardown_method(self):
        """Force GC to prevent mock accumulation."""
        import gc
        gc.collect()
```

### API Tests with Mocks

```python
@pytest.mark.api
@pytest.mark.xdist_group(name="api_endpoints_tests")
class TestAPIEndpoints:
    def teardown_method(self):
        """Force GC to prevent mock accumulation."""
        import gc
        gc.collect()

    async def test_endpoint_with_mock(self):
        mock_service = AsyncMock(spec=SomeService)
        # ... test code ...
```

### Integration Tests

```python
@pytest.mark.integration
@pytest.mark.xdist_group(name="integration_postgres_tests")
class TestPostgresIntegration:
    def setup_method(self):
        """Reset any global state before test."""
        # Reset module-level variables if needed
        pass

    def teardown_method(self):
        """Force GC after test."""
        import gc
        gc.collect()
```

### Unit Tests (Simple)

**Minimal pattern** (only xdist_group):

```python
@pytest.mark.unit
@pytest.mark.xdist_group(name="unit_calculator_tests")
class TestCalculator:
    def test_addition(self):
        assert add(2, 3) == 5
```

---

## Environment Variable Best Practices

### ❌ NEVER Do This

```python
# Direct mutation - pollutes other tests
import os
os.environ["SOME_VAR"] = "value"
```

### ✅ ALWAYS Do This Instead

**Option 1: Use monkeypatch (preferred)**
```python
def test_something(monkeypatch):
    monkeypatch.setenv("SOME_VAR", "value")
    # Automatically cleaned up after test
```

**Option 2: Use setup_method + cleanup**
```python
class TestSomething:
    def setup_method(self):
        self.original_var = os.environ.get("SOME_VAR")
        os.environ["SOME_VAR"] = "value"

    def teardown_method(self):
        if self.original_var is not None:
            os.environ["SOME_VAR"] = self.original_var
        else:
            del os.environ["SOME_VAR"]
        gc.collect()
```

---

## Debugging State Pollution

### Symptoms

1. **Test passes alone, fails in parallel:**
   ```bash
   # Passes
   pytest tests/test_auth.py::test_something -v

   # Fails
   pytest tests/test_auth.py -n auto -v
   ```
   **Cause:** State pollution from another test in same worker

2. **Intermittent failures:**
   ```bash
   # Sometimes passes, sometimes fails
   for i in {1..10}; do pytest tests/test_auth.py -n auto; done
   ```
   **Cause:** Non-deterministic test execution order in workers

3. **Memory grows over time:**
   ```bash
   watch -n 1 'ps aux | grep pytest'
   # Memory steadily increases during test run
   ```
   **Cause:** Missing teardown_method + gc.collect()

### Diagnosis

**Step 1: Check pre-commit validation**
```bash
python scripts/check_test_memory_safety.py tests/your_test_file.py
```

**Step 2: Run with verbose worker output**
```bash
pytest tests/your_test_file.py -n auto -v --tb=short
# Look for which worker (gw0, gw1, etc.) failed
```

**Step 3: Isolate the test**
```bash
# Run just the failing test in parallel
pytest tests/your_test_file.py::TestClass::test_method -n 4 -v
```

**Step 4: Check for global state**
```bash
grep -n "os.environ" tests/your_test_file.py
grep -n "_global_" tests/your_test_file.py
grep -n "module\\..*=" tests/your_test_file.py
```

### Common Fixes

1. **Auth test failing with 401/403:**
   - **Cause:** MCP_SKIP_AUTH pollution from conftest.py
   - **Fix:** Add setup_method with `os.environ["MCP_SKIP_AUTH"] = "false"`

2. **Memory explosion:**
   - **Cause:** AsyncMock/MagicMock without GC
   - **Fix:** Add teardown_method with `gc.collect()`

3. **Flaky integration test:**
   - **Cause:** Missing xdist_group marker
   - **Fix:** Add `@pytest.mark.xdist_group(name="integration_tests")`

---

## Validation and Enforcement

### Pre-commit Hook

Automatically runs on every commit:
```yaml
# .pre-commit-config.yaml
- id: check-test-memory-safety
  name: Check Test Memory Safety
  entry: python scripts/check_test_memory_safety.py
  language: system
  types: [python]
  pass_filenames: true
  stages: [commit]
```

Checks for:
- ✅ AsyncMock/MagicMock without teardown_method
- ✅ Auth tests without setup_method
- ✅ Test classes without xdist_group markers
- ✅ Direct os.environ mutation

### CI/CD Validation

Runs in GitHub Actions (Phase 1):
```bash
make validate-pre-push
# Includes: python scripts/check_test_memory_safety.py
```

### Manual Validation

```bash
# Check single file
python scripts/check_test_memory_safety.py tests/test_auth.py

# Check all test files
python scripts/check_test_memory_safety.py tests/

# Generate full report (comprehensive validation)
python scripts/check_test_memory_safety.py tests/ > memory_safety_report.txt
```

---

## Migration Guide

### For Existing Tests

1. **Find your test class:**
   ```bash
   grep -n "class Test" tests/your_file.py
   ```

2. **Check if it uses mocks:**
   ```bash
   grep -n "AsyncMock\|MagicMock\|@patch" tests/your_file.py
   ```

3. **Add the pattern:**
   ```python
   @pytest.mark.xdist_group(name="your_category_tests")
   class TestYourFeature:
       def teardown_method(self):
           import gc
           gc.collect()
   ```

4. **If auth test, add setup_method too:**
   ```python
   def setup_method(self):
       import os
       import mcp_server_langgraph.auth.middleware as middleware_module
       middleware_module._global_auth_middleware = None
       os.environ["MCP_SKIP_AUTH"] = "false"
   ```

5. **Validate:**
   ```bash
   python scripts/check_test_memory_safety.py tests/your_file.py
   pytest tests/your_file.py -n auto -v
   ```

### For New Tests

1. **Use the template from "Quick Reference" at top of this document**
2. **Run validation before committing:**
   ```bash
   python scripts/check_test_memory_safety.py tests/your_new_test.py
   ```
3. **Verify parallel execution:**
   ```bash
   pytest tests/your_new_test.py -n auto -v
   ```

---

## References

- **ADR-0052:** Pytest-xdist Memory Explosion Prevention
- **ADR-0053:** Pytest-xdist State Pollution Prevention
- **Memory Safety Guidelines:** `tests/MEMORY_SAFETY_GUIDELINES.md`
- **Validation Script:** `scripts/check_test_memory_safety.py`
- **Comprehensive Scan:** `PYTEST_XDIST_STATE_POLLUTION_SCAN_REPORT.md`
- **Regression Tests:** `tests/regression/test_service_principal_test_isolation.py`
- **Example Fixes:** Commit `4d71c2d9` (56 files, 922 insertions)

---

## FAQ

**Q: Do I need all 3 parts for every test?**
A: No. Only add what you need:
- xdist_group: Always (all test classes)
- teardown_method: If using AsyncMock/MagicMock
- setup_method: If manipulating env vars or global state

**Q: What if my test doesn't use mocks or env vars?**
A: Just add @pytest.mark.xdist_group, that's sufficient.

**Q: Can I skip this for unit tests?**
A: Add xdist_group always. Add setup/teardown only if using mocks or global state.

**Q: How do I know which xdist_group name to use?**
A: Group related tests together. Use descriptive names: `auth_tests`, `api_endpoints_tests`, `integration_postgres_tests`

**Q: What if the pre-commit hook fails?**
A: Don't bypass it! Fix the violations. The hook prevents pollution bugs from reaching production.

**Q: My test is flaky. How do I debug?**
A: See "Debugging State Pollution" section above. Run with `-n auto -v --tb=short` to see worker assignments.

**Q: Can I use fixtures instead of setup_method?**
A: You can, but setup_method is more explicit and easier to debug. Fixtures with autouse=True can cause ordering issues.

---

**For questions or issues, see:** `docs/architecture/adr/ADR-0053-pytest-xdist-state-pollution-prevention.md`
