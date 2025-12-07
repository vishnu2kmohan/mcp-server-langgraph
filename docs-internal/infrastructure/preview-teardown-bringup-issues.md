# Preview GKE Teardown and Bringup Issues Log

**Date**: 2025-12-05/06
**Objective**: Complete teardown and recreation of preview GKE deployment to validate IaC

---

## Executive Summary

During the teardown and recreation of the preview GKE infrastructure, we encountered **16 distinct issues** spanning Terraform state management, GCP API behaviors, Kubernetes secrets management, and Cloud Monitoring metric availability. This document catalogs each issue with root cause analysis and remediation steps.

**Final Status**: Preview GKE environment fully operational with all pods running (2025-12-06)

---

## Issue Tracker

### Issue #1: Keycloak Database Dependency Blocking postgres User Deletion

**Severity**: HIGH
**Component**: CloudSQL
**Phase**: Terraform Destroy

**Symptoms**:
- Terraform destroy failed with: `INVALID_PASSWORD: the password should not reuse recent passwords`
- CloudSQL instance couldn't be deleted due to postgres user having owned objects

**Root Cause**:
- Keycloak creates a database (`keycloak`) during runtime with objects owned by the `postgres` role
- OpenFGA creates a database (`openfga`) with similar ownership
- These runtime-created databases prevent the `postgres` user from being dropped
- CloudSQL's password policy blocks reusing recent passwords

**Resolution**:
1. Added `RUNTIME_DATABASES` array to teardown script with `keycloak` and `openfga`
2. Created `cleanup_runtime_databases()` function to delete these databases before CloudSQL destruction
3. Modified `delete_cloud_sql()` to call cleanup function first

**Code Changes**:
```bash
# scripts/gcp/teardown-preview-infrastructure.sh
readonly RUNTIME_DATABASES=(
    "keycloak"
    "openfga"
)

cleanup_runtime_databases() {
    for db_name in "${RUNTIME_DATABASES[@]}"; do
        gcloud sql databases delete "$db_name" \
            --instance="$CLOUD_SQL_INSTANCE" \
            --project="$PROJECT_ID" \
            --quiet
    done
}
```

**Prevention**:
- Teardown script now handles runtime-created databases automatically
- Consider documenting all databases that services create at runtime

---

### Issue #2: Service Networking Connection Timing Issue

**Severity**: HIGH
**Component**: VPC / Service Networking
**Phase**: Terraform Destroy

**Symptoms**:
- Error: `Unable to remove Service Networking Connection: Producer services (e.g. CloudSQL, Cloud Memstore, etc.) are still using this connection`
- VPC deletion failed

**Root Cause**:
- GCP's Service Networking API has a propagation delay after CloudSQL/Redis deletion
- The connection still reports producer services using it even after those services are deleted
- Terraform doesn't wait long enough for GCP internal propagation

**Resolution**:
1. Added 60-second wait after CloudSQL/Redis deletion before attempting VPC deletion
2. Added retry logic with 30-second intervals for private services address deletion

**Code Changes**:
```bash
# scripts/gcp/teardown-preview-infrastructure.sh
log_info "Waiting 60 seconds for Service Networking Connection to propagate..."
sleep 60

# Retry logic for private services address deletion
local max_retries=3
local retry_count=0
while [ $retry_count -lt $max_retries ]; do
    if gcloud compute addresses delete "$PRIVATE_SERVICES_ADDRESS" --global --quiet 2>/dev/null; then
        break
    fi
    sleep 30
    retry_count=$((retry_count + 1))
done
```

**Prevention**:
- Wait times are now built into the teardown script
- Consider increasing to 90+ seconds in production environments

---

### Issue #3: Workload Identity Pool Soft-Deletion

**Severity**: MEDIUM
**Component**: IAM / Workload Identity Federation
**Phase**: Terraform Apply (Recreation)

**Symptoms**:
- Terraform create: `Error 409: Requested entity already exists`
- Terraform import: `Cannot import non-existent remote object`
- Contradictory errors - can't create OR import

