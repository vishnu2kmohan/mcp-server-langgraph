# Run Comprehensive Lint Checks

Execute comprehensive code quality checks to ensure code passes all lint validations before commit/push.

## Quick Lint Operations

### Check for Issues (Non-destructive)
```bash
make lint-check
```
Runs all lint checks without modifying files:
- flake8 (syntax errors, code style)
- black (formatting check)
- isort (import order check)
- mypy (type checking)
- bandit (security scan)

### Auto-fix Formatting Issues
```bash
make lint-fix
```
Automatically fixes:
- Code formatting (black)
- Import order (isort)

Then run `make lint-check` to verify remaining issues.

## Pre-commit/Pre-push Simulation

### Test Pre-commit Hook
```bash
make lint-pre-commit
```
Simulates what will run when you commit:
- Runs on all files (or staged files if available)
- Auto-fixes black/isort issues
- Runs flake8, mypy, bandit validation
- Shows exactly what the pre-commit hook will do

### Test Pre-push Hook
```bash
make lint-pre-push
```
Simulates what will run when you push:
- Runs on files changed from `origin/main`
- Comprehensive validation (flake8, black, isort, mypy, bandit)
- Blocks if any check fails

## Individual Linters

### Flake8 (Syntax & Style)
```bash
uv run flake8 src/ --count --select=E9,F63,F7,F82 --show-source --statistics
```
Catches:
- Syntax errors
- Undefined names
- Import issues
- Critical code issues

### Black (Code Formatting)
```bash
# Check only
uv run black --check src/ --line-length=127

# Auto-fix
uv run black src/ --line-length=127
```

### Isort (Import Sorting)
```bash
# Check only
uv run isort --check src/ --profile=black --line-length=127

# Auto-fix
uv run isort src/ --profile=black --line-length=127
```

### Mypy (Type Checking)
```bash
uv run mypy src/ --ignore-missing-imports --show-error-codes
```
Enforces type safety based on `pyproject.toml` configuration.

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

1. **Auto-fixable issues (black/isort)**:
   ```bash
   make lint-fix
   ```

2. **Check what's still wrong**:
   ```bash
   make lint-check
   ```

3. **Fix remaining issues manually** (flake8, mypy, bandit errors)

4. **Test before committing**:
   ```bash
   make lint-pre-commit
   ```

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
The local lint checks match exactly what CI/CD runs:
- Pre-commit: Formatting + basic validation
- Pre-push: Comprehensive checks (same as CI lint job)
- CI will fail if pre-push passes but CI fails (shouldn't happen!)

## Summary

After running lint checks, provide:
- ✅ Checks that passed
- ❌ Checks that failed with error details
- 🔧 Auto-fix suggestions
- 📝 File references for manual fixes
- 🚀 Next steps to resolve all issues
