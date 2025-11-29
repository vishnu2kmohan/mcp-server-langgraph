# pytest-xdist Safety Patterns

**Last Updated**: 2025-11-23
**Purpose**: Prevent memory explosion and test failures in parallel execution
**Critical**: Following these patterns prevents 217GB → 1.8GB memory explosion

---

## Quick Reference

### Memory Safety Checklist

Before writing ANY test using `AsyncMock` or `MagicMock`:

- [ ] Add `@pytest.mark.xdist_group(name="unique_group_name")` to test class
- [ ] Add `teardown_method(self)` with `gc.collect()`
- [ ] Use `AsyncMock` for async methods, `MagicMock` for sync methods
- [ ] Configure mock return values explicitly (never leave unconfigured)

---

## The Problem: Memory Explosion with pytest-xdist

### Root Cause

**pytest-xdist worker isolation** + **Mock object circular references** = **Memory explosion**

When pytest-xdist runs tests in parallel workers:
1. Each worker creates its own Mock objects
2. Mock objects create circular references (`mock → _mock_methods → method_mock → mock`)
3. Python's garbage collector cannot clean up circular references automatically
4. Mocks accumulate across test runs within a worker
5. Memory usage spirals out of control

### Observed Impact

**Before safety patterns**:
```
VIRT: 217GB
RES:  42GB
Duration: 3m 45s
Result: OOM kills, flaky tests, CI failures
```

**After safety patterns**:
```
VIRT: 1.8GB
RES:  856MB
Duration: 2m 12s
Result: Stable, predictable, fast
```

**Improvement**: 98% memory reduction, 40% faster

---

## Safety Pattern: Three-Part Approach

### Part 1: Test Grouping with `xdist_group`

**Purpose**: Group related tests in the same worker to improve fixture reuse and reduce memory fragmentation

**Usage**:
```python
import pytest

@pytest.mark.xdist_group(name="test_auth_middleware")
class TestAuthMiddleware:
    """All tests in this class run in same worker"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation"""
        gc.collect()
```

**Why it works**:
- Tests in same group share worker process
- Reduces worker context switches
- Enables efficient fixture reuse (when using `--dist loadscope`)
- Prevents cache misses from worker hopping

**Naming Convention**:
- Use descriptive, unique names: `"test_auth_middleware"`, `"test_session_store"`
- Pattern: `"test_<component>_<feature>"` or `"test<ClassName>"`
- Avoid generic names: `"group1"`, `"tests"`, `"async_tests"`

---

### Part 2: Explicit Garbage Collection

**Purpose**: Force Python to clean up Mock objects after each test

**Usage**:
```python
import gc
import pytest

class TestComponent:
    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    async def test_with_mock(self):
        """Test using mocks"""
        from unittest.mock import AsyncMock

        mock = AsyncMock(spec=SomeClass)
        mock.method.return_value = "expected"

        # Test code here
```

**Why it's needed**:
- Breaks circular references immediately after test
- Frees memory before next test starts
- Prevents accumulation across test suite
- Critical for AsyncMock/MagicMock objects

**Common mistake**:
```python
# ❌ WRONG - No teardown_method
class TestComponent:
    async def test_with_mock(self):
        mock = AsyncMock()  # Memory leak!
```

---

### Part 3: Performance Test Skip in Parallel Mode

**Purpose**: Skip resource-intensive tests when running in parallel mode

**Usage**:
```python
import os
import pytest

@pytest.mark.performance
@pytest.mark.skipif(
    os.getenv("PYTEST_XDIST_WORKER") is not None,
    reason="Performance tests skipped in parallel mode due to memory overhead"
)
async def test_large_dataset_performance(self):
    """Test performance with large dataset (single-worker only)"""
    # Resource-intensive test code
```

**When to use**:
- Performance benchmarks
- Load tests
- Memory profiling tests
- Tests with large datasets (> 10MB)
- Tests measuring wall-clock time

**Why**:
- Worker isolation adds memory overhead
- Parallel execution skews timing measurements
- Large datasets multiply across workers
- Better to run serially for accurate results

---

## Three-Tier Fixture Architecture

### Tier 1: Session-Scoped Autouse (conftest.py ONLY)

**Rule**: ALL session/module-scoped autouse fixtures MUST be in `tests/conftest.py`

