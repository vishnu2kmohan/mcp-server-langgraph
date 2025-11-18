# Run Comprehensive Lint Checks

Execute comprehensive code quality checks to ensure code passes all lint validations before commit/push.

## Quick Lint Operations

### Check for Issues (Non-destructive)
```bash
make lint-check
```
Runs all lint checks without modifying files:
- ruff check (linting - replaces Flake8 + isort)
- ruff format --check (formatting check - replaces Black)
- mypy (type checking - **warning-only**, non-blocking during gradual rollout)
- bandit (security scan)

### Auto-fix Formatting Issues
```bash
make lint-fix
```
Automatically fixes:
- Linting issues (ruff check --fix)
- Code formatting (ruff format)

Then run `make lint-check` to verify remaining issues.

## Pre-commit/Pre-push Simulation

### Test Pre-commit Hook
```bash
make lint-pre-commit
```
Simulates what will run when you commit:
- Runs on all files (or staged files if available)
- Auto-fixes with Ruff (linting + formatting)
- Runs mypy, bandit validation
- Shows exactly what the pre-commit hook will do

### Test Pre-push Hook
```bash
make lint-pre-push
```
Simulates what will run when you push:
- Runs on files changed from `origin/main`
- Comprehensive validation (ruff, mypy, bandit)
- Blocks if any check fails

## Individual Linters

### Ruff (Linting - replaces Flake8 + isort)
```bash
# Check only
uv run ruff check src/

# Auto-fix
uv run ruff check --fix src/
```
Catches:
- Syntax errors
- Undefined names
- Import issues
- Import order violations
- Code style violations (E, W, F, C90, N rules)
- Critical code issues

### Ruff Format (Formatting - replaces Black)
```bash
# Check only
uv run ruff format --check src/

# Auto-fix
uv run ruff format src/
```
Black-compatible formatting with 127 character line length.

### Mypy (Type Checking)
```bash
uv run mypy src/ --ignore-missing-imports --show-error-codes
```
Checks type safety based on `pyproject.toml` configuration.

**Note**: Mypy is currently **non-blocking** (warning-only) during gradual rollout.
500+ type errors remain to be fixed. Mypy will be made blocking in future once
type error count is significantly reduced.

### Bandit (Security Scan)
```bash
uv run bandit -r src/ -ll
```
Scans for common security issues.

## Install/Reinstall Hooks

```bash
make lint-install
```
Installs or reinstalls:
- Pre-commit hook (runs on `git commit`)
- Pre-push hook (runs on `git push`)

## Troubleshooting

### "Lint checks failed" - How to fix:

1. **Auto-fixable issues (ruff)**:
   ```bash
   make lint-fix
   ```

2. **Check what's still wrong**:
   ```bash
   make lint-check
   ```

3. **Fix remaining issues manually**:
   - **ruff errors**: Most are auto-fixable, remaining must be fixed manually
   - **bandit errors**: Must be fixed (security issues)
   - **mypy errors**: Optional during gradual rollout (type annotations)

4. **Test before committing**:
   ```bash
   make lint-pre-commit
   ```

**Note**: Only ruff and bandit errors will block commits/pushes. Mypy errors
are currently warnings only.

### Bypass hooks (NOT RECOMMENDED):
```bash
git commit --no-verify
git push --no-verify
```
Only use in emergencies - will break CI/CD if lint fails.

## Workflow Integration

### Before Committing:
```bash
# 1. Check current status
make lint-check

# 2. Auto-fix what you can
make lint-fix

# 3. Fix remaining issues manually

# 4. Test pre-commit hook
make lint-pre-commit
```

### Before Pushing:
```bash
# Test what pre-push will check
make lint-pre-push
```

### CI/CD Alignment:
The local lint checks match what CI/CD runs:
- Pre-commit: Formatting + basic validation (mypy disabled due to 500+ errors)
- Pre-push: Comprehensive checks (mypy warning-only, same as CI lint job)
- CI will fail if pre-push passes but CI fails (rare, but possible)

**Mypy Status**:
- Pre-commit hook: **Disabled** (commented out in `.pre-commit-config.yaml`)
- Pre-push hook: **Warning-only** (shows errors but doesn't block)
- CI/CD: **Warning-only** (`continue-on-error: true`)
- Future: Will be made **blocking** once type error count is reduced

## Summary

After running lint checks, provide:
- ✅ Checks that passed
- ❌ Checks that failed with error details (blocking: ruff, bandit)
- ⚠️ Mypy warnings (non-blocking, optional to fix)
- 🔧 Auto-fix suggestions
- 📝 File references for manual fixes
- 🚀 Next steps to resolve all issues

## Important Notes

### Mypy is Non-Blocking
During gradual rollout, mypy type checking is **non-blocking**:
- Shows warnings but doesn't prevent commits/pushes
- Fixing mypy errors is **optional** but recommended
- Future versions will make `mypy` blocking once error count is reduced
- See `.claude/memory/lint-workflow.md` for full mypy enforcement roadmap

### What Will Block You
Only these checks will prevent commits/pushes:
- **ruff check**: Linting errors (syntax, undefined names, imports, code style)
- **ruff format**: Formatting violations (auto-fixed, just re-stage files)
- **bandit**: Security vulnerabilities (high/medium severity)
