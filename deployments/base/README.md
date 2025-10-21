# Kubernetes Base Manifests

This directory contains the base Kubernetes manifests for the MCP Server LangGraph deployment.

## Structure

```
base/
├── kustomization.yaml          # Base kustomization
├── deployment.yaml             # Main application deployment
├── service.yaml                # Kubernetes service
├── configmap.yaml              # Configuration
├── secret.yaml                 # Secrets template
├── serviceaccount.yaml         # Service account
├── hpa.yaml                    # Horizontal Pod Autoscaler
├── pdb.yaml                    # Pod Disruption Budget
├── networkpolicy.yaml          # Network policies
├── postgres-statefulset.yaml  # PostgreSQL database
├── postgres-service.yaml       # PostgreSQL service
├── openfga-deployment.yaml    # OpenFGA authorization
├── openfga-service.yaml        # OpenFGA service
├── keycloak-deployment.yaml   # Keycloak SSO
├── keycloak-service.yaml       # Keycloak service
├── redis-session-deployment.yaml  # Redis session store
├── redis-session-service.yaml     # Redis session service
├── qdrant-deployment.yaml     # Qdrant vector database
└── qdrant-service.yaml         # Qdrant service
```

## Usage

### Direct Application

```bash
kubectl apply -k deployments/base
```

### With Overlays (Recommended)

```bash
# Development
kubectl apply -k deployments/overlays/dev

# Staging
kubectl apply -k deployments/overlays/staging

# Production
kubectl apply -k deployments/overlays/production
```

### With Helm

```bash
helm install mcp-server-langgraph deployments/helm/mcp-server-langgraph
```

## Customization

Do not modify these base manifests directly. Instead:

1. Create an overlay in `deployments/overlays/<env>/`
2. Use Kustomize patches to customize
3. Reference the base in your overlay's `kustomization.yaml`

Example overlay structure:

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

bases:
  - ../../base

patches:
  - path: deployment-patch.yaml
    target:
      kind: Deployment
      name: mcp-server-langgraph
```

## Migration

This structure was created by consolidating:
- `deployments/kubernetes/base/` (removed)
- `deployments/kustomize/base/` (moved here)

Old backups are available in `deployments/DEPRECATED/` if needed.
