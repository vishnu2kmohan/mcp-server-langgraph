# Helm Chart Dependency Validation

**Purpose**: Prevent corrupted partial Helm chart caches from causing CI failures
**Created**: 2025-12-11
**Root Cause Analysis**: `.claude/plans/purrfect-dazzling-breeze.md`

---

## Problem

CI cache corruption caused 14 checks to fail despite local validation passing.

**Root Cause**: GitHub Actions cache contained 5/7 Helm chart dependencies from a partial build (rate limiting or timeout). The CI logic only checked if "any" charts existed, not if ALL expected charts were present.

**Charts Present (5)**: grafana, jaeger, keycloak, openfga, postgresql
**Charts Missing (2)**: redis, kube-prometheus-stack

---

## Solution

### 1. CI Cache Validation (3 workflows)

All CI workflows now validate chart COUNT, not just existence:

```bash
EXPECTED_CHARTS=7  # openfga, postgresql, redis, keycloak, grafana, jaeger, kube-prometheus-stack
ACTUAL_CHARTS=$(ls charts/*.tgz 2>/dev/null | wc -l)
if [ "$ACTUAL_CHARTS" -ne "$EXPECTED_CHARTS" ]; then
  echo "Cache incomplete: $ACTUAL_CHARTS/$EXPECTED_CHARTS"
  # Clear cache and rebuild
fi
```

Updated files:
- `.github/workflows/ci.yaml` (lines 350-400)
- `.github/workflows/validate-kubernetes.yaml` (lines 56-110)
- `.github/workflows/deployment-validation.yml` (lines 44-99)

### 2. Pre-Push Validation Hook

New hook validates chart count before pushing:

```yaml
- id: validate-helm-chart-deps
  name: Validate Helm Chart Dependencies Complete
  stages: [pre-push]
```

### 3. Pytest Validation

New test verifies all Chart.yaml dependencies are downloaded:

```python
def test_all_chart_dependencies_present(self):
    # In tests/integration/deployment/test_helm_templates.py
```

---

## Expected Helm Charts (7)

| Chart | Source | Purpose |
|-------|--------|---------|
| openfga | openfga/openfga | Authorization (OpenFGA) |
| postgresql | bitnami/postgresql | Database |
| redis | bitnami/redis | Cache/Sessions |
| keycloak | codecentric/keycloakx | Authentication (SSO) |
| grafana | grafana/grafana | Dashboards |
| jaeger | jaegertracing/jaeger | Tracing |
| kube-prometheus-stack | prometheus-community | Metrics + Alerting |

---

## Cache Invalidation

If you suspect cache corruption, invalidate by:

**Option A**: Regenerate Chart.lock (recommended)
```bash
cd deployments/helm/mcp-server-langgraph
helm dependency update  # Regenerates Chart.lock
git add Chart.lock
git commit -m "chore: regenerate Chart.lock to invalidate cache"
```

**Option B**: Clear GitHub Actions cache manually
```bash
gh cache delete --all --repo vishnu2kmohan/mcp-server-langgraph
```

---

## Local Validation

Before pushing, verify Helm charts are complete:

```bash
# Check chart count
ls deployments/helm/mcp-server-langgraph/charts/*.tgz | wc -l
# Should output: 7

# Or run the hook directly
pre-commit run validate-helm-chart-deps --all-files --hook-stage pre-push

# Or run the test
uv run pytest tests/integration/deployment/test_helm_templates.py::TestHelmDependencies::test_all_chart_dependencies_present -v
```

---

## GHCR Image Strategy

CI-built images are pulled from GHCR for faster E2E tests:

| Service | GHCR Image | CI Workflow | Fallback |
|---------|------------|-------------|----------|
| keycloak-test | `ghcr.io/vishnu2kmohan/mcp-server-langgraph-keycloak:latest` | `build-keycloak-image.yaml` | `docker/Dockerfile.keycloak` |
| mcp-server-test | `ghcr.io/vishnu2kmohan/mcp-server-langgraph:test-latest` | `ci.yaml` (docker-build job) | `docker/Dockerfile.test` |
| builder-test | `ghcr.io/vishnu2kmohan/mcp-server-langgraph-builder:latest` | `build-builder-image.yaml` | `docker/Dockerfile.builder` |
| playground-test | `ghcr.io/vishnu2kmohan/mcp-server-langgraph-playground:latest` | `build-playground-image.yaml` | `docker/Dockerfile.playground` |
| alembic-migrate-test | `ghcr.io/vishnu2kmohan/mcp-server-langgraph-alembic:latest` | `build-alembic-image.yaml` | `docker/Dockerfile.alembic` |

All images are built weekly on Monday 7 AM UTC to pick up security updates.

---

## Troubleshooting

### CI shows "Cache incomplete: X/7 charts"

1. CI detected corrupted cache
2. It will automatically rebuild from scratch
3. If rebuild fails repeatedly, check GitHub API rate limiting

### Test fails: "Helm chart dependencies incomplete"

```bash
# Build dependencies locally
helm dependency build deployments/helm/mcp-server-langgraph

# Verify all charts present
ls deployments/helm/mcp-server-langgraph/charts/*.tgz
# Should show 7 .tgz files
```

### "pull access denied" for Docker image

Missing GHCR image. Either:
1. Wait for CI to build and push the image
2. Use local build: `docker-compose -f docker-compose.test.yml build <service>`

---

## References

- Root cause analysis: `.claude/plans/purrfect-dazzling-breeze.md`
- Helm chart: `deployments/helm/mcp-server-langgraph/Chart.yaml`
- Pre-push hook: `.pre-commit-config.yaml` (id: `validate-helm-chart-deps`)
- Test: `tests/integration/deployment/test_helm_templates.py::test_all_chart_dependencies_present`
