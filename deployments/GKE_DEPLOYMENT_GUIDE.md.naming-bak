# MCP Server LangGraph - GCP GKE Deployment Guide

**Version**: 1.0
**Last Updated**: 2025-11-01
**Target Platform**: Google Cloud Platform (GCP) - Google Kubernetes Engine (GKE) Autopilot
**Estimated Deployment Time**: 2-3 hours

---

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Architecture](#architecture)
4. [Deployment Phases](#deployment-phases)
5. [Phase 1: Infrastructure Setup](#phase-1-infrastructure-setup)
6. [Phase 2: GKE Cluster Deployment](#phase-2-gke-cluster-deployment)
7. [Phase 3: Application Deployment](#phase-3-application-deployment)
8. [Phase 4: Security Hardening](#phase-4-security-hardening)
9. [Phase 5: Observability](#phase-5-observability)
10. [Verification & Testing](#verification--testing)
11. [Troubleshooting](#troubleshooting)
12. [Cost Optimization](#cost-optimization)

---

## Overview

This guide provides step-by-step instructions for deploying MCP Server LangGraph on Google Kubernetes Engine (GKE) Autopilot with production-grade security, observability, and high availability.

### What You'll Deploy

- **GKE Autopilot Cluster**: Fully managed Kubernetes cluster (regional, multi-zone)
- **Cloud SQL PostgreSQL**: High-availability database with automated backups
- **Memorystore Redis**: High-availability cache with persistence
- **Workload Identity**: Secure pod-to-GCP service authentication
- **Private Networking**: VPC-native with Cloud NAT
- **Observability**: Cloud Monitoring, Logging, Trace, Profiler
- **Security**: Binary Authorization, Network Policies, Encryption

### Key Benefits

- **40-60% cost savings** vs. traditional GKE (pay-per-pod with Autopilot)
- **99.9% uptime** with regional deployment
- **Zero node management** (Google manages everything)
- **Automatic security patching**
- **Built-in monitoring and logging**

---

## Prerequisites

### 1. GCP Account & Project

- **GCP Account** with billing enabled
- **GCP Project** created
- **Billing Account** linked to project

```bash
# Create project
gcloud projects create PROJECT_ID --name="MCP LangGraph Production"

# Link billing
gcloud billing projects link PROJECT_ID --billing-account=BILLING_ACCOUNT_ID

# Set active project
gcloud config set project PROJECT_ID
```

### 2. Required Tools

| Tool | Version | Installation |
|------|---------|--------------|
| **gcloud CLI** | Latest | `curl https://sdk.cloud.google.com \| bash` |
| **Terraform** | ≥ 1.5.0 | [terraform.io/downloads](https://terraform.io/downloads) |
| **kubectl** | ≥ 1.28 | `gcloud components install kubectl` |
| **kustomize** | ≥ 5.0 | `brew install kustomize` |

Verify installations:
```bash
gcloud version
terraform version
kubectl version --client
kustomize version
```

### 3. IAM Permissions

Required roles (or `roles/owner`):
- `roles/compute.networkAdmin`
- `roles/container.admin`
- `roles/cloudsql.admin`
- `roles/redis.admin`
- `roles/iam.securityAdmin`
- `roles/resourcemanager.projectIamAdmin`

### 4. Enable Required APIs

```bash
gcloud services enable \
    container.googleapis.com \
    compute.googleapis.com \
    sqladmin.googleapis.com \
    redis.googleapis.com \
    servicenetworking.googleapis.com \
    cloudresourcemanager.googleapis.com \
    iam.googleapis.com \
    binaryauthorization.googleapis.com \
    monitoring.googleapis.com \
    logging.googleapis.com \
    cloudtrace.googleapis.com \
    cloudprofiler.googleapis.com \
    secretmanager.googleapis.com \
    artifactregistry.googleapis.com \
    --project=PROJECT_ID
```

---

## Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                      Internet (Users/APIs)                           │
└────────────────────────────────┬────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    Cloud Load Balancer                               │
│                    (with Cloud Armor DDoS protection)                │
└────────────────────────────────┬────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      VPC (us-central1)                               │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │  GKE Autopilot Cluster (Regional - 3 Zones)                    │ │
│  │                                                                 │ │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐                     │ │
│  │  │  Zone A  │  │  Zone B  │  │  Zone C  │                     │ │
│  │  │  Pods    │  │  Pods    │  │  Pods    │                     │ │
│  │  └────┬─────┘  └────┬─────┘  └────┬─────┘                     │ │
│  │       │             │             │                            │ │
│  │       └─────────────┴─────────────┘                            │ │
│  │                     │                                           │ │
│  │                     │ Workload Identity                         │ │
│  │                     ▼                                           │ │
│  │       ┌─────────────────────────────────┐                      │ │
│  │       │  GCP Service Accounts           │                      │ │
│  │       │  - Cloud SQL access             │                      │ │
│  │       │  - Secret Manager access         │                      │ │
│  │       │  - Cloud Storage access          │                      │ │
│  │       └─────────────────────────────────┘                      │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │  Cloud SQL PostgreSQL (Regional HA)                            │ │
│  │  - Primary: Zone A                                             │ │
│  │  - Replica: Zone B (automatic failover)                        │ │
│  │  - Read Replica: us-east1 (optional)                           │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │  Memorystore Redis (STANDARD_HA)                               │ │
│  │  - Primary: Zone A                                             │ │
│  │  - Replica: Zone B (automatic failover)                        │ │
│  │  - RDB snapshots every 12 hours                                │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │  Cloud NAT (2 Static IPs)                                      │ │
│  │  - Outbound internet access for private nodes                  │ │
│  └────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    Cloud Operations Suite                            │
│  - Cloud Monitoring (metrics + dashboards)                          │
│  - Cloud Logging (centralized logs)                                 │
│  - Cloud Trace (distributed tracing)                                │
│  - Cloud Profiler (performance profiling)                           │
│  - Error Reporting (error aggregation)                              │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Deployment Phases

| Phase | Description | Duration | Complexity |
|-------|-------------|----------|------------|
| **Phase 1** | Infrastructure Setup (Terraform backend, networking) | 30 min | Low |
| **Phase 2** | GKE Cluster Deployment (cluster, databases, cache) | 45 min | Medium |
| **Phase 3** | Application Deployment (Kustomize, pods, services) | 20 min | Low |
| **Phase 4** | Security Hardening (Binary Auth, policies) | 30 min | Medium |
| **Phase 5** | Observability (monitoring, logging, tracing) | 25 min | Medium |
| **Total** | | **2.5 hours** | |

---

## Phase 1: Infrastructure Setup

### Step 1.1: Create Terraform State Backend

```bash
cd terraform/backend-setup-gcp

# Create terraform.tfvars
cat > terraform.tfvars <<EOF
project_id    = "YOUR_PROJECT_ID"
region        = "us-central1"
bucket_prefix = "mcp-langgraph"
EOF

# Initialize and apply
terraform init
terraform plan
terraform apply -auto-approve

# Save bucket name
export TF_STATE_BUCKET=$(terraform output -raw terraform_state_bucket)
echo "State bucket: $TF_STATE_BUCKET"
```

**Expected Output**:
```
Apply complete! Resources: 2 added, 0 changed, 0 destroyed.

Outputs:
terraform_state_bucket = "mcp-langgraph-terraform-state-us-central1-abc123"
```

**Time**: ~5 minutes

### Step 1.2: Update Environment Configuration

```bash
cd terraform/environments/gcp-prod

# Update main.tf with actual bucket name
sed -i "s/bucket = \"mcp-langgraph-terraform-state-us-central1-XXXXX\"/bucket = \"$TF_STATE_BUCKET\"/g" main.tf

# Create terraform.tfvars
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars`:
```hcl
project_id  = "YOUR_PROJECT_ID"
region      = "us-central1"
team        = "platform"
cost_center = "engineering"

# Monitoring (create notification channels first)
monitoring_notification_channels = [
  # "projects/PROJECT_ID/notificationChannels/CHANNEL_ID",
]

# Security
enable_binary_authorization = false  # Enable after Phase 4
enable_private_endpoint     = false  # Set true for maximum security

# Optional: Authorize your IP for cluster access
master_authorized_networks_cidrs = [
  {
    cidr_block   = "YOUR_IP/32"
    display_name = "My IP"
  }
]
```

**Time**: ~5 minutes

---

## Phase 2: GKE Cluster Deployment

### Step 2.1: Initialize Terraform

```bash
cd terraform/environments/gcp-prod

terraform init
```

**Expected Output**:
```
Initializing modules...
Initializing the backend...
Terraform has been successfully initialized!
```

### Step 2.2: Review Deployment Plan

```bash
terraform plan -out=tfplan
```

Review the plan carefully. It should create:
- 1 VPC network
- 1 subnet with secondary ranges
- 1 Cloud Router
- 1 Cloud NAT
- 2 NAT IPs
- 1 GKE Autopilot cluster
- 1 Cloud SQL instance (PostgreSQL 15, regional HA)
- 1 Memorystore instance (Redis 7.0, STANDARD_HA)
- Multiple service accounts for Workload Identity
- IAM bindings
- Firewall rules
- Monitoring alerts

**Time**: ~2 minutes

### Step 2.3: Deploy Infrastructure

```bash
terraform apply tfplan
```

**Expected Duration**: ~20-25 minutes

**What happens**:
1. VPC and networking (2 min)
2. Cloud SQL instance (10-12 min)
3. Memorystore instance (5-7 min)
4. GKE cluster (8-10 min)
5. Workload Identity (1 min)

**Expected Output**:
```
Apply complete! Resources: 25+ added, 0 changed, 0 destroyed.

Outputs:
cluster_name = "mcp-prod-gke"
kubectl_config_command = "gcloud container clusters get-credentials..."
cloudsql_connection_name = "PROJECT_ID:us-central1:mcp-prod-postgres"
redis_host = "10.x.x.x"
```

### Step 2.4: Configure kubectl

```bash
# Get credentials
eval $(terraform output -raw kubectl_config_command)

# Verify access
kubectl cluster-info
kubectl get nodes
kubectl get namespaces
```

**Expected Output**:
```
Kubernetes control plane is running at https://X.X.X.X
CoreDNS is running at https://X.X.X.X/api/v1/namespaces/kube-system/services/kube-dns:dns/proxy

NAME              STATUS   AGE
default           Active   5m
kube-node-lease   Active   5m
kube-public       Active   5m
kube-system       Active   5m
```

**Time**: ~25 minutes (total for Phase 2)

---

## Phase 3: Application Deployment

### Step 3.1: Create Secrets in Secret Manager

```bash
PROJECT_ID="YOUR_PROJECT_ID"

# Create secrets
gcloud secrets create mcp-production-secrets \
  --replication-policy="automatic" \
  --project="$PROJECT_ID"

# Add secret data (create a JSON file with all secrets)
cat > /tmp/secrets.json <<EOF
{
  "anthropic_api_key": "sk-ant-...",
  "google_api_key": "AIza...",
  "openai_api_key": "sk-proj-...",
  "jwt_secret": "$(openssl rand -base64 32)",
  "api_key": "$(openssl rand -base64 32)",
  "postgres_database": "mcp_langgraph",
  "postgres_user": "postgres",
  "postgres_password": "$(terraform output -raw cloudsql_user_password)",
  "cloudsql_connection_name": "$(terraform output -raw cloudsql_connection_name)",
  "redis_host": "$(terraform output -raw redis_host)",
  "redis_port": "$(terraform output -raw redis_port)",
  "redis_password": "$(terraform output -raw redis_auth_string)",
  "keycloak_admin_password": "$(openssl rand -base64 24)",
  "keycloak_db_password": "$(openssl rand -base64 24)",
  "openfga_preshared_key": "$(openssl rand -base64 32)"
}
EOF

# Upload secrets
gcloud secrets versions add mcp-production-secrets \
  --data-file=/tmp/secrets.json \
  --project="$PROJECT_ID"

# Secure cleanup
rm -f /tmp/secrets.json

log_info "✅ Secrets created"
```

### Step 3.2: Install External Secrets Operator

```bash
# Add Helm repo
helm repo add external-secrets https://charts.external-secrets.io
helm repo update

# Install operator
helm install external-secrets \
  external-secrets/external-secrets \
  --namespace external-secrets-system \
  --create-namespace \
  --set installCRDs=true

# Wait for operator to be ready
kubectl wait --for=condition=ready pod \
  -l app.kubernetes.io/name=external-secrets \
  -n external-secrets-system \
  --timeout=120s
```

### Step 3.3: Deploy Application

```bash
cd deployments/overlays/production-gke

# Update kustomization.yaml with your project ID
sed -i "s/PROJECT_ID/$PROJECT_ID/g" kustomization.yaml
sed -i "s/PROJECT_ID/$PROJECT_ID/g" external-secrets.yaml
sed -i "s/PROJECT_ID/$PROJECT_ID/g" serviceaccount-patch.yaml
sed -i "s/PROJECT_ID/$PROJECT_ID/g" otel-collector-config.yaml
sed -i "s/YOUR_PROJECT_ID/$PROJECT_ID/g" configmap-patch.yaml

# Apply with Kustomize
kubectl apply -k .

# Watch rollout
kubectl rollout status deployment/production-mcp-server-langgraph \
  -n mcp-production \
  --timeout=10m
```

**Expected Output**:
```
namespace/mcp-production created
serviceaccount/production-mcp-server-langgraph created
deployment.apps/production-mcp-server-langgraph created
service/production-mcp-server-langgraph created
horizontalpodautoscaler.autoscaling/production-mcp-server-langgraph created
poddisruptionbudget.policy/mcp-server-langgraph-pdb created

Waiting for deployment "production-mcp-server-langgraph" rollout to finish...
deployment "production-mcp-server-langgraph" successfully rolled out
```

### Step 3.4: Verify Deployment

```bash
# Check pods
kubectl get pods -n mcp-production

# Check services
kubectl get svc -n mcp-production

# View logs
kubectl logs -n mcp-production -l app=mcp-server-langgraph --tail=50

# Test health endpoint
kubectl port-forward -n mcp-production svc/production-mcp-server-langgraph 8000:8000 &
curl http://localhost:8000/health/live
curl http://localhost:8000/health/ready
```

**Time**: ~20 minutes (total for Phase 3)

---

## Phase 4: Security Hardening

### Step 4.1: Set Up Binary Authorization

```bash
# Run setup script
./deployments/security/binary-authorization/setup-binary-auth.sh \
  PROJECT_ID \
  production

# Enable in cluster (update terraform.tfvars)
cd terraform/environments/gcp-prod
```

Edit `terraform.tfvars`:
```hcl
enable_binary_authorization = true
```

Apply changes:
```bash
terraform apply -auto-approve
```

### Step 4.2: Sign Container Images

```bash
# Sign production images
IMAGE_URL="us-central1-docker.pkg.dev/PROJECT_ID/mcp-production/mcp-server-langgraph:2.8.0"

./deployments/security/binary-authorization/sign-image.sh \
  PROJECT_ID \
  production \
  "$IMAGE_URL"
```

### Step 4.3: Configure Network Policies

Network policies are already included in the production overlay (`network-policy.yaml`).

Verify:
```bash
kubectl get networkpolicies -n mcp-production
```

### Step 4.4: Enable Private Endpoint (Optional - Maximum Security)

**Warning**: This makes the cluster control plane only accessible via VPC.

Edit `terraform.tfvars`:
```hcl
enable_private_endpoint = true
```

Apply:
```bash
terraform apply -auto-approve
```

Access cluster:
```bash
# From within VPC (bastion host or Cloud Shell)
gcloud container clusters get-credentials mcp-prod-gke \
  --region=us-central1 \
  --internal-ip
```

**Time**: ~30 minutes (total for Phase 4)

---

## Phase 5: Observability

### Step 5.1: Verify Cloud Logging

```bash
# Check logs are flowing
gcloud logging read \
  'resource.type="k8s_container" AND resource.labels.namespace_name="mcp-production"' \
  --limit=20 \
  --project=PROJECT_ID
```

### Step 5.2: Verify Cloud Monitoring

```bash
# List metrics
gcloud monitoring time-series list \
  --filter='resource.type="k8s_container" AND resource.labels.namespace_name="mcp-production"' \
  --project=PROJECT_ID \
  --format=json \
  --limit=5
```

### Step 5.3: View in Cloud Console

Open dashboards:
- **GKE**: https://console.cloud.google.com/kubernetes/workload/overview?project=PROJECT_ID
- **Cloud Logging**: https://console.cloud.google.com/logs?project=PROJECT_ID
- **Cloud Monitoring**: https://console.cloud.google.com/monitoring?project=PROJECT_ID
- **Cloud Trace**: https://console.cloud.google.com/traces?project=PROJECT_ID

**Time**: ~10 minutes (total for Phase 5)

---

## Verification & Testing

### Health Checks

```bash
# Get service endpoint (if LoadBalancer)
SERVICE_IP=$(kubectl get svc production-mcp-server-langgraph \
  -n mcp-production \
  -o jsonpath='{.status.loadBalancer.ingress[0].ip}')

# Or port-forward
kubectl port-forward -n mcp-production \
  svc/production-mcp-server-langgraph 8000:8000 &

# Test endpoints
curl http://localhost:8000/health/live     # Should return 200
curl http://localhost:8000/health/ready    # Should return 200
curl http://localhost:8000/health/startup  # Should return 200
```

### Database Connectivity

```bash
# Test Cloud SQL connection
kubectl exec -it -n mcp-production \
  $(kubectl get pod -n mcp-production -l app=mcp-server-langgraph -o jsonpath='{.items[0].metadata.name}') \
  -c cloud-sql-proxy \
  -- wget -qO- http://localhost:9801/readiness

# Should return: ok
```

### Redis Connectivity

```bash
# Check Redis from application pod
kubectl exec -it -n mcp-production \
  $(kubectl get pod -n mcp-production -l app=mcp-server-langgraph -o jsonpath='{.items[0].metadata.name}') \
  -- sh -c 'echo PING | nc $REDIS_HOST $REDIS_PORT'

# Should return: +PONG
```

### Workload Identity

```bash
# Verify service account annotation
kubectl get sa production-mcp-server-langgraph \
  -n mcp-production \
  -o jsonpath='{.metadata.annotations.iam\.gke\.io/gcp-service-account}'

# Should show: mcp-prod-app-sa@PROJECT_ID.iam.gserviceaccount.com
```

---

## Troubleshooting

### Issue: Pods stuck in Pending

**Symptoms**: Pods show `Pending` status

**Diagnosis**:
```bash
kubectl describe pod POD_NAME -n mcp-production
```

**Common Causes**:
1. **Resource requests too high**: Autopilot provisions nodes automatically, but there are limits
   - Solution: Reduce CPU/memory requests
   - Check: `cluster_resource_limits` in Terraform

2. **Image pull errors**: Can't pull from Artifact Registry
   - Solution: Verify Workload Identity permissions
   - Check: `kubectl get events -n mcp-production`

3. **Binary Authorization blocking**: Image not signed
   - Solution: Sign the image
   - Check: `gcloud logging read 'protoPayload.serviceName="binaryauthorization.googleapis.com"'`

### Issue: Can't access Cloud SQL

**Symptoms**: Connection timeout to PostgreSQL

**Diagnosis**:
```bash
# Check Cloud SQL Proxy logs
kubectl logs -n mcp-production POD_NAME -c cloud-sql-proxy

# Check private service connection
gcloud services vpc-peerings list --network=mcp-prod-vpc
```

**Solution**:
1. Verify private service connection exists
2. Check firewall rules allow traffic
3. Verify Cloud SQL instance is running
4. Check Cloud SQL Proxy configuration

### Issue: Workload Identity not working

**Symptoms**: Permission denied errors accessing GCP services

**Diagnosis**:
```bash
# Check service account annotation
kubectl get sa -n mcp-production production-mcp-server-langgraph -o yaml

# Check IAM binding
gcloud iam service-accounts get-iam-policy \
  mcp-prod-app-sa@PROJECT_ID.iam.gserviceaccount.com
```

**Solution**:
1. Verify annotation: `iam.gke.io/gcp-service-account`
2. Verify IAM binding exists
3. Wait 1-2 minutes for propagation

---

## Cost Optimization

### Expected Costs (Monthly)

**Production Environment**:
| Component | Configuration | Cost/Month |
|-----------|---------------|------------|
| GKE Autopilot | ~25 pods (500m CPU, 1GB RAM avg) | $360 |
| Cloud SQL | 4 vCPU, 15GB RAM, HA, 1 replica | $280 |
| Memorystore | 5GB Redis HA | $220 |
| Networking | NAT, egress | $60 |
| Monitoring/Logging | Standard retention | $50 |
| **Total** | | **$970/month** |

**Cost Savings**:
- vs. Standard GKE: **$400-500/month saved** (40-50%)
- vs. VM-based: **$800-1000/month saved** (55-65%)

### Optimization Tips

1. **Right-size pod resources**:
   ```yaml
   resources:
     requests:
       cpu: 250m      # Start small
       memory: 512Mi  # Monitor actual usage
   ```

2. **Use committed use discounts**:
   ```bash
   # 1-year commitment: 25% discount
   # 3-year commitment: 52% discount
   ```

3. **Enable cost allocation**:
   ```hcl
   enable_cost_allocation = true
   ```

4. **Monitor with budgets**:
   ```bash
   gcloud billing budgets create \
     --billing-account=BILLING_ACCOUNT_ID \
     --display-name="MCP Production Budget" \
     --budget-amount=1200USD \
     --threshold-rule=percent=50 \
     --threshold-rule=percent=90
   ```

---

## Next Steps

After deployment:

1. **Set up CI/CD**: Configure GitHub Actions for automated deployments
2. **Enable Binary Authorization**: Sign images in CI/CD pipeline
3. **Configure monitoring**: Create custom dashboards and alerts
4. **Set up backups**: Verify automated backups are running
5. **Load testing**: Test with production-like traffic
6. **Document runbooks**: Create operational procedures
7. **Disaster recovery**: Test failover and recovery procedures

---

## Support

For issues or questions:

1. **Check documentation**: Review module READMEs in `terraform/modules/`
2. **Check logs**: View Cloud Logging for errors
3. **GCP Support**: https://cloud.google.com/support
4. **Project issues**: https://github.com/vishnu2kmohan/mcp-server-langgraph/issues

---

## Appendix

### A. Useful Commands

```bash
# View all resources
kubectl get all -n mcp-production

# Scale deployment manually
kubectl scale deployment production-mcp-server-langgraph \
  -n mcp-production \
  --replicas=5

# View resource usage
kubectl top pods -n mcp-production
kubectl top nodes

# Export configuration
kubectl get deployment production-mcp-server-langgraph \
  -n mcp-production \
  -o yaml > deployment-backup.yaml

# Rollback deployment
kubectl rollout undo deployment/production-mcp-server-langgraph \
  -n mcp-production
```

### B. Terraform Commands

```bash
# View outputs
terraform output

# View specific output
terraform output -raw cluster_name

# Refresh state
terraform refresh

# Import existing resource
terraform import module.gke.google_container_cluster.autopilot projects/PROJECT_ID/locations/us-central1/clusters/CLUSTER_NAME
```

### C. Cost Tracking

```bash
# View project costs
gcloud billing accounts list

# Export billing to BigQuery
gcloud beta billing accounts describe BILLING_ACCOUNT_ID

# View cost breakdown
# Go to: https://console.cloud.google.com/billing/BILLING_ACCOUNT_ID/reports
```

---

**End of Deployment Guide**

**Next Document**: [Operational Runbooks](./GKE_OPERATIONAL_RUNBOOKS.md)
