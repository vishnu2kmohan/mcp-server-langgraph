# Pytest-xdist Best Practices for FastAPI Testing

## Overview

This document outlines best practices for writing tests that work correctly with `pytest-xdist` (parallel test execution). Following these practices prevents intermittent test failures and ensures reliable test execution.

## Background: The Bug We Fixed (Commit 079e82e)

### The Problem

In commit `079e82e`, we fixed a critical bug where API endpoint tests were failing intermittently with **401 Unauthorized errors** when run with `pytest -n auto` (parallel execution).

**Root Cause**: Async FastAPI dependencies were being overridden with **sync lambda functions** instead of **async functions**, causing FastAPI to ignore the override in pytest-xdist workers.

```python
# ❌ INCORRECT (caused intermittent 401 failures)
async def get_current_user():  # Async dependency
    ...

app.dependency_overrides[get_current_user] = lambda: {"user_id": "test"}  # Sync lambda
```bash
```python
# ✅ CORRECT (fix from commit 079e82e)
async def get_current_user():  # Async dependency
    ...

async def mock_get_current_user_async():  # Async override
    return {"user_id": "test"}

app.dependency_overrides[get_current_user] = mock_get_current_user_async
```

### Why It Only Failed in Pytest-xdist

- **Isolation**: Works correctly when run with `pytest -xvs` (single process)
- **Intermittent**: Fails randomly when run with `pytest -n auto` (parallel workers)
- **Reason**: FastAPI's dependency injection system checks function signatures at import time, and pytest-xdist workers may cache or share module state differently

## ⚠️ CRITICAL: Module-Level Singleton Issue (bearer_scheme)

### The Second Bug We Fixed (Latest)

After fixing the async/sync mismatch bug, we discovered **another critical issue** causing intermittent 401 errors in pytest-xdist:

**Root Cause**: Module-level `bearer_scheme` singleton in `auth/middleware.py:816`

```python
# In auth/middleware.py (production code)
bearer_scheme = HTTPBearer(auto_error=False)  # MODULE-LEVEL SINGLETON!

async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),  # Uses singleton
) -> Dict[str, Any]:
    ...
```

**Problem**: Even when overriding `get_current_user`, the nested `bearer_scheme` dependency is NOT overridden, causing test pollution across pytest-xdist workers.

**The Fix**: Override BOTH `get_current_user` AND `bearer_scheme`:

```python
from mcp_server_langgraph.auth.middleware import bearer_scheme, get_current_user

# CRITICAL: Must override bearer_scheme to prevent singleton pollution
app.dependency_overrides[bearer_scheme] = lambda: None
app.dependency_overrides[get_current_user] = mock_get_current_user_async
```

**Why This Matters**:
- Test execution order in pytest-xdist is non-deterministic
- If TestAPIKeyEndpointAuthorization (no auth) runs before TestCreateAPIKey (mocked auth) on same worker
- The bearer_scheme singleton gets "primed" with no-credentials state
- Subsequent tests fail with 401 even though get_current_user is overridden

##  Core Principles

### 1. Override ALL Nested Dependencies

**Rule**: When overriding a dependency that has nested `Depends()`, override ALL levels.

```python
# ❌ WRONG: Only overrides top-level dependency
app.dependency_overrides[get_current_user] = mock_user

# ✅ CORRECT: Overrides BOTH top-level AND nested dependencies
app.dependency_overrides[bearer_scheme] = lambda: None  # Nested dependency
app.dependency_overrides[get_current_user] = mock_user  # Top-level dependency
```

### 2. Match Async/Sync Signatures

**Rule**: Dependency override MUST match the original function's async/sync signature.

| Original Dependency | Override Function | Status |
|---------------------|-------------------|--------|
| `async def get_user()` | `async def mock_user()` | ✅ Correct |
| `async def get_user()` | `def mock_user()` | ❌ Wrong |
| `async def get_user()` | `lambda: {...}` | ❌ Wrong |
| `def get_manager()` | `def mock_manager()` | ✅ Correct |
| `def get_manager()` | `lambda: ...` | ✅ OK (both sync) |

### 2. Always Clean Up Dependency Overrides

**Rule**: Clear `app.dependency_overrides` in fixture teardown to prevent state pollution.

