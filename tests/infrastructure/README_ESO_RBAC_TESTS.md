# External Secrets Operator RBAC Integration Tests

## Overview

This document describes the integration tests for External Secrets Operator (ESO) RBAC configuration on GKE staging.

The tests validate that:
1. ✅ GCP service account has proper IAM roles (`roles/container.admin`)
2. ✅ ESO is installed with all required components (controller, webhook, cert-controller)
3. ✅ ESO RBAC resources are created (ClusterRoles, ClusterRoleBindings)
4. ✅ ESO can sync secrets from GCP Secret Manager

## Background: The RBAC Issue

### Problem
External Secrets Operator installation failed with RBAC permission errors:
```
Error: cannot create resource 'clusterroles' at the cluster scope
User cannot create resource 'roles' - requires container.roles.create
```

### Root Cause
The GCP service account had `roles/container.developer`, which lacks permissions to create cluster-scoped RBAC resources (ClusterRoles, ClusterRoleBindings).

### Solution
Upgraded the service account IAM role from `roles/container.developer` to `roles/container.admin` in the infrastructure setup script.

**Fixed in commit:** `669f6cb` (Nov 2, 2025)
**File:** `scripts/gcp/setup-preview-infrastructure.sh` (lines 301-306)

## Prerequisites

### Required Tools
- `kubectl` configured for GKE staging cluster
- `gcloud` CLI authenticated with appropriate permissions
- `pytest` with dev dependencies installed

### Required Access
- GKE cluster access (via `gcloud container clusters get-credentials`)
- GCP project IAM viewer permissions (to query service account roles)
- Kubernetes read permissions (to query deployments, CRDs, RBAC resources)

### Environment Variables
Set these before running tests:

```bash
# GCP Project ID (or use gcloud config)
export GCP_PROJECT_ID="your-project-id"

# GCP Service Account Email
export GCP_SERVICE_ACCOUNT_EMAIL="github-actions-gke@your-project-id.iam.gserviceaccount.com"
```

If not set, the tests will attempt to auto-detect from `gcloud config`.

## Installation

### 1. Apply Infrastructure Fix (One-Time Setup)

Run the infrastructure script to:
- Grant `roles/container.admin` to the service account
- Install External Secrets Operator with RBAC permissions

```bash
./scripts/gcp/setup-preview-infrastructure.sh
```

This script will:
1. Configure Workload Identity with proper IAM roles
2. Install ESO via Helm with CRDs
3. Verify deployments are running
4. Verify CRDs are installed

### 2. Connect to GKE Staging Cluster

```bash
# Get credentials for staging cluster
gcloud container clusters get-credentials staging-mcp-server-langgraph-gke \
    --region=us-central1 \
    --project=your-project-id
```

### 3. Verify kubectl Access

```bash
# Should show external-secrets-system namespace
kubectl get namespace external-secrets-system

# Should show ESO deployments
kubectl get deployment -n external-secrets-system
```

## Running the Tests

### Run All ESO RBAC Tests

```bash
# From project root
pytest tests/infrastructure/test_external_secrets_rbac.py -v -m integration
```

### Run Specific Test Classes

```bash
# Test only GCP IAM configuration
pytest tests/infrastructure/test_external_secrets_rbac.py::TestGCPServiceAccountIAM -v

# Test only ESO deployments
pytest tests/infrastructure/test_external_secrets_rbac.py::TestESONamespaceAndDeployments -v

# Test only RBAC resources
pytest tests/infrastructure/test_external_secrets_rbac.py::TestESORBACResources -v

# Test only secret synchronization
pytest tests/infrastructure/test_external_secrets_rbac.py::TestExternalSecretSync -v
```

### Run Specific Test Functions

```bash
# Test service account has container.admin role
pytest tests/infrastructure/test_external_secrets_rbac.py::TestGCPServiceAccountIAM::test_service_account_has_container_admin_role -v

# Test ClusterRoles exist
pytest tests/infrastructure/test_external_secrets_rbac.py::TestESORBACResources::test_eso_controller_clusterrole_exists -v
```

### Expected Output (All Tests Pass)

