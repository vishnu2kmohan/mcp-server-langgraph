# Optimized Deployment Manifests (Experimental)

**Status**: 🧪 Experimental / Archive Candidate
**Last Updated**: 2024-10-21
**Maintained**: No (archived for reference)

## ⚠️ Important Notice

This directory contains **experimental** deployment optimizations that were tested but **NOT integrated into production**.

**For active deployments, use**:
- **Production**: `deployments/helm/mcp-server-langgraph/` (Helm chart - recommended)
- **Staging**: `deployments/overlays/staging-gke/` (Kustomize)
- **Development**: `deployments/overlays/dev/` (Kustomize)

---

## What This Directory Contains

Experimental optimizations tested during performance tuning:

### Files

| File | Purpose | Status |
|------|---------|--------|
| `deployment.yaml` | Optimized Deployment (no init containers) | Experimental |
| `hpa.yaml` | Horizontal Pod Autoscaler | Experimental |
| `postgres-statefulset.yaml` | PostgreSQL StatefulSet | Experimental |
| `redis-session-deployment.yaml` | Redis Deployment | Experimental |

### Optimizations Attempted

1. **Init Container Removal**
   - Removed service dependency checks (Redis, Postgres, Keycloak)
   - Replaced with longer startupProbe failureThreshold (60 vs 30)
   - Application-level retries using tenacity library
   - Kubernetes DNS-based service discovery

   **Benefits**:
   - Faster pod startup (no init container overhead)
   - Reduced complexity
   - Better observability (app handles retries with metrics)

   **Tradeoffs**:
   - Pods may restart more during initial startup if deps not ready
   - Requires application code changes (tenacity integration)

2. **Probe Timing Adjustments**
   - Extended startup period for cold starts
   - Reduced readiness/liveness frequencies for stable pods

3. **Resource Tuning**
   - Memory: 512Mi → 768Mi (observed heap usage patterns)
   - CPU: 500m → 750m (LLM call overhead)

---

## Why Not in Production?

This directory was created during performance experiments but **NOT integrated** because:

1. **Divergence Risk**: Separate manifests can drift from main deployment definitions
2. **Maintenance Burden**: Two deployment paths to maintain
3. **Testing Complexity**: Would require parallel CI/CD pipelines
4. **Limited Value**: Optimizations can be added to Helm chart values instead

**Codex Finding**: Directory noted as drifting from live Kustomize/Helm definitions

---

## Recommended Actions

### Option 1: Archive (Recommended)

Keep for historical reference but clearly mark as archived:

```bash
# Add ARCHIVED notice
mv deployments/optimized deployments/archived-experiments/optimized-$(date +%Y%m%d)
```

### Option 2: Integrate into Helm Chart

Extract useful optimizations into Helm chart values:

```yaml
# values-optimized.yaml
resources:
  requests:
    memory: 768Mi
    cpu: 750m

probes:
  startup:
    failureThreshold: 60  # Extended for cold starts
```

### Option 3: Remove

If no longer needed for reference:

```bash
rm -rf deployments/optimized/
```

---

## If You Want to Use These Optimizations

**Don't use these files directly.** Instead:

1. **Review the changes** in this directory
2. **Extract the optimizations** you want (resource limits, probe timings, etc.)
3. **Add them to Helm chart** as values in `values-production.yaml`:

```yaml
# Example: values-production-optimized.yaml
resources:
  limits:
    memory: 2Gi
    cpu: 2000m
  requests:
    memory: 768Mi  # From optimized/
    cpu: 750m      # From optimized/

startupProbe:
  failureThreshold: 60  # From optimized/
```

4. **Test thoroughly** in staging before production

---

## Comparison with Current Deployments

| Feature | Base/Helm | Optimized | Recommendation |
|---------|-----------|-----------|----------------|
| Init containers | Yes (3) | No | Keep init (reliability > speed) |
| Startup probe | 30 failures | 60 failures | Consider 45 as middle ground |
| Memory request | 512Mi | 768Mi | Profile and decide per environment |
| CPU request | 500m | 750m | Profile and decide per environment |

---

## Historical Context

**Created**: October 2024
**Purpose**: Performance optimization experiments
**Status**: Never deployed to production
**Last Modified**: 2024-10-21

**Codex Note**: Identified as source of configuration drift (Codex Finding P2 #10)

---

## Recommendation

**Archive this directory** and integrate useful optimizations into Helm chart values.

```bash
# Proposed archival
git mv deployments/optimized deployments/archived/optimized-202410
git commit -m "chore(deployment): archive experimental optimized manifests"
```

Or update Helm values to support optimization profiles:

```bash
# deployments/helm/mcp-server-langgraph/values-profiles/
├── values-baseline.yaml        # Standard config
├── values-optimized.yaml       # Performance-tuned config
└── values-cost-optimized.yaml  # Resource-constrained config
```

---

**Conclusion**: This directory should be archived or removed to prevent confusion and drift.

For performance tuning, use Helm chart value overlays instead of maintaining separate manifest files.