```python
@pytest.fixture
def test_client(mock_current_user):
    from fastapi import FastAPI
    from mcp_server_langgraph.api.api_keys import router
    from mcp_server_langgraph.auth.middleware import get_current_user

    app = FastAPI()
    app.include_router(router)

    async def mock_get_current_user_async():
        return mock_current_user

    app.dependency_overrides[get_current_user] = mock_get_current_user_async

    yield TestClient(app)

    # ✅ REQUIRED: Clear overrides to prevent pollution
    app.dependency_overrides.clear()
```python
### 3. Use `@pytest.mark.xdist_group` for Related Tests

**Rule**: Group related tests to run in the same pytest-xdist worker.

```python
@pytest.mark.unit
@pytest.mark.api
@pytest.mark.xdist_group(name="api_keys_api_tests")  # ✅ Group tests together
class TestCreateAPIKey:
    """All tests in this class run in the same worker"""

    def test_create_api_key_success(self, test_client):
        ...

    def test_create_api_key_custom_expiration(self, test_client):
        ...
```

**Why**: Ensures tests that share fixtures or state run sequentially in the same worker, preventing race conditions.

### 4. Force Garbage Collection in Teardown

**Rule**: Call `gc.collect()` in `teardown_method()` to prevent mock accumulation.

```python
import gc

@pytest.mark.xdist_group(name="test_group")
class TestSomething:
    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()
```python
**Why**: Pytest-xdist workers can accumulate `AsyncMock` and `MagicMock` objects, leading to memory leaks. See `tests/MEMORY_SAFETY_GUIDELINES.md`.

## Complete Example: Correct Pattern

Here's a complete example of a correctly written test fixture for FastAPI endpoints:

```python
import gc
from unittest.mock import AsyncMock
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.fixture
def mock_api_key_manager():
    """Mock APIKeyManager for testing"""
    manager = AsyncMock()
    manager.create_api_key.return_value = {
        "key_id": "key_12345",
        "api_key": "mcp_test_key",
        "name": "Test Key",
    }
    return manager


@pytest.fixture
def mock_keycloak_client():
    """Mock KeycloakClient for testing"""
    client = AsyncMock()
    client.issue_token_for_user.return_value = {
        "access_token": "test_token",
        "expires_in": 900,
    }
    return client


@pytest.fixture
def mock_current_user():
    """Shared mock current user fixture"""
    return {
        "user_id": "user:alice",
        "keycloak_id": "00000000-0000-0000-0000-000000000000",  # gitleaks:allow
        "username": "alice",
        "email": "alice@example.com",
    }


@pytest.fixture(scope="function")
def api_keys_test_client(mock_api_key_manager, mock_keycloak_client, mock_current_user):
    """FastAPI TestClient with mocked dependencies for API endpoints"""
    from fastapi import FastAPI

    from mcp_server_langgraph.api.api_keys import router
    from mcp_server_langgraph.auth.middleware import bearer_scheme, get_current_user
    from mcp_server_langgraph.core.dependencies import (
        get_api_key_manager,
        get_keycloak_client,
    )

    app = FastAPI()

    # ✅ CORRECT: Async override for async dependency
    async def mock_get_current_user_async():
        return mock_current_user

    # ✅ CORRECT: Sync overrides for sync dependencies
    def mock_get_api_key_manager_sync():
        return mock_api_key_manager

    def mock_get_keycloak_client_sync():
        return mock_keycloak_client

    # ✅ CRITICAL: Override bearer_scheme to prevent module-level singleton pollution
    app.dependency_overrides[bearer_scheme] = lambda: None
    app.dependency_overrides[get_api_key_manager] = mock_get_api_key_manager_sync
    app.dependency_overrides[get_keycloak_client] = mock_get_keycloak_client_sync
    app.dependency_overrides[get_current_user] = mock_get_current_user_async

    # Include router AFTER setting overrides
    app.include_router(router)

    client = TestClient(app)

    yield client

    # ✅ REQUIRED: Cleanup to prevent state pollution
    app.dependency_overrides.clear()


@pytest.mark.unit
@pytest.mark.api
@pytest.mark.xdist_group(name="api_keys_api_tests")
class TestCreateAPIKey:
    """Tests for POST /api/v1/api-keys/"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_create_api_key_success(self, api_keys_test_client, mock_api_key_manager):
        """Test successful API key creation"""
        response = api_keys_test_client.post(
            "/api/v1/api-keys/",
            json={"name": "Test Key", "expires_days": 365},
        )

        assert response.status_code == 201
        data = response.json()
        assert "key_id" in data
        assert "api_key" in data
```

