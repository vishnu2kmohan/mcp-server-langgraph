# Kubernetes Deployment Guide

Complete guide for deploying MCP Server with LangGraph to Kubernetes (GKE, EKS, AKS, Rancher, VMware Tanzu).

> **📦 Version Compatibility**: See [VERSION_COMPATIBILITY.md](VERSION_COMPATIBILITY.md) for detailed version information and upgrade guidance.

## What's New in v2.4.0

**Infrastructure Updates (2025-10-14)**:
- **🔄 Updated All Images**: OpenFGA (v1.10.2), Keycloak (26.4.0), OTEL Collector (0.137.0), Prometheus (v3.2.1), Grafana (11.5.1)
- **🗄️ PostgreSQL 16**: Upgraded from 15-alpine to 16-alpine with StatefulSet deployment
- **📊 Observability Stack Refresh**: Major updates to monitoring and tracing components
- **🎯 Complete K8s Manifests**: Added missing OpenFGA and PostgreSQL base manifests
- **📦 Updated Helm Dependencies**: All Bitnami charts updated to latest stable versions

## What's New in v2.1.0

This release adds enterprise authentication and session management capabilities:

- **🔐 Keycloak SSO**: Production-ready OpenID Connect/OAuth2 authentication provider
- **💾 Redis Session Store**: Persistent session management with TTL and sliding windows
- **🔄 Pluggable Authentication**: Switch between inmemory (dev) and Keycloak (production)
- **📦 Helm Dependencies**: Automatic deployment of Keycloak and Redis via Helm chart
- **🎯 Environment-Specific Configs**: Dev uses inmemory auth, Production uses Keycloak+Redis
- **📊 Enhanced Monitoring**: 9 new Prometheus alerts for Keycloak, Redis, and sessions

