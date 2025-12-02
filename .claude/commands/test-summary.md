---
description: - `all` - Run all tests and generate complete summary (default)
argument-hint: <scope>
---
# Generate Comprehensive Test Summary

**Usage**: `/test-summary` or `/test-summary <scope>`

**Scopes**:
- `all` - Run all tests and generate complete summary (default)
- `unit` - Unit tests only
- `integration` - Integration tests only
- `quality` - Property + contract + regression tests
- `failed` - Analyze failed tests only

---

## 🧪 Test Summary Generation

### Step 1: Determine Test Scope

Based on $ARGUMENTS, determine which tests to run:

**All Tests** (default):
```bash
pytest -v --tb=short --cov=src --cov-report=term-missing
```

**Unit Tests**:
```bash
pytest -m unit -v --tb=short --cov=src --cov-report=term-missing
```

**Integration Tests**:
```bash
pytest -m integration -v --tb=short
```

**Quality Tests**:
```bash
pytest -m "property or contract or regression" -v --tb=short
```

---

### Step 2: Run Tests and Collect Results

Execute tests and capture all output:

```bash
# Run tests with JSON output
pytest -v --tb=short --json-report --json-report-file=/tmp/test_results.json

# Also capture human-readable output
pytest -v --tb=short 2>&1 | tee /tmp/test_output.txt
```

**Capture**:
- Total tests discovered
- Tests passed/failed/skipped
- Test execution time
- Coverage percentage
- Failed test details (if any)

---

### Step 3: Analyze Test Results

Parse test results from JSON and text output:

**Summary Statistics**:
```python
{
    "total": <total tests>,
    "passed": <passed count>,
    "failed": <failed count>,
    "skipped": <skipped count>,
    "errors": <error count>,
    "pass_rate": <passed / total * 100>,
    "duration": <total seconds>,
    "coverage": <coverage percentage>
}
```

**Failed Tests** (if any):
- Test name and file location
- Failure reason (assertion, exception)
- Stack trace (abbreviated)
- Related code (file:line)

**Skipped Tests**:
- Test name
- Skip reason
- Category (infrastructure, experimental, etc.)

---

### Step 4: Coverage Analysis

Analyze code coverage:

```bash
# Generate detailed coverage report
pytest --cov=src --cov-report=html --cov-report=term-missing

# Parse coverage summary
coverage report | grep "TOTAL"
```

**Coverage Breakdown**:
- Overall coverage percentage
- Files with < 80% coverage
- Uncovered lines (critical paths)
- Coverage delta from last run

---

### Step 5: Categorize Tests

Group tests by category from markers:

**Categories**:
- **Unit Tests**: Tests with `@pytest.mark.unit`
- **Integration Tests**: Tests with `@pytest.mark.integration`
- **Property Tests**: Tests with `@pytest.mark.property`
- **Contract Tests**: Tests with `@pytest.mark.contract`
- **Regression Tests**: Tests with `@pytest.mark.regression`

**For Each Category**:
- Total count
- Pass/fail breakdown
- Average duration
- Status (all passing, some failing, all failing)

---

### Step 6: Identify Test Patterns

From passed tests, identify successful patterns:

**Patterns Observed**:
- Most common fixture usage
- Typical test structure (Given-When-Then)
- Common mock patterns
- Assertion styles

**From `.claude/context/testing-patterns.md`**:
- Reference existing patterns
- Note new patterns discovered
- Recommend pattern updates if needed

---

### Step 7: Analyze Failed Tests (if any)

For each failed test, provide:

**Failure Analysis**:
1. **Test Name**: Full test name with class
2. **Location**: File path and line number
3. **Failure Type**: Assertion, exception, timeout, etc.
4. **Error Message**: Actual vs expected
5. **Stack Trace**: Relevant portion
6. **Suggested Fix**: Based on error analysis
7. **Related Files**: Files that may need changes

**Common Failure Patterns**:
- Mock configuration issues
- Async/await problems
- Assertion mismatches
- Infrastructure dependency missing
- Timeout issues

---

### Step 8: Performance Analysis

Analyze test performance:

**Slow Tests** (> 1 second):
- List tests exceeding threshold
- Execution time
- Potential optimization

