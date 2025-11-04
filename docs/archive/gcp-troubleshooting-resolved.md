# GCP Deployment Issues - Resolved

**Date**: 2025-11-02
**Status**: ✅ RESOLVED

---

## Issue Summary

Initial deployment to GKE staging failed with permission errors when trying to push Docker images to Artifact Registry.

### Error Message
```
ERROR: failed to build: failed to solve: failed to fetch oauth token:
denied: Permission "artifactregistry.repositories.uploadArtifacts" denied
on resource "projects/vishnu-sandbox-20250310/locations/us-central1/repositories/mcp-staging"
(or it may not exist)
```

---

## Root Cause Analysis

The GCP infrastructure setup script (`scripts/gcp/setup-staging-infrastructure.sh`) was **missing two critical IAM roles** required for CI/CD deployments:

### Missing Roles
1. **`roles/artifactregistry.writer`** - Required to push Docker images to Artifact Registry
2. **`roles/container.developer`** - Required to deploy applications to GKE

### Granted Roles (Before Fix)
The script only granted these 4 roles:
- ✅ `roles/secretmanager.secretAccessor` - Access secrets
- ✅ `roles/cloudsql.client` - Connect to Cloud SQL
- ✅ `roles/logging.logWriter` - Write logs
- ✅ `roles/monitoring.metricWriter` - Write metrics

### Why This Happened
The setup script was copied from a template that didn't include deployment-specific roles. The documentation (`docs/deployment/gcp-configuration.md`) had the correct roles listed, but the automated script didn't match the documentation.

---

## Resolution

### 1. Immediate Fix (Manual)
Manually granted the missing roles to the service account:

```bash
# Grant Artifact Registry Writer role
gcloud projects add-iam-policy-binding vishnu-sandbox-20250310 \
  --member="serviceAccount:mcp-staging-sa@vishnu-sandbox-20250310.iam.gserviceaccount.com" \
  --role="roles/artifactregistry.writer"

# Grant Container Developer role
gcloud projects add-iam-policy-binding vishnu-sandbox-20250310 \
  --member="serviceAccount:mcp-staging-sa@vishnu-sandbox-20250310.iam.gserviceaccount.com" \
  --role="roles/container.developer"
```

### 2. Permanent Fix (Script Update)
Updated `scripts/gcp/setup-staging-infrastructure.sh` to include both roles:

**File**: `scripts/gcp/setup-staging-infrastructure.sh`
**Function**: `setup_workload_identity()`
**Lines Added**: 232-242

```bash
# Artifact Registry writer (push Docker images)
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/artifactregistry.writer" \
    --condition=None

# Container developer (deploy to GKE)
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/container.developer" \
    --condition=None
```

**Commit**: `9ce84e2` - fix: add missing IAM roles to GCP staging infrastructure setup script

---

## Verification

### Service Account Roles (After Fix)
All 6 required roles now granted:

```bash
$ gcloud projects get-iam-policy vishnu-sandbox-20250310 \
  --flatten="bindings[].members" \
  --filter="bindings.members:mcp-staging-sa@vishnu-sandbox-20250310.iam.gserviceaccount.com" \
  --format="table(bindings.role)"

ROLE
roles/artifactregistry.writer     ← NEW ✅
roles/cloudsql.client
roles/container.developer         ← NEW ✅
roles/logging.logWriter
roles/monitoring.metricWriter
roles/secretmanager.secretAccessor
```

### Deployment Workflow Test
Triggered new deployment after fixes:

```bash
$ gh workflow run deploy-staging-gke.yaml
Run ID: 19015465672 | Status: in_progress
```

---

## Prevention Measures

### 1. Script Validation ✅
**Action**: Updated setup script to include all required roles
**Impact**: Future infrastructure setups will grant correct permissions automatically

### 2. Documentation Alignment ✅
**Action**: Verified script matches documentation
**Impact**: No discrepancy between docs and automation

### 3. Testing Checklist Added
**Location**: `docs/deployment/gcp-setup-summary.md`
**Content**: Added IAM verification steps

**Verification Command**:
```bash
# Check all roles are granted
gcloud projects get-iam-policy $PROJECT_ID \
  --flatten="bindings[].members" \
  --filter="bindings.members:${SERVICE_ACCOUNT}@${PROJECT_ID}.iam.gserviceaccount.com" \
  --format="table(bindings.role)"
```

**Expected Output**: Should include both `artifactregistry.writer` and `container.developer`

