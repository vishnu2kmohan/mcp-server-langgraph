# GitHub Actions Workload Identity Federation Module

This Terraform module configures **Workload Identity Federation (WIF)** for keyless authentication from GitHub Actions to Google Cloud Platform.

## Features

- ✅ **Keyless Authentication**: No service account keys needed
- ✅ **Declarative Configuration**: Fully managed by Terraform
- ✅ **Repository-Level Access Control**: Restrict access to specific GitHub repositories
- ✅ **Multiple Service Accounts**: Support for different workflows (staging, production, terraform)
- ✅ **Comprehensive IAM**: Project-level, Artifact Registry, Storage, Secret Manager access
- ✅ **Idempotent**: Safe to run multiple times

## Architecture

```
GitHub Actions Workflow
         │
         ├─ OIDC Token (from GitHub)
         │
         ▼
Workload Identity Provider (Google Cloud)
         │
         ├─ Validates token
         ├─ Maps GitHub attributes → Google Cloud attributes
         │
         ▼
Service Account (impersonation)
         │
         ├─ Project-level IAM roles
         ├─ Artifact Registry access
         ├─ Storage bucket access
         ├─ Secret Manager access
         │
         ▼
GCP Resources (GKE, Cloud SQL, etc.)
```

## Usage

### Basic Example

```hcl
module "github_actions_wif" {
  source = "../../modules/github-actions-wif"

  project_id              = "my-gcp-project"
  project_number          = "123456789"
  github_repository_owner = "myorg"

  service_accounts = {
    staging = {
      account_id   = "github-actions-staging"
      display_name = "GitHub Actions - Staging"
      description  = "Service account for GitHub Actions staging deployments"

      # Restrict to specific repository
      repository_filter = "mcp-server-langgraph"

      # Project-level roles
      project_roles = [
        "roles/container.developer",
        "roles/logging.logWriter",
        "roles/monitoring.metricWriter",
      ]

      # Artifact Registry access
      artifact_registry_repositories = [
        {
          location   = "us-central1"
          repository = "mcp-staging"
          role       = "roles/artifactregistry.writer"
        }
      ]
    }
  }
}
```

### Complete Example with Multiple Service Accounts

```hcl
module "github_actions_wif" {
  source = "../../modules/github-actions-wif"

  project_id              = var.project_id
  project_number          = var.project_number
  github_repository_owner = "myorg"

  pool_id              = "github-actions-pool"
  pool_display_name    = "GitHub Actions Pool"
  provider_id          = "github-actions-provider"
  provider_display_name = "GitHub Actions OIDC Provider"

  service_accounts = {
    # Staging deployment service account
    staging = {
      account_id        = "github-actions-staging"
      display_name      = "GitHub Actions - Staging Deployment"
      description       = "Deploys to GKE staging cluster"
      repository_filter = "mcp-server-langgraph"

      project_roles = [
        "roles/container.developer",
        "roles/artifactregistry.writer",
        "roles/logging.logWriter",
        "roles/monitoring.metricWriter",
      ]

      artifact_registry_repositories = [
        {
          location   = "us-central1"
          repository = "mcp-staging"
          role       = "roles/artifactregistry.writer"
        }
      ]
    }

    # Production deployment service account
    production = {
      account_id        = "github-actions-production"
      display_name      = "GitHub Actions - Production Deployment"
      description       = "Deploys to GKE production cluster"
      repository_filter = "mcp-server-langgraph"

      project_roles = [
        "roles/container.developer",
        "roles/artifactregistry.writer",
        "roles/logging.logWriter",
        "roles/monitoring.metricWriter",
        "roles/cloudtrace.agent",
      ]

      artifact_registry_repositories = [
        {
          location   = "us-central1"
          repository = "mcp-production"
          role       = "roles/artifactregistry.writer"
        }
      ]

      storage_buckets = [
        {
          bucket_name = "my-production-backups"
          role        = "roles/storage.objectCreator"
        }
      ]
    }

    # Terraform service account
    terraform = {
      account_id   = "github-actions-terraform"
      display_name = "GitHub Actions - Terraform"
      description  = "Manages infrastructure via Terraform"

      project_roles = [
        "roles/compute.networkAdmin",
        "roles/container.admin",
        "roles/iam.serviceAccountAdmin",
        "roles/resourcemanager.projectIamAdmin",
        "roles/storage.admin",
      ]

      storage_buckets = [
        {
          bucket_name = "terraform-state-bucket"
          role        = "roles/storage.objectAdmin"
        }
      ]

      secret_ids = ["terraform-secrets"]
    }
  }
}
```

