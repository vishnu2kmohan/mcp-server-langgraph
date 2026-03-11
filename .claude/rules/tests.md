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

## Required Test Class Structure (MANDATORY)

Every Python test class MUST include `teardown_method()` with `gc.collect()`.
Non-unit test classes (integration, contract, e2e, meta) MUST also have
`@pytest.mark.xdist_group`. Unit tests (`tests/unit/`) do NOT need xdist_group.

**Before generating test code**, verify:
- `teardown_method` with `gc.collect()` present (prevents 217GB OOM in xdist)
- `@pytest.mark.xdist_group` present (non-unit tests only)
- `spec=` on all AsyncMock/MagicMock instances
- `side_effect=` on all patched singletons (not `return_value=`)

```python
# Non-unit test class (integration/contract/e2e)
@pytest.mark.integration
@pytest.mark.xdist_group(name="my_feature")  # REQUIRED for non-unit
class TestMyFeatureIntegration:
    """Integration tests for my feature."""

    def teardown_method(self):  # REQUIRED for ALL test classes
        """Clean up after each test."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_feature_works_with_real_service(self):
        ...

# Unit test class (no xdist_group needed)
@pytest.mark.unit
class TestMyFeatureUnit:
    """Unit tests for my feature."""

    def teardown_method(self):  # REQUIRED for ALL test classes
        """Clean up after each test."""
        gc.collect()

    def test_feature_returns_expected_value(self):
        ...
```

**Why gc.collect() is mandatory**: AsyncMock/MagicMock objects create circular
references that prevent automatic garbage collection. Under pytest-xdist, mock
objects accumulate across tests in the same worker, leading to memory explosion
(observed: 217GB VIRT, 42GB RES). `gc.collect()` in teardown forces cleanup.

**Why xdist_group for non-unit tests**: Integration/e2e tests access shared
resources (databases, Redis, Docker). Without xdist_group, two tests modifying
the same resource can run on different workers and corrupt each other's state.
Unit tests use pure mocks with no shared state, so grouping them just adds
serialization overhead.

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

**ALWAYS use `spec=` parameter** to catch typos at test time.

**ALWAYS use `side_effect=` instead of `return_value=`** when the mock is a patch target for a module-level function (see xdist Safety Rule 1 above).

| Wrong | Correct |
|-------|---------|
| `AsyncMock()` | `AsyncMock(spec=TargetClass)` |
| `patch("mod.func", return_value=mock)` | `patch("mod.func", side_effect=lambda: mock)` |
| `obj.method = AsyncMock` | `obj.method = AsyncMock(spec=TargetClass.method)` |

```python
# CORRECT - spec + side_effect for xdist safety
mock_client = AsyncMock(spec=RedisClient)
mock_client.get = AsyncMock(side_effect=lambda *a, **kw: "value")

# OK - return_value on local mock methods (not a patched singleton)
mock_client = AsyncMock(spec=RedisClient)
mock_client.get.return_value = "value"  # Safe: mock_client is test-local

# WRONG - typos silently pass, fail in production
mock_client = AsyncMock()
mock_client.gett.return_value = "value"  # Undetected typo!

# WRONG - assigns class, not instance (AttributeError at runtime)
obj.method = AsyncMock  # Missing parentheses!
```

### External Service Mocks

| External | Mock Pattern |
|----------|-------------|
| Redis | `AsyncMock(spec=RedisClient)` + `side_effect=lambda` |
| LLM | `AsyncMock(spec=ChatModel)` + `side_effect=lambda` |
| OpenFGA | `AsyncMock(spec=OpenFGAClient)` + `side_effect=lambda` |
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

## Test Co-Evolution (CRITICAL — Prevents Test Drift)

When changing implementation code, you MUST update corresponding tests in the
same changeset. Search for affected assertions before committing.

| Change | Update |
|--------|--------|
| API response types / Pydantic models / OpenAPI schemas | Contract tests validating those shapes |
| Component text, classes, callbacks, DOM structure | Component test assertions (`getByText`, `toHaveClass`, etc.) |
| Default values (theme, preferences, config) | All tests asserting those defaults |
| Barrel file exports (`index.ts`) | `lazy.test.ts` and barrel import tests |
| Routes / navigation items | `route-coverage.test.tsx` and nav tests |
| New API endpoints | MSW handlers in `src/mocks/handlers/` |

