# Pre-Push Hook Performance Optimization Plan

**Status:** 🟡 **HIGH PRIORITY - Developer Productivity**
**Baseline:** 8-12 minutes push time (43 pre-push hooks)
**Target:** 2-4 minutes push time (<15 consolidated hooks)
**Impact:** 50-70% reduction in wait time
**Estimated Effort:** 3-4 hours

---

## Problem Analysis

### Current State (43 Hooks)

**Issue:** Many hooks run `uv run --frozen pytest` on individual test files/functions, causing:
- **43 separate pytest invocations** during each push
- **43× Python interpreter startup overhead** (~1-2s each)
- **43× pytest initialization overhead** (~0.5-1s each)
- **Total overhead:** ~64-129 seconds just in startup costs
- **Actual test time:** ~4-7 minutes
- **TOTAL:** 8-12 minutes per push

**Developer Impact:**
- Long wait times discourage frequent pushes
- Context switching during wait reduces productivity
- Frustration with slow feedback loops

### Root Cause

Hooks were designed for **granular file-specific validation** (good intent), but resulted in **excessive process overhead** (poor performance).

**Example - Deployment Hooks (Lines 460-491):**
```yaml
# CURRENT: 4 separate hooks, 4 pytest invocations
- id: validate-deployment-secrets
  entry: uv run --frozen pytest tests/deployment/test_helm_configuration.py::test_deployment_secret_keys_exist_in_template

- id: validate-cors-security
  entry: uv run --frozen pytest tests/deployment/test_helm_configuration.py::test_kong_cors_not_wildcard_with_credentials

- id: check-hardcoded-credentials
  entry: uv run --frozen pytest tests/deployment/test_helm_configuration.py::test_no_hardcoded_credentials_in_configmap

- id: validate-redis-password-required
  entry: uv run --frozen pytest tests/deployment/test_helm_configuration.py::test_redis_password_not_optional
```

**Problem:** 4× pytest startup for tests in the SAME FILE!

---

## Optimization Strategy

### Principle 1: Consolidate Related Tests

**Group tests by:**
1. Same test file
2. Same test domain (deployment, meta, docs, etc.)
3. Similar runtime characteristics

**Example - Consolidated Deployment Hook:**
```yaml
# OPTIMIZED: 1 hook, 1 pytest invocation
- id: validate-deployment-configuration
  name: Validate Deployment Configuration (Helm + Kustomize)
  entry: uv run --frozen pytest tests/deployment/test_helm_configuration.py -v --tb=short
  language: system
  files: ^deployments/.*\.(yaml|yml)$
  pass_filenames: false
  stages: [pre-push]
```

**Savings:** 4 hooks → 1 hook = **75% reduction** for this group

### Principle 2: Use pytest-testmon for Incremental Testing

**Install pytest-testmon:**
```toml
# pyproject.toml
[tool.pytest.ini_options]
# Enable test monitoring for incremental runs
testmon_data_path = ".testmon"
```

**Benefits:**
- Only run tests affected by changed files
- ~60-80% reduction in test execution time for typical changes
- Works across pytest invocations (maintains state)

**Example:**
```bash
# First push: Runs all tests (8-12 min)
git push

# Subsequent push (changed 1 file): Runs only affected tests (~2-3 min)
git push
```

### Principle 3: Parallel Hook Execution (Where Safe)

**Pre-commit supports parallel execution:**
```yaml
# Run linters in parallel (read-only, independent)
- id: flake8
  require_serial: false  # ← Allow parallel execution

- id: mypy
  require_serial: false  # ← Allow parallel execution

# Run tests serially (may have side effects)
- id: test-suite
  require_serial: true  # ← Force sequential
```

**Savings:** 30-40% reduction on independent checks

---

## Consolidation Plan

### Group 1: Deployment Tests (15 hooks → 3 hooks)

**Current Hooks:**
1. validate-deployment-secrets
2. validate-cors-security
3. check-hardcoded-credentials
4. validate-redis-password-required
5. validate-kustomize-builds
6. validate-network-policies
7. validate-service-accounts
8. validate-docker-compose-qdrant
9. trivy-scan-k8s-manifests
10. ... (more deployment hooks)

**Consolidated:**
```yaml
- id: validate-helm-configuration
  name: Validate Helm Configuration
  entry: uv run --frozen pytest tests/deployment/test_helm_configuration.py -v --tb=short
  files: ^deployments/helm/.*\.(yaml|yml)$
  stages: [pre-push]

- id: validate-kustomize-deployments
  name: Validate Kustomize Deployments
  entry: uv run --frozen pytest tests/deployment/test_kustomize_builds.py tests/deployment/test_network_policies.py tests/deployment/test_service_accounts.py -v --tb=short
  files: ^deployments/kustomize/.*\.(yaml|yml)$
  stages: [pre-push]

- id: validate-docker-compose
  name: Validate Docker Compose
  entry: uv run --frozen pytest tests/test_docker_compose_validation.py -v --tb=short
  files: ^(docker-compose.*\.ya?ml|deployments/local/.*)$
  stages: [pre-push]
```

