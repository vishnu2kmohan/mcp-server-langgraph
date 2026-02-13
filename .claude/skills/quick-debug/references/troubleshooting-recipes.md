# Troubleshooting Recipes

Diagnostic commands and fix templates for the `/quick-debug` skill, organized by error category.

---

## Diagnostic Commands by Error Type

### For Import Errors

```bash
# Check if module exists
uv run --frozen python -c "import {module}" 2>&1

# Check installed packages
uv pip list | grep {module}

# Check for unstaged files
git status --short | grep "^ M"

# Verify Python environment
which python
uv run --frozen python --version
```

### For Test Failures

```bash
# Run failing test in verbose mode
uv run --frozen pytest {test_file}::{test_name} -vv -s

# Check test dependencies
grep -r "import.*{module}" tests/

# Check for mock issues
grep -A 5 "AsyncMock\|MagicMock" {test_file}
```

### For Async Errors

```bash
# Check event loop configuration
grep "asyncio_mode" pyproject.toml

# Check for await issues
grep -n "async def\|await" {file} | head -20

# Check fixture scopes
grep -B 2 "@pytest.fixture" {test_file}
```

### For Connection Errors

```bash
# Check if services are running
docker ps | grep -E "redis|postgres|openfga"

# Check service health
curl -s http://localhost:8080/healthz || echo "Service not responding"

# Check port availability
netstat -tuln | grep {port}
```

---

## Quick Fix Templates

### Import Error Fix

```bash
# Add missing import
# In {file}:{line}, add:
from {module} import {name}

# Or install missing dependency
uv pip install {package}

# Or commit missing files
git add {file}
git commit -m "fix: add missing {file}"
```

### Test Failure Fix

```python
# Update test assertion
# In {test_file}:{line}, change:
assert result == expected  # Old

# To:
assert result == actual_value  # New (with correct value)
```

### Async Error Fix

```python
# Add missing await
# In {file}:{line}, change:
result = async_function()  # Missing await

# To:
result = await async_function()  # Fixed
```

### Mock Error Fix

```python
# Use AsyncMock for async functions
# In {test_file}:{line}, change:
@patch("module.async_func")  # Wrong

# To:
@patch("module.async_func", new_callable=AsyncMock)  # Correct
```

---

## Usage Examples

### Example 1: Quick Debug Without Arguments

```
User: /quick-debug

Claude:
Looking for recent errors...

Found 3 recent test failures:
1. tests/test_session.py::test_create - AssertionError
2. tests/test_auth.py::test_login - ImportError
3. tests/integration/test_api.py::test_health - ConnectionError

Analyzing most recent: ImportError in test_auth.py

Error: ImportError: cannot import name 'get_session_store'
Category: Import Error

Diagnostics:
- Module exists: src/mcp_server_langgraph/auth/session.py
- Function exists: get_session_store (line 42)
- Uncommitted changes detected in session.py

Root Cause: Function 'get_session_store' exists in working copy but not committed.

Quick Fix:
```bash
git add src/mcp_server_langgraph/auth/session.py
git commit -m "fix: add missing session store functions"
```

After fix, run:
```bash
uv run --frozen pytest tests/test_auth.py::test_login -v
```
```

### Example 2: Debug Specific Error

```
User: /quick-debug "RuntimeError: Event loop is closed"

Claude:
Analyzing: RuntimeError: Event loop is closed
Category: Async/Event Loop Error

Common causes:
1. Session-scoped async fixture
2. Trying to use closed loop
3. Multiple event loops created

Searching codebase for async fixtures...

Found issue in tests/conftest.py:34
```python
@pytest.fixture(scope="session")  # <- Problem: session scope
async def redis_client():
    client = Redis()
    yield client
    await client.close()  # Loop already closed!
```

Quick Fix:
```python
@pytest.fixture  # <- Remove scope="session"
async def redis_client():
    client = Redis()
    yield client
    await client.close()
```

Explanation: Session-scoped async fixtures share one event loop across all tests,
but the loop gets closed before the fixture cleanup runs.

After fix, run:
```bash
uv run --frozen pytest tests/ -v -k "redis"
```
```

### Example 3: Docker Service Debug

```
User: /quick-debug "ConnectionError: Failed to connect to Redis"

Claude:
Analyzing: ConnectionError: Failed to connect to Redis
Category: Connection/Service Error

Checking Docker services...

Docker Status:
- postgres: Up (healthy)
- openfga: Up (healthy)
- redis: Down

Root Cause: Redis service not running

Quick Fix (1 minute):
```bash
docker compose up -d redis

# Wait for health check
timeout 30s bash -c 'until docker compose ps redis | grep healthy; do sleep 1; done'
```

Verification:
```bash
docker compose ps redis
redis-cli ping  # Should return PONG
```

After service is up, re-run tests:
```bash
uv run --frozen pytest tests/test_session.py -v
```

Prevention:
Add to .claude/memory/:
- Always run `docker compose ps` before test sessions
- Add health checks to docker-compose.yml
- Consider `make setup-infra` before testing
```
