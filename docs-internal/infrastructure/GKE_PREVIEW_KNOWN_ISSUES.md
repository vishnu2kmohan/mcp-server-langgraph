# GKE Preview Environment - Known Issues and Solutions

**Created**: 2025-12-06
**Last Updated**: 2025-12-06
**Purpose**: Document all issues encountered during gke-preview-up/down testing for permanent resolution

---

## Issue #1: Workload Identity Federation Pool Soft-Delete Recovery

**Status: ✅ RESOLVED (Automated)**

### Symptom
```
Error 409: Requested entity already exists
```

When running `terraform apply` to create a WIF pool, Terraform fails because GCP has a 30-day soft-delete retention policy for WIF pools.

### Root Cause
GCP Workload Identity Pools are not immediately deleted - they enter a "DELETED" state for 30 days before permanent removal. Terraform cannot create a new pool with the same ID during this period.

### Solution (Automated in scripts/gcp/lib/common.sh)
The `gke-preview-up.sh` script now includes **fully automatic** WIF pool recovery via the `recover_soft_deleted_wif()` function. When a soft-deleted pool is detected, the script will:

1. Display a transparent warning banner explaining that a previously deleted pool was found
2. Automatically undelete the pool and provider
3. Import both resources into Terraform state

The user sees a clear warning message:

```bash
# Check if pool exists in DELETED state
if gcloud iam workload-identity-pools describe github-actions-pool \
    --location=global --project="$PROJECT_ID" 2>&1 | grep -q "DELETED"; then

    # Undelete the pool
    gcloud iam workload-identity-pools undelete github-actions-pool \
        --location=global --project="$PROJECT_ID"

    # Import into Terraform state
    terraform import 'module.github_actions_wif.google_iam_workload_identity_pool.github_actions' \
        "projects/$PROJECT_ID/locations/global/workloadIdentityPools/github-actions-pool"
fi
```

### Prevention
- Always use `gke-preview-down.sh` for teardown (handles state properly)
- If WIF pool is in DELETED state, script will auto-recover

---

## Issue #2: WIF Provider Soft-Delete Recovery

### Symptom
```
Error 409: Requested entity already exists (for WIF provider)
```

### Root Cause
Same as Issue #1 - WIF providers have the same 30-day soft-delete policy.

### Solution (Implemented)
The script now recovers WIF providers along with pools:

```bash
# Undelete provider
gcloud iam workload-identity-pools providers undelete github-actions-provider \
    --workload-identity-pool=github-actions-pool \
    --location=global --project="$PROJECT_ID"

# Import into Terraform
terraform import 'module.github_actions_wif.google_iam_workload_identity_pool_provider.github_actions' \
    "projects/$PROJECT_ID/locations/global/workloadIdentityPools/github-actions-pool/providers/github-actions-provider"
```

---

## Issue #3: Service Networking Connection Deletion Timing

### Symptom
```
Error code 9: Failed to delete connection; Producer services (e.g. CloudSQL, Cloud Memstore, etc.) are still using this connection.
```

### Root Cause
GCP Service Networking Connections have eventual consistency. After deleting CloudSQL or Memorystore instances, the connection metadata can take 5-15 minutes to fully release.

### Solution Options

#### Option A: Retry with Delay (Recommended for Scripts)
```bash
# In gke-preview-down.sh
delete_service_networking_connection() {
    local max_retries=3
    local retry_delay=120  # 2 minutes

    for ((i=1; i<=max_retries; i++)); do
        if terraform destroy -target='module.vpc.google_service_networking_connection.private_services[0]' -auto-approve; then
            return 0
        fi
        log_warn "Retry $i/$max_retries: Service Networking Connection not ready, waiting ${retry_delay}s..."
        sleep $retry_delay
    done

    log_warn "Service Networking Connection deletion deferred - will be cleaned up on next destroy"
    return 1
}
```

#### Option B: gcloud Direct Delete
```bash
gcloud services vpc-peerings delete \
    --network=preview-mcp-slg-vpc \
    --service=servicenetworking.googleapis.com \
    --project="$PROJECT_ID" \
    --quiet
```

#### Option C: Force VPC Peering Delete
```bash
gcloud compute networks peerings delete servicenetworking-googleapis-com \
    --network=preview-mcp-slg-vpc \
    --project="$PROJECT_ID" \
    --quiet
```

