# AWS EKS Deployment - Quick Reference Card

## 🚀 One-Command Deployment

```bash
./scripts/deploy-all-phases.sh
```

---

## 📋 Manual Deployment Steps

### 1. Infrastructure (25 min)

```bash
cd terraform/backend-setup && terraform apply
cd ../environments/prod && terraform apply
aws eks update-kubeconfig --region us-east-1 --name mcp-langgraph-prod-eks
```

### 2. GitOps (10 min)

```bash
kubectl apply -k deployments/argocd/base/
kubectl apply -f deployments/argocd/projects/
kubectl apply -f deployments/argocd/applications/
```

### 3. Security (30 min)

```bash
helm install falco falcosecurity/falco -n security --create-namespace
helm install external-secrets external-secrets/external-secrets -n external-secrets-system --create-namespace
helm install reloader stakater/reloader -n kube-system
helm install kyverno kyverno/kyverno -n kyverno --create-namespace
kubectl apply -f deployments/security/kyverno/policies.yaml
```

### 4. High Availability (30 min)

```bash
istioctl install --set profile=production
kubectl label namespace mcp-server-langgraph istio-injection=enabled
git clone https://github.com/kubernetes/autoscaler && cd autoscaler/vertical-pod-autoscaler && ./hack/vpa-up.sh
```

### 5. Operations (30 min)

```bash
helm install kubecost kubecost/cost-analyzer -n kubecost --create-namespace
helm install chaos-mesh chaos-mesh/chaos-mesh -n chaos-mesh --create-namespace
velero install --provider aws --bucket mcp-langgraph-backups
```

---

## 🔧 Essential Commands

### kubectl

```bash
# Get all resources
kubectl get all -n mcp-server-langgraph

# View logs
kubectl logs -n mcp-server-langgraph -l app=mcp-server-langgraph --tail=100

# Describe pod
kubectl describe pod <pod-name> -n mcp-server-langgraph

# Execute into pod
kubectl exec -it <pod-name> -n mcp-server-langgraph -- /bin/bash
```

### Terraform

```bash
# Plan changes
terraform plan

# Apply changes
terraform apply

# Show outputs
terraform output

# Destroy (careful!)
terraform destroy
```

### ArgoCD

```bash
# Get initial password
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d

# Port forward
kubectl port-forward svc/argocd-server -n argocd 8080:443

# CLI sync
argocd app sync mcp-server-langgraph-prod

# View status
argocd app get mcp-server-langgraph-prod
```

### Helm

```bash
# List releases
helm list -A

# Get values
helm get values <release> -n <namespace>

# Upgrade release
helm upgrade <release> <chart> -n <namespace>

# Rollback
helm rollback <release> -n <namespace>
```

---

## 🔍 Monitoring Access

```bash
# ArgoCD UI
kubectl port-forward svc/argocd-server -n argocd 8080:443
# https://localhost:8080

# Kubecost
kubectl port-forward -n kubecost svc/kubecost-cost-analyzer 9090:9090
# http://localhost:9090

# Chaos Mesh
kubectl port-forward -n chaos-mesh svc/chaos-dashboard 2333:2333
# http://localhost:2333

# Grafana (if installed separately)
kubectl port-forward -n monitoring svc/grafana 3000:80
# http://localhost:3000
```

---

## 💰 Cost Quick Reference

**Production**: ~$803/month
- VPC: $134
- EKS: $323
- RDS: $157
- Redis: $172
- Monitoring: $17

**Development**: ~$250/month (69% savings)

---

## 🔒 Security Quick Check

```bash
# Check Pod Security Standards
kubectl get ns mcp-server-langgraph -o yaml | grep pod-security

# View Falco alerts
kubectl logs -n security -l app.kubernetes.io/name=falco | grep WARNING

# Check Kyverno policies
kubectl get clusterpolicies

# Check external secrets
kubectl get externalsecrets -A

# View security scans in GitHub
# Navigate to: Security > Code scanning alerts
```

---

## 📊 Health Checks

```bash
# Nodes
kubectl get nodes

# Pods
kubectl get pods -A | grep -v "Running\\|Completed"

# Services
kubectl get svc -A

# Ingress
kubectl get ingress -A

# ArgoCD apps
kubectl get applications -n argocd

# Check all health
kubectl get --raw /healthz && echo " - Cluster healthy"
```

---

## 🆘 Quick Troubleshooting

### Pods CrashLooping
```bash
kubectl describe pod <pod> -n <namespace>
kubectl logs <pod> -n <namespace> --previous
```

### ArgoCD Not Syncing
```bash
kubectl describe application <app> -n argocd
argocd app sync <app> --force
```

### Database Connection Failed
```bash
# Test from cluster
kubectl run -it --rm debug --image=postgres:16 -- psql -h <host> -U postgres
```

### High Costs
```bash
# Check Kubecost
kubectl port-forward -n kubecost svc/kubecost-cost-analyzer 9090:9090
# Review recommendations
```

---

## 📞 Support Resources

- **Deployment Guide**: `deployments/DEPLOYMENT_GUIDE.md`
- **Terraform Docs**: `terraform/README.md`
- **ArgoCD Guide**: `deployments/argocd/README.md`
- **Complete Report**: `AWS_EKS_IMPLEMENTATION_COMPLETE.md`

---

## 🎯 Success Indicators

✅ All nodes Ready
✅ All pods Running
✅ ArgoCD syncing applications
✅ Falco monitoring without critical alerts
✅ Kyverno policies enforcing
✅ Costs within budget ($803/month)
✅ Backups running daily
✅ Monitoring dashboards showing data

---

**Implementation Status**: ✅ COMPLETE
**Production Ready**: ✅ YES
**Deploy Now**: `./scripts/deploy-all-phases.sh`
