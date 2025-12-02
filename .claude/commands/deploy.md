---
description: You are tasked with deploying the mcp-server-langgraph application to various targets. This command
---
# Unified Deployment Command

You are tasked with deploying the mcp-server-langgraph application to various targets. This command provides a unified interface for deploying to Kubernetes, GKE, Cloud Run, Helm, and Kustomize.

## Deployment Context

**Available Targets**:
- **Kubernetes** (kubectl + Kustomize): GCP, Azure, AWS overlays
- **GKE Staging**: Google Kubernetes Engine (staging-gke overlay)
- **Cloud Run**: Google Cloud Run serverless
- **Helm**: Kubernetes package manager with dependencies
- **Kustomize Overlays**: dev, staging, production
- **LangGraph Platform**: LangGraph Cloud deployment

**Deployment Structure**:
```
deployments/
├── base/               # Base Kubernetes manifests
├── cloudrun/           # Cloud Run deployment
├── helm/               # Helm charts
├── kubernetes/         # K8s overlays (GCP, Azure, AWS)
├── overlays/           # Kustomize overlays (dev, staging, prod)
├── langgraph-platform/ # LangGraph Cloud
└── kong/               # Kong API Gateway
```

## Your Task

### Step 1: Gather Deployment Information

Ask the user using the AskUserQuestion tool:

**Question 1**: What is your deployment target?
- Header: "Target"
- Options:
  - Kubernetes (GCP): Deploy to GKE or GCP Kubernetes
  - Kubernetes (Azure): Deploy to AKS
  - Kubernetes (AWS): Deploy to EKS
  - GKE Staging: Staging environment on GKE
  - Cloud Run: Google Cloud Run serverless
  - Helm: Package manager deployment
  - Kustomize Overlay: Dev/Staging/Production overlay

**Question 2**: What environment?
- Header: "Environment"
- Options:
  - dev: Development environment
  - staging: Staging environment
  - production: Production environment

**Question 3**: Deployment mode?
- Header: "Mode"
- Options:
  - Full Deploy: Complete deployment with all dependencies
  - App Only: Deploy only the application (skip dependencies)
  - Dry Run: Show what would be deployed (no actual deployment)
  - Validate Only: Validate manifests without deploying

### Step 2: Pre-Deployment Validation

Before deploying, validate the environment:

**Validation Checklist**:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  PRE-DEPLOYMENT VALIDATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Environment Checks:
  ✓ Check kubectl installed and configured
  ✓ Verify cluster context (correct cluster)
  ✓ Check namespace exists
  ✓ Verify required secrets exist
  ✓ Validate RBAC permissions
  ✓ Check resource quotas

  Manifest Validation:
  ✓ Run kubectl --dry-run=client
  ✓ Validate YAML syntax
  ✓ Check image tags exist
  ✓ Verify resource requests/limits
  ✓ Validate environment variables

  Dependency Checks:
  ✓ Redis availability
  ✓ PostgreSQL availability
  ✓ OpenFGA availability
  ✓ Keycloak availability (if applicable)
  ✓ External secrets configured (if applicable)
```

**Commands to Run**:
```bash
# Check kubectl
kubectl version --client

# Check cluster context
kubectl config current-context

# Validate manifests
kubectl apply --dry-run=client -k deployments/<overlay>

# Check secrets
kubectl get secrets -n mcp-server-langgraph

# Check resource quotas
kubectl get resourcequota -n mcp-server-langgraph
```

### Step 3: Target-Specific Deployment

#### Target 1: Kubernetes (GCP/Azure/AWS)

**For GCP**:
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

**For Azure (AKS)**:
```bash
# Set context
az aks get-credentials --resource-group <rg> --name <cluster>

# Deploy with Kustomize
kubectl apply -k deployments/kubernetes/overlays/azure/

# Verify
kubectl get pods -n mcp-server-langgraph -w
```

**For AWS (EKS)**:
```bash
# Set context
aws eks update-kubeconfig --name <cluster> --region <region>

# Deploy
kubectl apply -k deployments/kubernetes/overlays/aws/

# Verify
kubectl get all -n mcp-server-langgraph
```

#### Target 2: GKE Staging

**Deployment Steps**:
```bash
# 1. Set GCP project
gcloud config set project <project-id>

# 2. Get cluster credentials
gcloud container clusters get-credentials <cluster-name> --region=us-central1

# 3. Apply staging overlay
kubectl apply -k deployments/overlays/staging-gke/

# 4. Wait for rollout
kubectl rollout status deployment/mcp-server-langgraph -n mcp-server-langgraph

