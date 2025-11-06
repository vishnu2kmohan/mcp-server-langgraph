# Production Deployment Guide

This guide explains how to deploy mcp-server-langgraph to production using Helm and Kustomize with proper secret management.

## Prerequisites

1. External Secrets Operator installed in your cluster
2. Cloud secret manager configured (AWS Secrets Manager, GCP Secret Manager, or Azure Key Vault)
3. kubectl and helm CLI tools installed
4. Access to the target Kubernetes cluster

## Deployment Options

### Option 1: Helm with External Secrets (Recommended for Production)

This approach uses External Secrets Operator to inject secrets from cloud secret managers.

#### Step 1: Configure Cloud Secrets

**For GCP Secret Manager:**
```bash
# Create secrets in GCP Secret Manager
gcloud secrets create anthropic-api-key --data-file=- <<EOF
your-anthropic-api-key-here
EOF

gcloud secrets create jwt-secret-key --data-file=- <<EOF
your-jwt-secret-here
EOF

# Grant service account access
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="serviceAccount:mcp-server-langgraph@PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

**For AWS Secrets Manager:**
```bash
# Create secrets in AWS Secrets Manager
aws secretsmanager create-secret \
  --name anthropic-api-key \
  --secret-string "your-anthropic-api-key-here"

aws secretsmanager create-secret \
  --name jwt-secret-key \
  --secret-string "your-jwt-secret-here"

# Attach IAM policy to service account role
```

#### Step 2: Deploy with Production Values

```bash
# Deploy to production namespace
helm upgrade --install mcp-server-langgraph \
  ./deployments/helm/mcp-server-langgraph \
  --namespace production \
  --create-namespace \
  --values ./deployments/helm/values-production.yaml \
  --set externalSecrets.secretStore.projectID=YOUR_GCP_PROJECT_ID \
  --wait

# Verify deployment
kubectl get pods -n production
kubectl logs -n production -l app=mcp-server-langgraph
```

#### Step 3: Deploy with Staging Values

```bash
# Deploy to staging namespace
helm upgrade --install mcp-server-langgraph \
  ./deployments/helm/mcp-server-langgraph \
  --namespace staging \
  --create-namespace \
  --values ./deployments/helm/values-staging.yaml \
  --set externalSecrets.secretStore.projectID=YOUR_STAGING_PROJECT_ID \
  --wait
```

### Option 2: Kustomize for GKE Production

This approach uses Kustomize with environment variable substitution for GCP-specific deployments.

#### Step 1: Set Environment Variables

```bash
# Set your GCP project ID
export GCP_PROJECT_ID=your-gcp-project-id

# Verify variable is set
echo $GCP_PROJECT_ID
```

#### Step 2: Build and Apply with Kustomize

```bash
# Build the Kustomize configuration
cd deployments/overlays/production-gke
kustomize build . > /tmp/production-manifest.yaml

# Review the generated manifest
less /tmp/production-manifest.yaml

# Apply to cluster
kubectl apply -f /tmp/production-manifest.yaml

# Or apply directly
kustomize build . | kubectl apply -f -
```

#### Step 3: Verify Deployment

```bash
# Check deployment status
kubectl get all -n production-mcp-server-langgraph

# Check if GCP_PROJECT_ID was substituted correctly
kubectl get configmap -n production-mcp-server-langgraph otel-collector-config -o yaml | grep project:

# Verify pods are running
kubectl get pods -n production-mcp-server-langgraph
```

## Secret Management Best Practices

### DO NOT Use Inline Secrets in Production

❌ **Never do this in production:**
```yaml
secrets:
  anthropicApiKey: "sk-ant-api03-..."  # NEVER commit real secrets!
  jwtSecretKey: "my-secret-key"
```

✅ **Instead, use External Secrets:**
```yaml
externalSecrets:
  enabled: true
  secretStore:
    kind: SecretStore
    provider: gcpsm
    projectID: YOUR_PROJECT_ID
  secrets:
    - name: mcp-server-langgraph-secrets
      remoteRefs:
        - remoteKey: anthropic-api-key
          secretKey: anthropic-api-key
```

### External Secrets Operator Setup

If External Secrets Operator is not installed:

```bash
# Install External Secrets Operator
helm repo add external-secrets https://charts.external-secrets.io
helm install external-secrets \
  external-secrets/external-secrets \
  -n external-secrets-system \
  --create-namespace

# Create SecretStore for GCP
kubectl apply -f - <<EOF
apiVersion: external-secrets.io/v1beta1
kind: SecretStore
metadata:
  name: gcpsm-secret-store
  namespace: production
spec:
  provider:
    gcpsm:
      projectID: "YOUR_PROJECT_ID"
      auth:
        workloadIdentity:
          clusterLocation: us-central1
          clusterName: production-cluster
          serviceAccountRef:
            name: mcp-server-langgraph
EOF
```

## Validation

### Pre-Deployment Validation

Run validation tests before deploying to production:

```bash
# Validate Helm chart
helm template mcp-server-langgraph \
  ./deployments/helm/mcp-server-langgraph \
  --values ./deployments/helm/values-production.yaml \
  --debug > /tmp/helm-output.yaml

