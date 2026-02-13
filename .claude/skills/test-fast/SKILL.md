---
name: test-fast
description: Execute tests with optimized speed for rapid development iteration. Use for fast feedback during development without coverage overhead.
allowed-tools:
  - "Bash(uv:*)"
  - "Bash(npm:*)"
  - Read
---
# Fast Test Iteration

**Usage**: `/test-fast` or `/test-fast <mode>`

**Modes**: `dev` (recommended) | `core` (fastest) | `parallel` (all parallel) | `unit` (unit only, no coverage)

---

## Why Fast Testing?

Standard tests with coverage are slow (`make test` ~45-60s, `make test-unit` ~30-40s).
Fast testing provides **40-70% speed improvement** by disabling coverage and enabling parallelism:

| Command | Duration | Coverage | Use Case |
|---------|----------|----------|----------|
| `make test` | ~45-60s | Yes | Pre-merge validation |
| `make test-unit` | ~30-40s | Yes | Standard unit tests |
| `make test-dev` | ~15-20s | No | **Active development** |
| `make test-fast` | ~20-30s | No | Quick full suite |
| `make test-fast-core` | ~3-5s | No | **Rapid iteration** |

---

## Fast Testing Options

### Development Mode (RECOMMENDED)

Best for active development - parallel, fast-fail, skip slow tests:
```bash
make test-dev
```
- Parallel (`pytest -n auto`), stop on first failure (`-x`), max 3 failures (`--maxfail=3`)
- Skip slow tests (`-m "unit and not slow"`), no coverage, short traceback (`--tb=short`)
- **Speed**: 40-60% faster | **Use case**: Active development, quick feedback loop

### Fastest Core Tests

Minimal test set for ultra-rapid iteration:
```bash
make test-fast-core
```
- Core unit tests only, parallel, no slow/integration tests, minimal output (`-q`)
- **Speed**: Typically < 5 seconds | **Use case**: Rapid iteration on critical paths

### All Tests (No Coverage)

Run all tests without coverage overhead:
```bash
make test-fast
```
- All unit and integration tests, parallel, no coverage, short traceback
- **Speed**: 30-40% faster than `make test` | **Use case**: Pre-commit validation

### Parallel Execution

Leverage multiple CPU cores:
```bash
make test-fast        # All tests in parallel
make test-fast-unit   # Unit tests only in parallel
```
- Automatic CPU core detection (`-n auto`), no coverage
- **Speed**: 40-60% faster, scales with CPU cores

---

## When to Use Each Mode

| Scenario | Command | Why |
|----------|---------|-----|
| Active development | `make test-dev` | Fast feedback, skips slow tests |
| Quick sanity check | `make test-fast-core` | Ultra-fast, core only |
| Pre-commit | `make test-fast` | Full suite, no coverage overhead |
| Before PR/merge | `make test` | Full validation with coverage |

---

## On-Demand References

For workflow integration, additional options, and watch mode, see [references/mode-configs.md](references/mode-configs.md).

For optimization tips, performance guidance, and example sessions, see [references/optimization-tips.md](references/optimization-tips.md).

---

## Related Commands

- `/test-summary` - Comprehensive test report with coverage
- `/test-all` - Run complete test suite
- `/test-failure-analysis` - Deep analysis of test failures
- `/quick-debug` - Fast debugging for test issues

---

**Last Updated**: 2025-10-21 | **Version**: 1.0 | **Performance**: 40-70% faster than standard tests
