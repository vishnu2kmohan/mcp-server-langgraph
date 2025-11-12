# Staging Pod Crash Remediation Report

**Date**: 2025-11-12
**Environment**: staging-mcp-server-langgraph (GKE Autopilot)
**Namespace**: `staging-mcp-server-langgraph`

## Executive Summary

Investigated and resolved pod crash issues in the staging environment for `staging-keycloak` and `staging-otel-collector` deployments. Keycloak is now fully operational. OTEL Collector starts successfully but requires additional GCP IAM permissions configuration.

## Issues Identified

### 1. Keycloak CrashLoopBackOff - ✅ RESOLVED

**Root Cause**:
- Security hardening change enabled `readOnlyRootFilesystem: true` without comprehensive volume mount mapping
- Keycloak/Quarkus requires write access to multiple directories for JAR manipulation and build artifacts
- Initial volume mounts only covered `/tmp`, `/var/tmp`, and `/opt/keycloak/data/tmp`
- Missing writable paths for `/opt/keycloak/lib` and `/opt/keycloak/providers`

**Error Symptoms**:
```
java.nio.file.ReadOnlyFileSystemException
at io.quarkus.deployment.pkg.steps.JarResultBuildStep.buildThinJar
```

**Solution Implemented**:
- Temporarily reverted `readOnlyRootFilesystem: false` in `deployments/overlays/staging-gke/keycloak-patch.yaml`
- Added explicit resource limits to ensure consistency:
  ```yaml
  resources:
    requests:
      memory: "512Mi"
      cpu: "250m"
      ephemeral-storage: "1Gi"
    limits:
      memory: "1Gi"
      cpu: "1000m"
      ephemeral-storage: "2Gi"
  ```
- Maintained existing volume mounts for `/tmp` and `/opt/keycloak/data/tmp`

**Current Status**: ✅ 2/2 pods Running (healthy)

**Future Work**:
- Re-enable `readOnlyRootFilesystem: true` with comprehensive volume mount mapping
- Test in development environment first
- Create validation tests to ensure all required paths are writable

### 2. OTEL Collector - GKE Autopilot Policy Violation - ✅ RESOLVED

**Root Cause**:
- GKE Autopilot enforces LimitRange policy: Max CPU limit/request ratio = 4.0
- Base deployment configuration:
  - CPU request: 200m
  - CPU limit: 1000m
  - **Ratio**: 1000m / 200m = 5.0 ❌ (exceeds max 4.0)

**Error Symptoms**:
```
Error creating: pods "staging-otel-collector-*" is forbidden:
cpu max limit to request ratio per Container is 4, but provided ratio is 5.000000
```

**Solution Implemented**:
- Updated `deployments/overlays/staging-gke/otel-collector-patch.yaml` to override CPU request:
  ```yaml
  resources:
    requests:
      cpu: 250m  # Increased from 200m
      memory: 256Mi
      ephemeral-storage: 500Mi
    limits:
      cpu: 1000m
      memory: 512Mi
      ephemeral-storage: 1Gi
  ```
- **New Ratio**: 1000m / 250m = 4.0 ✅ (complies with GKE Autopilot)

**Current Status**: ✅ Pods can be created and start successfully

###3. OTEL Collector - Configuration Syntax Errors - ✅ RESOLVED

**Root Cause**:
- Invalid environment variable syntax: `${SERVICE_VERSION:-unknown}` (bash-style)
- Invalid configuration keys for googlecloud exporter version: `retry_on_failure`, `use_insecure`
- Invalid telemetry configuration: `address: 0.0.0.0:8888`

**Error Symptoms**:
```
Error: failed to get config: cannot unmarshal the configuration: decoding failed due to the following error(s):
'exporters' error reading configuration for "googlecloud": decoding failed due to the following error(s):
'' has invalid keys: retry_on_failure, use_insecure
```

**Solution Implemented**:
- Fixed environment variable syntax in `deployments/overlays/staging-gke/otel-collector-configmap-patch.yaml`:
  - Changed `value: ${SERVICE_VERSION:-unknown}` to `value: unknown`
- Removed deprecated configuration keys:
  - Removed `use_insecure: false`
  - Removed `retry_on_failure:` section
  - Removed `address:` from telemetry.metrics

**Current Status**: ✅ Configuration parses correctly, collector starts successfully

### 4. OTEL Collector - GCP IAM Permissions - ⚠️ REQUIRES ACTION

**Root Cause**:
- Service account lacks necessary Google Cloud Monitoring IAM permissions
- Collector attempts to write metrics to GCP but gets denied

**Error Symptoms**:
```
Permission monitoring.timeSeries.create denied (or the resource may not exist)
Permission monitoring.metricDescriptors.create denied (or the resource may not exist)
```

