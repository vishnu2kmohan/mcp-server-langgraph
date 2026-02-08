---
name: test-status
description: Provides quick test status check without running full suite. Uses pytest collection for test discovery, falls back to file analysis in Plan mode. Use when user asks about test status, passing tests, or test health.
metadata:
  author: mcp-server-langgraph
  version: "2.0"
compatibility: Claude Code 1.0+
context: fork
agent: Explore
allowed-tools: Read, Grep, Glob, LS, Bash(uv run --frozen pytest --collect-only *), TaskList
disable-model-invocation: true
argument-hint: [--unit | --integration | --all]
---

# Quick Test Status Check

**Usage**: `/test-status` or `/test-status <marker>`

**Markers**: Any pytest marker (e.g., `unit`, `integration`, `api`, `security`)

## Plan Mode Compatibility

This skill is **Plan mode compatible** because:

1. **Uses `context: fork`** - Runs in isolated Explore subagent
2. **Uses `agent: Explore`** - Read-only tools by default
3. **No edits to codebase** - Only outputs status information

**Plan Mode Fallback**: If Bash is blocked in Plan mode, this skill falls back to static analysis of `tests/` directory structure and `conftest.py` files. Dynamic test collection requires exiting Plan mode.

## Purpose

Provides a **fast, lightweight status check** of tests without running comprehensive analysis.

Use this for:
- Quick validation during development
- Rapid feedback after code changes
- Fast status checks before commits

For comprehensive analysis, use `/test-summary` instead.

## Quick Status Check

### Step 1: Determine Scope

Based on arguments, determine which tests to check:

**Default (all tests)**:
```bash
uv run --frozen pytest -v --tb=line --no-cov -q
```

**Specific marker** (e.g., `/test-status unit`):
```bash
uv run --frozen pytest -m $ARGUMENTS -v --tb=line --no-cov -q
```

**Options used for speed**:
- `--no-cov` - Skip coverage (faster)
- `-q` - Quiet mode (less output)
- `--tb=line` - Minimal traceback
- `-x` - Stop on first failure (optional)

### Step 2: Run Fast Test Check

Execute tests with minimal overhead:
```bash
uv run --frozen pytest -v --tb=line --no-cov -q 2>&1 | tee ${TMPDIR:-/tmp}/test_status.txt
```

Capture:
- Total tests run
- Pass/fail count
- First failure (if any)
- Total duration

### Step 3: Parse Results

Extract key metrics from output (summary line like "437 passed in 12.34s").

### Step 4: Display Quick Status

Show concise status report:
- Status: PASSING | FAILING | ISSUES
- Quick Summary: Passed/Failed/Skipped counts, Duration
- Scope: all | unit | integration | marker
- Quick commands for next steps

## Example Outputs

### All Tests Passing
```
Test Status: PASSING

Quick Summary:
- Passed: 437
- Failed: 0
- Skipped: 3
- Duration: 12.3s

All tests passing - Ready to proceed
```

### Some Tests Failing
```
Test Status: FAILING

Quick Summary:
- Passed: 425
- Failed: 12
- Skipped: 3
- Duration: 15.2s

First failure: test_auth_with_invalid_token in tests/unit/auth/test_middleware.py:45

Run `/test-summary failed` for detailed analysis.
```

## Performance Comparison

| Command | Duration | Coverage | Detail Level | Use Case |
|---------|----------|----------|--------------|----------|
| `/test-status` | ~10-15s | No | Quick status | During development |
| `/test-summary` | ~30-60s | Yes | Comprehensive | Pre-commit, deployment |
| `make test-dev` | ~8-12s | No | Fast iteration | TDD workflow |

## Related Commands

- `/test-summary` - Comprehensive test analysis with coverage
- `/verify-tests` - Manually verify all tests pass
- `/test-fast` - Fast test iteration (40-70% faster)
- `/fix-issue` - Fix specific failing test
- `/tdd <feature>` - Start TDD workflow

## Tips

**During Development**:
1. Use `/test-status unit` after each change (fastest)
2. Use `/test-status` before commits (quick validation)
3. Use `/test-summary` before deployments (comprehensive)

**When Tests Fail**:
1. `/test-status` to see what failed
2. `uv run --frozen pytest --lf -x -vv` to debug first failure
3. `/test-summary failed` for detailed analysis
4. `/fix-issue <test-name>` for AI-assisted fix

**Fast Iteration**:
```bash
uv run --frozen pytest --lf -x          # Run last-failed, stop on first
make test-dev                           # Fast mode with minimal output
uv run --frozen pytest -m unit -x       # Fast unit tests only
```

---

**Command Type**: Quick Status
**Speed**: Fast (~10-15s)
**Detail Level**: Minimal
**Coverage**: No
**Use Case**: Rapid feedback during development

---

**Last Updated**: 2026-02-05
