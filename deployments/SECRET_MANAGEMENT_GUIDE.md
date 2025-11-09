# Secret Management Guide

Comprehensive guide for managing secrets across all deployment environments.

## Overview

This project uses different secret management strategies depending on the deployment target:

| Environment | Strategy | Secrets Backend | Authentication |
|-------------|----------|-----------------|----------------|
| Local Development | Static Secrets | `.env` file | N/A |
| Base (Kustomize) | Static Secrets (Git-excluded) | Kubernetes Secrets | Manual creation |
| Staging GKE | External Secrets Operator | Google Secret Manager | Workload Identity |
| Production GKE | External Secrets Operator | Google Secret Manager | Workload Identity |
| AWS EKS | External Secrets (planned) | AWS Secrets Manager | IRSA |
| Azure AKS | External Secrets (planned) | Azure Key Vault | Workload Identity |
| Helm Chart | Values or External Secret | Configurable | Varies by environment |

---

## Secret Management Strategies

### 1. Local Development (Docker Compose)

**Location**: `docker-compose.yml`, `.env`

**Strategy**: Plain-text environment variables and files

```bash
# Create .env file
cat > .env <<EOF
ANTHROPIC_API_KEY=your-anthropic-api-key
JWT_SECRET_KEY=your-jwt-secret-$(openssl rand -base64 32)
REDIS_PASSWORD=$(openssl rand -base64 16)
POSTGRES_PASSWORD=$(openssl rand -base64 16)
EOF

# Docker Compose automatically loads .env
docker-compose up -d
```

**Secrets**:
- `ANTHROPIC_API_KEY` - LLM provider API key
- `JWT_SECRET_KEY` - Token signing key
- `REDIS_PASSWORD` - Session store password
- `POSTGRES_PASSWORD` - Database password
- `KEYCLOAK_ADMIN_PASSWORD` - Keycloak admin password

**Security Notes**:
- ⚠️ `.env` is git-ignored (never commit!)
- ⚠️ Rotate secrets regularly
- ⚠️ Use strong random values (not "changeme")

---

### 2. Base Kustomize (Development/Testing)

**Location**: `deployments/base/secret.yaml` (excluded from Git)

**Strategy**: Static Kubernetes Secrets (manual creation)

```bash
# Create secret manually
kubectl create secret generic mcp-server-langgraph-secrets \
  --from-literal=anthropic-api-key="your-key" \
  --from-literal=jwt-secret-key="$(openssl rand -base64 32)" \
  --from-literal=redis-password="$(openssl rand -base64 16)" \
  --from-literal=postgres-password="$(openssl rand -base64 16)" \
  --namespace=mcp-server-langgraph

# Or apply from file (if you create secret.yaml)
kubectl apply -f deployments/base/secret.yaml
```

**Base Exclusion**:
```yaml
# deployments/base/kustomization.yaml
# secret.yaml is intentionally excluded from resources
# Operators must provision secrets separately
```

**Recommended Approach**:
1. **Don't commit secret.yaml** - Keep it local only
2. **Use External Secrets** - Migrate to External Secrets Operator for prod/staging
3. **Document requirements** - List required secret keys in README

---

### 3. Staging/Production GKE (External Secrets Operator)

**Location**: `deployments/overlays/{staging,production}-gke/external-secrets.yaml`

**Strategy**: External Secrets Operator + Google Secret Manager

#### Prerequisites

```bash
# 1. Install External Secrets Operator
helm repo add external-secrets https://charts.external-secrets.io
helm repo update
helm install external-secrets external-secrets/external-secrets \
  --namespace external-secrets-system \
  --create-namespace

# 2. Create GCP service account for External Secrets
gcloud iam service-accounts create external-secrets-sa \
  --project=YOUR_PROJECT_ID

# 3. Grant Secret Manager access
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:external-secrets-sa@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

# 4. Bind Kubernetes SA to GCP SA (Workload Identity)
gcloud iam service-accounts add-iam-policy-binding \
  external-secrets-sa@YOUR_PROJECT_ID.iam.gserviceaccount.com \
  --role=roles/iam.workloadIdentityUser \
  --member="serviceAccount:YOUR_PROJECT_ID.svc.id.goog[staging-mcp-server-langgraph/external-secrets-sa]"
```