**Root Cause**:
- GCP Workload Identity Pools use **soft-deletion** by default
- When deleted via `gcloud iam workload-identity-pools delete`, the pool enters `DELETED` state with 30-day retention
- During this period, the pool ID is reserved and can't be recreated
- Import fails because the pool is in deleted state, not active

**Resolution**:
1. Use `gcloud iam workload-identity-pools list --show-deleted` to detect soft-deleted pools
2. Use `gcloud iam workload-identity-pools undelete <pool-id>` to restore
3. Import restored pool into Terraform state

**Commands Used**:
```bash
# Check for soft-deleted pools
gcloud iam workload-identity-pools list --location=global --show-deleted

# Undelete the pool
gcloud iam workload-identity-pools undelete github-actions-pool --location=global

# Undelete the provider
gcloud iam workload-identity-pools providers undelete github-actions-provider \
    --workload-identity-pool=github-actions-pool --location=global

# Import into Terraform
terraform import "module.github_actions_wif.google_iam_workload_identity_pool.github_actions" \
    "projects/PROJECT_ID/locations/global/workloadIdentityPools/github-actions-pool"
```

**Prevention**:
- Update teardown script to check for and undelete WIF pools before recreation
- Or wait 30 days for permanent deletion
- Consider using different pool names for each environment to avoid conflicts

---

### Issue #4: Terraform State Lock Contention

**Severity**: MEDIUM
**Component**: Terraform
**Phase**: Terraform Apply/Destroy

**Symptoms**:
- Multiple `Error locking state: Error acquiring the state lock` errors
- Lock IDs: `1764968092629862`, `1764991867299349`, etc.

**Root Cause**:
- Multiple concurrent Terraform operations from previous session
- Background Terraform processes holding locks
- Session context loss led to orphaned Terraform processes

**Resolution**:
```bash
terraform force-unlock -force <lock-id>
```

**Prevention**:
- Kill orphaned Terraform processes before starting new operations
- Use CI/CD pipelines with proper locking mechanisms
- Avoid running Terraform in background without process management

---

### Issue #5: Redis Instance Already Exists But Not In State

**Severity**: MEDIUM
**Component**: Memorystore Redis
**Phase**: Terraform Apply

**Symptoms**:
- Terraform: `Error 409: Resource already exists`
- Resource exists in GCP but not in Terraform state

**Root Cause**:
- Previous Terraform destroy didn't complete for all resources
- Redis instance survived the partial destroy
- Fresh Terraform apply tried to create instead of managing existing resource

**Resolution**:
```bash
terraform import "module.memorystore.google_redis_instance.main" \
    "projects/PROJECT_ID/locations/REGION/instances/preview-mcp-slg-redis"
```

**Prevention**:
- Always verify complete resource deletion after terraform destroy
- Use terraform state list to check for orphaned state entries
- Implement post-destroy verification in teardown scripts

---

### Issue #6: GKE Monitoring Alert Policies - Metrics Not Found

**Severity**: LOW
**Component**: Cloud Monitoring
**Phase**: Terraform Apply

**Symptoms**:
- `Error 404: Cannot find metric(s) that match type = "kubernetes.io/pod/phase"`
- Similar errors for `container.googleapis.com/cluster/control_plane/upgrade_event`
- Similar errors for `kubernetes.io/container/ephemeral_storage/limit_utilization`
- Similar errors for `kubernetes.io/node/ready`
- Similar errors for `redis.googleapis.com/stats/uptime`

**Root Cause**:
- Alert policies reference metrics that only exist after the underlying resources are created and running
- Terraform creates alert policies in parallel with resources
- Metrics take ~10 minutes to become available after resource creation

**Resolution**:
- These alerts will succeed on subsequent Terraform apply after cluster is running
- Run `terraform apply` again after cluster is fully operational

**Prevention**:
- Add `depends_on` to alert policy resources to wait for cluster/redis creation
- Or use `google_monitoring_alert_policy` with `create_before_destroy = false`
- Or separate alert policies into a second Terraform apply phase

**Suggested Terraform Change**:
```hcl
resource "google_monitoring_alert_policy" "pods_pending" {
  depends_on = [google_container_cluster.autopilot]
  # ... rest of config
}
```

