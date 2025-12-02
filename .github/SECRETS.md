# GitHub Secrets and Variables Configuration

**Last Updated**: 2025-11-07
**Maintained By**: Engineering Team

## Overview

This document describes all secrets and repository variables required for GitHub Actions workflows in this repository. Each secret is categorized by workflow and includes setup instructions.

---

## Repository Structure

**Repository**: `vishnu2kmohan/mcp-server-langgraph`

Secrets are configured at: `Settings → Secrets and variables → Actions`

---

## Required Secrets

### GCP Workload Identity Federation

**Purpose**: Keyless authentication to Google Cloud Platform for deployments and compliance scanning.

#### Production Deployment

| Secret Name | Description | Setup Instructions |
|-------------|-------------|-------------------|
| `GCP_WIF_PROVIDER` | Workload Identity Pool Provider | `projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/github-actions-pool/providers/github-provider` |
| `GCP_PRODUCTION_SA_EMAIL` | Production service account | `production-deployer@PROJECT_ID.iam.gserviceaccount.com` |

**Used By**:
- `.github/workflows/deploy-production-gke.yaml` (4 jobs)
- All jobs have repository check: `if: github.repository == 'vishnu2kmohan/mcp-server-langgraph'`

**Setup Steps**:
```bash
# 1. Create Workload Identity Pool
gcloud iam workload-identity-pools create github-actions-pool \
  --location=global \
  --display-name="GitHub Actions Pool"

# 2. Create Provider
gcloud iam workload-identity-pools providers create-oidc github-provider \
  --location=global \
  --workload-identity-pool=github-actions-pool \
  --issuer-uri=https://token.actions.githubusercontent.com \
  --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository,attribute.actor=assertion.actor" \
  --attribute-condition="assertion.repository=='vishnu2kmohan/mcp-server-langgraph'"

# 3. Create Service Account
gcloud iam service-accounts create production-deployer \
  --display-name="Production Deployment Service Account"

# 4. Grant Permissions
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="serviceAccount:production-deployer@PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/container.developer"

# 5. Bind Workload Identity
gcloud iam service-accounts add-iam-policy-binding \
  production-deployer@PROJECT_ID.iam.gserviceaccount.com \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/github-actions-pool/attribute.repository/vishnu2kmohan/mcp-server-langgraph"
```

#### Staging Deployment

| Secret Name | Description | Setup Instructions |
|-------------|-------------|-------------------|
| `GCP_WIF_PROVIDER` | Workload Identity Pool Provider (same as production) | See above |
| `GCP_STAGING_SA_EMAIL` | Staging service account | `staging-deployer@PROJECT_ID.iam.gserviceaccount.com` |

**Used By**:
- `.github/workflows/deploy-staging-gke.yaml` (4 jobs)
- All jobs have repository check: `if: github.repository == 'vishnu2kmohan/mcp-server-langgraph'`

#### Compliance & Drift Detection

| Secret Name | Description | Setup Instructions |
|-------------|-------------|-------------------|
| `GCP_WIF_PROVIDER` | Workload Identity Pool Provider (same as production) | See above |
| `GCP_COMPLIANCE_SA_EMAIL` | Compliance scanner service account | `compliance-scanner@PROJECT_ID.iam.gserviceaccount.com` |
| `GCP_TERRAFORM_SA_EMAIL` | Terraform drift detection service account | `terraform-drift@PROJECT_ID.iam.gserviceaccount.com` |

**Used By**:
- `.github/workflows/gcp-compliance-scan.yaml` (1 job)
- `.github/workflows/gcp-drift-detection.yaml` (3 jobs)
- All jobs have repository check: `if: github.repository == 'vishnu2kmohan/mcp-server-langgraph'`

#### Vertex AI Integration Tests (CI)

| Secret Name | Description | Setup Instructions |
|-------------|-------------|-------------------|
| `GCP_WIF_PROVIDER` | Workload Identity Pool Provider (same as production) | See above |
| `GCP_VERTEX_AI_SA_EMAIL` | Vertex AI CI service account | `github-actions-vertex-ai@PROJECT_ID.iam.gserviceaccount.com` |

**Used By**:
- `.github/workflows/integration-tests.yaml` (vertex-ai-tests job)
- Job has repository check: `if: github.repository == 'vishnu2kmohan/mcp-server-langgraph'`

