# Pre-commit Hooks Catalog

**Last Updated**: 2025-11-23
**Purpose**: Complete catalog of all pre-commit hooks and validation strategy
**Total Hooks**: 78 hooks across 3 stages
**Config File**: `.pre-commit-config.yaml` (1,597 lines)

---

## Quick Reference

### Running Hooks Manually

```bash
# Run all pre-commit hooks on changed files
pre-commit run

# Run all hooks on all files
pre-commit run --all-files

# Run specific hook
pre-commit run ruff --all-files
pre-commit run mypy --all-files

# Skip specific hooks (use sparingly!)
SKIP=ruff,mypy git commit -m "message"

# Skip all hooks (emergency only!)
git commit --no-verify -m "message"
```

### Hook Stages

| Stage | Trigger | Duration | Purpose |
|-------|---------|----------|---------|
| **pre-commit** | `git commit` | < 30s | Fast validation on changed files |
| **pre-push** | `git push` | 8-12 min | Comprehensive validation (matches CI) |
| **manual** | Explicit run | Varies | Special-purpose hooks (run on-demand) |

---

## Pre-commit Stage (Fast - < 30s)

**Trigger**: Automatically on `git commit`
**Scope**: Changed files only
**Purpose**: Fast feedback loop for developers

### Code Quality & Formatting (7 hooks)

#### 1. `trailing-whitespace`
**Source**: pre-commit/pre-commit-hooks
**Purpose**: Remove trailing whitespace
**Auto-fix**: Yes

#### 2. `end-of-file-fixer`
**Source**: pre-commit/pre-commit-hooks
**Purpose**: Ensure files end with newline
**Auto-fix**: Yes

#### 3. `mixed-line-ending`
**Source**: pre-commit/pre-commit-hooks
**Purpose**: Normalize line endings (LF)
**Auto-fix**: Yes

#### 4. `ruff` (Linter)
**Source**: astral-sh/ruff-pre-commit
**Purpose**: Replaces isort + flake8 (10-100x faster)
**Auto-fix**: Yes (with `--fix`)
**Checks**: Import sorting, code style, complexity, unused imports
**Excludes**: `clients/(python|go|typescript)/`

#### 5. `ruff-format` (Formatter)
**Source**: astral-sh/ruff-pre-commit
**Purpose**: Replaces Black formatter
**Auto-fix**: Yes
**Args**: `--line-length=127`
**Excludes**: `clients/(python|go|typescript)/`

#### 6. `check-ast`
**Source**: pre-commit/pre-commit-hooks
**Purpose**: Validate Python syntax (no SyntaxError)
**Regression Prevention**: Commit a57fcc95 (pytestmark inside imports)

#### 7. `bandit`
**Source**: pycqa/bandit
**Purpose**: Security vulnerability scanning
**Args**: `-lll` (low confidence level), `--skip B608`
**Checks**: OWASP Top 10, hardcoded passwords, SQL injection, etc.

---

### Configuration Validation (5 hooks)

#### 8. `check-yaml`
**Source**: pre-commit/pre-commit-hooks
**Purpose**: Validate YAML syntax
**Args**: `--allow-multiple-documents`
**Excludes**: Helm templates (`deployments/helm/*/templates/`)

#### 9. `check-json`
**Source**: pre-commit/pre-commit-hooks
**Purpose**: Validate JSON syntax

#### 10. `check-toml`
**Source**: pre-commit/pre-commit-hooks
**Purpose**: Validate TOML syntax (pyproject.toml, etc.)

#### 11. `check-merge-conflict`
**Source**: pre-commit/pre-commit-hooks
**Purpose**: Detect unresolved merge conflict markers

#### 12. `check-added-large-files`
**Source**: pre-commit/pre-commit-hooks
**Purpose**: Prevent commits of large files
**Args**: `--maxkb=500`
**Excludes**: `uv.lock` (package manager lockfile)

---

### Security (2 hooks)

#### 13. `detect-private-key`
**Source**: pre-commit/pre-commit-hooks
**Purpose**: Prevent committing private keys
**Checks**: RSA, DSA, EC, OpenSSH private keys

