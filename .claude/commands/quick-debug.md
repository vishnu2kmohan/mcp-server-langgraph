# Quick Debug

**Usage**: `/quick-debug` or `/quick-debug <error-message>`

**Purpose**: Fast debugging workflow for common issues

---

## 🐛 What This Command Does

Provides AI-assisted debugging workflow to quickly identify and fix common issues:

1. Analyzes error messages and stack traces
2. Suggests likely causes based on patterns
3. Recommends debugging steps
4. Provides quick fixes for common problems
5. Links to relevant code locations

---

## 🔍 Debugging Workflow

### Step 1: Capture Error Information

If error message provided as argument:
```bash
# Use provided error
ERROR_MSG="$ARGUMENTS"
```bash
If no argument, look for recent errors:
```bash
# Check recent test failures
uv run --frozen pytest --lf -v 2>&1 | tee /tmp/test_errors.txt

# Check recent git commits for fix mentions
git log -10 --oneline | grep -i "fix"

# Check application logs (if running)
tail -50 logs/app.log 2>/dev/null || echo "No app logs found"
```

### Step 2: Categorize Error Type

Analyze error message to determine category:

**Import Errors**:
```python
ImportError: cannot import name 'X'
ModuleNotFoundError: No module named 'X'
```

→ Missing dependency, uncommitted code, wrong Python env

**Test Failures**:
```yaml
AssertionError: X != Y
AttributeError: 'NoneType' object has no attribute 'X'
```

→ Logic error, missing mock, incorrect test setup

**Runtime Errors**:
```yaml
RuntimeError: Event loop is closed
asyncio.TimeoutError: timeout exceeded
```

→ Async issues, resource management, timeouts

**Type Errors**:
```yaml
TypeError: X() takes 2 positional arguments but 3 were given
mypy error: Argument has incompatible type
```

→ Function signature mismatch, type annotation issues

**Database/Connection Errors**:
```yaml
ConnectionError: Failed to connect to Redis
sqlalchemy.exc.OperationalError
```

→ Service not running, configuration issue, network problem

### Step 3: AI-Assisted Analysis

Provide context to Claude for analysis:

```bash
Analyzing error: {error_message}

Error Category: {category}
Recent Changes: {git log -5}
Modified Files: {git diff --name-only}
Test Status: {pytest status}

Please analyze this error and suggest:
1. Most likely root cause
2. Quick diagnostic steps
3. Potential fixes
4. Similar issues in codebase
```

### Step 4: Run Diagnostic Commands

Based on error category, run relevant diagnostics:

**For Import Errors**:
```bash
# Check if module exists
python -c "import {module}" 2>&1

# Check installed packages
uv pip list | grep {module}

# Check for unstaged files
git status --short | grep "^ M"

# Verify Python environment
which python
python --version
```bash
**For Test Failures**:
```bash
# Run failing test in verbose mode
uv run --frozen pytest {test_file}::{test_name} -vv -s

# Check test dependencies
grep -r "import.*{module}" tests/

# Check for mock issues
grep -A 5 "AsyncMock\|MagicMock" {test_file}
```

**For Async Errors**:
```bash
# Check event loop configuration
grep "asyncio_mode" pyproject.toml

# Check for await issues
grep -n "async def\|await" {file} | head -20

# Check fixture scopes
grep -B 2 "@pytest.fixture" {test_file}
```bash
**For Connection Errors**:
```bash
# Check if services are running
docker ps | grep -E "redis|postgres|openfga"

# Check service health
curl -s http://localhost:8080/healthz || echo "Service not responding"

# Check port availability
netstat -tuln | grep {port}
```

### Step 5: Suggest Quick Fixes

Provide actionable fixes based on analysis:

**Common Fix Templates**:

**Import Error Fix**:
```bash
# Add missing import
# In {file}:{line}, add:
from {module} import {name}

# Or install missing dependency
uv pip install {package}

# Or commit missing files
git add {file}
git commit -m "fix: add missing {file}"
```bash
**Test Failure Fix**:
```python
# Update test assertion
# In {test_file}:{line}, change:
assert result == expected  # Old

# To:
assert result == actual_value  # New (with correct value)
```

**Async Error Fix**:
```python
# Add missing await
# In {file}:{line}, change:
result = async_function()  # Missing await

# To:
result = await async_function()  # Fixed
```bash
**Mock Error Fix**:
```python
# Use AsyncMock for async functions
# In {test_file}:{line}, change:
@patch("module.async_func")  # Wrong

# To:
@patch("module.async_func", new_callable=AsyncMock)  # Correct
```

### Step 6: Generate Debug Report

Create structured debug report:

```markdown
# Debug Report

**Generated**: {timestamp}
**Error**: {error_message}
**Category**: {category}

## Analysis

**Root Cause**: {likely_cause}

**Evidence**:
- Recent changes in {files}
- Error occurs at {location}
- Related to {component}

## Diagnostic Results

{diagnostic_output}

## Recommended Fix

**Quick Fix** (1-2 minutes):
```{language}
{quick_fix_code}
```

**Proper Fix** (5-10 minutes):
```{language}
{proper_fix_code}
```

## Testing

After applying fix, run:
```bash
{test_command}
```css
## Prevention

To avoid this in future:
- {prevention_step_1}
- {prevention_step_2}

## Related Issues

Similar errors found:
- {related_issue_1}
- {related_issue_2}
```

---

## 🎯 Common Issue Patterns

### Pattern 1: ImportError After Refactoring

