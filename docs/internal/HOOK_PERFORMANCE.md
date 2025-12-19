# Pre-commit Hook Performance Analysis

**Last Updated**: 2025-12-19
**Purpose**: Document hook performance and optimization opportunities

## Performance Baseline

Measured on typical development machine (Linux, 8+ cores, SSD).

### Fast Hooks (< 1 second)

| Hook | Duration | Notes |
|------|----------|-------|
| `trailing-whitespace` | 0.4s | File I/O bound |
| `end-of-file-fixer` | 0.3s | File I/O bound |
| `check-yaml` | 0.2s | Depends on file count |
| `check-json` | 0.1s | Depends on file count |
| `check-toml` | 0.1s | Depends on file count |
| `check-ast` | 0.6s | Python parsing |
| `ruff` | 0.3s | Rust-based, very fast |
| `ruff-format` | 0.3s | Rust-based, very fast |
| `gitleaks` | 0.8s | Go-based |

### Medium Hooks (1-5 seconds)

| Hook | Duration | Notes |
|------|----------|-------|
| `check-async-mock-configuration` | 1.0s | Python AST parsing |
| `validate-pytest-markers` | 1.3s | Python AST parsing |
| `validate-pytest-fixtures` | 1.5s | Python AST parsing |
| `check-test-sleep-duration` | 0.9s | Python AST parsing |

### Slow Hooks (> 5 seconds)

| Hook | Duration | Notes |
|------|----------|-------|
| `mypy` | 15-30s | Full type checking |
| `run-pre-push-tests` | 2-8 min | Full test suite |
| `frontend-build` | 30-60s | Node.js build |
| `frontend-test` | 20-40s | Vitest suite |
| `docker-build-smoke-test` | 60-120s | Docker build |
| `trivy-helm-full-scan` | 10-20s | Security scanning |

## Optimization Strategies

### 1. Staged-Only Checks

Hooks that support `pass_filenames: true` only check staged files:
- `ruff`, `ruff-format` - Already optimized
- `check-async-mock-configuration` - Fixed in commit fd02aeca
- `check-test-sleep-duration` - Staged only

### 2. Conditional Execution

Some hooks only run when relevant files change:
- `frontend-*` hooks only run when `frontend/` files change
- `validate-keycloak-config` only runs when keycloak files change
- `validate-docker-image-contents` only runs when Dockerfile changes

### 3. Stage Separation

- **pre-commit stage**: Fast checks (< 30s total)
- **pre-push stage**: Comprehensive checks (tests, mypy, builds)

### 4. Parallelization

Pre-commit runs hooks in parallel by default. Independent hooks run concurrently.

## Pre-commit vs Pre-push Distribution

### Pre-commit Stage (Target: < 30 seconds)
- All fast linting/formatting hooks
- Syntax validation
- Security scanning (gitleaks)
- Lock file validation

### Pre-push Stage (Target: < 10 minutes)
- Full test suite
- MyPy type checking
- Docker builds
- Integration tests
- Frontend builds

## Monitoring Hook Performance

### Manual Profiling
```bash
# Time a specific hook
time pre-commit run --all-files <hook-id>

# Time all pre-commit hooks
time pre-commit run --all-files

# Time all pre-push hooks
time pre-commit run --hook-stage pre-push --all-files
```

### Validation Dashboard
```bash
# Fast checks only
python scripts/validation/validate_dashboard.py --fast -v

# All checks with JSON output
python scripts/validation/validate_dashboard.py --json
```

## Recommendations

1. **Keep pre-commit under 30 seconds** - Developers run this frequently
2. **Move slow checks to pre-push** - Run comprehensive checks before push
3. **Use `pass_filenames: true`** - When checks can be localized
4. **Profile after adding hooks** - Measure impact of new hooks
5. **Consider CI offloading** - Very slow checks can run in CI only

## Troubleshooting Slow Commits

If commits are slow:

1. Check which hook is slow:
   ```bash
   pre-commit run --all-files -v 2>&1 | grep -E "^\[|Passed|Failed"
   ```

2. Skip specific hook temporarily:
   ```bash
   SKIP=hook-id git commit -m "message"
   ```

3. Skip all hooks (emergency only):
   ```bash
   git commit --no-verify -m "message"
   ```

## Changelog

- **2025-12-19**: Initial performance baseline documented
- **2025-12-19**: Fixed `check-async-mock-configuration` (was scanning all files)
