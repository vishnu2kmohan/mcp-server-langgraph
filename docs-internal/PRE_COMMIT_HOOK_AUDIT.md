# Pre-commit Hook File Scanning Audit

**Last Updated**: 2025-12-19
**Purpose**: Document which hooks scan all files vs staged files only

## Overview

Pre-commit hooks can be configured with `pass_filenames: true` (staged files only) or `pass_filenames: false` (scan all matching files). This document categorizes all hooks and explains the rationale.

## Hook Categories

### Category 1: Validation Hooks (All Files - Intentional)

These hooks intentionally scan all files because they validate project-wide constraints.

| Hook ID | Purpose | Rationale |
|---------|---------|-----------|
| `mypy` | Type checking | Must check all source for type consistency |
| `run-pre-push-tests` | Test suite | Runs full test suite |
| `run-integration-tests` | Integration tests | Runs full integration suite |
| `validate-fast` | Quick validation | Validates entire project |
| `validate-docs` | Documentation | Validates all docs |
| `validate-pytest-config` | Pytest config | Project-wide config |
| `validate-pytest-markers` | Marker validation | All test files |
| `validate-pytest-fixtures` | Fixture validation | All fixtures |
| `validate-adr-index` | ADR index | All ADRs |
| `validate-github-workflows-comprehensive` | Workflows | All workflow files |
| `validate-workflow-file-references` | Workflow refs | All workflows |
| `validate-workflow-test-deps` | Workflow deps | All workflows |
| `validate-keycloak-config` | Keycloak | All config files |
| `validate-docker-image-contents` | Docker | Dockerfile |
| `validate-gke-autopilot-compliance` | GKE | Deployment files |
| `validate-grafana-dashboards` | Grafana | Dashboard files |
| `validate-dependency-injection` | DI patterns | All source |
| `validate-minimum-coverage` | Coverage | Test results |
| `validate-test-collection` | Test collection | All tests |
| `validate-test-isolation` | Test isolation | All tests |
| `validate-no-placeholders` | Placeholder check | All files |

### Category 2: Audit Hooks (All Files - Intentional)

These hooks audit the entire codebase for patterns.

| Hook ID | Purpose | Rationale |
|---------|---------|-----------|
| `audit-todo-fixme-markers` | TODO tracking | All files |
| `detect-dead-test-code` | Dead code | All test files |
| `check-e2e-completion` | E2E status | All E2E tests |
| `check-test-sleep-budget` | Sleep budget | All tests |
| `check-testid-consistency` | Test ID sync | All tests |
| `check-internal-links` | Link validation | All docs |
| `check-helm-placeholders` | Helm values | All helm files |

### Category 3: Build/Test Hooks (All Files - Intentional)

These hooks build or test the entire project.

| Hook ID | Purpose | Rationale |
|---------|---------|-----------|
| `frontend-build` | Frontend build | Full build required |
| `frontend-test` | Frontend tests | Full test suite |
| `frontend-lint` | Frontend lint | All frontend files |
| `frontend-typecheck` | Frontend types | All frontend files |
| `frontend-format-check` | Frontend format | All frontend files |
| `docker-build-smoke-test` | Docker build | Full build |
| `python-version-smoke-test` | Python version | Environment check |
| `trivy-helm-full-scan` | Security scan | All helm files |

### Category 4: Lock/Dependency Hooks (All Files - Intentional)

| Hook ID | Purpose | Rationale |
|---------|---------|-----------|
| `uv-lock-check` | Lockfile sync | Project-wide |
| `uv-pip-check` | Dependency conflicts | Project-wide |

### Category 5: Staged-Only Hooks (pass_filenames: true)

These hooks only check staged files.

| Hook ID | Purpose |
|---------|---------|
| `ruff` | Linting staged Python files |
| `ruff-format` | Formatting staged Python files |
| `trailing-whitespace` | Whitespace in staged files |
| `end-of-file-fixer` | EOF in staged files |
| `check-yaml` | YAML syntax in staged files |
| `check-json` | JSON syntax in staged files |
| `check-toml` | TOML syntax in staged files |
| `check-ast` | Python AST in staged files |
| `gitleaks` | Secrets in staged files |
| `check-async-mock-configuration` | AsyncMock in staged test files |
| `check-async-mock-instantiation` | AsyncMock class assignment |
| `check-test-naming-conventions` | Test naming in staged files |
| `check-test-sleep-duration` | Sleep duration in staged tests |

## Recent Changes

### 2025-12-19: Fixed `check-async-mock-configuration`

**Issue**: Hook had `pass_filenames: false`, causing it to scan ALL test files instead of staged files. This blocked commits due to pre-existing violations.

**Fix**: Changed to `pass_filenames: true` so it only checks staged files.

**Commit**: `fd02aeca`

## Guidelines for New Hooks

### Use `pass_filenames: true` when:
- The check is localized to individual files
- Pre-existing violations in unchanged files should not block commits
- The check is fast per-file

### Use `pass_filenames: false` when:
- The check requires project-wide context
- The check validates relationships between files
- The check must run on all matching files regardless of changes

## Maintenance

- Review this document quarterly
- Update when adding new hooks
- Test new hooks with both settings to understand behavior
