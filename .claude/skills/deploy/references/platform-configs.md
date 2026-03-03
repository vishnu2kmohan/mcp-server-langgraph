# Platform Deployment Configurations

Target-specific deployment instructions for all 6 supported deployment targets.

---

## Target 1: Kubernetes (GCP/Azure/AWS)

### GCP

```bash
# Set context
gcloud container clusters get-credentials <cluster-name> --region=<region>

# Deploy with Kustomize
kubectl apply -k deployments/kubernetes/overlays/gcp/

# Wait for rollout
kubectl rollout status deployment/mcp-server-langgraph -n mcp-server-langgraph

# Verify deployment
kubectl get pods -n mcp-server-langgraph
kubectl get svc -n mcp-server-langgraph
```

### Azure (AKS)

```bash
# Set context
az aks get-credentials --resource-group <rg> --name <cluster>

# Deploy with Kustomize
kubectl apply -k deployments/kubernetes/overlays/azure/

# Verify
kubectl get pods -n mcp-server-langgraph -w
```

### AWS (EKS)

```bash
# Set context
aws eks update-kubeconfig --name <cluster> --region <region>

# Deploy
kubectl apply -k deployments/kubernetes/overlays/aws/

# Verify
kubectl get all -n mcp-server-langgraph
```

---

## Target 2: GKE Staging

**Deployment Steps**:
```bash
# 1. Set GCP project
gcloud config set project <project-id>

# 2. Get cluster credentials
gcloud container clusters get-credentials <cluster-name> --region=us-central1

# 3. Apply staging overlay
kubectl apply -k deployments/overlays/stg-gke/

# 4. Wait for rollout
kubectl rollout status deployment/mcp-server-langgraph -n mcp-server-langgraph

# 5. Verify external secrets
kubectl get externalsecrets -n mcp-server-langgraph

# 6. Check workload identity
kubectl describe sa mcp-server-langgraph-sa -n mcp-server-langgraph

# 7. Test endpoint
kubectl get ingress -n mcp-server-langgraph
```

---

## Target 3: Cloud Run

**Deployment Steps**:
```bash
# 1. Navigate to Cloud Run deployment
cd deployments/cloudrun/

# 2. Set up secrets (if first time)
bash setup-secrets.sh

# 3. Deploy to Cloud Run
bash deploy.sh

# Or manually:
gcloud run deploy mcp-server-langgraph \
  --source . \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --set-env-vars="$(cat .env.cloudrun)" \
  --min-instances=1 \
  --max-instances=10 \
  --memory=2Gi \
  --cpu=2

# 4. Get service URL
gcloud run services describe mcp-server-langgraph --region=us-central1 --format="value(status.url)"
```

---

## Target 4: Helm

**Deployment Steps**:
```bash
# 1. Add Helm dependencies
cd deployments/helm/mcp-server-langgraph/
helm dependency update

# 2. Validate chart
helm lint .

# 3. Dry run
helm install mcp-server-langgraph . --dry-run --debug

# 4. Install (dev environment)
helm install mcp-server-langgraph . \
  --namespace mcp-server-langgraph \
  --create-namespace \
  --values values.yaml \
  --set environment=dev

# 5. Or install (staging/production)
helm install mcp-server-langgraph . \
  --namespace mcp-server-langgraph \
  --create-namespace \
  --values values-stg.yaml  # or values-prod.yaml

# 6. Verify release
helm status mcp-server-langgraph -n mcp-server-langgraph

# 7. Get resources
kubectl get all -n mcp-server-langgraph
```

---

## Target 5: Kustomize Overlays

### Dev

```bash
kubectl apply -k deployments/overlays/dev/
kubectl get pods -n mcp-server-langgraph -l app=mcp-server-langgraph
```

### Staging

```bash
kubectl apply -k deployments/overlays/staging/
kubectl rollout status deployment/mcp-server-langgraph -n mcp-server-langgraph
```

### Production

```bash
# Production requires extra confirmation
kubectl apply -k deployments/overlays/prod/ --dry-run=client
# Review output, then:
kubectl apply -k deployments/overlays/prod/
kubectl rollout status deployment/mcp-server-langgraph -n mcp-server-langgraph
```

---

## Target 6: LangGraph Platform

**Deployment Steps**:
```bash
cd deployments/langgraph-platform/

# Deploy using LangGraph CLI
langgraph deploy \
  --name mcp-server-langgraph \
  --file agent.py \
  --env-file .env

# Or using API
curl -X POST https://api.langgraph.com/v1/deployments \
  -H "Authorization: Bearer $LANGGRAPH_API_KEY" \
  -d @deployment-config.json
```
