# Pod Failure Troubleshooting Runbook

**Last Updated**: 2025-11-12
**Maintainer**: Platform Team
**Environment**: All (Development, Staging, Production)

## Table of Contents

1. [Quick Diagnosis](#quick-diagnosis)
2. [Common Pod Failure Patterns](#common-pod-failure-patterns)
3. [Step-by-Step Troubleshooting](#step-by-step-troubleshooting)
4. [Prevention Checklist](#prevention-checklist)
5. [Automated Tools](#automated-tools)

---

## Quick Diagnosis

### Check Pod Status
```bash
# Get all pods in namespace
kubectl get pods -n <namespace>

# Get pods with issues
kubectl get pods -n <namespace> | grep -E "Error|CrashLoop|Pending|CreateContainer|ImagePull|Evicted"

# Get detailed pod information
kubectl describe pod <pod-name> -n <namespace>
```

### Check Recent Events
```bash
# Get recent events sorted by timestamp
kubectl get events -n <namespace> --sort-by='.lastTimestamp' | tail -50

# Get events for specific pod
kubectl get events -n <namespace> --field-selector involvedObject.name=<pod-name>
```

### Check Pod Logs
```bash
# Get current container logs
kubectl logs <pod-name> -c <container-name> -n <namespace>

# Get previous container logs (if pod restarted)
kubectl logs <pod-name> -c <container-name> -n <namespace> --previous

# Follow logs in real-time
kubectl logs -f <pod-name> -c <container-name> -n <namespace>
```

---

## Common Pod Failure Patterns

### 1. CrashLoopBackOff

**Symptoms**:
- Pod status: `CrashLoopBackOff`
- Restart count increasing
- Pod alternates between Running and Terminating

**Common Causes**:

#### A. Application Errors
```bash
# Check logs for application errors
kubectl logs <pod-name> -n <namespace> --previous | tail -100
```

**Solutions**:
- Fix application code errors
- Update configuration
- Check environment variables

#### B. Filesystem Permissions (readOnlyRootFilesystem)
**Error**: `java.nio.file.ReadOnlyFileSystemException` or `Permission denied`

**Root Cause**: `readOnlyRootFilesystem: true` without proper volume mounts

**Solution**:
```yaml
# Add writable volume mounts
volumeMounts:
- name: tmp
  mountPath: /tmp
- name: cache
  mountPath: /var/tmp
- name: app-data
  mountPath: /app/data  # Application-specific writable path

volumes:
- name: tmp
  emptyDir: {}
- name: cache
  emptyDir: {}
- name: app-data
  emptyDir: {}
```

**Prevention**:
1. Test readOnlyRootFilesystem in development first
2. Run validation script: `python3 scripts/validate_gke_autopilot_compliance.py`
3. Monitor for filesystem errors in logs

#### C. Missing Dependencies
**Error**: `ModuleNotFoundError`, `ImportError`, or similar

**Solutions**:
- Verify Docker image contains all dependencies
- Check requirements.txt or package.json is complete
- Rebuild and push updated image

#### D. Configuration Errors
**Error**: Configuration file not found or invalid

**Solutions**:
- Verify ConfigMaps are created and mounted correctly
- Check Secret references are correct
- Validate configuration syntax

---

### 2. CreateContainerConfigError

**Symptoms**:
- Pod status: `CreateContainerConfigError`
- Container never starts
- Pod stuck in this state

**Common Causes**:

#### A. Missing Secrets/ConfigMaps
**Error**: `secret "example-secret" not found` or `configmap "example-config" not found`

**Diagnosis**:
```bash
kubectl describe pod <pod-name> -n <namespace> | grep -A 5 "Events:"
```

**Solutions**:
```bash
# List secrets
kubectl get secrets -n <namespace>

# List configmaps
kubectl get configmaps -n <namespace>

# Create missing secret
kubectl create secret generic <secret-name> \
  --from-literal=key=value \
  -n <namespace>
```

#### B. Invalid Volume Mounts
**Error**: Volume mount path conflicts or invalid

**Solutions**:
- Check volume mount paths don't overlap
- Verify volume names match between `volumes` and `volumeMounts`
- Ensure mount paths are absolute

---

### 3. ImagePullBackOff / ErrImagePull

**Symptoms**:
- Pod status: `ImagePullBackOff` or `ErrImagePull`
- Image cannot be pulled from registry

**Common Causes**:

#### A. Image Does Not Exist
**Solutions**:
- Verify image tag is correct
- Check image exists in registry:
  ```bash
  docker pull <image>:<tag>
  ```
- Update deployment with correct image tag

#### B. Authentication Failure
**Solutions**:
```bash
# Create image pull secret
kubectl create secret docker-registry <secret-name> \
  --docker-server=<registry> \
  --docker-username=<username> \
  --docker-password=<password> \
  --docker-email=<email> \
  -n <namespace>

# Add to ServiceAccount
kubectl patch serviceaccount <sa-name> \
  -p '{"imagePullSecrets": [{"name": "<secret-name>"}]}' \
  -n <namespace>
```

---

### 4. Pending (Insufficient Resources)

**Symptoms**:
- Pod status: `Pending`
- Events show: `Insufficient cpu` or `Insufficient memory`

**Diagnosis**:
```bash
# Check node resources
kubectl top nodes

# Check pod resource requests
kubectl describe pod <pod-name> -n <namespace> | grep -A 10 "Requests:"

# Check resource quotas
kubectl get resourcequota -n <namespace>
```

**Solutions**:

#### A. Reduce Resource Requests
```yaml
resources:
  requests:
    cpu: 100m        # Reduce from 500m
    memory: 128Mi    # Reduce from 512Mi
```

#### B. Scale Up Cluster
```bash
# GKE Autopilot auto-scales, but you can trigger it
gcloud container clusters resize <cluster-name> \
  --num-nodes=<new-count> \
  --zone=<zone>
```

---

### 5. GKE Autopilot Specific Errors

#### A. CPU Limit/Request Ratio Violation
**Error**: `cpu max limit to request ratio per Container is 4, but provided ratio is X`

**Root Cause**: GKE Autopilot enforces max ratio of 4.0

**Diagnosis**:
```bash
# Calculate ratio
# ratio = cpu_limit / cpu_request
# Example: 1000m / 200m = 5.0 (FAILS)
```

**Solution**:
```yaml
resources:
  requests:
    cpu: 250m      # Increased from 200m
  limits:
    cpu: 1000m
# New ratio: 1000/250 = 4.0 ✅
```

**Prevention**:
- Run validation: `python3 scripts/validate_gke_autopilot_compliance.py`
- Pre-commit hook automatically checks

#### B. Memory Limit/Request Ratio Violation
**Error**: `memory max limit to request ratio per Container is 4, but provided ratio is X`

**Solution**: Same as CPU - ensure ratio ≤ 4.0

---

### 6. Liveness/Readiness Probe Failures

**Symptoms**:
- Pod restarts frequently
- Events show: `Liveness probe failed` or `Readiness probe failed`

**Diagnosis**:
```bash
# Check probe configuration
kubectl get deployment <deployment> -n <namespace> -o yaml | grep -A 10 "livenessProbe:"
```

**Common Causes**:

#### A. Probe Endpoint Not Available
**Error**: `connection refused` or `404 Not Found`

**Solutions**:
- Verify health endpoint exists and is accessible
- Check port numbers match
- Ensure health endpoint doesn't require authentication

#### B. Probe Timeout Too Short
**Solutions**:
```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 60    # Increase if app starts slowly
  periodSeconds: 30
  timeoutSeconds: 10          # Increase if endpoint is slow
  failureThreshold: 3
```

#### C. Missing Health Check Extension
**Error** (OTEL Collector): `connection refused on port 13133`

**Root Cause**: health_check extension not enabled

**Solution**:
```yaml
# In OTEL Collector config
extensions:
  health_check:
    endpoint: 0.0.0.0:13133

service:
  extensions: [health_check]  # Must be enabled!
```

---

## Step-by-Step Troubleshooting

### Step 1: Identify the Problem

```bash
# Get overview of all pods
kubectl get pods -n <namespace>

# Identify problematic pods
kubectl get pods -n <namespace> | grep -vE "Running|Completed"
```

### Step 2: Gather Information

```bash
# Describe pod for detailed info
kubectl describe pod <pod-name> -n <namespace>

# Check logs
kubectl logs <pod-name> -n <namespace>
kubectl logs <pod-name> -n <namespace> --previous

# Check events
kubectl get events -n <namespace> --sort-by='.lastTimestamp' | tail -50
```

### Step 3: Analyze Root Cause

Use the patterns above to match symptoms to common causes.

### Step 4: Apply Fix

Follow solution steps for the identified problem.

### Step 5: Verify Fix

```bash
# Watch pod status
kubectl get pods -n <namespace> -w

# Check if pod is running and ready
kubectl get pod <pod-name> -n <namespace>

# Verify no restarts
kubectl describe pod <pod-name> -n <namespace> | grep "Restart Count:"
```

### Step 6: Clean Up

```bash
# Delete old ReplicaSets (keep last 2-3 for rollback)
kubectl delete replicaset <old-replicaset-name> -n <namespace>

# Scale down deployments if needed
kubectl scale deployment <deployment> --replicas=<count> -n <namespace>
```

---

## Prevention Checklist

### Before Deployment

- [ ] Run validation script:
  ```bash
  python3 scripts/validate_gke_autopilot_compliance.py deployments/overlays/<overlay>
  ```

- [ ] Run regression tests:
  ```bash
  pytest tests/regression/test_pod_deployment_regression.py -v
  ```

- [ ] Verify kustomize builds:
  ```bash
  kubectl kustomize deployments/overlays/<overlay> | kubectl apply --dry-run=client -f -
  ```

- [ ] Check resource ratios (GKE Autopilot):
  - CPU ratio ≤ 4.0
  - Memory ratio ≤ 4.0

- [ ] Verify no environment variable conflicts:
  - No env vars with both `value` and `valueFrom`

- [ ] Test in development/staging first

### After Deployment

- [ ] Monitor pod status for 10 minutes
- [ ] Check logs for errors
- [ ] Verify metrics are being collected
- [ ] Test application functionality
- [ ] Set up alerts for pod failures

---

## Automated Tools

### 1. Validation Script
```bash
# Validate all overlays
python3 scripts/validate_gke_autopilot_compliance.py deployments/overlays

# Validate specific overlay
python3 scripts/validate_gke_autopilot_compliance.py deployments/overlays/staging-gke
```

**Checks**:
- CPU/memory limit/request ratios
- Environment variable configuration
- readOnlyRootFilesystem volume mounts

### 2. Regression Tests
```bash
# Run all regression tests
pytest tests/regression/test_pod_deployment_regression.py -v

# Run specific test
pytest tests/regression/test_pod_deployment_regression.py::TestGKEAutopilotCompliance::test_cpu_limit_request_ratio -v
```

### 3. Pre-commit Hook
```bash
# Install
git config core.hooksPath .githooks
chmod +x .githooks/pre-commit

# Will automatically run on git commit
git commit -m "message"
```

### 4. CI/CD Pipeline
GitHub Actions workflow automatically runs on every PR:
- Kustomize build validation
- GKE Autopilot compliance checks
- Regression test suite

---

## Quick Reference

### Essential Commands

```bash
# Get pod status
kubectl get pods -n <namespace>

# Describe pod
kubectl describe pod <pod-name> -n <namespace>

# Get logs
kubectl logs <pod-name> -c <container> -n <namespace>

# Get previous logs (after restart)
kubectl logs <pod-name> -c <container> -n <namespace> --previous

# Get events
kubectl get events -n <namespace> --sort-by='.lastTimestamp'

# Delete pod (forces recreation)
kubectl delete pod <pod-name> -n <namespace>

# Rollout restart deployment
kubectl rollout restart deployment/<deployment> -n <namespace>

# Rollback deployment
kubectl rollout undo deployment/<deployment> -n <namespace>

# Scale deployment
kubectl scale deployment/<deployment> --replicas=<count> -n <namespace>
```

### Resource Commands

```bash
# Check node resources
kubectl top nodes

# Check pod resources
kubectl top pods -n <namespace>

# Get resource quotas
kubectl get resourcequota -n <namespace>

# Get limit ranges
kubectl get limitrange -n <namespace>
```

### Debugging Commands

```bash
# Execute command in pod
kubectl exec -it <pod-name> -c <container> -n <namespace> -- /bin/sh

# Port forward to pod
kubectl port-forward <pod-name> <local-port>:<pod-port> -n <namespace>

# Copy files from pod
kubectl cp <namespace>/<pod-name>:<path> <local-path>
```

---

## Additional Resources

- [Staging Pod Crash Remediation Report](./STAGING_POD_CRASH_REMEDIATION.md)
- [GKE Autopilot Resource Limits](https://cloud.google.com/kubernetes-engine/docs/concepts/autopilot-resource-requests)
- [Kubernetes Pod Lifecycle](https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/)
- [Debugging Pods](https://kubernetes.io/docs/tasks/debug/debug-application/debug-pods/)

---

## Changelog

- 2025-11-12: Initial version based on staging pod crash investigation