## Vitest Test Isolation (CRITICAL — Prevents Flaky Tests)

These rules prevent the most common sources of frontend test flakiness.
The global `setup.ts` handles `cleanup()`, `clearStorageMocks()`, `clearAllMocks()`,
and `gc()` in afterEach — but these patterns still cause issues within a file.

### Rule 1: Always include afterEach with cleanup + timer restoration

Every test file MUST have `afterEach` with `cleanup()` and timer restoration
if fake timers are used. The global `setup.ts` calls `cleanup()` and
`clearAllMocks()` but does NOT call `clearTimers()` (by design).

```typescript
// CORRECT - Explicit cleanup + timer restoration
afterEach(() => {
  cleanup();
  vi.clearAllMocks();
  vi.useRealTimers(); // Required if ANY test in the file uses fake timers
});

// WRONG - Missing timer cleanup (fake timers leak to next test)
afterEach(() => {
  cleanup();
  vi.clearAllMocks();
  // Fake timers from previous test still active!
});
```

### Rule 2: Create Redux stores per-test, NEVER at module level

```typescript
// CORRECT - Fresh store per test
describe("MyComponent", () => {
  it("should render", () => {
    const store = createTestStore();
    render(<Provider store={store}><MyComponent /></Provider>);
  });
});

// WRONG - Shared store pollutes between tests
const store = createTestStore(); // Module-level = shared!
describe("MyComponent", () => {
  it("test 1", () => { render(...); }); // Modifies store state
  it("test 2", () => { render(...); }); // Sees stale state from test 1
});
```

### Rule 3: Use vi.importActual for partial mocking — EXCEPT heavy barrels

For **small modules**, spread the actual exports and override only what you need:

```typescript
// CORRECT - Small module: preserves all exports, overrides specific ones
vi.mock("../utils/cn", async () => {
  const actual = await vi.importActual("../utils/cn");
  return { ...actual, cn: vi.fn((...args) => args.join(" ")) };
});
```

**NEVER use `vi.importActual` on heavy barrel exports** — they load the
entire dependency tree into each fork worker, causing OOM (>8GB heap).

| Module | Lines | Re-exports | OOM Risk |
|--------|-------|------------|----------|
| `../../api` (`src/api/index.ts`) | 5,132 | ~200 | **CRITICAL** |
| `../../hooks` (`src/hooks/index.ts`) | 577 | 107 | **CRITICAL** |
| Any barrel `index.ts` with >50 exports | varies | varies | **HIGH** |

```typescript
// WRONG - Loads 5132-line barrel into fork worker → OOM at >8GB
vi.mock("../../api", async () => {
  const actual = await vi.importActual("../../api"); // 💀 OOM
  return { ...actual, useMyQuery: vi.fn() };
});

// WRONG - hooks barrel transitively imports api barrel → OOM
vi.mock("../../hooks", async () => {
  const actual = await vi.importActual("../../hooks"); // 💀 OOM
  return { ...actual, useMyHook: vi.fn() };
});

// CORRECT - Mock only the hooks your component actually uses
vi.mock("../../hooks", () => ({
  useRiskAssessment: vi.fn(() => ({
    riskScore: 0.72,
    riskLevel: "medium",
    isLoading: false,
    error: null,
  })),
  useDecisionHistory: vi.fn(() => ({
    similarDecisions: [],
    isLoading: false,
    error: null,
  })),
}));
```

**How to identify which hooks to mock**: Read the component source to find
which named imports it uses from the barrel, then mock only those.

### Rule 4: Never double-wrap with Router providers

`TestProvider` already includes `RouterProvider`. Adding `TestRouter`,
`MemoryRouter`, or another `RouterProvider` inside causes "Router inside Router" errors.

```typescript
// CORRECT - TestProvider includes routing
render(<TestProvider><MyComponent /></TestProvider>);

// CORRECT - Custom wrapper that already has Router
render(<MyComponent />, { wrapper: createWrapper(store) });

// WRONG - Double Router
render(
  <TestProvider>
    <MemoryRouter>   {/* DUPLICATE - TestProvider already has Router */}
      <MyComponent />
    </MemoryRouter>
  </TestProvider>
);
```

### Rule 5: Scope mock variables to describe blocks or beforeEach

Module-level `vi.fn()` variables accumulate state across tests.
`vi.clearAllMocks()` clears call history but NOT mock implementations.

