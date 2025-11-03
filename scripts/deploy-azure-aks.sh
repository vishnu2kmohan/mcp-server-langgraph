#!/bin/bash
# Deployment script for Azure AKS
# Implements all 11 Kubernetes best practices for Azure

set -e  # Exit on error
set -u  # Exit on undefined variable

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
RESOURCE_GROUP="${AZURE_RESOURCE_GROUP:-mcp-production-rg}"
CLUSTER_NAME="${AKS_CLUSTER_NAME:-mcp-production}"
LOCATION="${AZURE_LOCATION:-eastus}"
ENVIRONMENT="${AZURE_ENVIRONMENT:-azure}"  # Terraform automation not yet available
NAMESPACE="mcp-server-langgraph"

# Functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_prerequisites() {
    log_info "Checking prerequisites..."

    # Check Azure CLI
    if ! command -v az &> /dev/null; then
        log_error "Azure CLI not found. Please install: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli"
        exit 1
    fi

    # Check kubectl
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl not found. Please install: https://kubernetes.io/docs/tasks/tools/"
        exit 1
    fi

    # Check helm
    if ! command -v helm &> /dev/null; then
        log_error "helm not found. Please install: https://helm.sh/docs/intro/install/"
        exit 1
    fi

    # Check terraform
    if ! command -v terraform &> /dev/null; then
        log_error "terraform not found. Please install: https://www.terraform.io/downloads"
        exit 1
    fi

    # Check Azure login
    if ! az account show &> /dev/null; then
        log_error "Not logged into Azure. Run: az login"
        exit 1
    fi

    log_info "✓ All prerequisites met"
}

deploy_infrastructure() {
    log_error "=========================================="
    log_error "TERRAFORM AUTOMATION NOT YET AVAILABLE"
    log_error "=========================================="
    echo ""
    log_warn "AKS Terraform automation is currently under development."
    log_warn "The terraform/environments/azure directory does not exist yet."
    echo ""
    log_info "Please use the MANUAL deployment process instead:"
    log_info "1. See documentation: docs/deployment/kubernetes/aks.mdx"
    log_info "2. Follow the manual runbook using Azure CLI"
    log_info "3. Or help contribute AKS Terraform modules!"
    echo ""
    log_info "What's missing:"
    log_info "  - terraform/modules/aks/ (AKS cluster module)"
    log_info "  - terraform/modules/azure-vnet/ (Azure networking)"
    log_info "  - terraform/modules/azure-cache/ (Azure Cache for Redis)"
    log_info "  - terraform/environments/azure-prod/"
    echo ""
    exit 1
}

configure_kubectl() {
    log_info "Configuring kubectl for AKS cluster..."

    az aks get-credentials \
        --resource-group "$RESOURCE_GROUP" \
        --name "$CLUSTER_NAME" \
        --overwrite-existing

    log_info "✓ kubectl configured"
}

deploy_velero() {
    log_info "Deploying Velero for backup/DR..."

    # Get storage account details
    STORAGE_ACCOUNT=$(terraform -chdir=terraform/environments/azure output -raw storage_account_name 2>/dev/null || echo "")
    STORAGE_CONTAINER="${CLUSTER_NAME}-backups"

    if [ -z "$STORAGE_ACCOUNT" ]; then
        log_warn "Storage account not found in Terraform outputs. Creating..."
        STORAGE_ACCOUNT="${CLUSTER_NAME}backups${RANDOM}"
        az storage account create \
            --name "$STORAGE_ACCOUNT" \
            --resource-group "$RESOURCE_GROUP" \
            --location "$LOCATION" \
            --sku Standard_LRS
    fi

    # Create container
    az storage container create \
        --name "$STORAGE_CONTAINER" \
        --account-name "$STORAGE_ACCOUNT" || true

    # Get storage account key
    STORAGE_KEY=$(az storage account keys list \
        --resource-group "$RESOURCE_GROUP" \
        --account-name "$STORAGE_ACCOUNT" \
        --query '[0].value' -o tsv)

    # Create secret for Velero
    kubectl create secret generic cloud-credentials \
        --namespace velero \
        --from-literal=AZURE_STORAGE_ACCOUNT_ACCESS_KEY="$STORAGE_KEY" \
        --dry-run=client -o yaml | kubectl apply -f -

    # Install Velero
    helm repo add vmware-tanzu https://vmware-tanzu.github.io/helm-charts
    helm repo update

    helm upgrade --install velero vmware-tanzu/velero \
        --namespace velero \
        --create-namespace \
        --values deployments/backup/velero-values-azure.yaml \
        --set configuration.backupStorageLocation[0].bucket="$STORAGE_CONTAINER" \
        --set configuration.backupStorageLocation[0].config.resourceGroup="$RESOURCE_GROUP" \
        --set configuration.backupStorageLocation[0].config.storageAccount="$STORAGE_ACCOUNT"

    # Apply backup schedules
    kubectl apply -f deployments/backup/backup-schedule.yaml

    log_info "✓ Velero deployed"
}