# 5. Verify external secrets
kubectl get externalsecrets -n mcp-server-langgraph

# 6. Check workload identity
kubectl describe sa mcp-server-langgraph-sa -n mcp-server-langgraph

# 7. Test endpoint
kubectl get ingress -n mcp-server-langgraph
```

#### Target 3: Cloud Run

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

#### Target 4: Helm

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
  --values values-staging.yaml  # or values-production.yaml

# 6. Verify release
helm status mcp-server-langgraph -n mcp-server-langgraph

# 7. Get resources
kubectl get all -n mcp-server-langgraph
```

#### Target 5: Kustomize Overlays

**For Dev**:
```bash
kubectl apply -k deployments/overlays/dev/
kubectl get pods -n mcp-server-langgraph -l app=mcp-server-langgraph
```

**For Staging**:
```bash
kubectl apply -k deployments/overlays/staging/
kubectl rollout status deployment/mcp-server-langgraph -n mcp-server-langgraph
```

**For Production**:
```bash
# Production requires extra confirmation
kubectl apply -k deployments/overlays/production/ --dry-run=client
# Review output, then:
kubectl apply -k deployments/overlays/production/
kubectl rollout status deployment/mcp-server-langgraph -n mcp-server-langgraph
```

#### Target 6: LangGraph Platform

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

### Step 4: Post-Deployment Verification

**Verification Checklist**:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  POST-DEPLOYMENT VERIFICATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Application Health:
  ✓ Pods are running (all replicas ready)
  ✓ Health checks passing (/health endpoint)
  ✓ Readiness probes passing
  ✓ No CrashLoopBackOff errors

  Dependencies:
  ✓ Redis connection successful
  ✓ PostgreSQL connection successful
  ✓ OpenFGA connection successful
  ✓ Keycloak connection successful (if applicable)

  Observability:
  ✓ Metrics being exported to Prometheus
  ✓ Traces being sent to Jaeger/OTLP
  ✓ Logs flowing to aggregation system
  ✓ Grafana dashboards showing data

  Network & Ingress:
  ✓ Service endpoints accessible
  ✓ Ingress/Load balancer configured
  ✓ TLS certificates valid
  ✓ DNS resolving correctly

  Security:
  ✓ Network policies in place
  ✓ Pod security policies/standards enforced
  ✓ Secrets properly mounted
  ✓ RBAC configured correctly
```

**Verification Commands**:
```bash
# 1. Check pod status
kubectl get pods -n mcp-server-langgraph -l app=mcp-server-langgraph

# 2. Check pod logs
kubectl logs -n mcp-server-langgraph -l app=mcp-server-langgraph --tail=50

# 3. Test health endpoint
kubectl port-forward -n mcp-server-langgraph svc/mcp-server-langgraph 8000:8000 &
curl http://localhost:8000/health

# 4. Check service endpoints
kubectl get endpoints -n mcp-server-langgraph

# 5. Describe pod for events
kubectl describe pod -n mcp-server-langgraph -l app=mcp-server-langgraph

# 6. Check resource usage
kubectl top pods -n mcp-server-langgraph

# 7. Verify dependencies
kubectl exec -it -n mcp-server-langgraph <pod-name> -- \
  python -c "import redis; r = redis.Redis(host='redis', port=6379); print(r.ping())"
```

### Step 5: Smoke Tests

Run automated smoke tests:

**Basic Smoke Tests**:
```bash
#!/bin/bash
# smoke-test.sh

echo "Running smoke tests..."

# 1. Health check
curl -f http://<service-url>/health || exit 1

# 2. MCP server ping
curl -f http://<service-url>/v1/ping || exit 1

# 3. Authentication test (if applicable)
curl -H "Authorization: Bearer $TEST_TOKEN" \
     http://<service-url>/v1/sessions || exit 1

# 4. Agent invocation test
curl -X POST http://<service-url>/v1/agent/invoke \
     -H "Content-Type: application/json" \
     -d '{"input":"test"}' || exit 1

echo "✅ All smoke tests passed!"
```

### Step 6: Rollback Plan

If deployment fails, provide rollback instructions:

**Rollback Strategy**:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ROLLBACK PLAN
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Automatic Rollback (K8s):
    kubectl rollout undo deployment/mcp-server-langgraph -n mcp-server-langgraph

  Helm Rollback:
    helm rollback mcp-server-langgraph -n mcp-server-langgraph

  Manual Rollback (Kustomize):
    git checkout <previous-commit>
    kubectl apply -k deployments/overlays/<env>/

  Cloud Run Rollback:
    gcloud run services update-traffic mcp-server-langgraph \
      --to-revisions=<previous-revision>=100 \
      --region=us-central1

  Verification After Rollback:
    1. Check pod status
    2. Verify application health
    3. Run smoke tests
    4. Monitor error rates
```

