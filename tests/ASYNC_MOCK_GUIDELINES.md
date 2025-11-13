# AsyncMock Best Practices for Test Safety

**CRITICAL**: Always configure AsyncMock return values to prevent subtle authorization bugs and pytest-xdist test pollution.

## The Problem

Unconfigured `AsyncMock` objects are **truthy**, which causes dangerous bugs in authorization checks:

```python
# ❌ DANGEROUS - Unconfigured AsyncMock
mock_openfga = AsyncMock()

# When awaited, returns truthy AsyncMock instead of False!
authorized = await mock_openfga.check_permission(user="alice", relation="admin", object="org:acme")

if authorized:  # ❌ BUG: Evaluates to True even though permission should be denied!
    return  # Authorization incorrectly granted!
```

This bug was discovered in `tests/api/test_scim_security.py` where unconfigured AsyncMock caused authorization checks to incorrectly pass, bypassing security controls.

## The Solution

**ALWAYS** configure AsyncMock with explicit `return_value` or `side_effect`:

### ✅ CORRECT Pattern - Explicit Configuration

```python
# Authorization checks (should deny)
mock_openfga = AsyncMock()
mock_openfga.check_permission.return_value = False  # ✅ Explicit False

# When awaited, returns False as expected
authorized = await mock_openfga.check_permission(...)
if authorized:  # ✅ Correctly evaluates to False
    return  # Authorization correctly denied
```

### ✅ CORRECT Pattern - Explicit Success Case

```python
# Authorization checks (should allow)
mock_openfga = AsyncMock()
mock_openfga.check_permission.return_value = True  # ✅ Explicit True

# Admin user test
authorized = await mock_openfga.check_permission(user="admin", relation="admin", object="org:acme")
assert authorized is True  # ✅ Admin correctly authorized
```

### ✅ CORRECT Pattern - Exception Handling

```python
# Test error scenarios
mock_openfga = AsyncMock()
mock_openfga.check_permission.side_effect = Exception("OpenFGA unavailable")  # ✅ Explicit exception

with pytest.raises(Exception):
    await mock_openfga.check_permission(...)
```

### ✅ CORRECT Pattern - Void Functions

```python
# Functions that return None
mock_openfga = AsyncMock()
mock_openfga.write_tuples.return_value = None  # ✅ Explicit None

await mock_openfga.write_tuples([...])  # Returns None as expected
```

## Why This Matters

### 1. Authorization Bypass Bugs

Unconfigured AsyncMock returns truthy values, causing authorization checks to **incorrectly pass**:

```python
# REAL BUG from tests/api/test_scim_security.py (BEFORE fix):
mock_openfga = AsyncMock()  # ❌ Unconfigured

# This returned <AsyncMock> (truthy) instead of False!
authorized = await openfga.check_permission(...)

if authorized:  # ❌ BUG: Always True, bypassing security!
    # Authorization granted when it should be denied
    pass
```

**Impact**: Security tests passed even though authorization was broken!

### 2. Pytest-xdist State Pollution

Unconfigured AsyncMock objects accumulate in worker processes, causing:
- Memory leaks (observed: 217GB VIRT, 42GB RES)
- Coroutine warnings: `RuntimeWarning: coroutine 'AsyncMockMixin._execute_mock_call' was never awaited`
- Intermittent test failures in parallel execution

### 3. Pydantic Validation Errors

When unconfigured AsyncMock leaks into Pydantic models:

```python
# Pydantic sees coroutine object instead of string:
ValidationError: 1 validation error for SCIMName
familyName
  Input should be a valid string [type=string_type,
  input_value=<coroutine object AsyncMockMixin._execute_mock_call at 0x7fad4fa55d40>,
  input_type=coroutine]
```

## Common Patterns

### Authorization Checks

```python
# Testing that regular users are DENIED
mock_openfga = AsyncMock()
mock_openfga.check_permission.return_value = False  # Explicit deny

with pytest.raises(HTTPException) as exc_info:
    await create_resource(current_user=regular_user, openfga=mock_openfga)

assert exc_info.value.status_code == 403
```

### Admin Authorization

```python
# Testing that admin users are ALLOWED
mock_openfga = AsyncMock()
mock_openfga.check_permission.return_value = True  # Explicit allow

result = await create_resource(current_user=admin_user, openfga=mock_openfga)
assert result.created is True
```

### Write Operations

```python
# Testing write operations (return None)
mock_openfga = AsyncMock()
mock_openfga.write_tuples.return_value = None  # Explicit None
mock_openfga.delete_tuples_for_object.return_value = None  # Explicit None

await service.sync_permissions(openfga=mock_openfga)
mock_openfga.write_tuples.assert_called_once()
```

### Error Scenarios

```python
# Testing error handling
mock_keycloak = AsyncMock()
mock_keycloak.create_user.side_effect = Exception("Keycloak unavailable")  # Explicit exception

with pytest.raises(HTTPException) as exc_info:
    await create_user(keycloak=mock_keycloak)

assert exc_info.value.status_code == 500
```

## Validation

### Pre-commit Hook

A pre-commit hook checks for unconfigured AsyncMock instances:

```bash
# Automatically run by pre-commit
python scripts/check_async_mock_configuration.py tests/**/*.py
```

### Meta-Test

`tests/meta/test_async_mock_configuration.py` validates all AsyncMock instances in the codebase:

```bash
pytest tests/meta/test_async_mock_configuration.py
```

## Quick Reference

| Use Case | Pattern |
|----------|---------|
| **Authorization Denial** | `mock.check_permission.return_value = False` |
| **Authorization Grant** | `mock.check_permission.return_value = True` |
| **Void Functions** | `mock.method.return_value = None` |
| **Exception Handling** | `mock.method.side_effect = Exception("error")` |
| **Data Returns** | `mock.method.return_value = {"key": "value"}` |

## References

- **Original Bug**: `tests/api/test_scim_security.py` (fixed in commit abb04a6a)
- **Root Cause Analysis**: `/tmp/pytest_xdist_strategy_analysis.md`
- **Audit Report**: 65 unconfigured high-risk instances found (2025-11-13)
- **Related**: CWE-862 (Missing Authorization), OWASP A01:2021 (Broken Access Control)

## Enforcement

1. **Pre-commit hook**: Blocks commits with unconfigured AsyncMock (non-blocking initially, will become blocking)
2. **Meta-test**: Fails if unconfigured AsyncMock instances are detected
3. **Code review**: AsyncMock configuration is required in all test PRs
4. **CI/CD**: Pre-commit hooks run in CI to catch violations

---

**Remember**: Unconfigured AsyncMock is not just a style issue—it's a **security bug** that can bypass authorization checks!
