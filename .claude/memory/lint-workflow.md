# Lint Workflow & Enforcement Strategy

**Created**: 2025-10-20
**Purpose**: Comprehensive guide to lint enforcement before commits/pushes to prevent CI/CD failures

## Overview

This project uses a **two-stage lint enforcement strategy** to catch issues early and prevent CI/CD failures:

1. **Pre-commit hooks**: Auto-fix formatting, catch obvious errors
2. **Pre-push hooks**: Comprehensive validation before remote push

## Architecture

```
Developer Workflow:
┌─────────────────┐
│   Code Changes  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  git add files  │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│           git commit                     │
│  ┌─────────────────────────────────┐   │
│  │  PRE-COMMIT HOOK (auto-fix)     │   │
│  │  • black (auto-format)          │   │
│  │  • isort (auto-sort imports)    │   │
│  │  • flake8 (syntax check)        │   │
│  │  • mypy (type check - blocking) │   │
│  │  • bandit (security scan)       │   │
│  │  • gitleaks (secret detection)  │   │
│  └─────────────────────────────────┘   │
│           ↓ PASS                        │
│    Commit Created ✓                     │
└────────┬────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│            git push                      │
│  ┌─────────────────────────────────┐   │
│  │  PRE-PUSH HOOK (validate)       │   │
│  │  • flake8 (comprehensive)       │   │
│  │  • black --check (no auto-fix)  │   │
│  │  • isort --check                │   │
│  │  • mypy (strict, blocking)      │   │
│  │  • bandit (security)            │   │
│  │                                 │   │
│  │  Scope: Files changed from      │   │
│  │         origin/main             │   │
│  └─────────────────────────────────┘   │
│           ↓ PASS                        │
│    Push Succeeds ✓                      │
└────────┬────────────────────────────────┘
         │
         ▼
┌─────────────────┐
│   CI/CD (GitHub │
│    Actions)     │
│  • Same checks  │
│  • Should pass  │
│    (aligned!)   │
└─────────────────┘
```

## Configuration Files

### 1. `.pre-commit-config.yaml`
Pre-commit hook configuration with all linters:
- **Location**: `/home/vishnu/git/vishnu2kmohan/mcp-server-langgraph/.pre-commit-config.yaml`
- **Hooks**: black, isort, flake8, mypy, bandit, gitleaks, trailing-whitespace, etc.
- **Behavior**: Auto-fixes formatting, blocks on validation failures
- **Scope**: Staged files only (fast)

### 2. `.git/hooks/pre-push`
Custom pre-push hook script:
- **Location**: `/home/vishnu/git/vishnu2kmohan/mcp-server-langgraph/.git/hooks/pre-push`
- **Behavior**: Comprehensive validation, blocks push on failure
- **Scope**: Files changed from `origin/main` (fast, relevant)
- **Checks**: flake8, black, isort, mypy (strict), bandit

### 3. `pyproject.toml`
Central configuration for all linters:
- **black**: line-length=127, target py310-py312
- **isort**: profile=black, line-length=127
- **flake8**: max-line-length=127, ignore E203,W503
- **mypy**: strict mode with gradual rollout (see phases)

### 4. `Makefile`
Convenient targets for manual lint operations:
- `make lint-check` - Non-destructive check
- `make lint-fix` - Auto-fix formatting
- `make lint-pre-commit` - Simulate pre-commit hook
- `make lint-pre-push` - Simulate pre-push hook
- `make lint-install` - Install/reinstall hooks

### 5. `.claude/commands/lint.md`
Slash command for Claude Code:
- **Usage**: `/lint`
- **Purpose**: Quick lint check and troubleshooting guide

## Linter Details

### Black (Code Formatting)
- **Purpose**: Consistent code formatting
- **Behavior**: Auto-fixes in pre-commit, validates in pre-push
- **Configuration**: 127 character line length
- **Target**: Python 3.10-3.12
- **When it runs**: Pre-commit (auto-fix), Pre-push (validate)

### Isort (Import Sorting)
- **Purpose**: Consistent import order
- **Behavior**: Auto-fixes in pre-commit, validates in pre-push
- **Configuration**: black profile, 127 line length
- **When it runs**: Pre-commit (auto-fix), Pre-push (validate)

### Flake8 (Syntax & Style)
- **Purpose**: Catch syntax errors, undefined names, style issues
- **Behavior**: Blocks on errors (E9, F63, F7, F82)
- **Configuration**: Aligned with black (ignore E203, W503)
- **When it runs**: Pre-commit, Pre-push, CI/CD

