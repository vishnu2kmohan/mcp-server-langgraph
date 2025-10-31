# Terraform Backend Setup

This directory contains the one-time setup for Terraform state management infrastructure.

## What This Creates

1. **S3 Bucket** for Terraform state storage
   - Versioning enabled
   - Server-side encryption (AES-256)
   - Public access blocked
   - Access logging enabled
   - Lifecycle policy for cost optimization

2. **DynamoDB Table** for state locking
   - On-demand billing
   - Point-in-time recovery
   - Server-side encryption

3. **S3 Bucket** for access logs
   - Versioning enabled
   - 90-day retention policy

## Prerequisites

- AWS CLI configured with admin credentials
- Terraform >= 1.5.0

## Usage

### 1. Initialize and Apply

```bash
cd terraform/backend-setup

# Initialize Terraform (local state for this module only)
terraform init

# Review planned changes
terraform plan

# Create backend infrastructure
terraform apply
```

### 2. Note the Outputs

After applying, note the outputs:

```bash
terraform output

# Example output:
# terraform_state_bucket = "mcp-langgraph-terraform-state-us-east-1-123456789012"
# terraform_locks_table = "mcp-langgraph-terraform-locks"
```

### 3. Configure Environment Modules

Use these values in your environment `backend.tf` files:

```hcl
terraform {
  backend "s3" {
    bucket         = "mcp-langgraph-terraform-state-us-east-1-123456789012"
    key            = "environments/prod/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "mcp-langgraph-terraform-locks"
    encrypt        = true
  }
}
```

## Security Considerations

- **Bucket Encryption**: All state files are encrypted at rest
- **Access Logging**: All bucket access is logged for audit
- **Versioning**: Previous state versions are retained
- **State Locking**: DynamoDB prevents concurrent modifications
- **Public Access**: Completely blocked at bucket level

## Disaster Recovery

### State File Recovery

```bash
# List all versions of a state file
aws s3api list-object-versions \
  --bucket mcp-langgraph-terraform-state-us-east-1-123456789012 \
  --prefix environments/prod/terraform.tfstate

# Restore a specific version
aws s3api get-object \
  --bucket mcp-langgraph-terraform-state-us-east-1-123456789012 \
  --key environments/prod/terraform.tfstate \
  --version-id <VERSION_ID> \
  terraform.tfstate.backup
```

### Lock Release

If a lock gets stuck:

```bash
# Delete the lock item
aws dynamodb delete-item \
  --table-name mcp-langgraph-terraform-locks \
  --key '{"LockID":{"S":"mcp-langgraph-terraform-state-us-east-1-123456789012/environments/prod/terraform.tfstate-md5"}}'
```

## Cost Estimate

- S3 storage: ~$0.50/month (for typical state files)
- DynamoDB: ~$0.10/month (with on-demand billing)
- **Total**: ~$0.60/month

## Cleanup

⚠️ **WARNING**: Only destroy this if you're completely done with Terraform

```bash
# Remove lifecycle protection
terraform state rm aws_s3_bucket.terraform_state
terraform state rm aws_s3_bucket.terraform_state_logs
terraform state rm aws_dynamodb_table.terraform_locks

# Delete resources
terraform destroy
```

## Troubleshooting

### Error: Bucket already exists

If you see `BucketAlreadyExists`, the bucket name is globally unique. Either:
1. Delete the existing bucket
2. Modify the bucket name in `main.tf`

### Error: Access Denied

Ensure your AWS credentials have administrator access:

```bash
aws sts get-caller-identity
```

Required permissions:
- `s3:*` on new buckets
- `dynamodb:*` on new tables
- `logs:*` for CloudWatch