#### Create Secrets in Google Secret Manager

```bash
# Set project
export GCP_PROJECT_ID=your-project-id

# Create secrets
echo -n "your-anthropic-api-key" | \
  gcloud secrets create staging-anthropic-api-key \
  --data-file=- \
  --project=$GCP_PROJECT_ID

echo -n "$(openssl rand -base64 32)" | \
  gcloud secrets create staging-jwt-secret \
  --data-file=- \
  --project=$GCP_PROJECT_ID

echo -n "$(openssl rand -base64 16)" | \
  gcloud secrets create staging-redis-password \
  --data-file=- \
  --project=$GCP_PROJECT_ID

echo -n "$(openssl rand -base64 16)" | \
  gcloud secrets create staging-postgres-password \
  --data-file=- \
  --project=$GCP_PROJECT_ID

# Verify secrets created
gcloud secrets list --project=$GCP_PROJECT_ID
```

#### External Secrets Configuration

```yaml
# deployments/overlays/staging-gke/external-secrets.yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: mcp-server-external-secrets
  namespace: staging-mcp-server-langgraph
spec:
  # Refresh interval
  refreshInterval: 1h

  # Secret store reference
  secretStoreRef:
    name: gcpsm-secret-store
    kind: SecretStore

  # Target Kubernetes secret
  target:
    name: staging-mcp-server-langgraph-secrets
    creationPolicy: Owner
    deletionPolicy: Retain

  # Data mapping (GSM secret → K8s secret key)
  data:
    - secretKey: anthropic-api-key
      remoteRef:
        key: staging-anthropic-api-key

    - secretKey: jwt-secret-key
      remoteRef:
        key: staging-jwt-secret

    - secretKey: redis-password
      remoteRef:
        key: staging-redis-password

    - secretKey: postgres-password
      remoteRef:
        key: staging-postgres-password
```

---

### 4. AWS EKS (External Secrets + AWS Secrets Manager)

**Status**: Planned (not yet implemented)

**Strategy**: External Secrets Operator + AWS Secrets Manager + IRSA

#### Prerequisites

```bash
# 1. Install External Secrets Operator (same as GKE)

# 2. Create IAM role for External Secrets
aws iam create-role \
  --role-name external-secrets-role \
  --assume-role-policy-document file://trust-policy.json

# 3. Attach Secrets Manager policy
aws iam attach-role-policy \
  --role-name external-secrets-role \
  --policy-arn arn:aws:iam::aws:policy/SecretsManagerReadWrite

# 4. Annotate Kubernetes ServiceAccount with IAM role
kubectl annotate serviceaccount external-secrets-sa \
  eks.amazonaws.com/role-arn=arn:aws:iam::ACCOUNT_ID:role/external-secrets-role \
  -n mcp-server-langgraph
```

#### Create Secrets in AWS Secrets Manager

```bash
# Create secrets
aws secretsmanager create-secret \
  --name mcp-server/staging/anthropic-api-key \
  --secret-string "your-anthropic-api-key"

aws secretsmanager create-secret \
  --name mcp-server/staging/jwt-secret \
  --secret-string "$(openssl rand -base64 32)"

# Tag secrets for organization
aws secretsmanager tag-resource \
  --secret-id mcp-server/staging/anthropic-api-key \
  --tags Key=Environment,Value=staging Key=Application,Value=mcp-server
```

---

### 5. Azure AKS (External Secrets + Azure Key Vault)

**Status**: Planned (not yet implemented)

**Strategy**: External Secrets Operator + Azure Key Vault + Workload Identity

#### Prerequisites

