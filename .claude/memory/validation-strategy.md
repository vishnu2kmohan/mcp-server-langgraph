# Validation Strategy

**Purpose**: Consolidated lint, hooks, and validation reference
**Merged from**: lint-workflow.md + pre-commit-hooks-catalog.md (now removed)

---

## Two-Stage Hook Strategy

| Stage | Trigger | Duration | Scope | Purpose |
|-------|---------|----------|-------|---------|
| Pre-commit | `git commit` | < 30s | Changed files | Fast feedback |
| Pre-push | `git push` | 8-12 min | All files | CI parity |

---

## Pre-commit Hooks (< 30s)

### Auto-fixers
| Hook | Purpose | Auto-fix |
|------|---------|----------|
| `trailing-whitespace` | Remove trailing whitespace | Yes |
| `end-of-file-fixer` | Ensure files end with newline | Yes |
| `ruff` | Linting (replaces isort + flake8) | Yes |
| `ruff-format` | Formatting (replaces black) | Yes |

### Validators
| Hook | Purpose | Blocks |
|------|---------|--------|
| `check-yaml` | YAML syntax | Yes |
| `check-json` | JSON syntax | Yes |
| `check-toml` | TOML syntax | Yes |
| `bandit` | Security vulnerabilities | Yes |
| `gitleaks` | Secret detection | Yes |
| `detect-private-key` | Private key detection | Yes |
| `check-added-large-files` | Files > 500KB | Yes |

---

## Pre-push Hooks (8-12 min)

### Phase 1: Validation (< 30s)
- Lockfile sync (`uv.lock` ↔ `pyproject.toml`)
- Workflow YAML validation

### Phase 2: Type Checking (1-2 min)
- MyPy on `src/mcp_server_langgraph/`
- Strict mode with gradual rollout

### Phase 3: Tests (3-5 min)
- Unit tests (`pytest -m unit`)
- Smoke tests (`pytest -m smoke`)
- Integration tests (`pytest -m integration`)
- Property tests (`pytest -m property`)

### Phase 4: All Hooks (5-8 min)
- All pre-commit hooks on all files

---

## Frontend Hooks

| Hook | Stage | Purpose | Duration |
|------|-------|---------|----------|
| `frontend-lint` | pre-commit | ESLint | 2-4s |
| `frontend-format-check` | pre-commit | Prettier | 1-2s |
| `frontend-typecheck` | pre-push | TypeScript | 3-30s |
| `frontend-build` | pre-push | Vite build | 20-40s |
| `frontend-test` | pre-push | Vitest | 20-30s |

---

## Quick Commands

```bash
# Manual validation
make lint-check     # Non-destructive check
make lint-fix       # Auto-fix formatting

# Simulate hooks
make lint-pre-commit   # Test pre-commit
make lint-pre-push     # Test pre-push

# Reinstall hooks
make lint-install
```

---

## Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| "Re-stage files" | Auto-fixer modified files | `git add <file>` |
| Pre-push failed | Lint issues | `make lint-fix` |
| CI fails but local passes | Scope difference | `pre-commit run --all-files` |
| Hooks not running | Not installed | `make lint-install` |
| MyPy errors | Type issues | Warning-only (gradual rollout) |

---

## Bypass (Emergency Only)

```bash
git commit --no-verify -m "WIP: emergency"
git push --no-verify
```

**Warning**: CI may fail. Fix and re-push properly ASAP.

---

## Hook Configuration

**Config Files**:
- `.pre-commit-config.yaml` - Hook definitions
- `pyproject.toml` - Ruff, mypy settings
- `.git/hooks/pre-push` - Custom pre-push script

---

## CI/CD Alignment

| Check | Pre-commit | Pre-push | CI |
|-------|-----------|----------|-----|
| Ruff format | Auto-fix | Validate | Validate |
| Ruff check | Auto-fix | Validate | Validate |
| MyPy | - | Warning | Warning |
| Bandit | Blocking | Blocking | Blocking |
| Tests | - | Full suite | Full suite |

---

**Full Reference**: `docs-internal/testing/TESTING.md#git-hooks-and-validation`
