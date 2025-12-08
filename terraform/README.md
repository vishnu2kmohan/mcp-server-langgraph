# MCP Server LangGraph - Terraform Infrastructure

This directory contains Infrastructure as Code (IaC) for deploying the MCP Server LangGraph application to Google Cloud Platform (GCP) using GKE Autopilot.

## Directory Structure

```
terraform/
├── modules/                    # Reusable Terraform modules
│   ├── gcp-project-services/  # GCP API enablement management
│   ├── gcp-vpc/               # VPC with subnets, Cloud NAT, private service connection
│   ├── gke-autopilot/         # GKE Autopilot cluster with backup and monitoring
│   ├── cloudsql/              # Cloud SQL PostgreSQL with HA
│   ├── memorystore/           # Memorystore for Redis with HA
│   └── gke-workload-identity/ # Workload Identity (GCP's IRSA equivalent)
└── environments/              # Environment-specific configurations
    ├── gcp-dev/              # Development environment (cost-optimized)
    ├── gcp-preview/          # Preview environment (matches production)
    └── gcp-prod/             # Production environment (full HA)
```

## Prerequisites

Before deploying, ensure you have:

1. **Required Tools**:
   - gcloud CLI configured with appropriate credentials
   - Terraform >= 1.5.0
   - kubectl >= 1.28
   - helm >= 3.12

2. **GCP Project Setup**:
   - Active GCP project with billing enabled
   - Sufficient IAM permissions (Project Editor or custom role)
   - Terraform state bucket created (see State Management section)

3. **Required GCP APIs**:
   The `gcp-project-services` module will automatically enable required APIs when you run terraform apply. However, if you need to enable them manually:
   ```bash
   gcloud services enable \
     container.googleapis.com \
     compute.googleapis.com \
     servicenetworking.googleapis.com \
     gkebackup.googleapis.com \
     secretmanager.googleapis.com \
     sqladmin.googleapis.com \
     redis.googleapis.com \
     monitoring.googleapis.com \
     logging.googleapis.com \
     --project=YOUR_PROJECT_ID
   ```

## Quick Start

### 1. Create Terraform State Bucket

Before initializing Terraform, create a GCS bucket for state storage:

```bash
# Set your project ID
export PROJECT_ID="your-gcp-project-id"
export REGION="us-central1"

# Create the state bucket
gsutil mb -p ${PROJECT_ID} -l ${REGION} gs://mcp-langgraph-tfstate

# Enable versioning
gsutil versioning set on gs://mcp-langgraph-tfstate

# Enable uniform bucket-level access
gsutil uniformbucketlevelaccess set on gs://mcp-langgraph-tfstate
```

### 2. Configure Environment Variables

Create a `terraform.tfvars` file in your environment directory:

```bash
cd terraform/environments/gcp-preview

cat > terraform.tfvars <<EOF
project_id = "your-gcp-project-id"
region     = "us-central1"
team       = "platform"

# Monitoring
monitoring_notification_channels = ["projects/PROJECT_ID/notificationChannels/CHANNEL_ID"]

# Optional: Master authorized networks for GKE control plane access
enable_master_authorized_networks = true
master_authorized_networks_cidrs = [
  {
    cidr_block   = "0.0.0.0/0"
    display_name = "All networks"
  }
]
EOF
```

### 3. Initialize Terraform

```bash
# Initialize Terraform with the GCS backend
terraform init

# Validate the configuration
terraform validate
```

### 4. Review and Apply Infrastructure

```bash
# Format code
terraform fmt -recursive

# Plan changes
terraform plan -out=tfplan

# Review the plan carefully, then apply
terraform apply tfplan
```

### 5. Configure kubectl

```bash
# Update kubeconfig for the new cluster
gcloud container clusters get-credentials mcp-preview-gke \
  --region=us-central1 \
  --project=your-gcp-project-id

# Verify cluster access
kubectl get nodes
```

## Environment Configuration