deploy_namespace_and_security() {
    log_info "Deploying namespace with security policies..."

    # Create namespace with Istio injection and PSS
    kubectl apply -f deployments/base/namespace.yaml

    # Apply network policies
    kubectl apply -f deployments/base/postgres-networkpolicy.yaml
    kubectl apply -f deployments/base/redis-networkpolicy.yaml
    kubectl apply -f deployments/base/keycloak-networkpolicy.yaml
    kubectl apply -f deployments/base/openfga-networkpolicy.yaml

    # Apply resource quotas
    kubectl apply -f deployments/base/resourcequota.yaml
    kubectl apply -f deployments/base/limitrange.yaml

    log_info "✓ Namespace and security policies deployed"
}

deploy_istio() {
    log_info "Deploying Istio service mesh..."

    # Check if Istio is already installed
    if ! kubectl get namespace istio-system &> /dev/null; then
        log_warn "Istio not found. Installing Istio..."

        # Download and install Istio
        curl -L https://istio.io/downloadIstio | sh -
        cd istio-*
        export PATH=$PWD/bin:$PATH
        istioctl install --set profile=production -y
        cd ..

        log_info "✓ Istio installed"
    else
        log_info "Istio already installed"
    fi

    # Apply Istio configurations
    kubectl apply -f deployments/service-mesh/istio/istio-config.yaml

    log_info "✓ Istio configured"
}

deploy_monitoring() {
    log_info "Deploying monitoring stack..."

    # Add Helm repos
    helm repo add grafana https://grafana.github.io/helm-charts
    helm repo add kubecost https://kubecost.github.io/cost-analyzer/
    helm repo update

    # Deploy Loki stack
    helm upgrade --install loki-stack grafana/loki-stack \
        --namespace monitoring \
        --create-namespace \
        --values deployments/monitoring/loki-stack-values.yaml

    # Get subscription ID
    SUBSCRIPTION_ID=$(az account show --query id -o tsv)

    # Deploy Kubecost
    helm upgrade --install kubecost kubecost/cost-analyzer \
        --namespace kubecost \
        --create-namespace \
        --values deployments/monitoring/kubecost-values.yaml \
        --set kubecostProductConfigs.clusterName="$CLUSTER_NAME" \
        --set azureCloudCost.enabled=true \
        --set azureCloudCost.costManagement.subscriptionId="$SUBSCRIPTION_ID" \
        --set azureCloudCost.costManagement.resourceGroup="$RESOURCE_GROUP"

    log_info "✓ Monitoring stack deployed"
}

deploy_application() {
    log_info "Deploying application with Helm..."

    # Get Azure Database endpoint
    AZURE_DB_FQDN=$(terraform -chdir=terraform/environments/azure output -raw azure_database_fqdn 2>/dev/null || echo "")

    if [ -z "$AZURE_DB_FQDN" ]; then
        log_warn "Azure Database endpoint not found. Using in-cluster PostgreSQL."
        POSTGRESQL_ENABLED=true
    else
        log_info "Using Azure Database: $AZURE_DB_FQDN"
        POSTGRESQL_ENABLED=false
    fi

    # Deploy application
    helm upgrade --install mcp-server-langgraph \
        ./deployments/helm/mcp-server-langgraph \
        --namespace "$NAMESPACE" \
        --create-namespace \
        --values deployments/helm/mcp-server-langgraph/values.yaml \
        --set postgresql.enabled="$POSTGRESQL_ENABLED" \
        --set postgresql.external.host="$AZURE_DB_FQDN" \
        --set postgresql.external.cloud.azure.enabled=true \
        --set serviceMesh.enabled=true

    log_info "✓ Application deployed"
}

