# Terraform Backend Configuration Files

This directory contains Terraform backend configuration files for each environment.

## Setup Instructions

### For GCP Environments

1. Copy the example file for your environment:
   ```bash
   cp gcp-dev.gcs.tfbackend.example gcp-dev.gcs.tfbackend
   cp gcp-staging.gcs.tfbackend.example gcp-staging.gcs.tfbackend
   cp gcp-prod.gcs.tfbackend.example gcp-prod.gcs.tfbackend
   ```

2. Edit the `.tfbackend` files if needed (e.g., to change bucket name or prefix)

3. Initialize Terraform with the backend config:
   ```bash
   cd terraform/environments/gcp-dev
   terraform init -backend-config=../../backend-configs/gcp-dev.gcs.tfbackend
   ```

### For AWS Environments

1. Copy the example file for your environment:
   ```bash
   cp aws-dev.s3.tfbackend.example aws-dev.s3.tfbackend
   cp aws-staging.s3.tfbackend.example aws-staging.s3.tfbackend
   cp prod.s3.tfbackend.example prod.s3.tfbackend
   ```

2. **IMPORTANT:** Edit each `.tfbackend` file and replace `ACCOUNT_ID` with your AWS account ID:
   ```
   bucket = "mcp-langgraph-terraform-state-us-east-1-123456789012"
   ```

3. Initialize Terraform with the backend config:
   ```bash
   cd terraform/environments/aws-dev
   terraform init -backend-config=../../backend-configs/aws-dev.s3.tfbackend
   ```

## Security Notes

- **DO NOT commit** actual `.tfbackend` files to version control
- The `.gitignore` file is configured to exclude `*.tfbackend` files
- Only `.example` files should be committed
- Keep your backend config files secure as they may contain sensitive information

## Migrating from Hardcoded Backend

If you're migrating from an existing setup with hardcoded backend configuration:

1. Create your `.tfbackend` file as described above
2. Run `terraform init -reconfigure -backend-config=path/to/your.tfbackend`
3. Terraform will migrate your existing state to use the new configuration

## Per-Environment Configuration

Each environment can have different backend settings:
- **GCP**: Different buckets or prefixes for isolation
- **AWS**: Different S3 buckets, regions, or DynamoDB tables

Customize the `.tfbackend` files as needed for your infrastructure requirements.
