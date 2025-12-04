# GKE Deployment Runbook

## Overview

This runbook provides step-by-step procedures for deploying mcp-server-langgraph to GKE staging and production environments with comprehensive validation.

## Prerequisites

### Required Tools
- `kubectl` (v1.28+)
- `gcloud` CLI configured with appropriate project
- `python3` (3.9+)
- `pytest` for validation tests
- Access to GKE cluster and GCP resources

### Required Permissions
- GKE cluster admin access
- Cloud SQL client permissions
- Workload Identity admin (for service account bindings)
- Secret Manager access

## Pre-Deployment Validation

### Step 1: Run Validation Script

**Always run pre-deployment validation before applying changes:**

```bash
./scripts/validate-deployment.sh preview-gke
```

This script validates:
- ✅ Kustomize builds successfully
- ✅ All deployment tests pass (28 tests)
- ✅ Cloud SQL Proxy correctly configured
- ✅ Service dependencies exist
- ✅ Workload Identity annotations present

**Expected output:**
```
================================================
GKE Deployment Pre-Flight Validation
================================================

✓ All validation checks passed!
✓ Pre-deployment validation completed successfully!
```

### Step 2: Manual Configuration Checklist

Before deployment, verify:

#### Cloud SQL Proxy Configuration
- [ ] `--http-port=9801` flag present
- [ ] `--health-check` flag present
- [ ] Liveness probe configured on port 9801
- [ ] Readiness probe configured on port 9801
- [ ] Private IP connectivity configured

Check with:
```bash
kubectl kustomize deployments/overlays/preview-gke/ | \
  grep -A 15 "name: cloud-sql-proxy"
```

#### Service Dependencies
- [ ] All init container service references exist
- [ ] Service names match (check for namePrefix transformations)
- [ ] Redis session service points to correct Memorystore instance
- [ ] External services (Cloud SQL, Redis) are accessible from VPC

Check with:
```bash
kubectl kustomize deployments/overlays/preview-gke/ | \
  grep -E "kind: Service|name:" | grep -A 1 "kind: Service"
```

#### Workload Identity
- [ ] GCP service accounts exist
- [ ] Workload Identity bindings configured
- [ ] K8s service accounts have correct annotations
- [ ] IAM roles assigned (cloudsql.client, secretmanager.secretAccessor)

Check with:
```bash
gcloud iam service-accounts list --filter="email ~ staging"
```

#### External Secrets
- [ ] SecretStore configured and valid
- [ ] ExternalSecret resources syncing
- [ ] Secrets exist in Google Secret Manager
- [ ] Service accounts have Secret Manager access

Check with:
```bash
kubectl get secretstore,externalsecret -n staging-mcp-server-langgraph
```

## Deployment Procedure

### Standard Deployment (Staging)

**Step 1: Get cluster credentials**
```bash
gcloud container clusters get-credentials staging-mcp-server-langgraph-gke \
  --region=us-central1 \
  --project=vishnu-sandbox-20250310
```

**Step 2: Run pre-deployment validation**
```bash
./scripts/validate-deployment.sh preview-gke
```

**Step 3: Review generated manifests**
```bash
less /tmp/preview-gke-manifests.yaml
```

**Step 4: Apply configuration**
```bash
kubectl apply -k deployments/overlays/preview-gke/
```

**Step 5: Monitor deployment**
```bash
# Watch pod status
kubectl get pods -n staging-mcp-server-langgraph -w

# Check deployment rollout
kubectl rollout status deployment/staging-keycloak -n staging-mcp-server-langgraph
kubectl rollout status deployment/staging-openfga -n staging-mcp-server-langgraph
kubectl rollout status deployment/staging-mcp-server-langgraph -n staging-mcp-server-langgraph
```

**Step 6: Validate deployment health**
```bash
# Check pod readiness
kubectl get pods -n staging-mcp-server-langgraph

# Check service endpoints
kubectl get endpoints -n staging-mcp-server-langgraph

# Check Cloud SQL Proxy logs
kubectl logs -n staging-mcp-server-langgraph \
  deployment/staging-keycloak -c cloud-sql-proxy --tail=50
```

## Post-Deployment Validation

### Automated Health Checks

Run post-deployment validation:
```bash
# Check all pods are running
kubectl get pods -n staging-mcp-server-langgraph | \
  grep -E "Running|Ready"

# Verify no CrashLoopBackOff
kubectl get pods -n staging-mcp-server-langgraph | \
  grep -v CrashLoopBackOff | grep -v Init:

# Check deployment status
kubectl get deployments -n staging-mcp-server-langgraph
```

### Manual Verification Checklist

- [ ] All pods show `Running` status
- [ ] All containers show `READY` state (e.g., 2/2)
- [ ] No pods in `CrashLoopBackOff` or `Error` state
- [ ] Services have healthy endpoints
- [ ] Cloud SQL Proxy health checks passing
- [ ] External Secrets syncing successfully
- [ ] Application endpoints responding

### Service Health Checks

