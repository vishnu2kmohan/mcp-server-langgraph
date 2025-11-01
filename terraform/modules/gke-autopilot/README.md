# GKE Autopilot Terraform Module

Production-ready Google Kubernetes Engine (GKE) Autopilot cluster with comprehensive security, observability, and best practices built-in.

## GKE Autopilot vs Standard

**GKE Autopilot** is a fully managed, hands-off Kubernetes experience:

| Feature | Autopilot | Standard |
|---------|-----------|----------|
| **Node Management** | Fully automated | Manual |
| **Pricing** | Pay per pod (CPU, memory) | Pay per node |
| **Security** | Hardened by default | Manual configuration |
| **Upgrades** | Automatic | Manual or scheduled |
| **Scaling** | Automatic | Manual or cluster autoscaler |
| **Best For** | Most workloads, reduced ops | Custom node configs, GPUs |

**When to use Autopilot:**
- Want hands-off Kubernetes management ✅
- Cost optimization (pay only for pods) ✅
- Security and compliance requirements ✅
- Standard workloads (web apps, APIs, batch jobs) ✅

**When to use Standard:**
- Need specific node machine types
- Require GPUs or custom hardware
- Need node-level customization (sysctls, kernel modules)
- Windows containers

## Features

### Core Features
- **Fully Managed Nodes** - Google manages all node infrastructure
- **Workload Identity** - GCP's IAM-based service account authentication (like AWS IRSA)
- **VPC-Native Networking** - Alias IP ranges for pods and services
- **Regional or Zonal** - High availability with regional clusters
- **Private Cluster Support** - Private nodes and/or private endpoint

### Security
- **Binary Authorization** - Image signing and verification
- **GKE Security Posture** - Automated vulnerability scanning
- **Shielded Nodes** - Secure Boot, vTPM (automatic in Autopilot)
- **Workload Identity** - Pod-level service account binding
- **Network Policy** - Pod-to-pod traffic control
- **Private Google Access** - Access Google APIs without public IPs

### Observability
- **Cloud Monitoring** - Metrics for system components and workloads
- **Cloud Logging** - Centralized log aggregation
- **Managed Prometheus** - Prometheus-compatible metrics
- **Dataplane V2 Observability** - eBPF-based network insights
- **Log Export** - Export to BigQuery for analysis
- **Alert Policies** - Pre-configured monitoring alerts

### Cost Optimization
- **Pay-per-Pod Pricing** - Only pay for pod resources
- **Autoscaling** - Automatic cluster and pod scaling
- **Cost Allocation** - Track costs by namespace/label
- **Resource Limits** - Set cluster-wide CPU/memory caps

### Backup & DR
- **GKE Backup** - Automated backup and restore
- **Fleet Registration** - Multi-cluster management with Anthos
- **Multi-Region** - Deploy across regions for HA

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    GKE Autopilot Cluster                        │
│                   (Google-Managed Nodes)                        │
│                                                                 │
│  ┌────────────────────────────────────────────────────────────┐│
│  │  Control Plane (Master)                                    ││
│  │  - Kubernetes API Server                                   ││
│  │  - Private IP: 172.16.0.0/28                               ││
│  │  - Workload Identity: ENABLED                              ││
│  │  - Binary Authorization: OPTIONAL                          ││
│  └────────────────────────────────────────────────────────────┘│
│                                                                 │
│  ┌────────────────────────────────────────────────────────────┐│
│  │  Worker Nodes (Autopilot-Managed)                          ││
│  │  - Auto-provisioned based on pod requests                  ││
│  │  - Auto-upgraded and patched                               ││
│  │  - Shielded GKE nodes (Secure Boot, vTPM)                  ││
│  │  - Dataplane V2 (eBPF networking)                          ││
│  └────────────────────────────────────────────────────────────┘│
│                                                                 │
│  ┌────────────────────────────────────────────────────────────┐│
│  │  Networking                                                ││
│  │  - VPC-Native (Alias IPs)                                  ││
│  │  - Pods: 10.4.0.0/14                                       ││
│  │  - Services: 10.8.0.0/20                                   ││
│  │  - Network Policy: ENABLED                                 ││
│  └────────────────────────────────────────────────────────────┘│
│                                                                 │
│  ┌────────────────────────────────────────────────────────────┐│
│  │  Observability                                             ││
│  │  - Cloud Monitoring (system + workloads)                   ││
│  │  - Cloud Logging (system + workloads)                      ││
│  │  - Managed Prometheus                                      ││
│  │  - Alert Policies                                          ││
│  └────────────────────────────────────────────────────────────┘│
│                                                                 │
│  ┌────────────────────────────────────────────────────────────┐│
│  │  Addons                                                    ││
│  │  - HTTP Load Balancing                                     ││
│  │  - Horizontal Pod Autoscaler                               ││
│  │  - Vertical Pod Autoscaler                                 ││
│  │  - NodeLocal DNSCache                                      ││
│  │  - GCE Persistent Disk CSI                                 ││
│  └────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