# Check for REPLACE_ME placeholders (should be none)
grep -i "REPLACE_ME" /tmp/helm-output.yaml && echo "FAIL: Found placeholders!" || echo "PASS: No placeholders"

# Run deployment tests
pytest tests/deployment/test_helm_configuration.py -v
pytest tests/deployment/test_kustomize_build.py -v

# Validate Kustomize build
cd deployments/overlays/production-gke
export GCP_PROJECT_ID=test-project
kustomize build . > /tmp/kustomize-output.yaml
grep "YOUR_PROJECT_ID" /tmp/kustomize-output.yaml && echo "FAIL: Found placeholders!" || echo "PASS: No placeholders"
```

### Post-Deployment Validation

After deploying to staging/production:

```bash
# Run smoke tests against staging
export STAGING_URL=https://staging-api.mcp-server-langgraph.com
curl -f $STAGING_URL/health || echo "Health check failed!"

# Run integration tests
pytest tests/e2e/ --base-url=$STAGING_URL -v

# Check logs for errors
kubectl logs -n staging -l app=mcp-server-langgraph --tail=100 | grep -i error
```

## Troubleshooting

### Issue: ExternalSecret not syncing

**Symptoms:**
```bash
kubectl get externalsecret -n production
# STATUS: SecretSyncedError
```

**Solution:**
```bash
# Check ExternalSecret events
kubectl describe externalsecret mcp-server-langgraph-secrets -n production

# Verify service account has secretmanager.secretAccessor role
gcloud projects get-iam-policy PROJECT_ID \
  --flatten="bindings[].members" \
  --filter="bindings.members:mcp-server-langgraph@*"

# Check SecretStore is configured correctly
kubectl get secretstore -n production -o yaml
```

### Issue: GCP_PROJECT_ID not substituted

**Symptoms:**
Kubernetes resources still contain `$(GCP_PROJECT_ID)` or `YOUR_PROJECT_ID`

**Solution:**
```bash
# Ensure environment variable is set BEFORE running kustomize
export GCP_PROJECT_ID=your-actual-project-id
kustomize build deployments/overlays/production-gke

# Or use sed replacement as fallback
kustomize build deployments/overlays/production-gke | \
  sed "s/\$(GCP_PROJECT_ID)/your-actual-project-id/g" | \
  kubectl apply -f -
```

### Issue: Pods not starting

**Symptoms:**
```bash
kubectl get pods -n production
# STATUS: CrashLoopBackOff or ImagePullBackOff
```

**Solution:**
```bash
# Check pod events
kubectl describe pod -n production -l app=mcp-server-langgraph

# Check logs
kubectl logs -n production -l app=mcp-server-langgraph --previous

# Common issues:
# 1. Missing secrets - verify ExternalSecret is synced
# 2. Wrong image tag - check image pull policy
# 3. Resource limits too low - adjust in values.yaml
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Deploy to Production

on:
  push:
    tags:
      - 'v*'

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Authenticate to GCP
        uses: google-github-actions/auth@v2
        with:
          credentials_json: ${{ secrets.GCP_SA_KEY }}

      - name: Get GKE credentials
        run: |
          gcloud container clusters get-credentials production-cluster \
            --region us-central1 \
            --project ${{ secrets.GCP_PROJECT_ID }}

      - name: Deploy with Helm
        run: |
          helm upgrade --install mcp-server-langgraph \
            ./deployments/helm/mcp-server-langgraph \
            --namespace production \
            --values ./deployments/helm/values-production.yaml \
            --set image.tag=${{ github.ref_name }} \
            --set externalSecrets.secretStore.projectID=${{ secrets.GCP_PROJECT_ID }} \
            --wait

      - name: Run smoke tests
        run: |
          kubectl wait --for=condition=ready pod \
            -l app=mcp-server-langgraph \
            -n production \
            --timeout=300s

          ./scripts/gcp/staging-smoke-tests.sh
```

## Security Checklist

Before deploying to production:

- [ ] All secrets stored in cloud secret manager (not in git)
- [ ] External Secrets Operator installed and configured
- [ ] Workload Identity (GCP) or IRSA (AWS) configured for service account
- [ ] Network policies applied to restrict pod-to-pod communication
- [ ] Pod security policies enforced
- [ ] TLS certificates configured for ingress
- [ ] Resource quotas and limits defined
- [ ] RBAC roles properly scoped
- [ ] Audit logging enabled
- [ ] No REPLACE_ME or YOUR_PROJECT_ID placeholders in rendered manifests

## Support

For deployment issues:
1. Check logs: `kubectl logs -n production -l app=mcp-server-langgraph`
2. Review events: `kubectl events -n production --for deployment/mcp-server-langgraph`
3. Run diagnostics: `kubectl describe pod -n production -l app=mcp-server-langgraph`
4. Consult troubleshooting guide above

For security issues, contact: security@example.com
