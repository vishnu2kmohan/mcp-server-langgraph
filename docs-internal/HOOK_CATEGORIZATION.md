# Pre-commit vs Pre-push Hook Categorization

**Date:** 2025-11-13
**Purpose:** Eliminate CI/CD surprises by matching local validation with GitHub CI exactly

## Performance Targets

- **Pre-commit (commit stage):** < 30 seconds - Fast feedback on changed files
- **Pre-push (push stage):** 5-10 minutes - Comprehensive CI-equivalent validation on all files

## Categorization Strategy

### PRE-COMMIT HOOKS (commit stage) - ~30 hooks

#### Category A: Auto-fixers (Instant - < 1s)
| Hook ID | Trigger | Purpose |
|---------|---------|---------|
| `trailing-whitespace` | All files | Remove trailing whitespace |
| `end-of-file-fixer` | All files | Ensure final newline |
| `mixed-line-ending` | All files | Fix line ending consistency |
| `black` | Python files | Code formatting |
| `isort` | Python files | Import sorting |
| `fix-mdx-syntax` | .mdx files | Auto-fix MDX errors |
| `terraform_fmt` | .tf files | Terraform formatting |

**Count:** 7 hooks
**Duration:** < 1s total

#### Category B: Fast Linters (< 5s)
| Hook ID | Trigger | Purpose |
|---------|---------|---------|
| `check-yaml` | .yaml/.yml | YAML syntax validation |
| `check-json` | .json | JSON syntax validation |
| `check-toml` | .toml | TOML syntax validation |
| `check-added-large-files` | All files | Prevent large file commits |
| `check-merge-conflict` | All files | Detect merge conflict markers |
| `detect-private-key` | All files | Prevent private key commits |
| `gitleaks` | All files | Secret scanning |
| `flake8` | Python files | Python linting |
| `bandit` | Python files | Security vulnerability scanning |
| `shellcheck` | Shell files | Bash script linting |

**Count:** 10 hooks
**Duration:** < 5s total

#### Category C: Critical Safety Checks (< 10s)
| Hook ID | Trigger | Always Run | Purpose |
|---------|---------|------------|---------|
| `uv-lock-check` | pyproject.toml, uv.lock | No | Lockfile sync validation |
| `prevent-local-config-commits` | All files | **Yes** | Prevent .local.json commits |
| `check-test-memory-safety` | tests/**/*.py | No | Pytest-xdist memory safety |
| `check-async-mock-usage` | tests/**/*.py | No | Prevent hanging tests |
| `validate-fixture-scopes` | tests/conftest.py | No | Prevent ScopeMismatch errors |

**Count:** 5 hooks
**Duration:** < 10s total

#### Category D: File-specific Fast Validators (< 10s)
| Hook ID | Trigger | Purpose |
|---------|---------|---------|
| `check-github-workflows` | .github/workflows/*.yml | Workflow JSON schema |
| `validate-github-workflows` | .github/workflows/*.yml | Context usage validation |
| `validate-mdx-extensions` | docs/**/*.md | Ensure .mdx extension |
| `validate-mdx-frontmatter` | docs/**/*.mdx | Frontmatter validation |
| `check-frontmatter-quotes` | .mdx files | Quote style standardization |
| `validate-serviceaccount-naming` | deployments/**/serviceaccount*.yaml | SA naming consistency |
| `check-test-sleep-duration` | tests/**/*.py | Prevent excessive sleeps |

**Count:** 7 hooks
**Duration:** < 10s total

**TOTAL PRE-COMMIT: 29 hooks | Target: < 30s**

---

### PRE-PUSH HOOKS (push stage) - ~60 hooks

