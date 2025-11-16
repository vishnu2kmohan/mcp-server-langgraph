# Pre-Push Hook Analysis & Optimization Opportunities

**Total pre-push hooks**: 45 hooks
**Estimated total runtime**: 8-12 minutes (acceptable for pre-push)

## Category Breakdown

### Documentation Validation (8 hooks)
1. `validate-mintlify-docs` - Mintlify documentation validation
2. `validate-docs-navigation` - Navigation consistency
3. `check-doc-links` - Internal link checking
4. **`mintlify-broken-links-check`** - PRIMARY validator (runs Mintlify CLI)
5. `validate-documentation-integrity` - ADR sync, Mermaid diagrams
6. `validate-documentation-structure` - Orphaned files, ADR numbering
7. `validate-adr-index` - ADR index up-to-date
8. `check-mermaid-styling` - Mermaid diagram styling

**⚡ OPTIMIZATION**: Potential overlap detected!
- `mintlify-broken-links-check` is marked as PRIMARY validator
- It covers navigation, links, frontmatter, MDX parsing
- Consider consolidating with `check-doc-links` and `validate-docs-navigation`

**Recommendation**: Keep `mintlify-broken-links-check` as authoritative, move others to manual or less frequent stages

---

### Test Validation & Quality (13 hooks)
1. `validate-pytest-config` - Pytest configuration compatibility
2. `validate-test-fixtures` - Fixture common issues
3. `validate-fixture-organization` - No duplicate fixtures
4. `regression-prevention-tests` - CI/CD regression prevention
5. `detect-dead-test-code` - Dead code in fixtures (Codex P0)
6. `validate-api-schemas` - API response schema validation
7. `validate-test-time-bombs` - Future dates/model names
8. `check-e2e-completion` - E2E test progress tracking
9. `check-test-sleep-budget` - Sleep time monitoring
10. `validate-meta-test-quality` - Property test quality
11. `validate-test-isolation` - Pytest-xdist best practices
12. `validate-test-dependencies` - Import dependencies check
13. `validate-fixture-scopes` - Fixture scope compatibility

**⚡ OPTIMIZATION**: Many test validators!
- Consider combining static analysis checks into one script
- `validate-test-fixtures`, `validate-fixture-organization`, `validate-test-isolation` could merge
- Budget/completion tracking could move to manual stage (informational only)

**Recommendation**:
- **Keep critical**: regression-prevention, dead-test-code, test-dependencies, fixture-scopes
- **Consider consolidating**: test-fixtures + fixture-organization + test-isolation → `validate-test-quality`
- **Move to manual**: check-e2e-completion, check-test-sleep-budget (informational tracking)

---

### Deployment & Infrastructure (11 hooks)
1. `validate-deployment-secrets` - Secret keys alignment
2. `validate-cors-security` - CORS configuration
3. `check-hardcoded-credentials` - No hardcoded credentials
4. `validate-redis-password-required` - Redis password mandatory
5. `trivy-scan-k8s-manifests` - Security scanning
6. `validate-gke-autopilot-compliance` - GKE Autopilot constraints
7. `validate-kustomize-builds` - Kustomize overlays build
8. `validate-network-policies` - NetworkPolicy ports
9. `validate-service-accounts` - RBAC & separation
10. `validate-serviceaccount-naming` - Naming consistency
11. `check-helm-placeholders` - Unresolved placeholders

**✅ STATUS**: Well-organized, no obvious redundancy
- Each check addresses specific deployment concerns
- All are lightweight (mostly YAML parsing)

**Recommendation**: Keep as-is, these are critical for deployment safety

---

### Kubernetes/Cloud Validation (5 hooks)
1. `validate-docker-compose-health-checks` - Docker Compose health checks
2. `helm-lint` - Helm chart validation
3. `validate-cloud-overlays` - AWS/GCP/Azure overlays
4. `validate-no-placeholders` - Production placeholder check
5. `terraform_validate` - Terraform syntax

**✅ STATUS**: Clean separation of concerns

**Recommendation**: Keep as-is

---

### Code Quality & Type Checking (4 hooks)
1. `mypy` - Type checking
2. `validate-dependency-injection` - DI configuration
3. `validate-github-action-versions` - GitHub Actions versions
4. `validate-workflow-test-deps` - Workflow dependency validation

**✅ STATUS**: All essential, no overlap

**Recommendation**: Keep as-is

---

### GitHub Actions/Workflow Validation (3 hooks)
1. `actionlint-workflow-validation` - Advanced workflow validation
2. `validate-github-action-versions` - Action version validation
3. `validate-workflow-test-deps` - Workflow test dependencies

**⚡ OPTIMIZATION**: Slight overlap
- `actionlint-workflow-validation` and `validate-github-action-versions` both validate workflows
- Could potentially merge version checking into actionlint

**Recommendation**: Keep separate (different concerns - syntax vs versions)

---

### Coverage & Performance (2 hooks)
1. `validate-minimum-coverage` - ≥ 64% coverage threshold
2. Manual: `validate-test-suite-performance` - < 120s duration (commented out in manual stage)

**⚡ OPTIMIZATION**: Coverage validation runs full test suite!
- This could be VERY slow (runs pytest --cov on entire codebase)
- Consider making this a CI-only check, not pre-push

**Recommendation**:
- Move `validate-minimum-coverage` to manual or CI-only
- Developers can run `pytest --cov` locally when needed
- CI will catch coverage regression

---

### Special Cases (2 hooks)
1. `validate-pre-push-hook` - Validates pre-push hook itself (meta!)
2. `check-async-mock-configuration` - Manual stage currently (will move to pre-push after fixes)

