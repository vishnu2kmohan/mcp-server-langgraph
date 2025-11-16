# Session 2 Quick Reference - Helm/Kubernetes Fixes

## At a Glance

**Total Issues**: 12
**Categories**: Pod Scheduling (3), Security (4), Health Checks (2), Resources (2), Documentation (1)
**Estimated Time**: 24-32 hours across 3 priority tiers
**Key Focus**: Production readiness, pod stability, security hardening

---

## Critical P0 Issues (6-8 hours)

### 1. Keycloak readOnlyRootFilesystem ⚠️ [2-3h]
- **File**: `deployments/base/keycloak-deployment.yaml`
- **Issue**: Currently disabled due to incomplete volume mounts
- **Fix**: Add `/opt/keycloak/lib` and `/opt/keycloak/providers` emptyDir volumes
- **Test**: `tests/regression/test_pod_deployment_regression.py`

### 2. GKE Autopilot CPU Ratios ⚠️ [1-2h]
- **File**: `deployments/overlays/staging-gke/otel-collector-patch.yaml`
- **Issue**: OTEL CPU ratio 5.0 > GKE max 4.0
- **Fix**: Increase CPU request 200m → 250m
- **Test**: `scripts/validate_gke_autopilot_compliance.py`

### 3. Network Policy JGroups Egress ✅ [1h]
- **File**: `deployments/overlays/staging-gke/network-policy.yaml`
- **Issue**: Verify TCP/7800 egress exists for Keycloak clustering
- **Status**: Already fixed, needs cross-environment validation
- **Test**: `tests/deployment/test_network_policies.py`

### 4. Cloud SQL Proxy Health Probes ⚠️ [2-3h]
- **File**: `deployments/overlays/staging-gke/cloud-sql-proxy-patch.yaml`
- **Issue**: Probes may use wrong port (5432 instead of 9801)
- **Fix**: Ensure `/liveness` and `/readiness` on port 9801
- **Test**: `tests/deployment/test_cloud_sql_proxy_config.py`

---

## High Priority P1 Issues (12-16 hours)

### 5. Topology Spread Constraints ❌ [2-3h]
- **File**: `deployments/base/deployment.yaml`
- **Add**: `topologySpreadConstraints` with zone (maxSkew: 1) and node (maxSkew: 2)
- **Why**: Ensures pods spread across zones for HA
- **Test**: NEW test needed

### 6. Pod Anti-Affinity Severity ⚠️ [1-2h]
- **File**: `deployments/base/deployment.yaml`
- **Change**: `preferred` → `required` for hostname topology
- **Keep**: Soft `preferred` for zone topology
- **Why**: Prevents accidental co-location on same node

### 7. Startup Probes ❌ [2-3h]
- **File**: `deployments/base/deployment.yaml`
- **Add**: `startupProbe` with 30+ failure threshold (60s wait)
- **Why**: MCP Server takes 10-15s to initialize
- **Test**: `tests/deployment/test_staging_deployment_requirements.py`

### 8. Resource Request/Limit Ratios ⚠️ [3-4h]
- **Files**: All deployments
- **Audit**: Check all CPU/memory ratios
- **Standardize**: Aim for 2.0-3.0 ratios (GKE allows up to 4.0)
- **Test**: `tests/regression/test_pod_deployment_regression.py`

### 9. Network Policy Hardening ⚠️ [3-4h]
- **File**: `deployments/base/networkpolicy.yaml`
- **Change**: Allow only specific egress (DNS, in-cluster, LLM APIs)
- **Why**: Implements zero-trust / least privilege
- **Test**: `tests/deployment/test_network_policies.py`

---

## Medium Priority P2 Issues (7-9 hours)

### 10. Helm Values Schema Validation ⚠️ [2-3h]
- **File**: `deployments/argocd/applications/mcp-server-app.yaml`
- **Check**: Ensure `postgresql.*` values match chart schema
- **Test**: NEW test for ArgoCD values validation

### 11. OTEL Config Hardening ⚠️ [2h]
- **File**: `deployments/overlays/staging-gke/otel-collector-configmap-patch.yaml`
- **Add**: Validation script to detect bash syntax and deprecated keys
- **Add**: Pre-commit hook for validation
- **Test**: `tests/regression/test_pod_deployment_regression.py:test_otel_collector_config_syntax`

### 12. Deployment Documentation ❌ [3-4h]
- **Create**: `docs-internal/DEPLOYMENT_CONFIGURATION_GUIDE.md`
- **Update**: `docs-internal/operations/DEPLOYMENT_CHECKLIST.md`
- **Create**: `docs-internal/operations/DEPLOYMENT_TROUBLESHOOTING.md`

---

## Work Phases

### Phase 1: P0 Critical (Day 1-2)
```bash
# 1. Validate network policy
pytest tests/deployment/test_network_policies.py -v

# 2. Fix OTEL CPU ratio
# Edit: deployments/overlays/staging-gke/otel-collector-patch.yaml
# Change: cpu: 200m -> 250m

# 3. Fix/validate Cloud SQL probes
pytest tests/deployment/test_cloud_sql_proxy_config.py -v

# 4. Fix Keycloak readOnlyFilesystem
# Edit: deployments/base/keycloak-deployment.yaml
# Add: lib and providers volume mounts
# Edit: deployments/overlays/staging-gke/keycloak-patch.yaml
# Change: readOnlyRootFilesystem: false -> true
```