#### Category E: Test-running Hooks (20-60s each)
| Hook ID | Entry Command | Duration |
|---------|---------------|----------|
| `validate-deployment-secrets` | `pytest tests/deployment/test_helm_configuration.py::test_deployment_secret_keys_exist_in_template` | 20-30s |
| `validate-cors-security` | `pytest tests/deployment/test_helm_configuration.py::test_kong_cors_not_wildcard_with_credentials` | 20-30s |
| `check-hardcoded-credentials` | `pytest tests/deployment/test_helm_configuration.py::test_no_hardcoded_credentials_in_configmap` | 20-30s |
| `validate-redis-password-required` | `pytest tests/deployment/test_helm_configuration.py::test_redis_password_not_optional` | 20-30s |
| `validate-documentation-quality` | `pytest tests/meta/test_documentation_validation.py` | 30-60s |
| `validate-documentation-integrity` | `pytest tests/test_documentation_integrity.py` | 30-60s |
| `validate-documentation-structure` | `pytest tests/regression/test_documentation_structure.py` | 30-60s |
| `validate-fixture-organization` | `pytest tests/test_fixture_organization.py` | 20-30s |
| `regression-prevention-tests` | `pytest tests/test_regression_prevention.py` | 20-30s |
| `validate-meta-test-quality` | `pytest tests/meta/test_property_test_quality.py tests/meta/test_context_manager_quality.py tests/meta/test_kubectl_safety.py` | 30-60s |
| `validate-github-action-versions` | `pytest tests/meta/test_github_actions_validation.py` | 20-30s |
| `validate-kustomize-builds` | `pytest tests/deployment/test_kustomize_builds.py` | 60-90s |
| `validate-network-policies` | `pytest tests/deployment/test_network_policies.py` | 20-30s |
| `validate-service-accounts` | `pytest tests/deployment/test_service_accounts.py` | 20-30s |
| `validate-docker-compose-health-checks` | `pytest tests/test_docker_compose_validation.py::TestDockerComposeQdrantSpecific::test_qdrant_uses_grpc_health_probe` | 20-30s |
| `validate-test-dependencies` | `pytest tests/regression/test_dev_dependencies.py::test_test_imports_have_dev_dependencies` | 20-30s |

**Count:** 16 hooks
**Duration:** 5-10 minutes total (parallel pytest runs possible)

#### Category F: Documentation Validators (30-60s each)
| Hook ID | Entry Command | Duration |
|---------|---------------|----------|
| `validate-docs-navigation` | `python3 scripts/validators/navigation_validator.py` | 10-20s |
| `validate-documentation-links` | `python3 scripts/validators/link_validator.py` | 30-60s |
| `validate-documentation-images` | `python3 scripts/validators/image_validator.py` | 10-20s |
| `validate-code-block-languages` | `python3 scripts/validators/codeblock_validator.py` | 20-40s |
| `check-doc-links` | `python3 scripts/ci/check-links.py` | 30-60s |
| `validate-adr-index` | `python scripts/generate_adr_index.py --check` | 10-20s |
| `validate-mintlify-docs` | `python3 scripts/validate_mintlify_docs.py docs` | 30-60s |

**Count:** 7 hooks
**Duration:** 2-4 minutes total

#### Category G: Deployment Validators (30-90s each)
| Hook ID | Entry Command | Duration |
|---------|---------------|----------|
| `trivy-scan-k8s-manifests` | `trivy config deployments --severity CRITICAL,HIGH` | 60-90s |
| `helm-lint` | `helm lint deployments/helm/mcp-server-langgraph` | 20-30s |
| `validate-cloud-overlays` | `kubectl kustomize deployments/kubernetes/overlays/{aws,gcp,azure}` | 30-60s |
| `validate-no-placeholders` | `kubectl kustomize deployments/overlays/production-gke \| grep ...` | 10-20s |
| `check-helm-placeholders` | `grep -r "YOUR_.*_PROJECT_ID" ...` | 10-20s |

**Count:** 5 hooks
**Duration:** 2-3 minutes total