## Common Pitfalls and How to Avoid Them

### Pitfall 1: Using Sync Lambda for Async Dependency

```python
# ❌ WRONG: Will fail intermittently in pytest-xdist
async def get_current_user():
    ...

app.dependency_overrides[get_current_user] = lambda: {"user_id": "test"}
```bash
**Fix**:
```python
# ✅ CORRECT: Use async function
async def mock_get_current_user_async():
    return {"user_id": "test"}

app.dependency_overrides[get_current_user] = mock_get_current_user_async
```

### Pitfall 2: Forgetting to Clear Overrides

```python
# ❌ WRONG: State pollution across tests
@pytest.fixture
def test_client():
    app.dependency_overrides[dep] = mock
    yield TestClient(app)
    # Missing cleanup!
```bash
**Fix**:
```python
# ✅ CORRECT: Always clear overrides
@pytest.fixture
def test_client():
    app.dependency_overrides[dep] = mock
    yield TestClient(app)
    app.dependency_overrides.clear()  # ✅ Cleanup
```

### Pitfall 3: Not Using xdist_group for Related Tests

```python
# ❌ WRONG: Tests may run in different workers
class TestAPIKeys:
    def test_create(self):
        ...

    def test_list(self):
        ...
```bash
**Fix**:
```python
# ✅ CORRECT: Group related tests
@pytest.mark.xdist_group(name="api_keys_tests")
class TestAPIKeys:
    def test_create(self):
        ...

    def test_list(self):
        ...
```

### Pitfall 4: Memory Leaks from AsyncMock

```python
# ❌ WRONG: Mocks accumulate in xdist workers
class TestAPIKeys:
    def test_something(self):
        mock = AsyncMock()
        ...
```bash
**Fix**:
```python
# ✅ CORRECT: Force GC in teardown
import gc

class TestAPIKeys:
    def teardown_method(self):
        gc.collect()

    def test_something(self):
        mock = AsyncMock()
        ...
```

## Testing Your Tests for Pytest-xdist Compatibility

### Run Tests in Parallel Multiple Times

```bash
# Run tests 10 times in parallel to catch intermittent failures
for i in {1..10}; do
    echo "Run $i"
    pytest -n auto tests/api/test_api_keys_endpoints.py
done
```bash
### Check for Consistent Worker Assignment

```bash
# Verify tests in same xdist_group run in same worker
pytest -n 8 -v tests/api/test_api_keys_endpoints.py | grep -E "\[gw[0-9]\]"
```

All tests in the same class should show the same `[gwX]` prefix.

### Monitor Memory Usage

```bash
# Check for memory leaks during parallel execution
pytest -n auto tests/ --memcheck
```bash
## Debugging Pytest-xdist Issues

### Enable Verbose Output

```bash
# See which worker runs each test
pytest -n auto -v tests/api/
```

### Run Without Parallel Execution

```bash
# Compare results with/without pytest-xdist
pytest -xvs tests/api/test_api_keys_endpoints.py  # Single process
pytest -n 8 tests/api/test_api_keys_endpoints.py   # Parallel
```bash
### Check for State Pollution

```bash
# Run tests in different orders
pytest -n auto --random-order tests/api/
```

## Worker-Scoped Resource Isolation

### Overview

To enable safe parallel test execution, our test infrastructure uses **worker-scoped resources**.
Each pytest-xdist worker (gw0, gw1, gw2, etc.) gets its own isolated resources to prevent
conflicts and race conditions.

### Worker-Aware Port Allocation

**Problem**: Multiple workers starting docker-compose with same ports causes "address already in use" errors.

**Solution**: Dynamic port offsets per worker.

```python
# tests/conftest.py:test_infrastructure_ports
def test_infrastructure_ports():
    worker_id = os.getenv("PYTEST_XDIST_WORKER", "gw0")
    worker_num = int(worker_id.replace("gw", ""))
    port_offset = worker_num * 100  # gw0=0, gw1=100, gw2=200

    return {
        "postgres": 9432 + port_offset,  # gw0:9432, gw1:9532, gw2:9632
        "redis": 9379 + port_offset,
        # ... other ports
    }
```

**Result**: Each worker can start docker-compose without conflicts.

### Worker-Scoped PostgreSQL Schemas

**Problem**: Multiple workers using `TRUNCATE TABLE` on shared connection causes data loss.

**Solution**: Each worker gets its own PostgreSQL schema.

