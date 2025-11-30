# Test Failure Analysis

**Usage**: `/test-failure-analysis` or `/test-failure-analysis --deep`

**Purpose**: Comprehensive analysis of test failures with root cause identification

---

## 🔬 What This Command Does

Performs deep analysis of test failures to identify root causes and suggest fixes:

1. Runs tests and captures all failures
2. Groups failures by pattern/category
3. Analyzes stack traces and error messages
4. Identifies common root causes
5. Suggests fixes with priority
6. Generates actionable report

---

## 📊 Analysis Workflow

### Step 1: Run Tests and Capture Failures

Execute test suite with detailed output:

```bash
# Run all tests, don't stop on first failure
uv run --frozen pytest tests/ -v --tb=short --maxfail=100 2>&1 | tee /tmp/test_output.txt

# Alternative: Only run previously failed tests
uv run --frozen pytest --lf -v --tb=long 2>&1 | tee /tmp/test_failures.txt

# Count failures
FAILURES=$(grep -c "FAILED" /tmp/test_output.txt)
ERRORS=$(grep -c "ERROR" /tmp/test_output.txt)
PASSED=$(grep -c "PASSED" /tmp/test_output.txt)

echo "Results: $PASSED passed, $FAILURES failed, $ERRORS errors"
```

### Step 2: Extract Failure Information

Parse test output to extract structured data:

```bash
# Extract failed test names
grep "FAILED" /tmp/test_output.txt | \
  sed 's/FAILED //' | \
  sed 's/ - .*//' > /tmp/failed_tests.txt

# Extract error types
grep -A 5 "FAILED\|ERROR" /tmp/test_output.txt | \
  grep -E "Error|Exception|assert" > /tmp/error_types.txt

# Extract file locations
grep "FAILED" /tmp/test_output.txt | \
  sed 's/::.*//' | \
  sort | uniq -c | \
  sort -rn > /tmp/failing_files.txt
```

### Step 3: Categorize Failures

Group failures by error pattern:

**Categories**:

**Assertion Failures** (Logic Errors):
```
AssertionError: assert X == Y
AssertionError: assert result is not None
```

**Import/Module Errors**:
```
ImportError: cannot import name
ModuleNotFoundError: No module named
```

**Async/Event Loop Errors**:
```
RuntimeError: Event loop is closed
asyncio.TimeoutError
RuntimeError: This event loop is already running
```

**Mock/Fixture Errors**:
```
AttributeError: Mock object has no attribute
TypeError: object MagicMock can't be used in 'await'
```

**Database/Connection Errors**:
```
ConnectionError
sqlalchemy.exc.OperationalError
redis.exceptions.ConnectionError
```

**Type Errors**:
```
TypeError: X() takes N arguments but M were given
TypeError: unsupported operand type(s)
```

**Configuration Errors**:
```
KeyError: environment variable not set
FileNotFoundError: config file missing
```

### Step 4: Pattern Analysis

Identify patterns across failures:

```bash
# Check if failures are in same module
MOST_FAILING_MODULE=$(head -1 /tmp/failing_files.txt | awk '{print $2}')

# Check if same error type
MOST_COMMON_ERROR=$(sort /tmp/error_types.txt | uniq -c | sort -rn | head -1)

# Check if recent code changes related
git diff --name-only HEAD~5 | while read file; do
    if grep -q "$file" /tmp/failing_files.txt; then
        echo "Recent change in $file may have caused failures"
    fi
done
```

**Pattern Detection**:

**Pattern: Cascade Failure**
```
If 80%+ of failures are ImportError:
  → Likely one missing import causing cascade
  → Fix that one import, most tests should pass
```

**Pattern: Infrastructure Failure**
```
If all failures are ConnectionError:
  → Docker service(s) not running
  → Start services, re-run tests
```

**Pattern: Fixture Scope Issue**
```
If all async test failures with "Event loop closed":
  → Session-scoped async fixture problem
  → Change to function scope
```

**Pattern: Recent Change Impact**
```
If all failing tests import same module:
  → Recent change broke that module
  → Review git diff for that file
```

### Step 5: Root Cause Analysis

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

