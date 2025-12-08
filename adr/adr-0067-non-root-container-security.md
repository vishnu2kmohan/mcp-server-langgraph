# ADR-0067: Non-Root Container Security Strategy

**Status**: Accepted
**Date**: 2025-12-07
**Author**: Claude Code
**Decision Makers**: Vishnu Mohan

## Context

During CI troubleshooting for E2E tests, we discovered that several containers in `docker-compose.test.yml` were running as root or had file permission issues that caused failures in CI but not locally. This highlighted the need for a comprehensive non-root container security strategy.

## Decision

### 1. Non-Root by Default

All containers MUST run as non-root users unless there is a documented, justified exception.

### 2. UID/GID Strategy

Use the UID specified by the upstream container image maintainer:

| Container | UID | Image Source |
|-----------|-----|--------------|
| Loki | 10001 | grafana/loki |
| Prometheus | 65534 (nobody) | prom/prometheus |
| Alertmanager | 65534 (nobody) | prom/alertmanager |
| Grafana | 472 | grafana/grafana |
| Jaeger | 10001 | jaegertracing/all-in-one |
| Keycloak | 1000 | quay.io/keycloak/keycloak |
| Qdrant | 1000 | qdrant/qdrant:*-unprivileged |
| Traefik | 1000 | traefik:v3.x (with high ports) |
| PostgreSQL | 70 | postgres:*-alpine |
| Redis | 999 | redis:*-alpine |

### 3. tmpfs Ownership

When using tmpfs mounts, explicitly set UID/GID:

```yaml
tmpfs:
  - /path:rw,noexec,nosuid,size=256m,uid=10001,gid=10001
```

### 4. Documented Exceptions

**Promtail** is the only container allowed to run as root because:
- Requires read access to Docker socket
- Needs to read container log files owned by various UIDs

## Consequences

### Positive

- Security parity: Local, CI, and production environments use consistent non-root policies
- Earlier failure detection: Permission issues caught locally instead of CI
- OpenShift ready: Containers work with OpenShift's restrictive SCC
- Reduced attack surface: Compromised containers cannot easily escalate privileges

### Negative

- Minor complexity: Must track different UIDs for different images
- Port restrictions: Services requiring port below 1024 need port mapping

## References

- [Docker Rootless Mode](https://docs.docker.com/engine/security/rootless/)
- [Kubernetes Security Context](https://kubernetes.io/docs/tasks/configure-pod-container/security-context/)
- [OpenShift Container Security](https://docs.openshift.com/container-platform/latest/authentication/managing-security-context-constraints.html)
