# Test Templates - pytest-xdist Compatible Patterns

This directory contains cookiecutter templates for creating memory-safe, pytest-xdist compatible tests following TDD best practices.

## Quick Start

```bash
# Copy template to your test directory
cp tests/templates/test_unit_template.py tests/unit/auth/test_my_feature.py

# Edit the file:
# 1. Replace placeholder imports with actual imports
# 2. Update test class name and xdist_group
# 3. Replace TODO comments with actual test implementation
# 4. Update docstrings

# Validate your test
python scripts/validation/check_test_memory_safety.py tests/unit/auth/test_my_feature.py
python scripts/validation/check_async_mock_usage.py tests/unit/auth/test_my_feature.py

# Run your test
pytest tests/unit/auth/test_my_feature.py -v
pytest tests/unit/auth/test_my_feature.py -n auto  # Verify parallel execution
```

## Available Templates

### 1. Unit Test Template (`test_unit_template.py`)

**Use when:**
- Testing individual functions/methods in isolation
- All external dependencies are mocked
- Tests execute quickly (< 1 second)
- No I/O operations (no files, network, database)

**Includes:**
- Standard xdist-compatible pattern (3 parts)
- Sync and async test examples
- Multiple mock configuration patterns
- Authorization test examples
- Error handling examples
- Parametrized test examples
- Performance test pattern (auto-skipped in parallel mode)

**Example use cases:**
- Testing business logic functions
- Testing validation functions
- Testing data transformations
- Testing authorization checks (mocked)
- Testing error handling

### 2. Integration Test Template (`test_integration_template.py`)

**Use when:**
- Testing components working together
- Using real infrastructure (PostgreSQL, Redis, Keycloak, OpenFGA)
- Testing API contracts, database interactions, external service calls
- May be slower (< 5 seconds per test)

**Includes:**
- Worker-scoped infrastructure fixtures
- Database + cache integration patterns
- Conditional skips for missing dependencies
- FastAPI endpoint integration tests
- Transaction rollback testing
- Concurrent operation testing
- Mixed real/mocked dependency patterns

**Example use cases:**
- Testing database operations
- Testing caching behavior
- Testing API endpoints with real DB
- Testing authentication flows
- Testing authorization with real OpenFGA
- Testing transaction handling

## Memory Safety Pattern (3 Parts)

All templates implement the **mandatory 3-part memory safety pattern** to prevent pytest-xdist memory explosion (observed: 217GB VIRT before pattern, 1.8GB VIRT after).

### Part 1: `@pytest.mark.xdist_group(name="...")`

Groups related tests to run in the same pytest-xdist worker.

```python
@pytest.mark.xdist_group(name="api_key_security")  # Descriptive name
class TestAPIKeySecurity:
    ...
```

**Why:** Reduces mock object diversity within workers, prevents scattered allocation.

### Part 2: `teardown_method()` with `gc.collect()`

Forces garbage collection after each test method.

```python
class TestAPIKeySecurity:
    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()
```

**Why:** AsyncMock/MagicMock create circular references that prevent normal GC. Explicit GC breaks these cycles.

### Part 3: Explicit AsyncMock Configuration

All mocks MUST have explicit `return_value` or `side_effect`.

```python
# ✅ CORRECT
mock = AsyncMock()
mock.method.return_value = {"key": "value"}  # Explicit!

# ❌ WRONG - Truthy mock causes authorization bypass bugs!
mock = AsyncMock()  # Unconfigured!
result = await mock.method()  # Returns truthy AsyncMock object
```

**Why:** Unconfigured AsyncMock returns truthy objects, causing authorization checks to incorrectly pass.

## When to Use Each Template

### Unit Test Template

```
Does your test use real infrastructure (DB, Redis, Keycloak)?
├─ No → Use test_unit_template.py
│   └─ Mock all external dependencies
│   └─ Fast execution (< 1 second)
│   └─ Run frequently during development
│
└─ Yes → Use test_integration_template.py
```

### Integration Test Template

```
Does your test need to verify real infrastructure behavior?
├─ Yes → Use test_integration_template.py
│   ├─ PostgreSQL → Use postgres_connection_clean fixture
│   ├─ Redis → Use redis_client_clean fixture
│   ├─ Keycloak → Use keycloak_client_real fixture (conditional)
│   └─ OpenFGA → Use openfga_client_real fixture (conditional)
│
└─ No → Use test_unit_template.py
```

## Customization Guide

### Step 1: Copy Template