#### Category H: Validation Scripts (10-30s each)
| Hook ID | Entry Command | Duration |
|---------|---------------|----------|
| `validate-pytest-config` | `python3 scripts/validate_pytest_config.py` | 10-15s |
| `validate-pre-push-hook` | `python3 scripts/validate_pre_push_hook.py` | 5-10s |
| `validate-gke-autopilot-compliance` | `python3 scripts/validate_gke_autopilot_compliance.py` | 20-30s |
| `validate-pytest-markers` | `python3 scripts/validate_pytest_markers.py` | 10-15s |
| `validate-dependency-injection` | `python3 .githooks/pre-commit-dependency-validation` | 30-45s |
| `validate-test-fixtures` | `python3 scripts/validate_test_fixtures.py` | 10-20s |
| `detect-dead-test-code` | `python3 scripts/detect_dead_test_code.py tests/` | 10-20s |
| `validate-api-schemas` | `python3 scripts/validate_api_schemas.py` | 10-20s |
| `validate-test-time-bombs` | `python3 scripts/validate_test_time_bombs.py` | 10-20s |
| `check-e2e-completion` | `python3 scripts/check_e2e_completion.py --min-percent 25` | 5-10s |
| `check-test-sleep-budget` | `python3 scripts/check_test_sleep_budget.py --max-seconds 60 --warn-seconds 45` | 10-20s |
| `validate-test-isolation` | `python scripts/validation/validate_test_isolation.py tests/` | 20-30s |
| `validate-workflow-test-deps` | `python3 scripts/validation/validate_workflow_test_deps.py` | 10-15s |
| `check-mermaid-styling` | `python3 scripts/check_mermaid_styling.py` | 10-20s |
| `actionlint-workflow-validation` | `actionlint -no-color -shellcheck= .github/workflows/*.{yml,yaml}` | 20-30s |

**Count:** 15 hooks
**Duration:** 3-5 minutes total

#### Category I: Terraform (Optional - only if .tf files changed)
| Hook ID | Entry Command | Duration |
|---------|---------------|----------|
| `terraform_validate` | `terraform validate` | 20-40s |

**Count:** 1 hook (terraform_fmt moved to pre-commit)
**Duration:** 20-40s

**TOTAL PRE-PUSH: 44 hooks (that should move) + 29 pre-commit hooks run on ALL files**

---

## Implementation Summary

### Hooks Moving to Push Stage (stages: [push])
**Total:** 44 hooks

**Breakdown:**
- Test-running hooks: 16
- Documentation validators: 7
- Deployment validators: 5
- Validation scripts: 15
- Terraform validate: 1

### Hooks Staying in Commit Stage (default or stages: [commit])
**Total:** 29 hooks

**Breakdown:**
- Auto-fixers: 7
- Fast linters: 10
- Critical safety checks: 5
- File-specific fast validators: 7

### Hooks Running in BOTH Stages
**Special case:** Some hooks run file-specifically in commit, then ALL files in push via `pre-commit run --all-files`

---

## Expected Performance

### Current State
- **Pre-commit:** 2-5 minutes (all 90+ hooks)
- **Pre-push:** 2-3 minutes (lockfile, workflows, mypy, all pre-commit, property tests)
- **Total before push:** 4-8 minutes

### After Reorganization
- **Pre-commit:** 15-30 seconds (29 fast hooks on changed files)
- **Pre-push:** 8-12 minutes (comprehensive validation on all files + full test suite)
- **Total before push:** 8-12 minutes (consolidated)

### Performance Improvement
- **Pre-commit:** 80-90% faster (2-5 min → 15-30s)
- **Commit frequency:** Can commit 10-20x more often
- **CI parity:** 100% - pre-push matches CI exactly
- **CI surprises:** Expected 80%+ reduction

---

## Next Steps

1. ✅ Create this categorization document
2. Update `.pre-commit-config.yaml` with `stages: [push]` for 44 hooks
3. Update `.git/hooks/pre-push` with new test suite phases
4. Update `scripts/validate_pre_push_hook.py` to verify new structure
5. Create `scripts/measure_hook_performance.py` for monitoring
6. Update documentation (TESTING.md, CONTRIBUTING.md, etc.)
7. Test and validate performance improvements

---

## References

- TDD Guidelines: `~/.claude/CLAUDE.md`
- Memory Safety: `tests/MEMORY_SAFETY_GUIDELINES.md`
- Pytest xdist: `tests/PYTEST_XDIST_ENFORCEMENT.md`
- Pre-commit Config: `.pre-commit-config.yaml` (1,243 lines)
- Pre-push Hook: `.git/hooks/pre-push` (139 lines)