**Required IAM Roles**:
- `roles/aiplatform.user` - Access Vertex AI APIs (Claude + Gemini)
- `roles/serviceusage.serviceUsageConsumer` - Consume GCP services

**Setup Steps**:
```bash
# Service account is created by Terraform (terraform/environments/gcp-staging-wif-only)
# After terraform apply, add the secret:
gh secret set GCP_VERTEX_AI_SA_EMAIL --body "github-actions-vertex-ai@PROJECT_ID.iam.gserviceaccount.com"
```

### Package Publishing

#### PyPI

| Secret Name | Description | Setup Instructions |
|-------------|-------------|-------------------|
| `PYPI_TOKEN` | PyPI API token for package publication | Create at https://pypi.org/manage/account/token/ |

**Used By**: `.github/workflows/release.yaml`

**Scopes Required**: Upload packages to `mcp-server-langgraph`

#### MCP Registry

| Secret Name | Description | Setup Instructions |
|-------------|-------------|-------------------|
| `MCP_REGISTRY_TOKEN` | MCP registry authentication token | Obtained from MCP registry admin |

**Used By**: `.github/workflows/release.yaml`

### Notifications

#### Slack

| Secret Name | Description | Setup Instructions |
|-------------|-------------|-------------------|
| `SLACK_WEBHOOK` | General release notifications | Create at Slack workspace settings |
| `SLACK_SECURITY_WEBHOOK` | Security alert notifications | Create separate webhook for security channel |

**Used By**:
- `.github/workflows/release.yaml` (deployment notifications)
- `.github/workflows/security-scan.yaml` (security alerts)

### Code Coverage

#### Codecov

| Secret Name | Description | Setup Instructions |
|-------------|-------------|-------------------|
| `CODECOV_TOKEN` | Codecov upload token | Obtained from https://codecov.io/ after repository setup |

**Used By**: `.github/workflows/ci.yaml`

**Note**: Optional for public repositories, required for private repositories.

---

## Repository Variables

**Purpose**: Non-sensitive configuration that may vary between environments.

### GCP Configuration

| Variable Name | Description | Default Value | Used By |
|---------------|-------------|---------------|---------|
| `GCP_PROJECT_ID` | Google Cloud project ID | `vishnu-sandbox-20250310` | GCP workflows |
| `GCP_REGION` | Primary GCP region | `us-central1` | GCP workflows |
| `ENABLE_STAGING_AUTODEPLOY` | Enable automatic staging deployments | `true` | `deploy-staging-gke.yaml` |

**Setup**:
```bash
# Set via GitHub UI: Settings → Secrets and variables → Actions → Variables tab
# Or via GitHub CLI:
gh variable set GCP_PROJECT_ID --body "your-project-id"
gh variable set GCP_REGION --body "us-central1"
gh variable set ENABLE_STAGING_AUTODEPLOY --body "true"
```

---

## Fork Behavior

### How Secrets Work on Forks

**IMPORTANT**: GitHub **does not** provide repository secrets to forked repositories for security reasons.

Our workflows handle this gracefully:

#### ✅ What Works on Forks

- Unit tests (`.github/workflows/ci.yaml` - test jobs)
- Code quality checks (`.github/workflows/quality-tests.yaml`)
- Smoke tests (`.github/workflows/smoke-tests.yml`)
- Shell tests (`.github/workflows/shell-tests.yml`)

#### ⏭️ What Skips on Forks (Intentional)

All jobs with this conditional will skip on forks:

```yaml
if: github.repository == 'vishnu2kmohan/mcp-server-langgraph'
```

**Affected Workflows**:
- GCP Deployments (4 workflows, 12 jobs)
  - `deploy-staging-gke.yaml` - Gracefully skips
  - `deploy-production-gke.yaml` - Gracefully skips
  - `gcp-compliance-scan.yaml` - Gracefully skips
  - `gcp-drift-detection.yaml` - Gracefully skips

**Why This is Good**:
- ✅ No confusing authentication errors
- ✅ Contributors can run tests without GCP access
- ✅ Clear intent in workflow code
- ✅ Forks still get full test coverage

### Contributing from a Fork

**For Contributors**:

1. Fork the repository
2. Make your changes
3. Run tests locally:
   ```bash
   uv run --frozen pytest tests/
   ```
4. Push to your fork
5. Create pull request

