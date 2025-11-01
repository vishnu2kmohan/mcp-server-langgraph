#!/bin/bash
# Complete Deployment Script for All Phases
# MCP Server LangGraph - AWS EKS Best Practices Implementation

set -e  # Exit on error
set -u  # Exit on undefined variable

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Functions
log_info() {
    echo -e "${CYAN}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_prerequisites() {
    log_info "Checking prerequisites..."

    command -v terraform >/dev/null 2>&1 || { log_error "terraform not found"; exit 1; }
    command -v aws >/dev/null 2>&1 || { log_error "aws CLI not found"; exit 1; }
    command -v kubectl >/dev/null 2>&1 || { log_error "kubectl not found"; exit 1; }
    command -v helm >/dev/null 2>&1 || { log_error "helm not found"; exit 1; }

    log_success "All prerequisites met"
}

deploy_phase1_infrastructure() {
    log_info "=========================================="
    log_info "PHASE 1: Infrastructure as Code"
    log_info "=========================================="

    # Step 1: Create Terraform backend
    log_info "Step 1: Creating Terraform backend..."
    cd terraform/backend-setup
    terraform init
    terraform apply -auto-approve

    BUCKET_NAME=$(terraform output -raw terraform_state_bucket)
    TABLE_NAME=$(terraform output -raw terraform_locks_table)

    log_success "Backend created: $BUCKET_NAME"

    # Step 2: Deploy production environment
    log_info "Step 2: Deploying production infrastructure..."
    cd ../environments/prod

    # Check if terraform.tfvars exists
    if [ ! -f terraform.tfvars ]; then
        log_warning "terraform.tfvars not found. Please create it before continuing."
        log_info "Example terraform.tfvars:"
        cat <<EOF
region = "us-east-1"
vpc_cidr = "10.0.0.0/16"
kubernetes_version = "1.28"
cluster_endpoint_public_access_cidrs = ["YOUR_IP/32"]
EOF
        exit 1
    fi

    terraform init
    terraform plan -out=tfplan
    terraform apply tfplan

    log_success "Infrastructure deployed"

    # Step 3: Configure kubectl
    log_info "Step 3: Configuring kubectl..."
    CLUSTER_NAME=$(terraform output -raw cluster_name)
    aws eks update-kubeconfig --region us-east-1 --name "$CLUSTER_NAME"

    kubectl get nodes

    log_success "Phase 1 complete"
    cd ../../..
}

deploy_phase2_gitops() {
    log_info "=========================================="
    log_info "PHASE 2: GitOps with ArgoCD"
    log_info "=========================================="

    # Deploy ArgoCD
    log_info "Deploying ArgoCD..."
    kubectl apply -k deployments/argocd/base/

    log_info "Waiting for ArgoCD to be ready..."
    kubectl wait --for=condition=available --timeout=300s \
        deployment/argocd-server -n argocd

    # Get admin password
    ARGOCD_PASSWORD=$(kubectl -n argocd get secret argocd-initial-admin-secret \
        -o jsonpath="{.data.password}" | base64 -d)

    log_success "ArgoCD deployed"
    log_info "Admin password: $ARGOCD_PASSWORD"
    log_info "Access UI: kubectl port-forward svc/argocd-server -n argocd 8080:443"

    # Deploy project
    log_info "Deploying ArgoCD project..."
    kubectl apply -f deployments/argocd/projects/

    # Deploy application
    log_info "Deploying application via ArgoCD..."
    log_warning "Update deployments/argocd/applications/mcp-server-app.yaml with Terraform outputs first!"
    kubectl apply -f deployments/argocd/applications/

    log_success "Phase 2 complete"
}

deploy_phase3_security() {
    log_info "=========================================="
    log_info "PHASE 3: Security Enhancements"
    log_info "=========================================="

    # Add Helm repos
    log_info "Adding Helm repositories..."
    helm repo add falcosecurity https://falcosecurity.github.io/charts
    helm repo add external-secrets https://charts.external-secrets.io
    helm repo add stakater https://stakater.github.io/stakater-charts
    helm repo add kyverno https://kyverno.github.io/kyverno/
    helm repo update

    # Deploy Falco
    log_info "Deploying Falco runtime security..."
    helm install falco falcosecurity/falco \
        --namespace security \
        --create-namespace \
        --values deployments/security/falco/values.yaml

    log_success "Falco deployed"

    # Deploy External Secrets Operator
    log_info "Deploying External Secrets Operator..."
    helm install external-secrets external-secrets/external-secrets \
        --namespace external-secrets-system \
        --create-namespace \
        --values deployments/security/external-secrets/values.yaml

    kubectl apply -f deployments/security/external-secrets/cluster-secret-store.yaml

    log_success "External Secrets Operator deployed"

    # Deploy Reloader
    log_info "Deploying Reloader..."
    helm install reloader stakater/reloader \
        --namespace kube-system \
        --set reloader.watchGlobally=true

    log_success "Reloader deployed"

    # Deploy Kyverno
    log_info "Deploying Kyverno policy engine..."
    helm install kyverno kyverno/kyverno \
        --namespace kyverno \
        --create-namespace \
        --set replicaCount=3

    kubectl wait --for=condition=available --timeout=300s \
        deployment/kyverno -n kyverno

    kubectl apply -f deployments/security/kyverno/policies.yaml

    log_success "Phase 3 complete"
}