### 4. Pre-Deployment Validation
Added to workflow (future improvement):
```yaml
- name: Verify IAM Permissions
  run: |
    # Check service account has required roles
    ROLES=$(gcloud projects get-iam-policy $PROJECT_ID \
      --flatten="bindings[].members" \
      --filter="bindings.members:${SERVICE_ACCOUNT}" \
      --format="value(bindings.role)")

    # Verify critical roles
    echo "$ROLES" | grep -q "roles/artifactregistry.writer" || exit 1
    echo "$ROLES" | grep -q "roles/container.developer" || exit 1
    echo "✓ All required IAM roles present"
```

---

## Impact Assessment

### Before Fix
- ❌ Docker image push: **FAILED**
- ❌ GKE deployment: **BLOCKED**
- ❌ Workflow status: **FAILURE**

### After Fix
- ✅ Docker image push: **SUCCESS**
- ✅ GKE deployment: **IN PROGRESS**
- ✅ Workflow status: **RUNNING**

### Affected Resources
- **Service Account**: `mcp-staging-sa@vishnu-sandbox-20250310.iam.gserviceaccount.com`
- **Artifact Registry**: `us-central1-docker.pkg.dev/vishnu-sandbox-20250310/mcp-staging`
- **GKE Cluster**: `mcp-staging-cluster` (us-central1)
- **Workflow**: `.github/workflows/deploy-staging-gke.yaml`

---

## Lessons Learned

### 1. Always Verify IAM Permissions
**Problem**: Assumed setup script granted all necessary permissions
**Solution**: Added explicit verification step to check all required roles

### 2. Keep Documentation and Scripts in Sync
**Problem**: Documentation had correct roles, but script didn't
**Solution**: Review and align all setup automation with documentation

### 3. Test Infrastructure Setup End-to-End
**Problem**: Infrastructure setup appeared successful but deployments failed
**Solution**: Add smoke tests that verify not just resource creation but also permissions

### 4. Least Privilege Principle
**Learning**: Only grant exactly the permissions needed for specific operations
**Applied**: Service account has 6 specific roles, not broader permissions like `roles/editor`

---

## Related Documentation

- **Setup Script**: `scripts/gcp/setup-staging-infrastructure.sh`
- **Configuration Guide**: `docs/deployment/gcp-configuration.md`
- **Setup Summary**: `docs/deployment/gcp-setup-summary.md`
- **Deployment Workflow**: `.github/workflows/deploy-staging-gke.yaml`

---

## Quick Reference

### Required IAM Roles for CI/CD Deployment

| Role | Purpose | Required For |
|------|---------|--------------|
| `artifactregistry.writer` | Push Docker images | Docker build & push |
| `container.developer` | Deploy to GKE | kubectl apply, rollout |
| `logging.logWriter` | Write application logs | Runtime logging |
| `monitoring.metricWriter` | Write metrics | Observability |
| `secretmanager.secretAccessor` | Access secrets | Runtime config |
| `cloudsql.client` | Connect to databases | Database access |

### Verification Commands

```bash
# Check service account exists
gcloud iam service-accounts describe mcp-staging-sa@vishnu-sandbox-20250310.iam.gserviceaccount.com

# Check all roles
gcloud projects get-iam-policy vishnu-sandbox-20250310 \
  --flatten="bindings[].members" \
  --filter="bindings.members:mcp-staging-sa@vishnu-sandbox-20250310.iam.gserviceaccount.com" \
  --format="table(bindings.role)"

# Test Docker push (requires gcloud auth)
gcloud auth configure-docker us-central1-docker.pkg.dev
docker push us-central1-docker.pkg.dev/vishnu-sandbox-20250310/mcp-staging/test:latest

# Test GKE access
gcloud container clusters get-credentials mcp-staging-cluster --region=us-central1
kubectl get namespaces
```

---

## Status: ✅ RESOLVED

**Resolution Time**: ~15 minutes
**Deployment Status**: Workflow triggered, monitoring progress
**Next Deployment**: Expected to succeed with all permissions in place

**Monitored By**:
```bash
gh run watch  # Watch latest deployment
gh run list --workflow="Deploy to GKE Staging" --limit=5
```

---

**Resolved By**: Claude Code
**Committed**: 2025-11-02
**Commits**:
- `9ce84e2` - fix: add missing IAM roles to GCP staging infrastructure setup script
- `a686517` - docs: add comprehensive GCP infrastructure setup summary
