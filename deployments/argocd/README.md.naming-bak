# ArgoCD GitOps Deployment

ArgoCD-based GitOps continuous deployment for MCP Server LangGraph.

## Overview

This directory contains ArgoCD configurations for declarative, GitOps-based deployment:

- **Automated Sync**: Changes in Git automatically deploy to cluster
- **Self-Healing**: Manual kubectl changes are automatically reverted
- **Multi-Environment**: Separate applications for dev/staging/prod
- **RBAC**: Role-based access control for team members
- **Notifications**: Slack notifications for deployment events

## Directory Structure

```
argocd/
├── base/
│   ├── namespace.yaml           # ArgoCD namespace
│   ├── argocd-install.yaml      # ConfigMaps and settings
│   ├── ingress.yaml             # ArgoCD UI ingress
│   └── kustomization.yaml       # Kustomize configuration
├── projects/
│   └── mcp-server-project.yaml  # ArgoCD Project definition
├── applications/
│   └── mcp-server-app.yaml      # Main application
└── README.md                     # This file
```

## Installation

### Prerequisites

- EKS cluster running (from Terraform)
- kubectl configured
- Helm 3.x installed

### Step 1: Deploy ArgoCD

```bash
# Apply ArgoCD installation
kubectl apply -k deployments/argocd/base/

# Wait for ArgoCD to be ready
kubectl wait --for=condition=available --timeout=300s \
  deployment/argocd-server -n argocd

# Get initial admin password
kubectl -n argocd get secret argocd-initial-admin-secret \
  -o jsonpath="{.data.password}" | base64 -d
```

### Step 2: Access ArgoCD UI

**Option A: Port Forward (Development)**
```bash
kubectl port-forward svc/argocd-server -n argocd 8080:443

# Access at https://localhost:8080
# Username: admin
# Password: (from step 1)
```

**Option B: Ingress (Production)**
```bash
# Update ingress.yaml with your domain
# Then access at https://argocd.example.com
```

### Step 3: Configure Slack Notifications (Optional)

```bash
# Create Slack app and get token
# https://api.slack.com/apps

# Update secret
kubectl create secret generic argocd-notifications-secret \
  -n argocd \
  --from-literal=slack-token=xoxb-your-token \
  --dry-run=client -o yaml | kubectl apply -f -
```

### Step 4: Deploy ArgoCD Project

```bash
kubectl apply -f deployments/argocd/projects/mcp-server-project.yaml
```

### Step 5: Deploy Application

```bash
# Update mcp-server-app.yaml with Terraform outputs:
# - IRSA role ARN
# - RDS endpoint
# - Redis endpoint

kubectl apply -f deployments/argocd/applications/mcp-server-app.yaml

# Watch deployment
kubectl get applications -n argocd
argocd app get mcp-server-langgraph-prod
```

## ArgoCD CLI

### Installation

```bash
# macOS
brew install argocd

# Linux
curl -sSL -o argocd https://github.com/argoproj/argo-cd/releases/latest/download/argocd-linux-amd64
chmod +x argocd
sudo mv argocd /usr/local/bin/
```

### Login

```bash
# Get initial password
ARGOCD_PASSWORD=$(kubectl -n argocd get secret argocd-initial-admin-secret \
  -o jsonpath="{.data.password}" | base64 -d)

# Login
argocd login localhost:8080 --username admin --password $ARGOCD_PASSWORD --insecure
```

### Common Commands

```bash
# List applications
argocd app list

# Get application details
argocd app get mcp-server-langgraph-prod

# Sync application
argocd app sync mcp-server-langgraph-prod

# View diff
argocd app diff mcp-server-langgraph-prod

# View logs
argocd app logs mcp-server-langgraph-prod

# Delete application
argocd app delete mcp-server-langgraph-prod
```

## Application Configuration

### Automated Sync

The application is configured for automated sync:

```yaml
syncPolicy:
  automated:
    prune: true        # Delete resources not in Git
    selfHeal: true     # Revert manual changes
```

### Sync Waves

Use annotations to control deployment order:

```yaml
metadata:
  annotations:
    argocd.argoproj.io/sync-wave: "1"  # Deploy in wave 1
```

Lower numbers deploy first:
- Wave 0: Namespaces, CRDs
- Wave 1: ConfigMaps, Secrets
- Wave 2: StatefulSets, Deployments
- Wave 3: Services, Ingress

### Health Checks

ArgoCD monitors these resources:
- Deployments (all replicas ready)
- StatefulSets (all replicas ready)
- DaemonSets (all nodes running)
- Services (endpoints available)

Custom health checks in `argocd-cm`:

```yaml
resource.customizations: |
  apps/Deployment:
    health.lua: |
      # Custom Lua health check
```

## Multi-Environment Setup

### Development Environment

```yaml
# applications/mcp-server-dev.yaml
spec:
  source:
    targetRevision: develop  # develop branch
  destination:
    namespace: mcp-server-langgraph-dev
  syncPolicy:
    automated:
      prune: true
      selfHeal: true  # Auto-sync for dev
```

### Staging Environment

```yaml
# applications/mcp-server-staging.yaml
spec:
  source:
    targetRevision: release  # release branch
  destination:
    namespace: mcp-server-langgraph-staging
  syncPolicy:
    automated:
      prune: true
      selfHeal: false  # Manual sync for staging
```

