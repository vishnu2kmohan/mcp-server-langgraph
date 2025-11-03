# GCP Cloud SQL Proxy Component

Reusable Kustomize component that adds a Cloud SQL Proxy sidecar to deployments.

## Usage

In your overlay's `kustomization.yaml`:

```yaml
components:
  - ../../components/gcp-cloud-sql-proxy
```

## What it does

Adds a Cloud SQL Proxy sidecar container that:
- Connects to Cloud SQL via private IP
- Exposes PostgreSQL on localhost:5432
- Uses Workload Identity for authentication
- Includes health checks and security contexts
- Provides production-ready resource limits

## Requirements

1. **Workload Identity**: ServiceAccount must be annotated with GCP service account
2. **Secret**: Must provide `cloudsql-connection-name` in format `project:region:instance`
3. **Network Access**: Private IP connectivity to Cloud SQL (VPC peering or Private Service Connect)

## Configuration

Override in your deployment patch:
- Secret name for CLOUDSQL_CONNECTION_NAME
- Resource limits if needed
- Port (default: 5432)

## Example

```yaml
# In your deployment-patch.yaml
containers:
- name: cloud-sql-proxy
  env:
  - name: CLOUDSQL_CONNECTION_NAME
    valueFrom:
      secretKeyRef:
        name: my-env-secrets  # Your secret name
        key: cloudsql-connection-name
```