#### 14. `gitleaks`
**Source**: gitleaks/gitleaks
**Purpose**: Detect secrets and credentials
**Checks**: API keys, tokens, passwords, AWS keys, etc.

---

### Python-Specific Validation (Local Hooks)

#### 15. `check-subprocess-timeout`
**Source**: Local (`.pre-commit-hooks/check_subprocess_timeout.py`)
**Purpose**: Enforce `timeout` parameter in `subprocess.run()`
**Scope**: `tests/**/*.py`
**Prevents**: Test hangs from missing timeouts
**Regression**: 119 subprocess.run() calls without timeout

---

## Pre-push Stage (Comprehensive - 8-12 min)

**Trigger**: Automatically on `git push`
**Scope**: All files
**Purpose**: Full validation matching CI exactly

### Type Checking (1 hook)

#### 16. `mypy` (Blocking)
**Source**: pre-commit/mirrors-mypy
**Purpose**: Static type checking
**Scope**: `src/mcp_server_langgraph/`
**Args**:
- `--ignore-missing-imports`
- `--check-untyped-defs`
- `--no-implicit-optional`
- `--show-error-codes`
- `--pretty`

**Dependencies**: pydantic, fastapi, types-PyYAML, types-redis, types-requests
**Status**: Enabled 2025-11-23 (all errors fixed)
**Previous**: 110+ errors kept in manual stage
**Current**: 0 errors, blocks pre-push

**Why blocking now**: Agent.py type errors fixed with `type: ignore[arg-type]` for list variance issues

---

### Test Execution (via custom script)

**Note**: Pre-push hooks also trigger `scripts/run_pre_push_tests.py` which runs:

1. **Lockfile validation** (< 30s)
   - Verify `uv.lock` synchronized with `pyproject.toml`
   - Check for dependency conflicts

2. **Workflow validation** (< 30s)
   - Validate GitHub Actions YAML syntax
   - Check workflow consistency

3. **Test suite** (3-5 min)
   - Unit tests (`pytest -m unit`)
   - Smoke tests (`pytest -m smoke`)
   - Integration tests (`pytest -m integration`)
   - Property tests (`pytest -m property`)

4. **All pre-commit hooks on all files** (5-8 min)
   - Re-runs all pre-commit stage hooks
   - Ensures comprehensive validation

**Total Duration**: 8-12 minutes (matches CI)

---

## Manual Stage (On-Demand)

**Trigger**: Explicit `pre-commit run <hook-id> --hook-stage manual`
**Purpose**: Special-purpose validation not needed for every commit

### Deployment Validation (20+ hooks)

These hooks validate deployment configurations but are too slow for regular commits:

#### Kubernetes Validation
- `validate-k8s-manifests` - Validate Kubernetes YAML syntax
- `validate-kustomize-overlays` - Validate Kustomize structure
- `check-kustomize-bases` - Verify Kustomize base references

#### Helm Validation
- `validate-helm-chart` - Validate Helm chart structure
- `helm-lint` - Run `helm lint` on charts
- `check-helm-dependencies` - Verify Helm dependencies

#### Docker Validation
- `validate-docker-compose` - Validate Docker Compose syntax
- `check-docker-compose-ports` - Verify port mappings
- `validate-dockerfile` - Dockerfile best practices

#### Terraform Validation
- `terraform-fmt` - Format Terraform files
- `terraform-validate` - Validate Terraform configuration
- `tflint` - Terraform linting

---

### Documentation Validation (10+ hooks)

#### MDX Documentation
- `validate-mdx-syntax` - Validate MDX files (Mintlify docs)
- `check-mdx-frontmatter` - Verify frontmatter fields
- `validate-mdx-links` - Check for broken links

#### API Documentation
- `validate-openapi-schema` - Validate OpenAPI 3.0 schema
- `check-openapi-examples` - Verify API examples

#### ADR Validation
- `check-adr-numbering` - Verify ADR sequential numbering
- `validate-adr-sync` - Ensure ADR index synchronized

---

### Test Infrastructure Validation (15+ hooks)

#### Test Organization
- `validate-fixture-organization` - Check for duplicate autouse fixtures
- `check-test-memory-safety` - Verify AsyncMock teardown patterns
- `validate-test-constants` - Ensure constant synchronization

