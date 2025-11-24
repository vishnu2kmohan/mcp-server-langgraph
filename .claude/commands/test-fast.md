# Fast Test Iteration

**Usage**: `/test-fast` or `/test-fast <mode>`

**Purpose**: Execute tests with optimized speed for rapid development iteration

**Modes**:
- `dev` - Development mode (recommended)
- `core` - Fastest core tests only
- `parallel` - All tests in parallel
- `unit` - Unit tests only (no coverage)

---

## 🚀 Why Fast Testing?

Standard test execution with coverage can be slow:
- `make test`: ~45-60 seconds (with coverage)
- `make test-unit`: ~30-40 seconds (with coverage)

Fast testing options provide **40-70% speed improvement** for rapid iteration:
- `make test-dev`: ~15-20 seconds ⚡
- `make test-fast-core`: ~3-5 seconds ⚡⚡
- `make test-fast`: ~20-30 seconds ⚡

---

## ⚡ Fast Testing Options

### Development Mode (RECOMMENDED)

Best for active development - parallel, fast-fail, skip slow tests:

```bash
make test-dev
```rust
**Features**:
- ✅ Parallel execution (`pytest -n auto`)
- ✅ Stop on first failure (`-x`)
- ✅ Max 3 failures (`--maxfail=3`)
- ✅ Skip slow tests (`-m "unit and not slow"`)
- ✅ No coverage overhead
- ✅ Short traceback (`--tb=short`)

**Speed**: 40-60% faster than standard tests
**Use case**: Active development, quick feedback loop

**Example output**:
```

Running tests in development mode (parallel, fast-fail, no coverage)...
✓ Development tests complete

Features: Parallel execution, stop on first failure, skip slow tests
```bash
---

### Fastest Core Tests

Minimal test set for ultra-rapid iteration:

```bash
make test-fast-core
```

**Features**:
- ✅ Core unit tests only
- ✅ Parallel execution
- ✅ No slow tests
- ✅ No integration tests
- ✅ Minimal output (`-q`)

**Speed**: Typically < 5 seconds ⚡⚡
**Use case**: Rapid iteration on critical paths

**Example**:
```rust
⚡ Running core unit tests only (fastest iteration)...
✓ Core tests complete

Use for rapid iteration (typically < 5 seconds)
```

---

### All Tests (No Coverage)

Run all tests without coverage overhead:

```bash
make test-fast
```bash
**Features**:
- ✅ All unit and integration tests
- ✅ Parallel execution
- ✅ No coverage collection
- ✅ Short traceback

**Speed**: 30-40% faster than `make test`
**Use case**: Pre-commit validation without coverage

**Example**:
```

⚡ Running all tests without coverage (parallel, fast iteration)...
✓ Fast tests complete

Tip: Use 'make test-dev' for fastest development iteration
```bash
---

### Parallel Execution

Leverage multiple CPU cores:

```bash
# All tests in parallel
make test-fast

# Unit tests only in parallel
make test-fast-unit
```

**Features**:
- ✅ Automatic CPU core detection (`-n auto`)
- ✅ No coverage overhead
- ✅ All test types

**Speed**: 40-60% faster, scales with CPU cores
**Use case**: Fast execution of full test suite

**Example**:
```yaml
⚡⚡ Running all tests in parallel (pytest-xdist)...
✓ Parallel tests complete

Speedup: ~40-60% faster than sequential execution
```

---

## 📊 Speed Comparison

| Command | Duration | Coverage | Use Case |
|---------|----------|----------|----------|
| `make test` | ~45-60s | ✅ Yes | Pre-merge validation |
| `make test-unit` | ~30-40s | ✅ Yes | Standard unit tests |
| `make test-dev` | ~15-20s | ❌ No | **Active development** ⭐ |
| `make test-fast` | ~20-30s | ❌ No | Quick full suite |
| `make test-fast-core` | ~3-5s | ❌ No | **Rapid iteration** ⚡⚡ |

---

## 💡 When to Use Each Mode

### During Active Development
```bash
# Use test-dev for best balance
make test-dev
```bash
Fast feedback, catches most issues, skip slow tests.

### Quick Sanity Check
```bash
# Use test-fast-core
make test-fast-core
```

Ultra-fast, core functionality only.

### Pre-Commit
```bash
# Use test-fast
make test-fast
```bash
Full test suite, fast execution.

### Before PR/Merge
```bash
# Use standard test with coverage
make test
```

Full validation with coverage metrics.

---

## 🔄 Workflow Integration

### Typical Development Workflow

1. **Make changes to code**
   ```bash
   # Edit src/mcp_server_langgraph/module.py
   ```

2. **Quick sanity check** (3-5s)
   ```bash
   make test-fast-core
   ```

3. **If core tests pass, run dev mode** (15-20s)
   ```bash
   make test-dev
   ```

4. **Before commit, run with coverage** (30-40s)
   ```bash
   make test-unit
   ```

5. **Before PR, run full suite** (45-60s)
   ```bash
   make test
   ```

---

## 🎯 Additional Fast Test Options

### Re-run Failed Tests Only

```bash
make test-failed
```bash
Runs only tests that failed in previous run (using pytest `--lf`).

**Speed**: Depends on failure count, typically very fast
**Use case**: Fixing specific test failures

---

### Skip Slow Tests

```bash
make test-slow
```

Runs only slow tests (marked with `@pytest.mark.slow`).

**Use case**: Periodic execution of comprehensive slow tests

---

### Watch Mode (Auto-rerun)

```bash
make test-watch
```bash
Automatically re-runs tests when files change.

**Requires**: pytest-watch
**Use case**: Continuous testing during development

---

## 🔧 Advanced Options

### Parallel with Specific Worker Count

```bash
# Use 4 workers
pytest -n 4

# Use all CPU cores
pytest -n auto  # (used by Make targets)
```

### Custom Test Selection

```bash
# Run specific test file
pytest tests/test_auth.py -n auto

# Run specific test
pytest tests/test_auth.py::test_login -n auto

# Run tests matching pattern
pytest -k "auth" -n auto
```bash
---

## ⚠️ Important Notes

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
```python
---

## 📈 Performance Tips

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
```bash
### 3. Parallel-Safe Test Isolation

```python
# Use unique identifiers per test
def test_user_creation():
    user_id = f"test_user_{uuid.uuid4()}"
    # Test with unique ID
```

---

## 🔗 Related Commands

- `/test-summary` - Comprehensive test report with coverage
- `/test-all` - Run complete test suite
- `/test-failure-analysis` - Deep analysis of test failures
- `/quick-debug` - Fast debugging for test issues

---

## 📊 Example Session

```bash
User: /test-fast dev

Claude:
Running development mode tests (fastest iteration)...

Executing: make test-dev

🚀 Running tests in development mode (parallel, fast-fail, no coverage)...

==================== test session starts ====================
collected 350 items / 27 skipped

tests/test_auth.py::test_login ✓
tests/test_auth.py::test_logout ✓
tests/test_core.py::test_agent_init ✓
...
tests/test_llm.py::test_factory ✓

============ 323 passed, 27 skipped in 18.23s ============

✓ Development tests complete

Speed: 18s (vs 45s with coverage - 60% faster)
Skipped: 27 slow tests
Features: Parallel execution, fast-fail enabled

Next steps:
- All tests passing ✅
- For coverage report: make test-unit
- For full suite: make test
```

---

**Last Updated**: 2025-10-21
**Command Version**: 1.0
**Performance**: 40-70% faster than standard tests
