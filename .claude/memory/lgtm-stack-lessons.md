# LGTM Stack & Keycloak GHCR Image - Lessons Learned

**Created**: 2025-12-08
**Author**: Claude Code
**Status**: Active

---

## Overview

This document captures lessons learned from migrating to the Grafana LGTM observability stack and implementing the Keycloak GHCR optimized image with `readOnlyRootFilesystem: true`.

---

## 1. Keycloak GHCR Optimized Image

### Key Implementation Details

**Image**: `ghcr.io/vishnu2kmohan/keycloak-optimized:26.4.2`

**Why Pre-Optimized Image?**
- Stock Keycloak image requires JIT compilation at runtime (writes to filesystem)
- Pre-built image runs `kc.sh build` at Docker build time
- Enables `readOnlyRootFilesystem: true` for security hardening
- Faster container startup (no runtime Quarkus augmentation)

### Critical Configuration

```yaml
# Container must use --optimized flag
args:
  - start
  - --optimized

# KC_HTTP_RELATIVE_PATH for gateway routing
env:
  - name: KC_HTTP_RELATIVE_PATH
    value: /authn
```

### Health Check Paths

| With `/authn` prefix | Without prefix |
|---------------------|----------------|
| `/authn/health/started` | `/health/started` |
| `/authn/health/live` | `/health/live` |
| `/authn/health/ready` | `/health/ready` |

**Rule**: When `KC_HTTP_RELATIVE_PATH=/authn` is set, ALL health check paths include the prefix.

### EmptyDir Volume Pattern

**CRITICAL**: Do NOT mount emptyDir at `/opt/keycloak/lib` - this overwrites Quarkus runtime JARs.

Safe mounts:
- `/tmp` - Temporary files
- `/var/tmp` - Additional temp storage
- `/opt/keycloak/data` - Keycloak work directory
- `/opt/keycloak/data/tmp` - Cache directory
- `/opt/keycloak/providers` - Custom provider JARs
- `/opt/keycloak/themes` - Custom themes

### Build Pipeline

Image built via GitHub Actions: `.github/workflows/build-keycloak-image.yaml`

Dockerfile: `docker/Dockerfile.keycloak`

---

## 2. LGTM Stack Migration

### Component Versions (2025-12-08)

| Component | Version | Replaces |
|-----------|---------|----------|
| Grafana Alloy | v1.9.0 | OTEL Collector + Promtail |
| Grafana Loki | 3.5.1 | (new - log aggregation) |
| Grafana Mimir | 2.16.1 | Prometheus |
| Grafana Tempo | 2.8.0 | Jaeger |
| Grafana | 11.5.1 | (upgraded) |

### Key Benefits

1. **Unified Vendor**: All Grafana components work seamlessly together
2. **Alloy Consolidation**: Single collector replaces OTEL Collector + Promtail
3. **Native OTLP Support**: Tempo and Mimir accept OTLP directly
4. **Better Scaling**: Mimir and Loki designed for horizontal scaling

### Migration Considerations

- **Prometheus queries** work unchanged in Mimir (PromQL compatible)
- **Jaeger UI** replaced with Tempo's native Grafana integration
- **OTEL Collector configs** may need translation to Alloy format
- **Existing dashboards** should work but verify data sources

### Docker Compose Pattern

```yaml
# LGTM stack services
alloy:
  image: grafana/alloy:v1.9.0

loki:
  image: grafana/loki:3.5.1

mimir:
  image: grafana/mimir:2.16.1

tempo:
  image: grafana/tempo:2.8.0

grafana:
  image: grafana/grafana:11.5.1
```

---

## 3. Documentation Update Patterns

### Files Updated for Keycloak GHCR Image

| File | Key Changes |
|------|-------------|
| `docs/deployment/kubernetes/gke.mdx` | GHCR image, `/authn` routing |
| `docs/deployment/kubernetes/keycloak-readonly-filesystem.mdx` | Implementation details |
| `docs/deployment/version-compatibility.mdx` | Version matrix update |
| `docs/guides/keycloak-sso.mdx` | Health check paths |
| `docs/integrations/keycloak.mdx` | Production deployment |

### Search Patterns for Future Updates

When updating Keycloak documentation, search for:
```bash
grep -r "quay.io/keycloak" docs/
grep -r "keycloak:2" docs/  # version patterns
grep -r "/health/ready" docs/  # health checks without /authn
```

---

## 4. Common Pitfalls

### Keycloak

1. **Wrong image**: Using stock `quay.io/keycloak/keycloak` with `--optimized` flag will fail
2. **Missing `/authn`**: Health checks fail if paths don't include KC_HTTP_RELATIVE_PATH
3. **lib volume mount**: Mounting emptyDir at `/opt/keycloak/lib` causes ClassNotFoundException
4. **Build args at runtime**: Cannot pass `--db=postgres` at runtime with `--optimized`

### LGTM Stack

1. **Alloy config syntax**: Different from OTEL Collector YAML format
2. **Data source IDs**: Grafana dashboard imports may need data source updates
3. **Storage backends**: Mimir/Loki need object storage for production (MinIO, S3)

---

## 5. Validation Commands

### Keycloak

```bash
# Test read-only filesystem
kubectl exec -it keycloak-xxx -c keycloak -- touch /test
# Expected: Read-only file system error

# Test health endpoint
kubectl exec -it keycloak-xxx -c keycloak -- curl http://localhost:8080/authn/health/ready
# Expected: {"status": "UP"}
```

### LGTM Stack

```bash
# Check Alloy health
curl http://localhost:12345/ready

# Check Loki ready
curl http://localhost:3100/ready

# Check Mimir ready
curl http://localhost:8080/ready

# Check Tempo ready
curl http://localhost:3200/ready
```

---

## 6. Related Documentation

- `docs/deployment/kubernetes/keycloak-readonly-filesystem.mdx` - Full implementation guide
- `docs/deployment/version-compatibility.mdx` - Version matrix
- `docker/Dockerfile.keycloak` - Optimized image build
- `.github/workflows/build-keycloak-image.yaml` - CI/CD pipeline

---

## 7. Future Considerations

1. **Keycloak version upgrades**: Rebuild GHCR image when upgrading Keycloak versions
2. **LGTM stack updates**: Watch for Grafana ecosystem releases
3. **Alloy config**: Consider migrating remaining OTEL Collector configs to Alloy format
4. **Object storage**: For production LGTM, configure MinIO or cloud object storage

---

**Last Updated**: 2025-12-08