#### Test Quality
- `check-test-markers` - Verify pytest markers registered
- `validate-test-naming` - Check test naming conventions
- `check-property-test-settings` - Validate Hypothesis settings

---

### Custom Project Validation (25+ hooks)

These are project-specific validation hooks:

#### Code Quality
- `check-import-order` - Verify import organization
- `validate-type-hints` - Check type hint coverage
- `check-docstring-coverage` - Ensure docstring presence

#### Configuration
- `validate-settings-schema` - Pydantic settings validation
- `check-env-var-usage` - Verify environment variables documented
- `validate-feature-flags` - Check feature flag configuration

#### Security
- `check-dependency-vulnerabilities` - Scan for CVEs
- `validate-auth-configuration` - Check auth settings
- `check-secrets-management` - Verify Infisical usage

#### Infrastructure
- `validate-prometheus-rules` - Validate Prometheus alert rules
- `check-grafana-dashboards` - Validate Grafana JSON
- `validate-service-mesh` - Check Istio/Linkerd config

---

## Hook Execution Strategy

### Two-Stage Validation

**Stage 1: Pre-commit (Fast - < 30s)**
- Auto-fixers (ruff-format, trailing-whitespace)
- Linters (ruff, bandit)
- Basic validation (YAML, JSON, TOML)
- Security scans (gitleaks, detect-private-key)

**Stage 2: Pre-push (Comprehensive - 8-12 min)**
- MyPy type checking (all files)
- Full test suite (unit, integration, property)
- All pre-commit hooks on all files
- Lockfile and workflow validation

**Rationale**:
- Commit frequently without friction
- Push only fully validated code
- Matches CI validation exactly
- Prevents surprises in CI

---

### When to Skip Hooks

**NEVER skip without good reason.** Hooks prevent bugs and security issues.

**Valid reasons to skip**:
1. **Emergency hotfix** - Critical production issue
2. **WIP commit** - Work-in-progress (use `git commit -m "WIP: ..."` instead)
3. **Known false positive** - Hook incorrectly flagging valid code
4. **Infrastructure changes** - Changes to .pre-commit-config.yaml itself

**How to skip**:
```bash
# Skip specific hooks
SKIP=ruff,mypy git commit -m "message"

# Skip all pre-commit hooks (emergency only)
git commit --no-verify -m "message"

# Skip pre-push hooks (emergency only)
git push --no-verify
```

**After skipping**: Always fix issues and re-push properly validated code ASAP

---

## Hook Configuration

### Global Settings

**From `.pre-commit-config.yaml`**:
```yaml
default_language_version:
  python: python3.13

fail_fast: false  # Run all hooks even if one fails
minimum_pre_commit_version: 3.0.0

ci:
  autofix_prs: false  # Don't auto-commit fixes in PRs
  autoupdate_schedule: monthly
```

---

### Updating Hooks

```bash
# Update all hooks to latest versions
pre-commit autoupdate

# Install/update hooks after config changes
pre-commit install --install-hooks
pre-commit install --hook-type pre-push

# Clean and reinstall
pre-commit clean
pre-commit install
```

---

## Troubleshooting

### Issue: Hook taking too long

**Symptoms**: Pre-commit stage > 30s

**Diagnosis**:
```bash
# Run with timing
time pre-commit run --all-files

# Identify slow hook
pre-commit run <hook-id> --verbose
```

**Fix**: Move slow hook to manual stage or optimize

---

### Issue: Hook failing incorrectly

**Symptoms**: Valid code flagged as error

**Diagnosis**:
```bash
# Run specific hook with verbose output
pre-commit run <hook-id> --verbose --all-files

# Check hook configuration
grep -A 10 "id: <hook-id>" .pre-commit-config.yaml
```

**Fix**:
- Add exclusion pattern to hook config
- Update hook args to reduce sensitivity
- Report false positive to hook maintainer

---

### Issue: Hooks not running

**Symptoms**: `git commit` doesn't trigger hooks