**Test Duration Distribution**:
- Fast (< 0.1s): X tests
- Medium (0.1-1s): Y tests
- Slow (> 1s): Z tests

**Recommendations**:
- Mark slow tests with `@pytest.mark.slow`
- Consider parallelization (`pytest -n auto`)
- Optimize fixtures (scope adjustment)

---

### Step 9: Generate Summary Report

Create comprehensive test summary:

```markdown
# Test Summary Report

**Generated**: YYYY-MM-DD HH:MM
**Scope**: [all|unit|integration|quality]
**Status**: ✅ PASS | ❌ FAIL | ⚠️ MIXED

---

## 📊 Overall Statistics

| Metric | Value | Status |
|--------|-------|--------|
| Total Tests | XXX | |
| Passed | XXX | 🟢 |
| Failed | XX | 🔴 |
| Skipped | XX | 🟡 |
| Pass Rate | XX% | 🟢/🟡/🔴 |
| Duration | XX.Xs | |
| Coverage | XX% | 🟢/🟡/🔴 |

---

## 📁 Test Breakdown by Category

### Unit Tests
- Total: XXX
- Passed: XXX (100%)
- Duration: XX.Xs
- Status: ✅

### Integration Tests
- Total: XX
- Passed: XX (XX%)
- Failed: X
- Duration: XX.Xs
- Status: ⚠️

### Property Tests
- Total: XX
- Passed: XX (100%)
- Examples Generated: XXXX
- Duration: XX.Xs
- Status: ✅

[... other categories ...]

---

## 📈 Coverage Analysis

**Overall Coverage**: XX%

**High Coverage** (≥ 90%):
- `file1.py`: 95%
- `file2.py`: 92%

**Medium Coverage** (70-89%):
- `file3.py`: 85%
- `file4.py`: 78%

**Low Coverage** (< 70%):
- `file5.py`: 65% ⚠️
- `file6.py`: 45% 🔴

**Uncovered Critical Paths**:
- `auth/middleware.py:123-145` - Error handling
- `core/agent.py:234-267` - Tool execution

---

## ❌ Failed Tests (if any)

### 1. test_feature_with_invalid_input

**Location**: `tests/test_feature.py::TestFeature::test_feature_with_invalid_input`

**Failure**:
```
AssertionError: assert False is True
Expected: True
Actual: False
```

**Stack Trace**:
```
tests/test_feature.py:45 in test_feature_with_invalid_input
    assert result.success is True
```

**Analysis**:
- Mock not configured correctly
- Expected behavior: Should return success=False for invalid input
- Suggested fix: Change assertion to `assert result.success is False`

**Related Files**:
- `src/mcp_server_langgraph/core/feature.py:67-89`

---

[... additional failures ...]

---

## ⏭️ Skipped Tests

### tests/integration/test_redis_session.py::test_redis_lifecycle
**Reason**: Redis not available
**Category**: Integration
**Note**: Requires `docker compose up redis`

---

## 🐌 Slow Tests (> 1s)

| Test | Duration | Recommendation |
|------|----------|----------------|
| test_llm_invocation | 2.3s | Mock LLM calls |
| test_database_query | 1.8s | Use smaller dataset |

---

## 💡 Recommendations

**Quality Improvements**:
1. Fix 3 failing unit tests (see failures above)
2. Increase coverage on `file6.py` (currently 45%)
3. Add integration test for new search feature

**Performance Optimizations**:
1. Mark slow tests with `@pytest.mark.slow`
2. Run fast tests in parallel: `pytest -n auto`
3. Optimize fixture scope for database tests

**Test Expansion**:
1. Add property tests for new auth feature
2. Add contract tests for new API endpoint
3. Add regression tests for fixed bugs

---

## 🎯 Next Steps

**If tests passing**:
1. ✅ Proceed with deployment
2. ✅ Update coverage report
3. ✅ Document new tests in TESTING.md

**If tests failing**:
1. 🔴 Fix failing tests before proceeding
2. 🔴 Review failure analysis above
3. 🔴 Re-run tests after fixes
4. 🔴 Do NOT deploy until all tests pass

---

## 📝 Test Commands Reference

**Run all tests**:
```bash
pytest -v
```

**Run with coverage**:
```bash
pytest --cov=src --cov-report=html
```

**Run specific category**:
```bash
pytest -m unit
pytest -m integration
pytest -m property
```

**Run failed tests only**:
```bash
pytest --lf  # Last failed
```

**Run in parallel**:
```bash
pytest -n auto
```

**Specialized test commands**:
```bash
# Fast testing (40-70% faster)
make test-dev           # Development mode (recommended)
make test-fast-core     # Core tests only (<5s)
make test-fast          # All tests in parallel

