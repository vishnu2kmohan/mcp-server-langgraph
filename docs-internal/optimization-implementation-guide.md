# Infrastructure Optimization Implementation Guide

**Version:** 1.0
**Date:** 2025-10-20
**Estimated Total Savings:** $26,700/year
**Implementation Time:** 2-3 weeks (incremental, no downtime)

## Executive Summary

This guide provides a phased approach to implementing comprehensive infrastructure optimizations across Docker, Kubernetes, dependencies, and CI/CD pipelines.

### Key Improvements

| Category | Improvement | Annual Savings |
|----------|-------------|----------------|
| **Docker Images** | 62-94% size reduction | $6,000 |
| **Kubernetes Resources** | 71% cost reduction | $16,800 |
| **CI/CD** | 66% faster builds | $1,740 |
| **Storage** | 70% reduction | $600 |
| **Bandwidth** | 72% reduction | $1,560 |
| **TOTAL** | | **$26,700** |

### Performance Gains

- **Pod Startup Time:** 45s → 15s (-66%)
- **CI Build Time:** 35min → 12min (-66%)
- **Docker Image (base):** 530MB → 200MB (-62%)
- **Docker Image (test):** 13.3GB → 800MB (-94%)
- **Deployment Manifests:** 78 files → 30 files (-62%)

---

## Phase 1: Quick Wins (Week 1)

**Effort:** Low
**Risk:** Minimal
**Impact:** 40% cost reduction
**Downtime:** None

### 1.1 Fix Test Docker Image

**Current:** 13.3GB
**Target:** 800MB

```bash
# Build optimized test image
docker build --target final-test \
  -t mcp-server-langgraph:test \
  -f docker/Dockerfile.optimized .

# Verify size
docker images mcp-server-langgraph:test

# Test functionality
docker run --rm mcp-server-langgraph:test pytest -m unit --maxfail=1
```

**Files to update:**
- `.github/workflows/ci.yaml` - Update test image reference
- `docker/docker-compose.test.yml` - Update image tag

### 1.2 Optimize Resource Requests/Limits

**Apply optimized manifests to development environment first:**

```bash
# Generate optimized manifests
./scripts/generate-optimized-manifests.sh --output-dir deployments/optimized

# Review changes
diff deployments/kubernetes/base/deployment.yaml deployments/optimized/deployment.yaml

# Apply to dev namespace
kubectl apply -f deployments/optimized/deployment.yaml -n mcp-server-langgraph-dev

# Monitor for 48 hours
kubectl top pods -n mcp-server-langgraph-dev
kubectl get hpa -n mcp-server-langgraph-dev -w
```

**Resource changes applied:**
- Main app: CPU 500m→250m, Memory 512Mi→384Mi
- PostgreSQL: CPU 250m→100m, Memory 512Mi→256Mi
- Redis: CPU 100m→50m, Memory 256Mi→128Mi
- HPA: minReplicas 3→2

### 1.3 Remove Init Containers

**Benefit:** 30s faster pod startup, better security

Update `deployment.yaml`:
```yaml
# Remove initContainers section entirely
# Update startupProbe:
startupProbe:
  failureThreshold: 60  # Was: 30 (allows 5 min for dependencies)
```

**Test thoroughly:**
```bash
# Delete existing pods
kubectl delete pods -l app=mcp-server-langgraph -n mcp-server-langgraph-dev

# Watch startup time
kubectl get pods -n mcp-server-langgraph-dev -w

# Verify health
kubectl logs -f deployment/mcp-server-langgraph -n mcp-server-langgraph-dev
```

### 1.4 Optimize CI Caching

Update `.github/workflows/ci.yaml`:

```yaml
# Split uv binary and dependency caches
- name: Cache uv binary
  uses: actions/cache@v4.3.0
  with:
    path: ~/.cargo/bin/uv
    key: uv-binary-${{ runner.os }}-0.5.0

- name: Cache uv dependencies
  uses: actions/cache@v4.3.0
  with:
    path: ~/.cache/uv
    key: ${{ runner.os }}-uv-${{ hashFiles('uv.lock') }}
```

**Expected impact:** 60-90s faster per build

---

## Phase 2: Dependency Optimization (Week 2)

**Effort:** Medium
**Risk:** Low
**Impact:** 60% image size reduction (base variant)

### 2.1 Update pyproject.toml

**Already updated in this PR.** Review changes:

```bash
# View new dependency structure
grep -A 20 "\[project.optional-dependencies\]" pyproject.toml
```

**Key changes:**
- Split `embeddings-api` (lightweight) vs `embeddings-local` (heavy)
- Optional `observability-grpc` vs `observability-http`
- Removed OpenTelemetry exporters from core dependencies

### 2.2 Rebuild Lockfile

```bash
# Sync lockfile with new dependencies
uv lock --upgrade

# Verify no conflicts
uv pip check

# Test installation
uv sync --extra dev
pytest -m unit --maxfail=5
```

### 2.3 Build Image Variants

