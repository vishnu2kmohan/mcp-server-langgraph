# GitHub Workflows Required Secrets and Variables

This document lists all secrets and repository variables required for GitHub Actions workflows to function correctly.

## Table of Contents

- [Required Secrets](#required-secrets)
- [Required Repository Variables](#required-repository-variables)
- [Optional Secrets](#optional-secrets)
- [Setup Instructions](#setup-instructions)
- [Security Best Practices](#security-best-practices)
- [Troubleshooting](#troubleshooting)

---

## Required Secrets

### GCP Authentication (Required for Deployments)

#### `GCP_WIF_PROVIDER`
- **Purpose**: Workload Identity Federation provider for keyless GCP authentication
- **Format**: `projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/POOL/providers/PROVIDER`
- **Used By**:
  - `deploy-gke-staging.yaml`
  - `deploy-gke-production.yaml`
  - `release.yaml`
- **Setup**:
  ```bash
  # Get your project number
  gcloud projects describe YOUR_PROJECT_ID --format="value(projectNumber)"

  # Create Workload Identity Pool
  gcloud iam workload-identity-pools create github-actions \
    --location=global \
    --display-name="GitHub Actions Pool"

  # Create provider
  gcloud iam workload-identity-pools providers create-oidc github \
    --location=global \
    --workload-identity-pool=github-actions \
    --display-name="GitHub Provider" \
    --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository" \
    --issuer-uri="https://token.actions.githubusercontent.com"
  ```

#### `GCP_STAGING_SA_EMAIL`
- **Purpose**: Service account email for staging deployments
- **Format**: `staging-deploy@PROJECT_ID.iam.gserviceaccount.com`
- **Used By**: `deploy-gke-staging.yaml`
- **Permissions Required**:
  - `roles/container.developer` (GKE deployments)
  - `roles/artifactregistry.writer` (Docker image push)
  - `roles/logging.logWriter` (Cloud Logging)
  - `roles/monitoring.metricWriter` (Cloud Monitoring)
- **Setup**:
  ```bash
  # Create service account
  gcloud iam service-accounts create staging-deploy \
    --display-name="Staging Deployment Service Account"

  # Grant permissions
  gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
    --member="serviceAccount:staging-deploy@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/container.developer"

  # Bind to Workload Identity
  gcloud iam service-accounts add-iam-policy-binding \
    staging-deploy@YOUR_PROJECT_ID.iam.gserviceaccount.com \
    --role="roles/iam.workloadIdentityUser" \
    --member="principalSet://iam.googleapis.com/projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/github-actions/attribute.repository/YOUR_REPO"
  ```

#### `GCP_PRODUCTION_SA_EMAIL`
- **Purpose**: Service account email for production deployments
- **Format**: `prod-deploy@PROJECT_ID.iam.gserviceaccount.com`
- **Used By**: `deploy-gke-production.yaml`, `release.yaml`
- **Permissions Required**: Same as staging SA
- **Setup**: Similar to staging SA

### PyPI Publishing (Required for Releases)

#### `PYPI_TOKEN`
- **Purpose**: API token for publishing packages to PyPI
- **Format**: `pypi-AgEIcHlwaS5vcmc...` (starts with `pypi-`)
- **Used By**: `release.yaml`
- **Scopes Required**: Upload packages
- **Setup**:
  1. Go to https://pypi.org/manage/account/token/
  2. Click "Add API token"
  3. Name: "GitHub Actions Release"
  4. Scope: "Entire account" or specific project
  5. Copy token and add to GitHub secrets

---

## Required Repository Variables

Configure in: Settings → Secrets and variables → Actions → Variables

### `GCP_PROJECT_ID`
- **Purpose**: GCP project ID for deployments
- **Example**: `vishnu-sandbox-20250310`
- **Used By**: All GCP-related workflows
- **Note**: Not a secret, safe to expose in logs

### `GCP_REGION`
- **Purpose**: GCP region for resources
- **Default**: `us-central1`
- **Used By**: Deployment workflows

### `ENABLE_STAGING_AUTODEPLOY`
- **Purpose**: Enable/disable automatic staging deployments on main push
- **Values**: `true` or `false`
- **Default**: `false`
- **Used By**: `deploy-gke-staging.yaml`

### `ENABLE_DEV_AUTODEPLOY`
- **Purpose**: Enable/disable automatic dev deployments
- **Values**: `true` or `false`
- **Default**: `false`
- **Used By**: `deploy-gke-dev.yaml` (if exists)

---

## Optional Secrets

### Observability and Alerting

#### `SLACK_WEBHOOK_URL`
- **Purpose**: Slack webhook for deployment and failure notifications
- **Format**: `https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXX`
- **Used By**:
  - `observability-alerts.yaml`
  - `dora-metrics.yaml`
- **Setup**:
  1. Create Slack app at https://api.slack.com/apps
  2. Enable "Incoming Webhooks"
  3. Add webhook to workspace
  4. Copy webhook URL

#### `PAGERDUTY_INTEGRATION_KEY`
- **Purpose**: PagerDuty integration key for critical alerts
- **Format**: 32-character alphanumeric key
- **Used By**: `observability-alerts.yaml`
- **Setup**:
  1. Go to Services → your service → Integrations
  2. Add "Events API V2" integration
  3. Copy integration key

#### `DATADOG_API_KEY`
- **Purpose**: Datadog API key for metrics and traces
- **Format**: 32-character alphanumeric key
- **Used By**: `observability-alerts.yaml`
- **Setup**:
  1. Go to Organization Settings → API Keys
  2. Create new API key: "GitHub Actions"
  3. Copy key

### Code Coverage

#### `CODECOV_TOKEN`
- **Purpose**: Codecov upload token for private repositories
- **Format**: UUID format
- **Used By**: `ci.yaml`
- **Note**: Not required for public repositories
- **Setup**:
  1. Go to https://codecov.io
  2. Add repository
  3. Copy upload token from repository settings

---

## Setup Instructions

### Quick Setup Checklist

For a new repository or organization:

- [ ] **GCP Authentication**
  - [ ] Create Workload Identity Pool and provider
  - [ ] Create staging and production service accounts
  - [ ] Bind service accounts to Workload Identity
  - [ ] Add `GCP_WIF_PROVIDER`, `GCP_STAGING_SA_EMAIL`, `GCP_PRODUCTION_SA_EMAIL` secrets
  - [ ] Add `GCP_PROJECT_ID`, `GCP_REGION` variables

- [ ] **PyPI Publishing** (if releasing packages)
  - [ ] Create PyPI API token
  - [ ] Add `PYPI_TOKEN` secret

- [ ] **Observability** (optional)
  - [ ] Create Slack webhook
  - [ ] Add `SLACK_WEBHOOK_URL` secret
  - [ ] Set up PagerDuty integration
  - [ ] Add `PAGERDUTY_INTEGRATION_KEY` secret
  - [ ] Set up Datadog
  - [ ] Add `DATADOG_API_KEY` secret

- [ ] **Deployment Automation** (optional)
  - [ ] Set `ENABLE_STAGING_AUTODEPLOY` variable to `true`
  - [ ] Set `ENABLE_DEV_AUTODEPLOY` variable to `true`

### Adding Secrets to GitHub

1. Navigate to your repository on GitHub
2. Go to **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Enter secret name (exactly as shown above)
5. Paste secret value
6. Click **Add secret**

**For Organization-level Secrets:**
1. Go to Organization **Settings** → **Secrets and variables** → **Actions**
2. Click **New organization secret**
3. Select repository access (All repositories / Selected repositories)
4. Add secret

---

## Security Best Practices

### Secret Rotation

Rotate secrets regularly:
- **GCP Service Account Keys**: Not applicable (using Workload Identity)
- **PyPI Tokens**: Every 6 months or after personnel changes
- **Webhook URLs**: After security incidents only
- **API Keys**: Every 3-6 months

### Least Privilege

Service accounts should have minimal permissions:
```bash
# Example: Staging SA only needs GKE and Artifact Registry access
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:staging-deploy@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/container.developer"

# Do NOT grant owner or editor roles
```

### Secret Scope

Prefer repository-specific secrets over organization-wide secrets:
- Easier to track usage
- Reduced blast radius if compromised
- Better access control

### Audit Logging

Monitor secret usage:
```bash
# Check GCP service account activity
gcloud logging read "protoPayload.authenticationInfo.principalEmail:staging-deploy@" \
  --limit=50 \
  --format=json
```

### Emergency Response

If a secret is compromised:

1. **Immediately rotate/revoke** the secret
2. **Review audit logs** for unauthorized usage
3. **Update in GitHub** with new value
4. **Document incident** for post-mortem
5. **Check for data exposure** from unauthorized access

---

## Troubleshooting

### Common Issues

#### "Error: failed to load secret"

**Cause**: Secret not configured or incorrect name

**Solution**:
1. Verify secret name matches exactly (case-sensitive)
2. Check secret is added at repository or organization level
3. Ensure workflow has correct permissions

#### "Error: Workload Identity authentication failed"

**Cause**: Misconfigured Workload Identity bindings

**Solution**:
```bash
# Verify binding
gcloud iam service-accounts get-iam-policy \
  staging-deploy@YOUR_PROJECT_ID.iam.gserviceaccount.com \
  --format=json

# Should see principalSet with your repository
# If not, add binding again (see setup instructions above)
```

#### "Error: Invalid PyPI token"

**Cause**: Token expired, revoked, or incorrect scope

**Solution**:
1. Generate new token at https://pypi.org/manage/account/token/
2. Ensure scope is "Entire account" or includes your package
3. Update `PYPI_TOKEN` secret in GitHub

#### Workflow skipped due to missing secret

**Cause**: Workflow checks `if: secrets.X != ''` and secret is not set

**Solution**: This is expected behavior for optional secrets. Either:
1. Add the secret to enable the feature
2. Leave as-is if feature not needed

---

## References

- [GitHub Actions Encrypted Secrets](https://docs.github.com/en/actions/security-guides/encrypted-secrets)
- [GCP Workload Identity Federation](https://cloud.google.com/iam/docs/workload-identity-federation)
- [PyPI API Tokens](https://pypi.org/help/#apitoken)
- [Slack Incoming Webhooks](https://api.slack.com/messaging/webhooks)

---

**Last Updated**: 2025-11-07
**Maintained By**: DevOps Team
**Questions**: Open an issue or contact the maintainers