### Phase 2: P1 High (Day 2-4)
```bash
# 1. Add startup probe
# Edit: deployments/base/deployment.yaml
# Add: startupProbe with httpGet /health/startup, failureThreshold: 30

# 2. Add topology spread constraints
# Edit: deployments/base/deployment.yaml
# Add: topologySpreadConstraints for zone (maxSkew: 1) and node (maxSkew: 2)

# 3. Fix pod anti-affinity
# Edit: deployments/base/deployment.yaml
# Change: preferred -> required for hostname topology

# 4. Audit and fix resource ratios
grep -r "requests:\|limits:" deployments/base/ | tee resource-audit.txt
# Standardize CPU/memory ratios across all deployments

# 5. Harden network policies
# Edit: deployments/base/networkpolicy.yaml
# Replace permissive rules with specific egress rules
```

### Phase 3: P2 Medium (Day 4-5)
```bash
# 1. Validate Helm schema
pytest tests/deployment/test_helm_configuration.py -v

# 2. Add OTEL validation script
# Create: scripts/validate_otel_config.py
# Add hook to .pre-commit-config.yaml

# 3. Write deployment documentation
# Create: docs-internal/DEPLOYMENT_CONFIGURATION_GUIDE.md
# Update: docs-internal/operations/DEPLOYMENT_CHECKLIST.md
# Create: docs-internal/operations/DEPLOYMENT_TROUBLESHOOTING.md
```

---

## Key Test Commands

```bash
# Validate all Kubernetes manifests
python scripts/validate_gke_autopilot_compliance.py deployments/overlays/staging-gke

# Run deployment tests
pytest tests/deployment/ -v

# Run regression tests
pytest tests/regression/test_pod_deployment_regression.py -v

# Validate Helm templates
helm lint deployments/helm/mcp-server-langgraph/
helm template test-release deployments/helm/mcp-server-langgraph/ | kubectl apply --dry-run=client -f -

# Validate kustomize builds
kustomize build deployments/overlays/staging-gke/ | kubectl apply --dry-run=client -f -
kustomize build deployments/overlays/production-gke/ | kubectl apply --dry-run=client -f -
```

---

## Success Checklist

### P0 Complete
- [ ] All pods start without crashes (livenessProbe doesn't trigger early)
- [ ] GKE Autopilot compliance check shows 0 violations
- [ ] Network policies allow required traffic, deny unauthorized
- [ ] kubectl get pods shows all READY 1/1

### P1 Complete
- [ ] Pods distributed: each zone has 1-2 pods (not all in one zone)
- [ ] Nodes check: no pod pair on same node (anti-affinity working)
- [ ] Slow startup services don't timeout (startup probe covers initialization)
- [ ] Node evictions prevented (resource requests match actual usage)

### P2 Complete
- [ ] Helm template renders successfully
- [ ] OTEL config validation passes
- [ ] Documentation matches current configuration

---

## File Dependencies

**Critical Files**:
- `/home/vishnu/git/vishnu2kmohan/worktrees/mcp-server-langgraph-session-20251116-105811/deployments/base/deployment.yaml` (5 issues)
- `/home/vishnu/git/vishnu2kmohan/worktrees/mcp-server-langgraph-session-20251116-105811/deployments/base/keycloak-deployment.yaml` (1 issue)
- `/home/vishnu/git/vishnu2kmohan/worktrees/mcp-server-langgraph-session-20251116-105811/deployments/base/networkpolicy.yaml` (1 issue)

**Overlay Files**:
- `/home/vishnu/git/vishnu2kmohan/worktrees/mcp-server-langgraph-session-20251116-105811/deployments/overlays/staging-gke/keycloak-patch.yaml` (1 issue)
- `/home/vishnu/git/vishnu2kmohan/worktrees/mcp-server-langgraph-session-20251116-105811/deployments/overlays/staging-gke/otel-collector-patch.yaml` (1 issue)
- `/home/vishnu/git/vishnu2kmohan/worktrees/mcp-server-langgraph-session-20251116-105811/deployments/overlays/staging-gke/network-policy.yaml` (1 issue)

**Test Files**:
- `/home/vishnu/git/vishnu2kmohan/worktrees/mcp-server-langgraph-session-20251116-105811/tests/deployment/test_network_policies.py`
- `/home/vishnu/git/vishnu2kmohan/worktrees/mcp-server-langgraph-session-20251116-105811/tests/regression/test_pod_deployment_regression.py`
- `/home/vishnu/git/vishnu2kmohan/worktrees/mcp-server-langgraph-session-20251116-105811/tests/deployment/test_staging_deployment_requirements.py`
- `/home/vishnu/git/vishnu2kmohan/worktrees/mcp-server-langgraph-session-20251116-105811/tests/deployment/test_cloud_sql_proxy_config.py`

---

## TDD Approach for Each Issue

1. **Write test first** (RED phase) - Define what "fixed" looks like
2. **Run test, confirm failure** - Proves test is valid
3. **Implement fix** (GREEN phase) - Minimal code change
4. **Run test, confirm pass** - Fix complete
5. **Document** (REFACTOR phase) - Add comments, update docs

---

## Related Historical Documents

- `docs-internal/operations/POD_FAILURE_PREVENTION_IMPLEMENTATION_SUMMARY.md` - Previous pod crash fixes
- `docs-internal/operations/STAGING_POD_CRASH_REMEDIATION.md` - Keycloak readOnly issue history
- `docs-internal/operations/STAGING_DEPLOYMENT_FIX_REPORT.md` - Network policy JGroups fix
- `adr/adr-0054-pod-failure-prevention-framework.md` - Framework for preventing future issues

---

**Status**: Ready for Session 2 implementation
**Last Updated**: 2025-11-16
**Effort Estimate**: 24-32 hours
**Priority**: P0 > P1 > P2
