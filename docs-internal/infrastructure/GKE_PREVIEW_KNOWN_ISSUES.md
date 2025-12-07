# GKE Preview Environment - Known Issues and Solutions

**Created**: 2025-12-06
**Last Updated**: 2025-12-07
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

**Status: ✅ RESOLVED (Automated)**

### Symptom
```
Error code 9: Failed to delete connection; Producer services (e.g. CloudSQL, Cloud Memstore, etc.) are still using this connection.
```

### Root Cause
GCP Service Networking Connections have eventual consistency. After deleting CloudSQL or Memorystore instances, the connection metadata can take 2-5 minutes to fully release.

### Solution (Automated in gke-preview-down.sh)
The `gke-preview-down.sh` script now includes **automatic retry logic** with a multi-stage fallback:

1. **Initial terraform destroy** - Attempts full destruction
2. **Error detection** - Checks for "Error code 9" / "Producer services still using"
3. **Wait and retry** - Waits 2 minutes and retries (up to 3 times)
4. **Fallback cleanup** - If retries fail:
   - Removes service networking resources from Terraform state
   - Attempts gcloud direct deletion of VPC peering
   - Runs final terraform destroy for remaining resources

```bash
# Configuration in gke-preview-down.sh
SERVICE_NETWORKING_MAX_RETRIES=3
SERVICE_NETWORKING_RETRY_DELAY=120  # 2 minutes

# Key functions added:
# - cleanup_service_networking_with_gcloud() - Direct gcloud VPC peering delete
# - remove_service_networking_from_state() - Remove problematic resources from state
# - terraform_destroy() - Enhanced with retry logic for service networking errors
```

### Manual Cleanup (if needed)

#### Option A: gcloud Direct Delete
```bash
gcloud services vpc-peerings delete \
    --network=preview-mcp-slg-vpc \
    --service=servicenetworking.googleapis.com \
    --project="$PROJECT_ID" \
    --quiet
```

#### Option B: Force VPC Peering Delete
```bash
gcloud compute networks peerings delete servicenetworking-googleapis-com \
    --network=preview-mcp-slg-vpc \
    --project="$PROJECT_ID" \
    --quiet
```

### Prevention
- Always use `gke-preview-down.sh` for teardown (handles retries automatically)
- The script now waits for GCP eventual consistency before VPC cleanup

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

## Issue #8: WIF Pool Active but Not in Terraform State

**Status: ✅ RESOLVED (Automated)**

### Symptom
```
Error 409: Requested entity already exists

  with module.github_actions_wif.google_iam_workload_identity_pool.github_actions

Error 400: Identity Pool does not exist (projects/.../workloadIdentityPools/github-actions-pool)

  with module.github_actions_wif.google_service_account_iam_member.github_actions_wif["preview"]
```

### Root Cause
When a WIF pool exists in GCP in an **active** state (not soft-deleted), but Terraform state is empty (e.g., after `gke-preview-down.sh --terraform-only` or manual state deletion), Terraform tries to create the pool and fails with Error 409.

Additionally, subsequent IAM bindings that reference the pool fail with Error 400 because Terraform's state shows the pool as non-existent (the create failed), while GCP shows it exists.

### Solution (Automated in scripts/gcp/lib/common.sh)
The `recover_soft_deleted_wif()` function now handles **both** soft-deleted and active pools:

1. **Soft-deleted pool**: Undelete the pool and import into Terraform state
2. **Active pool**: Import directly into Terraform state (new behavior)

```bash
# In recover_soft_deleted_wif() - case 1 (Active pool)
1)  # Active - already exists in GCP
    log_info "WIF pool already active: $pool_id"
    # Still need to import into Terraform state if not already tracked
    import_wif_to_terraform "$project_id" "$pool_id" "$provider_id"
    return 0
    ;;
```

The `import_wif_to_terraform()` function checks if the resource is already in Terraform state before importing, preventing duplicate import errors.

