# Scripts Directory Inventory

**Last Updated**: 2025-11-24 12:43:56
**Auto-generated** by `scripts/generate_script_inventory.py`
**Total Scripts**: 192
**Python Scripts**: 143
**Shell Scripts**: 49
**Actively Used**: 65 (33.9%)
**Unused/Utilities**: 127 (66.1%)

---

## Executive Summary

| Category | Count | Percentage | Description |
|----------|-------|------------|-------------|
| **Multi-System** | 6 | 3.1% | Used in hooks + Makefile + workflows |
| **Hooks + Makefile** | 2 | 1.0% | Dual integration (hooks + Make) |
| **Hooks + Workflows** | 3 | 1.6% | Dual integration (hooks + CI/CD) |
| **Makefile + Workflows** | 4 | 2.1% | Dual integration (Make + CI/CD) |
| **Hooks Only** | 22 | 11.5% | Pre-commit hooks only |
| **Makefile Only** | 10 | 5.2% | Makefile targets only |
| **Workflows Only** | 18 | 9.4% | GitHub Actions only |
| **Unused/Utilities** | 127 | 66.1% | Not referenced in active systems |

---

## CRITICAL Scripts (Multi-System Integration)

These scripts are used across multiple systems and are essential for the project.

| Script | Hook IDs | Makefile Targets | Workflows |
|--------|----------|------------------|----------|
| `run_pre_push_tests.py` | run-pre-push-tests | validate-pre-push-quick, validate-pre-push-full | ci |
| `adr_sync_validator.py` | validate-adr-sync | docs-validate-specialized | docs-validation |
| `mdx_extension_validator.py` | validate-mdx-extensions | docs-validate-specialized | docs-validation |
| `validate_pytest_config.py` | validate-pytest-config | validate-workflows | ci |
| `adr_sync_validator.py` | validate-adr-sync | docs-validate-specialized | docs-validation |
| `mdx_extension_validator.py` | validate-mdx-extensions | docs-validate-specialized | docs-validation |

---

## Dual Integration Scripts

### Hooks + Makefile

| Script | Hook IDs | Makefile Targets |
|--------|----------|------------------|
| `check_async_mock_configuration.py` | check-async-mock-configuration | generate-reports |
| `check_test_memory_safety.py` | check-test-memory-safety | generate-reports |

### Hooks + Workflows

| Script | Hook IDs | Workflows |
|--------|----------|----------|
| `staging-smoke-tests.sh` | shellcheck | deploy-staging-gke |
| `validate_gke_autopilot_compliance.py` | validate-workflow-file-references, validate-gke-autopilot-compliance | validate-k8s-configs |
| `validate_workflow_file_references.py` | validate-workflow-file-references | local-preflight-check |

### Makefile + Workflows

| Script | Makefile Targets | Workflows |
|--------|------------------|----------|
| `fix_mdx_syntax.py` | docs-fix-mdx | docs-validation |
| `test-integration.sh` | test-integration, test-integration-services, test-integration-build, test-integration-debug, test-coverage-combined, validate-pre-push-full | integration-tests |
| `check_version_consistency.py` | docs-validate-version | docs-validation |
| `validate_openapi.py` | validate-openapi | quality-tests |

---

## Single-System Integration Scripts

### Pre-Commit Hooks Only (22 scripts)

| Script | Hook IDs |
|--------|----------|
| `detect_dead_test_code.py` | detect-dead-test-code |
| `generate_adr_index.py` | validate-adr-index |
| `standardize_frontmatter.py` | check-frontmatter-quotes |
| `check_asyncmock_usage.py` | check-asyncmock-instantiation |
| `check_e2e_completion.py` | check-e2e-completion |
| `check_mermaid_styling.py` | check-mermaid-styling |
| `check_test_naming.py` | check-test-naming |
| `check_test_sleep_budget.py` | check-test-sleep-budget |
| `check_test_sleep_duration.py` | check-test-sleep-duration |
| `file_naming_validator.py` | validate-file-naming-conventions, validate-file-naming-conventions |
| `validate_docker_image_contents.py` | validate-docker-image-contents |
| `validate_fast.py` | validate-fast |
| `validate_github_workflows.py` | validate-github-workflows-comprehensive |
| `validate_keycloak_config.py` | validate-keycloak-config |
| `validate_pytest_fixtures.py` | validate-pytest-fixtures |
| `validate_pytest_markers.py` | validate-pytest-markers |
| `validate_test_fixtures.py` | validate-test-fixtures |
| `validate_test_ids.py` | validate-test-ids |
| `validate_test_isolation.py` | validate-test-isolation |
| `validate_workflow_test_deps.py` | validate-workflow-test-deps, validate-workflow-test-deps |

*... and 2 more scripts*

### Makefile Only (10 scripts)

| Script | Makefile Targets |
|--------|------------------|
| `generate_test_stats.py` | generate-reports |
| `test_helm_deployment.sh` | test-helm-deployment |
| `test_k8s_deployment.sh` | test-k8s-deployment |
| `generate_report.py` | security-scan-full |
| `setup_infisical.py` | setup-infisical |
| `setup_keycloak.py` | setup-keycloak |
| `setup_openfga.py` | setup-openfga |
| `wait_for_services.sh` | test-e2e, quick-start |
| `validate_deployments.py` | validate-deployments |
| `validate_docker_image_freshness.sh` | validate-docker-image |

