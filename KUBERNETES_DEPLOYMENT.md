# Kubernetes Deployment Guide

Complete guide for deploying MCP Server with LangGraph to Kubernetes (GKE, EKS, AKS, Rancher, VMware Tanzu).

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
# Install with default values
helm install langgraph-agent ./helm/langgraph-agent \
  --namespace langgraph-agent \
  --create-namespace

# Install with custom values
helm install langgraph-agent ./helm/langgraph-agent \
  --namespace langgraph-agent \
  --create-namespace \
  --values custom-values.yaml

# Install with CLI overrides
helm install langgraph-agent ./helm/langgraph-agent \
  --namespace langgraph-agent \
  --create-namespace \
  --set image.repository=gcr.io/my-project/langgraph-agent \
  --set image.tag=v1.0.0 \
  --set secrets.anthropicApiKey=$ANTHROPIC_API_KEY \
  --set secrets.jwtSecretKey=$JWT_SECRET_KEY

# Upgrade existing deployment
helm upgrade langgraph-agent ./helm/langgraph-agent \
  --namespace langgraph-agent \
  --reuse-values \
  --set image.tag=v1.1.0

# Rollback
helm rollback langgraph-agent 1 --namespace langgraph-agent
```

### Kustomize

Environment-specific overlays without templating.

```bash
# Development
kubectl apply -k kustomize/overlays/dev

# Staging
kubectl apply -k kustomize/overlays/staging

# Production
kubectl apply -k kustomize/overlays/production

# Preview changes before applying
kubectl kustomize kustomize/overlays/production

# Delete
kubectl delete -k kustomize/overlays/dev
```

### kubectl

Direct manifest application (less flexible).

```bash
# Apply all base manifests
kubectl apply -f kubernetes/base/

# Apply individual resources
kubectl apply -f kubernetes/base/namespace.yaml
kubectl apply -f kubernetes/base/configmap.yaml
kubectl apply -f kubernetes/base/secret.yaml
kubectl apply -f kubernetes/base/deployment.yaml
kubectl apply -f kubernetes/base/service.yaml
```

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
helm install langgraph-agent ./helm/langgraph-agent \
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
helm install langgraph-agent ./helm/langgraph-agent \
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
helm install langgraph-agent ./helm/langgraph-agent \
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
helm install langgraph-agent ./helm/langgraph-agent \
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
helm install langgraph-agent ./helm/langgraph-agent \
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
  --from-literal=openfga-model-id=$OPENFGA_MODEL_ID
```

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

**Health check failures:**
- Verify OpenFGA is accessible
- Check secrets are mounted correctly
- Review application logs

**Performance issues:**
- Check HPA metrics
- Review resource utilization
- Check for network policies blocking traffic

### Delete Everything

```bash
# Helm
helm uninstall langgraph-agent --namespace langgraph-agent

# Kustomize
kubectl delete -k kustomize/overlays/production

# kubectl
kubectl delete namespace langgraph-agent
```

## CI/CD Integration

See `.github/workflows/ci.yaml` for GitHub Actions or `.gitlab-ci.yml` for GitLab CI.

## Production Checklist

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