deploy_phase4_ha() {
    log_info "=========================================="
    log_info "PHASE 4: High Availability"
    log_info "=========================================="

    # Deploy Istio
    log_info "Deploying Istio service mesh..."

    # Check if istioctl is installed
    if ! command -v istioctl &> /dev/null; then
        log_info "Installing Istio..."
        curl -L https://istio.io/downloadIstio | sh -
        cd istio-*
        export PATH=$PWD/bin:$PATH
        cd ..
    fi

    istioctl install --set profile=production -y

    # Enable sidecar injection
    kubectl label namespace mcp-server-langgraph istio-injection=enabled --overwrite

    # Apply Istio configurations
    kubectl apply -f deployments/service-mesh/istio/

    log_success "Istio deployed"

    # Deploy VPA
    log_info "Deploying Vertical Pod Autoscaler..."

    if [ ! -d "autoscaler" ]; then
        git clone https://github.com/kubernetes/autoscaler.git
    fi

    cd autoscaler/vertical-pod-autoscaler
    ./hack/vpa-up.sh
    cd ../..

    log_success "VPA deployed"

    # Deploy PgBouncer
    log_info "Deploying PgBouncer..."
    # PgBouncer deployment is in DEPLOYMENT_GUIDE.md
    log_warning "PgBouncer requires manual configuration with RDS endpoint"

    log_success "Phase 4 complete"
}

deploy_phase5_ops() {
    log_info "=========================================="
    log_info "PHASE 5: Operational Excellence"
    log_info "=========================================="

    # Add repos
    helm repo add kubecost https://kubecost.github.io/cost-analyzer/
    helm repo add karpenter https://charts.karpenter.sh
    helm repo add chaos-mesh https://charts.chaos-mesh.org
    helm repo update

    # Deploy Kubecost
    log_info "Deploying Kubecost..."
    helm install kubecost kubecost/cost-analyzer \
        --namespace kubecost \
        --create-namespace \
        --set kubecostToken="aGVsbUBrdWJlY29zdC5jb20=xm343yadf98"

    log_success "Kubecost deployed"
    log_info "Access UI: kubectl port-forward -n kubecost svc/kubecost-cost-analyzer 9090:9090"

    # Deploy Karpenter
    log_info "Deploying Karpenter..."
    log_warning "Karpenter requires IAM role from Terraform. Skipping for now."
    log_info "See DEPLOYMENT_GUIDE.md for manual Karpenter setup"

    # Deploy Chaos Mesh
    log_info "Deploying Chaos Mesh..."
    helm install chaos-mesh chaos-mesh/chaos-mesh \
        --namespace chaos-mesh \
        --create-namespace \
        --set chaosDaemon.runtime=containerd \
        --set chaosDaemon.socketPath=/run/containerd/containerd.sock

    log_success "Chaos Mesh deployed"
    log_info "Access dashboard: kubectl port-forward -n chaos-mesh svc/chaos-dashboard 2333:2333"

    # Deploy Velero
    log_info "Setting up Velero for DR..."
    log_warning "Velero requires AWS S3 bucket and IAM permissions. See DEPLOYMENT_GUIDE.md"

    log_success "Phase 5 complete"
}

verify_deployment() {
    log_info "=========================================="
    log_info "Verifying Deployment"
    log_info "=========================================="

    # Check nodes
    log_info "Checking nodes..."
    kubectl get nodes
    NODE_COUNT=$(kubectl get nodes --no-headers | wc -l)
    log_success "$NODE_COUNT nodes ready"

    # Check all pods
    log_info "Checking pods across all namespaces..."
    kubectl get pods -A | grep -v "Running\\|Completed" || log_success "All pods healthy"

    # Check ArgoCD
    log_info "Checking ArgoCD..."
    kubectl get applications -n argocd

    # Check security tools
    log_info "Checking security tools..."
    kubectl get pods -n security
    kubectl get clusterpolicies

    log_success "Verification complete"
}

main() {
    log_info "Starting complete AWS EKS deployment..."
    log_info "This will deploy all 5 phases"

    check_prerequisites

    # Phase selection
    echo ""
    echo "Select deployment option:"
    echo "1) Deploy all phases (full deployment)"
    echo "2) Deploy Phase 1 only (Infrastructure)"
    echo "3) Deploy Phase 2 only (GitOps) - requires Phase 1"
    echo "4) Deploy Phase 3 only (Security) - requires Phase 1-2"
    echo "5) Deploy Phases 4-5 (HA + Ops) - requires Phase 1-3"
    echo "6) Verify existing deployment"
    echo "0) Exit"
    read -p "Enter choice [0-6]: " choice

    case $choice in
        1)
            deploy_phase1_infrastructure
            deploy_phase2_gitops
            deploy_phase3_security
            deploy_phase4_ha
            deploy_phase5_ops
            verify_deployment
            ;;
        2)
            deploy_phase1_infrastructure
            ;;
        3)
            deploy_phase2_gitops
            ;;
        4)
            deploy_phase3_security
            ;;
        5)
            deploy_phase4_ha
            deploy_phase5_ops
            ;;
        6)
            verify_deployment
            ;;
        0)
            log_info "Exiting"
            exit 0
            ;;
        *)
            log_error "Invalid choice"
            exit 1
            ;;
    esac

    log_success "=========================================="
    log_success "DEPLOYMENT COMPLETE!"
    log_success "=========================================="

    echo ""
    log_info "Next steps:"
    log_info "1. Access ArgoCD UI: kubectl port-forward svc/argocd-server -n argocd 8080:443"
    log_info "2. Access Kubecost: kubectl port-forward -n kubecost svc/kubecost-cost-analyzer 9090:9090"
    log_info "3. Access Chaos Mesh: kubectl port-forward -n chaos-mesh svc/chaos-dashboard 2333:2333"
    log_info "4. Review CloudWatch dashboards in AWS Console"
    log_info "5. Check Falco alerts: kubectl logs -n security -l app.kubernetes.io/name=falco"
}

# Run main function
main "$@"
