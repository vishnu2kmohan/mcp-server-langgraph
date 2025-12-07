# Lessons Learned: Non-Root Container CI Failure

**Date**: 2025-12-07
**Incident**: E2E tests failing in CI due to Loki container crash
**Root Cause**: File permission mismatch between local and CI environments
**Resolution Time**: ~2 hours
**PR**: #144

## Summary

Direct commits to `origin/main` bypassed branch protection (temporarily relaxed) and broke CI. During the fix process, we discovered that the Loki container was crashing with "permission denied" errors that didn't reproduce locally. This led to a comprehensive audit of container security configurations.

## What Happened

1. **Direct commits to main** bypassed PR review and CI validation
2. **Loki crashed in CI** with "permission denied" on `/etc/loki/local-config.yaml`
3. **Local testing passed** because the host UID matched the container expectations
4. **Initial fix was wrong**: Added `user: root` which violated security best practices

## Root Causes

### 1. File Permission Mismatch
- `loki-config.yaml` was created with mode 600 (owner-only) locally
- Loki runs as UID 10001, couldn't read the config
- Git preserves content but not permissions, so mode varied by environment

### 2. Non-Root Containers Not Enforced
- Several containers (Qdrant, Traefik) ran as root
- Inconsistent with Kubernetes deployments that enforce `runAsNonRoot: true`
- Local/CI parity gap

### 3. tmpfs Ownership Not Specified
- Default tmpfs owned by root
- Non-root containers couldn't write to ephemeral storage

## Fixes Applied

| Issue | Fix |
|-------|-----|
| Loki config permissions | Ensure mode 644, document requirement |
| Loki tmpfs ownership | Added `uid=10001,gid=10001` to tmpfs mount |
| Qdrant running as root | Changed to `-unprivileged` image with `user: 1000:1000` |
| Traefik running as root | Use high ports (8000/8081) with `user: 1000:1000` |

## Lessons Learned

### 1. Test Infrastructure Should Match Production Security
- If Kubernetes enforces `runAsNonRoot`, Docker Compose should too
- Catches permission issues before they reach CI

### 2. Initial Instinct to "Just Make It Work" Can Violate Policies
- `user: root` is tempting but creates technical debt
- Always ask: "Would this pass in production?"

### 3. File Permissions Are Not Portable
- Git tracks mode but execution context matters
- Config files should be world-readable (644) for non-root containers
- Use `.gitattributes` or documentation to enforce

### 4. tmpfs Needs Explicit Ownership for Non-Root
```yaml
# Wrong - owned by root
tmpfs:
  - /data:rw,size=256m

# Correct - owned by container user
tmpfs:
  - /data:rw,size=256m,uid=10001,gid=10001
```

### 5. Use Official Unprivileged Image Variants
- Qdrant provides `qdrant/qdrant:*-unprivileged`
- Prefer these over adding `user:` directive to root images
- Already configured for non-root operation

### 6. High Ports for Non-Root Network Services
- Non-root can't bind to ports < 1024
- Use internal high ports with external port mapping
- Document clearly in comments

## Prevention Measures

### Immediate (This PR)
- ✅ ADR-0067 documents non-root container strategy
- ✅ All containers now run as non-root (except Promtail)
- ✅ tmpfs ownership explicitly set

### Future (Recommended)
- [ ] Pre-commit hook to validate container UIDs in docker-compose
- [ ] CI test that verifies all containers run as non-root
- [ ] Add to deployment checklist

## References

- ADR-0067: Non-Root Container Security Strategy
- PR #144: Fix CI failures from direct commits
- Docker Compose file: `docker-compose.test.yml`