## Usage

### Basic Example (Development)

```hcl
module "gke" {
  source = "./terraform/modules/gke-autopilot"

  project_id   = "my-project"
  cluster_name = "dev-cluster"
  region       = "us-central1"

  # Network (from VPC module)
  network_name        = module.vpc.network_name
  subnet_name         = module.vpc.nodes_subnet_name
  pods_range_name     = module.vpc.pods_range_name
  services_range_name = module.vpc.services_range_name

  # Development settings
  regional_cluster        = false  # Zonal for cost savings
  zone                    = "us-central1-a"
  enable_private_endpoint = false  # Allow public access
  release_channel         = "REGULAR"
}
```

### Production Example (All Features)

```hcl
module "gke" {
  source = "./terraform/modules/gke-autopilot"

  project_id   = "my-project"
  cluster_name = "prod-cluster"
  region       = "us-central1"

  # Network configuration
  network_name        = module.vpc.network_name
  subnet_name         = module.vpc.nodes_subnet_name
  pods_range_name     = module.vpc.pods_range_name
  services_range_name = module.vpc.services_range_name

  # High Availability
  regional_cluster = true  # Multi-zone

  # Private cluster (maximum security)
  enable_private_nodes    = true
  enable_private_endpoint = false  # Set to true for fully private
  master_ipv4_cidr_block  = "172.16.0.0/28"

  # Control plane access
  enable_master_authorized_networks = true
  master_authorized_networks_cidrs = [
    {
      cidr_block   = "10.0.0.0/8"  # Internal VPC
      display_name = "VPC"
    },
    {
      cidr_block   = "203.0.113.0/24"  # Office IP
      display_name = "Office"
    }
  ]

  # Release channel (STABLE for production)
  release_channel = "STABLE"

  # Maintenance window (3 AM UTC)
  maintenance_start_time = "03:00"

  # Cluster resource limits
  cluster_resource_limits = [
    {
      resource_type = "cpu"
      minimum       = 4
      maximum       = 1000
    },
    {
      resource_type = "memory"
      minimum       = 16
      maximum       = 10000
    }
  ]

  # Security
  enable_binary_authorization        = true
  binary_authorization_evaluation_mode = "PROJECT_SINGLETON_POLICY_ENFORCE"
  enable_security_posture            = true
  security_posture_mode              = "ENTERPRISE"
  security_posture_vulnerability_mode = "VULNERABILITY_ENTERPRISE"

  # Networking
  enable_dataplane_v2   = true
  enable_network_policy = true

  # Observability
  monitoring_enabled_components = ["SYSTEM_COMPONENTS", "WORKLOADS"]
  logging_enabled_components    = ["SYSTEM_COMPONENTS", "WORKLOADS"]
  enable_managed_prometheus     = true

  enable_advanced_datapath_observability = true
  datapath_observability_relay_mode      = "INTERNAL_VPC_LB"

  # Log export to BigQuery
  enable_log_export     = true
  log_export_dataset_id = "gke_logs"

  # Monitoring alerts
  enable_monitoring_alerts          = true
  monitoring_notification_channels = [
    "projects/my-project/notificationChannels/1234567890"
  ]

  # Backup
  enable_backup_plan          = true
  backup_schedule_cron        = "0 2 * * *"  # 2 AM daily
  backup_retain_days          = 30
  backup_delete_lock_days     = 7
  backup_include_volume_data  = true
  backup_include_secrets      = false
  backup_namespace            = "*"

  # Fleet registration (for Anthos)
  enable_fleet_registration = true

  # Cost management
  enable_cost_allocation = true

  # Addons
  enable_http_load_balancing           = true
  enable_horizontal_pod_autoscaling    = true
  enable_vertical_pod_autoscaling      = true
  enable_dns_cache                     = true
  enable_gce_persistent_disk_csi_driver = true
  enable_gcs_fuse_csi_driver           = true
  enable_config_connector              = false

  # Gateway API (advanced ingress)
  enable_gateway_api   = true
  gateway_api_channel  = "CHANNEL_STANDARD"

  # Notifications
  notification_config_topic = "projects/my-project/topics/gke-notifications"

  # Protection
  enable_deletion_protection = true

  # Labels
  labels = {
    environment = "production"
    team        = "platform"
    cost_center = "engineering"
    compliance  = "soc2"
  }
}
```