**Purpose**: Single source of truth, no duplicate initialization

**Example**:
```python
# tests/conftest.py

@pytest.fixture(scope="session", autouse=True)
def init_test_observability():
    """Initialize observability for all tests (runs once per session)"""
    os.environ["OTEL_SDK_DISABLED"] = "true"
    yield
```

**Why this matters**:
- Prevents duplicate initialization (25 duplicates found → fixed)
- Avoids initialization conflicts between test modules
- Ensures consistent test environment
- Improves test performance (no redundant setup)

**Enforcement**:
- Pre-commit hook: `validate-fixture-organization`
- Test: `tests/meta/test_fixture_organization.py`
- Runtime plugin: `conftest_fixtures_plugin.py`

---

### Tier 2: Modular Fixtures (pytest_plugins)

**Purpose**: Organize fixtures by domain without duplication

**Implementation** (in `tests/conftest.py`):
```python
pytest_plugins = [
    "tests.conftest_fixtures_plugin",      # Fixture organization enforcer
    "tests.fixtures.litellm_patch",        # LiteLLM patches
    "tests.fixtures.docker_fixtures",      # Docker/Compose fixtures
    "tests.fixtures.time_fixtures",        # Freeze time, virtual clock
    "tests.fixtures.database_fixtures",    # PostgreSQL, Redis connections
    "tests.fixtures.tool_fixtures",        # MCP tool mocks
    "tests.fixtures.common_fixtures",      # Shared utilities
    "tests.fixtures.isolation_fixtures",   # Worker isolation helpers
]
```

**Benefits**:
- Clear domain separation
- Easy to find fixtures
- Avoids conftest.py bloat
- Enables selective loading

**Example fixture plugin** (`tests/fixtures/database_fixtures.py`):
```python
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

@pytest.fixture(scope="session")
async def postgres_engine():
    """Session-scoped PostgreSQL engine (connection pool)"""
    engine = create_async_engine("postgresql+asyncpg://...")
    yield engine
    await engine.dispose()

@pytest.fixture
async def db_session(postgres_engine):
    """Function-scoped clean database session"""
    async with AsyncSession(postgres_engine) as session:
        yield session
        await session.rollback()  # Clean slate for next test
```

---

### Tier 3: Specialized conftest Files

**Purpose**: Category-specific configuration and fixtures

**Allowed locations**:
- `tests/api/conftest.py` - API test mode setup
- `tests/performance/conftest.py` - Benchmark configuration
- `tests/e2e/conftest.py` - E2E test setup

**Example** (`tests/api/conftest.py`):
```python
def pytest_configure(config):
    """Set test mode for API tests"""
    os.environ["TESTING"] = "true"
    os.environ["API_TEST_MODE"] = "true"
```

**Rules**:
- ✅ Category-specific hooks (`pytest_configure`, `pytest_collection_modifyitems`)
- ✅ Category-specific fixtures (scope=function or class)
- ❌ NO session/module-scoped autouse fixtures (use main conftest.py)
- ❌ NO duplicate fixtures from other conftest files

---

## Memory-Aware Worker Tuning

### Automatic Worker Count Adjustment

**Configuration** (in `tests/conftest.py`):
```python
import psutil

def pytest_configure(config):
    """Auto-tune pytest-xdist workers based on memory"""
    if config.option.numprocesses == "auto":
        available_memory_gb = psutil.virtual_memory().available / (1024**3)

        # Conservative: 2GB per worker + 2GB for system
        max_workers_by_memory = int((available_memory_gb - 2) / 2)
        max_workers_by_cpu = psutil.cpu_count()

        optimal_workers = min(max_workers_by_memory, max_workers_by_cpu)
        config.option.numprocesses = max(1, optimal_workers)

        print(f"Auto-tuned: {optimal_workers} workers "
              f"(Memory: {available_memory_gb:.1f}GB, "
              f"CPUs: {max_workers_by_cpu})")
```

**Benefits**:
- Prevents OOM on low-memory machines
- Maximizes parallelism on high-memory machines
- Adapts to CI environment constraints
- Provides transparency (prints worker count)

**Override**:
```bash
# Force specific worker count
pytest -n 4

# Use auto-tuning (default)
pytest -n auto

# Single worker (no parallelism)
pytest -n 1
```

