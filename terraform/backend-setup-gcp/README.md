# Terraform Backend Setup for GCP

This directory contains Terraform configuration to set up the backend infrastructure for storing Terraform state in Google Cloud Storage (GCS).

## Overview

This setup creates:

- **GCS Bucket for Terraform State**: Stores Terraform state files with versioning, encryption, and lifecycle management
- **GCS Bucket for Access Logs**: Stores access logs for the state bucket with automatic cleanup
- **IAM Bindings**: (Optional) Grants permissions to a service account for state management

## Prerequisites

Before running this setup, ensure you have:

1. **gcloud CLI** installed and authenticated:
   ```bash
   gcloud auth login
   gcloud auth application-default login
   ```

2. **GCP Project** created with billing enabled:
   ```bash
   # Create a new project (if needed)
   gcloud projects create PROJECT_ID --name="MCP LangGraph"

   # Set the project
   gcloud config set project PROJECT_ID

   # Enable billing (replace BILLING_ACCOUNT_ID)
   gcloud billing projects link PROJECT_ID --billing-account=BILLING_ACCOUNT_ID
   ```

3. **Required APIs** enabled:
   ```bash
   gcloud services enable storage-api.googleapis.com
   gcloud services enable cloudresourcemanager.googleapis.com
   gcloud services enable iam.googleapis.com
   ```

4. **Terraform** 1.5.0 or later installed:
   ```bash
   terraform version
   ```

5. **Appropriate IAM Permissions**:
   - `storage.buckets.create`
   - `storage.buckets.update`
   - `storage.buckets.setIamPolicy`
   - `iam.serviceAccounts.actAs` (if using a service account)

   Recommended role: `roles/storage.admin` or custom role with the above permissions.

## Quick Start

### 1. Create terraform.tfvars

Create a `terraform.tfvars` file with your configuration:

```hcl
project_id = "your-gcp-project-id"
region     = "us-central1"

# Optional: specify a service account for Terraform operations
terraform_service_account = "terraform@your-project-id.iam.gserviceaccount.com"

# Optional: customize bucket prefix
bucket_prefix = "mcp-langgraph"
```

### 2. Initialize Terraform

```bash
terraform init
```

### 3. Review the Plan

```bash
terraform plan
```

This will show you the resources that will be created:
- 2 GCS buckets (state + logs)
- IAM bindings (if service account is specified)
- Lifecycle policies
- Logging configuration

### 4. Apply the Configuration

```bash
terraform apply
```

Review the output and type `yes` to confirm.

### 5. Note the Outputs

After successful apply, Terraform will output:
- Bucket names
- Backend configuration
- Setup instructions

**Example output:**
```
Outputs:

backend_config = {
  "bucket" = "mcp-langgraph-terraform-state-us-central1-a1b2c3d4"
  "prefix" = "env"
  "project" = "your-project-id"
  "region" = "us-central1"
}

terraform_state_bucket = "mcp-langgraph-terraform-state-us-central1-a1b2c3d4"
```

**Important:** Save the bucket name! You'll need it for configuring backends in other Terraform modules.

## Using the Backend in Other Modules

After setting up the backend, configure your environment Terraform files to use it:

### Option 1: Direct Backend Configuration

Add this to your `terraform/environments/gcp-prod/main.tf`:

```hcl
terraform {
  backend "gcs" {
    bucket  = "mcp-langgraph-terraform-state-us-central1-a1b2c3d4"  # Replace with your bucket name
    prefix  = "env/prod"
  }
}
```

### Option 2: Backend Configuration File

Create a `backend.conf` file:

```hcl
bucket  = "mcp-langgraph-terraform-state-us-central1-a1b2c3d4"
prefix  = "env/prod"
```

Then initialize with:

```bash
terraform init -backend-config=backend.conf
```

### Option 3: Use terraform.tfbackend

Create `terraform/environments/gcp-prod/backend.tfbackend`:

```hcl
bucket = "mcp-langgraph-terraform-state-us-central1-a1b2c3d4"
prefix = "env/prod"
```

Initialize:

```bash
terraform init -backend-config=backend.tfbackend
```

## Configuration Options

### Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `project_id` | GCP project ID | - | Yes |
| `region` | GCP region for buckets | `us-central1` | No |
| `bucket_prefix` | Prefix for bucket names | `mcp-langgraph` | No |
| `terraform_service_account` | Service account email for IAM bindings | `""` | No |
| `enable_cmek` | Enable Customer-Managed Encryption Keys | `false` | No |
| `kms_key_name` | KMS key for CMEK | `""` | No |
| `log_retention_days` | Days to retain logs | `90` | No |
| `state_version_retention` | Number of versions to keep | `10` | No |
| `labels` | Additional labels | `{}` | No |

### Example with All Options

