---
description: Git hooks and validation workflow - pre-commit and pre-push stages
paths:
  - ".git/**"
  - ".pre-commit-config.yaml"
globs:
  - "**/*.py"
  - "**/*.ts"
  - "**/*.tsx"
---

# Git Validation Rules

## Two-Stage Hook Strategy

| Stage | Trigger | Duration | Scope |
|-------|---------|----------|-------|
| Pre-commit | `git commit` | < 30s | Changed files |
| Pre-push | `git push` | 8-12 min | All files |

## Pre-commit (< 30s)

**Auto-fixers**: trailing-whitespace, end-of-file-fixer, ruff, ruff-format
**Validators**: check-yaml, check-json, bandit, gitleaks

## Pre-push (8-12 min)

1. Lockfile sync validation
2. MyPy type checking
3. Full test suite (unit + integration + property)
4. All hooks on all files

## Quick Commands

```bash
make lint-check       # Non-destructive check
make lint-fix         # Auto-fix formatting
make lint-pre-commit  # Simulate pre-commit
make lint-pre-push    # Simulate pre-push
```

## Troubleshooting

| Issue | Fix |
|-------|-----|
| "Re-stage files" | `git add <file>` after auto-fix |
| Pre-push failed | `make lint-fix` then retry |
| CI fails but local passes | `pre-commit run --all-files` |

## Bypass (Emergency Only)

```bash
git commit --no-verify -m "WIP: emergency"
git push --no-verify
```

**Warning**: CI may fail. Fix and re-push ASAP.
