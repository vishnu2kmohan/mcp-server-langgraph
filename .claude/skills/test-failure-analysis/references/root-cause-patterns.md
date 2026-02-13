# Root Cause Patterns

Reference for pattern analysis, root cause identification, analysis examples, and the failure patterns library. Used during Steps 4 and 5 of the test failure analysis workflow.

---

## Pattern Analysis

Identify patterns across failures:

```bash
# Check if failures are in same module
MOST_FAILING_MODULE=$(head -1 ${TMPDIR:-/tmp}/failing_files.txt | awk '{print $2}')

# Check if same error type
MOST_COMMON_ERROR=$(sort ${TMPDIR:-/tmp}/error_types.txt | uniq -c | sort -rn | head -1)

# Check if recent code changes related
git diff --name-only HEAD~5 | while read file; do
    if grep -q "$file" ${TMPDIR:-/tmp}/failing_files.txt; then
        echo "Recent change in $file may have caused failures"
    fi
done
```

### Pattern Detection Rules

**Pattern: Cascade Failure**
```
If 80%+ of failures are ImportError:
  -> Likely one missing import causing cascade
  -> Fix that one import, most tests should pass
```

**Pattern: Infrastructure Failure**
```
If all failures are ConnectionError:
  -> Docker service(s) not running
  -> Start services, re-run tests
```

**Pattern: Fixture Scope Issue**
```
If all async test failures with "Event loop closed":
  -> Session-scoped async fixture problem
  -> Change to function scope
```

**Pattern: Recent Change Impact**
```
If all failing tests import same module:
  -> Recent change broke that module
  -> Review git diff for that file
```

---

## Root Cause Analysis

For each failure category, determine root cause:

```python
def analyze_root_cause(failure_type, context):
    if failure_type == "ImportError":
        # Check git status for uncommitted files
        uncommitted = check_git_status()
        if uncommitted:
            return "Missing uncommitted files"

        # Check if dependency needs installing
        missing_deps = check_dependencies()
        if missing_deps:
            return f"Missing dependencies: {missing_deps}"

    elif failure_type == "AsyncMock":
        # Check for MagicMock used with async
        return "Using MagicMock instead of AsyncMock"

    elif failure_type == "EventLoopClosed":
        # Check fixture scopes
        return "Session-scoped async fixture issue"

    elif failure_type == "ConnectionError":
        # Check if services running
        services_down = check_docker_services()
        return f"Services not running: {services_down}"

    elif failure_type == "AssertionError":
        # Logic error - needs case-by-case analysis
        return "Logic error - manual review needed"
```

---

## Analysis Examples

### Example 1: Cascade Import Failure

**Scenario**: 45 test failures, all ImportError

**Analysis**:
```
Failed Tests: 45/50
Error Pattern: ImportError: cannot import name 'get_session_store'

Pattern Detection:
- All failures are ImportError
- All reference same function: get_session_store
- File exists: src/auth/session.py
- Function exists in file (line 42)
- File has uncommitted changes

Root Cause: CASCADE FAILURE
- Function exists in working copy
- Not committed to git
- All tests that import it fail

Impact: 45/45 failures (100%)
Fix Time: 2 minutes
Fix Priority: CRITICAL (blocks everything)

Recommended Fix:
```bash
git add src/mcp_server_langgraph/auth/session.py
git commit -m "fix: add missing session store functions"
```

Expected Outcome: 45/45 failures -> 0/45 failures
```

### Example 2: Infrastructure Failure

**Scenario**: 23 test failures, all ConnectionError

**Analysis**:
```
Failed Tests: 23/50
Error Pattern: ConnectionError: Error -2 connecting to localhost:6379

Pattern Detection:
- All failures are ConnectionError
- All reference Redis (port 6379)
- Tests are integration tests
- Redis service not running

Root Cause: INFRASTRUCTURE
- Redis Docker container not started
- Integration tests require Redis
- Simple fix: start service

Impact: 23/50 failures (46%)
Fix Time: 1 minute
Fix Priority: HIGH (blocks integration tests)

Recommended Fix:
```bash
docker compose up -d redis
# Wait for health
timeout 30s bash -c 'until docker compose ps redis | grep healthy; do sleep 1; done'
```

Expected Outcome: 23/23 failures -> 0/23 failures
```

### Example 3: Mixed Failures

**Scenario**: Multiple failure types

**Analysis**:
```
Failed Tests: 38/100

Failure Breakdown:
1. ImportError: 12 failures (32%)
2. ConnectionError: 8 failures (21%)
3. AsyncMock: 15 failures (39%)
4. AssertionError: 3 failures (8%)

Root Cause Analysis:

Category 1: ImportError (12 failures)
- Root Cause: Uncommitted file
- Fix: git add + commit
- Time: 2 min
- Priority: CRITICAL

Category 2: ConnectionError (8 failures)
- Root Cause: Redis not running
- Fix: docker compose up -d redis
- Time: 1 min
- Priority: HIGH

Category 3: AsyncMock (15 failures)
- Root Cause: Using MagicMock for async functions
- Fix: Change to AsyncMock in 5 test files
- Time: 10 min
- Priority: MEDIUM

Category 4: AssertionError (3 failures)
- Root Cause: Logic errors (need case-by-case review)
- Fix: Manual review and fix
- Time: 20 min
- Priority: LOW (small number)

Recommended Fix Sequence:
1. Commit missing file (2 min) -> 12 failures fixed -> 26 remaining
2. Start Redis (1 min) -> 8 failures fixed -> 18 remaining
3. Fix AsyncMock (10 min) -> 15 failures fixed -> 3 remaining
4. Fix assertions (20 min) -> 3 failures fixed -> 0 remaining

Total Time: 33 minutes
Current Pass Rate: 62%
Expected Pass Rate: 100%
```

---

## Failure Patterns Library

### Pattern: Shared Fixture Failure

**Signature**:
```
Multiple tests failing with same error in setup/teardown
```

**Example**:
```
test_user_create FAILED (fixture 'db' failed)
test_user_update FAILED (fixture 'db' failed)
test_user_delete FAILED (fixture 'db' failed)
```

**Root Cause**: Fixture initialization failing

**Fix**: Debug fixture in `conftest.py`

---

### Pattern: Async Fixture Scope

**Signature**:
```
RuntimeError: Event loop is closed
Occurs in fixture teardown
All async tests affected
```

**Root Cause**: Session-scoped async fixture

**Fix**:
```python
# Change from:
@pytest.fixture(scope="session")
async def fixture():
    ...

# To:
@pytest.fixture  # Default: function scope
async def fixture():
    ...
```

---

### Pattern: Parallel Execution Conflict

**Signature**:
```
Tests pass individually but fail when run together
Database conflicts, port conflicts
```

**Root Cause**: Tests not properly isolated

**Fix**: Use unique test data, cleanup after tests

---

### Pattern: Flaky Test

**Signature**:
```
Test passes sometimes, fails sometimes
Timing-related failures
```

**Root Cause**: Race condition, insufficient waits

**Fix**: Add proper async waits, increase timeouts
