# Distroless Container Health Check Patterns

**Last Updated**: 2025-12-07
**Purpose**: Lessons learned from Grafana LGTM stack health check debugging

---

## The Problem: Minimal/Distroless Images Lack Common Tools

Many modern container images (especially from Grafana) are built on minimal or distroless bases that **do not include** common utilities like `wget`, `curl`, or even a shell.

### Affected Images in This Project

| Image | Has wget/curl? | Has bash? | Recommended Health Check |
|-------|----------------|-----------|--------------------------|
| `grafana/alloy:v1.4.2` | No | Yes | Bash TCP check |
| `grafana/mimir:3.0.1` | No | No (distroless) | Disable health check |
| `grafana/tempo:2.9.0` | Yes (wget) | Yes | wget |
| `grafana/loki:3.0.0` | Yes (wget) | Yes | wget |
| `grafana/grafana:12.2.0` | Yes (wget) | Yes | wget |
| `qdrant/qdrant:v1.15.5` | No | Yes | Bash TCP check |

---

## Solution 1: Bash TCP Health Check (When Bash Available)

Use bash's built-in `/dev/tcp` feature to check if a port is open:

```yaml
healthcheck:
  test: ["CMD-SHELL", "timeout 2 bash -c '</dev/tcp/localhost/PORT' || exit 1"]
  interval: 10s
  timeout: 5s
  retries: 5
```

**Example** (from `docker-compose.test.yml`):
```yaml
alloy-test:
  image: grafana/alloy:v1.4.2
  healthcheck:
    # Alloy exposes /-/ready endpoint for readiness checks
    # NOTE: grafana/alloy image doesn't have wget/curl, use bash TCP check
    test: ["CMD-SHELL", "timeout 2 bash -c '</dev/tcp/localhost/12345' || exit 1"]
    interval: 10s
    timeout: 5s
    retries: 5
    start_period: 10s
```

### How It Works

1. `bash -c '</dev/tcp/localhost/PORT'` attempts to open a TCP connection
2. If the port is open, bash exits with code 0 (success)
3. If the port is closed, bash exits with code 1 (failure)
4. `timeout 2` ensures the command doesn't hang

---

## Solution 2: Disable Health Check (Distroless with No Shell)

For fully distroless images with no shell at all:

```yaml
healthcheck:
  disable: true
```

**Example** (from `docker-compose.test.yml`):
```yaml
mimir-test:
  image: grafana/mimir:3.0.1
  # NOTE: Mimir uses distroless image with no wget/curl
  # See: https://github.com/grafana/mimir/issues/9034
  # Healthcheck disabled; service is still accessible on port 9009
  healthcheck:
    disable: true
```

**Important**: When disabling health checks, use `condition: service_started` instead of `service_healthy` in `depends_on`:

```yaml
depends_on:
  mimir-test:
    condition: service_started  # NOT service_healthy (no healthcheck)
```

---

## Solution 3: Use wget When Available

For images that include wget (Loki, Tempo, Grafana):

```yaml
healthcheck:
  test: ["CMD", "wget", "--spider", "-q", "http://localhost:PORT/ready"]
  interval: 10s
  timeout: 5s
  retries: 5
```

---

## Diagnostic Commands

### Check What Tools Are Available in an Image

```bash
# Check if bash is available
docker run --rm IMAGE_NAME which bash

# Check if wget is available
docker run --rm IMAGE_NAME which wget

# Check if curl is available
docker run --rm IMAGE_NAME which curl

# List all binaries in /usr/bin
docker run --rm IMAGE_NAME ls /usr/bin/
```

### Debug Container Health Check Status

```bash
# See health status and failing streak
docker inspect --format='{{json .State.Health}}' CONTAINER_NAME | jq

# View last health check output
docker inspect --format='{{range .State.Health.Log}}{{.Output}}{{end}}' CONTAINER_NAME
```

---

## Related Issues

### Loki Timestamp Rejection

When using Grafana Alloy to collect logs, Alloy batches logs before sending. This can cause Loki to reject logs with "timestamp too old" errors.

**Fix** in `docker/loki/loki-config.yaml`:
```yaml
limits_config:
  reject_old_samples: false  # Disable for test environments
```

---

## Quick Reference Table

| Scenario | Pattern |
|----------|---------|
| Image has wget | `["CMD", "wget", "--spider", "-q", "URL"]` |
| Image has curl | `["CMD", "curl", "-f", "URL"]` |
| Image has bash only | `["CMD-SHELL", "timeout 2 bash -c '</dev/tcp/HOST/PORT'"]` |
| Distroless (no shell) | `healthcheck: { disable: true }` |

---

## Files Modified for LGTM Stack Health Checks

- `docker-compose.test.yml:698-705` - Alloy bash TCP check
- `docker-compose.test.yml:643-645` - Mimir health check disabled
- `docker/loki/loki-config.yaml:66-71` - Loki timestamp rejection disabled

---

**Remember**: Always verify what tools are available in a container image before writing health checks. Don't assume `wget` or `curl` exist.
