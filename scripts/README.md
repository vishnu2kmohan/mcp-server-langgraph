# Deployment Scripts

Automated deployment scripts for all cloud providers implementing 11 Kubernetes best practices.

## Available Scripts

- `deploy-gcp-gke.sh` - Deploy to Google Cloud Platform (GKE)
- `deploy-aws-eks.sh` - Deploy to Amazon Web Services (EKS)
- `deploy-azure-aks.sh` - Deploy to Microsoft Azure (AKS)

## Prerequisites

### Common Requirements

- `kubectl` - Kubernetes command-line tool
- `helm` - Kubernetes package manager
- `terraform` - Infrastructure as Code tool
- `jq` - JSON processor (for verification steps)
- `git` - For VPA installation

### Cloud-Specific Requirements

**GCP (GKE)**:
- `gcloud` CLI
- Authenticated with GCP: `gcloud auth login`
- Project set: `gcloud config set project PROJECT_ID`

**AWS (EKS)**:
- `aws` CLI
- Configured credentials: `aws configure`
- Or use IAM roles/instance profiles

**Azure (AKS)**:
- `az` CLI
- Logged in: `az login`

## Usage

### GCP GKE Deployment

```bash
# Set environment variables
export GCP_PROJECT_ID="your-project-id"
export GKE_CLUSTER_NAME="mcp-production"  # Optional, defaults to mcp-production
export GCP_REGION="us-central1"           # Optional, defaults to us-central1

# Run deployment
./scripts/deploy-gcp-gke.sh
```

### AWS EKS Deployment

```bash
# Set environment variables
export AWS_REGION="us-east-1"             # Optional, defaults to us-east-1
export EKS_CLUSTER_NAME="mcp-production"  # Optional, defaults to mcp-production
export AWS_ACCOUNT_ID="123456789012"      # Optional, auto-detected if not set

# Run deployment
./scripts/deploy-aws-eks.sh
```

### Azure AKS Deployment

```bash
# Set environment variables
export AZURE_RESOURCE_GROUP="mcp-production-rg"  # Optional
export AKS_CLUSTER_NAME="mcp-production"         # Optional
export AZURE_LOCATION="eastus"                   # Optional, defaults to eastus

# Run deployment
./scripts/deploy-azure-aks.sh
```

## Platform Automation Status

| Script | Status | Notes |
|--------|--------|-------|
| `deploy-gcp-gke.sh` | ✅ **Production Ready** | Full automation with dev/staging/prod environments |
| `deploy-aws-eks.sh` | ✅ **Production Ready** | Full automation with dev/staging/prod environments |
| `deploy-azure-aks.sh` | ❌ **Manual Only** | Terraform automation not yet available, see [aks.mdx](../docs/deployment/kubernetes/aks.mdx) |

**Note**: AKS deployment currently requires manual setup using Azure CLI. The script will display instructions pointing to the manual runbook.

## What Each Script Does

All deployment scripts follow the same pattern and implement all 11 best practices:

1. **Prerequisite Checks** - Validates all required tools are installed
2. **Infrastructure Deployment** - Deploys cloud resources via Terraform
3. **Kubectl Configuration** - Configures kubectl access to the cluster
4. **Velero Backup/DR** - Installs Velero with cloud-specific storage
5. **Karpenter (EKS only)** - Deploys intelligent autoscaling
6. **Namespace & Security** - Creates namespace with PSS and network policies
7. **Istio Service Mesh** - Installs/configures Istio with mTLS STRICT
8. **Monitoring Stack** - Deploys Loki, Kubecost with cloud billing integration
9. **Application Deployment** - Deploys app with Helm using cloud-managed databases
10. **VPA Deployment** - Installs Vertical Pod Autoscalers
11. **Verification** - Validates all components are working correctly

## Environment Selection

The GKE and EKS scripts now support environment selection:

**GKE Environments**:
```bash
export GCP_ENVIRONMENT=gcp-dev      # Development environment
export GCP_ENVIRONMENT=gcp-staging  # Staging environment
export GCP_ENVIRONMENT=gcp-prod     # Production environment (default)
```

**EKS Environments**:
```bash
export AWS_ENVIRONMENT=aws-dev      # Development (minimal cost)
export AWS_ENVIRONMENT=aws-staging  # Staging (cost-optimized)
export AWS_ENVIRONMENT=prod         # Production (default)
```

## Deployment Time

Approximate deployment times (automated deployments):

- **GKE**: 25-35 minutes
- **EKS**: 30-40 minutes (includes Karpenter)
- **AKS**: Manual deployment only (see documentation)

## Post-Deployment

After successful deployment, each script outputs next steps including:

- How to access Kubecost dashboard
- How to access Grafana
- How to view Velero backups
- How to verify Istio mTLS
- How to monitor costs in cloud console

## Troubleshooting

### Common Issues

**Issue**: Script exits with "command not found"
**Solution**: Install the missing tool (kubectl, helm, terraform, cloud CLI)

**Issue**: Terraform fails with authentication error
**Solution**: Ensure you're logged into the correct cloud provider

**Issue**: Pods stuck in Pending state
**Solution**: Check cluster has sufficient capacity and multiple availability zones

**Issue**: Istio sidecar not injected
**Solution**: Ensure namespace has `istio-injection: enabled` label

### Getting Help

1. Check logs: `kubectl logs -n <namespace> <pod-name>`
2. Check events: `kubectl get events -n <namespace> --sort-by='.lastTimestamp'`
3. Verify resources: `kubectl get all -n <namespace>`
4. Check Istio: `istioctl analyze -n <namespace>`

## Cleanup

To remove all deployed resources:

```bash
# GCP
terraform destroy -chdir=terraform/environments/gcp
gcloud container clusters delete $CLUSTER_NAME --region=$REGION

# AWS
terraform destroy -chdir=terraform/environments/aws
aws eks delete-cluster --name $CLUSTER_NAME --region $REGION

# Azure
terraform destroy -chdir=terraform/environments/azure
az aks delete --name $CLUSTER_NAME --resource-group $RESOURCE_GROUP
```

## Manual Deployment

If you prefer manual deployment or need to customize steps:

1. See `docs/IMPLEMENTATION_SUMMARY.md` for detailed deployment checklist
2. See `docs/kubernetes-best-practices-implementation.md` for comprehensive guide
3. See individual component READMEs in respective directories