# Specialized test types
make test-compliance    # GDPR, SOC2, SLA tests
make test-slow          # Slow tests only
make test-failed        # Re-run failed tests
make test-debug         # Debug mode with pdb

# Coverage options
make test-coverage-fast       # Fast coverage (unit only)
make test-coverage-changed    # Incremental coverage
```

---

**Report saved to**: `docs-internal/TEST_SUMMARY_$(date +%Y%m%d).md`
```

---

### Step 10: Save and Display Summary

Save summary to file and display to user:

```bash
# Save to dated file
SUMMARY_FILE=docs-internal/TEST_SUMMARY_$(date +%Y%m%d_%H%M).md
echo "$SUMMARY" > $SUMMARY_FILE

# Display summary
cat $SUMMARY_FILE

# Open HTML coverage if generated
if [ -f htmlcov/index.html ]; then
    echo "Coverage report: file://$(pwd)/htmlcov/index.html"
fi
```

---

## 🔍 Scope-Specific Behaviors

### Scope: unit

**Focus**: Fast unit tests only
**Command**: `pytest -m unit -v`
**Coverage**: Yes (src/ only)
**Duration**: Usually < 30 seconds
**Use Case**: Quick validation during development

### Scope: integration

**Focus**: Tests requiring infrastructure
**Command**: `pytest -m integration -v`
**Coverage**: No (external dependencies)
**Duration**: 1-5 minutes
**Use Case**: Pre-deployment validation
**Requires**: Docker services running

### Scope: quality

**Focus**: Property, contract, and regression tests
**Command**: `pytest -m "property or contract or regression" -v`
**Coverage**: No
**Duration**: 5-15 minutes (property tests generate many examples)
**Use Case**: Quality assurance, pre-release

### Scope: failed

**Focus**: Re-run and analyze failed tests only
**Command**: `pytest --lf -v`
**Coverage**: No
**Duration**: Quick (only failed tests)
**Use Case**: Debugging test failures

---

## 🎯 Integration with Sprint Workflow

**During Sprint**:
- Run `/test-summary unit` frequently (after each change)
- Run `/test-summary all` before commits
- Run `/test-summary integration` before deployments

**Sprint Milestones**:
- Start: Baseline test count and coverage
- Mid-sprint: Verify tests added for new code
- End: Comprehensive quality check

**Documentation**:
- Save test summaries to track progress
- Include in sprint retrospectives
- Reference in pull requests

---

## 📊 Example Output

```
=== Test Summary ===

Status: ✅ ALL TESTS PASSING

Overall:
- Total: 437 tests
- Passed: 437 (100%)
- Coverage: 69%
- Duration: 45.3s

By Category:
- Unit: 350/350 ✅
- Integration: 50/50 ✅
- Property: 27/27 ✅
- Contract: 20/20 ✅

Coverage Highlights:
- Excellent (≥90%): 45 files
- Good (70-89%): 32 files
- Needs work (<70%): 8 files

Recommendations:
- All tests passing - ready for deployment
- Consider adding tests for new search feature
- Increase coverage on compliance modules

Full Report: docs-internal/TEST_SUMMARY_20251020_1430.md
Coverage: file://htmlcov/index.html
```

---

## 🔗 Related Commands

- `/test-fast` - Fast test iteration (40-70% faster)
- `/validate` - Run all validations (includes tests)
- `/progress-update` - Include test status in sprint update
- `/start-sprint` - Initialize sprint with test baseline
- `/fix-issue` - Fix failing tests
- `/test-failure-analysis` - Deep analysis of failures

---

## 📝 Notes

- **Always run tests before committing**
- **Fix failing tests immediately** - Don't accumulate
- **Maintain coverage** - Don't let it drop
- **Add tests for bugs** - Prevent regression
- **Document test patterns** - Update testing-patterns.md

---

**Last Updated**: 2025-10-20
**Command Version**: 1.0