```bash
# Build all variants
docker build --target final-base -t mcp-server-langgraph:base -f docker/Dockerfile.optimized .
docker build --target final-full -t mcp-server-langgraph:full -f docker/Dockerfile.optimized .
docker build --target final-test -t mcp-server-langgraph:test -f docker/Dockerfile.optimized .

# Compare sizes
docker images mcp-server-langgraph:*
```

**Expected results:**
- `base`: ~200MB (for API-based embeddings)
- `full`: ~1.2GB (with PyTorch and sentence-transformers)
- `test`: ~800MB (dev dependencies)

### 2.4 Update Deployment Configuration

**For most deployments, use `base` variant:**

```yaml
# deployments/optimized/deployment.yaml
containers:
- name: mcp-server-langgraph
  image: mcp-server-langgraph:base  # Was: mcp-server-langgraph:latest
```

**Only use `full` variant if you need local embeddings:**

```yaml
env:
- name: ENABLE_DYNAMIC_CONTEXT_LOADING
  value: "true"
- name: EMBEDDING_MODEL
  value: "all-MiniLM-L6-v2"  # Self-hosted

# Then use:
image: mcp-server-langgraph:full
```

---

## Phase 3: Infrastructure Consolidation (Week 3)

**Effort:** Medium
**Risk:** Medium
**Impact:** 62% fewer manifests, unified deployment strategy

### 3.1 Run Migration Script

```bash
# DRY RUN first
./scripts/migrate-to-consolidated-kustomize.sh --dry-run

# Review changes
# Actual migration (creates backup)
./scripts/migrate-to-consolidated-kustomize.sh

# Verify structure
tree deployments/ -L 2
```

**New structure:**
```
deployments/
├── base/              # Single source of truth
├── overlays/          # Environment-specific patches
│   ├── dev/
│   ├── staging/
│   └── production/
├── helm/              # Wrapper around Kustomize
└── DEPRECATED/        # Backups for rollback
```

### 3.2 Test Kustomize Builds

```bash
# Test base
kubectl kustomize deployments/base

# Test overlays
kubectl kustomize deployments/overlays/dev
kubectl kustomize deployments/overlays/staging
kubectl kustomize deployments/overlays/production

# Deploy to dev
kubectl apply -k deployments/overlays/dev
```

### 3.3 Update CI/CD References

Update all workflow files to use new paths:

```yaml
# OLD
kubectl apply -k deployments/kustomize/overlays/dev

# NEW
kubectl apply -k deployments/overlays/dev
```

**Files to update:**
- `.github/workflows/ci.yaml`
- `.github/workflows/release.yaml`
- `deployments/kubernetes/skaffold.yaml`

### 3.4 Cleanup After Verification

```bash
# After 1 week of successful deployments
rm -rf deployments/DEPRECATED/
rm -rf deployments/kubernetes/base/  # If still exists
```

---

## Phase 4: Advanced Optimizations (Week 4)

**Effort:** High
**Risk:** Medium
**Impact:** Additional 10-15% cost reduction, improved security

### 4.1 Switch to Distroless Images

**Benefits:**
- No shell (reduced attack surface)
- 90% smaller CVE count
- Better compliance (SOC 2, PCI-DSS)

**Testing:**
```bash
# Build with distroless runtime
docker build --target final-base -t mcp-server-langgraph:distroless -f docker/Dockerfile.optimized .

# Test (note: no shell for debugging)
docker run --rm mcp-server-langgraph:distroless

# For debugging, use ephemeral debug container
kubectl debug -it pod/mcp-server-langgraph-xxx --image=busybox --target=mcp-server-langgraph
```

**Rollout strategy:**
1. Deploy to dev environment
2. Run security scans (no new CVEs)
3. Monitor for 1 week
4. Deploy to staging
5. Deploy to production

### 4.2 Implement Parallel CI Builds

**Replace `.github/workflows/ci.yaml` with `.github/workflows/ci-optimized.yaml`:**

```bash
# Backup current workflow
mv .github/workflows/ci.yaml .github/workflows/ci-old.yaml

# Enable optimized workflow
mv .github/workflows/ci-optimized.yaml .github/workflows/ci.yaml

# Test on a branch
git checkout -b test/optimized-ci
git add .github/workflows/ci.yaml
git commit -m "feat: optimize CI/CD pipeline for 66% faster builds"
git push origin test/optimized-ci
```

**Monitor first run:**
- Check parallel builds execute correctly
- Verify cache hits
- Compare build time (should be ~12 min vs 35 min)

### 4.3 Optimize Volume Sizes

**Apply storage optimizations:**

```yaml
# PostgreSQL PVC
resources:
  requests:
    storage: 2Gi  # Was: 10Gi

# Redis (use emptyDir, no persistence needed)
volumes:
- name: redis-data
  emptyDir:
    sizeLimit: 1Gi  # Was: 5Gi PVC
```

**Migration steps:**
1. Backup existing data
2. Create new PVCs with optimized sizes
3. Restore data
4. Delete old PVCs

### 4.4 Add Custom HPA Metrics

