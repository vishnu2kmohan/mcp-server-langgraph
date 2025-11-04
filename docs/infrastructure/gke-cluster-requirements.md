# GKE Cluster Requirements for CI/CD

## Overview

The CI/CD pipeline requires GKE clusters to exist before deployment workflows can succeed. This document outlines the required clusters and how to create them.

## Required Clusters

### Staging Cluster

**Name:** `mcp-staging-cluster`
**Location:** `us-central1`
**Project:** `vishnu-sandbox-20250310`
**Type:** GKE Autopilot (recommended) or Standard

**Creation via Terraform:**
```bash
cd terraform/environments/gcp-staging
terraform init
terraform plan
terraform apply
```

**Manual Creation:**
```bash
gcloud container clusters create-auto mcp-staging-cluster \
  --region=us-central1 \
  --project=vishnu-sandbox-20250310 \
  --release-channel=regular \
  --enable-master-authorized-networks \
  --network=default \
  --subnetwork=default
```

### Production Cluster

**Name:** `mcp-prod-gke`
**Location:** `us-central1`
**Project:** `vishnu-sandbox-20250310`
**Type:** GKE Autopilot

**Creation via Terraform:**
```bash
cd terraform/environments/gcp-prod
terraform init
terraform plan
terraform apply
```

## CI/CD Workflow Dependencies

### deploy-staging-gke.yaml

This workflow requires:
- ✅ GKE cluster: `mcp-staging-cluster` in `us-central1`
- ✅ Service account: `github-actions-staging@vishnu-sandbox-20250310.iam.gserviceaccount.com`
- ✅ Artifact Registry: `mcp-staging` repository
- ✅ GitHub variable: `ENABLE_STAGING_AUTODEPLOY=true`

**Workflow Trigger:**
- Push to `main` branch (when `ENABLE_STAGING_AUTODEPLOY=true`)
- Manual dispatch

**Current Status:**
❌ Cluster not found error: The cluster `mcp-staging-cluster` does not exist in the specified location.

**Resolution:**
Create the cluster using one of the methods above, then re-run the workflow.

### deploy-production-gke.yaml

This workflow requires:
- ⚠️  GKE cluster: `mcp-prod-gke` in `us-central1`
- ✅ Service account: `github-actions-production@vishnu-sandbox-20250310.iam.gserviceaccount.com`
- ✅ Artifact Registry: `mcp-production` repository

**Workflow Trigger:**
- Manual dispatch (requires approval)
- Release tags

## Verification

After creating clusters, verify they're accessible:

```bash
# Verify staging cluster
gcloud container clusters describe mcp-staging-cluster \
  --region=us-central1 \
  --project=vishnu-sandbox-20250310

# Verify production cluster
gcloud container clusters describe mcp-prod-gke \
  --region=us-central1 \
  --project=vishnu-sandbox-20250310

# Test GitHub Actions service account access
gcloud container clusters get-credentials mcp-staging-cluster \
  --region=us-central1 \
  --project=vishnu-sandbox-20250310

kubectl cluster-info
```

## Terraform Module Reference

The GKE Autopilot module is located at:
`terraform/modules/gke-autopilot/`

**Features:**
- Autopilot mode (Google-managed nodes)
- VPC-native networking
- Workload Identity Federation support
- Master authorized networks
- Binary authorization (optional)
- Backup agent integration
- Config Connector support

**Recent Fixes:**
- ✅ Duplicate lifecycle blocks merged (commit b6ac198)
- ✅ Variable validation moved to lifecycle preconditions
- ✅ Terraform validation added to pre-commit hooks

## Troubleshooting

### Error: Cluster not found

**Symptom:**
```
Error: NOT_FOUND: projects/vishnu-sandbox-20250310/locations/us-central1/clusters/mcp-staging-cluster not found
```

**Solution:**
The cluster doesn't exist. Create it using the methods above.

### Error: Permission denied

**Symptom:**
```
Error: github-actions-staging does not have permission to access cluster
```

**Solution:**
Verify the service account has the `container.developer` role:
```bash
gcloud projects get-iam-policy vishnu-sandbox-20250310 \
  --flatten="bindings[].members" \
  --filter="bindings.members:github-actions-staging*"
```

### Error: Artifact Registry repository not found

**Solution:**
Create the Artifact Registry repositories:
```bash
# Staging
gcloud artifacts repositories create mcp-staging \
  --repository-format=docker \
  --location=us-central1 \
  --project=vishnu-sandbox-20250310

# Production
gcloud artifacts repositories create mcp-production \
  --repository-format=docker \
  --location=us-central1 \
  --project=vishnu-sandbox-20250310
```

## Auto-Deploy Configuration

The deployment workflows check repository variables to determine if auto-deploy is enabled:

```bash
# Enable staging auto-deploy
gh variable set ENABLE_STAGING_AUTODEPLOY --body "true"

# Enable dev auto-deploy
gh variable set ENABLE_DEV_AUTODEPLOY --body "true"

# Verify
gh variable list
```

## Related Documentation

- [GKE Autopilot Module](../../terraform/modules/gke-autopilot/README.md)
- [Deployment Workflows](../ci-cd/deployment-workflows.md)
- [GitHub Actions WIF Setup](../../terraform/modules/github-actions-wif/README.md)
- [CI/CD Failure Analysis](../../workflow-analysis.md)

## Last Updated

2025-11-04 (Commit: b6ac198)

**Status:**
- Terraform module: ✅ Fixed and validated
- Service accounts: ✅ Created and configured
- Auto-deploy variables: ✅ Set
- GKE clusters: ❌ Need to be created