**What Happens in CI**:
- ✅ All tests run normally
- ✅ Code quality checks run
- ⏭️ GCP deployments skip (expected)
- ✅ PR gets full validation

**For Maintainers Reviewing PRs**:
- All test results available in PR
- GCP deployment tests run when merged to main
- No action required for fork CI limitations

---

## Security Best Practices

### Secret Rotation

**Recommended Schedule**:
- GCP Workload Identity: No rotation needed (federated identity)
- PyPI Token: Rotate every 6 months
- Slack Webhooks: Rotate if compromised
- Codecov Token: Rotate yearly

### Least Privilege

All service accounts follow least privilege:

```yaml
# Production Deployer
roles/container.developer     # Deploy to GKE
roles/artifactregistry.writer # Push images

# Compliance Scanner (read-only)
roles/container.viewer        # Read GKE config
roles/iam.securityReviewer   # Scan IAM policies

# Terraform Drift
roles/compute.viewer          # Read infrastructure state
```

### Audit Logs

Monitor secret usage:
```bash
# GCP audit logs for service account usage
gcloud logging read "protoPayload.authenticationInfo.principalEmail:github-actions" \
  --limit 50 \
  --format json

# GitHub Actions workflow runs
gh run list --limit 50
```

---

## Troubleshooting

### "Error: Secrets not found"

**Symptom**: Workflow fails with authentication errors

**Cause**: Secret not configured or wrong secret name

**Fix**:
1. Check secret exists: `Settings → Secrets and variables → Actions`
2. Verify exact name matches workflow (case-sensitive)
3. For forks: Expected behavior (see Fork Behavior section above)

### "Error: Workload Identity Pool not found"

**Symptom**: GCP authentication fails with WIF pool error

**Cause**: WIF provider not set up correctly or wrong format

**Fix**:
```bash
# Verify provider exists
gcloud iam workload-identity-pools providers describe github-provider \
  --location=global \
  --workload-identity-pool=github-actions-pool

# Check secret format (should be full path):
# projects/123456789/locations/global/workloadIdentityPools/github-actions-pool/providers/github-provider
```

### "Permission Denied" on GCP Operations

**Symptom**: Workflow runs but GCP operations fail

**Cause**: Service account lacks required IAM roles

**Fix**:
```bash
# Grant required role
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="serviceAccount:SERVICE_ACCOUNT_EMAIL" \
  --role="roles/REQUIRED_ROLE"

# Verify roles
gcloud projects get-iam-policy PROJECT_ID \
  --flatten="bindings[].members" \
  --filter="bindings.members:SERVICE_ACCOUNT_EMAIL"
```

### Workflows Skip on Main Branch

**Symptom**: GCP workflows skip even on main branch

**Cause**: Repository check failing

**Fix**:
```yaml
# Verify repository name in workflow matches actual repository:
if: github.repository == 'vishnu2kmohan/mcp-server-langgraph'
#                         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
#                         Must match exactly (case-sensitive)
```

---

## Validation

To validate your secrets configuration:

```bash
# Run workflow validation tests
uv run --frozen pytest tests/test_workflow_validation.py -v

# Test includes:
# - GCP auth steps have repository checks
# - Docker build actions use consistent versions
# - Action versions are valid
# - Coverage artifact handling
```

Expected output:
```
tests/test_workflow_validation.py::TestWorkflowValidation::test_gcp_auth_steps_have_secret_validation PASSED
tests/test_workflow_validation.py::TestWorkflowValidation::test_docker_build_actions_are_consistent PASSED
tests/test_workflow_validation.py::TestWorkflowValidation::test_action_versions_are_valid PASSED
```

---

## Related Documentation

- **Workflow Validation**: `docs-internal/CODEX_GITHUB_ACTIONS_WORKFLOW_VALIDATION.md`
- **Deployment Guide**: `docs-internal/DEPLOYMENT.md`
- **GCP Setup**: [Google Cloud Workload Identity Federation](https://cloud.google.com/iam/docs/workload-identity-federation)
- **GitHub Actions Secrets**: [Encrypted secrets](https://docs.github.com/en/actions/security-guides/encrypted-secrets)

---

## Support

For questions or issues with secrets configuration:

1. Check this document first
2. Review workflow validation tests
3. Check GCP audit logs for authentication issues
4. Contact the engineering team

**Last Review**: 2025-12-01
**Next Review**: 2026-01-01 (monthly)