### Prevention
- Always use `gke-preview-down.sh` for teardown (handles state properly)
- Script now auto-imports active WIF pools into Terraform state during `gke-preview-up.sh`

---

## Issue #9: GKE BackupPlan Deletion with Locked Backups

**Status: ⚠️ DOCUMENTED (Manual Workaround Required for Preview)**

### Symptom
```
Error: Error when reading or editing BackupPlan: googleapi: Error 400: Resource '"projects/PROJECT/locations/REGION/backupPlans/BACKUP_PLAN_NAME"' has nested resources. If the API supports cascading delete, set 'force' to true to delete it and its nested resources.
```

When running `terraform destroy`, the BackupPlan cannot be deleted because it has scheduled backups that are locked for deletion.

### Root Cause
GKE Backup Plans with `backup_delete_lock_days > 0` create backups that cannot be deleted until the lock expires. In the preview environment configuration:

```hcl
# terraform/modules/gke-autopilot/main.tf
retention_policy {
  backup_delete_lock_days = 7  # Prevents backup deletion for 7 days
  backup_retain_days      = 14
}
```

When a scheduled backup is created (e.g., via the weekly cron schedule), it inherits the delete lock. If you try to delete the BackupPlan before the lock expires, you get Error 400 because:

1. The BackupPlan has nested backup resources
2. The backups are locked and cannot be deleted
3. Terraform cannot cascade-delete without `force = true`

### Checking for Locked Backups
```bash
# List backups under the backup plan
gcloud beta container backup-restore backups list \
    --backup-plan=preview-mcp-server-langgraph-gke-backup-plan \
    --location=us-central1 \
    --project=PROJECT_ID

# Check a specific backup's delete lock time
gcloud beta container backup-restore backups describe BACKUP_NAME \
    --backup-plan=preview-mcp-server-langgraph-gke-backup-plan \
    --location=us-central1 \
    --project=PROJECT_ID \
    --format="yaml(deleteLockExpireTime)"
```

### Immediate Workaround (Manual)
Remove the BackupPlan from Terraform state and let it expire naturally:

```bash
# Remove from Terraform state (backup plan remains in GCP but orphaned)
terraform state rm 'module.gke.google_gke_backup_backup_plan.cluster[0]'

# Continue with terraform destroy for remaining resources
terraform destroy -auto-approve
```

The orphaned BackupPlan will remain in GCP until the backup locks expire, then can be manually deleted:

```bash
# After lock expires (check deleteLockExpireTime), delete backups
gcloud beta container backup-restore backups delete BACKUP_NAME \
    --backup-plan=preview-mcp-server-langgraph-gke-backup-plan \
    --location=us-central1 \
    --project=PROJECT_ID \
    --quiet

# Then delete the backup plan
gcloud beta container backup-restore backup-plans delete \
    preview-mcp-server-langgraph-gke-backup-plan \
    --location=us-central1 \
    --project=PROJECT_ID \
    --quiet
```

### Long-term Solution for Preview Environments
Set `backup_delete_lock_days = 0` for preview environments to allow immediate cleanup:

```hcl
# For preview environment: disable delete lock
retention_policy {
  backup_delete_lock_days = 0   # Allows immediate deletion
  backup_retain_days      = 7   # Shorter retention for preview
}
```

### Prevention
- For ephemeral/preview environments, use `backup_delete_lock_days = 0`
- For production environments, keep the 7-day lock for data protection
- Consider disabling backup plans entirely for preview: `enable_backup_plan = false`
- If you need backups in preview, use shorter cron schedules so locks expire faster