```typescript
// CORRECT - Fresh mock per test via beforeEach
describe("MyComponent", () => {
  let mockNavigate: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    mockNavigate = vi.fn();
    vi.clearAllMocks();
  });
});

// ACCEPTABLE - Module-level with clearAllMocks in beforeEach
// (OK because restartWorkersAfter=1 prevents inter-file leakage)
const mockNavigate = vi.fn();

beforeEach(() => {
  vi.clearAllMocks(); // Clears call history (not implementations)
});

// WRONG - Module-level without any reset
const mockNavigate = vi.fn();
// No beforeEach cleanup — call counts accumulate across tests
```

### Rule 5b: Use mockReset() to clear mockResolvedValueOnce queues

`vi.clearAllMocks()` clears call history but does NOT clear unconsumed
`mockResolvedValueOnce` values. These leak between tests and cause the
NEXT test to receive a stale mock response.

```typescript
// CORRECT - Reset mock before setting up new behavior
describe("resolveConflict", () => {
  it("test A", async () => {
    mockFetch
      .mockResolvedValueOnce({ ok: false, status: 409 })
      .mockResolvedValueOnce({ ok: true }); // Unconsumed if test only calls once
    // ...
  });

  it("test B", async () => {
    mockFetch.mockReset(); // Clears unconsumed Once queue from test A
    mockFetch.mockResolvedValueOnce({ ok: false, status: 409 });
    // ...
  });
});

// WRONG - Relies on clearAllMocks to clean up
beforeEach(() => {
  vi.clearAllMocks(); // Does NOT clear mockResolvedValueOnce queue!
});
```

### Rule 6: userEvent — await always, prefer fireEvent for timer-heavy components

**Always await** `userEvent` interactions:
```typescript
const user = userEvent.setup();
await user.click(button);    // CORRECT
user.click(button);          // WRONG - race condition
```

**CRITICAL**: `userEvent` v14 hangs indefinitely with components that have
pending timers (`setTimeout`, `setInterval`, `rAF`) or are rendered inside
`RouterProvider` (which uses React concurrent transitions). Symptoms:
test passes in isolation with `-t` filter, but hangs when run with other tests.

**Use `fireEvent` instead** when the component uses any of:
- `useDebouncedValue` / `useThrottledCallback` (setTimeout-based hooks)
- `motion.button` / `motion.div` (requestAnimationFrame-based)
- Heavy re-render cycles triggered by state changes

```typescript
// CORRECT - fireEvent for timer-heavy components
fireEvent.click(screen.getByTestId("filter-button"));
fireEvent.change(screen.getByTestId("search-input"), {
  target: { value: "query" },
});

// WRONG - hangs with timer-heavy components inside RouterProvider
const user = userEvent.setup();
await user.click(screen.getByTestId("filter-button")); // 💀 hangs
```

See also Rule 15 for mocking timer-based hooks.

### Rule 7: Use waitFor for async assertions

```typescript
await waitFor(() => {
  expect(screen.getByText("Loaded")).toBeInTheDocument();
});

// With timeout for slow operations
await waitFor(() => { expect(mockFn).toHaveBeenCalled(); }, { timeout: 1000 });
```

### Rule 8: Use beforeAll/afterAll ONLY for immutable setup

`beforeAll` is for read-only setup (MSW `server.listen()`). Mutable globals
must use `beforeEach`/`afterEach` to prevent leaks between tests.

### Rule 9: Keep test files under 1,000 lines

Test files >1,000 lines consume 800MB+ each and trigger OOM in sharded runs.
Split into multiple files by concern (e.g., `Component.core.test.tsx`,
`Component.features.test.tsx`, `Component.integration.test.tsx`).

A pre-commit hook enforces this limit via `scripts/check-test-file-size.sh`.

### Rule 10: Mock motion/react inline (hoisting requirement)

Due to Vitest's `vi.mock()` hoisting, `createMotionMock()` from test-utils
cannot be used directly. Copy the pattern inline.

```typescript
// CORRECT - Inline mock with filterMotionProps
vi.mock("motion/react", () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...filterMotionProps(props)}>{children}</div>,
  },
  AnimatePresence: ({ children }: any) => <>{children}</>,
  useReducedMotion: () => false,
}));

// WRONG - Import from test-utils (hoisting breaks this)
vi.mock("motion/react", () => createMotionMock()); // ERROR: hoisted above import
```

### Rule 11: Forward data-testid in wrapper components