### Step 6: Generate Failure Report

Create comprehensive report with fixes:

```markdown
# Test Failure Analysis Report

**Generated**: {timestamp}
**Tests Run**: {total_tests}
**Failed**: {failed_count}
**Errors**: {error_count}
**Pass Rate**: {pass_rate}%

---

## Executive Summary

**Status**: {overall_status}

**Top Issues**:
1. {top_issue_1} ({count} failures)
2. {top_issue_2} ({count} failures)
3. {top_issue_3} ({count} failures)

**Estimated Fix Time**: {total_time} minutes

---

## Failure Breakdown

### Category: {category_name} ({count} failures)

**Root Cause**: {root_cause}

**Affected Tests**:
- {test_1}
- {test_2}
- {test_3}

**Fix Priority**: {HIGH|MEDIUM|LOW}

**Recommended Fix**:
```{language}
{fix_code}
```

**Fix Time**: ~{minutes} minutes

---

## Fix Sequence

**Recommended order to maximize fix efficiency**:

1. **Fix infrastructure** (5 min)
   - Start Docker services
   - Will fix: {count} ConnectionError failures

2. **Fix import cascade** (2 min)
   - Commit missing file: {file}
   - Will fix: {count} ImportError failures

3. **Fix async mocks** (10 min)
   - Update {count} test files
   - Change MagicMock → AsyncMock

4. **Fix logic errors** (30 min)
   - Review {count} assertion failures
   - Update test expectations

**Total Estimated Time**: {total} minutes
**Expected Pass Rate After Fixes**: {projected}%

---

## Detailed Analysis

{detailed_breakdown_per_failure}

---

## Prevention Recommendations

To avoid these failures in future:

1. {prevention_1}
2. {prevention_2}
3. {prevention_3}
```

---

## 🎯 Analysis Examples

### Example 1: Cascade Import Failure

**Scenario**: 45 test failures, all ImportError

**Analysis**:
```
Failed Tests: 45/50
Error Pattern: ImportError: cannot import name 'get_session_store'

Pattern Detection:
✓ All failures are ImportError
✓ All reference same function: get_session_store
✓ File exists: src/auth/session.py
✓ Function exists in file (line 42)
✗ File has uncommitted changes

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

Expected Outcome: 45/45 failures → 0/45 failures
```

### Example 2: Infrastructure Failure

**Scenario**: 23 test failures, all ConnectionError

**Analysis**:
```
Failed Tests: 23/50
Error Pattern: ConnectionError: Error -2 connecting to localhost:6379

Pattern Detection:
✓ All failures are ConnectionError
✓ All reference Redis (port 6379)
✓ Tests are integration tests
✗ Redis service not running

Root Cause: INFRASTRUCTURE
- Redis Docker container not started
- Integration tests require Redis
- Simple fix: start service

Impact: 23/50 failures (46%)
Fix Time: 1 minute
Fix Priority: HIGH (blocks integration tests)

Recommended Fix:
```bash
docker-compose up -d redis
# Wait for health
timeout 30s bash -c 'until docker-compose ps redis | grep healthy; do sleep 1; done'
```

Expected Outcome: 23/23 failures → 0/23 failures
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
- Fix: docker-compose up -d redis
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
1. Commit missing file (2 min) → 12 failures fixed → 26 remaining
2. Start Redis (1 min) → 8 failures fixed → 18 remaining
3. Fix AsyncMock (10 min) → 15 failures fixed → 3 remaining
4. Fix assertions (20 min) → 3 failures fixed → 0 remaining

Total Time: 33 minutes
Current Pass Rate: 62%
Expected Pass Rate: 100%
```

---

## 📈 Failure Patterns Library

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

---

## 🔧 Fix Templates

### Template 1: ImportError Cascade Fix

```bash
#!/bin/bash
# Fix cascade import failures

# 1. Identify missing file
MISSING_FILE=$(grep -o "from .* import" /tmp/test_output.txt | \
               awk '{print $2}' | sort | uniq -c | sort -rn | head -1 | awk '{print $2}')

# 2. Check git status
git status src/ | grep -i "$MISSING_FILE"

# 3. Stage and commit
git add src/**/*${MISSING_FILE}*.py
git commit -m "fix: add missing ${MISSING_FILE} module"

# 4. Re-run tests
uv run --frozen pytest --lf -v
```

