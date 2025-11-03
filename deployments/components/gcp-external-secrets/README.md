# GCP External Secrets Component

Reusable Kustomize component for GCP External Secrets Operator configuration.

## Usage

In your overlay's `kustomization.yaml`:

```yaml
components:
  - ../../components/gcp-external-secrets

resources:
  - external-secrets.yaml  # Your environment-specific External Secrets
```

## What it provides

Base configuration and best practices for:
- GCP Secret Manager integration
- Workload Identity authentication
- SecretStore/ClusterSecretStore patterns
- ExternalSecret refresh intervals

## Requirements

1. **External Secrets Operator**: Must be installed in cluster
2. **Workload Identity**: ServiceAccount for External Secrets Operator
3. **GCP Permissions**: ServiceAccount needs `roles/secretmanager.secretAccessor`

## Example external-secrets.yaml

```yaml
apiVersion: external-secrets.io/v1
kind: SecretStore
metadata:
  name: gcp-secret-store
  namespace: your-namespace
spec:
  provider:
    gcpsm:
      projectID: "your-gcp-project"
      auth:
        workloadIdentity:
          clusterLocation: us-central1
          clusterName: your-cluster
          serviceAccountRef:
            name: external-secrets-operator
---
apiVersion: external-secrets.io/v1
kind: ExternalSecret
metadata:
  name: app-secrets
  namespace: your-namespace
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: gcp-secret-store
    kind: SecretStore
  target:
    name: app-secrets
    creationPolicy: Owner
  data:
  - secretKey: myKey
    remoteRef:
      key: secret-name-in-gcp
```