```bash
# 1. Create Azure Key Vault
az keyvault create \
  --name mcp-server-kv \
  --resource-group mcp-server-rg \
  --location eastus

# 2. Create managed identity
az identity create \
  --name external-secrets-identity \
  --resource-group mcp-server-rg

# 3. Grant Key Vault access
az keyvault set-policy \
  --name mcp-server-kv \
  --object-id $(az identity show --name external-secrets-identity --resource-group mcp-server-rg --query principalId -o tsv) \
  --secret-permissions get list
```

---

## Secret Rotation Strategy

### Rotation Schedule

| Secret Type | Rotation Frequency | Method |
|-------------|-------------------|--------|
| API Keys (Anthropic) | 90 days | Manual (provider managed) |
| JWT Secret | 30 days | Automated (External Secrets) |
| Database Passwords | 90 days | Cloud SQL password rotation |
| Redis Passwords | 90 days | Memorystore password rotation |

### Rotation Procedure

#### GCP (Cloud SQL)

```bash
# 1. Generate new password
NEW_PASSWORD=$(openssl rand -base64 24)

# 2. Update in Google Secret Manager
echo -n "$NEW_PASSWORD" | \
  gcloud secrets versions add staging-postgres-password \
  --data-file=- \
  --project=$GCP_PROJECT_ID

# 3. Update Cloud SQL user password
gcloud sql users set-password postgres \
  --instance=staging-cloudsql-instance \
  --password="$NEW_PASSWORD" \
  --project=$GCP_PROJECT_ID

# 4. External Secrets auto-syncs within 1 hour
# Or force sync:
kubectl annotate externalsecret mcp-server-external-secrets \
  force-sync=$(date +%s) \
  --namespace=staging-mcp-server-langgraph \
  --overwrite

# 5. Restart pods to pick up new secret
kubectl rollout restart deployment/staging-mcp-server-langgraph \
  --namespace=staging-mcp-server-langgraph
```

---

## Workload Identity Setup

### GCP Workload Identity

**Purpose**: Allow Kubernetes pods to authenticate to GCP services without service account keys

#### One-Time Setup

```bash
# 1. Enable Workload Identity on cluster
gcloud container clusters update CLUSTER_NAME \
  --workload-pool=PROJECT_ID.svc.id.goog

# 2. Create GCP service account
gcloud iam service-accounts create mcp-prod-app-sa \
  --project=PROJECT_ID

# 3. Grant permissions (example: Secret Manager)
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="serviceAccount:mcp-prod-app-sa@PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

# 4. Bind Kubernetes SA to GCP SA
gcloud iam service-accounts add-iam-policy-binding \
  mcp-prod-app-sa@PROJECT_ID.iam.gserviceaccount.com \
  --role=roles/iam.workloadIdentityUser \
  --member="serviceAccount:PROJECT_ID.svc.id.goog[production-mcp-server-langgraph/production-mcp-server-langgraph]"

# 5. Annotate Kubernetes ServiceAccount
kubectl annotate serviceaccount production-mcp-server-langgraph \
  iam.gke.io/gcp-service-account=mcp-prod-app-sa@PROJECT_ID.iam.gserviceaccount.com \
  --namespace=production-mcp-server-langgraph
```

**Configuration in Overlay**:

```yaml
# deployments/overlays/production-gke/serviceaccount-patch.yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: mcp-server-langgraph
  annotations:
    # Codex Finding #3: Use actual project ID (not PLACEHOLDER)
    iam.gke.io/gcp-service-account: mcp-prod-app-sa@vishnu-production-project.iam.gserviceaccount.com
```

---

## Troubleshooting

### Issue: Pods fail to start with "secret not found"

**Symptom**:
```
Error: couldn't find key redis-password in Secret mcp-server-langgraph-secrets
```

**Diagnosis**:
1. Check if secret exists:
   ```bash
   kubectl get secrets -n NAMESPACE | grep mcp-server
   ```

2. Check secret keys:
   ```bash
   kubectl describe secret SECRET_NAME -n NAMESPACE
   ```

