# Session 2: Comprehensive Helm/Kubernetes Configuration Action Plan

**Date**: 2025-11-16
**Based on**: OpenAI Codex Findings Analysis + Historical Pod Failure Prevention
**Priority**: P0-P2 across 3 categories
**Total Estimated Effort**: 24-32 hours

---

## Executive Summary

Comprehensive analysis of Codex findings and historical remediation documents identified **12 specific Kubernetes/Helm issues** organized into 3 priority tiers. Issues span pod scheduling, security hardening, health probes, network policies, and deployment configurations. All issues have existing test infrastructure and validation frameworks in place.

**Key Stat**: 5 critical pod failures already remediated in previous sessions; Session 2 focuses on hardening against recurrence and implementing advanced scheduling features.

---

## Priority Tier Assessment

| Priority | Count | Category | Effort | Impact |
|----------|-------|----------|--------|--------|
| **P0 (Critical)** | 4 | Pod Failure Prevention, Security | 8-10h | Production stability |
| **P1 (High)** | 5 | Advanced Scheduling, Resource Mgmt | 10-14h | Reliability, efficiency |
| **P2 (Medium)** | 3 | Documentation, Edge Cases | 6-8h | Maintainability |

---

# P0: CRITICAL ISSUES

## Issue P0-1: Keycloak readOnlyRootFilesystem Incomplete Hardening

**Status**: ⚠️ PARTIAL - Temporarily Disabled
**Severity**: CRITICAL (Security hardening incomplete)
**Files Affected**:
- `/home/vishnu/git/vishnu2kmohan/worktrees/mcp-server-langgraph-session-20251116-105811/deployments/overlays/preview-gke/keycloak-patch.yaml`
- `/home/vishnu/git/vishnu2kmohan/worktrees/mcp-server-langgraph-session-20251116-105811/deployments/base/keycloak-deployment.yaml` (lines 62-85)

**Test Files**:
- `/home/vishnu/git/vishnu2kmohan/worktrees/mcp-server-langgraph-session-20251116-105811/tests/regression/test_pod_deployment_regression.py`
- `/home/vishnu/git/vishnu2kmohan/worktrees/mcp-server-langgraph-session-20251116-105811/tests/deployment/test_staging_deployment_requirements.py`

**Problem**:
Keycloak deployment currently has `readOnlyRootFilesystem: false` due to incomplete volume mount mapping for Quarkus JAR manipulation. When enabled with `readOnlyRootFilesystem: true`, the pod crashes with:
```
java.nio.file.ReadOnlyFileSystemException
at io.quarkus.deployment.pkg.steps.JarResultBuildStep.buildThinJar
```

**Root Cause**:
Quarkus/Keycloak requires write access to multiple directories:
- `/opt/keycloak/lib` - Library directory for JAR artifacts
- `/opt/keycloak/providers` - Custom provider directory
- `/opt/keycloak/data/tmp` - Temporary data directory (partially fixed)

Current volume mounts only cover `/tmp` and `/opt/keycloak/data/tmp`.

**Fix**:
1. **Extend volume mounts** in `keycloak-deployment.yaml`:
   ```yaml
   volumeMounts:
   - name: tmp-volume
     mountPath: /tmp
   - name: keycloak-tmp
     mountPath: /opt/keycloak/data/tmp
   - name: lib-volume            # ADD
     mountPath: /opt/keycloak/lib
   - name: providers-volume      # ADD
     mountPath: /opt/keycloak/providers
   ```

2. **Define ephemeral volumes**:
   ```yaml
   volumes:
   - name: tmp-volume
     emptyDir: {}
   - name: keycloak-tmp
     emptyDir: {}
   - name: lib-volume            # ADD
     emptyDir:
       sizeLimit: 500Mi
   - name: providers-volume      # ADD
     emptyDir:
       sizeLimit: 100Mi
   ```

3. **Re-enable security hardening**:
   ```yaml
   securityContext:
     readOnlyRootFilesystem: true  # Change from false
   ```

4. **Add validation test** (TDD):
   ```python
   def test_keycloak_readonly_filesystem_has_all_required_mounts():
       """Validate all Quarkus paths have writable volumes"""
       required_paths = [
           '/tmp',
           '/opt/keycloak/lib',
           '/opt/keycloak/providers',
           '/opt/keycloak/data/tmp'
       ]
       # Kustomize build and validate mounts exist
   ```

**Validation**:
- [ ] Kustomize build succeeds
- [ ] Deploy to staging, verify pod reaches Running state
- [ ] Keycloak health endpoint returns `UP`
- [ ] Cluster formation succeeds (2/2 pods ready)
- [ ] Security scanner confirms readOnlyRootFilesystem: true

**Priority**: P0
**Effort**: 2-3 hours (mapping + testing + validation)
**Related**: ADR-0054, POD_FAILURE_PREVENTION_IMPLEMENTATION_SUMMARY.md

---

## Issue P0-2: GKE Autopilot CPU Ratio Violations (OTEL Collector)

