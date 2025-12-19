# Test Templates - Quick Reference

One-page reference for the most common test patterns. For complete templates, see `test_unit_template.py`, `test_integration_template.py`, and `README.md`.

## Memory Safety Pattern (MANDATORY)

All tests using AsyncMock/MagicMock MUST implement this 3-part pattern:

```python
import gc
from unittest.mock import AsyncMock

@pytest.mark.xdist_group(name="feature_name")  # Part 1: Group tests
class TestFeature:
    def teardown_method(self):  # Part 2: Force GC
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    async def test_something(self):
        mock = AsyncMock()
        mock.method.return_value = "value"  # Part 3: Explicit config
        # ... test implementation ...
```

**Impact:** 217GB VIRT → 1.8GB VIRT (98% reduction)

## Common Patterns

### Basic Unit Test

```python
import gc
import pytest
from unittest.mock import AsyncMock

pytestmark = pytest.mark.unit

@pytest.mark.xdist_group(name="auth_tests")
class TestAuthentication:
    def teardown_method(self):
        gc.collect()

    @pytest.mark.asyncio
    async def test_login_success(self):
        # GIVEN
        mock_auth = AsyncMock()
        mock_auth.verify_credentials.return_value = {"user_id": "123"}

        # WHEN
        result = await login(mock_auth, "user", "pass")

        # THEN
        assert result["user_id"] == "123"
```

### Authorization Test (Denial)

```python
@pytest.mark.asyncio
async def test_regular_user_denied(self):
    # GIVEN: Authorization denies
    mock_openfga = AsyncMock()
    mock_openfga.check_permission.return_value = False  # EXPLICIT!

    # WHEN: Regular user attempts action
    with pytest.raises(HTTPException) as exc_info:
        await admin_action(openfga=mock_openfga)

    # THEN: 403 Forbidden
    assert exc_info.value.status_code == 403
```

### Authorization Test (Grant)

```python
@pytest.mark.asyncio
async def test_admin_user_allowed(self):
    # GIVEN: Authorization grants
    mock_openfga = AsyncMock()
    mock_openfga.check_permission.return_value = True  # EXPLICIT!

    # WHEN: Admin performs action
    result = await admin_action(openfga=mock_openfga)

    # THEN: Success
    assert result.success is True
```

### Patching Async Methods

```python
import os
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_with_async_patch(self):
    from your_module import YourClass
    instance = YourClass()

    # CRITICAL: Use new_callable=AsyncMock!
    with patch.object(
        instance,
        "async_method",
        new_callable=AsyncMock,  # REQUIRED!
        return_value="value",
    ) as mock:
        result = await instance.method_under_test()
        assert result == expected
```

### Integration Test with Database

```python
pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

@pytest.mark.xdist_group(name="db_tests")
class TestDatabaseIntegration:
    def teardown_method(self):
        gc.collect()

    async def test_save_user(self, postgres_connection_clean):
        # GIVEN: Clean DB connection (worker-scoped)
        conn = postgres_connection_clean

        # WHEN: Insert data
        await conn.execute(
            "INSERT INTO users (id, name) VALUES ($1, $2)",
            "user-123", "Alice"
        )

        # THEN: Data persisted
        result = await conn.fetchrow(
            "SELECT * FROM users WHERE id = $1", "user-123"
        )
        assert result["name"] == "Alice"
```

### Integration Test with Redis

```python
async def test_cache_operations(self, redis_client_clean):
    # GIVEN: Clean Redis connection (worker-scoped DB)
    redis = redis_client_clean

    # WHEN: Set cache value
    await redis.setex("key", 3600, "value")

    # THEN: Value retrievable
    result = await redis.get("key")
    assert result.decode() == "value"
```

### Multiple Mocks

```python
@pytest.mark.asyncio
async def test_with_multiple_mocks(self):
    # GIVEN: Multiple mocks (all EXPLICIT)
    mock_keycloak = AsyncMock()
    mock_keycloak.get_user.return_value = {"id": "123"}

    mock_redis = AsyncMock()
    mock_redis.get.return_value = None
    mock_redis.setex.return_value = True

    mock_llm = AsyncMock()
    mock_llm.generate.return_value = {"text": "response"}

    # WHEN: Call with all mocks
    result = await service(
        keycloak=mock_keycloak,
        redis=mock_redis,
        llm=mock_llm
    )

    # THEN: Assert interactions
    mock_keycloak.get_user.assert_called_once()
    mock_redis.setex.assert_called_once()
```

