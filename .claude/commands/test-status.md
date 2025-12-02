---
description: Provides a **fast, lightweight status check** of tests without running comprehensive analysis.
argument-hint: <args>
---
# Quick Test Status Check

**Usage**: `/test-status` or `/test-status <marker>`

**Markers**: Any pytest marker (e.g., `unit`, `integration`, `api`, `security`)

---

## 🎯 Purpose

Provides a **fast, lightweight status check** of tests without running comprehensive analysis.

Use this for:
- Quick validation during development
- Rapid feedback after code changes
- Fast status checks before commits

For comprehensive analysis, use `/test-summary` instead.

---

## ⚡ Quick Status Check

### Step 1: Determine Scope

Based on $ARGUMENTS, determine which tests to check:

**Default (all tests)**:
```bash
pytest -v --tb=line --no-cov -q
```

**Specific marker** (e.g., `/test-status unit`):
```bash
pytest -m $ARGUMENTS -v --tb=line --no-cov -q
```

**Options used for speed**:
- `--no-cov` - Skip coverage (faster)
- `-q` - Quiet mode (less output)
- `--tb=line` - Minimal traceback (faster display)
- `-x` - Stop on first failure (optional, for even faster feedback)

---

### Step 2: Run Fast Test Check

Execute tests with minimal overhead:

```bash
# Run tests without coverage
pytest -v --tb=line --no-cov -q 2>&1 | tee /tmp/test_status.txt

# Capture exit code
TEST_EXIT=$?
```

**Capture**:
- Total tests run
- Pass/fail count
- First failure (if any)
- Total duration

---

### Step 3: Parse Results

Extract key metrics from output:

```bash
# Parse pytest output for summary line
# Example: "437 passed in 12.34s"
# Example: "425 passed, 12 failed in 23.45s"

SUMMARY=$(tail -n 5 /tmp/test_status.txt | grep -E "passed|failed|skipped")
```

---

### Step 4: Display Quick Status

Show concise status report:

```markdown
## ⚡ Test Status

**Status**: ✅ PASSING | ❌ FAILING | ⚠️ ISSUES

**Quick Summary**:
- Passed: XXX
- Failed: XX
- Skipped: XX
- Duration: XX.Xs

**Scope**: [all|unit|integration|$MARKER]

---

[If all passing]:
✅ **All tests passing** - Ready to proceed

[If failures]:
❌ **Tests failing** - Fix before proceeding
First failure: `test_name` in `file_path.py:line`

Run `/test-summary` for detailed failure analysis.

[If skipped tests]:
⚠️ **XX tests skipped** - May need infrastructure
Run with `-v` to see skip reasons.

---

**Quick Commands**:

Run failed tests only:
```bash
pytest --lf -x  # Stop on first failure
```

Run specific test:
```bash
pytest tests/path/test_file.py::test_name
```

Fast iteration:
```bash
make test-dev  # Fast mode (40-70% faster)
```

---

**Next Steps**:

✅ All passing → Proceed with commit/deployment
❌ Failures → Run `/test-summary failed` for analysis
⚠️ Skipped → Check infrastructure (docker compose up)

For comprehensive analysis: `/test-summary`
For test debugging: `/fix-issue <test-name>`
```

---

## 📊 Example Outputs

### All Tests Passing

```
⚡ Test Status

Status: ✅ PASSING

Quick Summary:
- Passed: 437
- Failed: 0
- Skipped: 3
- Duration: 12.3s

Scope: all

✅ All tests passing - Ready to proceed

⚠️ 3 tests skipped (infrastructure tests - requires docker)
```

---

### Some Tests Failing

```
⚡ Test Status

Status: ❌ FAILING

Quick Summary:
- Passed: 425
- Failed: 12
- Skipped: 3
- Duration: 15.2s

Scope: all

❌ Tests failing - Fix before proceeding

First failure: test_auth_with_invalid_token in tests/unit/auth/test_middleware.py:45

Run `/test-summary failed` for detailed analysis or `/fix-issue test_auth_with_invalid_token`

Quick fix:
```bash
pytest --lf -x -vv  # Re-run failed tests with verbose output
```
```

---

### Specific Marker (Unit Tests)

```
⚡ Test Status

Status: ✅ PASSING

Quick Summary:
- Passed: 350
- Failed: 0
- Skipped: 0
- Duration: 8.2s

Scope: unit

✅ All unit tests passing - Ready to proceed
```

---

## 🎯 Performance Comparison

| Command | Duration | Coverage | Detail Level | Use Case |
|---------|----------|----------|--------------|----------|
| `/test-status` | ~10-15s | No | Quick status | During development |
| `/test-summary` | ~30-60s | Yes | Comprehensive | Pre-commit, deployment |
| `make test-dev` | ~8-12s | No | Fast iteration | TDD workflow |

---

## 🔗 Related Commands

- `/test-summary` - Comprehensive test analysis with coverage
- `/verify-tests` - Manually verify all tests pass
- `/test-fast` - Fast test iteration (40-70% faster)
- `/fix-issue` - Fix specific failing test
- `/tdd <feature>` - Start TDD workflow

---

## 💡 Tips

**During Development**:
1. Use `/test-status unit` after each change (fastest)
2. Use `/test-status` before commits (quick validation)
3. Use `/test-summary` before deployments (comprehensive)

**When Tests Fail**:
1. `/test-status` to see what failed
2. `pytest --lf -x -vv` to debug first failure
3. `/test-summary failed` for detailed analysis
4. `/fix-issue <test-name>` for AI-assisted fix

**Fast Iteration**:
```bash
# TDD cycle with fast feedback
pytest --lf -x          # Run last-failed, stop on first
make test-dev           # Fast mode with minimal output
pytest -m unit -x       # Fast unit tests only
```

---

**Command Type**: Quick Status
**Speed**: Fast (~10-15s)
**Detail Level**: Minimal
**Coverage**: No
**Use Case**: Rapid feedback during development

---

**Last Updated**: 2025-11-23
**Command Version**: 1.0
