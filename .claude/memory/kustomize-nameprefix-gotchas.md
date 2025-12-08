# Kustomize namePrefix Gotchas

**Purpose**: Critical gotchas when using Kustomize `namePrefix` that can cause deployment failures.
**Last Updated**: 2025-12-07
**Related Issue**: PR #145, #146 (staging-to-preview rename)

---

## Critical: namePrefix Does NOT Update Secret References

When using `namePrefix: preview-` in `kustomization.yaml`, Kustomize **DOES NOT** automatically update `secretKeyRef.name` references in environment variables.

### The Problem

```yaml
# Base deployment (deployments/base/deployment.yaml)
env:
  - name: DATABASE_PASSWORD
    valueFrom:
      secretKeyRef:
        name: mcp-server-langgraph-secrets  # Original name
        key: database-password

# Overlay kustomization (deployments/overlays/preview-gke/kustomization.yaml)
namePrefix: preview-
```

**What Happens:**
1. Secret gets renamed to: `preview-mcp-server-langgraph-secrets`
2. **BUT** env vars still reference: `mcp-server-langgraph-secrets` (unchanged!)
3. Pod fails with: `CreateContainerConfigError` - secret not found

### The Solution

Always create a patch to explicitly update secret references when using `namePrefix`.

**Option 1: JSON 6902 Patch** (recommended for env arrays)

```yaml
# deployment-secret-refs-patch.yaml
- op: replace
  path: /spec/template/spec/containers/0/env
  value:
    - name: DATABASE_PASSWORD
      valueFrom:
        secretKeyRef:
          name: preview-mcp-server-langgraph-secrets  # Explicit prefix
          key: database-password
```

**Option 2: Strategic Merge Patch** (for simple cases)

```yaml
# deployment-patch.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mcp-server-langgraph
spec:
  template:
    spec:
      containers:
        - name: mcp-server-langgraph
          env:
            - name: DATABASE_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: preview-mcp-server-langgraph-secrets
                  key: database-password
```

### Test Validation

This project has TDD tests that catch this issue:

```bash
# Run the secret reference validation test
uv run --frozen pytest tests/kubernetes/test_kustomize_preview_gke.py::TestKustomizePreviewGKE::test_secret_references_use_preview_prefix -v
```

The test at `tests/kubernetes/test_kustomize_preview_gke.py:98` validates that all `secretKeyRef.name` values use the `preview-` prefix.

---

## Other namePrefix Gotchas

### 1. ConfigMap References

Same issue applies to `configMapKeyRef`:

```yaml
# This will NOT be auto-updated
env:
  - name: LOG_LEVEL
    valueFrom:
      configMapKeyRef:
        name: mcp-server-langgraph-config  # Won't get prefix!
        key: log-level
```

### 2. Volume Secret/ConfigMap References

Volume references are also NOT updated:

```yaml
volumes:
  - name: config
    secret:
      secretName: mcp-server-langgraph-secrets  # Won't get prefix!
```

### 3. Service References in Environment Variables

If you reference services by name in env vars, they need manual updating too:

```yaml
env:
  - name: REDIS_HOST
    value: redis-session  # May need to be preview-redis-session
```

---

## What IS Auto-Updated by namePrefix

Kustomize **DOES** automatically update:

1. Resource `metadata.name` fields
2. `spec.selector.matchLabels` (for Deployments)
3. `spec.template.metadata.labels` (for pod templates)
4. Service `spec.selector` labels

---

## Debugging Checklist

When pods fail after adding `namePrefix`:

1. **Check secret names**: `kubectl get secrets -n <namespace>`
2. **Check pod events**: `kubectl describe pod <pod> -n <namespace>`
3. **Look for**: `CreateContainerConfigError`, `secret "xxx" not found`
4. **Render manifests**: `kubectl kustomize deployments/overlays/<overlay>/ | grep secretKeyRef -A2`
5. **Run TDD tests**: `uv run --frozen pytest tests/kubernetes/test_kustomize_preview_gke.py -v`

---

## Related Files

- `tests/kubernetes/test_kustomize_preview_gke.py` - TDD tests for preview-gke overlay
- `deployments/overlays/preview-gke/deployment-redis-url-json-patch.yaml` - Example JSON 6902 patch
- `deployments/overlays/preview-gke/kustomization.yaml` - Preview overlay configuration