**Savings:** 15 hooks → 3 hooks = **80% reduction**, ~3-5 min saved

### Group 2: Meta Tests (8 hooks → 2 hooks)

**Current Hooks:**
- test_property_test_quality.py
- test_context_manager_quality.py
- test_kubectl_safety.py
- test_github_actions_validation.py
- test_fixture_validation.py
- test_coverage_enforcement.py
- ... (more meta tests)

**Consolidated:**
```yaml
- id: validate-meta-tests
  name: Validate Meta Tests (Quality, Safety, Coverage)
  entry: uv run --frozen pytest tests/meta/ -v --tb=short -m "not slow"
  files: ^tests/meta/.*\.py$
  stages: [pre-push]

- id: validate-test-infrastructure
  name: Validate Test Infrastructure
  entry: uv run --frozen pytest tests/test_fixture_organization.py tests/test_regression_prevention.py -v --tb=short
  files: ^tests/(conftest|.*_fixtures).*\.py$
  stages: [pre-push]
```

**Savings:** 8 hooks → 2 hooks = **75% reduction**, ~2-3 min saved

### Group 3: Documentation Tests (5 hooks → 1 hook)

**Current Hooks:**
- test_documentation_integrity.py
- test_documentation_structure.py
- mintlify-validation (multiple)
- adr-validation

**Consolidated:**
```yaml
- id: validate-documentation
  name: Validate Documentation (Mintlify + ADRs)
  entry: uv run --frozen pytest tests/test_documentation_integrity.py tests/regression/test_documentation_structure.py -v --tb=short
  files: ^(docs/.*\.(md|mdx)|adr/.*\.md)$
  stages: [pre-push]
```

**Savings:** 5 hooks → 1 hook = **80% reduction**, ~1-2 min saved

### Group 4: Type Checking (Keep Separate - Already Optimized)

```yaml
- id: mypy
  name: MyPy Type Checking
  entry: uv run --frozen mypy src --show-error-codes
  language: system
  types: [python]
  require_serial: false  # ← Allow parallel with other checks
  stages: [pre-push]
```

**No change needed** - already efficient

### Group 5: Security Scanning (Conditional - Skip if Tools Missing)

```yaml
- id: security-scanning
  name: Security Scanning (Trivy, Bandit)
  entry: |
    bash -c '
      # Run bandit (always available)
      uv run --frozen bandit -r src/ -ll || exit 1;

      # Run trivy if available (optional)
      if command -v trivy &> /dev/null; then
        trivy config deployments --severity CRITICAL,HIGH --exit-code 1 --quiet;
      else
        echo "⚠️  Trivy not installed - skipping (non-blocking)";
      fi
    '
  language: system
  files: \.(py|ya?ml)$
  stages: [pre-push]
```

**Savings:** Combines bandit + trivy, skips gracefully if tool missing

---

## Implementation Plan

### Phase 1: Consolidate Test Hooks (2 hours)

**Steps:**
1. Create consolidated hook IDs (as shown above)
2. Update `.pre-commit-config.yaml` lines 440-1100
3. Test locally: `pre-commit run --all-files --hook-stage pre-push`
4. Verify all tests still run: `git diff --stat`
5. Commit: `git commit -m "perf: consolidate pre-push hooks (43 → ~15)"`

**Expected Outcome:**
- 43 hooks → ~15 hooks
- 8-12 min → 5-7 min push time
- All validations preserved

### Phase 2: Add pytest-testmon (30 min)

**Steps:**
1. Add to `pyproject.toml`:
   ```toml
   [tool.pytest.testmon]
   # Track which tests need re-running based on code changes
   datafile = ".testmondata"
   ```

2. Install: `uv add --dev pytest-testmon`

3. Update consolidated test hooks to use `--testmon`:
   ```yaml
   entry: uv run --frozen pytest tests/deployment/ -v --tb=short --testmon
   ```

4. Add `.testmondata` to `.gitignore`

5. Test: Make small change, verify only affected tests run

**Expected Outcome:**
- Incremental pushes: 5-7 min → 2-4 min
- First push (full): Still 5-7 min (testmon builds cache)
- Subsequent pushes: 60-70% faster

### Phase 3: Enable Parallelization (30 min)

**Steps:**
1. Add `require_serial: false` to independent hooks (linters, formatters)
2. Keep `require_serial: true` for test suites (may have state)
3. Test: `pre-commit run --all-files --hook-stage pre-push`

