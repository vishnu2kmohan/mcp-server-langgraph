# Complete Deployment Guide
## MCP Server LangGraph - AWS EKS Production Deployment

This guide covers deploying all phases of the AWS EKS best practices implementation.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Phase 1: Infrastructure](#phase-1-infrastructure)
3. [Phase 2: GitOps](#phase-2-gitops)
4. [Phase 3: Security](#phase-3-security)
5. [Phase 4: High Availability](#phase-4-high-availability)
6. [Phase 5: Operational Excellence](#phase-5-operational-excellence)
7. [Verification](#verification)
8. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Tools Required

```bash
# Check versions
terraform --version  # >= 1.5.0
aws --version        # >= 2.x
kubectl version      # >= 1.28
helm version         # >= 3.12
```

### AWS Credentials

```bash
# Configure AWS CLI
aws configure

# Verify access
aws sts get-caller-identity
```

---

## Phase 1: Infrastructure

### Step 1: Create Terraform Backend

```bash
cd terraform/backend-setup

# Initialize Terraform
terraform init

# Review plan
terraform plan

# Create backend (S3 + DynamoDB)
terraform apply

# Note outputs
terraform output
```

**Outputs**:
- `terraform_state_bucket`: Save this!
- `terraform_locks_table`: Save this!

### Step 2: Configure Production Environment

```bash
cd ../environments/prod

# Edit main.tf - uncomment backend block
vim main.tf

# Update with values from Step 1:
# backend "s3" {
#   bucket         = "mcp-langgraph-terraform-state-us-east-1-ACCOUNT_ID"
#   key            = "environments/prod/terraform.tfstate"
#   region         = "us-east-1"
#   dynamodb_table = "mcp-langgraph-terraform-locks"
#   encrypt        = true
# }
```

### Step 3: Create Variables File

```bash
cat > terraform.tfvars <<EOF
region = "us-east-1"

# VPC
vpc_cidr = "10.0.0.0/16"

# EKS
kubernetes_version = "1.28"
cluster_endpoint_public_access_cidrs = ["YOUR_IP/32"]  # IMPORTANT: Restrict!
general_node_instance_types = ["t3.xlarge"]
enable_compute_nodes = false
enable_spot_nodes = true

# RDS
postgres_instance_class = "db.t3.large"
postgres_allocated_storage = 100

# Redis
redis_node_type = "cache.t3.medium"

# Monitoring (optional)
alarm_sns_topic_arns = []
EOF
```

### Step 4: Deploy Infrastructure

```bash
# Initialize with backend
terraform init

# Review plan (creates ~80 resources)
terraform plan -out=tfplan

# Apply (20-25 minutes)
terraform apply tfplan
```

**What Gets Created**:
- VPC with 6 subnets across 3 AZs
- 3 NAT gateways
- 5 VPC endpoints
- EKS cluster with 3 node groups
- RDS PostgreSQL Multi-AZ
- ElastiCache Redis Cluster (9 nodes)
- ~20 Security groups
- ~10 IAM roles
- Kubernetes namespace and secrets

### Step 5: Configure kubectl

```bash
# Get command from Terraform output
terraform output configure_kubectl

# Run it
aws eks update-kubeconfig --region us-east-1 --name mcp-langgraph-prod-eks

# Verify
kubectl get nodes
kubectl get ns
```

**Expected Output**:
```
NAME                                       STATUS   ROLES    AGE   VERSION
ip-10-0-xxx-xxx.ec2.internal               Ready    <none>   5m    v1.28.x
ip-10-0-yyy-yyy.ec2.internal               Ready    <none>   5m    v1.28.x
ip-10-0-zzz-zzz.ec2.internal               Ready    <none>   5m    v1.28.x
```

---

## Phase 2: GitOps

### Step 1: Deploy ArgoCD

```bash
# Deploy ArgoCD
kubectl apply -k deployments/argocd/base/

# Wait for readiness
kubectl wait --for=condition=available --timeout=300s \
  deployment/argocd-server -n argocd

# Get initial admin password
kubectl -n argocd get secret argocd-initial-admin-secret \
  -o jsonpath="{.data.password}" | base64 -d
```

### Step 2: Access ArgoCD UI

**Option A: Port Forward (Quick)**
```bash
kubectl port-forward svc/argocd-server -n argocd 8080:443

# Open browser: https://localhost:8080
# Username: admin
# Password: (from step 1)
```

**Option B: Ingress (Production)**
```bash
# Update ingress.yaml with your domain
vim deployments/argocd/base/ingress.yaml

# Reapply
kubectl apply -k deployments/argocd/base/

# Access at https://argocd.your-domain.com
```

### Step 3: Configure Slack Notifications (Optional)

```bash
# Create Slack app: https://api.slack.com/apps
# Get bot token

# Update secret
kubectl create secret generic argocd-notifications-secret \
  -n argocd \
  --from-literal=slack-token=xoxb-YOUR-TOKEN \
  --dry-run=client -o yaml | kubectl apply -f -
```

### Step 4: Deploy ArgoCD Project

```bash
kubectl apply -f deployments/argocd/projects/mcp-server-project.yaml
```

### Step 5: Deploy Application

```bash
# Get Terraform outputs
cd terraform/environments/prod

# Extract outputs
IRSA_ROLE=$(terraform output -raw application_irsa_role_arn)
RDS_ENDPOINT=$(terraform output -raw rds_endpoint)
REDIS_ENDPOINT=$(terraform output -raw redis_endpoint)

# Update application manifest
cd ../../../deployments/argocd/applications

# Edit mcp-server-app.yaml and update:
# - serviceAccount.annotations.eks.amazonaws.com/role-arn: $IRSA_ROLE
# - postgresql.externalHost: $RDS_ENDPOINT
# - redis.externalHost: $REDIS_ENDPOINT

# Deploy
kubectl apply -f mcp-server-app.yaml

# Watch sync
kubectl get applications -n argocd
```

---

## Phase 3: Security

### Step 1: Deploy Falco Runtime Security

```bash
# Add Falco Helm repo
helm repo add falcosecurity https://falcosecurity.github.io/charts
helm repo update

# Install Falco
helm install falco falcosecurity/falco \
  --namespace security \
  --create-namespace \
  --values deployments/security/falco/values.yaml

# Verify
kubectl get pods -n security
kubectl logs -n security -l app.kubernetes.io/name=falco
```

### Step 2: Deploy External Secrets Operator

```bash
# Add repo
helm repo add external-secrets https://charts.external-secrets.io
helm repo update

# Get IRSA role ARN
cd terraform/environments/prod
EXTERNAL_SECRETS_ROLE=$(terraform output -raw application_irsa_role_arn)

# Update values
cd ../../../deployments/security/external-secrets
sed -i "s|eks.amazonaws.com/role-arn:.*|eks.amazonaws.com/role-arn: $EXTERNAL_SECRETS_ROLE|" values.yaml

# Install
helm install external-secrets external-secrets/external-secrets \
  --namespace external-secrets-system \
  --create-namespace \
  --values values.yaml

# Deploy secret stores
kubectl apply -f cluster-secret-store.yaml

# Verify
kubectl get secretstores -A
kubectl get externalsecrets -n mcp-server-langgraph
```

### Step 3: Deploy Reloader

```bash
# Add repo
helm repo add stakater https://stakater.github.io/stakater-charts
helm repo update

# Install
helm install reloader stakater/reloader \
  --namespace kube-system \
  --set reloader.watchGlobally=true

# Verify
kubectl get pods -n kube-system -l app=reloader
```

### Step 4: Deploy Kyverno

```bash
# Add repo
helm repo add kyverno https://kyverno.github.io/kyverno/
helm repo update

# Install
helm install kyverno kyverno/kyverno \
  --namespace kyverno \
  --create-namespace \
  --set replicaCount=3

# Wait for readiness
kubectl wait --for=condition=available --timeout=300s \
  deployment/kyverno -n kyverno

# Apply policies
kubectl apply -f deployments/security/kyverno/policies.yaml

# Verify
kubectl get clusterpolicies
```

---

## Phase 4: High Availability

### Step 1: Update Helm Chart for Redis Cluster

```bash
cd deployments/helm/mcp-server-langgraph

# Update values.yaml
cat >> values.yaml <<EOF

# Redis Cluster Configuration (from Terraform)
redis:
  enabled: false
  cluster:
    enabled: true
    nodes:
      - $(terraform output -raw redis_endpoint)
  auth:
    enabled: true
    existingSecret: redis-credentials
    existingSecretPasswordKey: password
EOF

# Commit changes
git add values.yaml
git commit -m "Configure Redis Cluster mode"
git push
```

### Step 2: Deploy Istio Service Mesh

```bash
# Download Istio
curl -L https://istio.io/downloadIstio | sh -
cd istio-*
export PATH=$PWD/bin:$PATH

# Install Istio
istioctl install --set profile=production -y

# Enable sidecar injection for namespace
kubectl label namespace mcp-server-langgraph istio-injection=enabled

# Verify
kubectl get pods -n istio-system
```

### Step 3: Deploy Vertical Pod Autoscaler

```bash
# Clone VPA repo
git clone https://github.com/kubernetes/autoscaler.git
cd autoscaler/vertical-pod-autoscaler

# Deploy
./hack/vpa-up.sh

# Verify
kubectl get pods -n kube-system -l app=vpa

# Create VPA for application
cat <<EOF | kubectl apply -f -
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: mcp-server-vpa
  namespace: mcp-server-langgraph
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: mcp-server-langgraph
  updatePolicy:
    updateMode: "Auto"
EOF
```

### Step 4: Deploy PgBouncer

```bash
# Create PgBouncer deployment
kubectl apply -f - <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: pgbouncer
  namespace: mcp-server-langgraph
spec:
  replicas: 2
  selector:
    matchLabels:
      app: pgbouncer
  template:
    metadata:
      labels:
        app: pgbouncer
    spec:
      containers:
      - name: pgbouncer
        image: edoburu/pgbouncer:1.21.0
        ports:
        - containerPort: 5432
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: postgres-credentials
              key: url
        - name: POOL_MODE
          value: "transaction"
        - name: MAX_CLIENT_CONN
          value: "1000"
        - name: DEFAULT_POOL_SIZE
          value: "25"
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 500m
            memory: 512Mi
---
apiVersion: v1
kind: Service
metadata:
  name: pgbouncer
  namespace: mcp-server-langgraph
spec:
  ports:
  - port: 5432
    targetPort: 5432
  selector:
    app: pgbouncer
EOF
```

---

## Phase 5: Operational Excellence

### Step 1: Deploy Kubecost

```bash
# Add repo
helm repo add kubecost https://kubecost.github.io/cost-analyzer/
helm repo update

# Install
helm install kubecost kubecost/cost-analyzer \
  --namespace kubecost \
  --create-namespace \
  --set kubecostToken="aGVsbUBrdWJlY29zdC5jb20=xm343yadf98" \
  --set prometheus.server.global.external_labels.cluster_id=mcp-langgraph-prod

# Port forward to access UI
kubectl port-forward -n kubecost svc/kubecost-cost-analyzer 9090:9090

# Open http://localhost:9090
```

### Step 2: Deploy Karpenter

```bash
# Export cluster details
export CLUSTER_NAME=mcp-langgraph-prod-eks
export AWS_REGION=us-east-1
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Get IAM role (created by Terraform)
export KARPENTER_IAM_ROLE_ARN=$(terraform output -raw cluster_autoscaler_irsa_role_arn)

# Install Karpenter
helm repo add karpenter https://charts.karpenter.sh
helm repo update

helm install karpenter karpenter/karpenter \
  --namespace karpenter \
  --create-namespace \
  --set serviceAccount.annotations."eks\.amazonaws\.com/role-arn"=$KARPENTER_IAM_ROLE_ARN \
  --set settings.aws.clusterName=$CLUSTER_NAME \
  --set settings.aws.defaultInstanceProfile=KarpenterNodeInstanceProfile-$CLUSTER_NAME

# Create Provisioner
kubectl apply -f - <<EOF
apiVersion: karpenter.sh/v1alpha5
kind:Provisioner
metadata:
  name: default
spec:
  requirements:
    - key: karpenter.sh/capacity-type
      operator: In
      values: ["spot", "on-demand"]
    - key: kubernetes.io/arch
      operator: In
      values: ["amd64"]
  limits:
    resources:
      cpu: 1000
      memory: 1000Gi
  providerRef:
    name: default
  ttlSecondsAfterEmpty: 30
EOF
```

### Step 3: Deploy Chaos Mesh

```bash
# Add repo
helm repo add chaos-mesh https://charts.chaos-mesh.org
helm repo update

# Install
helm install chaos-mesh chaos-mesh/chaos-mesh \
  --namespace chaos-mesh \
  --create-namespace \
  --set chaosDaemon.runtime=containerd \
  --set chaosDaemon.socketPath=/run/containerd/containerd.sock

# Verify
kubectl get pods -n chaos-mesh

# Access dashboard
kubectl port-forward -n chaos-mesh svc/chaos-dashboard 2333:2333
# Open http://localhost:2333
```

### Step 4: Automated DR Testing

```bash
# Install Velero
wget https://github.com/vmware-tanzu/velero/releases/download/v1.12.0/velero-v1.12.0-linux-amd64.tar.gz
tar -xvf velero-v1.12.0-linux-amd64.tar.gz
sudo mv velero-v1.12.0-linux-amd64/velero /usr/local/bin/

# Create S3 bucket for backups
aws s3 mb s3://mcp-langgraph-velero-backups-$AWS_REGION

# Install Velero
velero install \
  --provider aws \
  --plugins velero/velero-plugin-for-aws:v1.8.0 \
  --bucket mcp-langgraph-velero-backups-$AWS_REGION \
  --backup-location-config region=$AWS_REGION \
  --snapshot-location-config region=$AWS_REGION \
  --use-node-agent

# Create backup schedule
velero schedule create daily-backup \
  --schedule="0 2 * * *" \
  --include-namespaces mcp-server-langgraph \
  --ttl 720h0m0s

# Test backup
velero backup create test-backup --include-namespaces mcp-server-langgraph

# Verify
velero backup get
```

---

## Verification

### Infrastructure Health

```bash
# Check all nodes
kubectl get nodes

# Check all pods
kubectl get pods -A

# Check Terraform resources
cd terraform/environments/prod
terraform show | grep "# aws"
```

### Application Health

```bash
# Check application pods
kubectl get pods -n mcp-server-langgraph

# Check services
kubectl get svc -n mcp-server-langgraph

# Check ingress
kubectl get ingress -n mcp-server-langgraph

# Check logs
kubectl logs -n mcp-server-langgraph -l app=mcp-server-langgraph --tail=100
```

### Security Verification

```bash
# Check Falco alerts
kubectl logs -n security -l app.kubernetes.io/name=falco | grep -i "critical\\|warning"

# Check Kyverno policies
kubectl get clusterpolicies

# Check external secrets
kubectl get externalsecrets -A

# Check pod security
kubectl get ns mcp-server-langgraph -o yaml | grep pod-security
```

### Cost Check

```bash
# Access Kubecost
kubectl port-forward -n kubecost svc/kubecost-cost-analyzer 9090:9090

# Open http://localhost:9090
```

---

## Troubleshooting

### Pods Not Starting

```bash
# Describe pod
kubectl describe pod <pod-name> -n mcp-server-langgraph

# Check events
kubectl get events -n mcp-server-langgraph --sort-by='.lastTimestamp'

# Check logs
kubectl logs <pod-name> -n mcp-server-langgraph
```

### ArgoCD Sync Issues

```bash
# Check application status
kubectl get applications -n argocd

# View sync status
kubectl describe application mcp-server-langgraph-prod -n argocd

# Force sync
kubectl patch application mcp-server-langgraph-prod -n argocd \
  --type merge -p '{"operation":{"initiatedBy":{"username":"admin"},"sync":{"syncStrategy":{"hook":{}}}}}'
```

### Terraform State Issues

```bash
# List state
terraform state list

# Show resource
terraform state show <resource>

# Refresh state
terraform refresh

# Force unlock (if locked)
terraform force-unlock <LOCK_ID>
```

### Database Connection Issues

```bash
# Test from pod
kubectl run -it --rm debug --image=postgres:16 --restart=Never -- \
  psql -h <RDS_ENDPOINT> -U postgres -d mcp_langgraph

# Check security groups
aws ec2 describe-security-groups --group-ids <SG_ID>
```

### Redis Connection Issues

```bash
# Test from pod
kubectl run -it --rm debug --image=redis:7 --restart=Never -- \
  redis-cli -h <REDIS_ENDPOINT> -a <AUTH_TOKEN> --tls ping

# Check cluster info
kubectl run -it --rm debug --image=redis:7 --restart=Never -- \
  redis-cli -h <REDIS_ENDPOINT> -a <AUTH_TOKEN> --tls cluster info
```

---

## Next Steps

1. **Set up monitoring dashboards** in Grafana
2. **Configure alerting** via SNS/Slack
3. **Run chaos experiments** with Chaos Mesh
4. **Review costs** in Kubecost
5. **Optimize resources** based on VPA recommendations
6. **Schedule DR drills** monthly
7. **Review security alerts** from Falco
8. **Update policies** in Kyverno as needed

---

## Support

For issues:
1. Check logs: `kubectl logs ...`
2. Check events: `kubectl get events ...`
3. Review documentation in each deployment directory
4. Check Terraform outputs: `terraform output`

---

**Deployment Time Estimate**:
- Phase 1 (Infrastructure): 30 minutes
- Phase 2 (GitOps): 15 minutes
- Phase 3 (Security): 30 minutes
- Phase 4 (HA): 30 minutes
- Phase 5 (Ops): 45 minutes
- **Total**: ~2.5 hours for complete deployment