**Solution**:
- Verify External Secrets is running: `kubectl get pods -n external-secrets-system`
- Check ExternalSecret status: `kubectl describe externalsecret -n NAMESPACE`
- Verify secret exists in Google Secret Manager: `gcloud secrets list --project=PROJECT_ID`
- Check Workload Identity binding

### Issue: External Secrets shows "SecretSyncError"

**Symptom**:
```
Status:
  Conditions:
    Type: SecretSyncError
    Reason: ErrorGettingSecret
```

**Diagnosis**:
```bash
# Check ExternalSecret status
kubectl describe externalsecret mcp-server-external-secrets -n NAMESPACE

# Check SecretStore status
kubectl describe secretstore gcpsm-secret-store -n NAMESPACE

# Check pod logs
kubectl logs -n external-secrets-system deployment/external-secrets
```

**Common Causes**:
1. **Workload Identity not configured**: Check ServiceAccount annotation
2. **IAM permissions missing**: Verify service account has `roles/secretmanager.secretAccessor`
3. **Secret doesn't exist in GSM**: Create secret in Google Secret Manager
4. **Wrong secret name**: Check `remoteRef.key` matches GSM secret name

### Issue: Placeholder values in production

**Symptom**:
```
Error: invalid GCP service account: mcp-prod-app-sa@PLACEHOLDER_GCP_PROJECT_ID.iam.gserviceaccount.com
```

**Diagnosis**:
```bash
# Check for placeholders
kustomize build deployments/overlays/production-gke | grep PLACEHOLDER
```

**Solution**:
- **Codex Finding #3 (P0)**: Fixed in commit d43d7d5
- Update `deployments/overlays/production-gke/config-vars.yaml` with actual project ID
- Use Kustomize replacements for dynamic substitution
- Or use Helm chart with values override

---

## Migration Guide

### From Static Secrets to External Secrets

#### Step 1: Create Secrets in Secret Manager

```bash
# List current secret keys
kubectl get secret mcp-server-langgraph-secrets -o json | \
  jq -r '.data | keys[]'

# Create each secret in GSM
kubectl get secret mcp-server-langgraph-secrets -o json | \
  jq -r '.data["anthropic-api-key"]' | base64 -d | \
  gcloud secrets create staging-anthropic-api-key --data-file=-
```

#### Step 2: Deploy External Secrets Operator

```bash
# Install operator
helm install external-secrets external-secrets/external-secrets \
  --namespace external-secrets-system \
  --create-namespace \
  --set installCRDs=true
```

#### Step 3: Create SecretStore

```bash
kubectl apply -f - <<EOF
apiVersion: external-secrets.io/v1beta1
kind: SecretStore
metadata:
  name: gcpsm-secret-store
  namespace: staging-mcp-server-langgraph
spec:
  provider:
    gcpsm:
      projectID: "YOUR_PROJECT_ID"
      auth:
        workloadIdentity:
          clusterLocation: us-central1
          clusterName: staging-gke-cluster
          serviceAccountRef:
            name: external-secrets-sa
EOF
```

#### Step 4: Create ExternalSecret

```bash
kubectl apply -f deployments/overlays/staging-gke/external-secrets.yaml
```

#### Step 5: Verify and Delete Static Secret

```bash
# Verify External Secret created target
kubectl get secret staging-mcp-server-langgraph-secrets -n staging-mcp-server-langgraph

# Verify keys match
kubectl get secret staging-mcp-server-langgraph-secrets -o json | jq -r '.data | keys[]'

# Test pod with new secret
kubectl rollout restart deployment/staging-mcp-server-langgraph -n staging-mcp-server-langgraph
kubectl rollout status deployment/staging-mcp-server-langgraph -n staging-mcp-server-langgraph

# If successful, delete static secret
kubectl delete secret mcp-server-langgraph-secrets -n staging-mcp-server-langgraph
```

---

## Security Best Practices

### 1. Never Commit Secrets

✅ **Good**:
```yaml
# .gitignore
.env
deployments/base/secret.yaml
*.local.yaml
values-*.local.yaml
```

