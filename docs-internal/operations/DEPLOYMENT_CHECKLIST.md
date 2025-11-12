# Kubernetes Deployment Checklist

**Purpose**: Pre-deployment checklist to prevent pod failures and ensure successful deployments

**Target Audience**: DevOps Engineers, Platform Engineers, SREs

**Last Updated**: 2025-11-12

---

## Pre-Deployment Validation

### 1. Configuration Validation

- [ ] **Kustomize builds successfully**
  ```bash
  kubectl kustomize deployments/overlays/<overlay-name>
  ```

- [ ] **Dry-run validation passes**
  ```bash
  kubectl kustomize deployments/overlays/<overlay-name> | kubectl apply --dry-run=client -f -
  ```

- [ ] **No validation errors in output**
  - Check for "Invalid value" errors
  - Check for missing required fields
  - Check for schema violations

### 2. GKE Autopilot Compliance (for GKE deployments)

- [ ] **Run automated validation**
  ```bash
  python3 scripts/validate_gke_autopilot_compliance.py deployments/overlays/<overlay-name>
  ```

- [ ] **CPU limit/request ratio ≤ 4.0**
  - Formula: `cpu_limit / cpu_request`
  - Example valid: 1000m / 250m = 4.0 ✅
  - Example invalid: 1000m / 200m = 5.0 ❌

- [ ] **Memory limit/request ratio ≤ 4.0**
  - Formula: `memory_limit / memory_request`

- [ ] **CPU/Memory within allowed ranges**
  - CPU: min 50m, max 4 cores
  - Memory: min 64Mi, max 8Gi

### 3. Security Configuration

- [ ] **If readOnlyRootFilesystem = true**
  - [ ] `/tmp` is mounted as writable volume
  - [ ] All application writable paths have volume mounts
  - [ ] Tested in development environment first

- [ ] **No privileged containers** (unless required)

- [ ] **Non-root user specified**
  ```yaml
  securityContext:
    runAsNonRoot: true
    runAsUser: <uid>
  ```

- [ ] **Capabilities dropped**
  ```yaml
  securityContext:
    capabilities:
      drop:
      - ALL
  ```

### 4. Resource Specifications

- [ ] **All containers have resource requests and limits**
  ```yaml
  resources:
    requests:
      cpu: <value>
      memory: <value>
    limits:
      cpu: <value>
      memory: <value>
  ```

- [ ] **Resource requests are realistic**
  - Based on actual usage patterns
  - Not over-provisioned
  - Not under-provisioned

- [ ] **Ephemeral storage specified if needed**
  ```yaml
  resources:
    requests:
      ephemeral-storage: 1Gi
    limits:
      ephemeral-storage: 2Gi
  ```

### 5. Environment Variables

- [ ] **No env vars with both `value` and `valueFrom`**
  ```yaml
  # INVALID:
  env:
  - name: MY_VAR
    value: "something"
    valueFrom:  # Cannot have both!
      secretKeyRef:
        name: my-secret
        key: my-key

  # VALID:
  env:
  - name: MY_VAR
    valueFrom:
      secretKeyRef:
        name: my-secret
        key: my-key
  ```

- [ ] **All valueFrom sources have exactly one key**
  - `configMapKeyRef` OR `secretKeyRef` OR `fieldRef` (not multiple)

- [ ] **All referenced secrets exist**
  ```bash
  kubectl get secret <secret-name> -n <namespace>
  ```

- [ ] **All referenced configmaps exist**
  ```bash
  kubectl get configmap <configmap-name> -n <namespace>
  ```

### 6. Health Probes

- [ ] **Liveness probe configured**
  ```yaml
  livenessProbe:
    httpGet:
      path: /health/live
      port: 8000
    initialDelaySeconds: 30
    periodSeconds: 10
  ```

- [ ] **Readiness probe configured**
  ```yaml
  readinessProbe:
    httpGet:
      path: /health/ready
      port: 8000
    initialDelaySeconds: 10
    periodSeconds: 5
  ```

- [ ] **Probe endpoints exist and are accessible**
  - Test endpoint returns 200 OK when healthy
  - Endpoint doesn't require authentication

- [ ] **initialDelaySeconds is sufficient for app startup**

- [ ] **Timeout and period values are appropriate**

### 7. Volumes and Storage

- [ ] **All required volumes are defined**
  ```yaml
  volumes:
  - name: tmp
    emptyDir: {}
  ```

- [ ] **All volume mounts reference existing volumes**

- [ ] **PersistentVolumeClaims exist and are bound**
  ```bash
  kubectl get pvc -n <namespace>
  ```

- [ ] **Storage class is available**
  ```bash
  kubectl get storageclass
  ```

### 8. Networking

- [ ] **Service exists for deployment (if needed)**
  ```bash
  kubectl get service -n <namespace>
  ```

- [ ] **Service ports match container ports**

- [ ] **Network policies allow required traffic**
  ```bash
  kubectl get networkpolicy -n <namespace>
  ```

- [ ] **Ingress configured correctly (if needed)**

### 9. IAM and Permissions

- [ ] **ServiceAccount exists**
  ```bash
  kubectl get serviceaccount -n <namespace>
  ```

- [ ] **Workload Identity configured (for GCP)**
  ```yaml
  metadata:
    annotations:
      iam.gke.io/gcp-service-account: <gcp-sa>@<project>.iam.gserviceaccount.com
  ```

