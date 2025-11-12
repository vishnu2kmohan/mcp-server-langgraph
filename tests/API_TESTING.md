# API Testing Guide

Comprehensive guide for testing FastAPI endpoints with proper dependency injection and mocking.

## Table of Contents
1. [Common Issues and Solutions](#common-issues-and-solutions)
2. [FastAPI Dependency Override Patterns](#fastapi-dependency-override-patterns)
3. [Test Client Setup Checklist](#test-client-setup-checklist)
4. [Examples](#examples)
5. [Troubleshooting](#troubleshooting)

---

## Common Issues and Solutions

### Issue 1: Getting 401 Unauthorized in Tests

**Symptom**: Test expects 200/404/403/500 but gets 401 Unauthorized

**Root Cause**: Missing dependency override in FastAPI TestClient fixture

**Example Error**:
```python
# Test expects 200 OK
assert response.status_code == status.HTTP_200_OK
# But gets 401
# AssertionError: assert 401 == 200
```

**Solution**: Ensure ALL endpoint dependencies are overridden

```python
# ❌ BAD: Missing get_openfga_client override
@pytest.fixture
def test_client(mock_sp_manager, mock_current_user):
    app.dependency_overrides[get_service_principal_manager] = lambda: mock_sp_manager
    app.dependency_overrides[get_current_user] = lambda: mock_current_user
    # MISSING: get_openfga_client override!
    return TestClient(app)

# ✅ GOOD: All dependencies overridden
@pytest.fixture
def test_client(mock_sp_manager, mock_current_user, mock_openfga_client):
    app.dependency_overrides[get_service_principal_manager] = lambda: mock_sp_manager
    app.dependency_overrides[get_current_user] = lambda: mock_current_user
    app.dependency_overrides[get_openfga_client] = lambda: mock_openfga_client
    return TestClient(app)
```

**Prevention**: Use `verify_dependency_overrides()` from `tests/utils/mock_factories.py`

**Reference**:
- Fixed: `tests/api/test_service_principals_endpoints.py` (4 tests)
- Root cause analysis: Missing OpenFGA dependency override

---

### Issue 2: Async/Sync Dependency Mismatch

**Symptom**: Dependency override silently ignored, endpoint uses real dependency

**Root Cause**: Override function doesn't match async/sync of original dependency

**Example Error**:
```python
# Endpoint dependency is async
async def get_current_user() -> Dict[str, Any]:
    ...

# ❌ BAD: Sync override for async dependency
def mock_get_current_user_sync():  # Wrong!
    return {"user_id": "test"}

app.dependency_overrides[get_current_user] = mock_get_current_user_sync
# FastAPI will IGNORE this override in pytest-xdist!
```

**Solution**: Match async/sync signature of original dependency

```python
# ✅ GOOD: Async override for async dependency
async def mock_get_current_user_async():
    return {"user_id": "test"}

app.dependency_overrides[get_current_user] = mock_get_current_user_async
```

**Critical Dependencies and Their Signatures**:

| Dependency | Type | Returns |
|-----------|------|---------|
| `get_current_user` | **async** | `Dict[str, Any]` |
| `get_service_principal_manager` | **sync** | `ServicePrincipalManager` |
| `get_openfga_client` | **sync** | `Optional[OpenFGAClient]` |
| `get_keycloak_client` | **sync** | `KeycloakClient` |
| `get_api_key_manager` | **sync** | `APIKeyManager` |

**Reference**:
- `tests/api/test_service_principals_endpoints.py:117-140`
- Comment: "Using wrong async/sync causes FastAPI to ignore override in pytest-xdist"

---

## FastAPI Dependency Override Patterns

### Pattern 1: Complete Test Client Fixture

```python
import gc
from unittest.mock import AsyncMock
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

@pytest.fixture
def mock_openfga_client():
    """Mock OpenFGA client for authorization checks"""
    from tests.utils.mock_factories import create_mock_openfga_client
    return create_mock_openfga_client(authorized=True)

@pytest.fixture
def test_client(mock_sp_manager, mock_current_user, mock_openfga_client):
    """FastAPI TestClient with all required dependencies"""
    from fastapi import FastAPI
    from mcp_server_langgraph.api.service_principals import router
    from mcp_server_langgraph.auth.middleware import get_current_user
    from mcp_server_langgraph.core.dependencies import (
        get_openfga_client,
        get_service_principal_manager,
    )

    app = FastAPI()
    app.include_router(router)

    # Override dependencies - MUST match async/sync of originals!
    async def mock_get_current_user_async():
        return mock_current_user

    def mock_get_sp_manager_sync():
        return mock_sp_manager

    def mock_get_openfga_sync():
        return mock_openfga_client

    app.dependency_overrides[get_service_principal_manager] = mock_get_sp_manager_sync
    app.dependency_overrides[get_current_user] = mock_get_current_user_async
    app.dependency_overrides[get_openfga_client] = mock_get_openfga_sync

    yield TestClient(app)

    # Cleanup to prevent state pollution in xdist workers
    app.dependency_overrides.clear()


@pytest.mark.xdist_group(name="api_tests")  # Isolate API tests in xdist
class TestMyEndpoint:
    def teardown_method(self):
        """Force GC to prevent mock accumulation"""
        gc.collect()

    def test_endpoint(self, test_client):
        response = test_client.post("/api/endpoint")
        assert response.status_code == 200
```

### Pattern 2: Using Shared Fixtures

```python
from tests.fixtures.api_fixtures import mock_openfga_client, create_api_test_client

@pytest.fixture
def test_client(mock_openfga_client):
    """Simpler setup using shared fixtures"""
    from mcp_server_langgraph.api.my_router import router
    from mcp_server_langgraph.core.dependencies import get_openfga_client

    return create_api_test_client(
        router=router,
        dependency_overrides={
            get_openfga_client: lambda: mock_openfga_client,
        },
    )
```

---

## Test Client Setup Checklist

Before writing API endpoint tests, verify:

- [ ] **All endpoint dependencies are identified**
  - Check endpoint function signature for all `Depends(...)` parameters
  - Include transitive dependencies (dependencies of dependencies)

- [ ] **All dependencies are mocked in fixture**
  - Each dependency has a mock fixture created
  - Each dependency override is added to `app.dependency_overrides`

- [ ] **Async/sync signatures match**
  - Async dependencies have async override functions
  - Sync dependencies have sync override functions

- [ ] **xdist group is specified**
  - Add `@pytest.mark.xdist_group(name="...")` to test class
  - Group related tests together for better performance

- [ ] **Cleanup is configured**
  - `app.dependency_overrides.clear()` in fixture teardown
  - `teardown_method()` with `gc.collect()` in test class

- [ ] **Memory safety (if using AsyncMock)**
  - Test class has `teardown_method()` with `gc.collect()`
  - Test class has `@pytest.mark.xdist_group` marker
  - See: `tests/MEMORY_SAFETY_GUIDELINES.md`

---

## Examples

### Example 1: Service Principal Endpoint Test

```python
# tests/api/test_service_principals_endpoints.py

@pytest.fixture
def mock_openfga_client():
    """Mock OpenFGA client for authorization"""
    mock_client = AsyncMock()
    mock_client.check_permission = AsyncMock(return_value=True)
    return mock_client

@pytest.fixture
def test_client(mock_sp_manager, mock_current_user, mock_openfga_client):
    """Complete test client with all dependencies"""
    from fastapi import FastAPI
    from mcp_server_langgraph.api.service_principals import router
    from mcp_server_langgraph.auth.middleware import get_current_user
    from mcp_server_langgraph.core.dependencies import (
        get_openfga_client,
        get_service_principal_manager,
    )

    app = FastAPI()
    app.include_router(router)

    # Async override for async dependency
    async def mock_get_current_user_async():
        return mock_current_user

    # Sync overrides for sync dependencies
    def mock_get_sp_manager_sync():
        return mock_sp_manager

    def mock_get_openfga_sync():
        return mock_openfga_client

    app.dependency_overrides[get_service_principal_manager] = mock_get_sp_manager_sync
    app.dependency_overrides[get_current_user] = mock_get_current_user_async
    app.dependency_overrides[get_openfga_client] = mock_get_openfga_sync

    yield TestClient(app)
    app.dependency_overrides.clear()

@pytest.mark.xdist_group(name="service_principals_api")
class TestServicePrincipalEndpoint:
    def teardown_method(self):
        gc.collect()

    def test_create_endpoint(self, test_client):
        response = test_client.post("/api/v1/service-principals/", json={...})
        assert response.status_code == 200
```

### Example 2: Per-Test Mock Configuration

```python
def test_unauthorized_access(test_client, mock_openfga_client):
    """Test that unauthorized users get 403"""
    # Reconfigure mock for this specific test
    mock_openfga_client.check_permission.return_value = False

    response = test_client.post("/api/endpoint")
    assert response.status_code == 403
```

---

## Troubleshooting

### Problem: Test gets 401 even with dependency overrides

**Diagnosis**:
1. Check if endpoint has dependencies you missed
2. Verify async/sync match for all overrides
3. Add debug logging to see which dependency is failing

```python
# Add this to your test
import logging
logging.basicConfig(level=logging.DEBUG)

# Run single test with verbose output
pytest tests/api/test_file.py::test_name -vvs
```

### Problem: Dependency override works locally but fails in CI

**Cause**: pytest-xdist parallel execution exposes state pollution

**Solution**:
1. Add `@pytest.mark.xdist_group(name="...")` to test class
2. Ensure `app.dependency_overrides.clear()` in fixture cleanup
3. Add `teardown_method()` with `gc.collect()`

### Problem: Tests interfere with each other

**Cause**: Shared global state (singletons, circuit breakers, etc.)

**Solution**:
1. Use `reset_singleton_dependencies()` from `mcp_server_langgraph.core.dependencies`
2. Use dedicated xdist groups for tests with shared state
3. For circuit breaker tests: Use `@pytest.mark.skip_resilience_reset`

---

## Required Dependencies by Endpoint

### Service Principal Endpoints
```python
from mcp_server_langgraph.core.dependencies import (
    get_current_user,           # async - authentication
    get_service_principal_manager,  # sync - operations
    get_openfga_client,         # sync - authorization
)
```

### Auth Endpoints
```python
from mcp_server_langgraph.core.dependencies import (
    get_keycloak_client,        # sync - user auth
    get_api_key_manager,        # sync - API key validation
)
```

### Tool Endpoints
```python
from mcp_server_langgraph.core.dependencies import (
    get_current_user,           # async - authentication
    get_openfga_client,         # sync - authorization
)
```

---

## Keycloak Mocking for Contract Tests

**Context**: Contract tests validate router registration and API structure without testing authentication logic.

### Issue: Keycloak Connection Failures in CI

**Symptom**: Contract tests fail with `httpx.ConnectError: All connection attempts failed`

**Root Cause**: Tests import the production app which attempts to connect to Keycloak during initialization

**Example Failure**:
```python
# Contract test in tests/api/test_router_registration.py
def test_api_keys_create_endpoint_exists(test_client):
    response = test_client.post("/api/v1/api-keys/", json={"name": "test"})
    # FAILS: httpx.ConnectError - Keycloak not running in CI
```

### Solution: MCP_SKIP_AUTH Environment Variable

Use `monkeypatch.setenv("MCP_SKIP_AUTH", "true")` to bypass Keycloak initialization:

```python
@pytest.fixture
def test_client(monkeypatch):
    """
    FastAPI TestClient for contract tests with authentication bypassed.

    TDD Context:
    - RED: Tests failed with Keycloak connection errors in CI
    - GREEN: Set MCP_SKIP_AUTH=true to bypass auth during app import
    - REFACTOR: This pattern prevents external dependencies in contract tests

    The MCP_SKIP_AUTH environment variable must be set BEFORE importing
    the app, as Keycloak client initialization happens during module import.
    """
    # CRITICAL: Set env var BEFORE importing app
    monkeypatch.setenv("MCP_SKIP_AUTH", "true")

    # Now safe to import - Keycloak initialization will be skipped
    from mcp_server_langgraph.mcp.server_streamable import app

    return TestClient(app)
```

### Why This Works

1. **app module imports Keycloak client** during initialization
2. **Keycloak client checks MCP_SKIP_AUTH** before attempting connection
3. **If MCP_SKIP_AUTH=true**, Keycloak client returns mock/no-op instance
4. **Contract tests can run** without external Keycloak service

### When to Use This Pattern

✅ **Use MCP_SKIP_AUTH for**:
- Contract tests (router registration, OpenAPI schema)
- API structure tests (endpoint existence, HTTP methods)
- Tests validating response schemas (not authentication logic)

❌ **Don't use MCP_SKIP_AUTH for**:
- Authentication/authorization tests
- Integration tests requiring real Keycloak
- End-to-end tests with full auth flow

### Examples from This Project

**Contract Tests** (`tests/api/test_router_registration.py`):
```python
@pytest.fixture
def test_client(monkeypatch):
    monkeypatch.setenv("MCP_SKIP_AUTH", "true")
    from mcp_server_langgraph.mcp.server_streamable import app
    return TestClient(app)

class TestEndpointAccessibility:
    def test_api_keys_create_endpoint_exists(self, test_client):
        # Test only validates endpoint exists, not auth logic
        response = test_client.post("/api/v1/api-keys/", json={"name": "test"})
        assert response.status_code != 404  # Endpoint registered
```

**API Versioning Tests** (`tests/api/test_api_versioning.py`):
```python
@pytest.fixture
def test_client(monkeypatch):
    monkeypatch.setenv("MCP_SKIP_AUTH", "true")
    from mcp_server_langgraph.mcp.server_streamable import app
    return TestClient(app)

class TestVersionNegotiation:
    def test_version_header_accepted(self, test_client):
        # Test only validates version header handling
        response = test_client.get("/api/v1/api-keys/",
                                   headers={"X-API-Version": "1.0"})
        assert response.status_code != 400  # Header accepted
```

### Troubleshooting

**Issue**: Still getting Keycloak connection errors

**Check**:
1. Environment variable set BEFORE import: ✅ `monkeypatch.setenv()` before `from ... import app`
2. Variable name correct: ✅ `MCP_SKIP_AUTH` (not `SKIP_AUTH`)
3. Value is string "true": ✅ `"true"` (not boolean `True`)

**Issue**: Tests pass locally but fail in CI

**Cause**: Local environment has Keycloak running, CI doesn't

**Solution**: Always use `MCP_SKIP_AUTH` for contract tests to ensure CI consistency

### Related Issues Fixed

- **Quality Tests Workflow** (Run #19309378654): 5 contract test failures
  - `test_api_keys_create_endpoint_exists` ✅ Fixed
  - `test_api_keys_list_endpoint_exists` ✅ Fixed
  - `test_service_principals_list_endpoint_exists` ✅ Fixed
  - `test_version_header_accepted` ✅ Fixed
  - `test_unsupported_version_returns_error` ✅ Fixed

### References

- **Fixed Tests**: `tests/api/test_router_registration.py`, `tests/api/test_api_versioning.py`
- **CI Failure**: Quality Tests Workflow Run #19309378654
- **Commit**: b37d5f9 - "fix(ci): comprehensive remediation of CI/CD workflow failures"

---

## Best Practices

1. **Use reusable mock factories**
   - `from tests.utils.mock_factories import create_mock_openfga_client`
   - `from tests.fixtures.api_fixtures import mock_openfga_client`

2. **Always clean up overrides**
   ```python
   yield TestClient(app)
   app.dependency_overrides.clear()  # Essential for xdist!
   ```

3. **Group related tests**
   ```python
   @pytest.mark.xdist_group(name="my_api_tests")
   class TestMyAPI:
       ...
   ```

4. **Document required overrides**
   ```python
   @pytest.fixture
   def test_client(...):
       """
       TestClient with dependencies:
       - get_current_user (async)
       - get_openfga_client (sync)
       - get_sp_manager (sync)
       """
   ```

5. **Verify overrides are complete**
   ```python
   from tests.utils.mock_factories import verify_dependency_overrides

   verify_dependency_overrides(
       app.dependency_overrides,
       [get_current_user, get_openfga_client, get_sp_manager],
   )
   ```

---

## References

- **Test Utilities**: `tests/utils/mock_factories.py`
- **Shared Fixtures**: `tests/fixtures/api_fixtures.py`
- **Example Tests**: `tests/api/test_service_principals_endpoints.py`
- **Memory Safety**: `tests/MEMORY_SAFETY_GUIDELINES.md`
- **Fixture Organization**: See pre-commit hook `validate-fixture-organization`

---

## Changelog

### 2025-11-12: Added Keycloak Mocking Section
- Added comprehensive Keycloak mocking guide for contract tests
- Documented MCP_SKIP_AUTH environment variable pattern
- Fixed 5 contract test failures (Keycloak connection errors in CI)
- Added examples from `test_router_registration.py` and `test_api_versioning.py`
- Included troubleshooting guide for CI/local environment differences

**Root Cause**: Contract tests attempted real Keycloak connections during app import in CI

### 2025-11-11: Initial Version
- Added comprehensive guide for API testing
- Documented common 401 error causes
- Added dependency override checklist
- Created troubleshooting section

**Root Cause**: Fixed 4 service principal tests that failed due to missing OpenFGA dependency override