Each environment (gcp-dev/gcp-preview/gcp-prod) has its own:
- `main.tf` - Main infrastructure configuration
- `variables.tf` - Environment-specific variable definitions
- `outputs.tf` - Output values (cluster info, connection strings, etc.)
- `terraform.tfvars` - Variable values (gitignored, create from template)

### Environment Differences

| Feature | Dev | Preview | Production |
|---------|-----|---------|------------|
| Cluster Type | Zonal | Regional | Regional |
| GKE Backup | Disabled | Weekly | Daily |
| Cloud SQL HA | No | Yes | Yes |
| Redis Tier | BASIC | STANDARD_HA | STANDARD_HA |
| Cost (approx) | $300-500/mo | $800-1,200/mo | $2,000-3,500/mo |

## Modules

### gcp-project-services Module

Manages GCP API enablement with conditional flags:
- Core APIs (container, compute)
- Networking APIs (servicenetworking)
- GKE feature APIs (gkebackup, containerscanning)
- Database APIs (sqladmin, redis)
- Monitoring APIs (monitoring, logging)

**Key Features**:
- Declarative API management
- Automatic dependency tracking
- Safe defaults (disable_on_destroy = false)

### gcp-vpc Module

Creates a regional VPC with:
- Custom subnet for GKE nodes
- Secondary IP ranges for pods and services
- Cloud NAT with configurable IP allocation
- Private Service Connection for Cloud SQL and Memorystore
- VPC Flow Logs with sampling
- Optional Cloud Armor security policies

### gke-autopilot Module

Deploys GKE Autopilot cluster with:
- Autopilot mode (Google-managed nodes and scaling)
- Workload Identity for secure pod authentication
- Private cluster option with master authorized networks
- GKE Backup plans with configurable retention
- Fleet registration for Anthos (optional)
- Managed Prometheus monitoring
- Security posture management (BASIC or ENTERPRISE)
- Cost allocation tracking

**Key Addons**:
- HTTP Load Balancing
- Horizontal/Vertical Pod Autoscaling
- GCS Fuse CSI driver (for Cloud Storage mounting)
- GCE Persistent Disk CSI driver

### cloudsql Module

Creates Cloud SQL PostgreSQL with:
- Multi-AZ high availability (regional)
- Automated backups with point-in-time recovery
- Private IP only (no public exposure)
- SSL/TLS required for connections
- Query Insights for performance monitoring
- Automatic storage autoscaling
- Read replicas (optional, configurable per environment)

### memorystore Module

Deploys Memorystore for Redis:
- Standard HA tier with automatic failover
- Transit encryption (TLS)
- Redis AUTH enabled
- RDB persistence with configurable snapshots
- Read replicas for improved read performance
- Cross-region replication for DR (optional)

### gke-workload-identity Module

Creates Workload Identity bindings:
- GCP service accounts for Kubernetes pods
- IAM role bindings (logging, monitoring, tracing)
- Cloud SQL access grants
- Secret Manager access for application secrets
- Cloud Storage bucket permissions
- Pub/Sub topic/subscription access

## State Management

Terraform state is stored in Google Cloud Storage:
- **Bucket**: `mcp-langgraph-tfstate`
- **Encryption**: Google-managed or customer-managed keys (KMS)
- **Versioning**: Enabled for state history
- **Access**: Uniform bucket-level access
- **State Locking**: Automatic via GCS

**State file organization**:
- `env/dev/` - Development state
- `env/preview/` - Preview state
- `env/prod/` - Production state

## Security Best Practices

1. **Secrets Management**: Use Secret Manager, never commit secrets to version control
2. **IAM**: Follow least privilege principle for all service accounts
3. **Networking**: Private clusters with private IP for databases
4. **Encryption**: Enable encryption at rest and in transit for all services
5. **Logging**: Cloud Audit Logs and VPC Flow Logs enabled
6. **Workload Identity**: Use Workload Identity instead of service account keys
7. **Binary Authorization**: Enable for production workloads (optional)

## Validation and Preconditions

The infrastructure includes built-in validation:

- **API Prerequisites**: Modules validate that required APIs are enabled before resource creation
- **Feature Dependencies**: Backup agent requires backup plan to be enabled
- **Config Connector**: Cannot be used with fully private cluster endpoints
- **Input Validation**: Project IDs, regions, CIDR blocks are validated

If prerequisites are missing, you'll receive clear error messages with remediation steps.

## Cost Estimation

Use Terraform Cloud or Infracost for cost estimation:

```bash
# Using Infracost
brew install infracost
infracost breakdown --path terraform/environments/gcp-prod
```

**Estimated monthly costs** (us-central1):
- **Dev**: $300-500 (zonal cluster, BASIC Redis, no HA)
- **Staging**: $800-1,200 (regional cluster, HA databases, weekly backups)
- **Prod**: $2,000-3,500 (regional cluster, HA, daily backups, read replicas)

**Cost optimization tips**:
- Use dev environment for testing (zonal, BASIC tier Redis)
- Schedule cluster downtime for non-production environments
- Monitor with GCP Cost Management and set budgets

## Monitoring and Alerting

Each environment can enable monitoring alerts:

```hcl
enable_monitoring_alerts = true
monitoring_notification_channels = [
  "projects/PROJECT_ID/notificationChannels/CHANNEL_ID"
]
```

**Alerts configured**:
- GKE: Node CPU/memory, pod crash loops
- Cloud SQL: CPU, memory, disk usage, replication lag
- Memorystore: Memory usage, CPU, connection count

Create notification channels via GCP Console or gcloud:

```bash
gcloud alpha monitoring channels create \
  --display-name="Platform Team Email" \
  --type=email \
  --channel-labels=email_address=platform@example.com
```

## Cleanup

To destroy infrastructure (WARNING: irreversible):

```bash
# Disable deletion protection first (if enabled)
# Edit terraform.tfvars and set:
# enable_deletion_protection = false

# Re-apply to update protection settings
terraform apply

# Then destroy
terraform destroy
```

**Important**: Some resources (like Cloud SQL, backups) may have deletion protection enabled. You must disable it before destroying.

## Troubleshooting

### State Lock Issues

```bash
# View current state lock (if any)
gsutil cat gs://mcp-langgraph-tfstate/env/prod/default.tflock

# GCS state backend locks automatically timeout after 4 minutes
# Wait or contact the lock holder
```

### GKE Access Issues

```bash
# Update kubeconfig
gcloud container clusters get-credentials mcp-preview-gke \
  --region=us-central1 \
  --project=your-gcp-project-id

# Verify access
kubectl get nodes

# Check IAM permissions
gcloud projects get-iam-policy your-gcp-project-id \
  --flatten="bindings[].members" \
  --filter="bindings.members:user:your-email@example.com"
```

### API Enablement Errors

If you see "API not enabled" errors:

```bash
# Enable specific API
gcloud services enable gkebackup.googleapis.com --project=your-gcp-project-id

# Or let the gcp-project-services module enable it
# Ensure module.project_services is properly configured with enable_*_api = true
```

### Module Dependency Issues

If resources fail due to API timing:

```bash
# Sometimes APIs need time to propagate
# Wait 1-2 minutes and retry
terraform apply
```

## CI/CD Integration

Drift detection runs automatically:
- `.github/workflows/gcp-drift-detection.yaml` - Runs every 6 hours
- `.github/workflows/gcp-compliance-scan.yaml` - Validates compliance

**Recommended**: Add terraform validate to your PR workflow (see terraform-validate.yaml).

## Support

For issues or questions:
- Check module documentation in `modules/*/README.md` (if available)
- Review Terraform logs: `TF_LOG=DEBUG terraform plan`
- Consult GCP documentation:
  - [GKE Autopilot](https://cloud.google.com/kubernetes-engine/docs/concepts/autopilot-overview)
  - [Cloud SQL](https://cloud.google.com/sql/docs)
  - [Workload Identity](https://cloud.google.com/kubernetes-engine/docs/how-to/workload-identity)

## Related Documentation

- GKE Deployment Guide: See project docs
- Disaster Recovery: Cloud SQL and GKE backups configured
- Architecture Decision Records: See project ADRs