```python
# tests/conftest.py:postgres_connection_clean
async def postgres_connection_clean(postgres_connection_real):
    worker_id = os.getenv("PYTEST_XDIST_WORKER", "gw0")
    schema_name = f"test_worker_{worker_id}"  # test_worker_gw0, test_worker_gw1, etc.

    # Create and use worker-scoped schema
    await postgres_connection_real.execute(f"CREATE SCHEMA IF NOT EXISTS {schema_name}")
    await postgres_connection_real.execute(f"SET search_path TO {schema_name}, public")

    yield postgres_connection_real

    # Cleanup: Drop schema (safe, isolated)
    await postgres_connection_real.execute(f"DROP SCHEMA IF EXISTS {schema_name} CASCADE")
```

**Result**: Worker gw0's TRUNCATE doesn't affect worker gw1's data.

### Worker-Scoped Redis DB Indexes

**Problem**: Multiple workers using `FLUSHDB` on shared Redis instance wipes all data.

**Solution**: Each worker gets its own Redis database index.

```python
# tests/conftest.py:redis_client_clean
async def redis_client_clean(redis_client_real):
    worker_id = os.getenv("PYTEST_XDIST_WORKER", "gw0")
    worker_num = int(worker_id.replace("gw", ""))
    db_index = worker_num + 1  # gw0→DB1, gw1→DB2, etc. (DB0 reserved)

    # Select worker-scoped database
    await redis_client_real.select(db_index)

    yield redis_client_real

    # Cleanup: FLUSHDB (safe, isolated)
    await redis_client_real.flushdb()
```

**Result**: Worker gw0's FLUSHDB doesn't affect worker gw1's data. Supports up to 15 workers (Redis has 16 DBs).

### Worker Utility Functions

Use the worker utility library for consistent worker-scoped resources:

```python
from tests.utils.worker_utils import (
    get_worker_id,           # → "gw0", "gw1", "gw2"
    get_worker_num,          # → 0, 1, 2
    get_worker_port_offset,  # → 0, 100, 200
    get_worker_postgres_schema,  # → "test_worker_gw0"
    get_worker_redis_db,     # → 1, 2, 3
    worker_tmp_path,         # → Worker-scoped temp directories
)

# Example usage
worker_id = get_worker_id()  # "gw0"
schema = get_worker_postgres_schema()  # "test_worker_gw0"
ports_offset = get_worker_port_offset()  # 0
```

### Infrastructure Tests

For tests that use docker-compose or other heavy infrastructure:

```python
@pytest.mark.infrastructure
@pytest.mark.xdist_group(name="infra_docker_compose")
class TestMyInfrastructure:
    """Tests requiring docker-compose services"""
    pass
```

**Run Strategy:**
```bash
# Run unit tests in parallel (fast)
pytest -n auto -m "not infrastructure" tests/

# Run infrastructure tests serially or limited workers (safer)
pytest -n0 -m infrastructure tests/
# OR
pytest -n2 -m infrastructure tests/  # Limit workers for infra tests
```

## References

- **Async/Sync Fix**: Commit `079e82e` - Async/sync dependency override mismatch
- **Worker Isolation Fix**: Commit `8259c81` - Complete pytest-xdist isolation
- **Architecture Decision**: `adr/adr-0052-pytest-xdist-isolation-strategy.md`
- **Regression Tests**: `tests/regression/test_pytest_xdist_*.py`
- **Worker Utilities**: `tests/utils/worker_utils.py`
- **Memory Safety**: `tests/MEMORY_SAFETY_GUIDELINES.md`
- **FastAPI Testing**: https://fastapi.tiangolo.com/tutorial/testing/
- **Pytest-xdist**: https://pytest-xdist.readthedocs.io/

## Summary Checklist

Before committing test code that uses FastAPI dependency overrides:

- [ ] Async dependencies overridden with async functions (not lambdas)
- [ ] Sync dependencies can use sync functions or lambdas
- [ ] `app.dependency_overrides.clear()` called in fixture teardown
- [ ] `@pytest.mark.xdist_group` used for related tests
- [ ] `gc.collect()` called in `teardown_method()` if using mocks
- [ ] Tests pass consistently when run 10+ times with `pytest -n auto`
- [ ] All tests in same class run in same worker (check `[gwX]` prefix)
- [ ] No memory leaks observed during parallel execution

By following these practices, you'll ensure your tests work reliably in both single-process and parallel execution modes.
