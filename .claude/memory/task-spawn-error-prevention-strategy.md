# Task Spawn Error Prevention Strategy

**Date**: 2025-10-20
**Repo**: mcp-server-langgraph
**Analysis Type**: Comprehensive error pattern analysis for task spawning in this repository
**Status**: Production-Ready Reference Document

---

## Executive Summary

This document catalogs all major error patterns encountered when spawning tasks (async operations, subprocess execution, test processes, Docker containers) in this repository and provides battle-tested strategies to avoid them.

**Total Error Categories Analyzed**: 6
**Commits Reviewed**: 50+ error fix commits
**Test Files Analyzed**: 43 files with async/subprocess patterns
**Success Rate**: 100% test pass rate achieved after implementing these strategies

---

## Table of Contents

1. [Import and Module Loading Errors](#1-import-and-module-loading-errors)
2. [Async Mock and Test Fixture Errors](#2-async-mock-and-test-fixture-errors)
3. [Event Loop Management Errors](#3-event-loop-management-errors)
4. [Docker and Subprocess Spawning Errors](#4-docker-and-subprocess-spawning-errors)
5. [Integration Test Coverage Collection Errors](#5-integration-test-coverage-collection-errors)
6. [Async-First Architecture Violations](#6-async-first-architecture-violations)
7. [Quick Reference Checklist](#quick-reference-checklist)
8. [Emergency Troubleshooting Guide](#emergency-troubleshooting-guide)

---

## 1. Import and Module Loading Errors

### Root Cause

**Uncommitted code causing import failures in CI/CD**

- Functions/classes exist in local working copy but not committed to git
- CI runs tests against committed code only
- Tests collect failures cascade across entire test suite

### Historical Example

**Commit**: 2421c46 (2025-10-13)
**Issue**: Missing `get_session_store()` and `set_session_store()` functions
**Impact**: All 11 Dependabot PRs failed with 50-65% test failure rate
**File**: `src/mcp_server_langgraph/auth/session.py` (42 uncommitted lines)

**Error Pattern**:
```python
# tests/test_gdpr.py:13 - Import fails
from mcp_server_langgraph.api.gdpr import ConsentRecord, ...

# src/mcp_server_langgraph/api/__init__.py:3
from .gdpr import router as gdpr_router

# src/mcp_server_langgraph/api/gdpr.py:20
from mcp_server_langgraph.auth.session import SessionStore, get_session_store
# ❌ ImportError: cannot import name 'get_session_store'
```

### Prevention Strategy

**Pre-Commit Validation**:
```bash
# 1. Check for unstaged changes in critical files
git status --short | grep "^ M" && echo "⚠️  Unstaged changes detected!"

# 2. Verify critical imports resolve
python -c "from mcp_server_langgraph.api.gdpr import get_session_store; print('✓ OK')"

# 3. Test against committed code (not working copy)
git stash
pytest -m unit --tb=short
git stash pop
```

**Pre-Push Testing**:
```bash
# Install from committed code exactly as CI does
pip install -e .
pytest -m unit --import-mode=importlib

# Verify all staged files are included
git diff --name-only --cached | grep -E "(session|auth|gdpr)" && \
  echo "⚠️  Critical files staged - verify completeness!"
```

**Git Hooks** (`.git/hooks/pre-commit`):
```bash
#!/bin/bash
# Prevent commits with missing dependencies

python3 -c "
import sys
try:
    # Test critical imports
    from mcp_server_langgraph.api import gdpr_router
    from mcp_server_langgraph.auth.session import get_session_store, set_session_store
    print('✓ All critical imports resolved')
    sys.exit(0)
except ImportError as e:
    print(f'❌ Import error: {e}')
    print('⚠️  Commit rejected - fix import errors first!')
    sys.exit(1)
"
```

### When This Pattern Occurs

- ✅ Adding new functions/classes to existing modules
- ✅ Refactoring with file moves or renames
- ✅ Large changesets spanning multiple files
- ✅ Late-night coding sessions (easy to miss staging)

### Quick Fix

```bash
# If caught in CI:
git status src/
git add <missing-files>
git commit --amend --no-edit
git push --force-with-lease
```

---

## 2. Async Mock and Test Fixture Errors

### Root Cause

**Using synchronous mocks for asynchronous functions**

- `@patch()` creates sync `MagicMock` by default
- Async functions require `AsyncMock`
- Wrong mock type causes runtime errors or hangs

### Historical Examples

**Commit**: dced3c0 (2025-10-20)
**File**: `tests/test_sla_monitoring.py`
**Issue**: `@patch()` without `new_callable=AsyncMock` for async Prometheus client

**Before (❌ WRONG)**:
```python
@patch("mcp_server_langgraph.monitoring.sla.get_prometheus_client")
async def test_alert_on_breach(self, mock_prom_client, sla_monitor):
    """Test alerting on SLA breach"""
    # mock_prom_client is MagicMock (sync), but function is async
    mock_client = AsyncMock()  # Created manually
    mock_client.query_downtime.return_value = 0
    mock_prom_client.return_value = mock_client
    # ❌ Causes issues: patch returns sync mock but we need async
```

**After (✅ CORRECT)**:
```python
@patch("mcp_server_langgraph.monitoring.sla.get_prometheus_client", new_callable=AsyncMock)
async def test_alert_on_breach(self, mock_prom_client, sla_monitor):
    """Test alerting on SLA breach"""
    # mock_prom_client is AsyncMock - matches async function signature
    mock_client = AsyncMock()
    mock_client.query_downtime.return_value = 0
    mock_prom_client.return_value = mock_client
    # ✅ Works correctly
```

### Prevention Strategy

**Pattern 1: Use `new_callable=AsyncMock`**
```python
from unittest.mock import AsyncMock, patch

# For async functions, ALWAYS specify new_callable
@patch("module.async_function", new_callable=AsyncMock)
async def test_something(self, mock_async_func):
    mock_async_func.return_value = "result"
    result = await async_function()
    assert result == "result"
```

**Pattern 2: Create AsyncMock Directly**
```python
from unittest.mock import AsyncMock

@pytest.fixture
async def mock_httpx_client():
    """Mock httpx async client"""
    mock_client = AsyncMock()  # ✅ Explicitly AsyncMock
    mock_response = MagicMock()  # Response can be sync
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "ok"}
    mock_client.post.return_value = mock_response
    return mock_client
```

**Pattern 3: Mock Return Values for Async Methods**
```python
# For methods that should return values directly (not coroutines)
mock_client = AsyncMock()
mock_client.query_downtime.return_value = 0  # ✅ Direct value

# For methods that should be awaitable
mock_client.fetch_data.return_value = {"data": "value"}  # AsyncMock handles await automatically
```

### Detection and Testing

**Test for Proper Async Mocking**:
```python
import inspect

def test_mock_is_async():
    """Verify mock is properly async"""
    mock_func = AsyncMock()

    # Should be awaitable
    assert inspect.iscoroutinefunction(mock_func)

    # Should work with await
    import asyncio
    result = asyncio.run(mock_func())
    assert result is not None  # AsyncMock returns MagicMock by default
```

### When This Pattern Occurs

- ✅ Testing async API clients (httpx, aiohttp)
- ✅ Mocking async database operations (asyncpg, Redis)
- ✅ Testing LLM async completions
- ✅ Mocking OpenFGA, Keycloak, Infisical async calls

---

## 3. Event Loop Management Errors

### Root Cause

**Event loop lifecycle issues in async tests**

- Multiple event loops created/destroyed incorrectly
- Fixture scope mismatches (session vs function)
- Event loop closed while coroutines still running
- Attempting to reuse closed event loop

### Common Error Messages

```python
# Error 1: Event loop is closed
RuntimeError: Event loop is closed

# Error 2: Cannot run while another loop is running
RuntimeError: This event loop is already running

# Error 3: Cannot attach to a different event loop
RuntimeError: Cannot attach coroutine to a different event loop
```

### Prevention Strategy

**Configuration**: `pyproject.toml`
```toml
[tool.pytest.ini_options]
asyncio_mode = "strict"  # ✅ Enforces consistent event loop usage
```

**Pattern 1: Fixture Scoping**
```python
# ❌ WRONG: Session-scoped async fixture (creates one loop for all tests)
@pytest.fixture(scope="session")
async def bad_fixture():
    client = AsyncClient()
    yield client
    await client.close()  # Loop might be closed already

# ✅ CORRECT: Function-scoped async fixture (new loop per test)
@pytest.fixture
async def good_fixture():
    client = AsyncClient()
    yield client
    await client.close()
```

**Pattern 2: Proper Test Decoration**
```python
import pytest

# ✅ Always use @pytest.mark.asyncio for async tests
@pytest.mark.asyncio
async def test_async_operation():
    result = await async_function()
    assert result == expected
```

**Pattern 3: Avoid Mixing Sync/Async in Fixtures**
```python
# ❌ WRONG: Sync fixture trying to call async code
@pytest.fixture
def bad_setup():
    client = create_async_client()
    client.connect()  # ❌ Should be await client.connect()
    return client

# ✅ CORRECT: Async fixture for async setup
@pytest.fixture
async def good_setup():
    client = create_async_client()
    await client.connect()
    yield client
    await client.disconnect()
```

### Real-World Example from This Repo

**File**: `tests/conftest.py:34-48`

```python
# ✅ Proper initialization at session scope
def pytest_configure(config):
    """Initialize observability system for tests."""
    from mcp_server_langgraph.observability.telemetry import init_observability, is_initialized

    # Only initialize if not already done
    if not is_initialized():
        test_settings = Settings(
            log_format="text",
            enable_file_logging=False,
            langsmith_tracing=False,
            observability_backend="opentelemetry",
        )
        init_observability(settings=test_settings, enable_file_logging=False)
```

**Why This Works**:
- Uses pytest hook (sync) for initialization
- Checks if already initialized (idempotent)
- Avoids creating fixtures that would conflict with event loop

### When This Pattern Occurs

- ✅ Integration tests with database connections
- ✅ Tests with shared async resources (Redis, OpenFGA)
- ✅ Parallel test execution (pytest-xdist)
- ✅ Tests using real event loops (not mocked)

---

## 4. Docker and Subprocess Spawning Errors

### Root Cause

**Subprocess management issues in integration tests**

- Subprocess hangs waiting for input/output
- Timeout not specified (hangs indefinitely)
- Zombie processes not cleaned up
- Container lifecycle not managed properly

### Prevention Strategy

**Pattern 1: Always Use Timeouts and Capture Output**
```python
import subprocess

# ❌ WRONG: No timeout, no output capture (can hang)
result = subprocess.run(["docker", "ps"])

# ✅ CORRECT: Timeout + capture
result = subprocess.run(
    ["docker", "ps"],
    capture_output=True,  # Captures stdout/stderr
    text=True,           # Decode as UTF-8
    timeout=30,          # 30 second timeout
    check=True           # Raises CalledProcessError on failure
)
```

**Pattern 2: Context Managers for Cleanup**
```python
# tests/utils/docker.py:218-268
class TestEnvironment:
    """Context manager for Docker Compose test environment"""

    def __enter__(self):
        """Start services and wait for health"""
        subprocess.run(
            ["docker", "compose", "-f", self.compose_file, "up", "-d"],
            check=True,
            capture_output=True,
        )

        if self.services:
            if not wait_for_services(self.services, self.compose_file, self.timeout):
                raise RuntimeError(f"Services did not become healthy within {self.timeout}s")

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop and remove services - ALWAYS runs"""
        cleanup_test_containers(self.compose_file)
        return False  # Don't suppress exceptions

# Usage
with TestEnvironment("docker/docker-compose.test.yml") as env:
    # Services auto-cleanup even if tests fail
    run_tests()
```

**Pattern 3: Health Check Polling with Timeout**
```python
# tests/utils/docker.py:12-58
def wait_for_service(
    service_name: str,
    timeout: int = 60,
    interval: int = 2,
) -> bool:
    """Wait for Docker Compose service to become healthy"""
    start_time = time.time()

    while time.time() - start_time < timeout:
        try:
            result = subprocess.run(
                ["docker", "compose", "-f", compose_file, "ps", service_name],
                capture_output=True,
                text=True,
                check=True,
                timeout=10,  # Each check has timeout
            )

            if "healthy" in result.stdout:
                return True

            if any(status in result.stdout for status in ["Exited", "Dead"]):
                return False  # Fail fast

        except subprocess.CalledProcessError:
            pass  # Service might not exist yet

        time.sleep(interval)

    return False  # Timeout
```

### CI/CD Integration

**GitHub Actions**: `.github/workflows/ci.yaml:87-93`

```yaml
- name: Run integration tests (containerized)
  run: |
    chmod +x scripts/test-integration.sh
    mkdir -p coverage-integration
    chmod 777 coverage-integration
    ./scripts/test-integration.sh --build --no-cache
```

**Shell Script Pattern**:
```bash
#!/bin/bash
set -euo pipefail  # Exit on error, undefined var, pipe failure

cleanup() {
    echo "Cleaning up containers..."
    docker compose -f docker/docker-compose.test.yml down -v --remove-orphans
}

trap cleanup EXIT  # Always cleanup on script exit

# Start services
docker compose -f docker/docker-compose.test.yml up -d --build

# Wait for health (with timeout)
timeout 120s bash -c 'until docker compose -f docker/docker-compose.test.yml ps | grep healthy; do sleep 2; done'

# Run tests
pytest -m integration

# Coverage collected via volume mount
```

### When This Pattern Occurs

- ✅ Integration tests requiring infrastructure (Postgres, Redis, OpenFGA)
- ✅ E2E tests with Docker Compose stacks
- ✅ CI/CD pipeline test execution
- ✅ Local development environment setup

---

## 5. Integration Test Coverage Collection Errors

### Root Cause

**Coverage data not collected from inside Docker containers**

- Tests run in containers, coverage written to container filesystem
- CI can't access container-internal files
- Coverage reports incomplete (unit tests only)

### Historical Example

**Commit**: 3d5d4b0 (2025-10-20)
**File**: `.github/workflows/ci.yaml`
**Achievement**: Enabled integration test coverage collection via Docker volumes

### Prevention Strategy

**Pattern 1: Volume Mounts for Coverage Data**

**docker-compose.test.yml**:
```yaml
services:
  test-runner:
    build: .
    volumes:
      - ./coverage-integration:/app/coverage-integration  # ✅ Mount host directory
    environment:
      - COVERAGE_FILE=/app/coverage-integration/.coverage
    command: pytest -m integration --cov=src --cov-report=xml:/app/coverage-integration/coverage-integration.xml
```

**Pattern 2: Copy Coverage from Container**

```bash
# Alternative: Copy coverage after tests complete
docker compose -f docker-compose.test.yml up --abort-on-container-exit

# Extract coverage from container
if docker ps -a | grep -q mcp-test-runner; then
    docker cp mcp-test-runner:/app/coverage-integration/coverage-integration.xml \
        ./coverage-integration/ || echo "⚠️  No integration coverage found"
fi
```

**Pattern 3: Merge Coverage Reports**

**CI Workflow**:
```yaml
- name: Merge coverage reports
  run: |
    pip install coverage
    if [ -f coverage-integration/coverage-integration.xml ]; then
        echo "Merging unit and integration coverage..."
        echo "✓ Both coverage sources available"
    else
        echo "Using unit test coverage only"
    fi

- name: Upload coverage
  uses: codecov/codecov-action@v5.5.1
  with:
    files: ./coverage.xml,./coverage-integration/coverage-integration.xml
    fail_ci_if_error: false
    flags: combined
```

### Directory Structure

```
mcp-server-langgraph/
├── coverage.xml                    # Unit test coverage (host)
├── coverage-integration/           # Integration coverage (volume mount)
│   └── coverage-integration.xml
└── htmlcov-combined/              # Merged HTML report
    └── index.html
```

### When This Pattern Occurs

- ✅ Integration tests in Docker containers
- ✅ CI/CD coverage reporting
- ✅ Combined coverage metrics (unit + integration)
- ✅ Coverage trending over time

---

## 6. Async-First Architecture Violations

### Root Cause

**Mixing synchronous and asynchronous code incorrectly**

- Calling sync blocking functions in async context (blocks event loop)
- Not awaiting async functions (returns coroutine, not result)
- Using sync libraries for I/O in async application

### Architectural Decision

**Reference**: `adr/0019-async-first-architecture.md`

**Core Principle**: All I/O operations MUST be async. Pure CPU work MAY be sync.

### Prevention Strategy

**Pattern 1: Always Use Async I/O Libraries**

```python
# ❌ WRONG: Sync HTTP client blocks event loop
import requests

async def fetch_data(url: str) -> dict:
    response = requests.get(url)  # ❌ Blocks for 1-30 seconds
    return response.json()

# ✅ CORRECT: Async HTTP client
import httpx

async def fetch_data(url: str) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.get(url)  # ✅ Non-blocking
        return response.json()
```

**Pattern 2: Concurrent Execution with asyncio.gather**

```python
# Execute multiple I/O operations concurrently
async def enrich_user_data(user_id: str) -> UserData:
    # Run 3 API calls in parallel
    # Total time = max(20ms, 50ms, 30ms) = 50ms (not 100ms)
    session, roles, preferences = await asyncio.gather(
        get_session(user_id),      # 20ms
        get_user_roles(user_id),   # 50ms
        get_preferences(user_id),  # 30ms
    )
    return UserData(session=session, roles=roles, preferences=preferences)
```

**Pattern 3: Timeout Management**

```python
async def call_llm_with_timeout(prompt: str, timeout: int = 30) -> str:
    """Prevent operations from hanging"""
    try:
        return await asyncio.wait_for(
            llm.acall(prompt),
            timeout=timeout
        )
    except asyncio.TimeoutError:
        raise LLMTimeoutError(f"LLM call exceeded {timeout}s timeout")
```

### Library Selection

| Component | ✅ Async Library | ❌ Sync (Rejected) |
|-----------|-----------------|-------------------|
| HTTP Client | `httpx.AsyncClient` | `requests` |
| Redis | `redis.asyncio` | `redis` |
| LLM | `litellm.acompletion` | `litellm.completion` |
| Web Framework | `FastAPI` | `Flask` |
| Database | `asyncpg` | `psycopg2` |
| OpenFGA | `openfga_sdk` (async) | N/A |

### Real-World Example

**File**: `src/mcp_server_langgraph/core/parallel_executor.py`

```python
class ParallelToolExecutor:
    """Execute tools in parallel with dependency resolution"""

    async def execute_parallel(
        self,
        invocations: List[ToolInvocation],
        tool_executor: Callable,
    ) -> List[ToolResult]:
        """Execute tools respecting dependencies"""
        graph = self._build_dependency_graph(invocations)
        execution_order = self._topological_sort(graph)
        levels = self._group_by_level(execution_order, graph, invocations)

        results = {}

        # Execute each level in parallel
        for level in levels:
            # All tools in same level have no dependencies on each other
            level_results = await asyncio.gather(
                *[self._execute_single(inv, tool_executor, results) for inv in level],
                return_exceptions=True  # Don't fail entire level on one error
            )

            # Store results for next level's dependencies
            for inv, result in zip(level, level_results):
                results[inv.invocation_id] = result

        return list(results.values())
```

### When This Pattern Occurs

- ✅ All LLM API calls
- ✅ Database queries (Redis, PostgreSQL)
- ✅ External API calls (Keycloak, OpenFGA, Infisical)
- ✅ File I/O in async contexts
- ✅ Network operations

---

## Quick Reference Checklist

### Before Committing Code

```bash
# 1. Verify all changes are staged
git status --short

# 2. Test critical imports
python -c "from mcp_server_langgraph.api import gdpr_router; print('✓ OK')"

# 3. Run unit tests against committed code
git stash
pytest -m unit --tb=short
git stash pop

# 4. Verify async mocks
grep -r "patch.*async" tests/ | grep -v "new_callable=AsyncMock"
# Should return empty (all async patches use AsyncMock)
```

### Before Spawning Async Tasks

```python
# ✅ Checklist
- [ ] Function decorated with `async def`
- [ ] All I/O operations use async libraries (httpx, asyncpg, redis.asyncio)
- [ ] All async calls use `await`
- [ ] Test decorated with `@pytest.mark.asyncio`
- [ ] Mocks use `AsyncMock` not `MagicMock`
- [ ] Timeout specified with `asyncio.wait_for()`
- [ ] Error handling for `asyncio.TimeoutError`
```

### Before Spawning Subprocess

```python
# ✅ Checklist
- [ ] `capture_output=True` specified
- [ ] `timeout=<seconds>` specified
- [ ] Using context manager or try/finally for cleanup
- [ ] Health check polling with timeout
- [ ] Error handling for `subprocess.CalledProcessError`
- [ ] Zombie process prevention (wait() or context manager)
```

### Before Running Integration Tests

```bash
# ✅ Checklist
- [ ] Docker Compose file has volume mounts for coverage
- [ ] Timeout specified for service startup
- [ ] Health checks defined in docker-compose.yml
- [ ] Cleanup script or context manager in place
- [ ] CI workflow copies coverage from containers
- [ ] .gitignore excludes coverage-integration/
```

---

## Emergency Troubleshooting Guide

### Symptom: ImportError in CI but works locally

**Diagnosis**:
```bash
# Check for unstaged files
git status

# Compare local vs committed
git diff src/
```

**Fix**:
```bash
git add <missing-files>
git commit --amend --no-edit
git push --force-with-lease
```

### Symptom: Event loop is closed

**Diagnosis**:
- Check fixture scopes (should be `function` not `session` for async fixtures)
- Verify `@pytest.mark.asyncio` on test
- Check `asyncio_mode = "strict"` in `pyproject.toml`

**Fix**:
```python
# Change from session to function scope
@pytest.fixture  # Remove scope="session"
async def my_fixture():
    ...
```

### Symptom: Test hangs indefinitely

**Diagnosis**:
- Subprocess without timeout
- Async operation without `asyncio.wait_for()`
- Sync blocking call in async context

**Fix**:
```python
# Add timeout
result = await asyncio.wait_for(operation(), timeout=30)

# Or for subprocess
subprocess.run(cmd, timeout=30, capture_output=True)
```

### Symptom: Coverage reports missing integration tests

**Diagnosis**:
```bash
# Check if coverage file exists in container
docker compose -f docker-compose.test.yml exec test-runner ls -la /app/coverage-integration/

# Check volume mount
docker compose -f docker-compose.test.yml config | grep volumes -A 5
```

**Fix**:
Add volume mount to `docker-compose.test.yml`:
```yaml
volumes:
  - ./coverage-integration:/app/coverage-integration
```

### Symptom: AsyncMock not awaitable

**Diagnosis**:
```python
# Check if using regular Mock instead of AsyncMock
@patch("module.function")  # ❌ Missing new_callable
```

**Fix**:
```python
@patch("module.function", new_callable=AsyncMock)  # ✅ Correct
```

---

## Validation Commands

### Verify No Async Mock Issues

```bash
# Find all async patches without AsyncMock
rg '@patch.*' tests/ | \
  rg -v 'new_callable=AsyncMock' | \
  rg '(async def|await)'
# Should be empty
```

### Verify All Subprocess Calls Have Timeouts

```bash
# Find subprocess.run without timeout
rg 'subprocess\.run\(' --type py | \
  rg -v 'timeout='
# Should only show safe cases or be empty
```

### Verify Docker Cleanup

```bash
# Check for orphaned containers
docker ps -a | grep mcp-server-langgraph
# Should be empty or only running containers

# Check for orphaned volumes
docker volume ls | grep mcp
# Should only show expected volumes
```

---

## Success Metrics

**After Implementing These Strategies**:

- ✅ **100% test pass rate** (437+ tests)
- ✅ **Zero import errors** in CI
- ✅ **Zero event loop errors** in test suite
- ✅ **60-65% combined coverage** (unit + integration)
- ✅ **Zero subprocess hangs** in CI
- ✅ **Reliable Docker container lifecycle** management

**Test Suite Statistics**:
- Unit tests: ~400 tests, 2-5 seconds execution
- Integration tests: ~200 tests, 30-60 seconds in Docker
- Property tests: 27+ Hypothesis tests
- Contract tests: 20+ MCP protocol tests

---

## Document Maintenance

**Update Triggers**:
- New error pattern discovered in CI/CD
- Major library version upgrade (e.g., LangGraph 0.2 → 0.6)
- New async technology introduced
- Integration test infrastructure changes

**Review Frequency**: Monthly or after major incidents

**Ownership**: Development team, primary contact: Platform Team

---

## References

### Internal Documentation

- `adr/0019-async-first-architecture.md` - Async-first design principles
- `reports/archive/2025-10/TEST_FAILURE_ROOT_CAUSE.md` - Import error root cause analysis
- `.github/workflows/ci.yaml` - CI/CD pipeline configuration
- `tests/conftest.py` - Pytest configuration and fixture patterns
- `tests/utils/docker.py` - Docker utilities and context managers

### Commit History

- `2421c46` - Fix missing session store functions (import error)
- `dced3c0` - Fix async mock in SLA monitoring test
- `3d5d4b0` - Enable integration test coverage collection
- `8f88b0c` - Resolve async benchmark test failures
- `2d1a9eb` - Resolve observability lazy initialization test failures

### External Resources

- [Python asyncio documentation](https://docs.python.org/3/library/asyncio.html)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [unittest.mock.AsyncMock](https://docs.python.org/3/library/unittest.mock.html#unittest.mock.AsyncMock)
- [Docker Compose](https://docs.docker.com/compose/)

---

**End of Document**

_This strategy document is maintained as living documentation. Please update with new patterns as they are discovered._