**Status**: ✅ PARTIALLY FIXED, Needs Validation
**Severity**: CRITICAL (Blocks pod creation)
**Files Affected**:
- `/home/vishnu/git/vishnu2kmohan/worktrees/mcp-server-langgraph-session-20251116-105811/deployments/overlays/preview-gke/otel-collector-patch.yaml`
- `/home/vishnu/git/vishnu2kmohan/worktrees/mcp-server-langgraph-session-20251116-105811/deployments/base/otel-collector-deployment.yaml`

**Test Files**:
- `/home/vishnu/git/vishnu2kmohan/worktrees/mcp-server-langgraph-session-20251116-105811/tests/regression/test_pod_deployment_regression.py`
- `/home/vishnu/git/vishnu2kmohan/worktrees/mcp-server-langgraph-session-20251116-105811/scripts/validate_gke_autopilot_compliance.py`

**Problem**:
GKE Autopilot enforces strict resource ratio limits: CPU limit/request ratio ≤ 4.0

Current configuration (problematic):
- CPU request: 200m
- CPU limit: 1000m
- **Ratio**: 1000m / 200m = **5.0** ❌ (exceeds 4.0 max)

Error on pod creation:
```
cpu max limit to request ratio per Container is 4, but provided ratio is 5.000000
```

**Fix**:
1. **Update CPU request in otel-collector-patch.yaml**:
   ```yaml
   spec:
     template:
       spec:
         containers:
         - name: otel-collector
           resources:
             requests:
               cpu: 250m          # Increase from 200m
               memory: 256Mi
               ephemeral-storage: 500Mi
             limits:
               cpu: 1000m         # Keep at 1000m
               memory: 512Mi
               ephemeral-storage: 1Gi
   ```

2. **Verify ratio**: 1000m / 250m = **4.0** ✅

3. **Add validation to pre-commit hook**:
   ```python
   def validate_gke_autopilot_ratios(manifest):
       """Ensure CPU limit/request ratio ≤ 4.0"""
       ratio = cpu_limit / cpu_request
       assert ratio <= 4.0, f"Ratio {ratio} exceeds GKE Autopilot max 4.0"
   ```

**Validation**:
- [ ] Kustomize build succeeds for preview-gke overlay
- [ ] Deploy OTEL collector pod, verify it reaches Running state
- [ ] No GKE policy violation errors in events
- [ ] Validation script confirms compliance: `python scripts/validate_gke_autopilot_compliance.py deployments/overlays/preview-gke`

**Priority**: P0
**Effort**: 1-2 hours (config update + testing)
**Related**: STAGING_POD_CRASH_REMEDIATION.md, POD_FAILURE_PREVENTION_IMPLEMENTATION_SUMMARY.md

---

## Issue P0-3: Network Policy Missing Egress Rules for Keycloak Clustering

**Status**: ✅ FIXED (Verified in previous session)
**Severity**: CRITICAL (Cluster formation failure)
**Files Affected**:
- `/home/vishnu/git/vishnu2kmohan/worktrees/mcp-server-langgraph-session-20251116-105811/deployments/overlays/preview-gke/network-policy.yaml`
- `/home/vishnu/git/vishnu2kmohan/worktrees/mcp-server-langgraph-session-20251116-105811/deployments/base/keycloak-networkpolicy.yaml`

**Test Files**:
- `/home/vishnu/git/vishnu2kmohan/worktrees/mcp-server-langgraph-session-20251116-105811/tests/deployment/test_network_policies.py`
- `/home/vishnu/git/vishnu2kmohan/worktrees/mcp-server-langgraph-session-20251116-105811/tests/deployment/test_staging_deployment_requirements.py`

**Problem**:
Keycloak uses JGroups for distributed clustering on TCP/7800 (and management on 9000). Network policies allowed **ingress** but blocked **egress** to pod-to-pod traffic, preventing cluster formation.

Error observed:
```
java.net.SocketTimeoutException on TCP/7800
Cluster health: DOWN (1/2 pods in CrashLoopBackOff)
```

**Fix Status**: ✅ ALREADY FIXED
Current preview-gke/network-policy.yaml includes:
```yaml
egress:
- to:
  - podSelector:
      matchLabels:
        app: keycloak
  ports:
  - port: 7800    # JGroups cluster communication
    protocol: TCP
  - port: 9000    # Management endpoint
    protocol: TCP
```

**Validation Required**:
- [ ] Verify egress rules exist in all environment overlays (dev, staging, production)
- [ ] Test cluster formation: Deploy 2 Keycloak pods, verify both reach Ready state
- [ ] Verify JGroups cluster health endpoint: `GET /health/cluster` returns `UP`
- [ ] Run test: `pytest tests/deployment/test_network_policies.py::TestNetworkPolicySelectors -v`

**Priority**: P0
**Effort**: 1 hour (verification + cross-environment validation)
**Related**: STAGING_DEPLOYMENT_FIX_REPORT.md

---

## Issue P0-4: Cloud SQL Proxy Health Probe Misconfiguration

**Status**: ⚠️ NEEDS HARDENING
**Severity**: CRITICAL (Pod health checks may fail)
**Files Affected**:
- `/home/vishnu/git/vishnu2kmohan/worktrees/mcp-server-langgraph-session-20251116-105811/deployments/overlays/preview-gke/cloud-sql-proxy-patch.yaml` (if exists)
- `/home/vishnu/git/vishnu2kmohan/worktrees/mcp-server-langgraph-session-20251116-105811/deployments/base/deployment.yaml` (cloud-sql-proxy sidecar, if added)

