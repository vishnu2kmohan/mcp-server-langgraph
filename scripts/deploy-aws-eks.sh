#!/bin/bash
# Deployment script for AWS EKS
# Implements all 11 Kubernetes best practices for AWS

set -e  # Exit on error
set -u  # Exit on undefined variable

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
AWS_REGION="${AWS_REGION:-us-east-1}"
CLUSTER_NAME="${EKS_CLUSTER_NAME:-mcp-production}"
AWS_ACCOUNT_ID="${AWS_ACCOUNT_ID:-}"
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

    # Check AWS CLI
    if ! command -v aws &> /dev/null; then
        log_error "AWS CLI not found. Please install: https://aws.amazon.com/cli/"
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

    # Get AWS account ID if not set
    if [ -z "$AWS_ACCOUNT_ID" ]; then
        AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
        log_info "AWS Account ID: $AWS_ACCOUNT_ID"
    fi

    log_info "✓ All prerequisites met"
}

deploy_infrastructure() {
    log_info "Deploying AWS infrastructure with Terraform..."

    cd terraform/environments/aws

    # Initialize Terraform
    terraform init

    # Plan
    terraform plan \
        -var="aws_region=$AWS_REGION" \
        -var="cluster_name=$CLUSTER_NAME" \
        -var="aws_account_id=$AWS_ACCOUNT_ID" \
        -out=tfplan

    # Apply
    terraform apply tfplan

    cd ../../..

    log_info "✓ Infrastructure deployed"
}

configure_kubectl() {
    log_info "Configuring kubectl for EKS cluster..."

    aws eks update-kubeconfig \
        --region "$AWS_REGION" \
        --name "$CLUSTER_NAME"

    log_info "✓ kubectl configured"
}

deploy_velero() {
    log_info "Deploying Velero for backup/DR..."

    # Create S3 bucket for backups (if not exists)
    BUCKET_NAME="${CLUSTER_NAME}-backups-${AWS_ACCOUNT_ID}"
    if ! aws s3 ls "s3://$BUCKET_NAME" &> /dev/null; then
        aws s3 mb "s3://$BUCKET_NAME" --region "$AWS_REGION"
        aws s3api put-bucket-versioning \
            --bucket "$BUCKET_NAME" \
            --versioning-configuration Status=Enabled
    fi

    # Get Velero IAM role ARN
    VELERO_ROLE_ARN=$(terraform -chdir=terraform/environments/aws output -raw velero_role_arn 2>/dev/null || echo "")

    # Install Velero
    helm repo add vmware-tanzu https://vmware-tanzu.github.io/helm-charts
    helm repo update

    helm upgrade --install velero vmware-tanzu/velero \
        --namespace velero \
        --create-namespace \
        --values deployments/backup/velero-values-aws.yaml \
        --set configuration.backupStorageLocation[0].bucket="$BUCKET_NAME" \
        --set configuration.backupStorageLocation[0].config.region="$AWS_REGION" \
        --set configuration.volumeSnapshotLocation[0].config.region="$AWS_REGION" \
        --set serviceAccount.server.annotations."eks\.amazonaws\.com/role-arn"="$VELERO_ROLE_ARN"

    # Apply backup schedules
    kubectl apply -f deployments/backup/backup-schedule.yaml

    log_info "✓ Velero deployed"
}

deploy_karpenter() {
    log_info "Deploying Karpenter for intelligent autoscaling..."

    # Get Karpenter IAM role ARN
    KARPENTER_ROLE_ARN=$(terraform -chdir=terraform/environments/aws output -raw karpenter_controller_role_arn 2>/dev/null || echo "")
    KARPENTER_INSTANCE_PROFILE=$(terraform -chdir=terraform/environments/aws output -raw karpenter_node_instance_profile_name 2>/dev/null || echo "")
    KARPENTER_SQS_QUEUE=$(terraform -chdir=terraform/environments/aws output -raw karpenter_sqs_queue_name 2>/dev/null || echo "")

    # Install Karpenter
    helm repo add karpenter https://charts.karpenter.sh
    helm repo update

    helm upgrade --install karpenter karpenter/karpenter \
        --namespace karpenter \
        --create-namespace \
        --set serviceAccount.annotations."eks\.amazonaws\.com/role-arn"="$KARPENTER_ROLE_ARN" \
        --set settings.aws.clusterName="$CLUSTER_NAME" \
        --set settings.aws.clusterEndpoint="$(aws eks describe-cluster --name $CLUSTER_NAME --query cluster.endpoint --output text)" \
        --set settings.aws.defaultInstanceProfile="$KARPENTER_INSTANCE_PROFILE" \
        --set settings.aws.interruptionQueueName="$KARPENTER_SQS_QUEUE"

    # Apply provisioners (update cluster name placeholder)
    sed "s/\${CLUSTER_NAME}/$CLUSTER_NAME/g" deployments/karpenter/provisioner-default.yaml | kubectl apply -f -

    log_info "✓ Karpenter deployed"
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

    # Deploy Kubecost
    helm upgrade --install kubecost kubecost/cost-analyzer \
        --namespace kubecost \
        --create-namespace \
        --values deployments/monitoring/kubecost-values.yaml \
        --set kubecostProductConfigs.clusterName="$CLUSTER_NAME" \
        --set awsCloudCost.enabled=true \
        --set awsCloudCost.cur.region="$AWS_REGION"

    log_info "✓ Monitoring stack deployed"
}

deploy_application() {
    log_info "Deploying application with Helm..."

    # Get RDS endpoint
    RDS_ENDPOINT=$(terraform -chdir=terraform/environments/aws output -raw rds_endpoint 2>/dev/null || echo "")

    if [ -z "$RDS_ENDPOINT" ]; then
        log_warn "RDS endpoint not found. Using in-cluster PostgreSQL."
        POSTGRESQL_ENABLED=true
    else
        log_info "Using RDS instance: $RDS_ENDPOINT"
        POSTGRESQL_ENABLED=false
    fi

    # Deploy application
    helm upgrade --install mcp-server-langgraph \
        ./deployments/helm/mcp-server-langgraph \
        --namespace "$NAMESPACE" \
        --create-namespace \
        --values deployments/helm/mcp-server-langgraph/values.yaml \
        --set postgresql.enabled="$POSTGRESQL_ENABLED" \
        --set postgresql.external.host="$RDS_ENDPOINT" \
        --set postgresql.external.cloud.rds.enabled=true \
        --set postgresql.external.cloud.rds.region="$AWS_REGION" \
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

    # Check Karpenter
    KARPENTER_PODS=$(kubectl get pods -n karpenter -l app.kubernetes.io/name=karpenter -o json | jq '.items | length')
    log_info "Karpenter pods running: $KARPENTER_PODS"

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
    log_info "4. Check Karpenter provisioners:"
    log_info "   kubectl get provisioners"
    log_info ""
    log_info "5. Monitor costs in AWS Cost Explorer:"
    log_info "   https://console.aws.amazon.com/cost-management/home#/cost-explorer"
}

# Main execution
main() {
    log_info "Starting EKS deployment for $CLUSTER_NAME..."

    check_prerequisites
    deploy_infrastructure
    configure_kubectl
    deploy_velero
    deploy_karpenter
    deploy_namespace_and_security
    deploy_istio
    deploy_monitoring
    deploy_application
    deploy_vpa
    verify_deployment
    print_next_steps

    log_info "\n✓ EKS deployment completed successfully!"
}

# Run main function
main "$@"
