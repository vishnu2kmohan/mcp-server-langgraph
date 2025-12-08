# Container Security Patterns

**Purpose**: Guide for non-root container configurations
**Created**: 2025-12-07
**Related ADR**: ADR-0067

## Quick Reference: Non-Root Container Requirements

### 1. All Containers Must Run as Non-Root

Check docker-compose files for explicit `user:` directives or known non-root images:

```yaml
# Explicit user (for images that default to root)
traefik-gateway:
  image: traefik:v3.2
  user: "1000:1000"

# OR use unprivileged image variant
qdrant-test:
  image: qdrant/qdrant:v1.15.5-unprivileged
  user: "1000:1000"
```

### 2. tmpfs Ownership for Non-Root Containers

Always specify UID/GID when using tmpfs:

```yaml
# WRONG - root owns tmpfs, non-root can't write
tmpfs:
  - /data:rw,size=256m

# CORRECT - container user owns tmpfs
tmpfs:
  - /data:rw,noexec,nosuid,size=256m,uid=10001,gid=10001
```

### 3. Config File Permissions

All mounted config files must be world-readable:

```bash
# Check: Should be 644 or 755
ls -la docker/loki/loki-config.yaml
-rw-r--r-- 1 user group ... loki-config.yaml  # Good

# Fix if needed
chmod 644 docker/loki/loki-config.yaml
```

### 4. High Ports for Non-Root Services

Non-root users cannot bind to ports < 1024. Use port mapping:

```yaml
traefik-gateway:
  user: "1000:1000"
  command:
    # Internal high ports
    - "--entrypoints.web.address=:8000"
    - "--entrypoints.dashboard.address=:8081"
  ports:
    - "80:8000"    # External 80 -> internal 8000
    - "8080:8081"  # External 8080 -> internal 8081
```

## Container UID Reference

| Container | UID | Notes |
|-----------|-----|-------|
| Loki | 10001 | grafana/loki default |
| Prometheus | 65534 | nobody user |
| Alertmanager | 65534 | nobody user |
| Grafana | 472 | grafana user |
| Jaeger | 10001 | jaeger user |
| Keycloak | 1000 | keycloak user |
| Qdrant | 1000 | Use `-unprivileged` image |
| Traefik | 1000 | Requires high ports |
| PostgreSQL | 70 | postgres user |
| Redis | 999 | redis user |
| **Promtail** | root | **EXCEPTION**: Requires Docker socket access |

## Troubleshooting

### "Permission denied" on config file
```bash
# Container can't read mounted config
chmod 644 path/to/config.yaml
```

### "mkdir: permission denied" on tmpfs
```yaml
# Add UID/GID to tmpfs mount
tmpfs:
  - /path:rw,uid=CONTAINER_UID,gid=CONTAINER_GID
```

### Container can't bind to port
```yaml
# Use internal high port with mapping
command:
  - "--port=8000"  # Not 80
ports:
  - "80:8000"
```

### Finding container UID
```bash
# Check running container
docker exec <container> id

# Check image default
docker run --rm <image> id
```

## OpenShift Compatibility

OpenShift assigns arbitrary UIDs. Ensure containers work with GID 0:

```dockerfile
# Dockerfile pattern for OpenShift
RUN chown -R 1000:0 /app && \
    chmod -R g=u /app
```

## Related Files

- `docker-compose.test.yml` - Test infrastructure
- `adr/adr-0067-non-root-container-security.md` - Full ADR
- `docs-internal/lessons-learned/2025-12-07-non-root-containers-ci-failure.md` - Incident details
