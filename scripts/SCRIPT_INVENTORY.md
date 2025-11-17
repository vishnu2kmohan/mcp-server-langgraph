# Scripts Directory Inventory

**Last Updated**: 2025-11-16
**Total Scripts**: 172 (123 Python, 49 Shell)
**Audit Scope**: Comprehensive analysis of all scripts in `scripts/` directory

---

## Executive Summary

| Category | Count | Description |
|----------|-------|-------------|
| **CRITICAL (Multi-system)** | 7 | Used in hooks + Makefile + workflows |
| **CRITICAL (Hooks only)** | 23 | Used in `.pre-commit-config.yaml` |
| **IMPORTANT (Makefile)** | 10 | Used in Makefile targets |
| **IMPORTANT (Workflows)** | 15 | Used in GitHub Actions workflows |
| **UNUSED/Utilities** | 117 | Not referenced in active systems |

---

## CRITICAL Scripts (Priority 1)

### Multi-System Integration (Highest Priority)

#### TRIPLE Usage (Hooks + Make + Workflows)

| Script | Purpose | Hook ID | Makefile Target | Workflow |
|--------|---------|---------|----------------|----------|
| `validators/adr_sync_validator.py` | ADR synchronization validation | `validate-adr-sync` | `docs-validate` | `docs-validation.yaml` |
| `validators/mdx_extension_validator.py` | MDX file extension validation | `validate-mdx-extensions` | `docs-validate-mdx` | `docs-validation.yaml` |

#### DUAL Usage (Hooks + Make)

| Script | Purpose | Hook ID | Makefile Target |
|--------|---------|---------|-----------------|
| `check_async_mock_configuration.py` | Prevent authorization bypass bugs | `check-async-mock-configuration` | `validate-tests` |
| `check_test_memory_safety.py` | Prevent pytest-xdist OOM (200GB+) | `check-test-memory-safety` | `validate-tests` |

### Pre-Commit Hooks Only (23 Scripts)

#### Test Quality & Safety (10 scripts)

| Script | Hook ID | Purpose |
|--------|---------|---------|
| `check_test_sleep_duration.py` | `check-test-sleep-duration` | Enforce max sleep durations (unit: 0.5s, integration: 2.0s) |
| `check_test_sleep_budget.py` | `check-test-sleep-budget` | Monitor total wall-clock sleep (max: 60s) |
| `check_async_mock_usage.py` | `check-async-mock-usage` | Prevent hanging tests from non-async mocks |
| `check_e2e_completion.py` | `check-e2e-completion` | Track E2E implementation progress (target: 80%) |
| `detect_dead_test_code.py` | `detect-dead-test-code` | Detect unreachable code after return statements |
| `validate_api_schemas.py` | `validate-api-schemas` | Ensure API responses match Pydantic schemas |
| `validate_test_time_bombs.py` | `validate-test-time-bombs` | Detect hard-coded future dates/models |
| `validate_test_fixtures.py` | `validate-test-fixtures` | Validate FastAPI dependency overrides |
| `validate_test_ids.py` | `validate-test-ids` | Prevent hardcoded IDs causing xdist pollution |
| `validate_pytest_markers.py` | `validate-pytest-markers` | Ensure all pytest.mark.* are registered |

#### Documentation & ADR Management (4 scripts)

| Script | Hook ID | Purpose |
|--------|---------|---------|
| `standardize_frontmatter.py` | `check-frontmatter-quotes` | Standardize MDX frontmatter quote style |
| `validators/todo_audit.py` | `audit-todo-fixme-markers` | Audit TODO/FIXME/XXX markers |
| `generate_adr_index.py` | `validate-adr-index` | Generate and validate ADR index |
| `check_mermaid_styling.py` | `check-mermaid-styling` | Validate Mermaid ColorBrewer2 Set3 styling |

#### Infrastructure & Configuration (6 scripts)

| Script | Hook ID | Purpose |
|--------|---------|---------|
| `validate_github_workflows.py` | `validate-github-workflows` | Validate workflow context usage |
| `validate_gke_autopilot_compliance.py` | `validate-gke-autopilot-compliance` | Validate GKE Autopilot constraints |
| `validate_serviceaccount_names.py` | `validate-serviceaccount-naming` | Validate K8s ServiceAccount naming |
| `validate_docker_image_contents.py` | `validate-docker-image-contents` | Validate Docker image contents |
| `validate_keycloak_config.py` | `validate-keycloak-config` | Validate Keycloak service config |
| `validation/validate_test_isolation.py` | `validate-test-isolation` | Validate pytest-xdist isolation patterns |

