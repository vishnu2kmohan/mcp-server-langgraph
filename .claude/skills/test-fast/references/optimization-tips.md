# Optimization Tips & Performance Guidance

Reference material for the `test-fast` skill. Loaded on demand.

---

## Important Notes

### Coverage vs Speed Trade-off

Fast test modes **disable coverage** for speed. Before committing:

```bash
# Always run with coverage before commit
make test-unit
```

This ensures coverage doesn't drop.

### Parallel Testing Considerations

**Safe for parallel**:
- Unit tests (isolated, no shared state)
- Most integration tests (with proper fixtures)

**May need sequential**:
- Tests that modify shared database state
- Tests that use fixed ports/resources
- Tests with race conditions

If parallel tests fail inconsistently:
```bash
# Run sequentially to verify
pytest tests/test_file.py -v
```

---

## Performance Tips

### 1. Mark Slow Tests

Help pytest skip slow tests in dev mode:

```python
import pytest

@pytest.mark.slow
def test_comprehensive_integration():
    # Long-running test
    ...
```

Then `make test-dev` automatically skips these.

### 2. Use Fixtures Efficiently

```python
# Bad: function scope for expensive setup
@pytest.fixture
def expensive_resource():
    return setup_expensive_thing()

# Good: session scope if safe
@pytest.fixture(scope="session")
def expensive_resource():
    return setup_expensive_thing()
```

### 3. Parallel-Safe Test Isolation

```python
# Use unique identifiers per test
def test_user_creation():
    user_id = f"test_user_{uuid.uuid4()}"
    # Test with unique ID
```

---

## Example Session

```bash
User: /test-fast dev

Claude:
Running development mode tests (fastest iteration)...

Executing: make test-dev

Running tests in development mode (parallel, fast-fail, no coverage)...

==================== test session starts ====================
collected 350 items / 27 skipped

tests/test_auth.py::test_login PASSED
tests/test_auth.py::test_logout PASSED
tests/test_core.py::test_agent_init PASSED
...
tests/test_llm.py::test_factory PASSED

============ 323 passed, 27 skipped in 18.23s ============

Development tests complete

Speed: 18s (vs 45s with coverage - 60% faster)
Skipped: 27 slow tests
Features: Parallel execution, fast-fail enabled

Next steps:
- All tests passing
- For coverage report: make test-unit
- For full suite: make test
```

---

*Part of the test-fast skill. See [../SKILL.md](../SKILL.md) for main instructions.*