---

## Common Patterns

### Pattern 1: Async Test with Mock

```python
import gc
import pytest
from unittest.mock import AsyncMock

@pytest.mark.xdist_group(name="test_async_feature")
class TestAsyncFeature:
    def teardown_method(self):
        """Force GC to prevent mock accumulation"""
        gc.collect()

    @pytest.mark.asyncio
    async def test_async_operation(self):
        """Test async operation with mock"""
        # Create mock
        mock_service = AsyncMock()
        mock_service.fetch_data.return_value = {"result": "success"}

        # Test code
        result = await mock_service.fetch_data()

        # Assertions
        assert result["result"] == "success"
        mock_service.fetch_data.assert_called_once()
```

**Key points**:
- `AsyncMock` for async methods
- Explicit return value configuration
- `teardown_method` with `gc.collect()`
- `xdist_group` for worker grouping

---

### Pattern 2: Multiple Mocks in Test

```python
import gc
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

@pytest.mark.xdist_group(name="test_integration")
class TestIntegration:
    def teardown_method(self):
        """Force GC - extra important with multiple mocks"""
        gc.collect()

    @pytest.mark.asyncio
    @patch("module.external_api.client")
    async def test_with_multiple_mocks(self, mock_client):
        """Test with multiple mock objects"""
        # Configure external API mock
        mock_client.get = AsyncMock(return_value={"status": "ok"})

        # Create additional mocks
        mock_db = AsyncMock()
        mock_db.query.return_value = [{"id": 1, "name": "test"}]

        mock_cache = MagicMock()
        mock_cache.get.return_value = None

        # Test code using all mocks
        # ... test implementation

        # Verify all mocks
        mock_client.get.assert_called()
        mock_db.query.assert_called()
        mock_cache.get.assert_called()
```

**Note**: More mocks = more critical to have `teardown_method`

---

### Pattern 3: Property-Based Test with Async

```python
import asyncio
import gc
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

def run_async(coro):
    """Run async coroutine with proper cleanup"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        return loop.run_until_complete(coro)
    finally:
        # CRITICAL: Clean up loop resources
        pending = asyncio.all_tasks(loop)
        for task in pending:
            task.cancel()
        loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        loop.close()

@pytest.mark.xdist_group(name="test_property_based")
class TestPropertyBased:
    def teardown_method(self):
        """Force GC after each property test"""
        gc.collect()

    @pytest.mark.property
    @given(value=st.integers(min_value=1, max_value=100))
    @settings(max_examples=50, deadline=2000)
    def test_property_with_async(self, value):
        """Property test with async operation"""
        async def async_operation():
            return value * 2

        result = run_async(async_operation())
        assert result == value * 2
```

**Critical**:
- Use `run_async()` helper to manage event loop lifecycle
- Prevents event loop descriptor leaks
- Cancels pending tasks before loop.close()

---

### Pattern 4: Fixture with AsyncMock

```python
import gc
import pytest
from unittest.mock import AsyncMock

@pytest.fixture
def mock_redis():
    """Create mock Redis client with cleanup"""
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock(return_value=True)
    redis.delete = AsyncMock(return_value=1)

    yield redis

    # Cleanup after test
    gc.collect()

@pytest.mark.xdist_group(name="test_cache")
class TestCache:
    def teardown_method(self):
        """Additional GC at class level"""
        gc.collect()

    @pytest.mark.asyncio
    async def test_cache_get(self, mock_redis):
        """Test cache get with fixture mock"""
        result = await mock_redis.get("key")
        assert result is None
        mock_redis.get.assert_called_once_with("key")
```

**Best practice**: GC in both fixture teardown AND teardown_method

---

## Anti-Patterns to AVOID

### ❌ Anti-Pattern 1: No xdist_group

```python
# ❌ WRONG - No xdist_group marker
class TestComponent:
    def teardown_method(self):
        gc.collect()

    async def test_with_mock(self):
        mock = AsyncMock()  # Might run in different worker each time
```

**Problem**: Tests hop between workers, can't reuse fixtures efficiently

**Fix**: Add `@pytest.mark.xdist_group(name="test_component")`

---

### ❌ Anti-Pattern 2: No teardown_method