See the [Keycloak Integration Guide](../integrations/keycloak.md) for detailed setup and configuration.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Container Image](#container-image)
- [Deployment Methods](#deployment-methods)
  - [Helm (Recommended)](#helm-recommended)
  - [Kustomize](#kustomize)
  - [kubectl](#kubectl)
- [Platform-Specific Guides](#platform-specific-guides)
  - [Google Kubernetes Engine (GKE)](#google-kubernetes-engine-gke)
  - [Amazon Elastic Kubernetes Service (EKS)](#amazon-elastic-kubernetes-service-eks)
  - [Azure Kubernetes Service (AKS)](#azure-kubernetes-service-aks)
  - [Rancher](#rancher)
  - [VMware Tanzu](#vmware-tanzu)
- [Secrets Management](#secrets-management)
- [Monitoring and Observability](#monitoring-and-observability)
- [Scaling](#scaling)
- [Troubleshooting](#troubleshooting)

## Prerequisites

- Kubernetes cluster 1.25+ (any distribution)
- `kubectl` configured to communicate with your cluster
- Helm 3.0+ (for Helm deployments)
- Container registry access (Docker Hub, GCR, ECR, ACR)
- Secrets (Anthropic API key, JWT secret, OpenFGA credentials)
- **NEW v2.1.0**: Keycloak client credentials (if using Keycloak auth)
- **NEW v2.1.0**: Redis password (if using Redis sessions)
- **NEW v2.4.0**: PostgreSQL password (for shared database)

**Container Image Versions** (as of v2.4.0):
- OpenFGA: v1.10.2
- Keycloak: 26.4.0
- PostgreSQL: 16-alpine
- Redis: 7-alpine
- BusyBox (init containers): 1.36

See [VERSION_COMPATIBILITY.md](VERSION_COMPATIBILITY.md) for complete version matrix and upgrade guidance.

## Container Image

### Build the Image

```bash
# Build for single architecture
docker build -t langgraph-agent:latest .

# Build for multiple architectures (required for mixed clusters)
docker buildx build --platform linux/amd64,linux/arm64 -t langgraph-agent:latest .
```

### Push to Registry

```bash
# Docker Hub
docker tag langgraph-agent:latest your-username/langgraph-agent:latest
docker push your-username/langgraph-agent:latest

# Google Container Registry (GCR)
docker tag langgraph-agent:latest gcr.io/PROJECT_ID/langgraph-agent:latest
docker push gcr.io/PROJECT_ID/langgraph-agent:latest

# Amazon Elastic Container Registry (ECR)
aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin ACCOUNT_ID.dkr.ecr.us-west-2.amazonaws.com
docker tag langgraph-agent:latest ACCOUNT_ID.dkr.ecr.us-west-2.amazonaws.com/langgraph-agent:latest
docker push ACCOUNT_ID.dkr.ecr.us-west-2.amazonaws.com/langgraph-agent:latest

# Azure Container Registry (ACR)
az acr login --name myregistry
docker tag langgraph-agent:latest myregistry.azurecr.io/langgraph-agent:latest
docker push myregistry.azurecr.io/langgraph-agent:latest
```

## Deployment Methods

### Helm (Recommended)

Most flexible method with templating and easy upgrades.

```bash
# Install with default values (includes Keycloak and Redis dependencies)
helm install langgraph-agent ./deployments/helm/langgraph-agent \
  --namespace langgraph-agent \
  --create-namespace

# Install with custom values
helm install langgraph-agent ./deployments/helm/langgraph-agent \
  --namespace langgraph-agent \
  --create-namespace \
  --values custom-values.yaml

# Install with CLI overrides
helm install langgraph-agent ./deployments/helm/langgraph-agent \
  --namespace langgraph-agent \
  --create-namespace \
  --set image.repository=gcr.io/my-project/langgraph-agent \
  --set image.tag=v1.0.0 \
  --set secrets.anthropicApiKey=$ANTHROPIC_API_KEY \
  --set secrets.jwtSecretKey=$JWT_SECRET_KEY

# NEW v2.1.0: Install with Keycloak SSO and Redis sessions
helm install langgraph-agent ./deployments/helm/langgraph-agent \
  --namespace langgraph-agent \
  --create-namespace \
  --set config.authProvider=keycloak \
  --set config.sessionBackend=redis \
  --set secrets.keycloakClientSecret=$KEYCLOAK_CLIENT_SECRET \
  --set secrets.redisPassword=$REDIS_PASSWORD \
  --set keycloak.enabled=true \
  --set redis.enabled=true

# Upgrade existing deployment
helm upgrade langgraph-agent ./helm/langgraph-agent \
  --namespace langgraph-agent \
  --reuse-values \
  --set image.tag=v1.1.0

# Rollback
helm rollback langgraph-agent 1 --namespace langgraph-agent
```

**Helm Chart Dependencies (NEW v2.1.0)**:

The Helm chart now includes optional dependencies for Keycloak and Redis:

```yaml
# Chart.yaml
dependencies:
  - name: redis
    version: 18.4.0
    repository: https://charts.bitnami.com/bitnami
    condition: redis.enabled
  - name: keycloak
    version: 17.3.0
    repository: https://charts.bitnami.com/bitnami
    condition: keycloak.enabled
```

When `keycloak.enabled=true` or `redis.enabled=true`, Helm automatically deploys and configures these services.

### Kustomize

Environment-specific overlays without templating.

```bash
# Development (inmemory auth, memory sessions)
kubectl apply -k deployments/kustomize/overlays/dev

# Staging (Keycloak auth, Redis sessions)
kubectl apply -k deployments/kustomize/overlays/staging

# Production (Keycloak auth with SSL, Redis sessions with SSL)
kubectl apply -k deployments/kustomize/overlays/production

# Preview changes before applying
kubectl kustomize deployments/kustomize/overlays/production

# Delete
kubectl delete -k deployments/kustomize/overlays/dev
```

**Environment-Specific Configurations (NEW v2.1.0)**:

Each Kustomize overlay configures authentication and session management differently:

- **Dev**: `auth_provider=inmemory`, `session_backend=memory` (no external dependencies)
- **Staging**: `auth_provider=keycloak`, `session_backend=redis` (full enterprise stack)
- **Production**: Same as staging, plus SSL verification and longer TTLs

The base Kustomize configuration includes all infrastructure components (UPDATED v2.4.0):

```yaml
# deployments/kustomize/base/kustomization.yaml
resources:
  - namespace.yaml
  - configmap.yaml
  - secret.yaml
  - deployment.yaml
  - service.yaml
  - postgres-statefulset.yaml      # NEW v2.4.0
  - postgres-service.yaml          # NEW v2.4.0
  - openfga-deployment.yaml        # NEW v2.4.0
  - openfga-service.yaml           # NEW v2.4.0
  - keycloak-deployment.yaml       # NEW v2.1.0, updated v2.4.0
  - keycloak-service.yaml          # NEW v2.1.0
  - redis-session-deployment.yaml  # NEW v2.1.0
  - redis-session-service.yaml     # NEW v2.1.0
```

### kubectl

Direct manifest application (less flexible).

```bash
# Apply all base manifests (includes Keycloak and Redis - NEW v2.1.0)
kubectl apply -f deployments/kubernetes/base/

# Apply individual resources
kubectl apply -f deployments/kubernetes/base/namespace.yaml
kubectl apply -f deployments/kubernetes/base/configmap.yaml
kubectl apply -f deployments/kubernetes/base/secret.yaml
kubectl apply -f deployments/kubernetes/base/deployment.yaml
kubectl apply -f deployments/kubernetes/base/service.yaml

# NEW v2.1.0: Apply Keycloak and Redis resources
kubectl apply -f deployments/kubernetes/base/keycloak-deployment.yaml
kubectl apply -f deployments/kubernetes/base/keycloak-service.yaml
kubectl apply -f deployments/kubernetes/base/redis-session-deployment.yaml
kubectl apply -f deployments/kubernetes/base/redis-session-service.yaml
```

**What's in the Base Manifests (UPDATED v2.4.0)**:

- **postgres-statefulset.yaml**: PostgreSQL 16 StatefulSet with persistent storage, shared by OpenFGA and Keycloak
- **postgres-service.yaml**: Headless and ClusterIP services for database access
- **openfga-deployment.yaml**: OpenFGA v1.10.2 with PostgreSQL backend, 2 replicas, HA setup
- **openfga-service.yaml**: ClusterIP service exposing HTTP, gRPC, and playground
- **keycloak-deployment.yaml**: Keycloak 26.4.0 with PostgreSQL backend, 2 replicas, health probes
- **keycloak-service.yaml**: ClusterIP service with session affinity for OAuth flows
- **redis-session-deployment.yaml**: Redis 7 with AOF persistence, LRU eviction, password protection
- **redis-session-service.yaml**: ClusterIP service for session storage

See [deployments/kubernetes/base/](../../deployments/kubernetes/base/) for full manifest details.

## Platform-Specific Guides

### Google Kubernetes Engine (GKE)

#### 1. Create GKE Cluster

```bash
gcloud container clusters create langgraph-cluster \
  --zone us-central1-a \
  --num-nodes 3 \
  --machine-type n1-standard-2 \
  --enable-autoscaling \
  --min-nodes 3 \
  --max-nodes 10 \
  --enable-stackdriver-kubernetes \
  --enable-ip-alias \
  --enable-network-policy \
  --workload-pool=PROJECT_ID.svc.id.goog

# Get credentials
gcloud container clusters get-credentials langgraph-cluster --zone us-central1-a
```

#### 2. Enable Workload Identity

```bash
# Create GCP service account
gcloud iam service-accounts create langgraph-agent

# Bind Kubernetes SA to GCP SA
gcloud iam service-accounts add-iam-policy-binding \
  langgraph-agent@PROJECT_ID.iam.gserviceaccount.com \
  --role roles/iam.workloadIdentityUser \
  --member "serviceAccount:PROJECT_ID.svc.id.goog[langgraph-agent/langgraph-agent]"

# Annotate Kubernetes ServiceAccount
kubectl annotate serviceaccount langgraph-agent \
  --namespace langgraph-agent \
  iam.gke.io/gcp-service-account=langgraph-agent@PROJECT_ID.iam.gserviceaccount.com
```

#### 3. Deploy with Helm

```bash
helm install langgraph-agent ./deployments/helm/langgraph-agent \
  --namespace langgraph-agent \
  --create-namespace \
  --set image.repository=gcr.io/PROJECT_ID/langgraph-agent \
  --set image.tag=v1.0.0 \
  --set serviceAccount.annotations."iam\.gke\.io/gcp-service-account"=langgraph-agent@PROJECT_ID.iam.gserviceaccount.com
```

#### 4. Configure GKE Ingress

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: langgraph-agent
  annotations:
    kubernetes.io/ingress.class: "gce"
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
spec:
  rules:
  - host: langgraph-agent.example.com
    http:
      paths:
      - path: /*
        pathType: ImplementationSpecific
        backend:
          service:
            name: langgraph-agent
            port:
              number: 80
```

### Amazon Elastic Kubernetes Service (EKS)

#### 1. Create EKS Cluster

```bash
# Using eksctl
eksctl create cluster \
  --name langgraph-cluster \
  --region us-west-2 \
  --nodegroup-name standard-workers \
  --node-type t3.medium \
  --nodes 3 \
  --nodes-min 3 \
  --nodes-max 10 \
  --managed \
  --enable-ssm

# Update kubeconfig
aws eks update-kubeconfig --name langgraph-cluster --region us-west-2
```

#### 2. Setup IAM Roles for Service Accounts (IRSA)

```bash
# Create IAM OIDC provider
eksctl utils associate-iam-oidc-provider \
  --cluster langgraph-cluster \
  --region us-west-2 \
  --approve

# Create IAM policy (if needed for Secrets Manager, S3, etc.)
cat > policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue",
        "secretsmanager:DescribeSecret"
      ],
      "Resource": "arn:aws:secretsmanager:us-west-2:ACCOUNT_ID:secret:langgraph/*"
    }
  ]
}
EOF

aws iam create-policy \
  --policy-name LangGraphAgentPolicy \
  --policy-document file://policy.json

# Create service account with IAM role
eksctl create iamserviceaccount \
  --name langgraph-agent \
  --namespace langgraph-agent \
  --cluster langgraph-cluster \
  --region us-west-2 \
  --attach-policy-arn arn:aws:iam::ACCOUNT_ID:policy/LangGraphAgentPolicy \
  --approve
```

#### 3. Deploy with Helm

```bash
helm install langgraph-agent ./deployments/helm/langgraph-agent \
  --namespace langgraph-agent \
  --create-namespace \
  --set image.repository=ACCOUNT_ID.dkr.ecr.us-west-2.amazonaws.com/langgraph-agent \
  --set image.tag=v1.0.0 \
  --set serviceAccount.annotations."eks\.amazonaws\.com/role-arn"=arn:aws:iam::ACCOUNT_ID:role/langgraph-agent-role
```

#### 4. Configure ALB Ingress

```bash
# Install AWS Load Balancer Controller
helm repo add eks https://aws.github.io/eks-charts
helm install aws-load-balancer-controller eks/aws-load-balancer-controller \
  -n kube-system \
  --set clusterName=langgraph-cluster
```

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: langgraph-agent
  annotations:
    kubernetes.io/ingress.class: alb
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
    alb.ingress.kubernetes.io/certificate-arn: arn:aws:acm:us-west-2:ACCOUNT_ID:certificate/CERT_ID
spec:
  rules:
  - host: langgraph-agent.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: langgraph-agent
            port:
              number: 80
```

### Azure Kubernetes Service (AKS)

#### 1. Create AKS Cluster

```bash
# Create resource group
az group create --name langgraph-rg --location eastus

# Create AKS cluster
az aks create \
  --resource-group langgraph-rg \
  --name langgraph-cluster \
  --node-count 3 \
  --enable-managed-identity \
  --enable-cluster-autoscaler \
  --min-count 3 \
  --max-count 10 \
  --network-plugin azure \
  --enable-oidc-issuer \
  --enable-workload-identity

# Get credentials
az aks get-credentials --resource-group langgraph-rg --name langgraph-cluster
```

#### 2. Setup Workload Identity

```bash
# Get OIDC issuer URL
OIDC_ISSUER=$(az aks show --resource-group langgraph-rg --name langgraph-cluster --query "oidcIssuerProfile.issuerUrl" -o tsv)

# Create managed identity
az identity create \
  --resource-group langgraph-rg \
  --name langgraph-agent-identity

# Get client ID
CLIENT_ID=$(az identity show --resource-group langgraph-rg --name langgraph-agent-identity --query clientId -o tsv)

# Create federated credential
az identity federated-credential create \
  --name langgraph-agent-federated \
  --identity-name langgraph-agent-identity \
  --resource-group langgraph-rg \
  --issuer $OIDC_ISSUER \
  --subject system:serviceaccount:langgraph-agent:langgraph-agent
```

#### 3. Deploy with Helm

```bash
helm install langgraph-agent ./deployments/helm/langgraph-agent \
  --namespace langgraph-agent \
  --create-namespace \
  --set image.repository=myregistry.azurecr.io/langgraph-agent \
  --set image.tag=v1.0.0 \
  --set serviceAccount.annotations."azure\.workload\.identity/client-id"=$CLIENT_ID
```

### Rancher

#### 1. Access Rancher UI

Navigate to your Rancher instance and select your cluster.

#### 2. Deploy via Rancher Apps

1. Go to **Apps & Marketplace**
2. Click **Charts** → **Helm**
3. Upload the `helm/langgraph-agent` chart
4. Configure values in the UI
5. Click **Install**

#### 3. Deploy via kubectl

```bash
# Use Rancher's generated kubeconfig
# Download from Rancher UI or use Rancher CLI

# Deploy
helm install langgraph-agent ./deployments/helm/langgraph-agent \
  --namespace langgraph-agent \
  --create-namespace
```

### VMware Tanzu

#### 1. Login to Tanzu

```bash
tanzu login --server https://your-supervisor.example.com

# Switch to namespace
tanzu cluster kubeconfig get langgraph-cluster --admin

export KUBECONFIG=~/.kube/config
```

#### 2. Create Namespace

```bash
kubectl create namespace langgraph-agent
```

#### 3. Deploy with Helm

```bash
helm install langgraph-agent ./deployments/helm/langgraph-agent \
  --namespace langgraph-agent \
  --set image.repository=harbor.example.com/library/langgraph-agent \
  --set image.tag=v1.0.0
```

#### 4. Configure Tanzu Ingress

Use VMware's NSX-T or Contour ingress controllers.

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: langgraph-agent
  annotations:
    kubernetes.io/ingress.class: contour
spec:
  rules:
  - host: langgraph-agent.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: langgraph-agent
            port:
              number: 80
```

## Secrets Management

### Kubernetes Secrets (Basic)

```bash
kubectl create secret generic langgraph-agent-secrets \
  --namespace langgraph-agent \
  --from-literal=anthropic-api-key=$ANTHROPIC_API_KEY \
  --from-literal=jwt-secret-key=$JWT_SECRET_KEY \
  --from-literal=openfga-store-id=$OPENFGA_STORE_ID \
  --from-literal=openfga-model-id=$OPENFGA_MODEL_ID \
  --from-literal=postgres-username=postgres \
  --from-literal=postgres-password=$POSTGRES_PASSWORD \
  --from-literal=keycloak-client-secret=$KEYCLOAK_CLIENT_SECRET \
  --from-literal=keycloak-admin-username=admin \
  --from-literal=keycloak-admin-password=$KEYCLOAK_ADMIN_PASSWORD \
  --from-literal=redis-password=$REDIS_PASSWORD
```

**Required Secrets**:
- `postgres-username`: PostgreSQL admin username (default: postgres)
- `postgres-password`: PostgreSQL admin password
- `keycloak-client-secret`: OAuth2 client secret from Keycloak setup
- `keycloak-admin-username`: Keycloak admin username
- `keycloak-admin-password`: Keycloak admin password
- `redis-password`: Password for Redis session store

### External Secrets Operator (Recommended)

```bash
# Install External Secrets Operator
helm repo add external-secrets https://charts.external-secrets.io
helm install external-secrets external-secrets/external-secrets \
  --namespace external-secrets-system \
  --create-namespace

# Create SecretStore (AWS Secrets Manager example)
kubectl apply -f - <<EOF
apiVersion: external-secrets.io/v1beta1
kind: SecretStore
metadata:
  name: aws-secrets-manager
  namespace: langgraph-agent
spec:
  provider:
    aws:
      service: SecretsManager
      region: us-west-2
      auth:
        jwt:
          serviceAccountRef:
            name: langgraph-agent
EOF

# Create ExternalSecret
kubectl apply -f - <<EOF
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: langgraph-agent-secrets
  namespace: langgraph-agent
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: aws-secrets-manager
    kind: SecretStore
  target:
    name: langgraph-agent-secrets
  data:
  - secretKey: anthropic-api-key
    remoteRef:
      key: langgraph/anthropic-api-key
  - secretKey: jwt-secret-key
    remoteRef:
      key: langgraph/jwt-secret-key
  - secretKey: keycloak-client-secret
    remoteRef:
      key: langgraph/keycloak-client-secret
  - secretKey: redis-password
    remoteRef:
      key: langgraph/redis-password
EOF
```

### Sealed Secrets

```bash
# Install Sealed Secrets
kubectl apply -f https://github.com/bitnami-labs/sealed-secrets/releases/download/v0.24.0/controller.yaml

# Seal a secret
echo -n "my-secret-value" | kubectl create secret generic langgraph-agent-secrets \
  --dry-run=client \
  --from-file=anthropic-api-key=/dev/stdin \
  -o yaml | \
  kubeseal -o yaml > sealed-secret.yaml

# Apply sealed secret
kubectl apply -f sealed-secret.yaml
```

## Monitoring and Observability

### Prometheus & Grafana

```bash
# Install Prometheus stack
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm install prometheus prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --create-namespace

# ServiceMonitor is auto-created if monitoring.serviceMonitor.enabled=true in values.yaml
```

### Access Grafana

```bash
kubectl port-forward -n monitoring svc/prometheus-grafana 3000:80

# Default credentials: admin/prom-operator
```

### Jaeger

```bash
# Install Jaeger Operator
kubectl create namespace observability
kubectl apply -f https://github.com/jaegertracing/jaeger-operator/releases/download/v1.51.0/jaeger-operator.yaml -n observability

# Create Jaeger instance
kubectl apply -f - <<EOF
apiVersion: jaegertracing.io/v1
kind: Jaeger
metadata:
  name: jaeger
  namespace: observability
spec:
  strategy: production
  storage:
    type: elasticsearch
    elasticsearch:
      nodeCount: 3
EOF
```

## Scaling

### Horizontal Pod Autoscaling

HPA is configured by default in Helm values:

```yaml
autoscaling:
  enabled: true
  minReplicas: 3
  maxReplicas: 10
  targetCPUUtilizationPercentage: 70
  targetMemoryUtilizationPercentage: 80
```

### Vertical Pod Autoscaling

```bash
# Install VPA
kubectl apply -f https://github.com/kubernetes/autoscaler/releases/download/vertical-pod-autoscaler-0.13.0/vpa-v0.13.0.yaml

# Create VPA resource
kubectl apply -f - <<EOF
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: langgraph-agent-vpa
  namespace: langgraph-agent
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: langgraph-agent
  updatePolicy:
    updateMode: "Auto"
EOF
```

### Cluster Autoscaling

Enabled by default in most managed Kubernetes offerings (GKE, EKS, AKS).

## Troubleshooting

### Check Pod Status

```bash
kubectl get pods -n langgraph-agent
kubectl describe pod <pod-name> -n langgraph-agent
kubectl logs <pod-name> -n langgraph-agent
kubectl logs <pod-name> -n langgraph-agent --previous  # Previous container logs
```

### Check Events

```bash
kubectl get events -n langgraph-agent --sort-by='.lastTimestamp'
```

### Debug Container

```bash
kubectl exec -it <pod-name> -n langgraph-agent -- /bin/bash
```

### Common Issues

**Pods not starting:**
- Check image pull secrets
- Verify resource requests/limits
- Check init container logs
- **NEW v2.1.0**: Verify Keycloak and Redis are running if using those backends

**Health check failures:**
- Verify OpenFGA is accessible
- Check secrets are mounted correctly
- Review application logs
- **NEW v2.1.0**: Test Keycloak connectivity from app pod
- **NEW v2.1.0**: Test Redis connectivity from app pod

**Performance issues:**
- Check HPA metrics
- Review resource utilization
- Check for network policies blocking traffic
- **NEW v2.1.0**: Monitor Redis memory usage and eviction rate

### Keycloak Troubleshooting (NEW v2.1.0)

```bash
# Check Keycloak pod status
kubectl get pods -n langgraph-agent -l app.kubernetes.io/name=keycloak

# Check Keycloak logs
kubectl logs -n langgraph-agent -l app.kubernetes.io/name=keycloak --tail=100

# Test Keycloak health endpoint
kubectl run curl-test --rm -it --restart=Never --image=curlimages/curl -- \
  curl -f http://keycloak.langgraph-agent:8080/health

# Port-forward to access Keycloak admin console
kubectl port-forward -n langgraph-agent svc/keycloak 8080:8080
# Then access http://localhost:8080

# Verify realm configuration
python scripts/setup/setup_keycloak.py --verify --environment=production
```

**Common Keycloak Issues:**
- **Client secret mismatch**: Re-run `setup_keycloak.py` and update Kubernetes secret
- **SSL verification errors**: For testing, set `KEYCLOAK_VERIFY_SSL=false` (not for production!)
- **Token refresh failures**: Check session configuration and Redis connectivity
- **Realm not found**: Verify `KEYCLOAK_REALM` ConfigMap value matches deployed realm

See [Keycloak Integration Guide](../integrations/keycloak.md) and [Keycloak Runbooks](../runbooks/) for detailed troubleshooting.

### Redis Session Store Troubleshooting (NEW v2.1.0)

```bash
# Check Redis pod status
kubectl get pods -n langgraph-agent -l app=redis-session

# Check Redis logs
kubectl logs -n langgraph-agent -l app=redis-session --tail=100

# Test Redis connectivity
kubectl run redis-test --rm -it --restart=Never --image=redis:7-alpine \
  --namespace=langgraph-agent \
  -- redis-cli -h redis-session -a "$REDIS_PASSWORD" PING

# Check Redis memory usage
kubectl exec -n langgraph-agent -it \
  $(kubectl get pod -n langgraph-agent -l app=redis-session -o jsonpath='{.items[0].metadata.name}') \
  -- redis-cli -a "$REDIS_PASSWORD" INFO memory

# Check active session count
kubectl exec -n langgraph-agent -it \
  $(kubectl get pod -n langgraph-agent -l app=redis-session -o jsonpath='{.items[0].metadata.name}') \
  -- redis-cli -a "$REDIS_PASSWORD" DBSIZE
```

**Common Redis Issues:**
- **Connection refused**: Check service name (`redis-session`) and port (6379) in REDIS_URL
- **Authentication failed**: Verify `redis-password` secret matches deployed Redis password
- **Out of memory**: Check maxmemory settings in Redis ConfigMap, increase if needed
- **High eviction rate**: Increase Redis memory or reduce SESSION_TTL_SECONDS

See [Redis Runbooks](../runbooks/) for detailed troubleshooting:
- [redis-down.md](../runbooks/redis-down.md) - Service outage recovery
- [redis-memory.md](../runbooks/redis-memory.md) - Memory management
- [session-errors.md](../runbooks/session-errors.md) - Session operation failures

### Delete Everything

```bash
# Helm
helm uninstall langgraph-agent --namespace langgraph-agent

# Kustomize
kubectl delete -k deployments/kustomize/overlays/production

# kubectl
kubectl delete namespace langgraph-agent
```

## CI/CD Integration

See `.github/workflows/ci.yaml` for GitHub Actions or `.gitlab-ci.yml` for GitLab CI.

## Production Checklist

**Infrastructure**:
- [ ] Use External Secrets Operator or cloud-native secret management
- [ ] Configure resource limits and requests
- [ ] Enable HPA and cluster autoscaling
- [ ] Configure Pod Disruption Budget
- [ ] Set up network policies
- [ ] Configure ingress with TLS
- [ ] Enable monitoring and alerting
- [ ] Configure log aggregation
- [ ] Set up backup and disaster recovery
- [ ] Document runbooks
- [ ] Test rollback procedures
- [ ] Configure RBAC appropriately
- [ ] Use dedicated node pools for AI workloads
- [ ] Enable pod security policies/standards

**NEW v2.1.0 - Authentication & Sessions**:
- [ ] Deploy Keycloak with PostgreSQL backend (not H2 in-memory)
- [ ] Configure Keycloak realm and client (run `scripts/setup/setup_keycloak.py`)
- [ ] Deploy Redis session store with persistence enabled
- [ ] Set `KEYCLOAK_VERIFY_SSL=true` in production
- [ ] Configure strong Redis password
- [ ] Set appropriate `SESSION_TTL_SECONDS` for your workload
- [ ] Enable session sliding window for better UX
- [ ] Configure `SESSION_MAX_CONCURRENT` limit
- [ ] Set up Prometheus alerts for Keycloak and Redis
- [ ] Test token refresh flow end-to-end
- [ ] Verify session persistence across Redis restarts
- [ ] Configure backup for Redis session data (if critical)