Wrapper components (SelectionCard, FormField) MUST accept and forward
`data-testid` to the rendered DOM element. Silently dropping it causes
hard-to-diagnose test failures.

### Rule 12: Never use tight timing thresholds in performance tests

Under 8-shard parallel load, render times are 4-5x slower than solo.
Use relative comparisons (`expect(optimized).toBeLessThan(baseline * 0.5)`)
or generous thresholds (5x solo baseline). Never `expect(time).toBeLessThan(500)`.

### Rule 13: Mark unimplemented feature tests as .todo()

When writing TDD tests for planned features (e.g., "ADR-0102 Popup Mode"),
mark them as `.todo()` until the feature is implemented. This prevents
false negatives in the test suite while preserving the test specification.

```typescript
// CORRECT - Feature planned but not implemented
describe("Popup Mode (ADR-0102)", () => {
  it.todo("should detect popup mode when window.opener exists");
  it.todo("should post message to opener on success");
});

// WRONG - Full test body for unimplemented feature (fails every run)
it("should detect popup mode", async () => {
  // Test body expects behavior that doesn't exist yet
  await waitFor(() => { expect(postMessage).toHaveBeenCalled(); }); // Always times out
});
```

### Rule 14: Wait for specific values in debounced storage assertions

When testing debounced persistence (e.g., preferences saving after 500ms),
use `waitFor` to assert the SPECIFIC expected value, not just that the
function was called. The first call may be from initialization, not the update.

```typescript
// CORRECT - Wait for specific updated value
await waitFor(
  () => {
    const calls = vi.mocked(storage.set).mock.calls;
    const lastCall = calls[calls.length - 1];
    expect(lastCall[1].hitl.enabled).toBe(false); // Specific value
  },
  { timeout: 1500 },
);

// WRONG - Waits for any call (may match initialization, not update)
await waitFor(() => {
  expect(storage.set).toHaveBeenCalled(); // Resolves immediately from init
});
const lastCall = vi.mocked(storage.set).mock.calls.slice(-1)[0];
expect(lastCall[1].hitl.enabled).toBe(false); // Fails - init value is true
```

### Rule 15: Mock timer-based hooks to prevent hangs

Hooks that use `setTimeout`/`setInterval` internally create pending macrotasks
that leak between tests and block `userEvent` event dispatch. Mock them to
return values synchronously.

```typescript
// CORRECT - Mock the utility module, return values synchronously
vi.mock("../utils/performance", () => ({
  useDebouncedValue: (value: unknown) => value,
  useStableCallback: (callback: unknown) => callback,
}));

// WRONG - Loading the real hook creates setTimeout(150ms) per render
// which leaks across test boundaries and causes userEvent hangs
```

**Common timer-based hooks to mock**:

| Hook | Timer | Mock Pattern |
|------|-------|-------------|
| `useDebouncedValue` | `setTimeout` | `(value) => value` |
| `useThrottledCallback` | `setTimeout` | `(callback) => callback` |
| `useBatchedUpdates` | `requestAnimationFrame` | Return items directly |

**When NOT to mock**: If the test specifically validates debounce/throttle
behavior, use `vi.useFakeTimers()` with `vi.advanceTimersByTimeAsync()` instead.

## Frontend OOM Prevention (CRITICAL)

The frontend has **810+ test files** that cause OOM when run together.

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
# WRONG - will OOM with 810+ test files
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

**Debugging failures**: Failed shard logs are preserved in `.vitest-shard-logs/`:
```bash
# After a failing run, inspect specific shard log
cat .vitest-shard-logs/shard-14.log

# Re-run a specific failing file directly
npx vitest run src/path/to/failing.test.tsx

# The summary shows all failing test files and their shard numbers
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

## pytest-xdist Safety (CRITICAL)

Tests run in parallel via `pytest -n auto` (xdist). Tests on the **same worker share a process**, so module-level singletons persist between tests. The following patterns prevent cross-test contamination.

### Rule 1: NEVER use `return_value=` on patched singletons

When patching dependency injection getters (e.g., `get_session_service`, `get_sandbox_runner`, `get_openfga_client`), **always use `side_effect=lambda`** instead of `return_value=`.

```python
# CORRECT - Fresh evaluation per call, immune to xdist contamination
with patch(
    "module.get_service",
    side_effect=lambda: mock_service,
):
    ...