### Error Handling

```python
@pytest.mark.asyncio
async def test_error_handling(self):
    # GIVEN: Mock raises exception
    mock_service = AsyncMock()
    mock_service.method.side_effect = Exception("Error!")

    # WHEN: Call that should handle error
    with pytest.raises(Exception) as exc_info:
        await function(mock_service)

    # THEN: Error handled correctly
    assert "Error!" in str(exc_info.value)
```

### Parametrized Test

```python
@pytest.mark.parametrize("input,expected", [
    ("input1", "output1"),
    ("input2", "output2"),
    ("input3", "output3"),
])
def test_multiple_cases(self, input, expected):
    result = function(input)
    assert result == expected
```

### Performance Test (Skipped in Parallel)

```python
import os

@pytest.mark.performance
@pytest.mark.skipif(
    os.getenv("PYTEST_XDIST_WORKER") is not None,
    reason="Performance tests skipped in parallel mode"
)
class TestPerformance:
    def teardown_method(self):
        gc.collect()

    @pytest.mark.asyncio
    async def test_large_dataset(self):
        # Run separately: pytest -k performance --no-cov
        result = await process_large_dataset(size=10000)
        assert result.processed == 10000
```

## Common Mistakes

### ❌ WRONG: Unconfigured AsyncMock

```python
mock = AsyncMock()  # Truthy! Causes auth bypass bugs!
authorized = await mock.check_permission(...)
if authorized:  # Always True!
    return
```

### ✅ CORRECT: Explicit Configuration

```python
mock = AsyncMock()
mock.check_permission.return_value = False  # Explicit!
authorized = await mock.check_permission(...)
if authorized:  # Correctly False
    return
```

### ❌ WRONG: Missing teardown_method

```python
class TestFeature:
    # Missing teardown! Causes 217GB memory usage!
    async def test_something(self):
        mock = AsyncMock()  # Leaks!
```

### ✅ CORRECT: With teardown_method

```python
@pytest.mark.xdist_group(name="feature")
class TestFeature:
    def teardown_method(self):
        gc.collect()  # Prevents leaks

    async def test_something(self):
        mock = AsyncMock()
```

### ❌ WRONG: Sync patch on async method

```python
with patch.object(obj, "async_method") as mock:  # Hangs!
    await obj.async_method()
```

### ✅ CORRECT: AsyncMock for async methods

```python
with patch.object(obj, "async_method", new_callable=AsyncMock) as mock:
    await obj.async_method()  # Works!
```

## Validation Commands

```bash
# Validate memory safety
python scripts/validation/check_test_memory_safety.py tests/your_test.py

# Validate AsyncMock usage
python scripts/validation/check_async_mock_usage.py tests/your_test.py

# Run tests
pytest tests/your_test.py -v

# Run with parallelization
pytest tests/your_test.py -n auto

# Run with coverage
pytest tests/your_test.py --cov=src
```

## Pre-commit Checklist

- [ ] `@pytest.mark.xdist_group(name="...")` on all test classes
- [ ] `teardown_method()` with `gc.collect()` in all test classes
- [ ] All AsyncMock/MagicMock have explicit `return_value` or `side_effect`
- [ ] Async methods patched with `new_callable=AsyncMock`
- [ ] Tests pass: `pytest tests/your_test.py -v`
- [ ] Tests pass in parallel: `pytest tests/your_test.py -n auto`
- [ ] Validation passes: `python scripts/validation/check_test_memory_safety.py`

## Quick Template Copy

```bash
# Unit test
cp tests/templates/test_unit_template.py tests/unit/<feature>/test_<name>.py

# Integration test
cp tests/templates/test_integration_template.py tests/integration/<feature>/test_<name>_integration.py
```

## Help

- Full templates: `tests/templates/test_unit_template.py`, `test_integration_template.py`
- Complete guide: `tests/templates/README.md`
- Memory safety: `tests/MEMORY_SAFETY_GUIDELINES.md`
- pytest-xdist: `tests/PYTEST_XDIST_BEST_PRACTICES.md`
- AsyncMock: `tests/ASYNC_MOCK_GUIDELINES.md`

---

**Remember:** Tests FIRST (TDD), xdist_group ALWAYS, gc.collect() EVERYWHERE, AsyncMock EXPLICITLY configured!
