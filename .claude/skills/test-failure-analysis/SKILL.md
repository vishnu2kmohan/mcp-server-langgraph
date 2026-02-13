---
name: test-failure-analysis
description: Analyze test failures with root cause identification. Use when tests fail and you need to understand patterns, categorize errors, and get fix suggestions.
allowed-tools:
  - Bash(uv:*)
  - Read
  - Glob
  - Grep
argument-hint: <args>
---
# Test Failure Analysis

**Usage**: `/test-failure-analysis` or `/test-failure-analysis --deep`

**Purpose**: Comprehensive analysis of test failures with root cause identification

## Efficiency Pattern: Script Reference

For automated analysis, use the dedicated script:
```bash
uv run --frozen python scripts/workflow/test-failure-analyzer.py --output ${TMPDIR:-/tmp}/failure_analysis.md
```

This handles failure parsing, categorization, and fix suggestions in a single command.

---

## What This Command Does

Performs deep analysis of test failures to identify root causes and suggest fixes:

1. Runs tests and captures all failures
2. Groups failures by pattern/category
3. Analyzes stack traces and error messages
4. Identifies common root causes
5. Suggests fixes with priority
6. Generates actionable report

---

## Analysis Workflow

### Step 1: Run Tests and Capture Failures

Execute test suite with detailed output:

```bash
# Create secure temp files (cross-platform)
TMPFILE=$(mktemp)
TMPFILE2=$(mktemp)
trap "rm -f $TMPFILE $TMPFILE2" EXIT

# Run all tests, don't stop on first failure
uv run --frozen pytest tests/ -v --tb=short --maxfail=100 2>&1 | tee "$TMPFILE"

# Alternative: Only run previously failed tests
uv run --frozen pytest --lf -v --tb=long 2>&1 | tee "$TMPFILE2"

# Count failures
FAILURES=$(grep -c "FAILED" "$TMPFILE")
ERRORS=$(grep -c "ERROR" "$TMPFILE")
PASSED=$(grep -c "PASSED" "$TMPFILE")

echo "Results: $PASSED passed, $FAILURES failed, $ERRORS errors"
```

### Step 2: Extract Failure Information

Parse test output to extract structured data:

```bash
# Create temp files with cleanup (cross-platform)
FAILED_TESTS=$(mktemp)
ERROR_TYPES=$(mktemp)
FAILING_FILES=$(mktemp)
trap "rm -f $FAILED_TESTS $ERROR_TYPES $FAILING_FILES" EXIT

# Extract failed test names
grep "FAILED" "$TMPFILE" | \
  sed 's/FAILED //' | \
  sed 's/ - .*//' > "$FAILED_TESTS"

# Extract error types
grep -A 5 "FAILED\|ERROR" "$TMPFILE" | \
  grep -E "Error|Exception|assert" > "$ERROR_TYPES"

# Extract file locations
grep "FAILED" "$TMPFILE" | \
  sed 's/::.*//' | \
  sort | uniq -c | \
  sort -rn > "$FAILING_FILES"
```

### Step 3: Categorize Failures

Read `references/error-categories.md` for error categorization patterns. Match each extracted error against the known categories (Assertion, Import, Async, Mock, Database, Type, Configuration errors).

### Step 4: Pattern Analysis

Read `references/root-cause-patterns.md` for pattern detection rules and root cause analysis procedures. This covers cascade failures, infrastructure failures, fixture scope issues, recent change impact, and more.

### Step 5: Root Cause Analysis

Continue with `references/root-cause-patterns.md` which includes the root cause analysis pseudocode, analysis examples (cascade import, infrastructure, mixed failures), and the failure patterns library.

### Step 6: Generate Failure Report

Create comprehensive report with fixes using this template:

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
   - Change MagicMock -> AsyncMock

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

Read `references/fix-templates.md` for fix templates, advanced features (trend analysis, failure clustering, AI-powered suggestions), and troubleshooting guidance.

---

## Related Commands

- `/quick-debug` - Fast debugging for single issues
- `/test-summary failed` - Summary of failed tests
- `/coverage-trend` - Track test coverage changes

---

**Last Updated**: 2025-10-20
**Command Version**: 1.0
**AI-Assisted**: Yes (deep analysis with Claude)
**Automated**: Partial (pattern detection automated, fixes suggested)