### Step 7: Deployment Summary

Provide a summary after deployment:

**Example Summary**:
```
╔══════════════════════════════════════════════════════════════════╗
║              DEPLOYMENT SUMMARY                                  ║
║              mcp-server-langgraph → GKE Staging                  ║
╠══════════════════════════════════════════════════════════════════╣
║  Target:           GKE Staging (us-central1)                     ║
║  Environment:      staging                                       ║
║  Namespace:        mcp-server-langgraph                          ║
║  Deployment Time:  2m 34s                                        ║
║  Status:           ✅ SUCCESS                                    ║
╠══════════════════════════════════════════════════════════════════╣
║  Resources Deployed:                                             ║
║    - Deployment:       mcp-server-langgraph (3/3 ready)          ║
║    - Service:          mcp-server-langgraph (ClusterIP)          ║
║    - Ingress:          mcp-server-langgraph                      ║
║    - HPA:              mcp-server-langgraph (1-10 replicas)      ║
║    - ServiceAccount:   mcp-server-langgraph-sa                   ║
║    - ExternalSecrets:  mcp-server-langgraph-secrets              ║
╠══════════════════════════════════════════════════════════════════╣
║  Endpoints:                                                      ║
║    - Internal:     mcp-server-langgraph.mcp-server-langgraph.svc ║
║    - External:     https://staging.mcp.example.com               ║
║    - Health:       https://staging.mcp.example.com/health        ║
╠══════════════════════════════════════════════════════════════════╣
║  Verification:                                                   ║
║    ✅ All pods running (3/3)                                     ║
║    ✅ Health checks passing                                      ║
║    ✅ Dependencies connected (Redis, PostgreSQL, OpenFGA)        ║
║    ✅ Metrics exporting to Prometheus                            ║
║    ✅ Smoke tests passed                                         ║
╠══════════════════════════════════════════════════════════════════╣
║  Next Steps:                                                     ║
║    1. Monitor logs: kubectl logs -f -n mcp-server-langgraph      ║
║    2. Check metrics: <grafana-url>                               ║
║    3. Run integration tests                                      ║
║    4. Notify team of successful deployment                       ║
╚══════════════════════════════════════════════════════════════════╝
```

## Deployment Configurations

**Resource Requirements**:
```yaml
# Dev
requests:
  cpu: 100m
  memory: 256Mi
limits:
  cpu: 500m
  memory: 512Mi

# Staging
requests:
  cpu: 250m
  memory: 512Mi
limits:
  cpu: 1000m
  memory: 1Gi

# Production
requests:
  cpu: 500m
  memory: 1Gi
limits:
  cpu: 2000m
  memory: 2Gi
```

**Scaling Configuration**:
- Dev: 1 replica (no autoscaling)
- Staging: 1-3 replicas (HPA: CPU > 70%)
- Production: 3-10 replicas (HPA: CPU > 60%, Memory > 70%)

## Error Handling

**Common Errors**:

1. **ImagePullBackOff**:
   - Check image exists in registry
   - Verify image pull secrets
   - Check image tag is correct

2. **CrashLoopBackOff**:
   - Check application logs
   - Verify environment variables
   - Check secrets are mounted

3. **Pending Pods**:
   - Check resource quotas
   - Verify node resources available
   - Check PV/PVC status

4. **Ingress Not Working**:
   - Verify ingress controller installed
   - Check ingress annotations
   - Verify DNS records

## Integration with CI/CD

This command integrates with:
- `/ci-status` - Check CI/CD pipeline status before deploying
- `/pr-checks` - Validate PR before merge and deploy
- `/validate` - Run all validations pre-deployment
- `/test-all` - Run full test suite before deployment

## Notes

- Always validate in **dry-run** mode first
- Review resource quotas before production deployment
- Ensure secrets are properly configured
- Monitor deployment closely for first 15 minutes
- Have rollback plan ready
- Notify team of production deployments

---

**Success Criteria**:
- ✅ Deployment completed without errors
- ✅ All pods running and ready
- ✅ Health checks passing
- ✅ Dependencies connected
- ✅ Smoke tests passed
- ✅ Metrics and logs flowing
- ✅ Application accessible via endpoints