### With VPC Module

```hcl
# VPC
module "vpc" {
  source = "./terraform/modules/gcp-vpc"

  project_id   = var.project_id
  name_prefix  = "mcp-prod"
  region       = "us-central1"
  cluster_name = "mcp-prod-cluster"

  nodes_cidr    = "10.0.0.0/20"
  pods_cidr     = "10.4.0.0/14"
  services_cidr = "10.8.0.0/20"

  enable_private_service_connection = true
}

# GKE Autopilot
module "gke" {
  source = "./terraform/modules/gke-autopilot"

  project_id   = var.project_id
  cluster_name = "mcp-prod-cluster"
  region       = "us-central1"

  # Use VPC module outputs
  network_name        = module.vpc.network_name
  subnet_name         = module.vpc.nodes_subnet_name
  pods_range_name     = module.vpc.pods_range_name
  services_range_name = module.vpc.services_range_name

  regional_cluster        = true
  enable_private_nodes    = true
  enable_private_endpoint = false

  release_channel = "STABLE"

  enable_binary_authorization = true
  enable_security_posture     = true
  enable_dataplane_v2         = true
  enable_managed_prometheus   = true

  labels = {
    environment = "production"
    managed_by  = "terraform"
  }
}
```

## Workload Identity (GCP's IRSA)

Workload Identity allows Kubernetes pods to authenticate as GCP service accounts.

### Setup

1. **Enable Workload Identity** (automatic in this module):
```hcl
# Enabled by default in the module
workload_identity_enabled = true
```

2. **Create IAM bindings** (use the workload-identity module):
```hcl
module "workload_identity" {
  source = "./terraform/modules/gke-workload-identity"

  project_id = var.project_id
  namespace  = "default"

  service_accounts = {
    "app-sa" = {
      gcp_sa_name = "app-service-account"
      roles       = [
        "roles/storage.objectViewer",
        "roles/secretmanager.secretAccessor"
      ]
    }
  }
}
```

3. **Use in Kubernetes**:
```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: app-sa
  namespace: default
  annotations:
    iam.gke.io/gcp-service-account: app-service-account@PROJECT_ID.iam.gserviceaccount.com
---
apiVersion: v1
kind: Pod
metadata:
  name: app
spec:
  serviceAccountName: app-sa
  containers:
  - name: app
    image: gcr.io/PROJECT_ID/app:latest
```

Pods will automatically authenticate as the GCP service account.

## Binary Authorization

Enforce image signing policies before deployment.

### Enable Binary Authorization

```hcl
enable_binary_authorization          = true
binary_authorization_evaluation_mode = "PROJECT_SINGLETON_POLICY_ENFORCE"
```

### Create Policy

```bash
# Create attestor
gcloud container binauthz attestors create prod-attestor \
  --project=PROJECT_ID \
  --attestation-authority-note=prod-note \
  --attestation-authority-note-project=PROJECT_ID

# Create policy
cat <<EOF > policy.yaml
admissionWhitelistPatterns:
- namePattern: gcr.io/PROJECT_ID/*
defaultAdmissionRule:
  requireAttestationsBy:
  - projects/PROJECT_ID/attestors/prod-attestor
  evaluationMode: REQUIRE_ATTESTATION
  enforcementMode: ENFORCED_BLOCK_AND_AUDIT_LOG
EOF

gcloud container binauthz policy import policy.yaml
```