---

### Issue #7: GKE Autopilot Cluster Creation - Invalid Argument

**Severity**: HIGH
**Component**: GKE / Terraform Provider
**Phase**: Terraform Apply

**Symptoms**:
- `googleapi: Error 400: Request contains an invalid argument., badRequest`
- No specific field identified in error message

**Root Cause**:
- Terraform Google provider (v5.45.2) appears to have a bug with GKE Autopilot cluster creation
- The same configuration works via `gcloud container clusters create-auto`
- Likely related to how the provider serializes certain fields

**Workaround**:
```bash
# Create cluster via gcloud instead of Terraform
gcloud container clusters create-auto preview-mcp-server-langgraph-gke \
  --region=us-central1 \
  --project=vishnu-sandbox-20250310 \
  --network=preview-mcp-slg-vpc \
  --subnetwork=preview-mcp-slg-nodes-us-central1 \
  --cluster-secondary-range-name=pods \
  --services-secondary-range-name=services \
  --enable-private-nodes \
  --master-ipv4-cidr=172.16.0.0/28 \
  --release-channel=regular

# Then import into Terraform
terraform import "module.gke.google_container_cluster.autopilot" \
    "projects/PROJECT_ID/locations/us-central1/clusters/preview-mcp-server-langgraph-gke"
```

**Prevention**:
- Report bug to terraform-provider-google
- Consider using terraform-provider-google-beta for newer features
- Add fallback logic in CI/CD to use gcloud if Terraform fails
- Keep monitoring_config in lifecycle ignore_changes (already done)

---

### Issue #8: Stale Resource Names in Teardown Script

**Severity**: MEDIUM
**Component**: Teardown Script
**Phase**: Script Execution

**Symptoms**:
- Script failed to find resources with old naming convention
- VPC, CloudSQL, Redis names didn't match actual resource names

**Root Cause**:
- Script used old `staging-mcp-server-langgraph-*` naming convention
- Resources were renamed to `preview-mcp-slg-*` pattern
- Script wasn't updated during staging→preview rename

**Resolution**:
Updated all resource names in teardown script:
```bash
readonly VPC_NAME="preview-mcp-slg-vpc"
readonly CLOUD_SQL_INSTANCE="preview-mcp-slg-postgres"
readonly REDIS_INSTANCE="preview-mcp-slg-redis"
readonly PRIVATE_SERVICES_ADDRESS="preview-mcp-slg-private-services"
```

**Prevention**:
- Add validation to scripts that check resource existence before operations
- Centralize naming conventions in a single config file
- Add integration tests for teardown scripts

---

### Issue #9: Service Account Naming Mismatch

**Severity**: LOW
**Component**: IAM
**Phase**: Script Execution

**Symptoms**:
- Service accounts not found during cleanup

**Root Cause**:
- Teardown script used old service account names
- Terraform module uses different naming pattern

**Resolution**:
```bash
readonly SERVICE_ACCOUNTS=(
    "preview-mcp-slg-sa"
    "preview-keycloak"
    "preview-openfga"
    "github-actions-preview"
    "github-actions-production"
    "github-actions-terraform"
)
```

**Prevention**:
- Document service account naming conventions
- Use Terraform output to generate teardown script configs

---

### Issue #10: CloudSQL Database Already Exists

**Severity**: LOW
**Component**: CloudSQL
**Phase**: Terraform Apply

**Symptoms**:
- `Error 400: database "mcp_langgraph_preview" already exists`

**Root Cause**:
- Database was created during previous deployment
- Not tracked in Terraform state after partial destroy

**Resolution**:
- Either import the database or delete it manually before apply
- For fresh start, delete with: `gcloud sql databases delete mcp_langgraph_preview --instance=preview-mcp-slg-postgres`

---

### Issue #11: NAT Router/Config Naming

**Severity**: LOW
**Component**: VPC / Cloud NAT
**Phase**: Script Execution

**Symptoms**:
- NAT resources not found during cleanup

**Root Cause**:
- Terraform naming: `${short_prefix}-router-${region}` / `${short_prefix}-nat-${region}`
- Script used incorrect names

