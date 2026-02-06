---
purpose: Reference guide for writing tests with pytest, vitest, and Hypothesis
priority: high
category: testing
test-count: 437+
last-updated: 2026-02-05
---

# Testing Patterns Context

---

## Test Suite Overview

| Category | Count | Purpose |
|----------|-------|---------|
| Unit | 350+ | Fast, no external dependencies |
| Integration | 50+ | Requires infrastructure |
| Property | 27+ | Hypothesis edge case discovery |
| Contract | 20+ | MCP protocol compliance |
| Performance | 10+ | Regression tracking |

**Coverage**: 69% | **Pass Rate**: 99.3%

---

## Testing Philosophy

| Principle | Description |
|-----------|-------------|
| Mock externals | Don't rely on real services in unit tests |
| Behavior over implementation | Test what, not how |
| Comprehensive edge cases | Happy path + error cases |
| Property-based testing | Use Hypothesis for invariants |
| Clear naming | `test_<what>_<condition>_<expected>` |

---

## Common Test Patterns

### Pattern 1: Async Tests with Fixtures

```python
@pytest.mark.asyncio
@pytest.mark.unit
async def test_create_session(self, store):
    """Test creating a session"""
    # Given
    user_id = "user:alice"
    # When
    session_id = await store.create(user_id=user_id, username="alice", roles=["user"])
    # Then
    assert session_id is not None
    session = await store.get(session_id)
    assert session.user_id == user_id
```

**Key Points**: Use `@pytest.mark.asyncio`, fixtures for setup, `AsyncMock` for mocking

---

### Pattern 2: Mocking External Dependencies

```python
@patch("mcp_server_langgraph.llm.factory.create_llm_from_config")
async def test_route_input(self, mock_create_llm):
    mock_model = MagicMock()
    mock_model.ainvoke = AsyncMock(return_value=AIMessage(content="Hello!"))
    mock_create_llm.return_value = mock_model
    # ... test logic
```

**Key Points**: Patch at import point, use `MagicMock` for sync, `AsyncMock` for async

---

### Pattern 3: Property-Based Testing (Hypothesis)

```python
@pytest.mark.property
@given(username=st.sampled_from(["alice", "bob"]), expiration=st.integers(1, 86400))
@settings(max_examples=50, deadline=2000)
def test_jwt_roundtrip(self, username, expiration):
    token = auth.create_token(username, expires_in=expiration)
    result = run_async(auth.verify_token(token))
    assert result.valid and result.payload["username"] == username
```

---

### Pattern 4: Parametrized Tests

```python
@pytest.mark.parametrize("username,expected_roles", [
    ("alice", ["user", "premium"]),
    ("admin", ["admin"]),
])
async def test_user_roles(username, expected_roles):
    user = await provider.get_user(username)
    assert set(user.roles) == set(expected_roles)
```

---

### Pattern 5: Error Handling Tests

```python
async def test_create_exceeds_limit(self, store):
    for i in range(3):  # At limit
        await store.create(user_id=f"user:{i}", username=f"user{i}", roles=["user"])
    with pytest.raises(ValueError, match="Maximum concurrent sessions"):
        await store.create(user_id="user:4", username="user4", roles=["user"])
```

---

## Common Mock Fixtures

| Mock | Pattern |
|------|---------|
| Redis | `redis.get=AsyncMock(return_value=None)`, `redis.set=AsyncMock(return_value=True)` |
| OpenFGA | `client.check_permission=AsyncMock(return_value=True)` |
| LLM | `llm.ainvoke=AsyncMock(return_value=AIMessage(content="..."))` |
| Prometheus | `prom.custom_query=MagicMock(return_value=[...])` |

---

## Async Patterns

### Event Loop for Property Tests

```python
def run_async(coro):
    """Run async with proper cleanup for property tests"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        for task in asyncio.all_tasks(loop):
            task.cancel()
        loop.run_until_complete(asyncio.gather(*asyncio.all_tasks(loop), return_exceptions=True))
        loop.close()
```

### Async Fixture Loop Scope

```python
@pytest.fixture(scope="session", loop_scope="session")
async def postgres_pool():
    pool = await asyncpg.create_pool(...)
    yield pool
    await pool.close()
```

**Global config** (`pyproject.toml`): `asyncio_default_fixture_loop_scope = "session"`

### AsyncMock Best Practices

```python
# ❌ WRONG - Unconfigured mock is truthy
mock = AsyncMock()
if await mock.check():  # Always True!

# ✅ CORRECT - Explicit return value
mock = AsyncMock()
mock.check.return_value = False
```

---

## Meta-Test Patterns

| Pattern | Purpose | Location |
|---------|---------|----------|
| Marker validation | Ensure all markers registered | `tests/meta/test_pytest_markers.py` |
| Fixture organization | No duplicate autouse fixtures | `tests/meta/test_fixture_organization.py` |
| Memory safety | Mocks have gc.collect() teardown | `tests/meta/test_memory_safety.py` |
| CI parity | Pre-push matches CI | `tests/meta/ci/test_workflow_parity.py` |
| Doc validation | Code examples syntactically valid | `tests/meta/validation/test_documentation.py` |

---

## Frontend Test Patterns (Vitest)

### Mock Cleanup

| Function | Clears History | Resets mockReturnValue | Restores Original |
|----------|----------------|------------------------|-------------------|
| `vi.clearAllMocks()` | ✅ | ❌ | ❌ |
| `vi.resetAllMocks()` | ✅ | ✅ (undefined) | ❌ |
| `vi.restoreAllMocks()` | ✅ | ✅ | ✅ (spies) |