**Keycloak:**
```bash
kubectl exec -n staging-mcp-server-langgraph \
  deployment/staging-keycloak -c keycloak -- \
  curl -s http://localhost:8080/health/ready
```

**OpenFGA:**
```bash
kubectl exec -n staging-mcp-server-langgraph \
  deployment/staging-openfga -c openfga -- \
  curl -s http://localhost:8080/healthz
```

**MCP Server:**
```bash
kubectl exec -n staging-mcp-server-langgraph \
  deployment/staging-mcp-server-langgraph -c mcp-server-langgraph -- \
  curl -s http://localhost:8000/health/ready
```

## Troubleshooting

### Common Issues and Solutions

#### Issue 1: Pods Stuck in Init State

**Symptoms:**
```
NAME                                  READY   STATUS       RESTARTS   AGE
staging-mcp-server-langgraph-xxx      0/2     Init:0/3     0          5m
```

**Diagnosis:**
```bash
# Check init container logs
kubectl logs -n staging-mcp-server-langgraph \
  deployment/staging-mcp-server-langgraph -c wait-for-openfga

# Check which init container is blocking
kubectl describe pod -n staging-mcp-server-langgraph \
  <pod-name> | grep -A 10 "Init Containers"
```

**Common Causes:**
- Service name mismatch (missing namePrefix)
- Service doesn't exist
- Service has no healthy endpoints

**Solution:**
1. Verify service exists: `kubectl get svc -n staging-mcp-server-langgraph`
2. Check service has endpoints: `kubectl get endpoints -n staging-mcp-server-langgraph`
3. Verify init container references correct service name (with prefix)

#### Issue 2: Cloud SQL Proxy CrashLoopBackOff

**Symptoms:**
```
NAME                         READY   STATUS             RESTARTS      AGE
staging-keycloak-xxx         0/2     CrashLoopBackOff   10 (5m ago)   30m
```

**Diagnosis:**
```bash
# Check Cloud SQL Proxy logs
kubectl logs -n staging-mcp-server-langgraph \
  <pod-name> -c cloud-sql-proxy --tail=100

# Check for health probe failures
kubectl describe pod -n staging-mcp-server-langgraph <pod-name> | \
  grep -A 5 "Liveness\|Readiness"
```

**Common Causes:**
- Missing `--http-port=9801` flag
- Missing `--health-check` flag
- Incorrect health probe configuration
- Network connectivity issues (VPC, Private Google Access)

**Solution:**
1. Verify Cloud SQL Proxy args include `--http-port=9801` and `--health-check`
2. Check health probe configuration: port 9801, paths `/liveness` and `/readiness`
3. Verify Private Google Access enabled on VPC subnet
4. Check Cloud SQL instance is in correct VPC

#### Issue 3: Application Can't Connect to Database

**Symptoms:**
```
Connection to 127.0.0.1:5432 refused
```

**Diagnosis:**
```bash
# Check Cloud SQL Proxy is ready
kubectl logs -n staging-mcp-server-langgraph \
  <pod-name> -c cloud-sql-proxy | grep "ready for new connections"

# Check Workload Identity
kubectl describe sa -n staging-mcp-server-langgraph staging-keycloak | \
  grep "iam.gke.io/gcp-service-account"
```

**Common Causes:**
- Cloud SQL Proxy not started yet
- Workload Identity not configured
- Cloud SQL instance not accessible

**Solution:**
1. Wait for Cloud SQL Proxy to be ready (check readiness probe)
2. Verify Workload Identity annotation on ServiceAccount
3. Check GCP service account has `roles/cloudsql.client`
4. Verify Cloud SQL instance exists and is RUNNABLE

#### Issue 4: External Secrets Not Syncing

**Symptoms:**
```
ExternalSecret: staging-mcp-server-langgraph-secrets
Status: SecretSyncedError
```

**Diagnosis:**
```bash
# Check ExternalSecret status
kubectl describe externalsecret -n staging-mcp-server-langgraph

# Check SecretStore status
kubectl describe secretstore -n staging-mcp-server-langgraph staging-gcp-secret-store
```

**Common Causes:**
- SecretStore not configured correctly
- Service account missing Secret Manager permissions
- Secrets don't exist in Secret Manager

**Solution:**
1. Verify SecretStore references correct GCP project
2. Check service account has `roles/secretmanager.secretAccessor`
3. Verify secrets exist in Secret Manager: `gcloud secrets list`

### Emergency Rollback

If deployment causes critical issues:

**Step 1: Rollback deployment**
```bash
kubectl rollout undo deployment/staging-keycloak -n staging-mcp-server-langgraph
kubectl rollout undo deployment/staging-openfga -n staging-mcp-server-langgraph
kubectl rollout undo deployment/staging-mcp-server-langgraph -n staging-mcp-server-langgraph
```

**Step 2: Verify rollback**
```bash
kubectl rollout status deployment/staging-keycloak -n staging-mcp-server-langgraph
kubectl get pods -n staging-mcp-server-langgraph
```