# WRONG - return_value stored on Mock object; can be mutated by other tests
with patch(
    "module.get_service",
    return_value=mock_service,
):
    ...
```

**Why**: `return_value=X` stores X as a mutable attribute on the Mock. If the Mock leaks across test boundaries (common under xdist), the stored value can be corrupted by another test. `side_effect=lambda: X` creates a fresh return on every call.

**When this applies**: Any `patch()` that replaces a function used for dependency injection, singleton access, or factory creation. Common targets:
- `get_*` functions (get_session_service, get_openfga_client, get_sandbox_runner, etc.)
- `feature_flags` module-level instances
- `settings` module-level instances
- `is_feature_enabled` / `is_*_enabled` functions

**When `return_value=` is OK**: On fresh MagicMock objects created locally within a test (not on patched module-level functions). E.g., `mock = MagicMock(); mock.method.return_value = "x"` is safe if `mock` doesn't escape the test scope.

### Rule 2: Reset singletons in setup/teardown

```python
def setup_method(self):
    """Reset singletons before each test."""
    from mcp_server_langgraph.core.dependencies import reset_singleton_dependencies
    reset_singleton_dependencies()

def teardown_method(self):
    """Reset singletons and force GC after each test."""
    from mcp_server_langgraph.core.dependencies import reset_singleton_dependencies
    reset_singleton_dependencies()
    gc.collect()
```

### Rule 3: Bypass resilience decorators in LLM factory tests

`LLMFactory.ainvoke()` is wrapped by 4 decorators (circuit_breaker, retry_with_backoff, with_timeout, with_bulkhead) that capture module-level singletons in closures. Under xdist, these singletons get contaminated.

```python
# CORRECT - Unwrap ainvoke to bypass decorator singletons
def _get_unwrapped_ainvoke():
    fn = LLMFactory.ainvoke
    while hasattr(fn, "__wrapped__"):
        fn = fn.__wrapped__
    return fn

# In tests, patch ainvoke with the unwrapped version
with patch.object(LLMFactory, "ainvoke", _get_unwrapped_ainvoke()):
    ...

# WRONG - Calling ainvoke with contaminated decorator singletons
result = await factory.ainvoke(messages)  # RetryExhaustedError!
```

### Rule 4: Feature flag isolation

Feature flags are module-level singletons. Always patch at the **import site**, not the definition site.

```python
# CORRECT - Patch where the flag is read, use side_effect
with patch(
    "mcp_server_langgraph.tools.bash_tools.feature_flags"
) as mock_flags:
    mock_flags.enable_bash_tool = True
    ...

# CORRECT - For is_feature_enabled functions
with patch(
    "mcp_server_langgraph.privacy.middleware.is_feature_enabled",
    side_effect=lambda *a, **kw: False,
):
    ...

# WRONG - Patching the source module (other imports won't see it)
with patch(
    "mcp_server_langgraph.core.feature_flags.feature_flags"
) as mock_flags:
    ...  # Only works if the consumer imports via this exact path
```

### Rule 5: xdist_group — REQUIRED for non-unit tests, optional for unit tests

Non-unit test classes (integration, contract, e2e, meta, benchmarks) MUST use
`@pytest.mark.xdist_group`. Unit tests (`tests/unit/`) do NOT need it — they
use pure mocks with no shared mutable state, and grouping them just adds
serialization overhead (Phase 4.2: 77% of groups are singletons).

```python
# CORRECT - Non-unit test with xdist_group (REQUIRED)
@pytest.mark.integration
@pytest.mark.xdist_group(name="llm_factory")
class TestLLMFactory:
    def teardown_method(self):
        gc.collect()
    ...

# CORRECT - Unit test without xdist_group (OPTIONAL)
@pytest.mark.unit
class TestLLMFactoryUnit:
    def teardown_method(self):
        gc.collect()
    ...
```

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

### Memory Safety (MANDATORY — see Required Test Class Structure)

Every test class MUST have `teardown_method()` with `gc.collect()`.
This is enforced by `validate-test-isolation` and `check-test-memory-safety`
pre-push hooks. Omitting it causes OOM in CI (217GB memory observed).

```python
# CORRECT - Prevent memory leaks in xdist
def teardown_method(self):
    gc.collect()

# WRONG - Missing teardown entirely (most common violation)
# (no teardown_method defined)

# WRONG - Teardown without gc.collect
def teardown_method(self):
    pass
```
