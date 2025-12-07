# GKE Infrastructure Testing Guidance

**Last Updated**: 2025-12-07
**Purpose**: Key lessons learned from GKE Preview environment testing cycles

---

## Critical: Local vs CI Test Coverage Gap

### Tests That CANNOT Be Validated Locally

| Test Category | Why Not Local | CI Authentication |
|---------------|---------------|-------------------|
| Vertex AI Integration | Requires real GCP WIF auth | GitHub Actions WIF |
| GKE Workload Identity | Requires live cluster WIF | Kubernetes pod identity |
| Cloud SQL Connectivity | Requires private VPC peering | Service networking |

**Impact**: Infrastructure changes may pass local pre-push hooks but fail CI.

### Mitigation

1. After pushing infrastructure changes, **always monitor CI** for WIF-dependent test failures
2. If CI fails with WIF authentication errors, check WIF pool state (see below)
3. Docker Compose timing issues are pre-existing flaky tests, not new regressions

---

## GCP Workload Identity Federation (WIF) State Management

### Common CI Failure Pattern

```
google-github-actions/auth failed with: failed to generate Google Cloud federated token
{"error":"invalid_target","error_description":"The target service indicated by the \"audience\" is invalid.
This might be because the pool or provider is disabled or deleted or because it doesn't exist."}
```

### Root Cause

WIF pools have a **30-day soft-delete retention period**. During local testing with `gke-preview-up.sh` and `gke-preview-down.sh`, the WIF pool can enter:
- `DELETED` state (soft-deleted, 30-day retention)
- `disabled = true` state
- Provider mismatch (pool active, provider soft-deleted)

### Quick Check

```bash
# Check WIF pool state
gcloud iam workload-identity-pools describe github-actions-pool \
    --location=global --project=PROJECT_ID --format="yaml(state,disabled)"

# Check WIF provider state
gcloud iam workload-identity-pools providers describe github-actions-provider \
    --workload-identity-pool=github-actions-pool \
    --location=global --project=PROJECT_ID --format="yaml(state,disabled)"
```

### Quick Fix

```bash
# Undelete pool and provider
gcloud iam workload-identity-pools undelete github-actions-pool \
    --location=global --project=PROJECT_ID

gcloud iam workload-identity-pools providers undelete github-actions-provider \
    --workload-identity-pool=github-actions-pool \
    --location=global --project=PROJECT_ID
```

---

## GKE Autopilot Terraform Gotchas

### Auto-Managed Configurations (DO NOT SET)

GKE Autopilot clusters auto-manage these. Setting them causes Error 400:

| Attribute | Auto-Managed By Autopilot |
|-----------|---------------------------|
| `datapath_provider` | Always ADVANCED_DATAPATH |
| `monitoring_config` | Full monitoring suite |
| `logging_config` | SYSTEM_COMPONENTS + WORKLOADS |
| `vertical_pod_autoscaling` | Always enabled |

**Solution**: Comment out these blocks in Terraform, add `lifecycle { ignore_changes = [...] }`

### GKE BackupPlan Delete Lock

BackupPlans with `backup_delete_lock_days > 0` create **immutable backups** that cannot be deleted until lock expires.

**For preview environments**:
```hcl
retention_policy {
  backup_delete_lock_days = 0   # Allow immediate deletion
  backup_retain_days      = 7   # Shorter retention
}
```

**Or disable entirely**: `enable_backup_plan = false`

---

## Service Networking Connection Eventual Consistency

### The Error

```
Error code 9: Failed to delete connection; Producer services (e.g. CloudSQL, Cloud Memstore, etc.) are still using this connection.
```

### Why It Happens

After deleting CloudSQL/Memorystore, GCP Service Networking metadata takes 2-5 minutes to release.

### Solution

The `gke-preview-down.sh` script includes retry logic. If manual cleanup needed:

```bash
# Wait 3-5 minutes after CloudSQL/Redis delete, then:
terraform state rm 'module.vpc.google_service_networking_connection.private_services[0]'
terraform destroy -auto-approve  # Remaining resources
```

---

## Key Reference Documents

| Document | Purpose |
|----------|---------|
| `docs-internal/infrastructure/GKE_PREVIEW_KNOWN_ISSUES.md` | 12 documented issues with solutions |
| `scripts/gcp/gke-preview-up.sh` | Automated cluster creation with WIF recovery |
| `scripts/gcp/gke-preview-down.sh` | Automated teardown with retry logic |
| `scripts/gcp/lib/common.sh` | Shared functions for WIF/infrastructure |

---

## Infrastructure Test Workflow

### Before Infrastructure Changes

1. Check current WIF state (see above)
2. Review `GKE_PREVIEW_KNOWN_ISSUES.md` for relevant issues
3. Ensure you understand which tests require real GCP auth

### After Pushing Infrastructure Changes

1. Monitor CI for all checks, especially:
   - Integration Tests: Vertex AI
   - Any WIF-authenticated tests
2. If WIF auth fails: undelete pool/provider, re-run CI
3. Docker Compose timing failures are usually flaky, not your change

### Test Cycle Validation

Full test cycle (UP → validate → DOWN) takes ~35-40 minutes:
- UP phase: ~20 minutes (GKE Autopilot + CloudSQL + Redis)
- DOWN phase: ~15 minutes (includes retry waits for service networking)

---

## Common Make Targets

```bash
make gke-preview-up      # Create preview environment
make gke-preview-down    # Destroy preview environment (with retries)
make gke-preview-status  # Check current resource state
```

---

**Remember**: Green pre-push hooks do NOT guarantee green CI for infrastructure changes. Always verify CI after pushing Terraform/GKE changes.