**Test Files**:
- `/home/vishnu/git/vishnu2kmohan/worktrees/mcp-server-langgraph-session-20251116-105811/tests/deployment/test_cloud_sql_proxy_config.py`

**Problem**:
Cloud SQL Proxy (when used as sidecar) exposes health check on port 9801. Probe configuration must:
1. Use correct port (9801, not 5432 or 3306)
2. Use correct endpoints (`/liveness`, `/readiness`)
3. Have appropriate timeout/failure thresholds

If misconfigured, probes fail with "connection refused" → pod killed → CrashLoopBackOff

**Fix**:
1. **Ensure proxy patch has proper probes**:
   ```yaml
   containers:
   - name: cloud-sql-proxy
     image: gcr.io/cloud-sql-connectors/cloud-sql-proxy:2.7.0
     ports:
     - name: health
       containerPort: 9801
     livenessProbe:
       httpGet:
         port: health          # port 9801
         path: /liveness
       initialDelaySeconds: 10
       periodSeconds: 10
       timeoutSeconds: 5
       failureThreshold: 3
     readinessProbe:
       httpGet:
         port: health          # port 9801
         path: /readiness
       initialDelaySeconds: 5
       periodSeconds: 5
       timeoutSeconds: 3
       failureThreshold: 3
   ```

2. **Verify proxy startup args**:
   ```yaml
   args:
   - --instances=PROJECT_ID:REGION:INSTANCE
   - --port=5432            # PostgreSQL port binding (internal)
   - --max-connections=10
   - --health-check         # Enable health checks
   ```

3. **Add validation test** (TDD):
   ```python
   def test_cloud_sql_proxy_probes_use_correct_port():
       """Verify health probes use port 9801"""
       manifest = load_patch('cloud-sql-proxy-patch.yaml')
       proxy = manifest['spec']['template']['spec']['containers'][0]

       liveness = proxy['livenessProbe']
       assert liveness['httpGet']['port'] == 9801
       assert liveness['httpGet']['path'] == '/liveness'

       readiness = proxy['readinessProbe']
       assert readiness['httpGet']['port'] == 9801
       assert readiness['httpGet']['path'] == '/readiness'
   ```

**Validation**:
- [ ] Deployment renders successfully with proxy patch
- [ ] Deploy to staging, proxy pod reaches Running state
- [ ] Health checks return 200 OK
- [ ] Database connections successful through proxy
- [ ] Test passes: `pytest tests/deployment/test_cloud_sql_proxy_config.py -v`

