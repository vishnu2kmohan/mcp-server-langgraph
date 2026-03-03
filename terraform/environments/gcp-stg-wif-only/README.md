# GCP STG WIF-Only Deployment

This is a temporary Terraform configuration to deploy **only** the GitHub Actions Workload Identity Federation module.

## Why This Exists

The full stg environment (`gcp-stg/`) has pre-existing Terraform errors in other modules (gke-autopilot, memorystore) that are unrelated to the WIF deployment. This minimal configuration allows us to deploy WIF independently.

## Usage

```bash
cd terraform/environments/gcp-stg-wif-only

# Initialize
terraform init

# Plan
terraform plan

# Apply
terraform apply

# Get GitHub secrets
terraform output github_secrets
```

## After Deployment

Once WIF is deployed and GitHub secrets are configured:
1. Fix the pre-existing Terraform errors in other modules
2. Migrate this WIF configuration into the full stg environment
3. Remove this directory

## What Gets Created

- Workload Identity Pool: `github-actions-pool`
- Workload Identity Provider: `github-actions-provider`
- Service Accounts:
  - `github-actions-stg@PROJECT.iam.gserviceaccount.com`
  - `github-actions-terraform@PROJECT.iam.gserviceaccount.com`
  - `github-actions-production@PROJECT.iam.gserviceaccount.com`
- IAM Bindings for each service account