#### Test & Build Configuration (2 scripts)

| Script | Hook ID | Purpose |
|--------|---------|---------|
| `validate_pytest_config.py` | `validate-pytest-config` | Ensure pytest addopts have required plugins |
| `validate_pre_push_hook.py` | `validate-pre-push-hook` | Validate pre-push hook completeness |

---

## IMPORTANT Scripts (Priority 2)

### Makefile Integration (10 scripts)

| Category | Script | Make Target | Purpose |
|----------|--------|-------------|---------|
| **Setup** | `setup/setup_openfga.py` | `setup-openfga` | Initialize OpenFGA server |
| **Setup** | `setup/setup_keycloak.py` | `setup-keycloak` | Initialize Keycloak |
| **Setup** | `setup/setup_infisical.py` | `setup-infisical` | Initialize Infisical secrets |
| **Validation** | `validation/validate_deployments.py` | `validate-deployments` | Validate deployment configs |
| **Validation** | `validation/validate_openapi.py` | `validate-openapi` | Validate OpenAPI schema |
| **Deployment** | `deployment/test_k8s_deployment.sh` | `test-k8s-deploy` | Test K8s deployment |
| **Deployment** | `deployment/test_helm_deployment.sh` | `test-helm-deploy` | Test Helm deployment |
| **Reporting** | `security/generate_report.py` | `security-report` | Generate security reports |
| **Reporting** | `generate_test_stats.py` | `test-stats` | Generate test statistics |
| **Version** | `check_version_consistency.py` | `validate-versions` | Check version consistency |

### GitHub Workflows Integration (15 scripts)

| Category | Scripts | Workflow Usage |
|----------|---------|----------------|
| **Metrics** | `ci/dora_metrics.py`, `ci/track-coverage.py`, `ci/track-skipped-tests.py`, `ci/track_costs.py`, `ci/performance_regression.py` | `ci.yaml`, `metrics.yaml` |
| **Documentation** | `ci/check-links.py`, `ci/extract-changelog.py`, `fix_mdx_syntax.py` | `docs-validation.yaml`, `release.yaml` |
| **Infrastructure** | `gcp/setup-staging-infrastructure.sh`, `gcp/staging-smoke-tests.sh`, `k8s/health-check.sh`, `smoke-test-compose.sh` | `deploy-staging.yaml`, `integration-tests.yaml` |
| **Deployment** | `deployment/bump-versions.sh`, `deployment/publish_to_registry.sh` | `release.yaml`, `publish.yaml` |

---

## UNUSED/Developer Utilities (117 scripts)

### One-Time Fix/Refactoring Scripts (31 scripts)

**Purpose**: Completed code migrations and bulk fixes
**Status**: CANDIDATE FOR ARCHIVAL
**Examples**:
- `add_*.py` (20 scripts): Add missing decorators, guards, markers
- `fix_*.py` (11 scripts): Fix import issues, deprecations, syntax

**Recommendation**: Archive to `scripts/archive/completed/` since these were one-time use.

### Unused Validators (15 scripts)

**Purpose**: Validators not integrated into hooks/Make/CI
**Status**: EVALUATE FOR INTEGRATION OR REMOVAL
**Examples**:
- `validate_all_mermaid.py` - Not used (replaced by `check_mermaid_styling.py`)
- `validate_documentation_links.py` - Not used (replaced by Mintlify validator)
- `validators/link_validator.py` - Deprecated (replaced by `mintlify broken-links`)

**Recommendation**: Remove or integrate into pre-commit hooks if valuable.

### Analysis Tools (15 scripts)

**Purpose**: Development-time analysis and profiling
**Status**: KEEP BUT DOCUMENT AS DEV UTILITIES
**Examples**:
- `identify_critical_tests.py` - Identify high-impact tests
- `measure_hook_performance.py` - Profile pre-commit hooks
- `analyze_*.py` - Various code analysis utilities

**Recommendation**: Keep but document in `scripts/README.md` as developer tools.

### Infrastructure Setup (20+ scripts)

**Purpose**: One-time infrastructure setup
**Status**: ARCHIVE OR MOVE TO DEPLOYMENT DIRECTORY
**Examples**:
- `setup/init_*.py` - One-time initialization scripts
- `gcp/create_*.sh` - GCP resource creation

**Recommendation**: Move active ones to `deployment/setup/`, archive completed ones.

### Entry Point Issues (4 scripts)

**Files**: Various `__init__.py` and package markers
**Status**: NOT EXECUTABLE SCRIPTS
**Recommendation**: These are Python package markers, not scripts - ignore in inventory.

---

## Quality Metrics

