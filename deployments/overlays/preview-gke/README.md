# GKE Staging Overlay - Cloud-Native Architecture

**Last Updated**: 2025-11-02
**Purpose**: Production-ready GKE staging environment using cloud-managed services

## Architecture Overview

This overlay implements a **hybrid cloud-native architecture**:

### ✅ Cloud-Managed Services (Recommended)

1. **PostgreSQL** → **Cloud SQL**
   - Instance: `mcp-preview-postgres` (10.110.0.3)
   - Databases: keycloak, openfga, gdpr
   - Connection: Via Cloud SQL Proxy sidecar
   - Benefits: Automated backups, high availability, managed patches

2. **Redis** → **Memorystore Redis**
   - Instance: `mcp-preview-redis` (10.110.1.4:6379)
   - Connection: Direct private IP via VPC
   - Benefits: High availability, automatic failover, managed

### ⚠️  Self-Hosted Services (No Managed Alternative)

3. **Keycloak** - Identity & Access Management
   - Deployment: Kubernetes pods
   - Database: Connects to Cloud SQL via proxy sidecar
   - Reason: No direct GCP equivalent (Cloud Identity is different)

4. **OpenFGA** - Fine-Grained Authorization
   - Deployment: Kubernetes pods
   - Database: Connects to Cloud SQL via proxy sidecar
   - Reason: No GCP managed service

5. **Qdrant** - Vector Database
   - Deployment: Kubernetes pods with PVC
   - Reason: No GCP managed vector DB yet (Vertex AI Vector Search is different)

## Key Differences from Base

| Component | Base | GKE Staging |
|-----------|------|-------------|
| **PostgreSQL** | StatefulSet in K8s | Cloud SQL + Proxy |
| **Redis** | Deployment in K8s | Memorystore Redis |
| **Keycloak** | Self-hosted | Self-hosted + Cloud SQL |
| **OpenFGA** | Self-hosted | Self-hosted + Cloud SQL |
| **Qdrant** | Self-hosted | Self-hosted (same) |

## Configuration Details

### Cloud SQL Connection

**Main Application** (`deployment-patch.yaml`):
```yaml
containers:
- name: cloud-sql-proxy
  image: gcr.io/cloud-sql-connectors/cloud-sql-proxy:2.11.4
  args:
    - "vishnu-sandbox-20250310:us-central1:mcp-preview-postgres"
    - "--port=5432"
```

**Keycloak & OpenFGA**:
Similar Cloud SQL Proxy sidecars added via patches (see respective patch files)

### Memorystore Redis Connection

**Connection String**: `10.110.1.4:6379`
**Authentication**: Redis AUTH (password in Secret Manager)
**SSL/TLS**: Not required (private VPC)

##Services Excluded from Base

The following base resources are **intentionally excluded** for GKE staging:

- `postgres-statefulset.yaml` - Use Cloud SQL instead
- `postgres-service.yaml` - Not needed (Cloud SQL Proxy provides localhost:5432)
- `postgres-gdpr-schema-configmap.yaml` - Schema applied via migrations
- `redis-session-deployment.yaml` - Use Memorystore instead
- `redis-session-service.yaml` - Connect directly to Memorystore IP

## Deployment Instructions

### Prerequisites

1. **Cloud SQL Instance**: `mcp-preview-postgres` must exist
2. **Memorystore Redis**: `mcp-preview-redis` must exist
3. **Secrets in Secret Manager**:
   - `preview-keycloak-db-password`
   - `preview-openfga-db-password`
   - `preview-redis-password`

Run infrastructure setup if not done:
```bash
bash scripts/gcp/setup-preview-infrastructure.sh
```

### Deploy

```bash
kubectl apply -k deployments/overlays/preview-gke
```

### Verify

```bash
# Check all pods are running
kubectl get pods -n mcp-staging

# Verify Cloud SQL connectivity
kubectl logs -n mcp-staging -l app=mcp-server-langgraph -c cloud-sql-proxy

# Verify Memorystore Redis connectivity
kubectl exec -n mcp-staging -it POD_NAME -- redis-cli -h 10.110.1.4 -a PASSWORD ping
```

## Cost Savings

Using cloud-managed services provides:

- **Reduced operational overhead**: No database maintenance, patching, backups
- **Better reliability**: 99.95% SLA for Cloud SQL, 99.9% for Memorystore
- **Automatic scaling**: Cloud SQL can auto-scale storage
- **Simplified disaster recovery**: Point-in-time recovery, automated backups

**Estimated Monthly Cost** (vs self-hosted):
- Cloud SQL: $50/month (vs $0 for self-hosted, but + ops time)
- Memorystore: $100/month (vs $0 for self-hosted, but + ops time)
- **Net savings**: Reduces on-call burden, faster recovery time

## Troubleshooting

### PostgreSQL Connection Issues

```bash
# Check Cloud SQL Proxy logs
kubectl logs -n mcp-staging POD_NAME -c cloud-sql-proxy

# Verify Workload Identity
gcloud iam service-accounts get-iam-policy \
  mcp-preview-sa@vishnu-sandbox-20250310.iam.gserviceaccount.com

# Test connection
kubectl exec -n mcp-staging -it POD_NAME -- nc -zv 127.0.0.1 5432
```

### Redis Connection Issues

```bash
# Check Memorystore Redis status
gcloud redis instances describe mcp-preview-redis --region=us-central1

# Test connection from pod
kubectl run -it --rm redis-test --image=redis:alpine -n mcp-staging -- \
  redis-cli -h 10.110.1.4 -a $(gcloud secrets versions access latest --secret=preview-redis-password) ping
```

## Future Enhancements

- **Cloud Identity Platform**: Replace Keycloak (requires app changes)
- **Vertex AI Vector Search**: Replace Qdrant (requires embedding format changes)
- **Cloud Run for OpenFGA**: Serverless authorization service
- **Cloud Memorystore for Redis Cluster**: For higher throughput

## Related Documentation

- Infrastructure Setup: `scripts/gcp/setup-preview-infrastructure.sh`
- Cloud SQL Reference: `docs/deployment/gcp-preview-infrastructure.md`
- Deployment Prevention: `docs/deployment/deployment-issues-prevention.md`