### Production Environment

```yaml
# applications/mcp-server-prod.yaml
spec:
  source:
    targetRevision: main  # main branch (tags only)
  destination:
    namespace: mcp-server-langgraph
  syncPolicy:
    automated:
      prune: true
      selfHeal: false  # Manual sync for production
    syncOptions:
      - CreateNamespace=false  # Pre-created by Terraform
```

## RBAC Configuration

### Roles

1. **Admin**: Full access to all resources
2. **Developer**: Read/sync applications
3. **CI/CD**: Sync and update applications

### Groups

Configure in `argocd-rbac-cm`:

```yaml
policy.csv: |
  # Developers can sync apps
  p, role:developer, applications, sync, */*, allow
  g, developers@example.com, role:developer

  # Admins have full access
  g, admins@example.com, role:admin
```

## Notifications

### Triggers

- `on-deployed`: Application synced successfully
- `on-health-degraded`: Application unhealthy
- `on-sync-failed`: Sync failed

### Slack Integration

1. Create Slack app: https://api.slack.com/apps
2. Add bot token to secret
3. Invite bot to channel (#argocd-notifications)
4. Subscribe applications:

```yaml
annotations:
  notifications.argoproj.io/subscribe.on-deployed.slack: argocd-notifications
```

## Troubleshooting

### Application OutOfSync

```bash
# View diff
argocd app diff mcp-server-langgraph-prod

# Sync manually
argocd app sync mcp-server-langgraph-prod

# Hard refresh
argocd app sync mcp-server-langgraph-prod --force
```

### Health Check Failing

```bash
# View resource health
kubectl get applications -n argocd mcp-server-langgraph-prod -o yaml

# Check pods
kubectl get pods -n mcp-server-langgraph

# View logs
kubectl logs -n mcp-server-langgraph deployment/mcp-server-langgraph
```

### Sync Failing

```bash
# View sync status
argocd app get mcp-server-langgraph-prod

# View operation logs
argocd app logs mcp-server-langgraph-prod --kind sync

# Retry sync
argocd app sync mcp-server-langgraph-prod --retry-limit 5
```

### Webhook Not Triggering

```bash
# Check webhook secret
kubectl get secret -n argocd argocd-secret -o yaml

# GitHub webhook URL
https://argocd.example.com/api/webhook

# Webhook secret (from argocd-secret)
kubectl get secret -n argocd argocd-secret \
  -o jsonpath='{.data.webhook\.github\.secret}' | base64 -d
```

## Best Practices

### 1. Use Projects for Isolation

Group related applications in projects:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AppProject
metadata:
  name: team-a
spec:
  sourceRepos:
    - 'https://github.com/org/team-a-*'
  destinations:
    - namespace: 'team-a-*'
      server: '*'
```

### 2. Implement Sync Waves

Control deployment order:

```yaml
# Deploy database first
apiVersion: v1
kind: StatefulSet
metadata:
  annotations:
    argocd.argoproj.io/sync-wave: "1"

# Then application
apiVersion: apps/v1
kind: Deployment
metadata:
  annotations:
    argocd.argoproj.io/sync-wave: "2"
```

### 3. Use Sync Windows

Restrict production syncs:

```yaml
syncWindows:
  - kind: allow
    schedule: '0 2 * * *'  # 2 AM daily
    duration: 2h
    applications:
      - '*-prod'
```

### 4. Enable Notifications

Stay informed of deployment status:

```yaml
annotations:
  notifications.argoproj.io/subscribe.on-deployed.slack: team-channel
  notifications.argoproj.io/subscribe.on-sync-failed.slack: alerts-channel
```

### 5. Implement Progressive Delivery

Use Argo Rollouts for canary/blue-green:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: mcp-server-langgraph
spec:
  strategy:
    canary:
      steps:
        - setWeight: 20
        - pause: {duration: 5m}
        - setWeight: 50
        - pause: {duration: 5m}
```

## Security

### 1. Disable Admin User

Use SSO instead:

```yaml
# argocd-cm
data:
  admin.enabled: "false"
```

### 2. Use RBAC

Restrict access by role:

```yaml
policy.csv: |
  p, role:readonly, applications, get, */*, allow
  g, everyone, role:readonly
```

### 3. Enable Audit Logs

Track all changes:

```yaml
# argocd-cm
data:
  audit.log.enabled: "true"
```

### 4. Use Sealed Secrets

Don't commit secrets to Git:

```bash
# Install sealed-secrets controller
kubectl apply -f https://github.com/bitnami-labs/sealed-secrets/releases/download/v0.24.0/controller.yaml

# Create sealed secret
kubeseal --format yaml < secret.yaml > sealed-secret.yaml
```

## Monitoring

### Metrics

ArgoCD exports Prometheus metrics:

```
argocd_app_info
argocd_app_sync_total
argocd_app_health_status
```

### Grafana Dashboard

Import dashboard ID: 14584

https://grafana.com/grafana/dashboards/14584

## References

- [ArgoCD Documentation](https://argo-cd.readthedocs.io/)
- [ArgoCD Best Practices](https://argo-cd.readthedocs.io/en/stable/user-guide/best_practices/)
- [GitOps Principles](https://opengitops.dev/)