```hcl
project_id = "my-project-123"
region     = "us-central1"
bucket_prefix = "my-company-terraform"

terraform_service_account = "terraform@my-project-123.iam.gserviceaccount.com"

enable_cmek  = true
kms_key_name = "projects/my-project-123/locations/us-central1/keyRings/terraform/cryptoKeys/state"

log_retention_days       = 60
state_version_retention  = 20

labels = {
  team        = "platform"
  cost_center = "engineering"
  compliance  = "soc2"
}
```

## Features

### State Versioning

- GCS versioning is enabled on the state bucket
- Keeps last 10 versions by default (configurable)
- Older archived versions are automatically deleted
- You can restore previous versions if needed:

```bash
# List versions
gsutil ls -a gs://BUCKET_NAME/env/prod/

# Restore a specific version
gsutil cp gs://BUCKET_NAME/env/prod/default.tfstate#VERSION_NUMBER gs://BUCKET_NAME/env/prod/default.tfstate
```

### State Locking

GCS provides **built-in state locking** - no additional resources needed (unlike AWS DynamoDB).

- Automatic locking when `terraform apply` runs
- Prevents concurrent modifications
- Locks are automatically released after operations

### Encryption

**Default: Google-Managed Encryption**
- All data encrypted at rest automatically
- No configuration needed
- Keys managed by Google

**Optional: Customer-Managed Encryption Keys (CMEK)**
```hcl
enable_cmek  = true
kms_key_name = "projects/PROJECT_ID/locations/REGION/keyRings/RING/cryptoKeys/KEY"
```

Benefits:
- Full control over encryption keys
- Key rotation policies
- Audit key usage
- Compliance requirements (HIPAA, PCI-DSS)

### Access Logging

- All bucket access is logged to a separate logs bucket
- Logs include: who, when, what operation, from where
- Logs retained for 90 days (configurable)
- Older logs moved to NEARLINE storage after 30 days (cost savings)

View logs:
```bash
gsutil ls gs://LOGS_BUCKET_NAME/state-access-logs/
```

### Public Access Prevention

- **Enforced** on both buckets
- Prevents accidental public exposure
- Cannot be disabled without modifying Terraform

### Lifecycle Protection

- `prevent_destroy = true` on both buckets
- Prevents accidental deletion via Terraform
- Must be manually removed to delete buckets

### IAM Best Practices

If using a service account:
```hcl
terraform_service_account = "terraform@PROJECT_ID.iam.gserviceaccount.com"
```

The service account gets:
- `roles/storage.objectAdmin` on state bucket
- `roles/storage.objectAdmin` on logs bucket

**Principle of Least Privilege:**
- Only grant access to specific service accounts
- Use Workload Identity for GitHub Actions
- Avoid using user accounts for CI/CD

## Security Best Practices

### 1. Use Workload Identity Federation

For GitHub Actions (already configured in this repo):

```yaml
# .github/workflows/terraform.yaml
- uses: google-github-actions/auth@v1
  with:
    workload_identity_provider: 'projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/github-actions-pool/providers/github-provider'
    service_account: 'terraform@PROJECT_ID.iam.gserviceaccount.com'
```

### 2. Enable Audit Logging

Enable Data Access logs for GCS:

```bash
gcloud logging write test-entry "Test" --resource=gcs_bucket
```

Configure in `terraform/modules/gcp-vpc/main.tf`:
```hcl
resource "google_project_iam_audit_config" "gcs_audit" {
  project = var.project_id
  service = "storage.googleapis.com"

  audit_log_config {
    log_type = "DATA_READ"
  }
  audit_log_config {
    log_type = "DATA_WRITE"
  }
}
```

### 3. Use VPC Service Controls (Advanced)

For sensitive workloads, restrict access to GCS buckets:

```hcl
# Create a service perimeter
resource "google_access_context_manager_service_perimeter" "terraform_perimeter" {
  parent = "accessPolicies/${var.access_policy_id}"
  name   = "accessPolicies/${var.access_policy_id}/servicePerimeters/terraform"
  title  = "Terraform State Perimeter"

  status {
    restricted_services = ["storage.googleapis.com"]
    resources = ["projects/${data.google_project.current.number}"]
  }
}
```

### 4. Regular State Backups

While GCS versioning is enabled, consider periodic exports:

```bash
# Backup current state
gsutil cp gs://BUCKET_NAME/env/prod/default.tfstate ./backups/state-$(date +%Y%m%d).tfstate

# Automated backup script
#!/bin/bash
BUCKET="your-terraform-state-bucket"
BACKUP_DIR="./terraform-state-backups"
DATE=$(date +%Y%m%d)

for env in dev staging prod; do
  gsutil cp gs://${BUCKET}/env/${env}/default.tfstate ${BACKUP_DIR}/${env}-${DATE}.tfstate
done
```

## Cost Optimization

### Storage Costs

**State Bucket:**
- Typical state file: 100 KB - 5 MB
- 10 versions × 5 MB = 50 MB max
- Cost: ~$0.001/month (negligible)

