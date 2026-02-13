---
name: quick-debug
description: Fast debugging workflow for common issues. Use when you encounter errors, test failures, or infrastructure problems and need quick diagnosis and fixes.
allowed-tools:
  - Bash(uv:*)
  - Bash(docker logs:*)
  - Bash(docker ps:*)
  - Bash(docker inspect:*)
  - Bash(git:*)
  - Read
  - Glob
  - Grep
argument-hint: <error>
---
# Quick Debug

**Usage**: `/quick-debug` or `/quick-debug <error-message>`

**Purpose**: Fast debugging workflow for common issues

---

## What This Command Does

Provides AI-assisted debugging workflow to quickly identify and fix common issues:

1. Analyzes error messages and stack traces
2. Suggests likely causes based on patterns
3. Recommends debugging steps
4. Provides quick fixes for common problems
5. Links to relevant code locations

---

## Debugging Workflow

### Step 1: Capture Error Information

If error message provided as argument:
```bash
# Use provided error
ERROR_MSG="$ARGUMENTS"
```

If no argument, look for recent errors:
```bash
# Check recent test failures
uv run --frozen pytest --lf -v 2>&1 | tee ${TMPDIR:-/tmp}/test_errors.txt

# Check recent git commits for fix mentions
git log -10 --oneline | grep -i "fix"

# Check application logs (if running)
tail -50 logs/app.log 2>/dev/null || echo "No app logs found"
```

### Step 2: Categorize Error Type

Analyze error message to determine category:

| Category | Indicators | Likely Cause |
|----------|-----------|--------------|
| **Import Errors** | `ImportError`, `ModuleNotFoundError` | Missing dependency, uncommitted code, wrong Python env |
| **Test Failures** | `AssertionError`, `AttributeError` on NoneType | Logic error, missing mock, incorrect test setup |
| **Runtime Errors** | `RuntimeError: Event loop is closed`, `asyncio.TimeoutError` | Async issues, resource management, timeouts |
| **Type Errors** | `TypeError: X() takes N args`, `mypy error` | Function signature mismatch, type annotation issues |
| **Database/Connection Errors** | `ConnectionError`, `sqlalchemy.exc.OperationalError` | Service not running, configuration issue, network problem |

> Read `references/error-patterns.md` for detailed error pattern matching with code snippets and common issue patterns (ImportError after refactoring, AsyncMock issues, Event Loop Closed, Docker Service Not Running, Test Database State).

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

### Step 4: Run Diagnostics and Apply Fixes

Based on the error category, run relevant diagnostic commands and apply fixes.

> Read `references/troubleshooting-recipes.md` for diagnostic command blocks for each error type, fix templates (import errors, test failures, async errors, mock errors), and usage examples.

### Step 5: Generate Debug Report

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
```

## Prevention

To avoid this in future:
- {prevention_step_1}
- {prevention_step_2}

## Related Issues

Similar errors found:
- {related_issue_1}
- {related_issue_2}
```

### Step 6: Prevention Guidance

> Read `references/prevention-tips.md` for debug tips (reading error messages, checking recent changes, isolating problems, checking usual suspects, using memory files) and troubleshooting guides for edge cases (can't find error logs, too many errors, intermittent errors).

---

## Related Commands

- `/test-failure-analysis` - Deep analysis of test failures
- `/test-summary failed` - Summary of all failed tests
- `/validate` - Run all validations

---

**Last Updated**: 2025-10-20
**Command Version**: 1.0
**AI-Assisted**: Yes (uses Claude for analysis)
