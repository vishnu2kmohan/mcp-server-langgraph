---
description: Project-specific context efficiency extensions
paths:
  - "**/*"
---

# Context Efficiency (Project Extensions)

> **Base patterns**: Inherited from global `~/.claude/rules/context-efficiency.md`
> This file adds project-specific patterns only.

## Test Parallelism (Project-Specific)

### Python - Use xdist

- Default: `make test-unit` (uses `$(PYTEST_PARALLEL_FLAG)`)
- Direct: `uv run --frozen pytest -n auto`
- Opt-out: `PYTEST_SEQUENTIAL=1 make test`

### Frontend - Use Sharded Runner for Full Suite

**ALWAYS use sharded runner** (prevents OOM with 787+ test files):
```bash
# Fastest (~5-10 min) - RECOMMENDED
make test-frontend                               # or: bash scripts/run-tests-sharded.sh --parallel
make test-frontend-fast                          # or: bash scripts/run-tests-sharded.sh --fast --parallel

# CI mode (50 shards, sequential, heap capped at 6GB)
make test-frontend-ci                            # or: bash scripts/run-tests-sharded.sh --ci
bash scripts/run-tests-sharded.sh --ci --parallel  # CI mode + parallel (power-user override)
```

**Single file or small subset** (OK to use direct vitest):
```bash
npm test -- --run src/path/to/file.test.ts
```

**NEVER use for full suite** (will OOM):
```bash
npm test -- --run           # WRONG
npx vitest run              # WRONG
npm test -- --pool=threads  # WRONG for full suite
```

## Long-Running Command Output Capture

> **Full patterns**: See global `~/.claude/rules/context-efficiency.md` §Long-Running Command Output Capture
> including PROJ_TMP setup and the **Bash tool variable expansion bug** workaround
> (CRITICAL: always include a `#` comment line before any pipeline using `$VAR`).

```bash
# Project-specific examples — note the comment line before each pipeline
# run unit tests
uv run --frozen pytest -n auto 2>&1 | tee "$PROJ_TMP/pytest.log"
# run integration tests
uv run --frozen pytest tests/integration/ 2>&1 | tee "$PROJ_TMP/pytest-integration.log"
# run pre-commit hooks
pre-commit run --all-files 2>&1 | tee "$PROJ_TMP/precommit.log"
```

---

## Bulk Operations (Project-Specific)

- **192 scripts** in `scripts/` - check `scripts/SCRIPT_INVENTORY.md` before creating new ones
- Prefer `make` targets over direct commands (parallelism applied consistently)
- Use existing bulk fix scripts from `scripts/archive/unused/` when available

## Script Reuse

Before creating bulk operation scripts, ALWAYS:

1. Read `scripts/SCRIPT_INVENTORY.md` (192 scripts documented)
2. Search: `Glob scripts/**/*.py` or `Grep "pattern" path=scripts/`
3. Check `scripts/archive/unused/` for archived but reusable scripts
4. Check `.pre-commit-config.yaml` for existing validation hooks