**Logs Bucket:**
- Access logs: ~1 KB per operation
- 1000 operations/day × 30 days = 30 MB
- Cost: ~$0.001/month

**Total estimated cost: < $0.01/month**

### Cost Savings Tips

1. **Reduce log retention** (if compliance allows):
   ```hcl
   log_retention_days = 30
   ```

2. **Use COLDLINE for long-term backups**:
   ```hcl
   lifecycle_rule {
     action {
       type          = "SetStorageClass"
       storage_class = "COLDLINE"
     }
     condition {
       age = 90
     }
   }
   ```

3. **Regional vs Multi-Regional**:
   - Use regional buckets (already configured) for lower cost
   - Only use multi-regional if you need global redundancy

## Troubleshooting

### Issue: Permission Denied

**Error:**
```
Error: googleapi: Error 403: does not have storage.buckets.create access
```

**Solution:**
```bash
# Grant yourself storage admin role
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="user:YOUR_EMAIL@example.com" \
  --role="roles/storage.admin"
```

### Issue: Bucket Name Already Exists

**Error:**
```
Error: Error creating bucket: googleapi: Error 409: You already own this bucket.
```

**Solution:**
Bucket names are globally unique. The module adds a random suffix, but if you previously created a bucket:

1. **Option 1:** Import existing bucket:
   ```bash
   terraform import google_storage_bucket.terraform_state BUCKET_NAME
   ```

2. **Option 2:** Change bucket prefix:
   ```hcl
   bucket_prefix = "my-unique-prefix-123"
   ```

### Issue: State Locking

**Error:**
```
Error: Error locking state: Error acquiring the state lock
```

**Solution:**
GCS locks are automatic. If stuck:

1. **Check if another process is running:**
   ```bash
   # Find Terraform processes
   ps aux | grep terraform
   ```

2. **Force unlock (use with caution):**
   ```bash
   terraform force-unlock LOCK_ID
   ```

3. **Verify bucket permissions:**
   ```bash
   gsutil iam get gs://BUCKET_NAME
   ```

### Issue: Cannot Destroy Bucket

**Error:**
```
Error: Instance cannot be destroyed
```

**Solution:**
Buckets have `prevent_destroy = true`. To remove:

1. **Comment out lifecycle block** in `main.tf`:
   ```hcl
   # lifecycle {
   #   prevent_destroy = true
   # }
   ```

2. **Run terraform apply** to update the configuration

3. **Run terraform destroy**

**Warning:** Only do this if you're absolutely sure you want to delete the state!

## Maintenance

### Rotating Encryption Keys

If using CMEK:

```bash
# Create new key version
gcloud kms keys versions create \
  --location=REGION \
  --keyring=KEYRING \
  --key=KEY

# Update bucket to use new version (automatic with CMEK)
```

### Reviewing Access Logs

```bash
# List recent access logs
gsutil ls -l gs://LOGS_BUCKET/state-access-logs/ | head -20

# Download and analyze
gsutil cp -r gs://LOGS_BUCKET/state-access-logs/ ./logs/
```

### Monitoring Costs

```bash
# View storage costs
gcloud billing accounts list
gcloud alpha billing accounts describe BILLING_ACCOUNT_ID

# Set up budget alerts (recommended)
gcloud billing budgets create \
  --billing-account=BILLING_ACCOUNT_ID \
  --display-name="Terraform State Storage" \
  --budget-amount=10USD \
  --threshold-rule=percent=50 \
  --threshold-rule=percent=90
```

## Migration from AWS/Other Backends

### From AWS S3 to GCS

```bash
# 1. Pull latest state from AWS
cd terraform/environments/prod
terraform init
terraform state pull > state-backup-aws.json

# 2. Update backend configuration to GCS
# Edit main.tf to use GCS backend

# 3. Reinitialize with migration
terraform init -migrate-state

# 4. Verify state
terraform state list
terraform plan  # Should show no changes
```

### From Local to GCS

```bash
# 1. Backup local state
cp terraform.tfstate terraform.tfstate.backup

# 2. Add backend configuration
# Add backend "gcs" block to main.tf

# 3. Initialize and migrate
terraform init -migrate-state

# 4. Verify
gsutil ls gs://BUCKET_NAME/env/prod/
```

## Additional Resources

- [Terraform GCS Backend Documentation](https://developer.hashicorp.com/terraform/language/settings/backends/gcs)
- [GCS Best Practices](https://cloud.google.com/storage/docs/best-practices)
- [GCP IAM Permissions Reference](https://cloud.google.com/storage/docs/access-control/iam-permissions)
- [Workload Identity Federation](https://cloud.google.com/iam/docs/workload-identity-federation)

## Support

For issues or questions:
1. Check the [Troubleshooting](#troubleshooting) section
2. Review Terraform and GCS documentation
3. Open an issue in the repository

## License

This configuration is part of the MCP Server LangGraph project.