**Diagnosis**:
```bash
# Check if hooks installed
ls -la .git/hooks/

# Verify pre-commit config
pre-commit validate-config

# Check hook status
pre-commit run --all-files
```

**Fix**:
```bash
# Reinstall hooks
pre-commit install
pre-commit install --hook-type pre-push
```

---

## Hook Development

### Adding a New Hook

1. **Determine stage** (pre-commit, pre-push, or manual)
2. **Add to `.pre-commit-config.yaml`**:

```yaml
- repo: local
  hooks:
    - id: my-new-hook
      name: My New Hook
      description: |
        What this hook does and why.
        Include examples and edge cases.
      entry: python .pre-commit-hooks/my_new_hook.py
      language: python
      types: [python]  # or [yaml], [markdown], etc.
      files: ^src/.*\.py$  # Optional: limit scope
      exclude: ^tests/  # Optional: exclude patterns
      stages: [pre-commit]  # or [pre-push], [manual]
```

3. **Create hook script** (`.pre-commit-hooks/my_new_hook.py`)
4. **Test hook**:
```bash
# Test on specific files
pre-commit run my-new-hook --files src/module.py

# Test on all files
pre-commit run my-new-hook --all-files
```

5. **Document in this file** (update catalog)

---

### Hook Script Template

```python
#!/usr/bin/env python3
"""
My New Hook - Brief description

Purpose: What this hook validates
Scope: Which files it checks
Prevents: What regressions it prevents
"""

import argparse
import sys
from pathlib import Path


def check_file(filepath: Path) -> list[str]:
    """Check single file for violations"""
    violations = []

    with open(filepath) as f:
        content = f.read()

    # Validation logic here
    if "bad_pattern" in content:
        violations.append(
            f"{filepath}: Found bad_pattern (line X)"
        )

    return violations


def main() -> int:
    """Main entry point"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("filenames", nargs="*", help="Files to check")
    args = parser.parse_args()

    all_violations = []
    for filename in args.filenames:
        violations = check_file(Path(filename))
        all_violations.extend(violations)

    if all_violations:
        for violation in all_violations:
            print(violation, file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
```

---

## Integration with CI/CD

### Pre-commit.ci

**Enabled**: Yes (runs on all PRs)
**Config**: `.pre-commit-config.yaml` → `ci:` section
**Behavior**:
- Runs all pre-commit stage hooks on PR
- Does NOT auto-commit fixes (`autofix_prs: false`)
- Updates hooks monthly (`autoupdate_schedule: monthly`)

---

### GitHub Actions

**Workflow**: `.github/workflows/ci.yaml`
**Integration**: Pre-push hooks match CI validation exactly

**CI runs**:
1. All pre-commit hooks (`pre-commit run --all-files`)
2. MyPy type checking (same args as pre-push hook)
3. Full test suite (same markers as pre-push)
4. Deployment validation (manual hooks)

**Parity**: Pre-push duration (8-12 min) matches CI

---

## Performance Optimization

### Hook Performance Tips

1. **Use `files:` pattern** - Limit hook scope
   ```yaml
   files: ^src/.*\.py$  # Only check src/ Python files
   ```

2. **Use `exclude:` pattern** - Skip irrelevant files
   ```yaml
   exclude: ^(tests|docs)/  # Skip tests and docs
   ```

3. **Use `language: system`** - Avoid venv creation
   ```yaml
   language: system  # Use system Python (faster)
   ```

4. **Run expensive hooks in parallel**:
   ```bash
   # Run multiple hooks concurrently
   pre-commit run --hook-stage manual --all-files &
   ```

---

## Related Documentation

- Pre-commit Configuration: `.pre-commit-config.yaml`
- Hook Scripts: `.pre-commit-hooks/` directory
- Pre-push Test Script: `scripts/run_pre_push_tests.py`
- Hook Performance Metrics: `scripts/measure_hook_performance.py`
- CI Workflow: `.github/workflows/ci.yaml`
- Testing Guide: `TESTING.md#git-hooks-and-validation`

---

**Last Audit**: 2025-11-23 (78 hooks cataloged)
**Reorganization**: 2025-11-13 (Two-stage strategy implemented)
**Status**: Production-ready, matches CI validation exactly