**Status**: Meta-validation is clever but could cause issues if hook breaks

---

## Summary of Optimization Opportunities

### 🔴 HIGH IMPACT - Remove from Pre-Push

**`validate-minimum-coverage`** (Line 1409-1443)
- **Why**: Runs full test suite with coverage - VERY slow
- **Impact**: Could save 2-4 minutes per push
- **Alternative**: Run in CI only, or move to manual stage
- **Risk**: Low (CI will still catch coverage regression)

```yaml
# BEFORE: stages: [pre-push]
# AFTER:  stages: [manual]  # or remove entirely, rely on CI
```

---

### 🟡 MEDIUM IMPACT - Consolidate Overlapping Hooks

**Documentation Validators** (Lines 224-346)
- `validate-mintlify-docs`
- `validate-docs-navigation`
- `check-doc-links`
- **`mintlify-broken-links-check`** ← PRIMARY

**Why**: Mintlify CLI is marked as PRIMARY and comprehensive
**Impact**: Save 30-60 seconds
**Recommendation**:
```yaml
# Keep: mintlify-broken-links-check (PRIMARY)
# Move to manual: validate-docs-navigation, check-doc-links
# Reason: Mintlify CLI already validates navigation and links
```

---

**Test Quality Validators** (Lines 605-650, 1276-1303)
- `validate-test-fixtures`
- `validate-fixture-organization`
- `validate-test-isolation`

**Why**: All analyze test files for quality issues
**Impact**: Save 20-40 seconds
**Recommendation**: Merge into single `validate-test-quality.py` script

---

### 🟢 LOW IMPACT - Move Informational Hooks to Manual

**Progress Tracking** (Lines 769-796)
- `check-e2e-completion` - Tracks E2E progress
- `check-test-sleep-budget` - Monitors sleep time

**Why**: Informational only, don't block pushes
**Impact**: Save 10-20 seconds
**Recommendation**:
```yaml
stages: [manual]  # Run periodically to check progress
```

---

## Recommended Action Plan

### Phase 1: Quick Wins (Save ~3-5 minutes)

1. **Move `validate-minimum-coverage` to CI-only**
   ```yaml
   # Remove from .pre-commit-config.yaml pre-push stage
   # Add to .github/workflows/quality.yml instead
   ```

2. **Move informational hooks to manual**
   ```yaml
   - check-e2e-completion: stages: [manual]
   - check-test-sleep-budget: stages: [manual]
   ```

### Phase 2: Consolidation (Save ~1-2 minutes)

3. **Consolidate documentation validators**
   - Keep `mintlify-broken-links-check` as PRIMARY
   - Move `validate-docs-navigation` and `check-doc-links` to manual
   - Update documentation to explain Mintlify is authoritative

4. **Merge test quality validators**
   - Create `scripts/validate_test_quality.py` that combines:
     - validate-test-fixtures
     - validate-fixture-organization
     - validate-test-isolation
   - Single hook, single pytest run

### Phase 3: Long-term Optimization

5. **Parallel execution investigation**
   - Some hooks could run in parallel
   - Pre-commit framework runs sequentially by default
   - Consider custom script to parallelize independent checks

---

## Current Estimated Runtime

| Category | Hooks | Est. Time |
|----------|-------|-----------|
| Documentation | 8 | 90-120s |
| Test Validation | 13 | 120-180s |
| Deployment | 11 | 60-90s |
| Kubernetes | 5 | 45-60s |
| Code Quality | 4 | 60-90s |
| Workflows | 3 | 30-45s |
| Coverage | 1 | 120-240s ⚠️ |
| Special | 2 | 10-20s |
| **TOTAL** | **45** | **8-14 min** |

---

## After Phase 1 Optimizations

| Category | Hooks | Est. Time | Change |
|----------|-------|-----------|--------|
| Documentation | 5 | 60-80s | ⬇️ -30s |
| Test Validation | 10 | 90-120s | ⬇️ -30s |
| Deployment | 11 | 60-90s | - |
| Kubernetes | 5 | 45-60s | - |
| Code Quality | 4 | 60-90s | - |
| Workflows | 3 | 30-45s | - |
| Coverage | 0 | 0s | ⬇️ -180s |
| Special | 2 | 10-20s | - |
| **TOTAL** | **40** | **5-7 min** | **⬇️ -40%** |

---

## Recommendation: START HERE

**Immediate action** (no risk, high impact):

```bash
# 1. Move coverage validation to CI-only (saves ~3 minutes)
# Edit .pre-commit-config.yaml line 1415:
stages: [manual]  # Run manually with: pre-commit run validate-minimum-coverage

# 2. Move informational tracking to manual
# Edit lines 776, 796:
stages: [manual]  # Track progress periodically, not every push
```

**Impact**:
- Pre-push time: 8-12 min → 5-7 min (40% faster)
- Safety: No reduction (CI still runs all checks)
- Developer experience: ⬆️ Significantly improved

---

## Questions to Consider

1. **Coverage in CI vs Pre-Push**: Is it acceptable to move coverage validation to CI-only?
   - ✅ YES: CI catches regressions before merge
   - ❌ NO: Keep but consider optimizing pytest run

2. **Documentation validation overlap**: Trust Mintlify CLI as PRIMARY?
   - ✅ YES: It's authoritative and comprehensive
   - ❌ NO: Keep redundant validators for extra safety

3. **Test quality consolidation**: Worth the refactoring effort?
   - Moderate effort, moderate gain (~1 min saved)
   - Could improve maintainability

---

**Next Steps**: Review recommendations and approve Phase 1 optimizations?
