# MCP Server LangGraph - Terraform Infrastructure

This directory contains Infrastructure as Code (IaC) for deploying the MCP Server LangGraph application to AWS EKS.

## Directory Structure

```
terraform/
├── modules/              # Reusable Terraform modules
│   ├── vpc/             # VPC with public/private subnets, NAT gateways
│   ├── eks/             # EKS cluster with managed node groups
│   ├── rds/             # RDS PostgreSQL Multi-AZ
│   ├── elasticache/     # ElastiCache Redis Cluster
│   ├── iam/             # IAM roles and policies (IRSA)
│   ├── security-groups/ # Security groups for all resources
│   ├── ebs-csi/         # EBS CSI driver configuration
│   ├── alb-controller/  # AWS Load Balancer Controller
│   └── external-secrets/# External Secrets Operator
└── environments/        # Environment-specific configurations
    ├── dev/            # Development environment
    ├── staging/        # Staging environment
    └── prod/           # Production environment
```

## Prerequisites

- AWS CLI configured with appropriate credentials
- Terraform >= 1.5.0
- kubectl >= 1.28
- helm >= 3.12

## Quick Start

### 1. Initialize Terraform Backend

```bash
# Update backend configuration in environments/{env}/backend.tf
cd terraform/environments/prod
terraform init
```

### 2. Review and Apply Infrastructure

```bash
# Plan changes
terraform plan -out=tfplan

# Apply changes
terraform apply tfplan
```

### 3. Configure kubectl

```bash
# Update kubeconfig
aws eks update-kubeconfig --region us-east-1 --name mcp-server-langgraph-prod
```

## Environment Configuration

Each environment (dev/staging/prod) has its own:
- `main.tf` - Main configuration
- `variables.tf` - Environment-specific variables
- `outputs.tf` - Output values
- `backend.tf` - Remote state configuration
- `terraform.tfvars` - Variable values (gitignored)

## Modules

### VPC Module
Creates a multi-AZ VPC with:
- 3 public subnets
- 3 private subnets
- NAT gateways for each AZ
- VPC endpoints for S3, ECR, CloudWatch

### EKS Module
Deploys EKS cluster with:
- Managed node groups (general-purpose and compute-optimized)
- IRSA (IAM Roles for Service Accounts)
- EBS CSI driver addon
- VPC CNI addon
- CoreDNS addon

### RDS Module
Creates PostgreSQL database:
- Multi-AZ deployment
- Automated backups (7-day retention)
- Encryption at rest (KMS)
- Enhanced monitoring

### ElastiCache Module
Deploys Redis cluster:
- Cluster mode enabled
- Multi-AZ with automatic failover
- Encryption in transit and at rest
- Automatic backups

### IAM Module
Creates IAM resources:
- EKS cluster role
- Node group role
- IRSA roles for:
  - Application pods
  - External Secrets Operator
  - AWS Load Balancer Controller
  - EBS CSI driver

## State Management

Terraform state is stored in S3 with DynamoDB locking:
- **S3 Bucket**: `mcp-langgraph-terraform-state-{region}-{account_id}`
- **DynamoDB Table**: `mcp-langgraph-terraform-locks`
- **Encryption**: AES-256
- **Versioning**: Enabled

## Security Best Practices

1. **Secrets Management**: Use AWS Secrets Manager, never commit secrets
2. **IAM**: Least privilege principle for all roles
3. **Networking**: Private subnets for all data resources
4. **Encryption**: At rest and in transit for all supported services
5. **Logging**: CloudTrail and VPC Flow Logs enabled

## Cost Estimation

Use `terraform plan` with cost estimation:

```bash
# Using Infracost
brew install infracost
infracost breakdown --path .
```

Estimated monthly costs:
- **Dev**: ~$500-700
- **Staging**: ~$800-1,200
- **Prod**: ~$2,000-3,500

## Cleanup

To destroy infrastructure:

```bash
# WARNING: This will delete all resources
terraform destroy
```

## Troubleshooting

### State Lock Issues

```bash
# Force unlock (use with caution)
terraform force-unlock <LOCK_ID>
```

### EKS Access Issues

```bash
# Update kubeconfig
aws eks update-kubeconfig --region us-east-1 --name <cluster-name>

# Verify access
kubectl get nodes
```

## Support

For issues or questions:
- Check module READMEs in `modules/*/README.md`
- Review Terraform logs: `TF_LOG=DEBUG terraform plan`
- Consult AWS EKS documentation: https://docs.aws.amazon.com/eks/

## Related Documentation

- [EKS Deployment Guide](../../docs/deployment/kubernetes/eks.mdx)
- [Disaster Recovery](../../docs/deployment/disaster-recovery.mdx)
- [Architecture Decision Records](../../docs/architecture/)
