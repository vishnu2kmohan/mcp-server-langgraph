# Hook Performance Profile

**Date**: 2025-11-24 12:08:04
**Total Hooks**: 81

## Summary

- **Fast hooks (<500ms)**: 67 hooks
- **Medium hooks (500ms-2s)**: 11 hooks
- **Heavy hooks (>2s)**: 3 hooks

## Recommendations

### Move 3 Heavy Hooks to Pre-push

These hooks significantly slow down commits:

| Hook ID | Stage | Mean | p90 | p95 | Category |
|---------|-------|------|-----|-----|----------|
| `bandit` | commit | 22090ms | 23631ms | 23631ms | heavy |
| `prevent-local-config-commits` | commit | 6629ms | 6745ms | 6745ms | heavy |
| `validate-test-collection` | commit | 9536ms | 9616ms | 9616ms | heavy |

### Review 11 Medium Hooks

Consider moving pytest-based hooks to pre-push:

| Hook ID | Stage | Mean | p90 | p95 | Category |
|---------|-------|------|-----|-----|----------|
| `check-subprocess-timeout` | push | 874ms | 930ms | 930ms | medium |
| `check-banned-imports` | push | 1135ms | 1326ms | 1326ms | medium |
| `check-github-workflows` | commit | 553ms | 570ms | 570ms | medium |
| `check-test-sleep-duration` | commit | 551ms | 564ms | 564ms | medium |
| `validate-workflow-file-references` | commit | 506ms | 527ms | 527ms | medium |
| `validate-pytest-fixtures` | commit | 1114ms | 1149ms | 1149ms | medium |
| `shellcheck` | commit | 892ms | 939ms | 939ms | medium |
| `validate-pytest-markers` | commit | 759ms | 772ms | 772ms | medium |
| `check-asyncmock-instantiation` | commit | 533ms | 539ms | 539ms | medium |
| `check-test-naming` | commit | 619ms | 625ms | 625ms | medium |
| `terraform_fmt` | commit | 574ms | 576ms | 576ms | medium |

## All Hooks (sorted by p90)

