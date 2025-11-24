================================================================================
GitHub Actions Workflow Duplication Audit
================================================================================

📊 Summary Statistics
  Total workflows: 34
  Total jobs: 146
  Unique actions used: 40

🔄 Most Frequently Used Actions (Top 10)
  115× actions/checkout
   29× ./.github/actions/setup-python-deps
   28× actions/upload-artifact
   27× actions/setup-python
   19× actions/github-script
   18× astral-sh/setup-uv
   13× google-github-actions/auth
   10× hashicorp/setup-terraform
   10× aquasecurity/trivy-action
    7× actions/download-artifact

🎯 Actions Used in 5+ Workflows (Composite Action Candidates)
  115× actions/checkout
   29× ./.github/actions/setup-python-deps
   28× actions/upload-artifact
   27× actions/setup-python
   19× actions/github-script
   18× astral-sh/setup-uv
   13× google-github-actions/auth
   10× hashicorp/setup-terraform
   10× aquasecurity/trivy-action
    7× actions/download-artifact
    7× docker/setup-buildx-action
    7× github/codeql-action/upload-sarif
    6× docker/login-action
    6× docker/build-push-action
    5× azure/setup-kubectl
    5× actions/cache

🔍 Duplicate Step Sequences (3+ steps)

  Sequence #1 (6 steps, found in 2 locations):
    • uses:actions/checkout
    • uses:docker/setup-qemu-action
    • uses:docker/setup-buildx-action
    • uses:docker/login-action
    • run:PLATFORM_NAME=$(echo "${{ matrix.platform }}" | se
    ... and 1 more steps
  Found in:
    - ci.yaml → docker-multiplatform
    - release.yaml → build-and-push

  Sequence #2 (5 steps, found in 2 locations):
    • uses:actions/checkout
    • uses:docker/setup-qemu-action
    • uses:docker/setup-buildx-action
    • uses:docker/login-action
    • run:PLATFORM_NAME=$(echo "${{ matrix.platform }}" | se
  Found in:
    - ci.yaml → docker-multiplatform
    - release.yaml → build-and-push

  Sequence #3 (5 steps, found in 2 locations):
    • uses:docker/setup-qemu-action
    • uses:docker/setup-buildx-action
    • uses:docker/login-action
    • run:PLATFORM_NAME=$(echo "${{ matrix.platform }}" | se
    • uses:docker/build-push-action
  Found in:
    - ci.yaml → docker-multiplatform
    - release.yaml → build-and-push

  Sequence #4 (5 steps, found in 2 locations):
    • uses:actions/checkout
    • uses:actions/setup-python
    • uses:actions/cache
    • uses:actions/cache
    • uses:astral-sh/setup-uv
  Found in:
    - e2e-tests.yaml → e2e-tests
    - integration-tests.yaml → integration-tests

  Sequence #5 (4 steps, found in 2 locations):
    • uses:actions/checkout
    • uses:actions/setup-python
    • uses:astral-sh/setup-uv
    • run:# Install with dev extras (includes pytest, pyyaml
  Found in:
    - security-validation.yml → terraform-security
    - security-validation.yml → kubernetes-security

  Sequence #6 (4 steps, found in 2 locations):
    • uses:actions/checkout
    • uses:docker/setup-qemu-action
    • uses:docker/setup-buildx-action
    • uses:docker/login-action
  Found in:
    - ci.yaml → docker-multiplatform
    - release.yaml → build-and-push

  Sequence #7 (4 steps, found in 2 locations):
    • uses:docker/setup-qemu-action
    • uses:docker/setup-buildx-action
    • uses:docker/login-action
    • run:PLATFORM_NAME=$(echo "${{ matrix.platform }}" | se
  Found in:
    - ci.yaml → docker-multiplatform
    - release.yaml → build-and-push

  Sequence #8 (4 steps, found in 2 locations):
    • uses:docker/setup-buildx-action
    • uses:docker/login-action
    • run:PLATFORM_NAME=$(echo "${{ matrix.platform }}" | se
    • uses:docker/build-push-action
  Found in:
    - ci.yaml → docker-multiplatform
    - release.yaml → build-and-push

  Sequence #9 (4 steps, found in 2 locations):
    • uses:google-github-actions/auth
    • run:echo '${{ steps.auth.outputs.access_token }}' | do
    • uses:docker/setup-buildx-action
    • uses:docker/build-push-action
  Found in:
    - deploy-production-gke.yaml → build-and-push
    - deploy-staging-gke.yaml → build-and-push

  Sequence #10 (4 steps, found in 3 locations):
    • uses:actions/checkout
    • uses:google-github-actions/auth
    • uses:google-github-actions/setup-gcloud
    • run:gcloud container clusters get-credentials ${{ env.
  Found in:
    - deploy-production-gke.yaml → deploy-production
    - deploy-production-gke.yaml → post-deployment-validation
    - deploy-production-gke.yaml → rollback-on-failure

  Sequence #11 (4 steps, found in 2 locations):
    • uses:actions/checkout
    • uses:actions/setup-python
    • uses:actions/cache
    • uses:actions/cache
  Found in:
    - e2e-tests.yaml → e2e-tests
    - integration-tests.yaml → integration-tests

  Sequence #12 (4 steps, found in 2 locations):
    • uses:actions/setup-python
    • uses:actions/cache
    • uses:actions/cache
    • uses:astral-sh/setup-uv
  Found in:
    - e2e-tests.yaml → e2e-tests
    - integration-tests.yaml → integration-tests

  Sequence #13 (4 steps, found in 2 locations):
    • uses:actions/checkout
    • uses:hashicorp/setup-terraform
    • uses:google-github-actions/auth
    • run:cd terraform/environments/gcp-prod
  Found in:
    - gcp-drift-detection.yaml → detect-drift-prod
    - gcp-drift-detection.yaml → auto-remediate

  Sequence #14 (4 steps, found in 3 locations):
    • uses:actions/checkout
    • uses:actions/setup-python
    • uses:astral-sh/setup-uv
    • run:uv sync --frozen
  Found in:
    - local-preflight-check.yaml → validate-file-references
    - local-preflight-check.yaml → code-quality
    - local-preflight-check.yaml → unit-tests-fast

  Sequence #15 (3 steps, found in 2 locations):
    • uses:actions/checkout
    • run:cd /tmp
    • uses:./.github/actions/setup-python-deps
  Found in:
    - deployment-validation.yml → validate-network-policies
    - deployment-validation.yml → validate-service-accounts

  Sequence #16 (3 steps, found in 15 locations):
    • uses:actions/checkout
    • uses:actions/setup-python
    • uses:astral-sh/setup-uv
  Found in:
    - security-validation.yml → terraform-security
    - security-validation.yml → kubernetes-security
    - ci.yaml → test
    - ci.yaml → coverage-merge
    - ci.yaml → pre-commit
    - ci.yaml → push-stage-validators
    - docs-validation.yaml → specialized-validation
    - docs-validation.yaml → documentation-tests
    - dora-metrics.yaml → calculate-metrics
    - local-preflight-check.yaml → validate-file-references
    - local-preflight-check.yaml → code-quality
    - local-preflight-check.yaml → unit-tests-fast
    - performance-regression.yaml → run-benchmarks
    - release.yaml → publish-pypi
    - weekly-reports.yaml → regenerate-reports

  Sequence #17 (3 steps, found in 2 locations):
    • uses:actions/setup-python
    • uses:astral-sh/setup-uv
    • run:# Install with dev extras (includes pytest, pyyaml
  Found in:
    - security-validation.yml → terraform-security
    - security-validation.yml → kubernetes-security

  Sequence #18 (3 steps, found in 2 locations):
    • uses:actions/checkout
    • uses:./.github/actions/setup-python-deps
    • run:source .venv/bin/activate
  Found in:
    - smoke-tests.yml → smoke-tests
    - smoke-tests.yml → startup-validation

  Sequence #19 (3 steps, found in 2 locations):
    • uses:actions/checkout
    • uses:docker/setup-qemu-action
    • uses:docker/setup-buildx-action
  Found in:
    - ci.yaml → docker-multiplatform
    - release.yaml → build-and-push

  Sequence #20 (3 steps, found in 2 locations):
    • uses:docker/setup-qemu-action
    • uses:docker/setup-buildx-action
    • uses:docker/login-action
  Found in:
    - ci.yaml → docker-multiplatform
    - release.yaml → build-and-push

  ... and 17 more duplicate sequences

================================================================================
💡 Recommendations
================================================================================

1. **Create Composite Actions** for frequently used action combinations:
   - actions/checkout (used 115 times)
   - ./.github/actions/setup-python-deps (used 29 times)
   - actions/upload-artifact (used 28 times)
   - actions/setup-python (used 27 times)
   - actions/github-script (used 19 times)

2. **Consolidate Common Setup Steps**:
   - UV setup (appears in multiple workflows)
   - Python environment setup
   - Docker setup
   - Checkout and caching patterns

3. **Consider Workflow Templates** for similar workflows:
   - Test workflows (unit, integration, E2E)
   - Deployment workflows (dev, staging, production)
   - Validation workflows (docs, configs, security)

4. **Estimated Savings**:
   - 37 duplicate sequences found
   - ~195 duplicate step definitions
   - Potential maintenance reduction: 16 composite actions

================================================================================
Generated by: scripts/dev/audit_workflow_duplication.py
================================================================================