**Resolution**:
```bash
local short_prefix="preview-mcp-slg"
local nat_router="${short_prefix}-router-${REGION}"
local nat_config="${short_prefix}-nat-${REGION}"
```

---

### Issue #12: require_ssl Deprecation Warning

**Severity**: INFO
**Component**: CloudSQL / Terraform
**Phase**: Terraform Apply

**Symptoms**:
- Warning: `require_ssl` will be fully deprecated in a future major release

**Resolution**:
- Update CloudSQL module to use `ssl_mode` instead of `require_ssl`

**Suggested Change**:
```hcl
# Instead of:
require_ssl = true

# Use:
ssl_mode = "ENCRYPTED_ONLY"  # or "ALLOW_UNENCRYPTED_AND_ENCRYPTED"
```

---

### Issue #13: Background Process Accumulation

**Severity**: MEDIUM
**Component**: Session Management
**Phase**: Throughout

**Symptoms**:
- 13+ background Terraform processes accumulated
- Resource contention and lock conflicts

**Root Cause**:
- Running Terraform with `run_in_background: true` without cleanup
- Session context loss left orphaned processes

**Resolution**:
- Kill all background Terraform processes before new operations
- Use foreground operations for critical infrastructure changes

---

## Recommendations Summary

### Immediate Actions

1. **Update Teardown Script** (DONE):
   - Add runtime database cleanup
   - Add Service Networking Connection wait time
   - Fix all resource names

2. **Update GKE Module**:
   - Add proper `depends_on` for monitoring alert policies
   - Consider moving to terraform-provider-google-beta

3. **Update CloudSQL Module**:
   - Migrate from `require_ssl` to `ssl_mode`

### Process Improvements

1. **CI/CD Pipeline**:
   - Add post-destroy verification step
   - Add terraform state consistency checks
   - Add automatic WIF pool handling (undelete/wait)

2. **Documentation**:
   - Document all runtime-created resources (databases, secrets)
   - Document naming conventions centrally
   - Add runbook for common teardown issues

3. **Testing**:
   - Add integration tests for teardown script
   - Add Terraform plan validation in CI
   - Test teardown/recreation quarterly

### Long-term Improvements

1. Consider separate Terraform workspaces for stateful resources (CloudSQL, Redis)
2. Implement blue-green deployment for infrastructure changes
3. Add automated rollback capabilities
4. Consider using Terragrunt for dependency management

---

## Appendix: Command Reference

### Check for Soft-Deleted WIF Pools
```bash
gcloud iam workload-identity-pools list --location=global --show-deleted
```

### Force Unlock Terraform State
```bash
terraform force-unlock -force <LOCK_ID>
```

### Import Existing Resources
```bash
# Redis
terraform import "module.memorystore.google_redis_instance.main" \
    "projects/PROJECT/locations/REGION/instances/NAME"

# WIF Pool
terraform import "module.github_actions_wif.google_iam_workload_identity_pool.github_actions" \
    "projects/PROJECT/locations/global/workloadIdentityPools/POOL_NAME"

# GKE Cluster
terraform import "module.gke.google_container_cluster.autopilot" \
    "projects/PROJECT/locations/REGION/clusters/CLUSTER_NAME"
```

### Manual GKE Autopilot Creation (Workaround)
```bash
gcloud container clusters create-auto CLUSTER_NAME \
  --region=REGION \
  --project=PROJECT \
  --network=VPC_NAME \
  --subnetwork=SUBNET_NAME \
  --cluster-secondary-range-name=pods \
  --services-secondary-range-name=services \
  --enable-private-nodes \
  --master-ipv4-cidr=172.16.0.0/28 \
  --release-channel=regular
```

---

### Issue #14: Missing Redis Service for Memorystore

**Severity**: HIGH
**Component**: Kubernetes Services
**Phase**: Pod Startup

**Symptoms**:
- MCP server init container `wait-for-redis` stuck in Running state
- `nc: bad address 'preview-redis-session'` error

**Root Cause**:
- Redis ExternalName service pointed to old staging DNS: `redis-session-staging.staging.internal`
- ExternalName services with IP addresses don't work with DNS resolution in busybox