```
tests/infrastructure/test_external_secrets_rbac.py::TestGCPServiceAccountIAM::test_service_account_exists PASSED
tests/infrastructure/test_external_secrets_rbac.py::TestGCPServiceAccountIAM::test_service_account_has_container_admin_role PASSED
tests/infrastructure/test_external_secrets_rbac.py::TestGCPServiceAccountIAM::test_service_account_has_secret_manager_access PASSED
tests/infrastructure/test_external_secrets_rbac.py::TestESONamespaceAndDeployments::test_eso_namespace_exists PASSED
tests/infrastructure/test_external_secrets_rbac.py::TestESONamespaceAndDeployments::test_eso_controller_deployment_exists PASSED
tests/infrastructure/test_external_secrets_rbac.py::TestESONamespaceAndDeployments::test_eso_webhook_deployment_exists PASSED
tests/infrastructure/test_external_secrets_rbac.py::TestESONamespaceAndDeployments::test_eso_cert_controller_deployment_exists PASSED
tests/infrastructure/test_external_secrets_rbac.py::TestESOCRDs::test_externalsecret_crd_exists PASSED
tests/infrastructure/test_external_secrets_rbac.py::TestESOCRDs::test_secretstore_crd_exists PASSED
tests/infrastructure/test_external_secrets_rbac.py::TestESOCRDs::test_clustersecretstore_crd_exists PASSED
tests/infrastructure/test_external_secrets_rbac.py::TestESORBACResources::test_eso_controller_clusterrole_exists PASSED
tests/infrastructure/test_external_secrets_rbac.py::TestESORBACResources::test_eso_webhook_clusterrole_exists PASSED
tests/infrastructure/test_external_secrets_rbac.py::TestESORBACResources::test_eso_cert_controller_clusterrole_exists PASSED
tests/infrastructure/test_external_secrets_rbac.py::TestESORBACResources::test_eso_controller_clusterrolebinding_exists PASSED
tests/infrastructure/test_external_secrets_rbac.py::TestESORBACResources::test_eso_webhook_clusterrolebinding_exists PASSED
tests/infrastructure/test_external_secrets_rbac.py::TestESORBACResources::test_eso_cert_controller_clusterrolebinding_exists PASSED
tests/infrastructure/test_external_secrets_rbac.py::TestClusterSecretStoreConnectivity::test_clustersecretstore_gcp_exists PASSED
tests/infrastructure/test_external_secrets_rbac.py::TestClusterSecretStoreConnectivity::test_clustersecretstore_status_valid PASSED
tests/infrastructure/test_external_secrets_rbac.py::TestExternalSecretSync::test_externalsecret_resources_exist PASSED
tests/infrastructure/test_external_secrets_rbac.py::TestExternalSecretSync::test_externalsecret_sync_status PASSED
tests/infrastructure/test_external_secrets_rbac.py::TestExternalSecretSync::test_synced_secrets_exist PASSED

========================= 21 passed in 15.42s ==========================
```

## Test Coverage

### Test Classes and Functions

| Test Class | Tests | Purpose |
|-----------|-------|---------|
| `TestGCPServiceAccountIAM` | 3 | Verify GCP IAM roles are correctly configured |
| `TestESONamespaceAndDeployments` | 4 | Verify ESO components are deployed and running |
| `TestESOCRDs` | 3 | Verify ESO CRDs are installed |
| `TestESORBACResources` | 6 | Verify cluster-scoped RBAC resources exist |
| `TestClusterSecretStoreConnectivity` | 2 | Verify ClusterSecretStore can connect to GCP |
| `TestExternalSecretSync` | 3 | Verify secrets sync from GCP Secret Manager |
| **Total** | **21** | **Comprehensive ESO validation** |

### What Each Test Class Validates

#### 1. TestGCPServiceAccountIAM
- ✅ Service account exists
- ✅ Service account has `roles/container.admin` (CRITICAL for RBAC creation)
- ✅ Service account has Secret Manager access

#### 2. TestESONamespaceAndDeployments
- ✅ `external-secrets-system` namespace exists
- ✅ ESO controller deployment is running
- ✅ ESO webhook deployment is running
- ✅ ESO cert-controller deployment is running

#### 3. TestESOCRDs
- ✅ `externalsecrets.external-secrets.io` CRD exists
- ✅ `secretstores.external-secrets.io` CRD exists
- ✅ `clustersecretstores.external-secrets.io` CRD exists

#### 4. TestESORBACResources
- ✅ ClusterRole: `external-secrets-controller`
- ✅ ClusterRole: `external-secrets-webhook`
- ✅ ClusterRole: `external-secrets-cert-controller`
- ✅ ClusterRoleBinding: `external-secrets-controller`
- ✅ ClusterRoleBinding: `external-secrets-webhook`
- ✅ ClusterRoleBinding: `external-secrets-cert-controller`

#### 5. TestClusterSecretStoreConnectivity
- ✅ ClusterSecretStore `gcp-secret-manager` exists
- ✅ ClusterSecretStore status is Ready

#### 6. TestExternalSecretSync
- ✅ ExternalSecret resources exist
- ✅ ExternalSecret resources have Ready status
- ✅ Target Kubernetes secrets are created

## Troubleshooting

### Test Failures

