# Production GKE Overlay - Helm-Based Deployment Recommended

## ⚠️ Important: Use Helm for Production

**This Kustomize overlay is maintained for backward compatibility only.**

For production deployments, we strongly recommend using the **Helm chart** with the production values file:

```bash
helm install mcp-server ./deployments/helm/mcp-server-langgraph \
  -f deployments/helm/values-production-gke.yaml \
  --set gcp.projectId=YOUR_PROJECT_ID \
  --set ingress.hosts[0].host=api.example.com \
  --namespace production-mcp-server-langgraph \
  --create-namespace
```

### Why Helm?

- ✅ **Proper templating**: GCP project ID and other variables are correctly templated
- ✅ **Type safety**: Values are validated against schema
- ✅ **Reusability**: Same chart works across environments with different values files
- ✅ **Ecosystem**: Integrates with Helm ecosystem (Helmfile, ArgoCD Helm support, etc.)
- ✅ **Maintained**: Actively maintained with proper variable substitution

### Kustomize Limitations

The Kustomize overlay has known limitations:

1. **Manual variable substitution required**: `$(GCP_PROJECT_ID)` and placeholders must be replaced manually
2. **No type validation**: Easy to deploy with invalid configuration
3. **Complex replacements**: Kustomize replacements don't work for all fields

## Using Kustomize (Not Recommended)

If you must use Kustomize, follow these steps:

### Prerequisites

1. Set required environment variables:
```bash
export GCP_PROJECT_ID="your-gcp-project-id"
export IMAGE_TAG="2.8.0"  # Or use latest
```

2. Ensure you have:
   - Cloud SQL instance configured
   - Memorystore Redis configured
   - Workload Identity configured
   - External Secrets Operator installed

### Build and Deploy

```bash
# Build with variable substitution
kustomize build deployments/overlays/production-gke | \
  sed "s/PLACEHOLDER_GCP_PROJECT_ID/${GCP_PROJECT_ID}/g" | \
  kubectl apply -f -
```

Or use `envsubst`:

```bash
kustomize build deployments/overlays/production-gke | \
  envsubst '${GCP_PROJECT_ID}' | \
  kubectl apply -f -
```

### Required Manual Steps

Before deploying, you must:

1. **Replace GCP_PROJECT_ID** in:
   - `environment-vars.yaml`
   - `otel-collector-configmap-patch.yaml`
   - Image name in `kustomization.yaml`
   - ServiceAccount annotation in `serviceaccount-patch.yaml`

2. **Configure External Secrets**:
   - Install External Secrets Operator
   - Create SecretStore pointing to GCP Secret Manager
   - Populate secrets in Secret Manager

3. **Setup Cloud SQL and Redis**:
   - Create Cloud SQL instance
   - Create Memorystore Redis instance
   - Configure VPC connectivity

### Verification

After deployment:

```bash
# Check deployment status
kubectl get deployment -n production-mcp-server-langgraph

# Check pods
kubectl get pods -n production-mcp-server-langgraph

# Check logs
kubectl logs -n production-mcp-server-langgraph \
  -l app=mcp-server-langgraph \
  --tail=50

# Verify OpenTelemetry config has correct project ID
kubectl get configmap production-otel-collector-config \
  -n production-mcp-server-langgraph \
  -o yaml | grep "project:"
```

## Migration from Kustomize to Helm

To migrate an existing Kustomize deployment to Helm:

1. **Export current configuration**:
```bash
kubectl get configmap production-mcp-server-langgraph-config \
  -n production-mcp-server-langgraph \
  -o yaml > current-config.yaml
```

2. **Create Helm values** from current config:
```bash
# Review current-config.yaml and populate values-production-gke.yaml accordingly
```

3. **Dry run Helm deployment**:
```bash
helm install mcp-server ./deployments/helm/mcp-server-langgraph \
  -f deployments/helm/values-production-gke.yaml \
  --set gcp.projectId=YOUR_PROJECT_ID \
  --namespace production-mcp-server-langgraph \
  --dry-run --debug
```

4. **Deploy via Helm**:
```bash
# First, backup existing deployment
kubectl get all -n production-mcp-server-langgraph -o yaml > backup.yaml

# Deploy via Helm (will replace existing resources)
helm install mcp-server ./deployments/helm/mcp-server-langgraph \
  -f deployments/helm/values-production-gke.yaml \
  --set gcp.projectId=YOUR_PROJECT_ID \
  --namespace production-mcp-server-langgraph
```

## Troubleshooting

### Issue: Unsubstituted variables in deployed manifests

**Symptoms**: Seeing `$(GCP_PROJECT_ID)` or `PLACEHOLDER_` in running pods

**Solution**: Use the `sed` or `envsubst` commands shown above to replace placeholders before applying

### Issue: Image pull failures

**Symptoms**: Pods stuck in `ImagePullBackOff`

**Solution**: Verify GCP_PROJECT_ID is correctly substituted in image name:
```bash
kubectl describe pod -n production-mcp-server-langgraph \
  -l app=mcp-server-langgraph | grep Image:
```

### Issue: OpenTelemetry export failures

**Symptoms**: Logs show "permission denied" or "project not found"

**Solution**: Verify:
1. Project ID is correctly set in otel-collector ConfigMap
2. Workload Identity is configured
3. GCP service account has required permissions

## References

- [Helm Chart Configuration](../../helm/mcp-server-langgraph/Chart.yaml)
- [Production Values File](../../helm/values-production-gke.yaml)
- [Kustomize Documentation](https://kustomize.io/)
- [Workload Identity Setup](https://cloud.google.com/kubernetes-engine/docs/how-to/workload-identity)