### Template 2: Docker Service Fix

```bash
#!/bin/bash
# Fix infrastructure failures

# 1. Identify which service
SERVICE=$(grep -o "localhost:[0-9]*" /tmp/test_output.txt | \
          sed 's/localhost://' | sort | uniq)

# Map port to service
case $SERVICE in
    6379) SERVICE_NAME="redis" ;;
    5432) SERVICE_NAME="postgres" ;;
    8080) SERVICE_NAME="openfga" ;;
esac

# 2. Start service
docker-compose up -d $SERVICE_NAME

# 3. Wait for healthy
timeout 60s bash -c "until docker-compose ps $SERVICE_NAME | grep healthy; do sleep 2; done"

# 4. Re-run tests
uv run --frozen pytest --lf -v
```

### Template 3: AsyncMock Batch Fix

```python
#!/usr/bin/env python3
"""Fix AsyncMock issues in test files."""

import re
import sys
from pathlib import Path

def fix_async_mock(file_path):
    content = Path(file_path).read_text()

    # Find @patch decorators above async functions
    pattern = r'@patch\("([^"]+)"\)\s*\nasync def'

    # Replace with AsyncMock version
    replacement = r'@patch("\1", new_callable=AsyncMock)\nasync def'

    fixed_content = re.sub(pattern, replacement, content)

    if fixed_content != content:
        Path(file_path).write_text(fixed_content)
        print(f"Fixed: {file_path}")
        return True
    return False

# Run on all test files
for test_file in Path("tests").rglob("test_*.py"):
    fix_async_mock(test_file)
```

---

## 💡 Advanced Features

### Feature 1: Failure Trend Analysis

Track failure patterns over time:

```bash
# Store failure data
mkdir -p .test-history
echo "$(date +%Y-%m-%d),$FAILURES,$ERRORS,$PASSED" >> .test-history/trend.csv

# Analyze trend
tail -30 .test-history/trend.csv | awk -F',' '
{
    total = $2 + $3 + $4
    fail_rate = ($2 + $3) / total * 100
    print $1, fail_rate "%"
}'
```

### Feature 2: Failure Clustering

Group similar failures:

```python
def cluster_failures(failures):
    clusters = {}

    for failure in failures:
        # Extract error message
        error = extract_error(failure)

        # Find similar errors (edit distance < 5)
        cluster_key = find_similar(error, clusters.keys())

        if not cluster_key:
            cluster_key = error

        clusters[cluster_key] = clusters.get(cluster_key, []) + [failure]

    return clusters
```

### Feature 3: AI-Powered Suggestions

Use Claude to suggest fixes:

```
For each unique failure:
1. Extract stack trace
2. Extract surrounding code
3. Ask Claude: "What's the likely cause of this error?"
4. Get suggested fix
5. Apply if high confidence
```

---

## 🔗 Related Commands

- `/quick-debug` - Fast debugging for single issues
- `/test-summary failed` - Summary of failed tests
- `/coverage-trend` - Track test coverage changes

---

## 🛠️ Troubleshooting

### Issue: Too many failures to analyze

```bash
# Focus on most common error
grep "FAILED" /tmp/test_output.txt | \
  awk -F':' '{print $NF}' | \
  sort | uniq -c | sort -rn | head -5
```

### Issue: Can't determine root cause

```bash
# Run with full traceback
uv run --frozen pytest --lf -vv --tb=long

# Enable debugging
uv run --frozen pytest --lf --pdb
```

### Issue: Failures are intermittent

```bash
# Run multiple times
for i in {1..10}; do
    uv run --frozen pytest tests/ > /tmp/run_$i.txt 2>&1
    grep -c "FAILED" /tmp/run_$i.txt
done
```

---

**Last Updated**: 2025-10-20
**Command Version**: 1.0
**AI-Assisted**: Yes (deep analysis with Claude)
**Automated**: Partial (pattern detection automated, fixes suggested)