## Outputs

The module provides outputs that you can use to configure GitHub Actions:

```hcl
# Get the Workload Identity Provider name
output "wif_provider" {
  value = module.github_actions_wif.workload_identity_provider_name
}

# Get service account emails
output "service_account_emails" {
  value = module.github_actions_wif.service_account_emails
}

# Get all GitHub secrets (formatted for easy copy-paste)
output "github_secrets" {
  value     = module.github_actions_wif.github_secrets
  sensitive = false
}
```

## GitHub Actions Integration

Once the module is applied, add these secrets to your GitHub repository:

1. **GCP_WIF_PROVIDER**: The Workload Identity Provider name (from `workload_identity_provider_name` output)
2. **GCP_STAGING_SA_EMAIL**: The staging service account email (from `service_account_emails["staging"]` output)
3. **GCP_PRODUCTION_SA_EMAIL**: The production service account email (from `service_account_emails["production"]` output)
4. **GCP_TERRAFORM_SA_EMAIL**: The terraform service account email (from `service_account_emails["terraform"]` output)

### GitHub Actions Workflow Example

```yaml
name: Deploy to GKE Staging

on:
  push:
    branches: [main]

permissions:
  contents: read
  id-token: write  # Required for OIDC

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5

      # Authenticate using Workload Identity Federation
      - id: auth
        uses: google-github-actions/auth@v3
        with:
          workload_identity_provider: ${{ secrets.GCP_WIF_PROVIDER }}
          service_account: ${{ secrets.GCP_STAGING_SA_EMAIL }}

      # Now you can use gcloud, kubectl, etc.
      - name: Deploy to GKE
        run: |
          gcloud container clusters get-credentials my-cluster --region us-central1
          kubectl apply -k deployments/overlays/staging
```

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|----------|
| project_id | GCP Project ID | string | n/a | yes |
| project_number | GCP Project Number | string | n/a | yes |
| github_repository_owner | GitHub repository owner/org | string | n/a | yes |
| service_accounts | Map of service accounts to create | map(object) | n/a | yes |
| pool_id | Workload Identity Pool ID | string | "github-actions-pool" | no |
| pool_display_name | Pool display name | string | "GitHub Actions Pool" | no |
| provider_id | Provider ID | string | "github-actions-provider" | no |
| provider_display_name | Provider display name | string | "GitHub Actions OIDC Provider" | no |

## Outputs

| Name | Description |
|------|-------------|
| workload_identity_provider_name | Full WIF provider name for GitHub Actions |
| service_account_emails | Map of service account emails |
| service_account_ids | Map of service account resource IDs |
| github_secrets | Formatted secrets for GitHub repository |

## Security Best Practices

1. **Repository Filtering**: Use `repository_filter` to restrict service accounts to specific repositories
2. **Least Privilege**: Grant only the minimum required IAM roles
3. **Separate Service Accounts**: Use different service accounts for staging, production, and terraform
4. **Audit Logging**: Enable audit logging for all service account usage
5. **No Service Account Keys**: Never create or download service account keys (WIF eliminates this need)

## Troubleshooting

### Error: "workload_identity_provider or credentials_json must be specified"

**Cause**: GitHub Actions workflow missing required configuration

**Solution**: Ensure your workflow has:
- `id-token: write` permission
- `workload_identity_provider` input
- `service_account` input

### Error: "PERMISSION_DENIED: The caller does not have permission"

**Cause**: Service account lacks required IAM roles

**Solution**: Add the necessary role to `project_roles` or resource-specific access in the module configuration

### Error: "Pool already exists" during apply

**Cause**: Pool was previously created and deleted (in 30-day soft-delete period)

**Solution**: Undelete the pool:
```bash
gcloud iam workload-identity-pools undelete github-actions-pool \
  --location=global \
  --project=YOUR_PROJECT_ID
```

## Migration from Service Account Keys

If you're currently using service account keys:

1. Apply this Terraform module
2. Add the secrets to GitHub
3. Update workflows to use `google-github-actions/auth@v3` with WIF
4. Remove old `GCP_SA_KEY` secrets
5. Delete service account keys

## References

- [Workload Identity Federation](https://cloud.google.com/iam/docs/workload-identity-federation)
- [GitHub Actions OIDC](https://docs.github.com/en/actions/deployment/security-hardening-your-deployments/about-security-hardening-with-openid-connect)
- [google-github-actions/auth](https://github.com/google-github-actions/auth)