**Expected Outcome:**
- Additional 10-20% speedup on hooks that can run in parallel

### Phase 4: Performance Monitoring (30 min)

**Create monitoring script:**
```python
# scripts/measure_hook_performance.py
"""Measure pre-push hook performance."""

import time
import subprocess

def time_hook(hook_id):
    start = time.time()
    subprocess.run(['pre-commit', 'run', hook_id, '--all-files'], check=False)
    elapsed = time.time() - start
    return elapsed

# Measure all hooks
hooks = subprocess.check_output(['pre-commit', 'run', '--all-files', '--hook-stage', 'pre-push'], stderr=subprocess.STDOUT)

# Report slowest hooks
```

**Add to CI:**
```yaml
# .github/workflows/ci.yaml
- name: Measure hook performance
  run: python scripts/measure_hook_performance.py --stage pre-push
```

---

## Expected Results

### Before Optimization

| Category | Hooks | Time | % of Total |
|----------|-------|------|------------|
| Deployment Tests | 15 | 180s | 25% |
| Meta Tests | 8 | 120s | 17% |
| Documentation | 5 | 90s | 13% |
| Type Checking | 1 | 90s | 13% |
| Other Tests | 14 | 240s | 33% |
| **TOTAL** | **43** | **720s (12 min)** | **100%** |

### After Optimization

| Category | Hooks | Time | % of Total | Savings |
|----------|-------|------|------------|---------|
| Deployment Tests | 3 | 50s | 21% | -72% |
| Meta Tests | 2 | 35s | 15% | -71% |
| Documentation | 1 | 25s | 11% | -72% |
| Type Checking | 1 | 90s | 38% | 0% |
| Other Tests | 6 | 40s | 17% | -83% |
| **TOTAL** | **~13** | **240s (4 min)** | **100%** | **-67%** |

**With pytest-testmon (incremental):**
- **Full push:** 240s (4 min)
- **Incremental push:** 80-120s (1.5-2 min)
- **Savings:** 50-83% vs baseline

---

## Validation

### Pre-Optimization Benchmark

```bash
# Measure current performance
time git push --dry-run  # or time pre-commit run --all-files --hook-stage pre-push

# Expected: 8-12 minutes
```

### Post-Optimization Benchmark

```bash
# After consolidation
time git push --dry-run

# Expected: 4-5 minutes (first run)
# Expected: 2-3 minutes (incremental, with testmon)
```

### Success Criteria

- ✅ All existing validations preserved (same test coverage)
- ✅ Push time <5 min (full run)
- ✅ Push time <3 min (incremental run with testmon)
- ✅ No false positives/negatives introduced
- ✅ Pre-commit hook config remains maintainable

---

## Risks & Mitigation

### Risk 1: Consolidated Hooks May Fail Partially

**Issue:** If 1 of 10 tests fails in a consolidated hook, entire hook fails

**Mitigation:**
- Use pytest's `--tb=short` for concise failure output
- Group related tests (failure likely affects same area)
- Keep critical security checks separate if needed

### Risk 2: pytest-testmon False Negatives

**Issue:** testmon may miss test dependencies, skip necessary tests

**Mitigation:**
- Run full test suite periodically (CI always runs full)
- Add `--testmon-noselect` flag for full run when needed
- Monitor CI for failures not caught locally

### Risk 3: Parallel Execution Race Conditions

**Issue:** Some hooks may have hidden dependencies

**Mitigation:**
- Only parallelize truly independent hooks (linters, formatters)
- Keep test suites sequential (`require_serial: true`)
- Test thoroughly before rollout

---

## Next Steps

1. ✅ **Complete:** Analysis and planning (this document)
2. ⏳ **Pending:** Implement Phase 1 (consolidation)
3. ⏳ **Pending:** Implement Phase 2 (pytest-testmon)
4. ⏳ **Pending:** Implement Phase 3 (parallelization)
5. ⏳ **Pending:** Implement Phase 4 (monitoring)
6. ⏳ **Pending:** Validate performance gains
7. ⏳ **Pending:** Update documentation (TESTING.md, CONTRIBUTING.md)
8. ⏳ **Pending:** Train team on optimized workflow

---

## References

- **Current Config:** `.pre-commit-config.yaml:440-1100` (pre-push hooks)
- **Makefile Target:** `Makefile:565-619` (validate-pre-push)
- **Testing Guide:** `TESTING.md` (hook documentation)
- **Performance Script:** `scripts/measure_hook_performance.py` (to be created)
- **pytest-testmon Docs:** https://testmon.org/

---

**Last Updated:** 2025-11-15
**Owner:** Infrastructure Team
**Status:** Planning Complete, Implementation Pending
**Expected Delivery:** 3-4 hours of focused work
**Impact:** **67% reduction** in push time (12 min → 4 min)
