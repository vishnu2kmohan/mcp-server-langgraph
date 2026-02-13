# Error Patterns Reference

Detailed error type catalog and common issue patterns for the `/quick-debug` skill.

---

## Error Type Catalog

### Import Errors

```python
ImportError: cannot import name 'X'
ModuleNotFoundError: No module named 'X'
```

> Missing dependency, uncommitted code, wrong Python env

### Test Failures

```yaml
AssertionError: X != Y
AttributeError: 'NoneType' object has no attribute 'X'
```

> Logic error, missing mock, incorrect test setup

### Runtime Errors

```yaml
RuntimeError: Event loop is closed
asyncio.TimeoutError: timeout exceeded
```

> Async issues, resource management, timeouts

### Type Errors

```yaml
TypeError: X() takes 2 positional arguments but 3 were given
mypy error: Argument has incompatible type
```

> Function signature mismatch, type annotation issues

### Database/Connection Errors

```yaml
ConnectionError: Failed to connect to Redis
sqlalchemy.exc.OperationalError
```

> Service not running, configuration issue, network problem

---

## Common Issue Patterns

### Pattern 1: ImportError After Refactoring

**Symptoms**:
```python
ImportError: cannot import name 'get_session_store'
```

**Quick Check**:
```bash
git diff --cached src/  # Check staged changes
git status --short      # Check unstaged changes
```

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
```

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
docker compose ps
```

**Common Cause**: Service not started

**Fix**:
```bash
docker compose up -d redis
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
```

**Common Cause**: Test not cleaning up properly

**Fix**:
```python
@pytest.fixture
async def clean_db():
    yield
    # Cleanup after test
    await db.execute("DELETE FROM table")
```