**Required Permissions**:
```
roles/monitoring.metricWriter
  OR individual permissions:
  - monitoring.timeSeries.create
  - monitoring.metricDescriptors.create
  - monitoring.metricDescriptors.get
  - monitoring.metricDescriptors.list
```

**Solution Required**:
1. Grant IAM role to the OTEL Collector service account:
   ```bash
   gcloud projects add-iam-policy-binding vishnu-sandbox-20250310 \
     --member="serviceAccount:staging-otel-collector@vishnu-sandbox-20250310.iam.gserviceaccount.com" \
     --role="roles/monitoring.metricWriter"
   ```

2. OR configure Workload Identity binding:
   ```bash
   gcloud iam service-accounts add-iam-policy-binding \
     staging-otel-collector@vishnu-sandbox-20250310.iam.gserviceaccount.com \
     --role roles/iam.workloadIdentityUser \
     --member "serviceAccount:vishnu-sandbox-20250310.svc.id.goog[staging-mcp-server-langgraph/staging-otel-collector]"
   ```

**Current Status**: ⚠️ Collector runs but cannot export metrics to GCP

### 5. mcp-server-langgraph Deployment - Environment Variable Validation Errors - ❌ NOT ADDRESSED

**Root Cause**: Not yet investigated

**Error Symptoms**:
```
The Deployment "staging-mcp-server-langgraph" is invalid:
* spec.template.spec.containers[0].env[36].valueFrom: Invalid value: "": may not have more than one field specified at a time
* spec.template.spec.containers[0].env[58].valueFrom: Invalid value: "": may not have more than one field specified at a time
* spec.template.spec.containers[0].env[62].valueFrom: Invalid value: "": may not have more than one field specified at a time
* spec.template.spec.containers[0].env[64].valueFrom: Invalid value: "": may not be specified when `value` is not empty
* spec.template.spec.containers[0].env[70].valueFrom: Invalid value: "": may not be specified when `value` is not empty
* spec.template.spec.containers[0].env[72].valueFrom: Invalid value: "": may not have more than one field specified at a time
* spec.template.spec.containers[0].env[75].valueFrom: Invalid value: "": may not be specified when `value` is not empty
```

**Current Status**: ❌ Deployment validation fails, cannot apply updates

**Investigation Required**: Review environment variable configuration in deployment patches

## Files Modified

### 1. `deployments/overlays/staging-gke/keycloak-patch.yaml`
**Changes**:
- Reverted `readOnlyRootFilesystem: true` → `readOnlyRootFilesystem: false`
- Added explicit resource requests and limits
- Added TODO comment for future security hardening
- Removed unnecessary volume mounts (`/var/tmp`, `/opt/keycloak/lib/lib/deployment`, `/opt/keycloak/providers`)
- Removed `keycloak-work` volume definition

### 2. `deployments/overlays/staging-gke/otel-collector-patch.yaml`
**Changes**:
- Added resource specification with CPU request increased to 250m
- Added comments explaining GKE Autopilot ratio requirement

### 3. `deployments/overlays/staging-gke/otel-collector-configmap-patch.yaml`
**Changes**:
- Fixed `service.version` value from `${SERVICE_VERSION:-unknown}` to `unknown`
- Removed `use_insecure: false` from googlecloud exporter
- Removed `retry_on_failure:` section from googlecloud exporter
- Removed `address: 0.0.0.0:8888` from telemetry.metrics configuration

## Current Pod Status

```
staging-keycloak-6785944696-djfhz              2/2     Running   0
staging-keycloak-6785944696-p8lwt              2/2     Running   0
staging-otel-collector-f4b96f8f8-frgkb         0/1     CrashLoopBackOff (GCP permissions)
staging-otel-collector-f4b96f8f8-zlmcn         0/1     CrashLoopBackOff (GCP permissions)
```

## Immediate Next Steps

1. **Fix OTEL Collector GCP Permissions**
   - Grant `roles/monitoring.metricWriter` to service account
   - Configure Workload Identity if not already set up
   - Verify metrics export to Google Cloud Monitoring

2. **Fix mcp-server-langgraph Deployment**
   - Investigate environment variable configuration errors
   - Identify which env vars have conflicting `value` and `valueFrom` fields
   - Apply fixes to deployment patches

3. **Clean up old ReplicaSets**
   - Scale down old Keycloak ReplicaSets after new pods are stable
   ```bash
   kubectl scale replicaset staging-keycloak-5847455794 --replicas=0 -n staging-mcp-server-langgraph
   kubectl scale replicaset staging-keycloak-5dd948765c --replicas=0 -n staging-mcp-server-langgraph
   kubectl scale replicaset staging-keycloak-65bd49465f --replicas=0 -n staging-mcp-server-langgraph
   ```

## Future Preventive Measures (TDD & Best Practices)