deploy_vpa() {
    log_info "Deploying Vertical Pod Autoscalers..."

    # Install VPA (if not already installed)
    if ! kubectl get crd verticalpodautoscalers.autoscaling.k8s.io &> /dev/null; then
        log_info "Installing VPA..."
        git clone https://github.com/kubernetes/autoscaler.git /tmp/autoscaler
        cd /tmp/autoscaler/vertical-pod-autoscaler
        ./hack/vpa-up.sh
        cd -
        rm -rf /tmp/autoscaler
    fi

    # Apply VPA configurations
    kubectl apply -f deployments/base/postgres-vpa.yaml
    kubectl apply -f deployments/base/redis-vpa.yaml
    kubectl apply -f deployments/base/keycloak-vpa.yaml

    log_info "✓ VPA deployed"
}

verify_deployment() {
    log_info "Verifying deployment..."

    # Wait for pods
    kubectl wait --for=condition=ready pod \
        -l app=mcp-server-langgraph \
        -n "$NAMESPACE" \
        --timeout=300s

    # Check Istio sidecar injection
    POD_COUNT=$(kubectl get pods -n "$NAMESPACE" -l app=mcp-server-langgraph -o json | jq '.items | length')
    SIDECAR_COUNT=$(kubectl get pods -n "$NAMESPACE" -l app=mcp-server-langgraph -o json | jq '[.items[].spec.containers[] | select(.name=="istio-proxy")] | length')

    if [ "$POD_COUNT" -eq "$SIDECAR_COUNT" ]; then
        log_info "✓ Istio sidecars injected"
    else
        log_warn "Some pods missing Istio sidecars"
    fi

    # Check backup schedules
    BACKUP_COUNT=$(velero schedule get -o json 2>/dev/null | jq '.items | length' || echo "0")
    log_info "Velero backup schedules: $BACKUP_COUNT"

    # Check zone distribution
    log_info "Pod distribution across availability zones:"
    kubectl get pods -n "$NAMESPACE" -o wide | awk '{print $7}' | sort | uniq -c

    log_info "✓ Deployment verified"
}

print_next_steps() {
    log_info "\n=========================================="
    log_info "DEPLOYMENT COMPLETE!"
    log_info "==========================================\n"

    log_info "Next steps:"
    log_info "1. Access Kubecost dashboard:"
    log_info "   kubectl port-forward -n kubecost svc/kubecost-cost-analyzer 9090:9090"
    log_info "   Open http://localhost:9090"
    log_info ""
    log_info "2. Access Grafana (if deployed):"
    log_info "   kubectl port-forward -n monitoring svc/grafana 3000:80"
    log_info "   Open http://localhost:3000"
    log_info ""
    log_info "3. View Velero backups:"
    log_info "   velero backup get"
    log_info ""
    log_info "4. Check Istio mTLS:"
    log_info "   istioctl x authz check \$(kubectl get pod -n $NAMESPACE -l app=mcp-server-langgraph -o jsonpath='{.items[0].metadata.name}') -n $NAMESPACE"
    log_info ""
    log_info "5. Monitor costs in Azure Portal:"
    log_info "   https://portal.azure.com/#view/Microsoft_Azure_CostManagement/Menu/~/costanalysis"
}

# Main execution
main() {
    log_info "Starting AKS deployment for $CLUSTER_NAME..."
    echo ""
    log_warn "⚠️  IMPORTANT: Automated Terraform deployment not yet available for AKS"
    log_warn "    This script will guide you to the manual deployment documentation."
    log_warn "    See: docs/deployment/kubernetes/aks.mdx"
    echo ""

    check_prerequisites
    deploy_infrastructure
    configure_kubectl
    deploy_velero
    deploy_namespace_and_security
    deploy_istio
    deploy_monitoring
    deploy_application
    deploy_vpa
    verify_deployment
    print_next_steps

    log_info "\n✓ AKS deployment completed successfully!"
}

# Run main function
main "$@"