**Resolution**:
1. Delete the ExternalName service
2. Create ClusterIP service with manual Endpoints object pointing to Memorystore IP
3. Use correct port 6378 (Memorystore non-standard port)

```yaml
apiVersion: v1
kind: Service
metadata:
  name: preview-redis-session
  namespace: preview-mcp-server-langgraph
spec:
  type: ClusterIP
  ports:
  - name: redis
    port: 6378
    targetPort: 6378
---
apiVersion: v1
kind: Endpoints
metadata:
  name: preview-redis-session
  namespace: preview-mcp-server-langgraph
subsets:
- addresses:
  - ip: 10.192.48.85  # Memorystore Redis private IP
  ports:
  - name: redis
    port: 6378
```

---

### Issue #15: Missing Kubernetes Secrets Keys

**Severity**: HIGH
**Component**: Kubernetes Secrets
**Phase**: Pod Startup

**Symptoms**:
- MCP server pods stuck in `CreateContainerConfigError`
- Error: `couldn't find key redis-password in Secret`
- Error: `couldn't find key redis-url in Secret`

**Root Cause**:
- External Secrets Operator not configured/running in the cluster
- Secrets created manually were missing keys expected by deployment patches
- Memorystore AUTH is enabled but password wasn't in secrets

**Missing Keys**:
- `redis-password`: Memorystore AUTH string
- `redis-url`: Full Redis URL with password
- `checkpoint-redis-url`: Redis URL for checkpoint storage
- `gdpr-postgres-url`: PostgreSQL URL for GDPR storage
- `openfga-store-id`: OpenFGA store ID
- `openfga-model-id`: OpenFGA model ID
- `keycloak-client-id`: Keycloak client ID
- `keycloak-client-secret`: Keycloak client secret
- `infisical-*`: Infisical integration secrets
- `qdrant-api-key`: Qdrant API key

**Resolution**:
```bash
# Get Memorystore AUTH string
gcloud redis instances get-auth-string preview-mcp-slg-redis --region=us-central1

# Add all missing secrets
kubectl patch secret preview-mcp-server-langgraph-secrets -n preview-mcp-server-langgraph \
  --type='json' -p='[
    {"op": "add", "path": "/data/redis-password", "value": "<base64>"},
    {"op": "add", "path": "/data/redis-url", "value": "<base64>"},
    {"op": "add", "path": "/data/checkpoint-redis-url", "value": "<base64>"},
    ...
  ]'
```

**Prevention**:
- Document all required secret keys in deployment README
- Consider using External Secrets Operator or SealedSecrets
- Add validation script to check for missing secrets before deployment

---

### Issue #16: GKE Monitoring Metrics Persistently Unavailable

**Severity**: MEDIUM
**Component**: Cloud Monitoring / GKE
**Phase**: Terraform Apply

**Symptoms**:
- `Error 404: Cannot find metric(s) that match type = "kubernetes.io/pod/phase"`
- Similar errors for 4 other GKE/Redis metrics
- Persists for 2+ hours after cluster creation

**Affected Metrics**:
1. `container.googleapis.com/cluster/control_plane/upgrade_event`
2. `kubernetes.io/container/ephemeral_storage/limit_utilization`
3. `kubernetes.io/node/ready`
4. `kubernetes.io/pod/phase`
5. `redis.googleapis.com/stats/uptime`

**Root Cause**:
- GKE Autopilot may have different metric emission behavior than Standard GKE
- Some metrics (like `upgrade_event`) only exist when the event occurs
- Ephemeral storage metrics require containers with explicit limits configured
- Cloud Monitoring API may require explicit metric data before allowing alert policy creation

**Workaround**:
Option 1: Disable alert policies temporarily
```bash
# In terraform.tfvars
enable_monitoring_alerts = false
```

Option 2: Create alert policies manually via Console or gcloud after metrics appear

Option 3: Use `condition_absence` instead of `condition_threshold` (alerts on missing metrics)

**Current Status**: Infrastructure functional, alert policies deferred

