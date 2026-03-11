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

## Long-Running Command Output Capture (CRITICAL)

When running hooks, test suites, or any long-running command manually, **always
use `tee`** to capture full output to a file. Never pipe directly through `tail`
alone — it discards errors from the beginning of the output.

```bash
# CORRECT: tee captures everything, then tail the log
pre-commit run --all-files 2>&1 | tee /tmp/precommit.log
tail -60 /tmp/precommit.log  # or: Read /tmp/precommit.log

# CORRECT: tee + tail in pipeline for live summary + full capture
pytest -n auto 2>&1 | tee /tmp/pytest.log | tail -80

# WRONG: tail alone discards errors from early output
pre-commit run --all-files 2>&1 | tail -60
```

**Non-blocking batch collection**: When running hooks or tests manually to
validate before commit/push, use **non-failure-exit** mode to collect ALL
issues in a single pass rather than stopping at the first failure:

```bash
# CORRECT: Collect all issues (pytest continues past failures)
uv run --frozen pytest -n auto 2>&1 | tee /tmp/pytest.log

# CORRECT: pre-commit runs all hooks even if one fails (default behavior)
pre-commit run --all-files 2>&1 | tee /tmp/precommit.log

# WRONG: -x stops at first failure — misses other issues
uv run --frozen pytest -x 2>&1 | tee /tmp/pytest.log
```

**Log file convention**: `/tmp/{tool}-{stage}.log` (e.g., `/tmp/precommit-push.log`,
`/tmp/vitest-sharded.log`). Use `Read` tool on the log file to inspect specific
error sections after the run completes.

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