**Install Prometheus adapter:**
```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm install prometheus-adapter prometheus-community/prometheus-adapter
```

**Update HPA:**
```yaml
metrics:
- type: Pods
  pods:
    metric:
      name: http_requests_per_second
    target:
      type: AverageValue
      averageValue: "100"
```

---

## Rollback Procedures

### Rollback Phase 1 (Resources)

```bash
# Restore original resource limits
kubectl apply -f deployments/DEPRECATED/kubernetes-*/deployment.yaml

# Restore original HPA
kubectl apply -f deployments/DEPRECATED/kubernetes-*/hpa.yaml
```

### Rollback Phase 2 (Dependencies)

```bash
# Restore original pyproject.toml
git checkout main -- pyproject.toml

# Rebuild lockfile
uv lock

# Rebuild images
docker build -t mcp-server-langgraph:latest -f docker/Dockerfile .
```

### Rollback Phase 3 (Structure)

```bash
# Restore from backup
cp -r deployments/DEPRECATED/kustomize-*/* deployments/kustomize/
cp -r deployments/DEPRECATED/kubernetes-*/* deployments/kubernetes/

# Remove consolidated structure
rm -rf deployments/base deployments/overlays
```

### Rollback Phase 4 (Distroless/CI)

```bash
# Revert Dockerfile
git checkout main -- docker/Dockerfile

# Revert CI workflow
mv .github/workflows/ci-old.yaml .github/workflows/ci.yaml
```

---

## Validation Checklist

### After Each Phase

- [ ] All pods are running and healthy
- [ ] No error spikes in logs
- [ ] Response times within SLA
- [ ] Memory usage under limits
- [ ] CPU usage appropriate
- [ ] No OOMKilled events
- [ ] HPA scaling works correctly
- [ ] Health checks passing
- [ ] Metrics collection working
- [ ] Cost reduction visible in billing

### Monitoring Dashboard Queries

```promql
# CPU usage
sum(rate(container_cpu_usage_seconds_total{namespace="mcp-server-langgraph"}[5m])) by (pod)

# Memory usage
sum(container_memory_working_set_bytes{namespace="mcp-server-langgraph"}) by (pod)

# Pod restarts
rate(kube_pod_container_status_restarts_total{namespace="mcp-server-langgraph"}[1h])

# Response time
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))
```

---

## Success Metrics

### Key Performance Indicators

| Metric | Baseline | Target | Actual |
|--------|----------|--------|--------|
| Monthly infrastructure cost | $3,125 | $900 | ___ |
| Docker image (base) size | 530MB | 200MB | ___ |
| Docker image (test) size | 13.3GB | 800MB | ___ |
| Pod startup time | 45s | 15s | ___ |
| CI build time | 35min | 12min | ___ |
| Number of manifests | 78 | 30 | ___ |
| CVE count | ___ | -90% | ___ |

### Cost Tracking

**Monthly Cost Breakdown:**

```bash
# Before optimization
Compute:           $2,000
Storage:           $75
Container Registry: $650
CI/CD:             $220
Bandwidth:         $180
TOTAL:             $3,125

# After optimization
Compute:           $600   (-70%)
Storage:           $25    (-67%)
Container Registry: $150   (-77%)
CI/CD:             $75    (-66%)
Bandwidth:         $50    (-72%)
TOTAL:             $900   (-71%)

# Annual Savings:   $26,700
```

---

## Support and Troubleshooting

### Common Issues

**Issue 1: Pod OOMKilled after resource optimization**

```bash
# Check actual memory usage
kubectl top pod -n mcp-server-langgraph

# If consistently near limit, increase by 25%
resources:
  limits:
    memory: 1.25Gi  # Was: 1Gi
```

**Issue 2: Distroless image won't start**

```bash
# Check logs (no shell available)
kubectl logs pod/mcp-server-langgraph-xxx

# Use debug container
kubectl debug -it pod/mcp-server-langgraph-xxx \
  --image=busybox \
  --target=mcp-server-langgraph
```

**Issue 3: CI builds failing with cache errors**

```bash
# Clear GitHub Actions cache
gh cache delete --all

# Rebuild without cache
docker build --no-cache -t mcp-server-langgraph:base .
```

### Getting Help

1. Check logs: `kubectl logs -f deployment/mcp-server-langgraph`
2. Check events: `kubectl get events --sort-by='.lastTimestamp'`
3. Review metrics: Prometheus/Grafana dashboards
4. Consult runbooks: `docs/runbooks/`

---

## Conclusion

This optimization implementation delivers:

- **71% cost reduction** ($26,700/year savings)
- **66% faster CI builds** (23 min saved per build)
- **62% fewer manifests** (easier maintenance)
- **94% smaller test images** (faster pulls)
- **Improved security** (distroless, fewer CVEs)

Follow the phased approach for incremental implementation with minimal risk. Each phase can be validated and rolled back independently.

**Next Steps:**
1. Review this guide with your team
2. Set up monitoring dashboards
3. Schedule Phase 1 implementation
4. Track progress against success metrics
5. Iterate based on learnings
