# ADR: Resilience Decorator Parameter Conventions

**Status**: Accepted
**Date**: 2025-11-15
**Context**: Bug discovered where hardcoded decorator parameters prevented test optimization fixtures from working

## Problem

Resilience decorators (`@retry_with_backoff`, `@circuit_breaker`, `@with_timeout`, `@with_bulkhead`) support both explicit parameters and global configuration. However, explicit parameters take precedence due to the `param or config.value` pattern:

```python
def retry_with_backoff(max_attempts: Optional[int] = None, ...):
    config = get_resilience_config()
    max_attempts = max_attempts or config.retry.max_attempts  # PRECEDENCE ISSUE
```

**Problem**: When `max_attempts=3` is explicitly passed (truthy), it **always** overrides `config.retry.max_attempts`, even when tests set global config via `fast_retry_config` fixture.

**Symptom**: OpenFGA circuit breaker tests took 45s despite `fast_retry_config` setting `max_attempts=1` because decorators had `@retry_with_backoff(max_attempts=3)`.

## Decision

**NEVER hardcode parameters in resilience decorators** unless absolutely necessary for a specific use case.

### Rules

1. **DEFAULT: No parameters** - Let global config control behavior
   ```python
   @retry_with_backoff()  # ✅ CORRECT
   @circuit_breaker(name="openfga")  # ✅ OK (name is required)
   @with_timeout(operation_type="auth")  # ✅ OK (type is logical grouping)
   ```

2. **AVOID: Hardcoded parameters**
   ```python
   @retry_with_backoff(max_attempts=3)  # ❌ WRONG - prevents test optimization
   @circuit_breaker(name="llm", fail_max=5)  # ❌ WRONG - should use config
   ```

3. **EXCEPTION: Justified overrides with comment**
   ```python
   @retry_with_backoff(max_attempts=1)  # OVERRIDE JUSTIFIED: Critical path, no retries allowed
   @circuit_breaker(name="payment", fail_max=1)  # OVERRIDE JUSTIFIED: Financial transactions, fail immediately
   ```

### Reasoning

- **Testability**: Tests can override global config without modifying code
- **Flexibility**: Production vs test behavior controlled by config, not code
- **Consistency**: Same decorator behavior across codebase
- **Debuggability**: Config changes visible in one place

## Implementation

### Code Changes Required

1. ✅ **Fixed** `src/mcp_server_langgraph/auth/openfga.py`:
   - Lines 130, 219: Removed `max_attempts=3` parameters
   - Now uses global config (prod: 3, test: 1)

2. **TODO**: Audit all resilience decorator usage:
   ```bash
   grep -r "@retry_with_backoff(" src/ | grep -v "@retry_with_backoff()"
   grep -r "@circuit_breaker(" src/ | grep "fail_max="
   grep -r "@with_timeout(" src/ | grep "timeout_duration="
   ```

3. **TODO**: Add linter to detect violations:
   ```python
   # scripts/lint_resilience_decorators.py
   # Fail CI if hardcoded parameters found without OVERRIDE JUSTIFIED comment
   ```

### Documentation Updates

1. **Decorator docstrings**: Add warning about parameter precedence
2. **CONTRIBUTING.md**: Document this convention
3. **This ADR**: Reference in code reviews

## Consequences

### Positive

- ✅ Tests run 95% faster (45s → 0.81s per OpenFGA test)
- ✅ Test infrastructure works correctly (fast_retry_config respected)
- ✅ Production behavior unchanged (still uses max_attempts=3 from global config)
- ✅ Future-proof against similar issues

### Negative

- ⚠️ Developers must understand parameter precedence
- ⚠️ Requires code review discipline
- ⚠️ Existing code needs audit and cleanup

### Risks

- **Accidental override**: Developer adds parameter without understanding impact
- **Mitigation**: Linter + code review + this ADR

## Related

- **Bug Report**: OpenFGA tests taking 45s despite fast_retry_config fixture
- **Fix Commit**: 47e3eaae - Removed hardcoded retry parameters from OpenFGA client
- **Phase 3 Optimization**: docs-internal/COVERAGE_IMPROVEMENT_PLAN.md#phase-3
- **fast_retry_config Fixture**: tests/conftest.py:1794-1862

## Examples

### Before (Broken)

```python
# src/mcp_server_langgraph/auth/openfga.py (BEFORE)
@retry_with_backoff(max_attempts=3, exponential_base=1.5)  # ❌ Hardcoded
async def check_permission(self, user, relation, object):
    # ...
```

**Problem**: Tests using `fast_retry_config` (max_attempts=1) were ignored, causing 45s test duration.

### After (Fixed)

```python
# src/mcp_server_langgraph/auth/openfga.py (AFTER)
@retry_with_backoff()  # ✅ Uses global config
async def check_permission(self, user, relation, object):
    """
    Protected by:
    - Retry logic: Configurable via global resilience config (default: 3 attempts, test: 1 attempt)
    """
    # ...
```

**Result**: Tests using `fast_retry_config` now work correctly, reducing test time to 0.81s.

## Verification

### Test

```python
# tests/test_resilience_decorator_precedence.py (NEW)
def test_retry_decorator_respects_global_config():
    """Verify decorators use global config when no parameters provided."""
    from mcp_server_langgraph.resilience import retry_with_backoff, set_resilience_config, RetryConfig

    # Set global config
    test_config = RetryConfig(max_attempts=1)
    set_resilience_config(test_config)

    @retry_with_backoff()  # No parameters
    async def test_func():
        raise ValueError("Retry me")

    # Should fail after 1 attempt (not default 3)
    with pytest.raises(ValueError):
        await test_func()

    # Verify only 1 attempt was made
    assert call_count == 1
```

### Audit

```bash
# Find all hardcoded parameters
make lint-resilience-decorators

# Expected output: 0 violations (or justified overrides with comments)
```

## References

- Python decorator patterns: https://realpython.com/primer-on-python-decorators/
- Resilience patterns: https://docs.microsoft.com/en-us/azure/architecture/patterns/retry
- Parameter precedence: docs-internal/RESILIENCE_DECORATOR_PRECEDENCE.md

---

**Approved by**: Engineering Team
**Reviewed**: 2025-11-15
**Next Review**: 2026-01-15 (or when major refactoring occurs)