### Prevention
- Run CloudSQL/Redis destruction first, then wait before VPC cleanup
- Add retry logic with exponential backoff to teardown scripts
- Accept partial teardown as success if only VPC networking remains

---

## Issue #4: GKE Cluster Creation Error 400 (Invalid Argument)

### Symptom
```
Error 400: Request contains an invalid argument., badRequest
```

### Root Cause
Multiple possible causes:
1. Master CIDR conflicts with existing ranges
2. Secondary ranges not properly configured
3. Subnet not ready after VPC creation
4. Private cluster configuration issues

### Solution (Implemented in Terraform)
The GKE module now includes proper dependency chains:

```hcl
# In modules/gke-autopilot/main.tf
resource "google_container_cluster" "autopilot" {
  depends_on = [
    var.vpc_ready,           # Explicit VPC dependency
    var.subnet_ready,        # Wait for subnet
    var.private_services_ready  # Wait for private service connection
  ]

  # Use validated CIDR blocks
  private_cluster_config {
    master_ipv4_cidr_block = "172.16.0.0/28"  # Non-overlapping with VPC
  }
}
```

### Debugging Steps
1. Check VPC/subnet exist: `gcloud compute networks subnets list --project=PROJECT`
2. Check secondary ranges: `gcloud compute networks subnets describe SUBNET --region=REGION`
3. Check for CIDR conflicts: Ensure master CIDR doesn't overlap with any existing ranges

---

## Issue #5: Terraform State Lock Conflicts

### Symptom
```
Error: Error acquiring the state lock
```

### Root Cause
Parallel Terraform operations or crashed previous operations leave orphan locks.

### Solution
```bash
# Get lock ID from error message
terraform force-unlock -force LOCK_ID

# Then retry operation
terraform apply
```

### Prevention
- Never run parallel terraform operations
- Implement proper locking in scripts:
```bash
LOCKFILE="/tmp/gke-preview-terraform.lock"
exec 9>"$LOCKFILE"
if ! flock -n 9; then
    log_error "Another Terraform operation is in progress"
    exit 1
fi
```

---

## Issue #6: Orphaned GCP Resources After Partial Terraform Failure

### Symptom
Resources exist in GCP but not in Terraform state, causing drift.

### Root Cause
Terraform operation interrupted mid-apply, leaving some resources created but not tracked.

### Solution
The `gke-preview-down.sh` script includes orphan cleanup:

```bash
cleanup_orphaned_resources() {
    # Check for resources not in Terraform state

    # Orphaned GKE clusters
    if gcloud container clusters describe "$CLUSTER_NAME" --region="$REGION" &>/dev/null; then
        if ! terraform state show 'module.gke.google_container_cluster.autopilot' &>/dev/null; then
            gcloud container clusters delete "$CLUSTER_NAME" --region="$REGION" --quiet
        fi
    fi

    # Orphaned CloudSQL instances
    if gcloud sql instances describe "$CLOUD_SQL_INSTANCE" &>/dev/null; then
        if ! terraform state show 'module.cloudsql.google_sql_database_instance.main' &>/dev/null; then
            gcloud sql instances delete "$CLOUD_SQL_INSTANCE" --quiet
        fi
    fi

    # Orphaned Redis instances
    if gcloud redis instances describe "$REDIS_INSTANCE" --region="$REGION" &>/dev/null; then
        if ! terraform state show 'module.memorystore.google_redis_instance.main' &>/dev/null; then
            gcloud redis instances delete "$REDIS_INSTANCE" --region="$REGION" --quiet
        fi
    fi
}
```

### Prevention
- Use `gke-preview-down.sh --orphans-only` to clean orphans without full destroy
- Check resource status before running `gke-preview-up.sh`

---

## Recommended Teardown Order

To avoid dependency issues, destroy resources in this order:

1. **Kubernetes workloads** (if GKE exists)
2. **GKE cluster** (removes node pools, etc.)
3. **CloudSQL instance** (removes databases, users)
4. **Memorystore Redis** (removes replicas)
5. **Wait 2-3 minutes** (allow service networking to release)
6. **Service Networking Connection**
7. **VPC peering routes config**
8. **Private Services IP range**
9. **VPC firewall rules**
10. **Subnets and routers**
11. **VPC network**
12. **IAM resources** (service accounts, bindings)
13. **WIF pool and provider** (last, as these are least likely to have deps)

---

## Quick Reference: Manual Cleanup Commands

