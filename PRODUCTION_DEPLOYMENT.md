# Production Deployment Guide

Complete guide for deploying MCP Server with LangGraph to production environments.

## Table of Contents

1. [Pre-Deployment Checklist](#pre-deployment-checklist)
2. [Environment Setup](#environment-setup)
3. [Secret Management](#secret-management)
4. [Infrastructure Preparation](#infrastructure-preparation)
5. [Deployment Methods](#deployment-methods)
6. [Post-Deployment Verification](#post-deployment-verification)
7. [Monitoring & Alerting](#monitoring--alerting)
8. [Rollback Procedures](#rollback-procedures)
9. [Troubleshooting](#troubleshooting)

---

## Pre-Deployment Checklist

### Critical Requirements

Run the validation script before deploying:

```bash
python scripts/validate_production.py
```

**Manual Checklist:**

- [ ] **Git Repository Initialized**: Verify `.git` directory exists
- [ ] **All Tests Passing**: Run `make test` and ensure 100% pass rate
- [ ] **Security Scan Clean**: Run `make security-check` with no critical issues
- [ ] **Code Coverage ≥70%**: Run `make test-coverage`
- [ ] **Environment Configured**: All required secrets and config values set
- [ ] **OpenFGA Setup**: Store and Model IDs generated and configured
- [ ] **Secrets Manager**: Infisical or equivalent configured and tested
- [ ] **Docker Image Built**: Multi-arch image pushed to registry
- [ ] **Kubernetes Cluster Ready**: Cluster accessible and configured
- [ ] **DNS/Ingress Configured**: Domain names and SSL certificates ready
- [ ] **Monitoring Stack Deployed**: Prometheus, Grafana, Jaeger running
- [ ] **Backup Strategy**: Database and secret backup procedures in place
- [ ] **Incident Response Plan**: On-call rotation and runbooks prepared
- [ ] **Documentation Updated**: All README files and guides current

### Security Checklist

- [ ] **JWT Secret Rotated**: Default secret replaced with strong random value
- [ ] **API Keys Secured**: All LLM provider keys stored in secrets manager
- [ ] **OpenFGA Production Instance**: Not using in-memory store
- [ ] **TLS Enabled**: All inter-service communication encrypted
- [ ] **Network Policies**: Kubernetes network policies applied
- [ ] **RBAC Configured**: Least-privilege access controls
- [ ] **Rate Limiting**: Kong or equivalent rate limiting active
- [ ] **Audit Logging**: OpenFGA and application audit logs enabled
- [ ] **Secret Scanning**: Pre-commit hooks prevent secret commits
- [ ] **Vulnerability Scanning**: Container images scanned regularly
- [ ] **Non-Root Containers**: All pods running as non-root user
- [ ] **Pod Security Policies**: PSP or Pod Security Standards enforced

---

## Environment Setup

### 1. Clone and Configure Repository

```bash
# Clone repository
git clone https://github.com/vishnu2kmohan/mcp_server_langgraph.git
cd mcp_server_langgraph

# Create production environment file
cp .env.example .env.production

# Edit with production values
vim .env.production
```

### 2. Configure Production Environment Variables

**Required Variables:**

```bash
# Service
SERVICE_NAME=mcp-server-langgraph
SERVICE_VERSION=1.0.0
ENVIRONMENT=production

# LLM Provider (choose one or configure fallback)
LLM_PROVIDER=google  # or anthropic, openai, azure, bedrock
MODEL_NAME=gemini-2.5-flash-002
ENABLE_FALLBACK=true

# API Keys (use secrets manager - see Secret Management section)
GOOGLE_API_KEY=projects/PROJECT_ID/secrets/GOOGLE_API_KEY
# or
ANTHROPIC_API_KEY=projects/PROJECT_ID/secrets/ANTHROPIC_API_KEY
OPENAI_API_KEY=projects/PROJECT_ID/secrets/OPENAI_API_KEY

# Authentication
JWT_SECRET_KEY=projects/PROJECT_ID/secrets/JWT_SECRET_KEY
JWT_EXPIRATION_SECONDS=3600

# OpenFGA (production instance)
OPENFGA_API_URL=https://openfga.production.yourdomain.com
OPENFGA_STORE_ID=01HXXXXXXXXXXXXXXXXXXX
OPENFGA_MODEL_ID=01HYYYYYYYYYYYYYYYYYY

# Infisical (production project)
INFISICAL_SITE_URL=https://app.infisical.com
INFISICAL_CLIENT_ID=projects/PROJECT_ID/secrets/INFISICAL_CLIENT_ID
INFISICAL_CLIENT_SECRET=projects/PROJECT_ID/secrets/INFISICAL_CLIENT_SECRET
INFISICAL_PROJECT_ID=your-production-project-id

# Observability
OTLP_ENDPOINT=http://otel-collector.monitoring:4317
ENABLE_TRACING=true
ENABLE_METRICS=true
LOG_LEVEL=INFO
```

### 3. Generate Strong Secrets

```bash
# Generate JWT secret (256-bit)
openssl rand -base64 32

# Generate API keys (provider-specific)
# - Google: https://aistudio.google.com/apikey
# - Anthropic: https://console.anthropic.com/
# - OpenAI: https://platform.openai.com/
```

---

## Secret Management

### Option 1: Infisical (Recommended)

**Setup Infisical for Production:**

```bash
# 1. Create production project in Infisical dashboard
# 2. Create machine identity with production access
# 3. Generate client credentials

# 4. Store secrets in Infisical
infisical secrets set JWT_SECRET_KEY "YOUR_SECRET_HERE" --env=production
infisical secrets set GOOGLE_API_KEY "YOUR_API_KEY" --env=production
infisical secrets set ANTHROPIC_API_KEY "YOUR_API_KEY" --env=production
infisical secrets set OPENFGA_STORE_ID "YOUR_STORE_ID" --env=production
infisical secrets set OPENFGA_MODEL_ID "YOUR_MODEL_ID" --env=production

# 5. Configure Kubernetes secret with Infisical credentials
kubectl create secret generic infisical-credentials \
  --from-literal=client-id="YOUR_CLIENT_ID" \
  --from-literal=client-secret="YOUR_CLIENT_SECRET" \
  --from-literal=project-id="YOUR_PROJECT_ID" \
  -n langgraph-agent
```

### Option 2: Kubernetes Secrets

**If not using Infisical:**

```bash
# Create Kubernetes secrets
kubectl create secret generic langgraph-agent-secrets \
  --from-literal=jwt-secret-key="$(openssl rand -base64 32)" \
  --from-literal=google-api-key="YOUR_API_KEY" \
  --from-literal=openfga-store-id="YOUR_STORE_ID" \
  --from-literal=openfga-model-id="YOUR_MODEL_ID" \
  -n langgraph-agent

# Verify secret created
kubectl get secret langgraph-agent-secrets -n langgraph-agent -o yaml
```

### Option 3: Cloud Provider Secret Managers

**Google Secret Manager:**

```bash
# Store secrets
echo -n "YOUR_SECRET" | gcloud secrets create jwt-secret-key --data-file=-

# Grant access to service account
gcloud secrets add-iam-policy-binding jwt-secret-key \
  --member="serviceAccount:langgraph-agent@PROJECT.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

**AWS Secrets Manager:**

```bash
# Store secrets
aws secretsmanager create-secret \
  --name langgraph-agent/jwt-secret-key \
  --secret-string "YOUR_SECRET"

# Update IAM role for pod
```

**Azure Key Vault:**

```bash
# Store secrets
az keyvault secret set \
  --vault-name langgraph-agent-vault \
  --name jwt-secret-key \
  --value "YOUR_SECRET"
```

---

## Infrastructure Preparation

### 1. Deploy OpenFGA (Production)

**PostgreSQL Backend (Required for Production):**

```yaml
# openfga-postgres.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: openfga-config
  namespace: langgraph-agent
data:
  datastore-engine: postgres
  datastore-uri: "postgres://openfga:PASSWORD@postgres:5432/openfga?sslmode=require"

---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: openfga
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: openfga
        image: openfga/openfga:latest
        envFrom:
        - configMapRef:
            name: openfga-config
        - secretRef:
            name: openfga-secrets
```

**Deploy:**

```bash
kubectl apply -f kubernetes/openfga/
kubectl wait --for=condition=ready pod -l app=openfga -n langgraph-agent --timeout=300s
```

### 2. Setup OpenFGA Store and Model

```bash
# Run setup script
python setup_openfga.py --environment=production

# Save output to secrets
OPENFGA_STORE_ID=<store-id-from-output>
OPENFGA_MODEL_ID=<model-id-from-output>

# Store in secrets manager
infisical secrets set OPENFGA_STORE_ID "$OPENFGA_STORE_ID" --env=production
infisical secrets set OPENFGA_MODEL_ID "$OPENFGA_MODEL_ID" --env=production
```

### 3. Deploy Observability Stack

```bash
# Deploy Prometheus
helm upgrade --install prometheus prometheus-community/kube-prometheus-stack \
  --namespace monitoring --create-namespace

# Deploy Jaeger
helm upgrade --install jaeger jaegertracing/jaeger \
  --namespace monitoring

# Deploy Grafana (if not included with Prometheus)
helm upgrade --install grafana grafana/grafana \
  --namespace monitoring \
  --set adminPassword="CHANGE_ME"

# Deploy OpenTelemetry Collector
kubectl apply -f kubernetes/otel-collector/
```

---

## Deployment Methods

### Method 1: Helm (Recommended for Production)

**Build and Push Image:**

```bash
# Build multi-arch image
docker buildx build --platform linux/amd64,linux/arm64 \
  -t ghcr.io/vishnu2kmohan/langgraph-agent:1.0.0 \
  -t ghcr.io/vishnu2kmohan/langgraph-agent:latest \
  --push .
```

**Deploy with Helm:**

```bash
helm upgrade --install langgraph-agent ./helm/langgraph-agent \
  --namespace langgraph-agent \
  --create-namespace \
  --values helm/langgraph-agent/values-production.yaml \
  --set image.repository=ghcr.io/vishnu2kmohan/langgraph-agent \
  --set image.tag=1.0.0 \
  --set replicaCount=3 \
  --set autoscaling.enabled=true \
  --set autoscaling.minReplicas=3 \
  --set autoscaling.maxReplicas=10 \
  --set resources.requests.memory=512Mi \
  --set resources.requests.cpu=500m \
  --set resources.limits.memory=2Gi \
  --set resources.limits.cpu=2000m \
  --set kong.enabled=true \
  --set kong.rateLimitTier=premium \
  --wait --timeout=10m

# Verify deployment
kubectl rollout status deployment/langgraph-agent -n langgraph-agent
```

**Create `values-production.yaml`:**

```yaml
replicaCount: 3

image:
  repository: ghcr.io/vishnu2kmohan/langgraph-agent
  tag: "1.0.0"
  pullPolicy: IfNotPresent

autoscaling:
  enabled: true
  minReplicas: 3
  maxReplicas: 10
  targetCPUUtilizationPercentage: 70
  targetMemoryUtilizationPercentage: 80

resources:
  requests:
    cpu: 500m
    memory: 512Mi
  limits:
    cpu: 2000m
    memory: 2Gi

podDisruptionBudget:
  enabled: true
  minAvailable: 2

ingress:
  enabled: true
  className: nginx
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
  hosts:
    - host: langgraph-agent.yourdomain.com
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: langgraph-agent-tls
      hosts:
        - langgraph-agent.yourdomain.com

kong:
  enabled: true
  rateLimitTier: premium
  rateLimitPerMinute: 1000

secrets:
  useExternalSecrets: true
  infisicalClientId: ""  # Set via --set or external secrets
  infisicalClientSecret: ""
  infisicalProjectId: ""

config:
  environment: production
  logLevel: INFO
  enableTracing: true
  enableMetrics: true
  openfgaApiUrl: https://openfga.production.yourdomain.com
```

### Method 2: Kustomize

```bash
# Deploy to production overlay
kubectl apply -k kustomize/overlays/production

# Verify
kubectl rollout status deployment/prod-langgraph-agent -n langgraph-agent
```

### Method 3: ArgoCD (GitOps)

```yaml
# argocd-application.yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: langgraph-agent-prod
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/vishnu2kmohan/mcp_server_langgraph
    targetRevision: v1.0.0
    path: helm/langgraph-agent
    helm:
      valueFiles:
        - values-production.yaml
  destination:
    server: https://kubernetes.default.svc
    namespace: langgraph-agent
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
      - CreateNamespace=true
```

---

## Post-Deployment Verification

### 1. Health Checks

```bash
# Check pod status
kubectl get pods -n langgraph-agent

# Check health endpoints
POD_NAME=$(kubectl get pod -n langgraph-agent -l app=langgraph-agent -o jsonpath='{.items[0].metadata.name}')

kubectl exec -n langgraph-agent $POD_NAME -- curl -f http://localhost:8000/health
kubectl exec -n langgraph-agent $POD_NAME -- curl -f http://localhost:8000/health/ready
kubectl exec -n langgraph-agent $POD_NAME -- curl -f http://localhost:8000/health/startup
```

### 2. Functional Testing

```bash
# Test MCP endpoint (if using StreamableHTTP)
curl -X POST https://langgraph-agent.yourdomain.com/message \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"query": "Hello, test deployment"}'

# Test authentication
python scripts/test_production.py --endpoint https://langgraph-agent.yourdomain.com

# Test OpenFGA authorization
python example_openfga_usage.py --environment production
```

### 3. Monitoring Verification

```bash
# Check metrics collection
curl https://langgraph-agent.yourdomain.com/metrics/prometheus

# Verify traces in Jaeger
open http://jaeger.yourdomain.com

# Check Grafana dashboards
open https://grafana.yourdomain.com
```

### 4. Load Testing

```bash
# Run load test
kubectl run load-test --image=williamyeh/wrk --rm -it -- \
  wrk -t 10 -c 100 -d 30s https://langgraph-agent.yourdomain.com/health

# Monitor during load test
kubectl top pods -n langgraph-agent
```

---

## Monitoring & Alerting

### Recommended Alerts

**Create alerts in Prometheus/Alertmanager:**

```yaml
# prometheus-alerts.yaml
groups:
  - name: langgraph-agent
    interval: 30s
    rules:
      - alert: HighErrorRate
        expr: rate(agent_calls_failed_total[5m]) > 0.05
        for: 5m
        annotations:
          summary: "High error rate detected"

      - alert: HighLatency
        expr: histogram_quantile(0.95, agent_response_duration_bucket) > 5
        for: 5m
        annotations:
          summary: "P95 latency above 5 seconds"

      - alert: PodCrashLooping
        expr: rate(kube_pod_container_status_restarts_total[15m]) > 0
        annotations:
          summary: "Pod is crash looping"

      - alert: LowAvailability
        expr: avg(up{job="langgraph-agent"}) < 0.9
        for: 5m
        annotations:
          summary: "Service availability below 90%"
```

---

## Rollback Procedures

### Helm Rollback

```bash
# List releases
helm history langgraph-agent -n langgraph-agent

# Rollback to previous version
helm rollback langgraph-agent -n langgraph-agent

# Rollback to specific revision
helm rollback langgraph-agent 3 -n langgraph-agent
```

### Kubernetes Rollback

```bash
# Rollback deployment
kubectl rollout undo deployment/langgraph-agent -n langgraph-agent

# Rollback to specific revision
kubectl rollout undo deployment/langgraph-agent --to-revision=2 -n langgraph-agent
```

### ArgoCD Rollback

```bash
# Rollback via ArgoCD
argocd app rollback langgraph-agent-prod
```

---

## Troubleshooting

See separate [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for detailed debugging guides.

**Common Issues:**

1. **Pods not starting**: Check secrets and config maps
2. **Health checks failing**: Verify OpenFGA and Infisical connectivity
3. **High latency**: Check LLM provider API status and rate limits
4. **Authentication errors**: Verify JWT secret and token expiration
5. **Authorization failures**: Check OpenFGA store/model IDs

---

## Production Maintenance

### Regular Tasks

- **Daily**: Monitor alerts, check error rates, review logs
- **Weekly**: Review metrics dashboards, check resource utilization
- **Monthly**: Rotate secrets, update dependencies, review security scans
- **Quarterly**: Load testing, disaster recovery drills, security audits

### Scaling Recommendations

- **Horizontal**: 3-10 replicas based on load
- **Vertical**: 512Mi-2Gi memory, 500m-2000m CPU per pod
- **HPA**: Target 70% CPU, 80% memory utilization
- **Kong Rate Limiting**: 60-1000 req/min based on tier

---

For additional support, see:
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- [SECURITY_AUDIT.md](SECURITY_AUDIT.md)
- [KUBERNETES_DEPLOYMENT.md](KUBERNETES_DEPLOYMENT.md)