#### "Service account missing roles/container.admin"
**Cause:** Infrastructure script not run or IAM role not applied

**Fix:**
```bash
./scripts/gcp/setup-preview-infrastructure.sh
```

#### "Namespace external-secrets-system not found"
**Cause:** ESO not installed

**Fix:**
```bash
./scripts/gcp/setup-preview-infrastructure.sh
```

#### "ESO controller deployment not found"
**Cause:** ESO installation failed

**Check logs:**
```bash
# Check Helm releases
helm list -n external-secrets-system

# Re-install ESO
helm upgrade --install external-secrets \
    external-secrets/external-secrets \
    --namespace external-secrets-system \
    --create-namespace \
    --set installCRDs=true
```

#### "ClusterRole not found"
**Cause:** RBAC creation failed due to insufficient permissions

**Verify IAM role:**
```bash
gcloud projects get-iam-policy your-project-id \
    --flatten=bindings[].members \
    --filter=bindings.members:serviceAccount:github-actions-gke@your-project-id.iam.gserviceaccount.com \
    --format=json
```

Should include `roles/container.admin`.

#### "ClusterSecretStore not ready"
**Cause:** Service account lacks Secret Manager permissions

**Grant permissions:**
```bash
gcloud projects add-iam-policy-binding your-project-id \
    --member="serviceAccount:github-actions-gke@your-project-id.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"
```

#### "ExternalSecret sync failures"
**Cause:** Secrets don't exist in GCP Secret Manager or access denied

**Create test secret:**
```bash
echo -n "test-value" | gcloud secrets create test-secret \
    --data-file=- \
    --project=your-project-id
```

**Grant access:**
```bash
gcloud secrets add-iam-policy-binding test-secret \
    --member="serviceAccount:github-actions-gke@your-project-id.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor" \
    --project=your-project-id
```

### Manual Verification

If tests fail, manually verify the setup:

```bash
# 1. Check service account IAM roles
gcloud projects get-iam-policy your-project-id \
    --flatten=bindings[].members \
    --filter=bindings.members:serviceAccount:github-actions-gke@your-project-id.iam.gserviceaccount.com

# 2. Check ESO deployments
kubectl get deployment -n external-secrets-system

# 3. Check ESO CRDs
kubectl get crd | grep external-secrets

# 4. Check ClusterRoles
kubectl get clusterrole | grep external-secrets

# 5. Check ClusterRoleBindings
kubectl get clusterrolebinding | grep external-secrets

# 6. Check ClusterSecretStore
kubectl get clustersecretstore

# 7. Check ExternalSecrets
kubectl get externalsecret --all-namespaces
```

## CI/CD Integration

### GitHub Actions

Add to your workflow:

```yaml
- name: Run ESO RBAC Integration Tests
  run: |
    # Connect to GKE
    gcloud container clusters get-credentials staging-mcp-server-langgraph-gke \
      --region=us-central1 \
      --project=${{ env.GCP_PROJECT_ID }}

    # Set environment variables
    export GCP_PROJECT_ID=${{ env.GCP_PROJECT_ID }}
    export GCP_SERVICE_ACCOUNT_EMAIL="github-actions-gke@${{ env.GCP_PROJECT_ID }}.iam.gserviceaccount.com"

    # Run tests
    pytest tests/infrastructure/test_external_secrets_rbac.py -v -m integration
```

### Local Development

```bash
# One-time setup
export GCP_PROJECT_ID="your-project-id"
export GCP_SERVICE_ACCOUNT_EMAIL="github-actions-gke@your-project-id.iam.gserviceaccount.com"

# Get cluster credentials
gcloud container clusters get-credentials staging-mcp-server-langgraph-gke \
    --region=us-central1 \
    --project=$GCP_PROJECT_ID

# Run tests
source .venv/bin/activate
pytest tests/infrastructure/test_external_secrets_rbac.py -v -m integration
```

## Related Documentation

- **Infrastructure Setup:** `scripts/gcp/setup-preview-infrastructure.sh`
- **ESO Configuration:** `deployments/security/external-secrets/values.yaml`
- **ExternalSecret Manifests:** `deployments/overlays/preview-gke/external-secrets.yaml`
- **IAM Requirements:** `docs/deployment/iam-rbac-requirements.md`
- **Deployment Issues:** `docs/deployment/deployment-issues-prevention.md`

## References

- [External Secrets Operator Documentation](https://external-secrets.io/)
- [GCP Secret Manager](https://cloud.google.com/secret-manager/docs)
- [GKE Workload Identity](https://cloud.google.com/kubernetes-engine/docs/how-to/workload-identity)
- [Kubernetes RBAC](https://kubernetes.io/docs/reference/access-authn-authz/rbac/)