❌ **Bad**:
```yaml
# Committed in Git
data:
  api-key: "sk-ant-actual-api-key-here"
```

### 2. Use Strong Random Values

✅ **Good**:
```bash
JWT_SECRET=$(openssl rand -base64 32)  # 256-bit entropy
```

❌ **Bad**:
```bash
JWT_SECRET="my-secret-key"  # Weak, predictable
```

### 3. Rotate Regularly

✅ **Good**:
- Automated rotation with External Secrets
- Calendar reminders for manual rotation
- Documented rotation procedures

❌ **Bad**:
- Secrets never rotated
- Same secrets in all environments
- Shared secrets across teams

### 4. Principle of Least Privilege

✅ **Good**:
- Each component has separate service account
- Minimal IAM permissions (read-only where possible)
- Namespace-scoped secrets

❌ **Bad**:
- Single service account for all pods
- `roles/owner` IAM permission
- Cluster-wide secrets

### 5. Audit Secret Access

```bash
# GCP: View secret access logs
gcloud logging read \
  "resource.type=secretmanager.googleapis.com/Secret AND \
   protoPayload.resourceName:projects/PROJECT_ID/secrets/staging-" \
  --limit=50 \
  --project=PROJECT_ID

# Kubernetes: Audit who accessed secrets
kubectl get events --field-selector involvedObject.name=SECRET_NAME -n NAMESPACE
```

---

## Required Secrets by Environment

### Development (Local)

| Secret Key | Description | Example Value |
|------------|-------------|---------------|
| `ANTHROPIC_API_KEY` | Anthropic API key | `sk-ant-...` |
| `JWT_SECRET_KEY` | JWT signing key | Random 32-byte base64 |
| `REDIS_PASSWORD` | Redis password | Random 16-byte base64 |
| `POSTGRES_PASSWORD` | PostgreSQL password | Random 16-byte base64 |

### Staging GKE

| Secret Key | GSM Secret Name | Description |
|------------|-----------------|-------------|
| `anthropic-api-key` | `staging-anthropic-api-key` | LLM API key |
| `jwt-secret-key` | `staging-jwt-secret` | Token signing |
| `redis-url` | `staging-redis-url` | Memorystore Redis URL |
| `redis-password` | `staging-redis-password` | Redis auth |
| `postgres-password` | `staging-postgres-password` | Cloud SQL password |
| `keycloak-admin-password` | `staging-keycloak-admin` | Keycloak admin |

### Production GKE

| Secret Key | GSM Secret Name | Description |
|------------|-----------------|-------------|
| `anthropic-api-key` | `production-anthropic-api-key` | LLM API key (higher quota) |
| `jwt-secret-key` | `production-jwt-secret` | Token signing (rotated monthly) |
| `redis-url` | `production-redis-url` | Memorystore Redis HA URL |
| `redis-password` | `production-redis-password` | Redis auth (rotated) |
| `postgres-password` | `production-postgres-password` | Cloud SQL password (rotated) |

---

## References

- [External Secrets Operator Documentation](https://external-secrets.io/latest/)
- [Google Secret Manager](https://cloud.google.com/secret-manager/docs)
- [AWS Secrets Manager](https://aws.amazon.com/secrets-manager/)
- [Azure Key Vault](https://azure.microsoft.com/en-us/products/key-vault/)
- [Kubernetes Secrets](https://kubernetes.io/docs/concepts/configuration/secret/)
- [Workload Identity (GCP)](https://cloud.google.com/kubernetes-engine/docs/how-to/workload-identity)
- [IRSA (AWS)](https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts.html)

---

## Support

For secret management issues:
1. Check this guide's troubleshooting section
2. Review External Secrets logs: `kubectl logs -n external-secrets-system -l app.kubernetes.io/name=external-secrets`
3. Verify IAM permissions in cloud provider console
4. Contact platform team for Workload Identity setup

---

**Last Updated**: 2025-11-09
**Related Codex Findings**: #3 (P0 - Placeholder leakage), #7 (P1 - Secret references)