### GitHub Actions Workflows Only (18 scripts)

| Script | Workflows |
|--------|----------|
| `setup-staging-infrastructure.sh` | deploy-staging-gke, validate-deployments |
| `check-links.py` | docs-validation, link-checker |
| `dora_metrics.py` | dora-metrics |
| `extract-changelog.py` | release |
| `performance_regression.py` | performance-regression |
| `track-coverage.py` | coverage-trend |
| `track-skipped-tests.py` | track-skipped-tests |
| `track_costs.py` | cost-tracking |
| `bump-versions.sh` | bump-deployment-versions |
| `publish_to_registry.sh` | release |
| `check-links.py` | docs-validation, link-checker |
| `setup-staging-infrastructure.sh` | deploy-staging-gke, validate-deployments |
| `health-check.sh` | ci, deploy-staging-gke |
| `smoke-test-compose.sh` | ci |
| `validate_docs.py` | docs-validation |
| `validate_pre_push_hook.py` | ci |
| `validate_repo_root_calculations.py` | smoke-tests |
| `frontmatter_validator.py` | docs-validation |

---

## Unused/Utility Scripts (127 scripts)

These scripts are not referenced in .pre-commit-config.yaml, Makefile, or GitHub Actions workflows.

**Categories**:
- One-time fix/migration scripts (candidates for archival)
- Development analysis tools (keep as utilities)
- Infrastructure setup scripts (evaluate individually)

### Analysis by Directory

**ci/**: 1 scripts
  - `__init__.py`

**completed/**: 32 scripts
  - `add_colorbrewer_styling.py`
  - `add_comprehensive_test_hooks.py`
  - `add_diagram_styling.py`
  - `add_gc_import.py`
  - `add_memory_safety_to_tests.py`
  - *... and 27 more*

**deployment/**: 1 scripts
  - `deploy_langgraph_platform.sh`

**dev/**: 4 scripts
  - `audit_resource_ratios.py`
  - `detect_missing_lang_tags.py`
  - `identify_critical_tests.py`
  - `measure_hook_performance.py`

**development/**: 4 scripts
  - `generate_clients.sh`
  - `generate_openapi.py`
  - `update_documentation.py`
  - `update_imports.py`

**docs/**: 3 scripts
  - `add_missing_frontmatter.py`
  - `add_seo_fields.py`
  - `sync-adrs.py`

**gcp/**: 4 scripts
  - `setup-vertex-ai-staging.sh`
  - `setup-workload-identity.sh`
  - `teardown-staging-infrastructure.sh`
  - `validate-staging-deployment.sh`

**profiling/**: 1 scripts
  - `profile_hooks.py`

**scripts/**: 31 scripts
  - `__init__.py`
  - `build-infisical-wheels.sh`
  - `bump-version.sh`
  - `check-deployment-health.sh`
  - `check-pr-status.sh`
  - *... and 26 more*

**security/**: 1 scripts
  - `__init__.py`

**setup/**: 4 scripts
  - `docker-compose-quickstart.sh`
  - `setup_ldap_federation.py`
  - `setup_oidc_idp.py`
  - `setup_saml_idp.py`

**unused/**: 18 scripts
  - `apply_memory_safety_fixes.py`
  - `bulk_fix_async_mock.py`
  - `calculate_gke_resources.py`
  - `ci_health_check.py`
  - `convert_inline_styles_to_classdef.py`
  - *... and 13 more*

**validation/**: 13 scripts
  - `check_async_mock_usage.py`
  - `check_internal_links.py`
  - `check_test_environment_isolation.py`
  - `validate-gcp-permissions.sh`
  - `validate_api_schemas.py`
  - *... and 8 more*

**validators/**: 3 scripts
  - `__init__.py`
  - `k8s_config_validator.py`
  - `validate_github_workflows_comprehensive.py`

**workflow/**: 7 scripts
  - `analyze-test-patterns.py`
  - `generate-burndown.py`
  - `generate-progress-report.py`
  - `todo-tracker.py`
  - `track-command-usage.py`
  - `update-context-files.py`
  - `update-handoff-files.py`

---

## Recommendations

### Phase 5.2: Archive Unused Scripts
- Move one-time fix/migration scripts to `scripts/archive/completed/`
- Archive scripts with `add_*` or `fix_*` naming patterns
- Keep development analysis tools in `scripts/dev/`

### Phase 5.3: Add Tests for Critical Scripts
- Priority: Multi-system integration scripts (highest impact)
- Target: 80%+ coverage for CRITICAL scripts
- Use `tests/meta/test_scripts_governance.py` as template

### Phase 5.4: Audit Workflows for Duplication
- Review 29 workflow files for redundant script calls
- Consolidate duplicate validation logic
- Create composite actions for common patterns

---

## Maintenance

**Audit Frequency**: Quarterly (every 3 months)
**Regenerate**: Run `python scripts/generate_script_inventory.py`
**Auto-update**: Add to pre-commit hooks or monthly cron job

---

**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**By**: scripts/generate_script_inventory.py
**Commit**: {subprocess.run(['git', 'rev-parse', '--short', 'HEAD'], capture_output=True, text=True, timeout=5).stdout.strip()}
