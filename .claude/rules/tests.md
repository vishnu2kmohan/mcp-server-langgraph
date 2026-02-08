---
description: Testing conventions for pytest and Vitest test files
paths:
  - "tests/**"
  - "**/*.test.ts"
  - "**/*.test.tsx"
  - "**/*_test.py"
globs:
  - "tests/**/*.py"
  - "**/*.test.{ts,tsx}"
---

# Testing Rules

## Test Categories

| Category | Marker | Purpose |
|----------|--------|---------|
| Unit | `@pytest.mark.unit` | Fast, no external deps |
| Integration | `@pytest.mark.integration` | Requires infrastructure |
| Property | `@pytest.mark.property` | Hypothesis edge cases |
| Contract | `@pytest.mark.contract` | MCP protocol compliance |

## Naming Convention (CRITICAL)

**Minimum 3 parts required**: `test_<what>_<condition>_<expected>`

| Wrong (2 words) | Correct (3+ words) |
|-----------------|-------------------|
| `test_create_session` | `test_create_session_returns_id` |
| `test_validate_input` | `test_validate_input_rejects_empty` |
| `test_auth_works` | `test_auth_with_valid_token_succeeds` |

**Regex validation**: Test name must match `test_\w+_\w+_\w+` (3+ underscores).

## Async Test Pattern

```python
@pytest.mark.asyncio
@pytest.mark.unit
async def test_feature(self, fixture):
    # Given
    input_data = ...
    # When
    result = await function(input_data)
    # Then
    assert result.status == "success"
```

## AsyncMock Rules (CRITICAL)

**ALWAYS use `spec=` parameter** to catch typos at test time:

| Wrong | Correct |
|-------|---------|
| `AsyncMock()` | `AsyncMock(spec=TargetClass)` |
| `AsyncMock(return_value=x)` | `AsyncMock(spec=TargetClass, return_value=x)` |
| `obj.method = AsyncMock` | `obj.method = AsyncMock(spec=TargetClass.method)` |

```python
# CORRECT - spec catches attribute errors at test time
mock_client = AsyncMock(spec=RedisClient)
mock_client.get.return_value = "value"

# WRONG - typos silently pass, fail in production
mock_client = AsyncMock()
mock_client.gett.return_value = "value"  # Undetected typo!

# WRONG - assigns class, not instance (AttributeError at runtime)
obj.method = AsyncMock  # Missing parentheses!
```

### External Service Mocks

| External | Mock Pattern |
|----------|-------------|
| Redis | `AsyncMock(spec=RedisClient, return_value=None)` |
| LLM | `AsyncMock(spec=ChatModel, return_value=AIMessage(...))` |
| OpenFGA | `AsyncMock(spec=OpenFGAClient, return_value=True)` |
| HTTP | `httpx.AsyncClient` with `respx` |

## Property Tests

```python
@pytest.mark.property
@given(st.text(min_size=1))
@settings(max_examples=50, deadline=2000)
def test_invariant(self, input_text):
    # Test invariant holds for all inputs
```

## Frontend Tests (Vitest)

```typescript
describe("Component", () => {
  it("should render correctly", () => {
    render(<Component />);
    expect(screen.getByRole("button")).toBeInTheDocument();
  });
});
```

## Frontend OOM Prevention (CRITICAL)

The frontend has **787+ test files** that cause OOM when run together.

**ALWAYS use sharded runner for full suite**:
```bash
# Fastest (~5-10 min) - RECOMMENDED
bash scripts/run-tests-sharded.sh --fast --parallel

# Full suite with all shards
bash scripts/run-tests-sharded.sh --parallel

# Single shard (for debugging)
bash scripts/run-tests-sharded.sh --shard 1
```

**NEVER use direct vitest for full suite**:
```bash
# WRONG - will OOM with 787+ test files
npm test -- --run
npx vitest run
```

**OK for single file or small subset**:
```bash
# OK - single file
npm test -- --run src/hooks/useDebounce.test.ts

# OK - pattern matching small subset
npm test -- --run --testNamePattern="useDebounce"
```

## Commands

```bash
# Python
uv run --frozen pytest -m unit
uv run --frozen pytest -m integration
uv run --frozen pytest --cov=src

# Frontend (use sharded runner for full suite)
bash scripts/run-tests-sharded.sh --fast --parallel  # Full suite
npm test -- --run src/path/to/file.test.ts           # Single file
npm run test:coverage                                 # Coverage (sharded internally)
```

## Parallelism (Default, with Opt-Out)

**Prerequisite**: pytest-xdist is in pyproject.toml dev dependencies.

### Python - Use xdist by Default

| Purpose | Command |
|---------|---------|
| Unit tests | `make test-unit` (uses `$(PYTEST_PARALLEL_FLAG)`) |
| Direct call | `uv run --frozen pytest -n auto -m unit` |
| Sequential (opt-out) | `PYTEST_SEQUENTIAL=1 make test` |
| Limited workers (CI) | `PYTEST_WORKERS=4 make test` |

**Rationale**: xdist `-n auto` uses all CPU cores. 8,700+ tests complete in ~3min vs ~20min sequential.

**When to use sequential**: Debugging test isolation issues, or if xdist not installed.

### Frontend - Use Worker Pool by Default

| Purpose | Command |
|---------|---------|
| Unit tests (single file) | `npm test -- --run --pool=threads <file>` |
| Coverage | `npm run test:coverage -- --pool=threads` |
| Fallback (compat issues) | `npm test -- --pool=forks` |

## Fixtures Location

- `tests/conftest.py` - Shared fixtures
- `tests/unit/conftest.py` - Unit-specific
- `tests/integration/conftest.py` - Integration-specific

---

## Shift-Left Patterns (Pre-Commit Prevention)

### subprocess.run() Timeout

```python
# CORRECT - ALWAYS include timeout parameter
result = subprocess.run(cmd, capture_output=True, timeout=60)

# WRONG - Test hangs indefinitely if process stalls
result = subprocess.run(cmd, capture_output=True)
```

### Environment Variables (Use monkeypatch)

```python
# CORRECT - Auto-reverted after test
def test_with_env(monkeypatch):
    monkeypatch.setenv("API_KEY", "test-value")

# WRONG - Pollutes other tests in xdist workers
def test_with_env():
    os.environ["API_KEY"] = "test-value"  # Never reverted!
```

### Sleep Duration (Max 5s)

```python
# CORRECT - Short sleeps for async timing
await asyncio.sleep(0.1)

# WRONG - Tests should never sleep > 5s
await asyncio.sleep(30)  # Use mock instead
```

### Memory Safety (Cleanup in teardown)

```python
# CORRECT - Prevent memory leaks in xdist
def teardown_method(self):
    gc.collect()

# WRONG - No cleanup (causes OOM in CI with 217GB memory use)
def teardown_method(self):
    pass
```
