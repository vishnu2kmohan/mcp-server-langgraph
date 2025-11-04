# GitHub Actions Workflow Testing Checklist

**Use this checklist for ALL changes to `.github/workflows/*.yaml` files.**

---

## Before Committing Workflow Changes

### ☐ Step 1: Validate YAML Syntax

```bash
make validate-workflows
```

**Expected Output:**
```
✓ ci.yaml
✓ e2e-tests.yaml
✓ quality-tests.yaml
...
✓ Workflow syntax validation complete
```

**If validation fails**: Fix YAML syntax errors before proceeding.

---

### ☐ Step 2: Test with act (Dry-Run)

```bash
# List what would execute
act push -W .github/workflows/YOUR_WORKFLOW.yaml --list
```

**Expected Output:**
```
ID    Stage  Name
0     0      Checkout code
1     0      Install uv
2     0      Install dependencies
...
```

**If list fails**: Workflow has configuration errors (invalid triggers, job dependencies, etc.)

---

### ☐ Step 3: Test Workflow Execution with act

```bash
# Test specific job (faster)
act push -W .github/workflows/YOUR_WORKFLOW.yaml -j JOB_NAME

# Or use Makefile shortcut
make test-workflow-YOUR_WORKFLOW
```

**Watch for**:

- ✅ **Success indicators**:
- Dependencies install without errors
- Commands execute successfully
- No "ModuleNotFoundError"
- No "command not found"

❌ **Failure indicators** (MUST FIX):
- `pip install` (should use `uv`)
- `python scripts/...` without `uv run`
- `jq: command not found` (install jq first)
- `ModuleNotFoundError` (missing --extra flags)

⚠️ **Expected failures** (can ignore):
- Connection errors to Postgres/Redis (infrastructure not running)
- Tests skipping due to missing services

---

### ☐ Step 4: Verify Critical Sections

Check these in act output:

#### Dependency Installation
```
| Install dependencies
| uv sync --extra dev --extra builder
| ✓ Dependencies installed from lockfile with dev+builder extras
- ✅ GOOD
```

#### Tool Installation
```
| Install pre-commit
| uv tool install pre-commit
| ✓ pre-commit installed via uv tool
- ✅ GOOD
```

#### Script Execution
```
| Run skipped test tracker
| uv run python scripts/ci/track-skipped-tests.py
- ✅ GOOD
```

---

### ☐ Step 5: Fix Issues Found by act

**If act reveals problems**:

1. Fix the workflow file
2. Retest with act immediately
3. Repeat until act test passes
4. Only THEN proceed to commit

**DO NOT** push hoping "it will work in CI" if act fails!

---

### ☐ Step 6: Run Pre-commit Hooks

```bash
pre-commit run --all-files
```

**Expected**: All hooks pass, including workflow validation

---

### ☐ Step 7: Commit Changes

```bash
git add .github/workflows/YOUR_WORKFLOW.yaml
git commit -m "fix: description of changes"
```

**Commit message should mention**:
- What was changed
- Why it was changed
- That it was tested with act

Example:
```
fix: add missing optional dependencies to E2E tests workflow

- Add --extra dev --extra builder to uv sync command
- Fixes ModuleNotFoundError: No module named 'black'
- Tested locally with act before committing

act output: Dependency installation successful ✅
```

---

### ☐ Step 8: Push and Monitor CI

```bash
git push origin main

# Watch workflow runs
gh run watch

# Or check status
gh run list --limit=5
```

**Compare**:
- Did CI behave like act predicted?
- Any surprises?
- If yes, update act configuration for next time

---

## Post-Commit Review

### ☐ After CI Completes

**If CI Passed** ✅:
- Great! act testing worked
- No action needed

**If CI Failed** ❌:
1. Get CI logs: `gh run view <RUN_ID> --log-failed`
2. Compare with act output
3. Identify discrepancy:
   - Missing environment variable?
   - Different runner image?
   - GitHub-specific service issue?
4. Update .actrc or testing approach
5. Document learnings in this file or workflow comments

---

## Common Workflow Issues to Check

### Issue: Missing Dependencies

**Check in Workflow**:
```yaml
# ❌ BAD
- run: uv sync

# ✅ GOOD
- run: uv sync --extra dev --extra builder
```

**Test with act**: Should show dependency installation success

---

### Issue: Using pip Instead of uv

**Check in Workflow**:
```yaml
# ❌ BAD
- run: pip install pre-commit

# ✅ GOOD
- run: uv tool install pre-commit
```

**Test with act**: May work locally (system pip) but fail in CI

---

### Issue: Bare python Commands

**Check in Workflow**:
```yaml
# ❌ BAD
- run: python scripts/ci/check-links.py

# ✅ GOOD
- run: uv run python scripts/ci/check-links.py
```

**Test with act**: Shows if python is in PATH correctly

---

### Issue: Missing System Tools

**Check in Workflow**:
```yaml
# If using jq, must install it:
- name: Install jq
  run: sudo apt-get update && sudo apt-get install -y jq

# Then use it:
- run: jq '.field' file.json
```

**Test with act**: Will show "command not found" if missing

---

## Quick Reference

### Fast Validation (< 5 seconds)
```bash
make validate-workflows
```

### Medium Testing (30 seconds - 2 minutes)
```bash
make test-workflows
```

### Comprehensive Testing (2-5 minutes)
```bash
act push -W .github/workflows/ci.yaml -j test
act push -W .github/workflows/e2e-tests.yaml -j e2e-tests
act push -W .github/workflows/quality-tests.yaml -j property-tests
```

---

## Decision Tree

```
Made workflow changes?
  ├─ Changed dependency installation?
  │   └─ ✅ TEST WITH ACT (critical)
  │
  ├─ Added new tool/command?
  │   └─ ✅ TEST WITH ACT (critical)
  │
  ├─ Changed triggers/events?
  │   └─ ✅ TEST WITH ACT (recommended)
  │
  ├─ Updated comments/documentation only?
  │   └─ ⚠️ Validate syntax only (make validate-workflows)
  │
  └─ Changed job dependencies/order?
      └─ ✅ TEST WITH ACT (critical)
```

---

**Remember**: 5 minutes of local `act` testing saves 30+ minutes of CI debugging!

---

**Maintained By**: CI/CD Team
**Last Review**: 2025-11-02