```bash
# For unit tests
cp tests/templates/test_unit_template.py tests/unit/<feature>/test_<your_feature>.py

# For integration tests
cp tests/templates/test_integration_template.py tests/integration/<feature>/test_<your_feature>_integration.py
```

### Step 2: Update Imports

Replace placeholder imports with your actual imports:

```python
# BEFORE (template)
# from mcp_server_langgraph.your_module import YourClass

# AFTER (your implementation)
from mcp_server_langgraph.auth.api_keys import APIKeyManager
from mcp_server_langgraph.auth.keycloak import KeycloakClient
```

### Step 3: Update Test Class

1. Rename test class to match feature
2. Update `xdist_group` name to match purpose
3. Update class docstring with references

```python
# BEFORE (template)
@pytest.mark.xdist_group(name="example_feature")
class TestExampleFeature:
    """Test suite for [FEATURE_NAME]."""

# AFTER (your implementation)
@pytest.mark.xdist_group(name="api_key_caching")
class TestAPIKeyCaching:
    """Test suite for API key caching with Redis.

    References:
    - Implementation: src/mcp_server_langgraph/auth/api_keys.py
    - ADR-0034: API Key Caching Strategy
    """
```

### Step 4: Replace TODO Tests

Replace placeholder `pass` statements with actual test implementation:

```python
# BEFORE (template)
async def test_example_async_function(self):
    """Test example asynchronous function."""
    # GIVEN: Configure mocks
    mock_dependency = AsyncMock()
    mock_dependency.some_method.return_value = {"key": "value"}
    pass  # TODO: Replace with actual test implementation

# AFTER (your implementation)
async def test_cache_hit_returns_cached_api_key(self):
    """Test that cache hit returns cached API key without Keycloak lookup.

    GIVEN: API key is cached in Redis
    WHEN: Validation is called
    THEN: Cached key is returned without Keycloak call
    """
    # GIVEN: Mocked dependencies
    mock_keycloak = AsyncMock()
    mock_redis = AsyncMock()
    mock_redis.get.return_value = b'{"user_id": "user-123", "api_key_hash": "..."}'

    # WHEN: Validate API key
    manager = APIKeyManager(keycloak_client=mock_keycloak, redis_client=mock_redis)
    result = await manager.validate_api_key("mcp_test_key")

    # THEN: Cached key returned, no Keycloak call
    assert result["user_id"] == "user-123"
    mock_keycloak.search_users.assert_not_called()
```

### Step 5: Add Appropriate Markers

Update module-level and class-level markers:

```python
# Module-level markers (apply to all tests in file)
pytestmark = [
    pytest.mark.unit,  # or pytest.mark.integration
    pytest.mark.auth,  # Feature marker
    pytest.mark.security,  # Additional markers as needed
]

# Class-level markers (specific to test class)
@pytest.mark.xdist_group(name="api_key_caching")
@pytest.mark.slow  # If tests take > 1 second
class TestAPIKeyCaching:
    ...
```

### Step 6: Validate

Run validation scripts to ensure compliance:

```bash
# Memory safety validation
python scripts/validation/check_test_memory_safety.py tests/unit/auth/test_api_key_caching.py

# AsyncMock usage validation
python scripts/validation/check_async_mock_usage.py tests/unit/auth/test_api_key_caching.py

# Run tests
pytest tests/unit/auth/test_api_key_caching.py -v
pytest tests/unit/auth/test_api_key_caching.py -n auto  # Verify parallel execution
```

## Common Patterns

### Authorization Test Pattern

```python
# Testing DENIAL (regular users)
@pytest.mark.asyncio
async def test_regular_user_denied_admin_action(self):
    """Test that regular users cannot perform admin actions."""
    # GIVEN: Authorization denies access
    mock_openfga = AsyncMock()
    mock_openfga.check_permission.return_value = False  # EXPLICIT!

    # WHEN: Regular user attempts admin action
    with pytest.raises(HTTPException) as exc_info:
        await perform_admin_action(openfga=mock_openfga)

    # THEN: 403 Forbidden
    assert exc_info.value.status_code == 403

# Testing GRANT (admin users)
@pytest.mark.asyncio
async def test_admin_user_allowed_admin_action(self):
    """Test that admin users can perform admin actions."""
    # GIVEN: Authorization grants access
    mock_openfga = AsyncMock()
    mock_openfga.check_permission.return_value = True  # EXPLICIT!

    # WHEN: Admin performs action
    result = await perform_admin_action(openfga=mock_openfga)

    # THEN: Action succeeds
    assert result.success is True
```

### Async Method Patching Pattern