**Prevention**:
- Add `depends_on` with longer delay for alert policy creation
- Use `time_sleep` resource to delay alert policy creation by 30+ minutes
- Consider using `ignore_errors` pattern with retry logic in CI/CD
- Separate alert policy creation into a second Terraform apply phase

**Suggested Terraform Change**:
```hcl
resource "time_sleep" "wait_for_metrics" {
  depends_on      = [google_container_cluster.autopilot]
  create_duration = "30m"
}

resource "google_monitoring_alert_policy" "pods_pending" {
  depends_on = [time_sleep.wait_for_metrics]
  # ... rest of config
}
```

---

## Final Status Summary

**Date**: 2025-12-06 05:55 UTC
**Terraform State**: Fully synchronized with GCP infrastructure

### Infrastructure State
| Component | Status | Notes |
|-----------|--------|-------|
| GKE Autopilot Cluster | Running | `preview-mcp-server-langgraph-gke` |
| CloudSQL PostgreSQL | Running | `preview-mcp-slg-postgres` |
| Memorystore Redis | Running | `preview-mcp-slg-redis` (10.192.48.85:6378) |
| VPC + Private Services | Configured | Private IP connectivity working |
| Workload Identity | Configured | 3 service accounts bound, all IAM bindings in TF state |

### Pod Status
| Pod | Ready | Status |
|-----|-------|--------|
| preview-keycloak | 2/2 | Running |
| preview-mcp-server-langgraph | 2/2 | Running |
| preview-openfga | 2/2 | Running |
| preview-otel-collector | 1/1 | Running |
| preview-qdrant | 1/1 | Running |

### Terraform State Summary
| Module | Resources | Status |
|--------|-----------|--------|
| project_services | 9 | Managed |
| vpc | 10 | Managed |
| github_actions_wif | 17 | Managed |
| gke | 2 | Managed (alerts disabled) |
| cloudsql | 7 | Managed (alerts enabled) |
| memorystore | 1 | Managed (alerts disabled) |
| workload_identity | 15 | Managed |

### Monitoring Alert Policies
| Module | Status | Notes |
|--------|--------|-------|
| CloudSQL | **Enabled** | 3 policies active (high_cpu, high_memory, high_disk) |
| GKE | **Disabled** | Metrics unavailable in Cloud Monitoring |
| Memorystore | **Disabled** | Metrics unavailable in Cloud Monitoring |

**Configuration**: `terraform/environments/gcp-preview/main.tf`
- GKE: `enable_monitoring_alerts = false` (line 191)
- Memorystore: `enable_monitoring_alerts = false` (line 337)

**Re-enable when ready**:
```bash
# Edit main.tf to set enable_monitoring_alerts = true for gke and memorystore
# Then run:
cd terraform/environments/gcp-preview
terraform apply
```

---

## Appendix: Command Reference

### Check for Soft-Deleted WIF Pools
```bash
gcloud iam workload-identity-pools list --location=global --show-deleted
```

### Force Unlock Terraform State
```bash
terraform force-unlock -force <LOCK_ID>
```

### Import Existing Resources
```bash
# Redis
terraform import "module.memorystore.google_redis_instance.main" \
    "projects/PROJECT/locations/REGION/instances/NAME"

# WIF Pool
terraform import "module.github_actions_wif.google_iam_workload_identity_pool.github_actions" \
    "projects/PROJECT/locations/global/workloadIdentityPools/POOL_NAME"

# GKE Cluster
terraform import "module.gke.google_container_cluster.autopilot" \
    "projects/PROJECT/locations/REGION/clusters/CLUSTER_NAME"
```

### Manual GKE Autopilot Creation (Workaround)
```bash
gcloud container clusters create-auto CLUSTER_NAME \
  --region=REGION \
  --project=PROJECT \
  --network=VPC_NAME \
  --subnetwork=SUBNET_NAME \
  --cluster-secondary-range-name=pods \
  --services-secondary-range-name=services \
  --enable-private-nodes \
  --master-ipv4-cidr=172.16.0.0/28 \
  --release-channel=regular
```

---

*Document created: 2025-12-05*
*Last updated: 2025-12-06 05:55 UTC*
*Terraform state status: Fully synchronized*