```bash
# Set project
export PROJECT=vishnu-sandbox-20250310
export REGION=us-central1

# Delete GKE
gcloud container clusters delete preview-mcp-server-langgraph-gke \
    --region=$REGION --project=$PROJECT --quiet

# Delete CloudSQL
gcloud sql instances delete preview-mcp-slg-postgres \
    --project=$PROJECT --quiet

# Delete Redis
gcloud redis instances delete preview-mcp-slg-redis \
    --region=$REGION --project=$PROJECT --quiet --async

# Delete VPC peering (after waiting for CloudSQL/Redis)
gcloud services vpc-peerings delete \
    --network=preview-mcp-slg-vpc \
    --service=servicenetworking.googleapis.com \
    --project=$PROJECT --quiet

# Delete VPC (after peering deleted)
gcloud compute networks delete preview-mcp-slg-vpc \
    --project=$PROJECT --quiet

# Undelete WIF pool (if in DELETED state)
gcloud iam workload-identity-pools undelete github-actions-pool \
    --location=global --project=$PROJECT
```

---

## Issue #7: GKE Autopilot Error 400 - Auto-Managed Configurations

### Symptom
```
Error 400: Request contains an invalid argument., badRequest
```

When creating a GKE Autopilot cluster via Terraform, the cluster creation fails with a generic Error 400.

### Root Cause
GKE Autopilot clusters have several configuration blocks that are **auto-managed by Google** and cannot be explicitly set during cluster creation:

1. **`datapath_provider`** - Autopilot uses ADVANCED_DATAPATH (Dataplane V2) by default
2. **`monitoring_config`** - Autopilot automatically enables many monitoring components
3. **`logging_config`** - Autopilot automatically configures logging components

Setting any of these explicitly in Terraform causes a `badRequest` error.

### Solution (Implemented)
In `terraform/modules/gke-autopilot/main.tf`:

1. **Remove `datapath_provider`** - Omit entirely (Autopilot uses ADVANCED_DATAPATH by default)

2. **Comment out `monitoring_config`**:
```hcl
# NOTE: For GKE Autopilot clusters, monitoring_config is managed automatically.
# Explicitly setting this causes "Error 400: badRequest" on cluster creation.
# Autopilot automatically enables SYSTEM_COMPONENTS, WORKLOADS, and additional
# components (STORAGE, HPA, POD, DAEMONSET, DEPLOYMENT, STATEFULSET, JOBSET,
# CADVISOR, KUBELET, DCGM).
#
# monitoring_config {
#   enable_components = var.monitoring_enabled_components
#   ...
# }
```

3. **Comment out `logging_config`**:
```hcl
# NOTE: For GKE Autopilot clusters, logging_config is managed automatically.
#
# logging_config {
#   enable_components = var.logging_enabled_components
# }
```

4. **Add lifecycle ignore_changes** for drift prevention:
```hcl
lifecycle {
  ignore_changes = [
    monitoring_config,  # Autopilot auto-manages these
    logging_config,     # Prevent drift detection
  ]
}
```

### GKE Autopilot Auto-Managed Features Reference

| Feature | Standard GKE | Autopilot |
|---------|-------------|-----------|
| `datapath_provider` | Configurable | Auto: ADVANCED_DATAPATH |
| `monitoring_config` | Configurable | Auto: Full suite enabled |
| `logging_config` | Configurable | Auto: SYSTEM_COMPONENTS + WORKLOADS |
| `network_policy` | Configurable | Auto: Enabled |
| `dns_config` | Configurable | Auto: Cloud DNS (v1.25.9+) |
| `vertical_pod_autoscaling` | Configurable | Auto: Managed |

### Prevention
- When writing Terraform for GKE Autopilot, always check Google Cloud documentation for auto-managed features
- Use lifecycle `ignore_changes` for any attribute that might be auto-configured
- Test with `terraform plan` before `terraform apply` to catch potential issues

### References
- https://cloud.google.com/kubernetes-engine/docs/concepts/autopilot-overview
- https://cloud.google.com/kubernetes-engine/docs/concepts/dataplane-v2

---

## Automated Testing Recommendations

1. **Pre-deployment checks**: Verify no orphaned resources exist
2. **Post-deployment checks**: Validate all resources created and healthy
3. **Teardown verification**: Confirm all resources deleted
4. **State consistency**: Verify Terraform state matches GCP reality

These are implemented in the `gke-preview-up.sh` and `gke-preview-down.sh` scripts.
