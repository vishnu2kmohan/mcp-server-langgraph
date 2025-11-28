# Kubernetes Security Requirements

Comprehensive security requirements for all Kubernetes deployments to prevent security vulnerabilities and pass automated security scans (Trivy, Kubesec).

## Table of Contents

1. [Security Context Requirements](#security-context-requirements)
2. [Container Security](#container-security)
3. [Volume Mounts for Read-Only Root Filesystem](#volume-mounts-for-read-only-root-filesystem)
4. [Automated Validation](#automated-validation)
5. [Common Issues and Solutions](#common-issues-and-solutions)
6. [Examples](#examples)

---

## Security Context Requirements

### Pod-Level Security Context

All deployments MUST define a pod-level security context:

```yaml
spec:
  template:
    spec:
      securityContext:
        runAsNonRoot: true
        runAsUser: 10000          # Non-root UID
        runAsGroup: 10000         # Non-root GID
        fsGroup: 10000            # File system group
        seccompProfile:
          type: RuntimeDefault    # Enable seccomp
```

**Rationale**:
- **runAsNonRoot**: Prevents containers from running as root user (security best practice)
- **runAsUser/runAsGroup**: Explicit non-root user reduces attack surface
- **fsGroup**: Ensures consistent file permissions
- **seccompProfile**: Restricts system calls available to containers

### Container-Level Security Context

**ALL containers** (including init containers) MUST define a security context:

```yaml
containers:
- name: my-container
  securityContext:
    allowPrivilegeEscalation: false   # REQUIRED
    runAsNonRoot: true                # REQUIRED
    runAsUser: 10000                  # REQUIRED
    runAsGroup: 10000                 # REQUIRED
    readOnlyRootFilesystem: true      # REQUIRED
    capabilities:
      drop:
        - ALL                         # REQUIRED
```

**Requirements**:

| Setting | Value | Severity | Reason |
|---------|-------|----------|--------|
| `allowPrivilegeEscalation` | `false` | **HIGH** | Prevents privilege escalation attacks |
| `runAsNonRoot` | `true` | **HIGH** | Prevents running as root |
| `runAsUser` | Non-zero integer | **HIGH** | Explicit non-root UID |
| `readOnlyRootFilesystem` | `true` | **HIGH** | Prevents filesystem tampering (AVD-KSV-0014) |
| `capabilities.drop` | `[ALL]` | **HIGH** | Removes all Linux capabilities |

---

## Container Security

### Read-Only Root Filesystem

**Requirement**: ALL containers MUST have `readOnlyRootFilesystem: true`

**Why**: Prevents container from modifying its own filesystem, reducing attack surface.

**Trivy Check**: AVD-KSV-0014 (HIGH severity)

**Example Violation**:
```yaml
# ❌ BAD - Security scan will FAIL
securityContext:
  readOnlyRootFilesystem: false   # HIGH severity finding
```

**Correct Implementation**:
```yaml
# ✅ GOOD - Security scan will PASS
securityContext:
  readOnlyRootFilesystem: true
```

**When Required**: ALL containers without exception

---

## Volume Mounts for Read-Only Root Filesystem

When `readOnlyRootFilesystem: true` is enabled, containers cannot write to their filesystem. Applications requiring writable directories MUST use volume mounts.

### Keycloak Example

Keycloak requires writable directories for:
- Temporary files
- Build artifacts
- Cache
- Data storage
- Providers
- Themes

**Implementation**:

```yaml
containers:
- name: keycloak
  securityContext:
    readOnlyRootFilesystem: true
  volumeMounts:
    # Temporary files
    - name: tmp
      mountPath: /tmp
    # Keycloak-specific directories
    - name: cache
      mountPath: /opt/keycloak/data/tmp
    - name: work-dir
      mountPath: /opt/keycloak/data
    - name: providers
      mountPath: /opt/keycloak/providers
    - name: themes
      mountPath: /opt/keycloak/themes

volumes:
  - name: tmp
    emptyDir: {}
  - name: cache
    emptyDir: {}
  - name: work-dir
    emptyDir: {}
  - name: providers
    emptyDir: {}
  - name: themes
    emptyDir: {}
```

### Common Writable Directories by Application

| Application | Required Writable Directories |
|-------------|------------------------------|
| **Keycloak** | `/tmp`, `/opt/keycloak/data`, `/opt/keycloak/data/tmp`, `/opt/keycloak/providers`, `/opt/keycloak/themes` |
| **PostgreSQL** | `/tmp`, `/var/lib/postgresql/data` |
| **Redis** | `/tmp`, `/data` |
| **Nginx** | `/tmp`, `/var/cache/nginx`, `/var/run` |
| **Init containers** | Usually just `/tmp` |

### Best Practices for Volume Mounts

1. **Use emptyDir for ephemeral data**:
   ```yaml
   volumes:
   - name: tmp
     emptyDir: {}
   ```

2. **Set size limits for production** (optional but recommended):
   ```yaml
   volumes:
   - name: tmp
     emptyDir:
       sizeLimit: 500Mi
   ```

3. **Use PersistentVolumes for persistent data**:
   ```yaml
   volumes:
   - name: data
     persistentVolumeClaim:
       claimName: my-app-data
   ```

---

## Automated Validation

### Pre-commit Hooks

Security requirements are enforced by pre-commit hooks:

**Trivy Security Scan** (`.pre-commit-config.yaml`):
```yaml
- id: trivy-scan-k8s-manifests
  name: Trivy Security Scan for Kubernetes Manifests
  files: ^deployments/.*\.(yaml|yml)$
```

Runs automatically on:
- Every commit touching deployment files
- Scans for CRITICAL and HIGH severity findings
- Fails commit if violations found

**Install Trivy**:
```bash
# macOS
brew install trivy

# Linux
curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh -s -- -b /usr/local/bin
```

### CI/CD Validation

**GitHub Actions** (`.github/workflows/quality-tests.yaml`):
```yaml
- name: Validate pre-commit hook configuration
  run: uv run --frozen pytest tests/regression/test_precommit_hook_dependencies.py -v
```

Validates:
- Pre-commit hooks properly configured
- Python hooks use isolated environments
- Dependencies specified correctly

### Test Suite

**Security Hardening Tests** (`tests/deployment/test_security_hardening.py`):

Automated tests validate:
1. ✅ All containers have `readOnlyRootFilesystem: true`
2. ✅ All containers have `runAsNonRoot: true`
3. ✅ All containers have `allowPrivilegeEscalation: false`
4. ✅ All containers drop ALL capabilities

**Run tests**:
```bash
uv run --frozen pytest tests/deployment/test_security_hardening.py -v
```

**Pre-deployment Validation** (`tests/deployment/test_staging_deployment_requirements.py`):

Validates staging-specific requirements:
1. ✅ Cloud SQL Proxy sidecar configured
2. ✅ Database connection via localhost
3. ✅ Health probes properly configured
4. ✅ Volume mounts for writable directories

---

## Common Issues and Solutions

### Issue 1: Container Fails to Start (Read-Only Filesystem)

**Symptom**: Pod crashes with "Read-only file system" error

**Root Cause**: Application trying to write to filesystem without volume mount

**Example Error**:
```
Error: EROFS: read-only file system, open '/opt/keycloak/data/h2/keycloakdb.mv.db'
```

**Solution**: Add volume mount for the writable directory

```yaml
volumeMounts:
  - name: work-dir
    mountPath: /opt/keycloak/data

volumes:
  - name: work-dir
    emptyDir: {}
```

### Issue 2: Trivy Scan Failure (AVD-KSV-0014)

**Symptom**: Pre-commit hook or CI fails with HIGH severity finding

**Error**:
```
AVD-KSV-0014 (HIGH): Container 'keycloak' should set 'securityContext.readOnlyRootFilesystem' to true
```

**Solution**: Set `readOnlyRootFilesystem: true` and add necessary volume mounts

**Before**:
```yaml
securityContext:
  readOnlyRootFilesystem: false  # FAILS security scan
```

**After**:
```yaml
securityContext:
  readOnlyRootFilesystem: true   # PASSES security scan
volumeMounts:
  - name: tmp
    mountPath: /tmp
volumes:
  - name: tmp
    emptyDir: {}
```

### Issue 3: Init Container Missing Security Context

**Symptom**: Security tests fail - init container has `readOnlyRootFilesystem=None`

**Root Cause**: Init containers inherit pod-level security context but should have explicit container-level settings

**Solution**: Add explicit security context to ALL init containers

```yaml
initContainers:
- name: wait-for-postgres
  securityContext:
    allowPrivilegeEscalation: false
    runAsNonRoot: true
    runAsUser: 10000
    runAsGroup: 10000
    readOnlyRootFilesystem: true
    capabilities:
      drop:
        - ALL
```

### Issue 4: Different Security Settings Between Overlays

**Symptom**: Staging passes security scan but production fails

**Root Cause**: Inconsistent security contexts between base deployment and overlays

**Solution**: Establish baseline security in base deployment, enhance in overlays

**Base Deployment** (`deployments/base/keycloak-deployment.yaml`):
```yaml
# Minimum security requirements for ALL environments
securityContext:
  allowPrivilegeEscalation: false
  runAsNonRoot: true
  runAsUser: 10000
  readOnlyRootFilesystem: true
  capabilities:
    drop:
      - ALL
```

**Staging/Production Overlays** (patch files):
```yaml
# Additional security hardening for specific environments
# Keep base requirements, add environment-specific enhancements
```

---

## Examples

### Complete Keycloak Deployment (Secure)

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: keycloak
  namespace: mcp-server-langgraph
spec:
  replicas: 2
  template:
    spec:
      # Pod-level security context
      securityContext:
        runAsNonRoot: true
        runAsUser: 10000
        fsGroup: 10000
        seccompProfile:
          type: RuntimeDefault

      # Init container with full security
      initContainers:
      - name: wait-for-postgres
        image: busybox:1.36
        securityContext:
          allowPrivilegeEscalation: false
          runAsNonRoot: true
          runAsUser: 10000
          readOnlyRootFilesystem: true
          capabilities:
            drop:
              - ALL

      # Main container with full security
      containers:
      - name: keycloak
        image: quay.io/keycloak/keycloak:26.4.2
        securityContext:
          allowPrivilegeEscalation: false
          runAsNonRoot: true
          runAsUser: 10000
          runAsGroup: 10000
          readOnlyRootFilesystem: true
          capabilities:
            drop:
              - ALL
        volumeMounts:
          - name: tmp
            mountPath: /tmp
          - name: cache
            mountPath: /opt/keycloak/data/tmp
          - name: work-dir
            mountPath: /opt/keycloak/data
          - name: providers
            mountPath: /opt/keycloak/providers
          - name: themes
            mountPath: /opt/keycloak/themes

      # Volumes for writable directories
      volumes:
        - name: tmp
          emptyDir: {}
        - name: cache
          emptyDir: {}
        - name: work-dir
          emptyDir: {}
        - name: providers
          emptyDir: {}
        - name: themes
          emptyDir: {}
```

### Staging Overlay with Cloud SQL Proxy (Secure)

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: keycloak
spec:
  template:
    spec:
      containers:
      - name: keycloak
        # Inherits base security context
        volumeMounts:
          - name: tmp
            mountPath: /tmp
          - name: cache
            mountPath: /opt/keycloak/data/tmp
          - name: work-dir
            mountPath: /opt/keycloak/data
          - name: providers
            mountPath: /opt/keycloak/providers
          - name: themes
            mountPath: /opt/keycloak/themes

      # Cloud SQL Proxy sidecar (also secure)
      - name: cloud-sql-proxy
        image: gcr.io/cloud-sql-connectors/cloud-sql-proxy:2.14.1
        securityContext:
          allowPrivilegeEscalation: false
          runAsNonRoot: true
          runAsUser: 65532
          readOnlyRootFilesystem: true
          capabilities:
            drop:
              - ALL
        volumeMounts:
          - name: tmp
            mountPath: /tmp

      volumes:
        - name: tmp
          emptyDir: {}
        - name: cache
          emptyDir: {}
        - name: work-dir
          emptyDir: {}
        - name: providers
          emptyDir: {}
        - name: themes
          emptyDir: {}
```

---

## Validation Checklist

Use this checklist before committing deployment changes:

### Required for ALL Containers

- [ ] `securityContext.allowPrivilegeEscalation: false`
- [ ] `securityContext.runAsNonRoot: true`
- [ ] `securityContext.runAsUser: <non-zero>`
- [ ] `securityContext.runAsGroup: <non-zero>`
- [ ] `securityContext.readOnlyRootFilesystem: true`
- [ ] `securityContext.capabilities.drop: [ALL]`

### Required for Containers with Read-Only Filesystem

- [ ] Volume mount for `/tmp`
- [ ] Volume mounts for application-specific writable directories
- [ ] Corresponding `volumes` section defines emptyDir/PVC

### Pod-Level Requirements

- [ ] `spec.securityContext.runAsNonRoot: true`
- [ ] `spec.securityContext.runAsUser: <non-zero>`
- [ ] `spec.securityContext.fsGroup: <non-zero>`
- [ ] `spec.securityContext.seccompProfile.type: RuntimeDefault`

### Automated Validation

- [ ] Trivy scan passes (no CRITICAL/HIGH findings)
- [ ] Security hardening tests pass
- [ ] Pre-deployment validation tests pass

---

## References

- **Trivy Security Scanner**: https://aquasecurity.github.io/trivy/
- **Kubernetes Security Context**: https://kubernetes.io/docs/tasks/configure-pod-container/security-context/
- **CIS Kubernetes Benchmark**: https://www.cisecurity.org/benchmark/kubernetes
- **Security Hardening Tests**: `tests/deployment/test_security_hardening.py`
- **Staging Validation**: `tests/deployment/test_staging_deployment_requirements.py`
- **Pre-commit Hooks**: `.pre-commit-config.yaml`

---

## Incident History

### 2025-11-12: Keycloak readOnlyRootFilesystem Violation

**Incident**: Deploy to GKE Staging workflow failed (Run #19309378657)

**Finding**: Trivy scan detected AVD-KSV-0014 (HIGH severity)
- Keycloak container had `readOnlyRootFilesystem: false`
- Security risk: allows container to tamper with filesystem
- Blocked staging deployment

**Resolution**:
1. Set `readOnlyRootFilesystem: true`
2. Added volume mounts for `/tmp`, `/opt/keycloak/data`, etc.
3. Created regression test `test_security_hardening.py`
4. Added Trivy scan to pre-commit hooks

**Prevention**:
- Automated security scans in pre-commit hooks
- Regression tests validate all containers
- CI validates security requirements before deployment

---

## Changelog

### 2025-11-12: Initial Version
- Created comprehensive security requirements documentation
- Documented readOnlyRootFilesystem requirement (AVD-KSV-0014)
- Added volume mount patterns for common applications
- Included automated validation setup
- Documented incident from staging deployment failure
- Added examples and troubleshooting guide

**Context**: Created following remediation of Deploy to GKE Staging failure (Run #19309378657)