- [ ] **GCP service account has required IAM roles**
  ```bash
  gcloud iam service-accounts get-iam-policy <sa-email>
  ```

- [ ] **Workload Identity binding configured**
  ```bash
  gcloud iam service-accounts add-iam-policy-binding <sa-email> \
    --role roles/iam.workloadIdentityUser \
    --member "serviceAccount:<project>.svc.id.goog[<namespace>/<ksa>]"
  ```

### 10. Image Configuration

- [ ] **Image tag is immutable (not `latest`)**
  - Use specific version tags or commit SHAs

- [ ] **Image exists in registry**
  ```bash
  docker pull <image>:<tag>
  ```

- [ ] **Image pull secrets configured (if private registry)**

- [ ] **imagePullPolicy set appropriately**
  - `Always` for staging/production
  - `IfNotPresent` for development

---

## Post-Deployment Validation

### 1. Immediate Checks (0-5 minutes)

- [ ] **All pods are Running**
  ```bash
  kubectl get pods -n <namespace>
  ```

- [ ] **No restarts occurring**
  ```bash
  watch kubectl get pods -n <namespace>
  ```

- [ ] **Check logs for startup errors**
  ```bash
  kubectl logs <pod-name> -n <namespace>
  ```

- [ ] **Health checks passing**
  ```bash
  kubectl describe pod <pod-name> -n <namespace> | grep -A 5 "Readiness:"
  ```

### 2. Short-term Monitoring (5-30 minutes)

- [ ] **Pods remain stable (no CrashLoopBackOff)**

- [ ] **Memory/CPU usage is reasonable**
  ```bash
  kubectl top pods -n <namespace>
  ```

- [ ] **No errors in application logs**

- [ ] **Metrics are being collected**

- [ ] **External dependencies are reachable**
  - Database connections working
  - External API calls succeeding

### 3. Functional Testing

- [ ] **Application endpoints are accessible**
  ```bash
  kubectl port-forward <pod> 8080:8080 -n <namespace>
  curl http://localhost:8080/health
  ```

- [ ] **Core functionality works**
  - Test critical user flows
  - Verify data persistence
  - Check integrations

- [ ] **Performance is acceptable**
  - Response times normal
  - No unusual latency

### 4. Long-term Monitoring (24-48 hours)

- [ ] **Set up alerts for**:
  - Pod restarts
  - OOM kills
  - Probe failures
  - Error rate increases

- [ ] **Monitor resource usage trends**

- [ ] **Check for memory leaks**

- [ ] **Verify log aggregation working**

---

## Rollback Procedure

If issues are detected post-deployment:

### 1. Quick Rollback
```bash
# Rollback to previous revision
kubectl rollout undo deployment/<deployment> -n <namespace>

# Verify rollback succeeded
kubectl rollout status deployment/<deployment> -n <namespace>
```

### 2. Rollback to Specific Revision
```bash
# List revisions
kubectl rollout history deployment/<deployment> -n <namespace>

# Rollback to specific revision
kubectl rollout undo deployment/<deployment> --to-revision=<revision> -n <namespace>
```

### 3. Rollback with Kustomize
```bash
# Revert Git changes
git revert <commit-hash>

# Reapply previous configuration
kubectl apply -k deployments/overlays/<overlay> --namespace=<namespace>
```

---

## Tools and Scripts

### Available Tools:
1. `scripts/validate_gke_autopilot_compliance.py` - Validation script
2. `tests/regression/test_pod_deployment_regression.py` - Regression tests
3. `.githooks/pre-commit` - Pre-commit validation hook
4. `.github/workflows/validate-k8s-configs.yml` - CI/CD pipeline

### Usage Examples:
```bash
# Validate before deploying
python3 scripts/validate_gke_autopilot_compliance.py deployments/overlays/production-gke

# Run all regression tests
pytest tests/regression/ -v

# Install pre-commit hook
git config core.hooksPath .githooks
```

---

## Common Mistakes to Avoid

1. ❌ **Deploying without validation**
   - Always run validation script first

2. ❌ **Enabling readOnlyRootFilesystem without testing**
   - Test in development first
   - Ensure all writable paths are mounted

3. ❌ **Not checking CPU/memory ratios on GKE Autopilot**
   - Ratio must be ≤ 4.0

4. ❌ **Using `latest` image tag**
   - Use specific versions or commit SHAs

5. ❌ **Not testing rollback procedure**
   - Verify you can rollback before deploying

6. ❌ **Insufficient health probe delays**
   - Account for slow application startup

7. ❌ **Missing IAM permissions**
   - Verify service account permissions before deploying

8. ❌ **Not monitoring after deployment**
   - Watch pods for at least 10 minutes

9. ❌ **Forgetting to delete old ReplicaSets**
   - Clean up after successful deployment

10. ❌ **Not documenting changes**
    - Always document what was changed and why

---

## Emergency Contacts

- **Platform Team**: @platform-team
- **On-Call Engineer**: Check PagerDuty
- **Documentation**: See [STAGING_POD_CRASH_REMEDIATION.md](./STAGING_POD_CRASH_REMEDIATION.md)

---

## Related Documentation

- [Pod Failure Troubleshooting Runbook](./POD_FAILURE_TROUBLESHOOTING_RUNBOOK.md)
- [Staging Pod Crash Remediation](./STAGING_POD_CRASH_REMEDIATION.md)
- [GKE Autopilot Best Practices](https://cloud.google.com/kubernetes-engine/docs/concepts/autopilot-overview)
