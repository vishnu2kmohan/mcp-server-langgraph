---
purpose: Prevent memory explosion and test failures in pytest-xdist parallel execution
priority: critical
category: testing
last-updated: 2026-02-05
---

# pytest-xdist Safety Patterns

---

## Problem & Impact

**Root Cause**: pytest-xdist worker isolation + Mock object circular references = Memory explosion

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| VIRT | 217GB | 1.8GB | 99% reduction |
| RES | 42GB | 856MB | 98% reduction |
| Duration | 3m 45s | 2m 12s | 40% faster |

---

## Memory Safety Checklist

Before writing ANY test using `AsyncMock` or `MagicMock`:

- [ ] Add `@pytest.mark.xdist_group(name="unique_group_name")` to test class
- [ ] Add `teardown_method(self)` with `gc.collect()`
- [ ] Use `AsyncMock` for async methods, `MagicMock` for sync methods
- [ ] Configure mock return values explicitly (never leave unconfigured)

---

## Three-Part Safety Approach

### 1. Test Grouping with `xdist_group`

```python
@pytest.mark.xdist_group(name="test_auth_middleware")
class TestAuthMiddleware:
    """All tests in this class run in same worker"""

    def teardown_method(self):
        gc.collect()
```

**Naming**: `"test_<component>_<feature>"` (avoid generic names like `"group1"`)

### 2. Explicit Garbage Collection

```python
class TestComponent:
    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    async def test_with_mock(self):
        mock = AsyncMock(spec=SomeClass)
        mock.method.return_value = "expected"
        # Test code here
```

### 3. Skip Performance Tests in Parallel Mode

```python
@pytest.mark.performance
@pytest.mark.skipif(
    os.getenv("PYTEST_XDIST_WORKER") is not None,
    reason="Performance tests skipped in parallel mode due to memory overhead"
)
async def test_large_dataset_performance(self):
    # Resource-intensive test code
```

---

## Three-Tier Fixture Architecture

### Tier 1: Session-Scoped Autouse (conftest.py ONLY)

**Rule**: ALL session/module-scoped autouse fixtures MUST be in `tests/conftest.py`

```python
# tests/conftest.py
@pytest.fixture(scope="session", autouse=True)
def init_test_observability():
    os.environ["OTEL_SDK_DISABLED"] = "true"
    yield
```

### Tier 2: Modular Fixtures (pytest_plugins)

```python
# tests/conftest.py
pytest_plugins = [
    "tests.fixtures.litellm_patch",
    "tests.fixtures.docker_fixtures",
    "tests.fixtures.database_fixtures",
    "tests.fixtures.tool_fixtures",
]
```

### Tier 3: Category-Specific conftest

Allowed in: `tests/api/`, `tests/performance/`, `tests/e2e/`

**Rules**:
- ✅ Category-specific hooks and function-scoped fixtures
- ❌ NO session/module-scoped autouse fixtures

---

## Anti-Patterns (AVOID)

| Anti-Pattern | Problem | Fix |
|--------------|---------|-----|
| No `xdist_group` | Tests hop between workers | Add `@pytest.mark.xdist_group(name="...")` |
| No `teardown_method` | Mocks accumulate in memory | Add `gc.collect()` in teardown |
| Unconfigured AsyncMock | Returns truthy `<AsyncMock>` | Always set `.return_value` |
| Large dataset in parallel | Memory multiplies across workers | Skip with `PYTEST_XDIST_WORKER` check |
| Duplicate autouse fixtures | Initialization conflicts | Define in `tests/conftest.py` only |

### Critical: Unconfigured AsyncMock Security Bug

```python
# ❌ WRONG - Security vulnerability
mock_openfga = AsyncMock()  # No return_value!
result = await mock_openfga.check_permission("user", "resource")
if result:  # Always True (<AsyncMock> is truthy)
    grant_access()  # SECURITY BUG!

# ✅ CORRECT
mock_openfga = AsyncMock()
mock_openfga.check_permission.return_value = False  # Explicit
```

---

## Template: Safe Async Test Class

```python
import gc
import pytest
from unittest.mock import AsyncMock

@pytest.mark.xdist_group(name="test_<component>")
class Test<Component>:
    def teardown_method(self):
        gc.collect()

    @pytest.mark.asyncio
    async def test_<operation>(self):
        # Given
        mock = AsyncMock()
        mock.method.return_value = "expected"

        # When
        result = await mock.method()

        # Then
        assert result == "expected"
```

---

## pytest Configuration

```toml
# pyproject.toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "session"  # Prevents loop mismatches
addopts = "--dist loadscope -n auto"
timeout = 60
```

---

## Troubleshooting

| Issue | Diagnosis | Fix |
|-------|-----------|-----|
| Memory keeps growing | Run `check_test_memory_safety.py` | Add `teardown_method` + `gc.collect()` |
| Pass individually, fail parallel | Check fixture scopes, shared state | Add `xdist_group`, use `dependency_overrides.clear()` |
| "Future attached to different loop" | Wrong fixture loop scope | Add `loop_scope="session"` to fixture |

---

## Validation Commands

```bash
# Check memory safety
uv run --frozen python scripts/validation/check_test_memory_safety.py tests/

# Run single worker (isolate issues)
pytest -n 1 tests/

# Show fixture setup
pytest --setup-show tests/test_file.py
```

---

## Related Docs

- Async Test Helpers: `.claude/context/async-test-helpers.md` (run_async, double GC)
- Memory Safety: `tests/MEMORY_SAFETY_GUIDELINES.md`
- AsyncMock Guidelines: `tests/ASYNC_MOCK_GUIDELINES.md`
- Fixture Organization Test: `tests/meta/test_fixture_organization.py`
- Test Constants: `.claude/context/test-constants-pattern.md`

---

**Enforcement**: Pre-commit hooks + runtime plugin + meta-tests