**Step 3: Clean up failed resources**
```bash
# Delete failed ReplicaSets
kubectl get replicasets -n staging-mcp-server-langgraph | \
  grep "0         0         0" | awk '{print $1}' | \
  xargs kubectl delete replicaset -n staging-mcp-server-langgraph
```

## Cleanup Procedures

### Delete Old ReplicaSets

After successful deployment:
```bash
# List old ReplicaSets (0 desired replicas)
kubectl get replicasets -n staging-mcp-server-langgraph | grep "0         0         0"

# Delete old ReplicaSets
kubectl get replicasets -n staging-mcp-server-langgraph -o json | \
  jq -r '.items[] | select(.spec.replicas == 0) | .metadata.name' | \
  xargs -I {} kubectl delete replicaset {} -n staging-mcp-server-langgraph
```

### Drain and Delete Failed Pods

```bash
# Delete all failed pods
kubectl get pods -n staging-mcp-server-langgraph | \
  grep -E "Error|CrashLoopBackOff|Init:Error" | awk '{print $1}' | \
  xargs kubectl delete pod -n staging-mcp-server-langgraph
```

## Best Practices

### Pre-Deployment
1. ✅ **Always run validation script** before applying changes
2. ✅ **Run tests locally** to ensure all 28 tests pass
3. ✅ **Review generated manifests** before applying
4. ✅ **Check for configuration drift** between environments
5. ✅ **Verify infrastructure** (Cloud SQL, Redis) is healthy

### During Deployment
1. ✅ **Monitor pod status** continuously during rollout
2. ✅ **Check logs** for errors immediately
3. ✅ **Validate health probes** are passing
4. ✅ **Watch for CrashLoopBackOff** early
5. ✅ **Don't apply multiple changes** simultaneously

### Post-Deployment
1. ✅ **Run post-deployment validation** checks
2. ✅ **Monitor for 10-15 minutes** to ensure stability
3. ✅ **Clean up old ReplicaSets** after success
4. ✅ **Document any issues** encountered
5. ✅ **Update runbook** with lessons learned

## Testing

### Run All Validation Tests

```bash
# Run all deployment tests
python -m pytest tests/deployment/ -v

# Expected output: 28 passed
```

### Specific Test Categories

```bash
# Cloud SQL Proxy configuration tests
python -m pytest tests/deployment/test_cloud_sql_proxy_config.py -v

# Service dependency tests
python -m pytest tests/deployment/test_service_dependencies.py -v

# Kustomize build tests
python -m pytest tests/deployment/test_kustomize_build.py -v
```

## Contact and Escalation

### Issue Severity Levels

- **P0 (Critical)**: Complete deployment failure, all pods failing
- **P1 (High)**: Partial deployment failure, some services down
- **P2 (Medium)**: Non-critical issues, warnings
- **P3 (Low)**: Cosmetic issues, cleanup needed

### Escalation Path

1. **Developer**: Check logs, review recent changes
2. **DevOps Lead**: Infrastructure validation, rollback decision
3. **On-Call**: Emergency response, incident management

## Appendix

### Useful Commands

```bash
# Get cluster info
gcloud container clusters describe staging-mcp-server-langgraph-gke \
  --region=us-central1 --project=vishnu-sandbox-20250310

# List all resources in namespace
kubectl get all -n staging-mcp-server-langgraph

# Get events (last 1 hour)
kubectl get events -n staging-mcp-server-langgraph \
  --sort-by='.lastTimestamp' | tail -50

# Describe all pods
kubectl describe pods -n staging-mcp-server-langgraph

# Get logs for all containers in a pod
kubectl logs -n staging-mcp-server-langgraph <pod-name> --all-containers

# Port forward to service
kubectl port-forward -n staging-mcp-server-langgraph \
  svc/staging-keycloak 8080:8080
```

### Configuration Validation Queries

```bash
# Check Cloud SQL Proxy configuration
kubectl kustomize deployments/overlays/preview-gke/ | \
  grep -A 30 "name: cloud-sql-proxy" | grep -E "args:|--"

# List all services
kubectl kustomize deployments/overlays/preview-gke/ | \
  grep -A 3 "kind: Service" | grep "name:"

# Check Workload Identity annotations
kubectl kustomize deployments/overlays/preview-gke/ | \
  grep -B 3 "iam.gke.io/gcp-service-account"

# Verify init container service references
kubectl kustomize deployments/overlays/preview-gke/ | \
  grep -A 10 "initContainers:" | grep "nc -z"
```

## Version History

| Date | Version | Changes | Author |
|------|---------|---------|--------|
| 2025-11-06 | 1.0 | Initial runbook with TDD validation | Claude |

## References

- [GKE Documentation](https://cloud.google.com/kubernetes-engine/docs)
- [Cloud SQL Proxy](https://cloud.google.com/sql/docs/postgres/sql-proxy)
- [Workload Identity](https://cloud.google.com/kubernetes-engine/docs/how-to/workload-identity)
- [External Secrets Operator](https://external-secrets.io/)
- [Kustomize](https://kustomize.io/)
