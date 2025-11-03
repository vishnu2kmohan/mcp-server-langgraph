# AWS Deployment Scripts

AWS-specific automation scripts for EKS infrastructure and application deployment.

## Scripts

### setup-staging-infrastructure.sh

One-time setup script for AWS EKS staging environment.

**Features**:
- Creates S3 backend for Terraform state
- Creates DynamoDB table for state locking
- Deploys complete EKS infrastructure via Terraform
- Configures kubectl access
- Sets up CloudWatch monitoring

**Usage**:
```bash
export AWS_REGION=us-east-1
./scripts/aws/setup-staging-infrastructure.sh
```

**Cost**: ~$324/month for staging environment

## Prerequisites

- AWS CLI configured with appropriate credentials
- Terraform >= 1.5.0
- kubectl >= 1.28
- Sufficient IAM permissions to create:
  - VPC, subnets, NAT gateways
  - EKS clusters
  - RDS instances
  - ElastiCache clusters
  - IAM roles and policies
  - CloudWatch resources

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `AWS_REGION` | AWS region | `us-east-1` |
| `AWS_ENVIRONMENT` | Environment (aws-dev, aws-staging, prod) | `prod` |
| `EKS_CLUSTER_NAME` | EKS cluster name | `mcp-{env}-eks` |

## Teardown

To delete all resources and stop incurring costs:

```bash
# Destroy staging infrastructure
cd terraform/environments/aws-staging
terraform destroy

# Or use the main deployment script
export AWS_ENVIRONMENT=aws-staging
./scripts/deploy-aws-eks.sh  # Then manually run terraform destroy
```

## Additional Resources

- [EKS Terraform Modules](../../terraform/modules/eks/)
- [AWS Monitoring Setup](../../monitoring/aws/)
- [Kubernetes Overlays](../../deployments/kubernetes/overlays/aws/)