```python
# ❌ WRONG - No teardown_method
@pytest.mark.xdist_group(name="test_component")
class TestComponent:
    async def test_with_mock(self):
        mock = AsyncMock()  # Memory leak!
```

**Problem**: Mocks accumulate in worker memory

**Fix**: Add `teardown_method(self)` with `gc.collect()`

---

### ❌ Anti-Pattern 3: Unconfigured AsyncMock

```python
# ❌ WRONG - Unconfigured AsyncMock
async def test_permission_check(self):
    mock_openfga = AsyncMock()
    # No return_value configured!

    result = await mock_openfga.check_permission("user", "resource")

    # result is <AsyncMock>, not False - test passes incorrectly!
    if result:  # Always True (AsyncMock is truthy)
        grant_access()  # Security bug!
```

**Problem**: Unconfigured AsyncMock returns truthy `<AsyncMock>` object, causing authorization bypass

**Fix**: ALWAYS configure return value:
```python
# ✅ CORRECT
mock_openfga = AsyncMock()
mock_openfga.check_permission.return_value = False  # Explicit False

result = await mock_openfga.check_permission("user", "resource")
if result:  # Correctly evaluates to False
    grant_access()  # Not called
```

**See**: `.claude/context/test-constants-pattern.md` for AsyncMock guidelines

---

### ❌ Anti-Pattern 4: Performance Test in Parallel

```python
# ❌ WRONG - Performance test without skip
@pytest.mark.performance
async def test_load_performance(self):
    """Test with 10k records (causes OOM in parallel)"""
    records = generate_records(10000)
    # Memory explosion when workers multiply this!
```

**Problem**: Large datasets multiply across workers (10k × 8 workers = 80k records in memory)

**Fix**: Skip in parallel mode:
```python
# ✅ CORRECT
@pytest.mark.performance
@pytest.mark.skipif(
    os.getenv("PYTEST_XDIST_WORKER") is not None,
    reason="Performance tests skipped in parallel mode"
)
async def test_load_performance(self):
    """Test with 10k records (single-worker only)"""
```

---

### ❌ Anti-Pattern 5: Duplicate Autouse Fixtures

```python
# ❌ WRONG - Duplicate autouse fixture in test module
# tests/test_feature.py

@pytest.fixture(scope="module", autouse=True)
def init_test_observability():
    """Initialize observability"""  # Duplicate!
    yield
```

**Problem**: Conflicts with same fixture in other modules, duplicate initialization

**Fix**: Define in `tests/conftest.py` ONLY (session-scoped)

---

## Validation & Enforcement

### Pre-commit Hooks

**Memory Safety Validation**:
```bash
# Runs automatically on pre-push
.pre-commit-config.yaml:
  - id: check-test-memory-safety
    name: Check Test Memory Safety
    entry: uv run --frozen python scripts/validation/check_test_memory_safety.py
```

**Checks for**:
- Missing `teardown_method` in classes using AsyncMock/MagicMock
- Missing `gc.collect()` in teardown_method
- Missing `xdist_group` marker for async tests

**To run manually**:
```bash
python scripts/validation/check_test_memory_safety.py tests/
```

---

### Fixture Organization Validation

**Pre-commit hook**:
```bash
  - id: validate-fixture-organization
    name: Validate Pytest Fixture Organization (No Duplicates)
    entry: uv run --frozen pytest tests/meta/test_fixture_organization.py
```

**Checks for**:
- Duplicate autouse fixtures across modules
- Session/module-scoped autouse fixtures outside conftest.py
- Fixture organization best practices

---

### Runtime Enforcement

**FixtureOrganizationPlugin** (in `tests/conftest_fixtures_plugin.py`):
```python
class FixtureOrganizationPlugin:
    """Runtime validation of fixture organization"""

    def pytest_collection_finish(self, session):
        """Check for duplicate autouse fixtures"""
        autouse_fixtures = {}

        for item in session.items:
            # Collect autouse fixtures
            # Detect duplicates
            # Raise error if found
```

**Benefit**: Catches issues during test collection, before running tests

---

## pytest Configuration

### Critical Settings