```python
@pytest.mark.asyncio
async def test_patching_async_method(self):
    """Test patching async methods with AsyncMock."""
    from your_module import YourClass

    instance = YourClass()

    # CRITICAL: Use new_callable=AsyncMock for async methods!
    with patch.object(
        instance,
        "async_method_name",
        new_callable=AsyncMock,  # REQUIRED!
        return_value=expected_value,  # EXPLICIT!
    ) as mock_method:
        result = await instance.method_under_test()

        assert result == expected_output
        mock_method.assert_called_once()
```

### Integration Test with Worker Isolation

```python
async def test_database_with_worker_isolation(self, postgres_connection_clean):
    """Test database operations with worker-scoped schema.

    Each pytest-xdist worker uses separate schema:
    - gw0 → test_worker_gw0
    - gw1 → test_worker_gw1
    - etc.
    """
    # GIVEN: Worker-scoped database connection
    conn = postgres_connection_clean

    # WHEN: Insert test data
    await conn.execute(
        "INSERT INTO users (id, name) VALUES ($1, $2)",
        "user-123",
        "Test User",
    )

    # THEN: Data is retrievable (isolated from other workers)
    result = await conn.fetchrow("SELECT * FROM users WHERE id = $1", "user-123")
    assert result["name"] == "Test User"
```

## Troubleshooting

### Tests Fail with Memory Errors in Parallel Mode

**Symptoms:**
```bash
pytest tests/ -n auto
# Memory usage spikes to 40GB+, tests OOM killed
```

**Solution:**
1. Verify `teardown_method()` exists in test class
2. Check that `gc.collect()` is being called
3. Run validation: `python scripts/validation/check_test_memory_safety.py`

### Authorization Tests Pass When They Should Fail

**Symptoms:**
```python
# Test passes even though permission should be denied
authorized = await mock_openfga.check_permission(...)
if authorized:  # Should be False but evaluates to True!
    return
```

**Solution:**
```python
# WRONG (unconfigured mock is truthy)
mock_openfga = AsyncMock()

# CORRECT (explicit False)
mock_openfga = AsyncMock()
mock_openfga.check_permission.return_value = False
```

### Tests Hang Indefinitely

**Symptoms:**
```bash
pytest tests/your_test.py -v
# Test hangs, never completes
```

**Solution:**
Async methods must be patched with `new_callable=AsyncMock`:

```python
# WRONG (causes hang)
with patch.object(instance, "async_method") as mock:
    await instance.method_under_test()  # HANGS!

# CORRECT (uses AsyncMock)
with patch.object(instance, "async_method", new_callable=AsyncMock) as mock:
    await instance.method_under_test()  # Works!
```

### Tests Pass Locally but Fail in CI/CD with pytest -n auto

**Symptoms:**
```bash
# Local (single worker): PASS
pytest tests/your_test.py -v

# CI (parallel): FAIL
pytest tests/ -n auto
```

**Solution:**
1. Verify `@pytest.mark.xdist_group` is applied to test class
2. Check for shared state or global variables
3. Ensure dependency overrides are cleared in teardown
4. Run validation: `pytest tests/your_test.py -n auto` locally

## References

### Documentation
- **Memory Safety:** `tests/MEMORY_SAFETY_GUIDELINES.md` (1,197 lines)
- **pytest-xdist:** `tests/PYTEST_XDIST_BEST_PRACTICES.md` (554 lines)
- **AsyncMock:** `tests/ASYNC_MOCK_GUIDELINES.md` (209 lines)
- **TDD Standards:** `~/.claude/CLAUDE.md` (Global TDD requirements)

### Reference Implementations
- **Unit Tests:** `tests/integration/security/test_api_key_indexed_lookup.py`
- **Integration Tests:** `tests/integration/database/test_postgres_connection.py`
- **API Tests:** `tests/api/test_api_keys_endpoints.py`

### ADRs
- **ADR-0052:** Pytest-xdist Isolation Strategy (worker-scoped resources)
- **ADR-0034:** API Key Caching Strategy (cache patterns)

### Validation Scripts
- **Memory Safety:** `scripts/validation/check_test_memory_safety.py`
- **AsyncMock Usage:** `scripts/validation/check_async_mock_usage.py`
- **Fixture Organization:** `scripts/validation/validate_fixture_organization.py`

### Pre-commit Hooks
- **check-test-memory-safety:** Enforces 3-part memory safety pattern
- **check-async-mock-usage:** Validates AsyncMock for async methods
- **validate-fixture-organization:** Prevents duplicate autouse fixtures

## Pytest Markers

Common markers used in templates:

