---
purpose: Prevent common async, subprocess, and Docker errors in CI/CD pipelines
priority: high
category: error-prevention
last-updated: 2026-02-05
---

# Task Spawn Error Prevention

---

## Error Categories

| Category | Root Cause | Prevention |
|----------|-----------|------------|
| Import errors | Uncommitted code | Verify `git status` before CI |
| Async mock errors | Sync mock for async function | Use `AsyncMock` + `new_callable` |
| Event loop errors | Lifecycle issues | Function-scoped async fixtures |
| Subprocess hangs | No timeout | Always use `timeout=` parameter |
| Coverage missing | Container isolation | Volume mounts for coverage |
| Blocking I/O | Sync in async context | Use async libraries (httpx, asyncpg) |

---

## Quick Fix Reference

### Import Error in CI

```bash
# Check for uncommitted files
git status --short
git add <missing-files>
git commit --amend --no-edit
git push --force-with-lease
```

### Event Loop Closed

```python
# Wrong: session-scoped async fixture
@pytest.fixture(scope="session")  # Remove scope
async def fixture():
    ...

# Correct: function-scoped (default)
@pytest.fixture
async def fixture():
    ...
```

### Test Hangs

```python
# Add timeout
result = await asyncio.wait_for(operation(), timeout=30)

# Or for subprocess
subprocess.run(cmd, timeout=30, capture_output=True)
```

---

## Async Mock Patterns

### Patching Async Functions

```python
# Wrong
@patch("module.async_function")

# Correct
@patch("module.async_function", new_callable=AsyncMock)
async def test_something(self, mock_async_func):
    mock_async_func.return_value = "result"
```

### Creating Async Mocks

```python
from unittest.mock import AsyncMock, MagicMock

# For async methods
mock_client = AsyncMock()
mock_client.fetch_data.return_value = {"data": "value"}

# For sync methods on async class
mock_client.sync_method = MagicMock(return_value="value")
```

---

## Subprocess Patterns

### Always Use

```python
result = subprocess.run(
    ["cmd", "arg"],
    capture_output=True,  # Required
    text=True,            # Decode as UTF-8
    timeout=30,           # Required
    check=True            # Raise on failure
)
```

### Context Manager for Cleanup

```python
class TestEnvironment:
    def __enter__(self):
        subprocess.run(["docker", "compose", "up", "-d"], check=True)
        return self

    def __exit__(self, *args):
        subprocess.run(["docker", "compose", "down", "-v"], check=True)
```

---

## Async-First Architecture

### Library Selection

| Component | Use | Avoid |
|-----------|-----|-------|
| HTTP Client | `httpx.AsyncClient` | `requests` |
| Redis | `redis.asyncio` | `redis` |
| LLM | `litellm.acompletion` | `litellm.completion` |
| Database | `asyncpg` | `psycopg2` |
| Web Framework | `FastAPI` | `Flask` |

### Concurrent Execution

```python
# Run multiple I/O operations in parallel
results = await asyncio.gather(
    get_session(user_id),
    get_user_roles(user_id),
    get_preferences(user_id),
)
```

---

## Pre-Spawn Checklists

### Async Task
- [ ] Function uses `async def`
- [ ] All I/O uses async libraries
- [ ] All async calls use `await`
- [ ] Test has `@pytest.mark.asyncio`
- [ ] Mocks use `AsyncMock`
- [ ] Timeout with `asyncio.wait_for()`

### Subprocess
- [ ] `capture_output=True`
- [ ] `timeout=<seconds>`
- [ ] Context manager or try/finally cleanup
- [ ] Health check polling with timeout
- [ ] Error handling for `CalledProcessError`

### Integration Tests
- [ ] Docker Compose has volume mounts for coverage
- [ ] Timeout for service startup
- [ ] Health checks in docker-compose.yml
- [ ] CI copies coverage from containers

---

## Emergency Troubleshooting

| Symptom | Diagnosis | Fix |
|---------|-----------|-----|
| ImportError in CI | `git diff src/` | Commit missing files |
| Event loop closed | Check fixture scope | Use function scope |
| Test hangs | No timeout | Add `asyncio.wait_for()` |
| Coverage missing | No volume mount | Add Docker volume |
| AsyncMock not awaitable | Missing `new_callable` | Add `new_callable=AsyncMock` |

---

## Validation Commands

```bash
# Find async patches without AsyncMock
rg '@patch.*' tests/ | rg -v 'new_callable=AsyncMock' | rg 'async def'

# Find subprocess.run without timeout
rg 'subprocess\.run\(' --type py | rg -v 'timeout='

# Check for orphaned containers
docker ps -a | grep mcp-server-langgraph
```

---

**Full Documentation**: `adr/adr-0019-async-first-architecture.md`