**Key**: Always reset mocks in `beforeEach`, don't rely on `clearAllMocks()` alone.

### RTK Query Hook Mocking

```typescript
beforeEach(() => {
  vi.clearAllMocks();
  (useGetDataQuery as ReturnType<typeof vi.fn>).mockReturnValue({
    data: mockDefaultData, isLoading: false, error: null,
  });
});
```

### AnimatePresence Mock

```typescript
vi.mock("motion/react", async () => {
  const actual = await vi.importActual("motion/react");
  return {
    ...actual,
    useReducedMotion: vi.fn(() => false),
    AnimatePresence: ({ children }) => <>{children}</>,
  };
});
```

### Reduced Motion Testing (WCAG 2.2 AA)

```typescript
const mockUseReducedMotion = vi.fn();
// When reduced motion preferred: variants=undefined, layout=false
// When not preferred: variants=defined, layout=true
```

---

## ADR-0091 API Response Transformation

Maintain two mock objects: `mockDataRaw` (snake_case) and `mockData` (camelCase).

```typescript
// MSW returns snake_case
const mockRaw = { auth_type: "oauth2", default_url: "..." };
// Assertions use camelCase
const mockExpected = { authType: "oauth2", defaultUrl: "..." };
```

---

## Test Markers

```python
@pytest.mark.unit          # Fast, no dependencies
@pytest.mark.integration   # Requires infrastructure
@pytest.mark.property      # Hypothesis tests
@pytest.mark.contract      # Protocol compliance
@pytest.mark.asyncio       # Async tests
```

**Running**: `pytest -m unit`, `pytest -m "unit and not slow"`

---

## Test Naming: `test_<what>_<condition>_<expected>`

| Good | Bad |
|------|-----|
| `test_create_session_success` | `test_session` |
| `test_get_nonexistent_returns_none` | `test_1` |
| `test_jwt_roundtrip` | `test_it_works` |

---

## Test Structure (Given-When-Then)

```python
async def test_feature(self):
    # Given - Setup
    user = create_user("alice")
    # When - Execute
    result = await feature.execute(user)
    # Then - Assert
    assert result.success is True
```

---

## Common Assertions

| Type | Pattern |
|------|---------|
| Success | `assert result is not None`, `assert result.success is True` |
| Error | `with pytest.raises(ValueError, match="message")` |
| Collection | `assert len(items) == 3`, `assert set(actual) == set(expected)` |
| Async | `results = await asyncio.gather(...)`, `assert all(r.success for r in results)` |

---

## Running Tests

```bash
pytest                      # All tests
pytest -m unit              # Unit only
pytest -x                   # Stop on first failure
pytest --cov=src            # With coverage
pytest -n auto              # Parallel (all CPUs)
pytest tests/test_x.py::TestClass::test_method  # Specific
```

---

## Pydantic Feature Flag Mocking

Standard mocking fails on Pydantic models. Use direct manipulation:

```python
original = feature_flags.enable_feature
try:
    feature_flags.enable_feature = False
    with patch.dict(os.environ, {k: v for k, v in os.environ.items() if k != "FF_TEST_MODE"}, clear=True):
        with pytest.raises(FeatureDisabledError):
            some_gated_function()
finally:
    feature_flags.enable_feature = original
```

---

## Frontend Test File Splitting

**Problem**: Large files (500+ lines) cause OOM in CI.
**Solution**: Split by category: `<Component>.<category>.test.tsx`

| Category | Tests |
|----------|-------|
| rendering | Basic display, structure |
| interaction | User events, callbacks |
| features | Specific feature areas |
| integration | External hooks, APIs |
| advanced | Edge cases, accessibility |

**Target**: 200-400 lines, 10-25 tests per file

---

## Data Flow Integration Testing

**Purpose**: E2E tests verifying Producer → Store → API → UI flows.
**Location**: `tests/integration/dataflow/`

### Memory Safety (pytest-xdist)

```python
def setup_method(self):
    from mcp_server_langgraph.core.dependencies import reset_singleton_dependencies
    reset_singleton_dependencies()

def teardown_method(self):
    reset_singleton_dependencies()
    gc.collect()
```

| Suite | Pattern | Markers |
|-------|---------|---------|
| Cost Flow | LLM Factory → CostMetrics → Storage → API | `cost` |
| Audit Flow | Producer → AuditService → Repository → API | `audit` |
| Session Flow | Chat API → SessionRepo → Storage → Sessions API | `session` |

---

## OTEL Data Flow Testing

Validate attribute naming at emission AND query layers:

```python
@pytest.mark.dataflow
async def test_dot_notation_used():
    # Verify span.set_attribute uses "session.id" not "session_id"
    # Verify query uses tags["session.id"] not tags["session_id"]
```

---

## Quick Reference

| Task | Steps |
|------|-------|
| New auth feature | 1. Test class 2. Fixture 3. Mock deps 4. Happy path 5. Error cases 6. Markers |
| New API endpoint | Contract tests, request/response validation, error codes, auth |
| New compliance | Unit with mocks, integration with real data, edge cases, fallbacks |

---

**Related Files**:
- Test config: `pyproject.toml`
- Testing guide: `docs-internal/testing/TESTING.md`
- CI workflow: `.github/workflows/ci.yaml`
- Vitest config: `src/mcp_server_langgraph/studio/frontend/vitest.config.ts`
- Data flow tests: `tests/integration/dataflow/`

---

**Auto-Generated**: Update when new patterns emerge
**Last Review**: 2026-01-31