**Symptoms**:
```python
ImportError: cannot import name 'get_session_store'
```

**Quick Check**:
```bash
git diff --cached src/  # Check staged changes
git status --short      # Check unstaged changes
```bash
**Common Cause**: Function moved/renamed but import not updated

**Fix**:
```bash
# Find all usages
grep -r "get_session_store" src/ tests/

# Update imports
# Or add to __init__.py
```

### Pattern 2: AsyncMock Issues

**Symptoms**:
```yaml
TypeError: object MagicMock can't be used in 'await' expression
```

**Quick Check**:
```bash
grep -B 2 "@patch.*async" tests/{file}
```

**Common Cause**: Using MagicMock instead of AsyncMock

**Fix**:
```python
@patch("module.async_func", new_callable=AsyncMock)
```

### Pattern 3: Event Loop Closed

**Symptoms**:
```yaml
RuntimeError: Event loop is closed
```

**Quick Check**:
```bash
grep "scope=" tests/{file} | grep "session"
```python
**Common Cause**: Session-scoped async fixture

**Fix**:
```python
@pytest.fixture  # Remove scope="session"
async def fixture():
    ...
```

### Pattern 4: Docker Service Not Running

**Symptoms**:
```yaml
ConnectionError: Error -2 connecting to localhost:6379
```

**Quick Check**:
```bash
docker ps | grep redis
docker-compose ps
```bash
**Common Cause**: Service not started

**Fix**:
```bash
docker-compose up -d redis
# Wait for health check
sleep 2
```

### Pattern 5: Test Database State

**Symptoms**:
```yaml
IntegrityError: duplicate key value violates unique constraint
```

**Quick Check**:
```bash
# Check if database cleanup is working
grep "cleanup\|teardown" tests/{file}
```python
**Common Cause**: Test not cleaning up properly

**Fix**:
```python
@pytest.fixture
async def clean_db():
    yield
    # Cleanup after test
    await db.execute("DELETE FROM table")
```

---

## 🚀 Usage Examples

### Example 1: Quick Debug Without Arguments

```bash
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
✓ Module exists: src/mcp_server_langgraph/auth/session.py
✓ Function exists: get_session_store (line 42)
✗ Uncommitted changes detected in session.py

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

```python
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
@pytest.fixture(scope="session")  # ← Problem: session scope
async def redis_client():
    client = Redis()
    yield client
    await client.close()  # Loop already closed!
```

Quick Fix:
```python
@pytest.fixture  # ← Remove scope="session"
async def redis_client():
    client = Redis()
    yield client
    await client.close()
```yaml
Explanation: Session-scoped async fixtures share one event loop across all tests,
but the loop gets closed before the fixture cleanup runs.

After fix, run:
```bash
uv run --frozen pytest tests/ -v -k "redis"
```

```bash
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
- redis: Down ✗

Root Cause: Redis service not running

Quick Fix (1 minute):
```bash
docker-compose up -d redis

# Wait for health check
timeout 30s bash -c 'until docker-compose ps redis | grep healthy; do sleep 1; done'
```yaml
Verification:
```bash
docker-compose ps redis
redis-cli ping  # Should return PONG
```

After service is up, re-run tests:
```bash
uv run --frozen pytest tests/test_session.py -v
```bash
Prevention:
Add to .claude/memory/:
- Always run `docker-compose ps` before test sessions
- Add health checks to docker-compose.yml
- Consider `make setup-infra` before testing
```

---

## 💡 Debug Tips

### Tip 1: Read Error Messages Carefully

Most error messages tell you exactly what's wrong:
- **Line number**: Where error occurred
- **Stack trace**: Call sequence leading to error
- **Error type**: Category of problem

### Tip 2: Check Recent Changes

```bash
# What did I just change?
git diff

# What did I stage?
git diff --cached

# Recent commits
git log -5 --oneline
```bash
### Tip 3: Isolate the Problem

```bash
# Run just the failing test
pytest tests/test_file.py::test_name -v

# Run with print statements
pytest tests/test_file.py::test_name -v -s

# Run with debugger
pytest tests/test_file.py::test_name --pdb
```

### Tip 4: Check the Usual Suspects

1. **Virtual environment**: Using project venv?
2. **Docker services**: All running and healthy?
3. **Git status**: Any uncommitted changes?
4. **Dependencies**: All installed?
5. **Configuration**: Correct .env settings?

### Tip 5: Use Memory Files

Check `.claude/memory/` for known issues:
- `python-environment-usage.md` - Python env problems
- `task-spawn-error-prevention-strategy.md` - Async/subprocess issues

---

## 🔗 Related Commands

- `/test-failure-analysis` - Deep analysis of test failures
- `/test-summary failed` - Summary of all failed tests
- `/validate` - Run all validations

---

## 🛠️ Troubleshooting

### Issue: Can't find error logs

```bash
# Check recent pytest output
ls -lt /tmp/test_*.txt

# Check application logs
find . -name "*.log" -mtime -1
```bash
### Issue: Too many errors to analyze

```bash
# Focus on first failure
pytest -x  # Stop on first failure

# Or most recent
pytest --lf  # Last failed
```

### Issue: Error is intermittent

```bash
# Run multiple times
for i in {1..10}; do pytest tests/test.py || break; done

# Check for timing issues
pytest tests/test.py --durations=10
```

---

**Last Updated**: 2025-10-20
**Command Version**: 1.0
**AI-Assisted**: Yes (uses Claude for analysis)