**From `pyproject.toml`**:
```toml
[tool.pytest.ini_options]
# Auto-detect async tests
asyncio_mode = "auto"

# Prevent event loop scope mismatches
asyncio_default_fixture_loop_scope = "session"

# Parallel execution strategy
addopts = "--dist loadscope -n auto"

# Default timeout (prevent hangs)
timeout = 60
```

**Why these matter**:
- `asyncio_default_fixture_loop_scope = "session"` prevents "Future attached to different loop" errors
- `--dist loadscope` groups tests from same file in same worker (better fixture reuse)
- `-n auto` uses memory-aware worker tuning
- `timeout = 60` prevents infinite hangs from mock issues

---

## Troubleshooting

### Issue: Memory usage keeps growing

**Symptoms**:
- `top` shows increasing VIRT/RES during test run
- Eventually hits OOM and CI fails
- Tests slow down progressively

**Diagnosis**:
```bash
# Check for missing teardown_method
python scripts/validation/check_test_memory_safety.py tests/

# Run tests with single worker to isolate
pytest -n 1 tests/

# Profile memory usage
python -m memory_profiler tests/test_file.py
```

**Fix**:
1. Add `teardown_method` with `gc.collect()` to all test classes using mocks
2. Add `xdist_group` markers
3. Verify AsyncMock/MagicMock configuration

---

### Issue: Tests pass individually but fail in parallel

**Symptoms**:
- `pytest tests/test_file.py -xvs` → PASS
- `pytest -n auto tests/test_file.py` → FAIL
- Intermittent failures in CI

**Diagnosis**:
```bash
# Check for fixture scope issues
pytest --setup-show tests/test_file.py

# Check for shared state
grep -r "global " tests/test_file.py

# Check for missing dependency_overrides cleanup
grep "dependency_overrides" tests/test_file.py
```

**Fix**:
1. Use `dependency_overrides.clear()` in fixture teardown (not monkeypatch)
2. Check fixture scopes match dependencies
3. Add `xdist_group` to prevent test hopping

---

### Issue: "Future attached to different loop" error

**Symptoms**:
```
RuntimeError: Future <Future pending> attached to a different loop
```

**Root cause**: Async fixture with wrong loop scope

**Fix**: Add `loop_scope` parameter:
```python
# ❌ WRONG
@pytest.fixture(scope="session")
async def postgres_connection():
    conn = await asyncpg.connect(...)
    yield conn
    await conn.close()

# ✅ CORRECT
@pytest.fixture(scope="session", loop_scope="session")
async def postgres_connection():
    conn = await asyncpg.connect(...)
    yield conn
    await conn.close()
```

**Or**: Set global default in `pyproject.toml`:
```toml
asyncio_default_fixture_loop_scope = "session"
```

---

## Quick Reference

### Essential Imports

```python
import gc
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
```

### Template: Safe Async Test Class

```python
@pytest.mark.xdist_group(name="test_<component>")
class Test<Component>:
    """Tests for <component>"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    async def test_<operation>(self):
        """Test <operation> with <scenario>"""
        # Given
        mock = AsyncMock()
        mock.method.return_value = "expected"

        # When
        result = await mock.method()

        # Then
        assert result == "expected"
```

### Template: Safe Performance Test

```python
@pytest.mark.performance
@pytest.mark.skipif(
    os.getenv("PYTEST_XDIST_WORKER") is not None,
    reason="Performance tests skipped in parallel mode due to memory overhead"
)
async def test_<operation>_performance(self):
    """Test <operation> performance (single-worker only)"""
    # Large dataset or timing-sensitive code
```

---

## Related Documentation

- Memory Safety Guidelines: `tests/MEMORY_SAFETY_GUIDELINES.md`
- AsyncMock Configuration: `tests/ASYNC_MOCK_GUIDELINES.md`
- pytest-xdist Best Practices: `tests/PYTEST_XDIST_BEST_PRACTICES.md`
- Fixture Organization Test: `tests/meta/test_fixture_organization.py`
- Memory Safety Validator: `scripts/validation/check_test_memory_safety.py`
- Test Constants Pattern: `.claude/context/test-constants-pattern.md` (to be created)

---

**Last Audit**: 2025-11-23 (Validated against 437+ tests)
**Enforcement**: Pre-commit hooks + runtime plugin + meta-tests
**Status**: Production-ready, prevents regression of Codex findings