| Metric | Count | Percentage | Status |
|--------|-------|------------|--------|
| **With shebang + docstring** | 126 | 73% | EXCELLENT |
| **With shebang only** | 41 | 24% | GOOD |
| **Missing entry points** | 5 | 3% | NEEDS FIXING |
| **Has corresponding tests** | 1 file | <1% | NEEDS IMPROVEMENT |

### Scripts Needing Fixes

| Script | Issue | Fix Required |
|--------|-------|--------------|
| `validators/__init__.py` | No shebang | Not needed (package marker) |
| `setup/__init__.py` | No shebang | Not needed (package marker) |
| TBD | Missing docstrings | Add module-level docstrings |
| TBD | No tests | Add unit tests for CRITICAL scripts |

---

## Recommendations

### Immediate Actions (This Sprint) - 2025-11-16

1. **Test Coverage** (HIGH PRIORITY)
   - Add unit tests for all 30 CRITICAL scripts
   - Target: 80% coverage for scripts in hooks/Make/CI
   - Use `tests/meta/test_scripts_governance.py` as template

2. **Documentation** (MEDIUM PRIORITY)
   - Fix 5 scripts with missing shebangs (if needed)
   - Document entry points for all IMPORTANT scripts
   - Update `scripts/README.md` with this inventory reference

3. **Archive Unused** (MEDIUM PRIORITY)
   - Create `scripts/archive/completed/` directory
   - Move 31 one-time fix scripts to archive
   - Update `.gitignore` if archiving outside repo

### Short-Term (Next Sprint)

1. **Consolidation**
   - Merge duplicate `fix_*.py` utilities
   - Consolidate overlapping validators
   - Remove deprecated validators replaced by Mintlify

2. **Integration**
   - Evaluate 15 unused validators for pre-commit integration
   - Add valuable validators to `.pre-commit-config.yaml`
   - Document analysis tools in `scripts/README.md`

3. **Organization**
   - Move infrastructure setup scripts to `deployment/setup/`
   - Separate dev utilities from production scripts
   - Create `scripts/dev/` for analysis tools

### Long-Term (CI/CD Optimization)

1. **Performance**
   - Profile CRITICAL scripts to identify slowdowns
   - Optimize pre-commit hooks (target: tier-2 < 3-5min)
   - Consider caching for expensive validators

2. **Quality**
   - Achieve 90%+ test coverage for CRITICAL scripts
   - Add integration tests for multi-system scripts
   - Implement script version tracking

3. **Maintenance**
   - Quarterly review of UNUSED scripts
   - Automated detection of dead scripts
   - Enforce testing requirements for new scripts

---

## Usage Patterns

### How to Find Script Usage

```bash
# Check if script is used in pre-commit hooks
grep -r "script_name.py" .pre-commit-config.yaml

# Check if script is used in Makefile
grep -r "script_name.py" Makefile

# Check if script is used in workflows
grep -r "script_name.py" .github/workflows/

# Check if script is called by other scripts
grep -r "script_name.py" scripts/
```

### Adding New Scripts

**Requirements for CRITICAL scripts:**
1. Must have shebang and docstring
2. Must have unit tests (80%+ coverage)
3. Must be integrated into one of:
   - `.pre-commit-config.yaml` (for hooks)
   - `Makefile` (for make targets)
   - `.github/workflows/*.yaml` (for CI/CD)

**Requirements for UTILITY scripts:**
1. Should have shebang and docstring
2. Should be documented in `scripts/README.md`
3. Should have clear purpose and usage examples

---

## Appendix: Full Script List

**Note**: For full detailed list of all 172 scripts with paths and descriptions, see the audit results from 2025-11-16.

**Quick Stats**:
- **Total**: 172 scripts
- **Python**: 123 scripts (.py)
- **Shell**: 49 scripts (.sh)
- **Actively Used**: 55 scripts (32%)
- **Candidates for Archival**: 117 scripts (68%)

---

## Maintenance

**Audit Frequency**: Quarterly (every 3 months)
**Last Audit**: 2025-11-16
**Next Audit**: 2026-02-16
**Owner**: Infrastructure Team
**Reviewers**: All team members contributing to `scripts/`

**Audit Process**:
1. Run comprehensive script audit (use Task/Explore agent)
2. Update this inventory with new categorizations
3. Archive completed one-time scripts
4. Add tests for new CRITICAL scripts
5. Update `scripts/README.md` references

---

**Generated**: 2025-11-16
**By**: OpenAI Codex Remediation (Phase 2)
**Reference**: docs-internal/CODEX_FINDINGS_REMEDIATION_REPORT.md
