# ADR-0054: Circuit Breaker Decorator Closure Isolation

**Status:** Accepted
**Date:** 2025-11-13
**Author:** Claude Code (automated via Codex findings validation)
**Related:** ADR-0026 (Circuit Breaker Pattern), ADR-0053 (pytest-xdist State Pollution)

## Context

During comprehensive code review by OpenAI Codex, a critical test isolation bug was discovered in the circuit breaker implementation. The bug manifested as test failures in `tests/test_openfga_client.py` when running the full test suite with `make test-unit` (pytest-xdist parallel execution), but tests passed when run in isolation.

### Problem Description

**Symptoms:**
- `tests/test_openfga_client.py:518`, `:559`, `:600` (TestOpenFGACircuitBreakerCriticality) failed with assertion errors
- Assertions expected circuit breaker state to be "open" but found "closed"
- Circuit breaker warnings appeared ("Circuit breaker open for openfga, failing fast") indicating fallback logic was firing
- Tests passed when run alone: `pytest tests/test_openfga_client.py -n 2`
- Tests failed when run with full suite: `make test-unit`

**Root Cause:**

The `@circuit_breaker` decorator creates a **closure** over the circuit breaker instance at decoration time:

```python
# src/mcp_server_langgraph/resilience/circuit_breaker.py:203-205
def decorator(func: Callable[P, T]) -> Callable[P, T]:
    # Get or create circuit breaker
    breaker = get_circuit_breaker(name)  # ← CLOSURE CAPTURES THIS INSTANCE
```

The old `reset_all_circuit_breakers()` function cleared the global registry:

```python
# OLD IMPLEMENTATION (BUGGY)
def reset_all_circuit_breakers() -> None:
    _circuit_breakers.clear()  # ← CLEARS REGISTRY, CREATES NEW INSTANCES
    logger.info("All circuit breakers reset")
```

**The Isolation Bug:**

1. Decorator applied at module import time captures circuit breaker instance A
2. Tests trigger failures → instance A transitions to "open" state
3. Autouse fixture calls `reset_all_circuit_breakers()` → clears registry
4. Test calls `get_circuit_breaker("openfga")` → creates NEW instance B (state="closed")
5. Test inspects instance B state → finds "closed"
6. Decorator still uses instance A → actually raises CircuitBreakerOpenError
7. **Assertion fails:** Test expects state "open" but registry shows "closed"

### Impact

**Affected Tests:**
- `tests/test_openfga_client.py::TestOpenFGACircuitBreakerCriticality::test_circuit_breaker_fails_closed_for_critical_resources` (line 518)
- `tests/test_openfga_client.py::TestOpenFGACircuitBreakerCriticality::test_circuit_breaker_fails_open_for_non_critical_resources` (line 559)
- `tests/test_openfga_client.py::TestOpenFGACircuitBreakerCriticality::test_circuit_breaker_defaults_to_critical_true` (line 600)

**Severity:** HIGH - Breaks CI/CD pipeline, prevents parallel test execution, undermines test reliability

## Decision

We will modify `reset_all_circuit_breakers()` to **reset the state of existing instances** instead of clearing the registry. This preserves decorator closure integrity while still providing the test isolation required.

### New Implementation

```python
def reset_all_circuit_breakers() -> None:
    """
    Reset all circuit breakers (for testing).

    Resets the state of all existing circuit breakers to CLOSED without
    removing them from the registry. This preserves decorator closure integrity
    by ensuring decorators continue to reference the same circuit breaker instances.

    Important: This function does NOT clear the registry. If you need to clear
    the registry completely (e.g., in teardown), call _circuit_breakers.clear()
    directly, but be aware that decorator closures will hold stale references.

    See: tests/resilience/test_circuit_breaker_decorator_isolation.py
    See: docs-internal/adr/ADR-0054-circuit-breaker-decorator-closure-isolation.md
    """
    # Reset state of all existing circuit breakers instead of clearing registry
    # This preserves decorator closure integrity
    for name, breaker in list(_circuit_breakers.items()):
        breaker.close()  # Reset to CLOSED state
        logger.debug(f"Circuit breaker state reset: {name}")

    logger.info(f"All circuit breakers reset ({len(_circuit_breakers)} total)")
```

### Regression Tests

Created comprehensive regression tests in `tests/resilience/test_circuit_breaker_decorator_isolation.py`:

1. **`test_decorator_closure_persists_after_registry_clear`** - Validates fix by ensuring decorator continues using same instance after reset
2. **`test_reset_circuit_breaker_preserves_instance_identity`** - Validates `reset_circuit_breaker()` also preserves instance identity
3. **`test_multiple_decorators_with_same_name_share_instance`** - Validates registry sharing works correctly

## Consequences

### Positive

✅ **Decorator closures remain valid** - Decorators continue to reference the correct circuit breaker instances
✅ **Test isolation preserved** - Each test starts with clean circuit breaker state (CLOSED)
✅ **Parallel execution works** - Tests pass reliably in pytest-xdist workers
✅ **CI/CD reliability** - `make test-unit` passes consistently
✅ **Backward compatible** - Existing tests continue to work
✅ **Clear semantics** - Function name "reset" accurately describes behavior (reset state, not destroy instances)