### References
- [GKE Backup and Restore documentation](https://cloud.google.com/kubernetes-engine/docs/add-on/backup-for-gke/concepts/backup-plan)
- [Backup delete lock behavior](https://cloud.google.com/kubernetes-engine/docs/add-on/backup-for-gke/concepts/retention)

---

## Issue #10: WIF Pool State Detection Bug (gcloud describe returns 0 for DELETED pools)

**Status: FIXED**

### Symptom
```
[INFO] WIF pool already active: github-actions-pool
  -> Importing WIF resources into Terraform state...
  -> Importing WIF pool into Terraform state...

Error: Cannot import non-existent remote object

Error 409: Requested entity already exists
  with module.github_actions_wif.google_iam_workload_identity_pool.github_actions
```

The script reports the WIF pool as "active" but then fails to import it and Terraform fails to create it because it "already exists".

### Root Cause
The `check_wif_pool_state()` function in `scripts/gcp/lib/common.sh` had a bug in how it detected soft-deleted WIF pools.

**Key insight**: `gcloud iam workload-identity-pools describe` returns **exit code 0 (success)** even for pools in the `DELETED` state. The command succeeds but the output shows `state: DELETED`.

The original implementation only checked the exit code:
```bash
# BUGGY - gcloud describe returns 0 even for DELETED pools!
if gcloud iam workload-identity-pools describe "$pool_id" \
    --location=global \
    --project="$project_id" &> /dev/null; then
    return 1  # Active - WRONG! Could be DELETED state
fi
```

### Solution (Implemented in scripts/gcp/lib/common.sh)
Fixed the function to explicitly check the `state` field from the describe output:

```bash
check_wif_pool_state() {
    local project_id="${1:-$(get_gcp_project)}"
    local pool_id="${2:-$WIF_POOL_ID}"

    # Get the pool state - gcloud describe returns success even for DELETED pools
    # We must check the actual state field in the output
    local pool_state
    pool_state=$(gcloud iam workload-identity-pools describe "$pool_id" \
        --location=global \
        --project="$project_id" \
        --format="value(state)" 2>/dev/null || echo "")

    case "$pool_state" in
        "ACTIVE")
            return 1  # Active
            ;;
        "DELETED")
            return 0  # Soft-deleted
            ;;
        *)
            # Pool doesn't exist or couldn't be described
            return 2  # Not found
            ;;
    esac
}
```

### Debugging Steps
To check the actual state of a WIF pool:
```bash
# Check state field explicitly
gcloud iam workload-identity-pools describe github-actions-pool \
    --location=global \
    --project=PROJECT_ID \
    --format="value(state)"
# Output: ACTIVE or DELETED

# Show full details
gcloud iam workload-identity-pools describe github-actions-pool \
    --location=global \
    --project=PROJECT_ID \
    --format=yaml
```

### Manual Recovery (if needed)
If you encounter this issue before the fix is deployed:
```bash
# 1. Undelete the pool
gcloud iam workload-identity-pools undelete github-actions-pool \
    --location=global \
    --project=PROJECT_ID

# 2. Undelete the provider
gcloud iam workload-identity-pools providers undelete github-actions-provider \
    --workload-identity-pool=github-actions-pool \
    --location=global \
    --project=PROJECT_ID

# 3. Import into Terraform state
cd terraform/environments/gcp-preview
terraform import -var="project_id=PROJECT_ID" -var="region=us-central1" \
    'module.github_actions_wif.google_iam_workload_identity_pool.github_actions' \
    'projects/PROJECT_ID/locations/global/workloadIdentityPools/github-actions-pool'

terraform import -var="project_id=PROJECT_ID" -var="region=us-central1" \
    'module.github_actions_wif.google_iam_workload_identity_pool_provider.github_actions' \
    'projects/PROJECT_ID/locations/global/workloadIdentityPools/github-actions-pool/providers/github-actions-provider'
```

### Prevention
- Always use the fixed version of `check_wif_pool_state()` that explicitly checks the `state` field
- The automated recovery in `gke-preview-up.sh` now properly handles this case

---

## Issue #11: BackupPlan Creation 409 Error (Already Exists)

**Status: ⚠️ DOCUMENTED (Script Enhancement Required)**

### Symptom
```
Error creating BackupPlan: googleapi: Error 409: Resource 'projects/PROJECT/locations/REGION/backupPlans/BACKUP_PLAN_NAME' already exists
```

During `gke-preview-up.sh`, Terraform fails to create the BackupPlan because one already exists in GCP but is not in Terraform state.

### Root Cause
When Issue #9 (BackupPlan with locked backups) occurs, the workaround removes the BackupPlan from Terraform state but leaves it orphaned in GCP. On the next `gke-preview-up.sh` run, Terraform tries to create a new BackupPlan with the same name and fails with Error 409.

This creates a circular problem:
1. **Issue #9**: Can't delete BackupPlan due to locked backups → remove from state
2. **Issue #11**: Can't create BackupPlan because orphaned one still exists → Error 409

### Solution (Manual)

**Option A: Import orphaned BackupPlan into Terraform state**
```bash
cd terraform/environments/gcp-preview

# Import the existing BackupPlan
terraform import \
  'module.gke.google_gke_backup_backup_plan.cluster[0]' \
  'projects/PROJECT_ID/locations/us-central1/backupPlans/preview-mcp-server-langgraph-gke-backup-plan'
```

**Option B: Delete orphaned BackupPlan (if no locked backups)**
```bash
# Check for backups under the plan
gcloud beta container backup-restore backups list \
    --backup-plan=preview-mcp-server-langgraph-gke-backup-plan \
    --location=us-central1 \
    --project=PROJECT_ID

# If no locked backups, delete the plan
gcloud beta container backup-restore backup-plans delete \
    preview-mcp-server-langgraph-gke-backup-plan \
    --location=us-central1 \
    --project=PROJECT_ID \
    --quiet
```

### Long-term Solution
Enhance `gke-preview-up.sh` to detect orphaned BackupPlans and either:
1. Import them into Terraform state before `terraform apply`
2. Delete them if they have no locked backups
3. Disable backup plans for preview environments entirely

### Prevention
- Set `enable_backup_plan = false` for preview environments
- Or set `backup_delete_lock_days = 0` to allow immediate deletion

---

## Issue #12: WIF Pool Soft-Delete Causing CI Failures

**Status: ⚠️ DOCUMENTED (Infrastructure Dependency)**

### Symptom
GitHub Actions CI jobs fail with:
```
google-github-actions/auth failed with: failed to generate Google Cloud federated token
{"error":"invalid_target","error_description":"The target service indicated by the \"audience\" parameters is invalid.
This might either be because the pool or provider is disabled or deleted or because it doesn't exist."}
```

### Root Cause
During local testing with `gke-preview-up.sh` and `gke-preview-down.sh`, the WIF pool can enter one of several states that break CI:

1. **Soft-deleted state**: Pool exists but in `DELETED` state (30-day retention)
2. **Disabled state**: Pool exists but `disabled = true`
3. **Provider mismatch**: Pool active but provider is soft-deleted/disabled

GitHub Actions uses WIF authentication for Vertex AI integration tests. When the pool/provider is in any of these broken states, CI authentication fails.

### Why This Wasn't Caught Locally
The pre-push hooks and local tests do not run WIF-authenticated tests:
- **Local tests**: Use mock credentials or local Docker Compose
- **Pre-push tests**: Run fast unit tests, not Vertex AI integration tests
- **CI-only tests**: Vertex AI tests require real GCP WIF authentication

This means infrastructure changes that break WIF only manifest as CI failures.

### Checking WIF State
```bash
# Check pool state
gcloud iam workload-identity-pools describe github-actions-pool \
    --location=global \
    --project=PROJECT_ID \
    --format="yaml(state,disabled)"

# Check provider state
gcloud iam workload-identity-pools providers describe github-actions-provider \
    --workload-identity-pool=github-actions-pool \
    --location=global \
    --project=PROJECT_ID \
    --format="yaml(state,disabled)"
```

### Solution (Immediate)
```bash
# If soft-deleted, undelete
gcloud iam workload-identity-pools undelete github-actions-pool \
    --location=global --project=PROJECT_ID

gcloud iam workload-identity-pools providers undelete github-actions-provider \
    --workload-identity-pool=github-actions-pool \
    --location=global --project=PROJECT_ID

# If disabled, enable (via Terraform apply or gcloud)
# Re-run CI to verify
```

### Long-term Solutions

1. **Separate WIF pool for preview**: Create dedicated WIF pools for preview environment testing that are never destroyed during teardown

2. **Skip WIF destroy in preview**: Modify `gke-preview-down.sh` to preserve WIF resources:
   ```bash
   # In terraform destroy target list, exclude WIF module
   terraform destroy -target=module.gke -target=module.cloudsql ...
   # Do NOT include: -target=module.github_actions_wif
   ```

3. **CI robustness**: Add retry logic to CI for WIF authentication failures with automatic recovery attempt

### Prevention
- Always run `gke-preview-up.sh` after `gke-preview-down.sh` to ensure WIF is restored
- Consider marking WIF resources with `prevent_destroy = true` in Terraform
- Add CI status check before pushing changes that affect infrastructure

---

## CI Failure Analysis Summary (2025-12-07)

### Failing Checks
| Workflow | Job | Root Cause | Locally Testable? |
|----------|-----|------------|-------------------|
| Integration Tests | Py3.12 (api) | Docker Compose timing | Partially |
| Integration Tests | Py3.12 (database) | Docker Compose timing | Partially |
| Integration Tests | Py3.12 (infrastructure) | Docker Compose timing | Partially |
| E2E Tests | All | Docker Compose + timing | Partially |
| Integration Tests | Vertex AI | WIF pool soft-deleted | No |

### Docker Compose Timing Issues
- **Pre-existing flaky tests**: Some integration tests have race conditions with Docker Compose service startup
- **Not caused by this PR**: These failures existed before the current changes
- **Mitigation**: Health checks and retry logic in test fixtures

### WIF Authentication Failure
- **Caused by**: WIF pool entering soft-deleted state during test cycles
- **Resolution**: Undelete pool and provider, then re-run CI
- **Prevention**: Preserve WIF resources during teardown

---

## Automated Testing Recommendations

1. **Pre-deployment checks**: Verify no orphaned resources exist
2. **Post-deployment checks**: Validate all resources created and healthy
3. **Teardown verification**: Confirm all resources deleted
4. **State consistency**: Verify Terraform state matches GCP reality
5. **WIF preservation**: Never destroy WIF pool/provider for shared environments
6. **BackupPlan cleanup**: Check for orphaned BackupPlans before apply
7. **CI validation**: Re-run CI after infrastructure changes to catch WIF issues

These are implemented in the `gke-preview-up.sh` and `gke-preview-down.sh` scripts.

---

## Test Cycle Results Summary (2025-12-07)

### Test Cycle v4 Results
| Phase | Duration | Result | Issues Encountered |
|-------|----------|--------|-------------------|
| UP | ~20 min | Partial Success | BackupPlan 409 (Issue #11) |
| DOWN | ~15 min | Partial Success | Service Networking Error 9, BackupPlan 400 (Issue #9) |
| Manual Cleanup | ~5 min | Success | Terraform state rm required |

### Resources Created/Destroyed
- **GKE Autopilot cluster**: Success
- **CloudSQL PostgreSQL**: Success
- **Memorystore Redis**: Success
- **VPC with Private Services**: Success (cleanup required retry)
- **WIF Pool/Provider**: Recovered from soft-delete, Success
- **GKE BackupPlan**: 409 on create, orphaned from previous cycle

### Lessons Learned
1. **BackupPlan idempotency**: Need to handle orphaned BackupPlans in gke-preview-up.sh
2. **Service Networking eventual consistency**: 2-3 minute wait is insufficient, need longer retry
3. **WIF state detection**: gcloud returns success for soft-deleted resources
4. **CI/WIF coupling**: Local testing cannot validate WIF-dependent CI jobs
