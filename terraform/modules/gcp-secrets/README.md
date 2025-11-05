# GCP Secret Manager Module

## Overview

This Terraform module manages application secrets in GCP Secret Manager, ensuring reproducible and idempotent secret provisioning across environments.

## Features

- Creates all required application secrets
- Manages IAM bindings for External Secrets Operator
- Supports multiple environments (dev, staging, production)
- Automatic replication policy
- Labeled for organization

## Usage

```hcl
module "secrets" {
  source = "../../modules/gcp-secrets"

  project_id  = "vishnu-sandbox-20250310"
  environment = "staging"

  # External Secrets Operator service account
  external_secrets_service_account = "external-secrets-staging@vishnu-sandbox-20250310.iam.gserviceaccount.com"

  # Optional: Application service account for direct access
  app_service_account = ""

  labels = {
    team        = "platform"
    cost_center = "engineering"
  }
}
```

## Secrets Created

This module creates the following secrets (with environment prefix):

1. `{env}-anthropic-api-key` - Anthropic Claude API key
2. `{env}-google-api-key` - Google AI/Gemini API key
3. `{env}-jwt-secret` - JWT signing secret
4. `{env}-postgres-username` - PostgreSQL username
5. `{env}-keycloak-db-password` - Keycloak database password
6. `{env}-openfga-db-password` - OpenFGA database password
7. `{env}-gdpr-db-password` - GDPR database password
8. `{env}-redis-host` - Redis host address
9. `{env}-redis-password` - Redis password

## Importing Existing Secrets

If secrets already exist (created manually), import them:

```bash
cd terraform/environments/gcp-staging

# Import each secret
terraform import 'module.secrets.google_secret_manager_secret.secrets["staging-anthropic-api-key"]' \
  projects/vishnu-sandbox-20250310/secrets/staging-anthropic-api-key

terraform import 'module.secrets.google_secret_manager_secret.secrets["staging-jwt-secret"]' \
  projects/vishnu-sandbox-20250310/secrets/staging-jwt-secret

# Import IAM bindings
terraform import 'module.secrets.google_secret_manager_secret_iam_member.external_secrets["staging-anthropic-api-key"]' \
  "projects/vishnu-sandbox-20250310/secrets/staging-anthropic-api-key roles/secretmanager.secretAccessor serviceAccount:external-secrets-staging@vishnu-sandbox-20250310.iam.gserviceaccount.com"

# Repeat for all secrets...
```

## Managing Secret Values

**Important**: This module manages the secret **metadata** (name, IAM, replication), NOT the secret **values**.

To set/update secret values:

```bash
# Create/update secret value
echo -n "your-secret-value" | gcloud secrets versions add staging-anthropic-api-key \
  --data-file=- \
  --project=vishnu-sandbox-20250310

# Or from file
gcloud secrets versions add staging-jwt-secret \
  --data-file=/path/to/secret.txt \
  --project=vishnu-sandbox-20250310
```

## Outputs

- `secret_ids` - Map of secret names to IDs
- `secret_names` - List of all secret names
- `iam_bindings_count` - Number of IAM bindings created

## Requirements

- Terraform >= 1.5.0
- Google Provider >= 5.0
- Secret Manager API enabled
- Service account with `roles/secretmanager.admin`

## Best Practices

1. **Never commit secret values** to version control
2. **Use Terraform** to manage secret metadata and IAM
3. **Use External Secrets Operator** to sync secrets into Kubernetes
4. **Rotate secrets** regularly using version management
5. **Import existing secrets** into Terraform state for tracking