### Negative

⚠️ **Registry accumulation** - Circuit breakers are never removed from registry during test execution
   - **Mitigation:** Test suite is short-lived, registry size is bounded by number of unique circuit breaker names
   - **Impact:** Negligible memory overhead (~1-2KB per circuit breaker instance)

⚠️ **Explicit cleanup required** - If tests need to completely clear registry, must call `_circuit_breakers.clear()` directly
   - **Mitigation:** Documented in function docstring
   - **Impact:** Minimal - very few tests need this

### Trade-offs

**Alternative 1: Make decorator lookup circuit breaker on each call**
```python
# Rejected: Adds overhead to hot path
def async_wrapper(*args, **kwargs):
    breaker = get_circuit_breaker(name)  # ← Lookup on EVERY call
    # ...
```
- ❌ Performance overhead on every protected function call
- ❌ Thread-safety concerns with concurrent registry modifications
- ✅ Would allow registry clearing

**Alternative 2: Use weak references in decorator closure**
```python
# Rejected: Complex, error-prone
import weakref
breaker_ref = weakref.ref(get_circuit_breaker(name))
```
- ❌ Significant complexity
- ❌ Risk of circuit breaker being garbage collected unexpectedly
- ❌ Harder to debug

**Selected Approach: Reset state without clearing registry**
- ✅ Simple, straightforward implementation
- ✅ Preserves decorator closure integrity
- ✅ Zero performance overhead
- ✅ Easy to understand and maintain

## Validation

### Test Results (Before Fix)

```bash
$ make test-unit
...
FAILED tests/test_openfga_client.py::TestOpenFGACircuitBreakerCriticality::test_circuit_breaker_fails_closed_for_critical_resources
FAILED tests/test_openfga_client.py::TestOpenFGACircuitBreakerCriticality::test_circuit_breaker_fails_open_for_non_critical_resources
FAILED tests/test_openfga_client.py::TestOpenFGACircuitBreakerCriticality::test_circuit_breaker_defaults_to_critical_true
AssertionError: Decorator blocked call (open state) but registry shows state 'closed' - this indicates decorator closure is stale!
```

### Test Results (After Fix)

```bash
$ pytest tests/resilience/test_circuit_breaker_decorator_isolation.py -xvs
tests/resilience/test_circuit_breaker_decorator_isolation.py::TestCircuitBreakerDecoratorIsolation::test_decorator_closure_persists_after_registry_clear PASSED
tests/resilience/test_circuit_breaker_decorator_isolation.py::TestCircuitBreakerDecoratorIsolation::test_reset_circuit_breaker_preserves_instance_identity PASSED
tests/resilience/test_circuit_breaker_decorator_isolation.py::TestCircuitBreakerDecoratorIsolation::test_multiple_decorators_with_same_name_share_instance PASSED

============================== 3 passed in 4.19s ===============================

$ make test-unit
...
All tests passed ✓
```

## Related Issues

**OpenAI Codex Findings:**
- Issue 2: OpenFGA circuit breaker tests failing with state inspection mismatches
- Root cause: `reset_all_circuit_breakers()` clearing registry while decorator closures held stale references

**Related ADRs:**
- ADR-0026: Circuit Breaker Pattern - Original circuit breaker implementation
- ADR-0053: pytest-xdist State Pollution Prevention - General test isolation patterns

**Related Tests:**
- `tests/resilience/test_circuit_breaker_decorator_isolation.py` - Regression tests for this fix
- `tests/test_openfga_client.py:518-600` - Original failing tests

## Implementation Checklist

- [x] Modify `reset_all_circuit_breakers()` to reset state instead of clearing registry
- [x] Add comprehensive docstring explaining behavior and trade-offs
- [x] Create regression tests in `test_circuit_breaker_decorator_isolation.py`
- [x] Verify all OpenFGA circuit breaker tests pass
- [x] Verify full test suite passes with `make test-unit`
- [x] Document decision in ADR-0054
- [x] Ensure pre-commit hooks pass
- [x] Commit and push changes

## References

- **Code:** `src/mcp_server_langgraph/resilience/circuit_breaker.py:395-416`
- **Tests:** `tests/resilience/test_circuit_breaker_decorator_isolation.py`
- **Original Bug:** `tests/test_openfga_client.py:518, :559, :600`
- **Python Closures:** https://docs.python.org/3/reference/expressions.html#lambda
- **pytest-xdist Isolation:** https://pytest-xdist.readthedocs.io/en/latest/how-to.html#making-session-scoped-fixtures-execute-only-once

---

**Next Steps:**
1. Monitor CI/CD for any edge cases
2. Consider adding circuit breaker registry size metrics if accumulation becomes a concern
3. Evaluate if similar closure issues exist in other decorators (retry, timeout, bulkhead)