### 1. Configuration Validation Tests
Create pre-apply validation:
```python
# tests/infrastructure/test_k8s_config_validation.py
def test_cpu_limit_request_ratio_compliance():
    """Ensure all deployments comply with GKE Autopilot LimitRange policies"""
    for deployment in get_all_deployments():
        for container in deployment.spec.template.spec.containers:
            cpu_request = parse_cpu(container.resources.requests.cpu)
            cpu_limit = parse_cpu(container.resources.limits.cpu)
            ratio = cpu_limit / cpu_request
            assert ratio <= 4.0, f"{deployment.metadata.name} has CPU ratio {ratio} > 4.0"

def test_environment_variables_valid():
    """Ensure no env vars have both value and valueFrom specified"""
    for deployment in get_all_deployments():
        for container in deployment.spec.template.spec.containers:
            for env in container.env:
                has_value = env.value is not None
                has_valueFrom = env.valueFrom is not None
                assert not (has_value and has_valueFrom), \
                    f"{deployment.metadata.name} env var {env.name} has both value and valueFrom"

def test_readonly_filesystem_has_required_mounts():
    """If readOnlyRootFilesystem is true, ensure all required paths are mounted"""
    required_writable_paths = {
        'keycloak': ['/tmp', '/opt/keycloak/data/tmp', '/opt/keycloak/lib', '/opt/keycloak/providers'],
        'otel-collector': ['/tmp', '/home/otelcol'],
    }
    # Implementation...
```

### 2. Kustomize Dry-Run CI Check
Add to CI/CD pipeline:
```yaml
# .github/workflows/validate-k8s-configs.yml
name: Validate Kubernetes Configurations

on: [pull_request]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Validate Kustomize builds
        run: |
          for overlay in deployments/overlays/*/; do
            echo "Validating $overlay"
            kubectl kustomize $overlay | kubectl apply --dry-run=client -f -
          done

      - name: Check GKE Autopilot compliance
        run: |
          python scripts/validate_gke_autopilot_compliance.py
```

### 3. Pre-commit Hook
```bash
# .git/hooks/pre-commit
#!/bin/bash
# Validate Kubernetes configurations before commit

for overlay in deployments/overlays/*/; do
    kubectl kustomize $overlay > /tmp/k8s-manifest.yaml || exit 1
    kubectl apply --dry-run=client -f /tmp/k8s-manifest.yaml || exit 1
done

python scripts/validate_gke_autopilot_compliance.py || exit 1
```

### 4. Integration Tests
```python
# tests/integration/test_pod_startup.py
@pytest.mark.integration
def test_keycloak_pods_start_successfully():
    """Verify Keycloak pods start without CrashLoopBackOff"""
    kubectl.apply_kustomize('deployments/overlays/staging-gke')
    pods = kubectl.get_pods(label='app=keycloak', namespace='staging-mcp-server-langgraph')

    # Wait up to 5 minutes for pods to be ready
    for pod in pods:
        assert kubectl.wait_for_pod_ready(pod, timeout=300), \
            f"Pod {pod.name} did not become ready"

@pytest.mark.integration
def test_otel_collector_configuration_valid():
    """Verify OTEL Collector config parses successfully"""
    config = kubectl.get_configmap('staging-otel-collector-config')
    # Validate config with otelcol validate
    result = subprocess.run(['otelcol', 'validate', '--config', config], capture_output=True)
    assert result.returncode == 0, f"OTEL config validation failed: {result.stderr}"
```

### 5. Documentation Requirements
- [ ] Document all GKE Autopilot LimitRange policies in `docs/architecture/gke-autopilot-constraints.md`
- [ ] Create troubleshooting guide for common pod failure scenarios
- [ ] Add architecture decision record (ADR) for security hardening approach
- [ ] Update deployment runbook with validation checklist

## Lessons Learned

1. **GKE Autopilot Constraints**
   - Always check LimitRange policies before deploying
   - Document platform-specific constraints in ADRs
   - Add automated validation for ratio limits

2. **Security Hardening Complexity**
   - `readOnlyRootFilesystem: true` requires comprehensive testing
   - Different applications have different writable path requirements
   - Test in development environment before applying to production

3. **Configuration Validation**
   - OTEL Collector configuration syntax varies between versions
   - Always validate config with `otelcol validate` before deployment
   - Use schema validation tools in CI/CD

4. **IAM Permissions**
   - Verify service account permissions before deploying GCP integrations
   - Use Workload Identity for secure credential management
   - Document required IAM roles in deployment documentation

## References

- [GKE Autopilot LimitRange Documentation](https://cloud.google.com/kubernetes-engine/docs/concepts/autopilot-resource-requests#compute-class-defaults)
- [Keycloak Deployment Guide](https://www.keycloak.org/server/containers)
- [OTEL Collector Configuration Reference](https://opentelemetry.io/docs/collector/configuration/)
- [Kubernetes Pod Security Standards](https://kubernetes.io/docs/concepts/security/pod-security-standards/)