### Mypy (Type Checking)
- **Purpose**: Static type checking for type safety
- **Behavior**: **NON-BLOCKING** during gradual rollout (500+ type errors remain)
- **Configuration**: Gradual strict mode rollout:
  - **Phase 1**: Core modules (config, feature_flags, observability) - strict
  - **Phase 2**: Auth, LLM, Agent modules - strict
  - **Phase 3**: Additional modules (context_manager, parallel_executor, etc.) - strict
  - **Tests**: Excluded from strict checking
- **Strict settings**:
  - `disallow_untyped_defs = true`
  - `disallow_untyped_calls = true` (for strict modules)
  - `no_implicit_optional = true`
  - `warn_redundant_casts = true`
  - `strict_equality = true`
- **When it runs**: Pre-push (warning-only), CI/CD (warning-only), `make lint-check`
- **Current status**:
  - Pre-commit hook: **DISABLED** (commented out in `.pre-commit-config.yaml`)
  - Pre-push hook: **WARNING ONLY** (shows errors but doesn't block)
  - CI/CD: `continue-on-error: true` (non-blocking)
  - Local `make lint-check`: Runs but doesn't block workflow
- **Future**: Will be made blocking once type error count is reduced significantly

### Bandit (Security Scanning)
- **Purpose**: Detect common security issues
- **Behavior**: Blocks on high/medium severity issues (-ll flag)
- **Scope**: Excludes tests directory
- **When it runs**: Pre-commit, Pre-push, CI/CD

### Gitleaks (Secret Detection)
- **Purpose**: Prevent committing secrets/credentials
- **Behavior**: Blocks on detected secrets
- **When it runs**: Pre-commit only

## Hook Behavior

### Pre-commit Hook Behavior

**Trigger**: `git commit`

**Scope**: Staged files only

**Checks**:
1. ✅ **Auto-fix** (modifies files, requires re-staging):
   - trailing-whitespace
   - end-of-file-fixer
   - black (formatting)
   - isort (imports)

2. ❌ **Validation** (blocks on failure):
   - check-yaml
   - check-json
   - check-toml
   - check-merge-conflict
   - detect-private-key
   - check-added-large-files (>500KB)
   - flake8 (critical errors only)
   - bandit (security scan)
   - gitleaks (secret detection)
   - **Note**: mypy is currently **DISABLED** in pre-commit hook (commented out in `.pre-commit-config.yaml` due to 500+ type errors)

**On Failure**:
- Commit is **blocked**
- Modified files must be re-staged (`git add`)
- Error messages show exactly what failed
- User must fix and retry

**Bypass** (not recommended):
```bash
git commit --no-verify
```

### Pre-push Hook Behavior

**Trigger**: `git push`

**Scope**: Files changed from `origin/main`

**Checks** (in order):
1. flake8 (comprehensive syntax check)
2. black --check (no auto-fix)
3. isort --check (no auto-fix)
4. mypy (type checking - **WARNING ONLY**, non-blocking during gradual rollout)
5. bandit (security scan)

**On Failure**:
- Push is **blocked**
- Clear error messages with fix instructions
- Suggests running `make format` or `make lint-check`

**On Success**:
- Push proceeds normally
- CI/CD should pass (checks are aligned)

**Bypass** (not recommended):
```bash
git push --no-verify
```

## Common Workflows

### Standard Development Workflow

```bash
# 1. Make code changes
vim src/mcp_server_langgraph/core/agent.py

# 2. Check lint status (optional but recommended)
make lint-check

# 3. Auto-fix formatting issues
make lint-fix

# 4. Stage changes
git add src/mcp_server_langgraph/core/agent.py

# 5. Commit (pre-commit hook runs automatically)
git commit -m "feat: add new agent capability"
# → Pre-commit runs: black, isort, flake8, mypy, bandit
# → Auto-fixes formatting, requires re-staging if needed
# → Blocks on validation failures

# 6. If auto-fixed, re-stage and commit again
git add src/mcp_server_langgraph/core/agent.py
git commit -m "feat: add new agent capability"

# 7. Push (pre-push hook runs automatically)
git push origin feature-branch
# → Pre-push runs: comprehensive validation
# → Blocks on any failures
# → Provides fix instructions
```

### Quick Fix Workflow

```bash
# Check what's wrong
make lint-check

# Auto-fix what can be fixed
make lint-fix

# Verify remaining issues
make lint-check

# Fix manually (mypy, flake8, bandit errors)
vim src/file.py

# Test pre-commit hook
make lint-pre-commit

# Test pre-push hook
make lint-pre-push

# Commit and push
git add .
git commit -m "fix: resolve lint issues"
git push
```

### Emergency Bypass Workflow

**⚠️ NOT RECOMMENDED - Only use in true emergencies**

```bash
# Bypass pre-commit
git commit --no-verify -m "WIP: emergency fix"

# Bypass pre-push
git push --no-verify

# ⚠️ WARNING: CI/CD may fail if lint issues exist
```

## Makefile Targets

### `make lint-check`
- **Purpose**: Check for lint issues without modifying files
- **Scope**: `src/` directory
- **Behavior**: Non-destructive, shows all issues
- **Use case**: Before committing, to see what needs fixing

### `make lint-fix`
- **Purpose**: Auto-fix formatting issues
- **What it fixes**: black formatting, isort import order
- **What it doesn't fix**: flake8, mypy, bandit errors (manual fix required)
- **Use case**: Quick formatting fix before commit

### `make lint-pre-commit`
- **Purpose**: Simulate what pre-commit hook will do
- **Scope**: All files (or staged if available)
- **Behavior**: Same as actual pre-commit hook
- **Use case**: Testing hook behavior without committing

### `make lint-pre-push`
- **Purpose**: Simulate what pre-push hook will do
- **Scope**: Files changed from `origin/main`
- **Behavior**: Same as actual pre-push hook
- **Use case**: Testing before pushing, catch issues early

### `make lint-install`
- **Purpose**: Install or reinstall lint hooks
- **What it does**:
  - Runs `pre-commit install`
  - Makes pre-push hook executable
  - Shows confirmation
- **Use case**: Initial setup, or if hooks get corrupted

### `make lint` (legacy)
- **Purpose**: Basic lint check (old target, still works)
- **Checks**: flake8, mypy on root directory
- **Note**: Prefer `make lint-check` for comprehensive checks

### `make format` (legacy)
- **Purpose**: Format code (old target, still works)
- **What it does**: black, isort on entire repo
- **Note**: Prefer `make lint-fix` for consistency

## Slash Command: `/lint`

**File**: `.claude/commands/lint.md`

**Usage**: Type `/lint` in Claude Code

**What it does**:
1. Runs comprehensive lint checks
2. Reports results with clear formatting
3. Provides fix suggestions
4. Shows next steps

**Example output**:
```
🔍 Running comprehensive lint checks...

- ✅ flake8: 0 errors
- ✅ black: All files formatted correctly
❌ isort: 2 files need import sorting
❌ mypy: 5 type errors found
- ✅ bandit: No security issues

🔧 Auto-fix suggestions:
  make lint-fix  # Fix isort issues

📝 Manual fixes needed:
  src/core/agent.py:42: error: Missing type annotation
  src/llm/factory.py:15: error: Incompatible return type

🚀 Next steps:
  1. Run: make lint-fix
  2. Fix mypy errors manually
  3. Run: make lint-pre-commit
  4. Commit when all checks pass
```

## CI/CD Alignment

### Local Checks vs CI/CD

The lint configuration is **intentionally aligned** between local and CI/CD:

| Check | Pre-commit | Pre-push | CI/CD |
|-------|-----------|----------|-------|
| black | ✅ Auto-fix | ✅ Validate | ✅ Validate |
| isort | ✅ Auto-fix | ✅ Validate | ✅ Validate |
| flake8 | ✅ Critical | ✅ Full | ✅ Full |
| mypy | ❌ Disabled* | ⚠️ Warning** | ⚠️ Warning** |
| bandit | ✅ Blocking | ✅ Blocking | ✅ Blocking |

\* Mypy is **disabled** in pre-commit hook (commented out in `.pre-commit-config.yaml`) due to 500+ type errors requiring gradual resolution
\** Mypy runs but is **non-blocking** (warning-only) during gradual rollout. Will be made blocking once type error count is significantly reduced.

### Why the Difference?

- **Local hooks**: Stricter to catch issues early
- **CI/CD mypy**: Currently non-blocking during gradual rollout
- **Future**: CI will be blocking once all modules pass strict type checking

### CI/CD Workflow File

**File**: `.github/workflows/ci.yaml`

**Lint Job** (lines 140-189):
```yaml
lint:
  name: Lint
  runs-on: ubuntu-latest
  steps:
    - name: Run flake8
      run: flake8 . --count --select=E9,F63,F7,F82 ...

    - name: Run black check
      run: black --check . --exclude venv

    - name: Run isort check
      run: isort --check . --skip venv ...

    - name: Run mypy
      run: mypy src/ --ignore-missing-imports
      continue-on-error: true  # TODO: Remove after strict rollout

    - name: Security scan with bandit
      run: bandit -r . -x ./tests,./venv -ll
```

**Build Job Dependency** (line 277):
```yaml
build-and-push:
  needs: [test, lint, validate-deployments]
```

This means **lint must pass** for builds/deploys to proceed!

## Troubleshooting

### "Pre-commit hook modified files, please re-stage"

**Cause**: black or isort auto-fixed formatting

**Solution**:
```bash
# Re-stage the auto-fixed files
git add <file>

# Commit again
git commit -m "your message"
```

### "Mypy errors in lint-check output"

**Cause**: Type checking errors (mypy is **warning-only**, won't block commits)

**Solution** (optional, errors are non-blocking):
```bash
# See detailed errors
make lint-check

# Fix type annotations manually (optional)
vim src/file.py

# Verify fix
uv run mypy src/file.py

# Commit (mypy won't block)
git commit

# Note: You can safely ignore mypy warnings during gradual rollout
# However, fixing them helps improve code quality and will be required in future
```

### "Pre-push hook failed, push blocked"

**Cause**: Lint issues on changed files

**Solution**:
```bash
# 1. See what failed
make lint-pre-push

# 2. Auto-fix formatting
make lint-fix

# 3. Check remaining issues
make lint-check

# 4. Fix manually

# 5. Commit fixes
git add .
git commit -m "fix: resolve lint issues"

# 6. Try push again
git push
```

### "CI/CD failing but local hooks passed"

**Cause**: Scope difference (local checks changed files, CI checks all)

**Solution**:
```bash
# Run pre-commit on all files (not just changed)
uv run pre-commit run --all-files

# Fix any new issues

# Commit and push
git add .
git commit -m "fix: CI lint issues"
git push
```

### "Hooks not running at all"

**Cause**: Hooks not installed or corrupted

**Solution**:
```bash
# Reinstall hooks
make lint-install

# Verify installation
ls -la .git/hooks/pre-commit
ls -la .git/hooks/pre-push

# Test hooks
make lint-pre-commit
make lint-pre-push
```

## Best Practices

### For Developers

1. **Run `make lint-check` before staging**: Catch issues early
2. **Use `make lint-fix` liberally**: Auto-fix what can be fixed
3. **Test hooks before pushing**: Run `make lint-pre-push` to avoid surprises
4. **Don't bypass hooks**: Use `--no-verify` only in true emergencies
5. **Consider fixing mypy errors**: While currently non-blocking, reducing type errors helps code quality and prepares for future strict enforcement

### For Code Reviewers

1. **Verify CI/CD passed**: Green checks mean lint passed
2. **Look for `--no-verify` in commits**: Should be questioned
3. **Check type annotations**: Ensure new code has proper types
4. **Review bandit warnings**: Security should never be ignored

### For Maintainers

1. **Keep hooks in sync with CI**: Update both `.pre-commit-config.yaml` and `.github/workflows/ci.yaml`
2. **Document hook changes**: Update this file when adding new checks
3. **Test hook modifications**: Run `make lint-pre-commit` and `make lint-pre-push` after changes
4. **Monitor CI failures**: If CI fails but hooks passed, investigate scope issues

## Future Enhancements

### Planned Improvements

1. **Mypy enforcement**:
   - Phase 1: Reduce type errors from 500+ to <100 through gradual fixes
   - Phase 2: Re-enable mypy in pre-commit hook (blocking)
   - Phase 3: Make pre-push mypy blocking
   - Phase 4: Remove `continue-on-error: true` in CI/CD
2. **Coverage in pre-push**: Add test coverage check to pre-push hook
3. **Performance tracking**: Add timing metrics to hook output
4. **Selective scope**: Allow running hooks on specific file patterns

### Configuration Evolution

As the codebase matures:
- **Mypy strictness**: Gradually enable strict mode for more modules
- **Flake8 rules**: Add more style checks (currently only critical errors)
- **Custom rules**: Add project-specific linting rules

## Reference Links

- **Pre-commit docs**: https://pre-commit.com/
- **Black docs**: https://black.readthedocs.io/
- **Isort docs**: https://pycqa.github.io/isort/
- **Flake8 docs**: https://flake8.pycqa.org/
- **Mypy docs**: https://mypy.readthedocs.io/
- **Bandit docs**: https://bandit.readthedocs.io/

## History

- **2025-10-21**: Documentation alignment and mypy status clarification
  - Updated documentation to reflect actual mypy enforcement status (non-blocking/disabled)
  - Clarified that mypy is disabled in pre-commit, warning-only in pre-push
  - Added roadmap for gradual mypy enforcement
  - Fixed inconsistencies between docs and implementation

- **2025-10-20**: Initial implementation of two-stage lint enforcement
  - Added enhanced `.pre-commit-config.yaml` (mypy initially included then disabled due to 500+ errors)
  - Created custom `.git/hooks/pre-push` script
  - Added Makefile targets: `lint-check`, `lint-fix`, `lint-pre-commit`, `lint-pre-push`, `lint-install`
  - Created `/lint` slash command
  - Documented complete workflow in this file

---

**Maintained by**: Project maintainers
**Last updated**: 2025-10-20
**Status**: Active, production-ready