| Hook ID | Stage | Mean | p90 | p95 | Category |
|---------|-------|------|-----|-----|----------|
| `bandit` | commit | 22090ms | 23631ms | 23631ms | heavy |
| `validate-test-collection` | commit | 9536ms | 9616ms | 9616ms | heavy |
| `prevent-local-config-commits` | commit | 6629ms | 6745ms | 6745ms | heavy |
| `check-banned-imports` | push | 1135ms | 1326ms | 1326ms | medium |
| `validate-pytest-fixtures` | commit | 1114ms | 1149ms | 1149ms | medium |
| `shellcheck` | commit | 892ms | 939ms | 939ms | medium |
| `check-subprocess-timeout` | push | 874ms | 930ms | 930ms | medium |
| `validate-pytest-markers` | commit | 759ms | 772ms | 772ms | medium |
| `check-test-naming` | commit | 619ms | 625ms | 625ms | medium |
| `terraform_fmt` | commit | 574ms | 576ms | 576ms | medium |
| `check-github-workflows` | commit | 553ms | 570ms | 570ms | medium |
| `check-test-sleep-duration` | commit | 551ms | 564ms | 564ms | medium |
| `check-asyncmock-instantiation` | commit | 533ms | 539ms | 539ms | medium |
| `validate-workflow-file-references` | commit | 506ms | 527ms | 527ms | medium |
| `gitleaks` | commit | 431ms | 451ms | 451ms | fast |
| `check-yaml` | commit | 370ms | 421ms | 421ms | fast |
| `check-ast` | commit | 394ms | 398ms | 398ms | fast |
| `mypy` | push | 328ms | 340ms | 340ms | fast |
| `trailing-whitespace` | commit | 294ms | 320ms | 320ms | fast |
| `check-added-large-files` | commit | 286ms | 300ms | 300ms | fast |
| `check-merge-conflict` | commit | 272ms | 285ms | 285ms | fast |
| `end-of-file-fixer` | commit | 270ms | 282ms | 282ms | fast |
| `mixed-line-ending` | commit | 271ms | 280ms | 280ms | fast |
| `detect-private-key` | commit | 252ms | 256ms | 256ms | fast |
| `check-json` | commit | 234ms | 237ms | 237ms | fast |
| `check-toml` | commit | 216ms | 219ms | 219ms | fast |
| `ruff-format` | commit | 209ms | 216ms | 216ms | fast |
| `check-frontmatter-quotes` | commit | 208ms | 209ms | 209ms | fast |
| `ruff` | commit | 199ms | 201ms | 201ms | fast |
| `validate-file-naming-conventions` | commit | 195ms | 197ms | 197ms | fast |
| `validate-mdx-extensions` | commit | 192ms | 197ms | 197ms | fast |
| `validate-docker-image-contents` | commit | 189ms | 190ms | 190ms | fast |
| `validate-adr-sync` | commit | 181ms | 182ms | 182ms | fast |
| `uv-lock-check` | push | 175ms | 178ms | 178ms | fast |
| `uv-pip-check` | push | 159ms | 164ms | 164ms | fast |
| `run-pre-push-tests` | push | 152ms | 160ms | 160ms | fast |
| `run-integration-tests` | manual | 148ms | 151ms | 151ms | fast |
| `validate-github-workflows-comprehensive` | push | 135ms | 143ms | 143ms | fast |
| `regression-prevention-tests` | push | 125ms | 136ms | 136ms | fast |
| `validate-test-fixtures` | push | 130ms | 134ms | 134ms | fast |
| `detect-dead-test-code` | push | 124ms | 134ms | 134ms | fast |
| `validate-keycloak-config` | commit | 133ms | 133ms | 133ms | fast |
| `validate-deployment-secrets` | push | 129ms | 132ms | 132ms | fast |
| `validate-no-placeholders` | push | 124ms | 130ms | 130ms | fast |
| `check-helm-placeholders` | push | 121ms | 127ms | 127ms | fast |
| `audit-todo-fixme-markers` | manual | 123ms | 126ms | 126ms | fast |
| `validate-dependency-injection` | push | 123ms | 125ms | 125ms | fast |
| `check-async-mock-configuration` | manual | 121ms | 124ms | 124ms | fast |
| `validate-minimum-coverage` | manual | 120ms | 124ms | 124ms | fast |
| `trivy-scan-k8s-manifests` | push | 120ms | 123ms | 123ms | fast |
| `actionlint-workflow-validation` | push | 121ms | 123ms | 123ms | fast |
| `validate-service-accounts` | push | 120ms | 122ms | 122ms | fast |
| `check-test-sleep-budget` | manual | 120ms | 122ms | 122ms | fast |
| `validate-documentation-integrity` | manual | 120ms | 122ms | 122ms | fast |
| `validate-fast` | push | 121ms | 122ms | 122ms | fast |
| `detect-slow-unit-tests` | manual | 120ms | 122ms | 122ms | fast |
| `validate-test-suite-performance` | manual | 119ms | 122ms | 122ms | fast |
| `validate-network-policies` | push | 120ms | 122ms | 122ms | fast |
| `validate-docker-compose-health-checks` | push | 119ms | 122ms | 122ms | fast |
| `validate-adr-index` | push | 121ms | 121ms | 121ms | fast |
| `validate-kustomize-builds` | push | 120ms | 121ms | 121ms | fast |
| `validate-documentation-structure` | manual | 120ms | 121ms | 121ms | fast |
| `helm-lint` | push | 120ms | 121ms | 121ms | fast |
| `check-hardcoded-credentials` | push | 119ms | 121ms | 121ms | fast |
| `validate-gke-autopilot-compliance` | push | 120ms | 121ms | 121ms | fast |
| `validate-redis-password-required` | push | 120ms | 121ms | 121ms | fast |
| `terraform_validate` | push | 118ms | 121ms | 121ms | fast |
| `validate-pytest-config` | push | 120ms | 121ms | 121ms | fast |
| `validate-fixture-scopes` | push | 119ms | 120ms | 120ms | fast |
| `validate-test-dependencies` | push | 119ms | 120ms | 120ms | fast |
| `validate-cloud-overlays` | push | 118ms | 120ms | 120ms | fast |
| `check-mermaid-styling` | manual | 119ms | 120ms | 120ms | fast |
| `validate-test-isolation` | push | 118ms | 119ms | 119ms | fast |
| `mintlify-broken-links-check` | push | 118ms | 119ms | 119ms | fast |
| `check-e2e-completion` | manual | 119ms | 119ms | 119ms | fast |
| `check-test-memory-safety` | push | 118ms | 119ms | 119ms | fast |
| `validate-workflow-test-deps` | push | 119ms | 119ms | 119ms | fast |
| `validate-test-ids` | push | 118ms | 119ms | 119ms | fast |
| `validate-cors-security` | push | 118ms | 119ms | 119ms | fast |
| `validate-meta-test-quality` | push | 118ms | 119ms | 119ms | fast |
| `validate-fixture-organization` | push | 118ms | 118ms | 118ms | fast |