| Marker | Purpose | Example |
|--------|---------|---------|
| `@pytest.mark.unit` | Unit test | All unit tests |
| `@pytest.mark.integration` | Integration test | Tests with real infrastructure |
| `@pytest.mark.asyncio` | Async test | Tests with async/await |
| `@pytest.mark.xdist_group(name="...")` | Worker grouping | All tests (required) |
| `@pytest.mark.performance` | Performance test | Large dataset tests |
| `@pytest.mark.skipif(...)` | Conditional skip | Missing dependencies |
| `@pytest.mark.parametrize(...)` | Parametrized test | Multiple input/output sets |
| `@pytest.mark.slow` | Slow test (> 1s) | Database migrations |
| `@pytest.mark.auth` | Auth-related | Authentication/authorization |
| `@pytest.mark.security` | Security test | Security-critical tests |
| `@pytest.mark.api` | API test | FastAPI endpoints |
| `@pytest.mark.database` | Database test | PostgreSQL operations |
| `@pytest.mark.redis` | Redis test | Cache operations |
| `@pytest.mark.keycloak` | Keycloak test | Requires Keycloak |
| `@pytest.mark.openfga` | OpenFGA test | Requires OpenFGA |

See `tests/constants.py` and `.claude/context/pytest-markers.md` for complete marker catalog (67 markers).

## Running Tests

```bash
# Run all tests in a file
pytest tests/unit/auth/test_api_keys.py -v

# Run specific test class
pytest tests/unit/auth/test_api_keys.py::TestAPIKeyCaching -v

# Run specific test method
pytest tests/unit/auth/test_api_keys.py::TestAPIKeyCaching::test_cache_hit -v

# Run with parallelization (verify xdist compatibility)
pytest tests/unit/auth/test_api_keys.py -n auto

# Run with coverage
pytest tests/unit/auth/test_api_keys.py --cov=src/mcp_server_langgraph/auth

# Run only fast tests (< 1 second)
pytest tests/ -m "unit and not slow"

# Run integration tests (excluding missing infrastructure)
pytest tests/integration/ -m integration

# Run performance tests separately (skipped in parallel mode)
pytest tests/ -k performance --no-cov

# Run tests matching pattern
pytest tests/ -k "api_key"

# Run last failed tests
pytest --lf -x

# Run with verbose output
pytest tests/ -vv
```

## Best Practices Summary

### DO (✅)

1. **Always use templates as starting point**
2. **Apply all 3 parts of memory safety pattern**
3. **Configure all AsyncMock/MagicMock explicitly**
4. **Use descriptive test names** (test_feature_scenario_expected_result)
5. **Follow GIVEN-WHEN-THEN structure**
6. **Clear dependency overrides in teardown**
7. **Use worker-scoped fixtures for integration tests**
8. **Add conditional skips for missing dependencies**
9. **Run validation scripts before committing**
10. **Test parallel execution with pytest -n auto**

### DON'T (❌)

1. **Never use unconfigured AsyncMock** (causes auth bypass bugs)
2. **Never skip teardown_method()** (causes memory leaks)
3. **Never omit xdist_group marker** (causes memory issues)
4. **Never patch async methods without new_callable=AsyncMock** (causes hangs)
5. **Never share state between tests** (causes flaky tests)
6. **Never assume test execution order** (pytest-xdist randomizes)
7. **Never use bare `pytest` command** (use `uv run pytest`)
8. **Never commit without running tests in parallel mode**
9. **Never skip pre-commit hooks** (they prevent bugs)
10. **Never test implementation details** (test behavior)

## Getting Help

1. **Check documentation first:**
   - `tests/MEMORY_SAFETY_GUIDELINES.md`
   - `tests/PYTEST_XDIST_BEST_PRACTICES.md`
   - `tests/ASYNC_MOCK_GUIDELINES.md`

2. **Run validation scripts:**
   - `python scripts/validation/check_test_memory_safety.py`
   - `python scripts/validation/check_async_mock_usage.py`

3. **Review reference implementations:**
   - `tests/integration/security/test_api_key_indexed_lookup.py`
   - `tests/api/test_api_keys_endpoints.py`

4. **Use slash commands:**
   - `/test-summary unit` - Analyze test results
   - `/quick-debug <error>` - AI-assisted debugging
   - `/test-failure-analysis` - Deep failure analysis

## Changelog

### 2025-12-19
- Initial release of test templates
- `test_unit_template.py` with 3-part memory safety pattern
- `test_integration_template.py` with worker isolation
- Comprehensive README with usage guide

---

**Remember:** Tests are first-class citizens. Write them first (TDD), keep them fast, make them reliable.
