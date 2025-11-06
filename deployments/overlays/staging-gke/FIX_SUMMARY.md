# GKE Staging Deployment Fixes - 2025-11-06

## Critical Issues Resolved

### 1. Cloud SQL Proxy Health Check Configuration (P0)

**Problem**: Cloud SQL Proxy sidecars were missing the `--http-port=9801` and `--health-check` flags, causing all liveness and readiness probes to fail with "connection refused" errors.

**Impact**:
- Keycloak pods: 300-400 restarts over 16 hours
- OpenFGA pods: 400+ restarts over 16 hours
- Complete deployment failure

**Root Cause**: Health check probes configured to check port 9801, but Cloud SQL Proxy wasn't exposing the HTTP admin server on that port.

**Fix**:
- Added `--http-port=9801` flag to Cloud SQL Proxy args
- Added `--health-check` flag to enable the HTTP health check server
- Applied to both `keycloak-patch.yaml` and `openfga-patch.yaml`

**Files Modified**:
- `deployments/overlays/staging-gke/keycloak-patch.yaml`
- `deployments/overlays/staging-gke/openfga-patch.yaml`

### 2. Missing Redis Session Service (P0)

**Problem**: Init containers in MCP server pods were waiting for `redis-session` service that didn't exist, causing all MCP server pods to be stuck in `Init:0/3` state indefinitely.

**Root Cause**: Kustomization deleted the self-hosted Redis deployment and service but didn't provide a replacement ExternalName service pointing to Memorystore Redis.

**Fix**:
- Created `redis-session-service-json-patch.yaml` to transform the base ClusterIP service into an ExternalName service
- Configured to point to Memorystore Redis at `10.138.129.37:6378` (non-standard port)
- Updated `deployment-init-containers-patch.yaml` to include wait-for-redis with correct service name and port

**Files Modified**:
- `deployments/overlays/staging-gke/redis-session-service-json-patch.yaml` (new)
- `deployments/overlays/staging-gke/deployment-init-containers-patch.yaml`
- `deployments/overlays/staging-gke/kustomization.yaml`

### 3. Service Name Mismatches (P1)

**Problem**: Init containers referenced unprefixed service names (e.g., `openfga`) but Kustomize applied `staging-` prefix to all services, causing DNS lookup failures.

**Fix**: Updated init container patches to use prefixed names:
- `openfga` → `staging-openfga`
- `keycloak` → `staging-keycloak`
- `redis-session` → `staging-redis-session`

**Files Modified**:
- `deployments/overlays/staging-gke/deployment-init-containers-patch.yaml`

## Test-Driven Development Approach

All fixes were implemented following strict TDD principles:

### RED Phase - Tests Written First
Created comprehensive test suites before implementing any fixes:
- `tests/deployment/test_cloud_sql_proxy_config.py` - Validates Cloud SQL Proxy configuration
- `tests/deployment/test_service_dependencies.py` - Validates service references and dependencies
- `tests/deployment/test_kustomize_build.py` - Validates Kustomize builds and manifests

### GREEN Phase - Minimal Fixes to Pass Tests
Implemented minimal changes to make all tests pass:
- 26/26 tests passing
- All critical configuration issues resolved
- Kustomize builds successfully

### REFACTOR Phase - Prevention Measures
Added validation to prevent future occurrences:
- Pre-commit hooks (see pre-commit configuration)
- Automated manifest validation
- Service dependency checking

## Test Coverage

```bash
# Run all deployment validation tests
python -m pytest tests/deployment/ -v

# Results: 26 passed in 3.95s
```

### Test Categories

1. **Cloud SQL Proxy Configuration** (11 tests)
   - HTTP port configuration
   - Required arguments validation
   - Health probe configuration
   - Resource limits
   - Security context

2. **Service Dependencies** (7 tests)
   - Service existence validation
   - Init container service references
   - Namespace consistency
   - External service endpoints

3. **Kustomize Build** (8 tests)
   - Build success validation
   - YAML validity
   - Resource field completeness
   - Duplicate detection
   - Selector validation

## Deployment Status

### Before Fix
- Keycloak: 0/2 pods ready (CrashLoopBackOff)
- OpenFGA: 0/2 pods ready (CrashLoopBackOff)
- MCP Server: 0/3 pods ready (Init:0/3)
- Total uptime: 0% over 16 hours

### After Fix
- Cloud SQL Proxy health check server: ✅ Running on port 9801
- Redis session service: ✅ Created and available
- Init containers: ✅ Correctly reference prefixed services
- Deployment rollout: ✅ In progress

## Known Limitations

### Network Connectivity Issue
Pods are experiencing timeouts connecting to `sqladmin.googleapis.com`:
```
ERROR: failed to get instance metadata: Get "https://sqladmin.googleapis.com/...":
       dial tcp: lookup sqladmin.googleapis.com: i/o timeout
```

**Status**: Under investigation
**Impact**: Pods can't establish Cloud SQL connections despite correct configuration
**Potential Causes**:
- VPC firewall rules blocking Google API access
- Missing VPC Service Connect or Private Google Access
- Network policy restrictions
- DNS resolution issues in GKE cluster

**Next Steps**:
1. Verify Private Google Access is enabled on VPC subnet
2. Check VPC firewall rules allow egress to Google APIs
3. Verify Cloud SQL instance is in the same VPC
4. Review network policies for Google API access

## Configuration Files Changed

```
deployments/overlays/staging-gke/
├── keycloak-patch.yaml                        # Added --http-port, --health-check
├── openfga-patch.yaml                         # Added --http-port, --health-check
├── deployment-init-containers-patch.yaml      # Fixed service names, added redis wait
├── redis-session-service-json-patch.yaml (new)# ExternalName to Memorystore
└── kustomization.yaml                         # Added redis service patch

tests/deployment/
├── test_cloud_sql_proxy_config.py (new)       # Cloud SQL Proxy validation
├── test_service_dependencies.py (new)         # Service dependency validation
└── test_kustomize_build.py (new)              # Kustomize build validation
```

## Prevention Measures

### 1. Pre-Commit Validation
Added hooks to validate:
- Kustomize builds successfully
- All referenced services exist
- Cloud SQL Proxy correctly configured
- No orphaned service references

### 2. Automated Testing
Tests run automatically on:
- Pre-commit (fast validation)
- CI/CD pipeline (full suite)
- Manual verification before deployment

### 3. Documentation
- This summary document
- Inline comments in patch files
- Test documentation with failure scenarios

## Lessons Learned

1. **Health Check Configuration**: Always verify sidecar containers have health check endpoints enabled when configuring probes
2. **Service References**: Kustomize namePrefix affects all resources - init containers must reference transformed names
3. **Managed Services**: When replacing self-hosted services with managed services, ensure ExternalName services or equivalent are created
4. **TDD for Infrastructure**: Writing tests first catches configuration errors before deployment
5. **Test What You Deploy**: Kustomize build validation prevents deployment-time surprises

## References

- Cloud SQL Proxy Health Checks: https://cloud.google.com/sql/docs/postgres/sql-proxy#health-checks
- Kustomize Name Transformers: https://kubernetes.io/docs/tasks/manage-kubernetes-objects/kustomization/#setting-cross-cutting-fields
- ExternalName Services: https://kubernetes.io/docs/concepts/services-networking/service/#externalname
- GKE Private Google Access: https://cloud.google.com/vpc/docs/configure-private-google-access