**Priority**: P0
**Effort**: 2-3 hours (if proxy patch doesn't exist; 30 min if already exists, just needs validation)
**Related**: test_cloud_sql_proxy_config.py

---

# P1: HIGH PRIORITY ISSUES

## Issue P1-1: Topology Spread Constraints Not Configured

**Status**: ❌ NOT IMPLEMENTED
**Severity**: HIGH (Uneven pod distribution across zones)
**Files Affected**:
- `/home/vishnu/git/vishnu2kmohan/worktrees/mcp-server-langgraph-session-20251116-105811/deployments/base/deployment.yaml` (line 251+)

**Test Files**:
- `/home/vishnu/git/vishnu2kmohan/worktrees/mcp-server-langgraph-session-20251116-105811/tests/deployment/test_staging_deployment_requirements.py` (new test needed)

**Problem**:
MCP Server deployment (3 replicas) lacks topology spread constraints. In multi-zone clusters (GKE standard), pods may cluster in a single zone, violating:
- High availability best practices
- Even load distribution
- Resilience to zone failures

**Current State**: Deployment specifies `affinity.podAntiAffinity.preferredDuringSchedulingIgnoredDuringExecution` but NOT topology constraints.

**Fix**:
1. **Add topology spread constraints** to `deployment.yaml`:
   ```yaml
   spec:
     template:
       spec:
         topologySpreadConstraints:
         - maxSkew: 1
           topologyKey: topology.kubernetes.io/zone
           whenUnsatisfiable: DoNotSchedule  # Prefer strict; change to ScheduleAnyway if necessary
           labelSelector:
             matchLabels:
               app: mcp-server-langgraph
         - maxSkew: 2
           topologyKey: kubernetes.io/hostname
           whenUnsatisfiable: ScheduleAnyway
           labelSelector:
             matchLabels:
               app: mcp-server-langgraph
   ```

2. **Explanation**:
   - **Zone spread**: Ensures max 1-pod difference per zone (highly available)
   - **Node spread**: Ensures distributed across nodes (reduces blast radius)
   - **DoNotSchedule**: Fails pod creation if constraint violated (strict safety)

3. **Add validation test**:
   ```python
   def test_deployment_has_topology_spread_constraints():
       """Verify mcp-server has zone-aware topology constraints"""
       manifest = load_manifest('deployment.yaml')
       constraints = manifest['spec']['template']['spec']['topologySpreadConstraints']

       # Should have zone constraint
       zone_constraint = [c for c in constraints
                         if c['topologyKey'] == 'topology.kubernetes.io/zone']
       assert len(zone_constraint) == 1, "Missing zone topology constraint"
       assert zone_constraint[0]['maxSkew'] == 1, "Zone maxSkew should be 1"
   ```

**Validation**:
- [ ] Kustomize build succeeds
- [ ] Deploy 3 replicas, verify pods spread across ≥2 zones (GKE)
- [ ] Verify each zone has 1-2 pods (maxSkew: 1)
- [ ] Kill a zone, verify pods reschedule (runbook test)
- [ ] Test passes: `pytest tests/deployment/test_staging_deployment_requirements.py::test_topology_spread_constraints -v`

**Priority**: P1
**Effort**: 2-3 hours (implementation + multi-zone testing)
**Related**: GKE Autopilot best practices, high availability patterns

---

## Issue P1-2: Pod Anti-Affinity Rule Severity Not Specified

**Status**: ⚠️ INCOMPLETE
**Severity**: HIGH (Weak pod distribution guarantee)
**Files Affected**:
- `/home/vishnu/git/vishnu2kmohan/worktrees/mcp-server-langgraph-session-20251116-105811/deployments/base/deployment.yaml` (affinity section)

**Test Files**:
- `/home/vishnu/git/vishnu2kmohan/worktrees/mcp-server-langgraph-session-20251116-105811/tests/deployment/test_staging_deployment_requirements.py` (new test)

**Problem**:
Deployment currently uses `podAntiAffinity.preferredDuringSchedulingIgnoredDuringExecution`, which is a "soft" constraint. Scheduler will still place 2+ replicas on same node if necessary. Should use:
- `requiredDuringSchedulingIgnoredDuringExecution` for strict (P0)
- `preferredDuringSchedulingIgnoredDuringExecution` with higher weight for soft (P1)

**Current Code**:
```yaml
affinity:
  podAntiAffinity:
    preferredDuringSchedulingIgnoredDuringExecution:
    - weight: 100
      podAffinityTerm:
        labelSelector:
          matchLabels:
            app: mcp-server-langgraph
        topologyKey: kubernetes.io/hostname
```

**Fix**:
Change to **required** anti-affinity:
```yaml
affinity:
  podAntiAffinity:
    requiredDuringSchedulingIgnoredDuringExecution:  # CHANGE: preferred → required
    - labelSelector:
        matchLabels:
          app: mcp-server-langgraph
      topologyKey: kubernetes.io/hostname
    preferredDuringSchedulingIgnoredDuringExecution:  # KEEP: for additional soft distribution
    - weight: 50
      podAffinityTerm:
        labelSelector:
          matchLabels:
            app: mcp-server-langgraph
        topologyKey: topology.kubernetes.io/zone
```

**Validation**:
- [ ] Kustomize build succeeds
- [ ] Deploy 3 replicas, verify all on different nodes
- [ ] Add fake pod to fill a node, verify replicas don't violate anti-affinity
- [ ] Test passes: `pytest tests/deployment/test_staging_deployment_requirements.py::test_pod_anti_affinity -v`

**Priority**: P1
**Effort**: 1-2 hours (config change + validation)

---

## Issue P1-3: Missing Startup Probe Configuration

**Status**: ❌ NOT CONFIGURED (Critical for slow-starting services)
**Severity**: HIGH (Premature pod termination)
**Files Affected**:
- `/home/vishnu/git/vishnu2kmohan/worktrees/mcp-server-langgraph-session-20251116-105811/deployments/base/deployment.yaml` (container spec)
- `/home/vishnu/git/vishnu2kmohan/worktrees/mcp-server-langgraph-session-20251116-105811/deployments/base/keycloak-deployment.yaml` (ALREADY HAS - line 122)
- `/home/vishnu/git/vishnu2kmohan/worktrees/mcp-server-langgraph-session-20251116-105811/deployments/base/openfga-deployment.yaml` (check if missing)

**Test Files**:
- `/home/vishnu/git/vishnu2kmohan/worktrees/mcp-server-langgraph-session-20251116-105811/tests/deployment/test_staging_deployment_requirements.py`

**Problem**:
MCP Server may take 10-15 seconds to fully initialize. Without startupProbe:
- Liveness probe kicks in too early
- Pod killed before ready
- Deployment enters CrashLoopBackOff

**Fix**:
1. **Add startup probe to mcp-server container**:
   ```yaml
   containers:
   - name: mcp-server-langgraph
     # ... other config ...
     startupProbe:
       httpGet:
         path: /health/startup
         port: 8000
       initialDelaySeconds: 0
       periodSeconds: 2
       timeoutSeconds: 3
       failureThreshold: 30  # 30 * 2s = 60s total wait
     livenessProbe:
       httpGet:
         path: /health/live
         port: 8000
       initialDelaySeconds: 10
       periodSeconds: 10
       timeoutSeconds: 5
       failureThreshold: 3
     readinessProbe:
       httpGet:
         path: /health/ready
         port: 8000
       initialDelaySeconds: 5
       periodSeconds: 5
       timeoutSeconds: 3
       failureThreshold: 3
   ```

2. **Verify health endpoints exist** in application code:
   ```bash
   grep -r "health/startup" src/
   grep -r "health/live" src/
   grep -r "health/ready" src/
   ```

3. **Add validation test**:
   ```python
   def test_mcp_server_has_startup_probe():
       """Verify mcp-server has startup probe for slow initialization"""
       manifest = load_manifest('deployment.yaml')
       container = manifest['spec']['template']['spec']['containers'][0]

       assert 'startupProbe' in container, "Missing startupProbe"
       probe = container['startupProbe']
       assert probe['failureThreshold'] >= 30, "Insufficient startup timeout"
   ```

**Validation**:
- [ ] Health endpoints implemented and tested
- [ ] Deploy pod, monitor startup sequence
- [ ] Liveness probe doesn't trigger during initial startup
- [ ] Pod reaches Ready state within timeout
- [ ] Test passes

**Priority**: P1
**Effort**: 2-3 hours (if endpoints need implementation; 1h if already exist)

---

## Issue P1-4: Resource Request/Limit Misalignment Across Deployments

**Status**: ⚠️ INCONSISTENT
**Severity**: HIGH (Scheduler under-utilization, eviction risks)
**Files Affected**:
- `/home/vishnu/git/vishnu2kmohan/worktrees/mcp-server-langgraph-session-20251116-105811/deployments/base/deployment.yaml` (MCP Server)
- `/home/vishnu/git/vishnu2kmohan/worktrees/mcp-server-langgraph-session-20251116-105811/deployments/base/keycloak-deployment.yaml` (Keycloak, line 146)
- `/home/vishnu/git/vishnu2kmohan/worktrees/mcp-server-langgraph-session-20251116-105811/deployments/base/openfga-deployment.yaml` (OpenFGA)
- `/home/vishnu/git/vishnu2kmohan/worktrees/mcp-server-langgraph-session-20251116-105811/deployments/overlays/preview-gke/otel-collector-patch.yaml` (OTEL, already fixed per P0-2)

**Test Files**:
- `/home/vishnu/git/vishnu2kmohan/worktrees/mcp-server-langgraph-session-20251116-105811/tests/regression/test_pod_deployment_regression.py:test_cpu_limit_request_ratio`

**Problem**:
Resource requests/limits vary significantly:

**Current State**:
- MCP Server: 2 CPU request, 4 CPU limit (ratio 2.0) ✅
- Keycloak: 500m CPU request, ? limit (check)
- OTEL: 250m CPU request, 1000m limit (ratio 4.0) ✅ (fixed per P0-2)
- OpenFGA: ? request, ? limit (needs audit)

Inconsistent ratios lead to:
- Uneven node utilization
- Unexpected pod evictions during node pressure
- Scheduler unable to bin-pack efficiently

**Fix**:
1. **Audit all deployments** for resource definitions
2. **Standardize ratios** across all services:
   ```
   - CPU ratio: 2.0-4.0 (prefer 2.0-3.0)
   - Memory ratio: 1.5-2.0
   ```

3. **Example standardization** (adjust per actual needs):
   ```yaml
   # Production-grade service (MCP Server, Keycloak)
   resources:
     requests:
       cpu: 500m
       memory: 512Mi
       ephemeral-storage: 500Mi
     limits:
       cpu: 1000m      # ratio: 2.0
       memory: 1Gi     # ratio: 2.0
       ephemeral-storage: 1Gi

   # Infrastructure service (OTEL, OpenFGA)
   resources:
     requests:
       cpu: 250m
       memory: 256Mi
       ephemeral-storage: 250Mi
     limits:
       cpu: 1000m      # ratio: 4.0
       memory: 512Mi   # ratio: 2.0
       ephemeral-storage: 500Mi
   ```

4. **Add validation script**:
   ```python
   def validate_resource_ratios(manifest):
       containers = manifest['spec']['template']['spec']['containers']
       for container in containers:
           limits = container.get('resources', {}).get('limits', {})
           requests = container.get('resources', {}).get('requests', {})

           cpu_ratio = int(limits.get('cpu', '0')) / int(requests.get('cpu', '1'))
           assert cpu_ratio <= 4.0, f"CPU ratio {cpu_ratio} exceeds GKE limit"
   ```

**Validation**:
- [ ] Audit all manifests in `deployments/base/` and overlays
- [ ] Document ratios in spreadsheet
- [ ] Apply standardized values
- [ ] Validation script passes: `python scripts/validate_gke_autopilot_compliance.py`
- [ ] Load test: Deploy all services, monitor node pressure

**Priority**: P1
**Effort**: 3-4 hours (audit + standardization + testing)

---

## Issue P1-5: Network Policy Egress Rules Too Permissive

**Status**: ⚠️ NEEDS HARDENING
**Severity**: HIGH (Security: allows unnecessary external traffic)
**Files Affected**:
- `/home/vishnu/git/vishnu2kmohan/worktrees/mcp-server-langgraph-session-20251116-105811/deployments/base/networkpolicy.yaml` (MCP Server egress)
- `/home/vishnu/git/vishnu2kmohan/worktrees/mcp-server-langgraph-session-20251116-105811/deployments/overlays/preview-gke/network-policy.yaml` (staging overlay)

**Test Files**:
- `/home/vishnu/git/vishnu2kmohan/worktrees/mcp-server-langgraph-session-20251116-105811/tests/deployment/test_network_policies.py`

**Problem**:
Network policies often allow:
```yaml
egress:
- to:
  - namespaceSelector: {}    # ❌ ENTIRE CLUSTER
    ports:
    - protocol: TCP
      port: 53               # DNS OK
- to:
  - namespaceSelector: {}    # ❌ ALL external traffic
    ports:
    - protocol: TCP
      port: 443
```

This violates zero-trust security (least privilege principle).

**Fix**:
1. **Enumerate required egress** by analyzing application:
   - DNS: 53/UDP to kube-system (CoreDNS)
   - LLM API: HTTPS 443 to external providers (Anthropic, OpenAI)
   - In-cluster: OpenFGA, Keycloak, PostgreSQL, Redis on specific ports
   - Observability: OTEL collector

2. **Rewrite with specific rules**:
   ```yaml
   egress:
   # DNS
   - to:
     - namespaceSelector:
         matchLabels:
           name: kube-system
     ports:
     - protocol: UDP
       port: 53

   # In-cluster services
   - to:
     - podSelector:
         matchLabels:
           app: openfga
     ports:
     - protocol: TCP
       port: 8080

   - to:
     - podSelector:
         matchLabels:
           app: keycloak
     ports:
     - protocol: TCP
       port: 8080

   # PostgreSQL (external service reference)
   - to:
     - namespaceSelector: {}  # Only if needed
     ports:
     - protocol: TCP
       port: 5432

   # LLM providers (Anthropic)
   - to:
     - namespaceSelector: {}
       ipBlock:
         cidr: 0.0.0.0/0
         except:
         - 169.254.169.254/32  # AWS metadata
         - 127.0.0.1/8
     ports:
     - protocol: TCP
       port: 443
   ```

3. **Document external dependencies** in comment:
   ```yaml
   # Required egress:
   # - Anthropic API: api.anthropic.com:443
   # - OpenAI API: api.openai.com:443 (if fallback enabled)
   # - Docker Hub: docker.io:443 (image pulls)
   ```

**Validation**:
- [ ] Application still functions with restricted rules
- [ ] Test external API calls work (LLM providers)
- [ ] Test blocked connections fail (validate rules work)
- [ ] Security scan passes
- [ ] Test passes: `pytest tests/deployment/test_network_policies.py::TestNetworkPolicySelectorStrict -v`

**Priority**: P1
**Effort**: 3-4 hours (enumeration + hardening + extensive testing)

---

# P2: MEDIUM PRIORITY ISSUES

## Issue P2-1: Helm Chart Values Schema Drift (ArgoCD Application)

**Status**: ⚠️ NEEDS VALIDATION
**Severity**: MEDIUM (Values not recognized by chart)
**Files Affected**:
- `/home/vishnu/git/vishnu2kmohan/worktrees/mcp-server-langgraph-session-20251116-105811/deployments/argocd/applications/mcp-server-app.yaml` (line 47)
- `/home/vishnu/git/vishnu2kmohan/worktrees/mcp-server-langgraph-session-20251116-105811/deployments/helm/mcp-server-langgraph/values.yaml` (reference)

**Test Files**:
- `/home/vishnu/git/vishnu2kmohan/worktrees/mcp-server-langgraph-session-20251116-105811/tests/deployment/test_helm_configuration.py`

**Problem**:
ArgoCD Application manifest uses values like `postgresql.externalHost` but Helm chart expects `external.host` (or similar). This causes value mismatches and template rendering failures.

**Codex Finding**:
> "Legacy keys vs. nested external.host schema mismatch"

**Fix**:
1. **Verify chart schema** in `deployments/helm/mcp-server-langgraph/values.yaml`:
   ```bash
   grep -A5 "postgresql\|external" deployments/helm/mcp-server-langgraph/values.yaml
   ```

2. **Check ArgoCD application values**:
   ```bash
   grep -A10 "postgresql\|external" deployments/argocd/applications/mcp-server-app.yaml
   ```

3. **Align values** to match chart schema

4. **Add validation test**:
   ```python
   def test_argocd_app_values_match_helm_schema():
       """Verify ArgoCD values match Helm chart schema"""
       argocd_app = load_yaml('deployments/argocd/applications/mcp-server-app.yaml')
       helm_chart = load_yaml('deployments/helm/mcp-server-langgraph/values.yaml')

       argocd_values = argocd_app['spec']['source']['helm']['values']

       # Validate postgresql values exist in chart schema
       if 'postgresql' in argocd_values:
           assert 'postgresql' in helm_chart, "postgresql not in helm values schema"
           # Check sub-keys
           for key in argocd_values['postgresql'].keys():
               assert key in helm_chart['postgresql'], f"{key} not in postgresql schema"
   ```

**Validation**:
- [ ] Test passes: `pytest tests/deployment/test_helm_configuration.py -v`
- [ ] Dry-run: `helm template test-release deployments/helm/mcp-server-langgraph --values deployments/argocd/applications/mcp-server-app.yaml`
- [ ] Deploy via ArgoCD, verify Application status = Synced

**Priority**: P2
**Effort**: 2-3 hours (investigation + alignment + testing)

---

## Issue P2-2: OTEL Collector Configuration Syntax Edge Cases

**Status**: ✅ FIXED, Needs Hardening
**Severity**: MEDIUM (Config validation, not runtime)
**Files Affected**:
- `/home/vishnu/git/vishnu2kmohan/worktrees/mcp-server-langgraph-session-20251116-105811/deployments/overlays/preview-gke/otel-collector-configmap-patch.yaml`
- `/home/vishnu/git/vishnu2kmohan/worktrees/mcp-server-langgraph-session-20251116-105811/deployments/base/otel-collector-configmap.yaml`

**Test Files**:
- `/home/vishnu/git/vishnu2kmohan/worktrees/mcp-server-langgraph-session-20251116-105811/tests/regression/test_pod_deployment_regression.py:test_otel_collector_config_syntax`

**Problem**:
OTEL configuration susceptible to typos/deprecated keys:
- Invalid env var syntax: `${SERVICE_VERSION:-unknown}` (bash-style) should be replaced with values
- Deprecated keys: `use_insecure`, `retry_on_failure` (version-specific)
- Invalid telemetry config addresses

**Current Status**: ✅ ALREADY FIXED per STAGING_POD_CRASH_REMEDIATION.md

**Hardening Needed**:
1. **Add config validation script**:
   ```python
   def validate_otel_config(config_yaml):
       """Validate OTEL collector config syntax"""
       # Check for bash-style env vars
       assert '${' not in config_yaml, "Bash-style env vars not allowed"

       # Parse as YAML
       config = yaml.safe_load(config_yaml)

       # Validate exporters
       for exporter_name, exporter_cfg in config.get('exporters', {}).items():
           # Check for deprecated keys based on exporter type
           if 'googlecloud' in exporter_name:
               deprecated = ['retry_on_failure', 'use_insecure']
               for key in deprecated:
                   assert key not in exporter_cfg, f"Deprecated key {key} in {exporter_name}"

       return True
   ```

2. **Add pre-commit hook**:
   ```bash
   # .pre-commit-config.yaml
   - id: validate-otel-config
     name: Validate OTEL Collector Config
     entry: python scripts/validate_otel_config.py
     language: python
     files: otel-collector.*\.ya?ml
   ```

3. **Add test**:
   ```python
   def test_otel_collector_config_no_bash_syntax():
       """Verify OTEL config uses valid syntax"""
       configmap = load_patch('otel-collector-configmap-patch.yaml')
       config = configmap['data']['config.yaml']

       assert '${' not in config, "Bash-style env vars detected"
   ```

**Validation**:
- [ ] Validation script passes on current configs
- [ ] Pre-commit hook added and tested
- [ ] Test passes: `pytest tests/regression/test_pod_deployment_regression.py::test_otel_collector_config_syntax -v`

**Priority**: P2
**Effort**: 2 hours (script + hook + testing)

---

## Issue P2-3: Deployment Documentation Gaps for Production Readiness

**Status**: ⚠️ INCOMPLETE
**Severity**: MEDIUM (Runbook missing, operational confusion)
**Files Affected**:
- `/home/vishnu/git/vishnu2kmohan/worktrees/mcp-server-langgraph-session-20251116-105811/docs-internal/DEPLOYMENT.md` (general)
- `/home/vishnu/git/vishnu2kmohan/worktrees/mcp-server-langgraph-session-20251116-105811/docs-internal/operations/DEPLOYMENT_CHECKLIST.md` (existing)
- `/home/vishnu/git/vishnu2kmohan/worktrees/mcp-server-langgraph-session-20251116-105811/docs-internal/operations/DEPLOYMENT_REMEDIATION_SUMMARY.md` (references)

**Problem**:
Missing documentation for:
1. Topology spread constraints rationale
2. Pod anti-affinity decision matrix
3. Health probe tuning guidelines
4. Resource request sizing methodology
5. Network policy best practices
6. Troubleshooting runbook for pod scheduling failures

**Fix**:
1. **Create `docs-internal/DEPLOYMENT_CONFIGURATION_GUIDE.md`** with sections:
   - Topology Spread Constraints (rationale, configuration, examples)
   - Pod Anti-Affinity (required vs preferred, topology keys)
   - Health Probes (startup, liveness, readiness, tuning)
   - Resource Requests/Limits (sizing, ratios, GKE Autopilot constraints)
   - Network Policies (architecture, rules, exceptions)

2. **Update `DEPLOYMENT_CHECKLIST.md`** with Session 2 items:
   - [ ] Keycloak readOnlyRootFilesystem re-enabled with full mounts
   - [ ] Topology spread constraints configured per zone
   - [ ] Pod anti-affinity rules in place (required severity)
   - [ ] Startup probes configured for slow-starting services
   - [ ] Resource ratios validated against GKE Autopilot limits
   - [ ] Network policies hardened to least privilege

3. **Create `DEPLOYMENT_TROUBLESHOOTING.md`**:
   - Pod stuck in Pending (scheduling conflicts)
   - Pod stuck in CrashLoopBackOff (topology, resources, probes)
   - Node pressure evictions (resource ratio issues)

**Validation**:
- [ ] Documentation reviewed by ops/SRE team
- [ ] Checklist matches current configuration
- [ ] Troubleshooting guide used in incident (validation by ops)

**Priority**: P2
**Effort**: 3-4 hours (documentation writing + review)

---

## Summary Table: All Issues

| ID | Title | Status | Severity | File | Test | Effort | Priority |
|-------|-------|--------|----------|------|------|--------|----------|
| **P0-1** | Keycloak readOnlyRootFilesystem | ⚠️ Disabled | CRITICAL | `keycloak-deployment.yaml` | `test_pod_deployment_regression.py` | 2-3h | P0 |
| **P0-2** | GKE CPU Ratio Violations | ✅ Partial | CRITICAL | `otel-collector-patch.yaml` | `test_pod_deployment_regression.py` | 1-2h | P0 |
| **P0-3** | Network Policy Egress (Keycloak) | ✅ Fixed | CRITICAL | `network-policy.yaml` | `test_network_policies.py` | 1h | P0 |
| **P0-4** | Cloud SQL Proxy Probes | ⚠️ Needs Check | CRITICAL | `cloud-sql-proxy-patch.yaml` | `test_cloud_sql_proxy_config.py` | 2-3h | P0 |
| **P1-1** | Topology Spread Constraints | ❌ Missing | HIGH | `deployment.yaml` | NEW | 2-3h | P1 |
| **P1-2** | Pod Anti-Affinity Severity | ⚠️ Weak | HIGH | `deployment.yaml` | NEW | 1-2h | P1 |
| **P1-3** | Startup Probe Config | ❌ Missing | HIGH | `deployment.yaml` | `test_staging_deployment_requirements.py` | 2-3h | P1 |
| **P1-4** | Resource Misalignment | ⚠️ Inconsistent | HIGH | Multiple | `test_pod_deployment_regression.py` | 3-4h | P1 |
| **P1-5** | Network Policy Too Permissive | ⚠️ Review | HIGH | `networkpolicy.yaml` | `test_network_policies.py` | 3-4h | P1 |
| **P2-1** | Helm Values Schema Drift | ⚠️ Review | MEDIUM | `mcp-server-app.yaml` | NEW | 2-3h | P2 |
| **P2-2** | OTEL Config Syntax Edge Cases | ✅ Fixed | MEDIUM | `otel-collector-configmap-patch.yaml` | `test_pod_deployment_regression.py` | 2h | P2 |
| **P2-3** | Deployment Documentation | ❌ Missing | MEDIUM | `DEPLOYMENT.md` | N/A | 3-4h | P2 |

**Total Estimated Effort**: 27-35 hours

---

## Implementation Sequence

### Phase 1: P0 (Critical) - 6-8 hours
1. Validate P0-3 (Network Policy) - verification only, 1h
2. Fix P0-2 (GKE CPU Ratios) - 1-2h
3. Fix/Validate P0-4 (Cloud SQL Probes) - 2-3h
4. Fix P0-1 (Keycloak readOnly) - 2-3h

### Phase 2: P1 (High) - 12-16 hours
5. Implement P1-3 (Startup Probes) - 2-3h
6. Implement P1-1 (Topology Constraints) - 2-3h
7. Fix P1-2 (Anti-Affinity) - 1-2h
8. Audit & Fix P1-4 (Resource Ratios) - 3-4h
9. Harden P1-5 (Network Policy) - 3-4h

### Phase 3: P2 (Medium) - 7-9 hours
10. Validate P2-1 (Helm Schema) - 2-3h
11. Harden P2-2 (OTEL Config) - 2h
12. Write P2-3 (Documentation) - 3-4h

---

## Success Criteria

### P0 Completion
- [ ] All pods start successfully with 0 crashes
- [ ] Health checks pass immediately upon startup
- [ ] GKE Autopilot policy validation shows 0 violations
- [ ] Network policies allow required traffic, block unauthorized

### P1 Completion
- [ ] Pods evenly distributed across zones (topology spread working)
- [ ] Pod anti-affinity prevents co-location on same node
- [ ] Slow-starting services don't prematurely terminate
- [ ] Resource usage aligns with requests (no evictions)
- [ ] Network policies restrict to least-privilege set

### P2 Completion
- [ ] Helm templates render with ArgoCD values
- [ ] OTEL configuration validates without warnings
- [ ] Deployment runbook complete and tested

---

## Related Documentation

- `docs-internal/operations/POD_FAILURE_PREVENTION_IMPLEMENTATION_SUMMARY.md`
- `docs-internal/operations/STAGING_POD_CRASH_REMEDIATION.md`
- `docs-internal/operations/STAGING_DEPLOYMENT_FIX_REPORT.md`
- `docs-internal/CODEX_FINDINGS_2025-11-16_COMPREHENSIVE_VALIDATION.md`
- `adr/adr-0054-pod-failure-prevention-framework.md`

---

**Session 2 Target**: Complete all 12 issues across P0/P1/P2 tiers
**Estimated Duration**: 4-5 focused sessions (24-32 hours)
**Expected Outcome**: Production-ready Helm/Kubernetes configuration with comprehensive validation framework