### Sign Images

```bash
# Sign image during CI/CD
gcloud container binauthz attestations sign-and-create \
  --artifact-url=gcr.io/PROJECT_ID/app:v1.0.0 \
  --attestor=prod-attestor \
  --attestor-project=PROJECT_ID \
  --keyversion-project=PROJECT_ID \
  --keyversion-location=us-central1 \
  --keyversion-keyring=binauthz \
  --keyversion-key=attestor-key \
  --keyversion=1
```

## Security Best Practices

### 1. Private Cluster

```hcl
enable_private_nodes    = true   # Nodes have no public IPs
enable_private_endpoint = true   # Control plane only accessible via VPC
```

**Access private endpoint:**
```bash
# From within VPC (bastion or VPN)
gcloud container clusters get-credentials CLUSTER_NAME --region=REGION

# Or use Cloud Identity-Aware Proxy
gcloud container clusters get-credentials CLUSTER_NAME --region=REGION --internal-ip
```

### 2. Master Authorized Networks

```hcl
enable_master_authorized_networks = true
master_authorized_networks_cidrs = [
  {
    cidr_block   = "10.0.0.0/8"
    display_name = "Internal VPC"
  }
]
```

### 3. Network Policies

```hcl
enable_network_policy = true
enable_dataplane_v2   = true  # eBPF for better performance
```

**Example Network Policy:**
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: deny-all-ingress
spec:
  podSelector: {}
  policyTypes:
  - Ingress
```

### 4. Security Posture

```hcl
enable_security_posture             = true
security_posture_mode               = "ENTERPRISE"
security_posture_vulnerability_mode = "VULNERABILITY_ENTERPRISE"
```

View security insights:
```bash
gcloud container clusters describe CLUSTER_NAME \
  --region=REGION \
  --format="value(securityPostureConfig)"
```

## Cost Optimization

### Autopilot Pricing

**Pay only for pod resources** (CPU, memory, ephemeral storage):
- vCPU: $0.048/hour
- Memory: $0.0053/GB/hour
- Storage: $0.000137/GB/hour

### Resource Requests

Autopilot bills based on pod resource requests. Optimize by:

```yaml
# Before optimization
resources:
  requests:
    cpu: 1000m      # $35/month
    memory: 2Gi     # $8/month
  # Total: $43/month

# After optimization
resources:
  requests:
    cpu: 250m       # $9/month
    memory: 512Mi   # $2/month
  # Total: $11/month (74% savings!)
```

### Cluster Resource Limits

Set cluster-wide limits to prevent runaway costs:

```hcl
cluster_resource_limits = [
  {
    resource_type = "cpu"
    minimum       = 1
    maximum       = 100  # Cap at 100 vCPUs
  },
  {
    resource_type = "memory"
    minimum       = 4
    maximum       = 1000  # Cap at 1000 GB
  }
]
```

### Cost Allocation

Track costs by namespace/label:

```hcl
enable_cost_allocation = true
```

View costs:
```bash
gcloud container clusters describe CLUSTER_NAME \
  --region=REGION \
  --format="value(costManagementConfig.enabled)"
```

## Monitoring & Logging

### Cloud Monitoring

Automatic collection of:
- **System components**: API server, scheduler, controller manager
- **Workloads**: Your application metrics

```hcl
monitoring_enabled_components = ["SYSTEM_COMPONENTS", "WORKLOADS"]
enable_managed_prometheus     = true
```

### Cloud Logging

Centralized logs:
```hcl
logging_enabled_components = ["SYSTEM_COMPONENTS", "WORKLOADS"]
```

Query logs:
```bash
gcloud logging read "resource.type=k8s_cluster AND resource.labels.cluster_name=CLUSTER_NAME"
```

### Export to BigQuery

```hcl
enable_log_export     = true
log_export_dataset_id = "gke_logs"
```

Query in BigQuery:
```sql
SELECT
  timestamp,
  jsonPayload.message
FROM
  `PROJECT_ID.gke_logs.k8s_cluster_*`
WHERE
  resource.labels.cluster_name = 'CLUSTER_NAME'
ORDER BY
  timestamp DESC
LIMIT 100
```

### Alert Policies

Pre-configured alerts:
- Cluster upgrade available
- High CPU usage (>80%)

Add custom alerts via `monitoring_notification_channels`.

## Backup & Restore

### Enable Backups

```hcl
enable_backup_plan         = true
backup_schedule_cron       = "0 2 * * *"  # Daily at 2 AM
backup_retain_days         = 30
backup_include_volume_data = true
```

### Restore from Backup

```bash
# List backups
gcloud container backup-restore backups list \
  --project=PROJECT_ID \
  --location=REGION \
  --backup-plan=CLUSTER_NAME-backup-plan

# Restore
gcloud container backup-restore restores create RESTORE_NAME \
  --project=PROJECT_ID \
  --location=REGION \
  --backup-plan=CLUSTER_NAME-backup-plan \
  --backup=BACKUP_NAME
```

## Accessing the Cluster

### Get Credentials

```bash
# Regional cluster
gcloud container clusters get-credentials CLUSTER_NAME \
  --region=REGION \
  --project=PROJECT_ID

# Zonal cluster
gcloud container clusters get-credentials CLUSTER_NAME \
  --zone=ZONE \
  --project=PROJECT_ID
```

### Verify Access

```bash
kubectl cluster-info
kubectl get nodes
kubectl get pods --all-namespaces
```

## Upgrading

Autopilot handles upgrades automatically based on the release channel.

### Release Channels

| Channel | Cadence | Use Case |
|---------|---------|----------|
| **RAPID** | Weekly | Testing, dev |
| **REGULAR** | Monthly | General use |
| **STABLE** | Quarterly | Production (recommended) |

### Manual Upgrade

```bash
# Check available versions
gcloud container get-server-config --region=REGION

# Upgrade (if needed)
gcloud container clusters upgrade CLUSTER_NAME \
  --region=REGION \
  --cluster-version=VERSION
```

## Troubleshooting

### Issue: Can't access private endpoint

**Error:** Unable to connect to the server: dial tcp: lookup X.X.X.X: no such host

**Solution:**
```bash
# Enable private endpoint access from Cloud Shell or compute instance
gcloud container clusters get-credentials CLUSTER_NAME \
  --region=REGION \
  --internal-ip
```

### Issue: Pod stuck in Pending

**Cause:** Resource requests too high or cluster at resource limit

**Solution:**
```bash
# Check pod events
kubectl describe pod POD_NAME

# Check cluster resource usage
kubectl top nodes

# Increase cluster resource limits
# Update cluster_resource_limits in Terraform
```

### Issue: Image pull errors with Binary Authorization

**Error:** denied by Binary Authorization

**Solution:**
```bash
# Check attestation
gcloud container binauthz attestations list \
  --attestor=ATTESTOR_NAME \
  --artifact-url=IMAGE_URL

# Sign image
gcloud container binauthz attestations sign-and-create \
  --artifact-url=IMAGE_URL \
  --attestor=ATTESTOR_NAME
```

## Inputs

See [variables.tf](./variables.tf) for complete list (80+ variables).

Key inputs:
- `project_id` - GCP project ID
- `cluster_name` - Cluster name
- `region` - GCP region
- `network_name` - VPC network name
- `subnet_name` - Subnet name
- `pods_range_name` - Pods secondary IP range name
- `services_range_name` - Services secondary IP range name

## Outputs

See [outputs.tf](./outputs.tf) for complete list.

Key outputs:
- `cluster_id` - Cluster ID
- `cluster_endpoint` - API server endpoint
- `workload_identity_pool` - Workload Identity pool
- `kubectl_config_command` - Command to configure kubectl

## Examples

- [Development cluster](../../environments/gcp-dev/)
- [Production cluster](../../environments/gcp-prod/)

## References

- [GKE Autopilot Overview](https://cloud.google.com/kubernetes-engine/docs/concepts/autopilot-overview)
- [Workload Identity](https://cloud.google.com/kubernetes-engine/docs/how-to/workload-identity)
- [Binary Authorization](https://cloud.google.com/binary-authorization/docs)
- [GKE Security Posture](https://cloud.google.com/kubernetes-engine/docs/concepts/about-security-posture-dashboard)
