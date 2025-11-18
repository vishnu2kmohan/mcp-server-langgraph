#!/bin/bash
#
# Vertex AI Workload Identity Setup for Staging
#
# This script configures Workload Identity Federation for Vertex AI access
# in the staging GKE environment. It creates a dedicated service account
# and binds it to the Kubernetes service account for keyless authentication.
#
# Prerequisites:
# - GKE cluster with Workload Identity enabled
# - gcloud CLI installed and authenticated
# - Staging infrastructure already created (run setup-staging-infrastructure.sh first)
#
# Usage:
#   ./scripts/gcp/setup-vertex-ai-staging.sh
#

set -euo pipefail

# Configuration
PROJECT_ID="${GCP_PROJECT_ID:-vishnu-sandbox-20250310}"
REGION="us-central1"
CLUSTER_NAME="mcp-staging-cluster"
K8S_NAMESPACE="mcp-staging"
K8S_SERVICE_ACCOUNT="mcp-server-langgraph"
GCP_SERVICE_ACCOUNT="vertex-ai-staging"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

check_prerequisites() {
    log_step "Checking prerequisites..."

    # Check gcloud
    if ! command -v gcloud &> /dev/null; then
        log_error "gcloud CLI not found. Please install: https://cloud.google.com/sdk/docs/install"
        exit 1
    fi

    # Check kubectl
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl not found. Please install: https://kubernetes.io/docs/tasks/tools/"
        exit 1
    fi

    # Set project
    log_info "Setting GCP project to: $PROJECT_ID"
    gcloud config set project "$PROJECT_ID"

    # Get project number (needed for Workload Identity)
    PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format="value(projectNumber)")
    log_info "Project number: $PROJECT_NUMBER"

    # Verify cluster exists
    if ! gcloud container clusters describe "$CLUSTER_NAME" --region="$REGION" &> /dev/null; then
        log_error "GKE cluster '$CLUSTER_NAME' not found. Run setup-staging-infrastructure.sh first."
        exit 1
    fi

    # Get cluster credentials
    log_info "Getting cluster credentials..."
    gcloud container clusters get-credentials "$CLUSTER_NAME" --region="$REGION"

    # Verify namespace exists
    if ! kubectl get namespace "$K8S_NAMESPACE" &> /dev/null; then
        log_error "Kubernetes namespace '$K8S_NAMESPACE' not found. Deploy staging manifests first."
        exit 1
    fi
}

enable_vertex_ai_api() {
    log_step "Enabling Vertex AI API..."

    gcloud services enable \
        aiplatform.googleapis.com \
        --project="$PROJECT_ID"

    log_info "Vertex AI API enabled successfully"
}

create_service_account() {
    log_step "Creating Vertex AI service account..."

    # Check if service account already exists
    if gcloud iam service-accounts describe "${GCP_SERVICE_ACCOUNT}@${PROJECT_ID}.iam.gserviceaccount.com" &> /dev/null; then
        log_warn "Service account ${GCP_SERVICE_ACCOUNT} already exists, skipping creation"
        return 0
    fi

    # Create service account
    gcloud iam service-accounts create "$GCP_SERVICE_ACCOUNT" \
        --display-name="Vertex AI Staging" \
        --description="Service account for Vertex AI access in staging environment" \
        --project="$PROJECT_ID"

    log_info "Service account created: ${GCP_SERVICE_ACCOUNT}@${PROJECT_ID}.iam.gserviceaccount.com"
}

grant_vertex_ai_permissions() {
    log_step "Granting Vertex AI permissions..."

    # Grant Vertex AI User role (allows API calls to Vertex AI)
    log_info "Granting aiplatform.user role..."
    gcloud projects add-iam-policy-binding "$PROJECT_ID" \
        --member="serviceAccount:${GCP_SERVICE_ACCOUNT}@${PROJECT_ID}.iam.gserviceaccount.com" \
        --role="roles/aiplatform.user" \
        --condition=None

    # Grant AI Platform Developer role (for model management)
    log_info "Granting aiplatform.developer role..."
    gcloud projects add-iam-policy-binding "$PROJECT_ID" \
        --member="serviceAccount:${GCP_SERVICE_ACCOUNT}@${PROJECT_ID}.iam.gserviceaccount.com" \
        --role="roles/aiplatform.developer" \
        --condition=None

    # Grant logging permissions (for Cloud Logging integration)
    log_info "Granting logging.logWriter role..."
    gcloud projects add-iam-policy-binding "$PROJECT_ID" \
        --member="serviceAccount:${GCP_SERVICE_ACCOUNT}@${PROJECT_ID}.iam.gserviceaccount.com" \
        --role="roles/logging.logWriter" \
        --condition=None

    # Grant monitoring permissions (for metrics)
    log_info "Granting monitoring.metricWriter role..."
    gcloud projects add-iam-policy-binding "$PROJECT_ID" \
        --member="serviceAccount:${GCP_SERVICE_ACCOUNT}@${PROJECT_ID}.iam.gserviceaccount.com" \
        --role="roles/monitoring.metricWriter" \
        --condition=None

    log_info "Permissions granted successfully"
}

setup_workload_identity_binding() {
    log_step "Setting up Workload Identity binding..."

    # Allow Kubernetes service account to impersonate GCP service account
    log_info "Binding Kubernetes SA to GCP SA..."
    gcloud iam service-accounts add-iam-policy-binding \
        "${GCP_SERVICE_ACCOUNT}@${PROJECT_ID}.iam.gserviceaccount.com" \
        --role="roles/iam.workloadIdentityUser" \
        --member="serviceAccount:${PROJECT_ID}.svc.id.goog[${K8S_NAMESPACE}/${K8S_SERVICE_ACCOUNT}]"

    log_info "Workload Identity binding created successfully"
}

annotate_kubernetes_service_account() {
    log_step "Annotating Kubernetes service account..."

    # Check if service account exists
    if ! kubectl get serviceaccount "$K8S_SERVICE_ACCOUNT" -n "$K8S_NAMESPACE" &> /dev/null; then
        log_error "Kubernetes service account '$K8S_SERVICE_ACCOUNT' not found in namespace '$K8S_NAMESPACE'"
        log_error "Deploy the staging manifests first: kubectl apply -k deployments/overlays/staging-gke"
        exit 1
    fi

    # Annotate the Kubernetes service account
    kubectl annotate serviceaccount "$K8S_SERVICE_ACCOUNT" \
        -n "$K8S_NAMESPACE" \
        iam.gke.io/gcp-service-account="${GCP_SERVICE_ACCOUNT}@${PROJECT_ID}.iam.gserviceaccount.com" \
        --overwrite

    log_info "Kubernetes service account annotated successfully"
}

verify_configuration() {
    log_step "Verifying configuration..."

    # Verify GCP service account
    log_info "Checking GCP service account..."
    if gcloud iam service-accounts describe "${GCP_SERVICE_ACCOUNT}@${PROJECT_ID}.iam.gserviceaccount.com" &> /dev/null; then
        echo "  ✓ GCP service account exists"
    else
        log_error "GCP service account not found"
        exit 1
    fi

    # Verify IAM bindings
    log_info "Checking IAM bindings..."
    local bindings
    bindings=$(gcloud projects get-iam-policy "$PROJECT_ID" \
        --flatten="bindings[].members" \
        --filter="bindings.members:serviceAccount:${GCP_SERVICE_ACCOUNT}@${PROJECT_ID}.iam.gserviceaccount.com" \
        --format="value(bindings.role)")

    if echo "$bindings" | grep -q "roles/aiplatform.user"; then
        echo "  ✓ aiplatform.user role granted"
    else
        log_warn "aiplatform.user role not found"
    fi

    if echo "$bindings" | grep -q "roles/aiplatform.developer"; then
        echo "  ✓ aiplatform.developer role granted"
    else
        log_warn "aiplatform.developer role not found"
    fi

    # Verify Workload Identity binding
    log_info "Checking Workload Identity binding..."
    local wi_binding
    wi_binding=$(gcloud iam service-accounts get-iam-policy \
        "${GCP_SERVICE_ACCOUNT}@${PROJECT_ID}.iam.gserviceaccount.com" \
        --format=json | jq -r '.bindings[] | select(.role=="roles/iam.workloadIdentityUser") | .members[]')

    if echo "$wi_binding" | grep -q "${PROJECT_ID}.svc.id.goog\[${K8S_NAMESPACE}/${K8S_SERVICE_ACCOUNT}\]"; then
        echo "  ✓ Workload Identity binding configured"
    else
        log_warn "Workload Identity binding not found"
    fi

    # Verify Kubernetes service account annotation
    log_info "Checking Kubernetes service account annotation..."
    local annotation
    annotation=$(kubectl get serviceaccount "$K8S_SERVICE_ACCOUNT" -n "$K8S_NAMESPACE" \
        -o jsonpath='{.metadata.annotations.iam\.gke\.io/gcp-service-account}')

    if [ "$annotation" == "${GCP_SERVICE_ACCOUNT}@${PROJECT_ID}.iam.gserviceaccount.com" ]; then
        echo "  ✓ Kubernetes service account annotated"
    else
        log_warn "Kubernetes service account annotation missing or incorrect"
    fi

    log_info "Configuration verification complete"
}

test_vertex_ai_access() {
    log_step "Testing Vertex AI access (optional)..."

    log_info "To test Vertex AI access from a pod, run:"
    echo ""
    echo "  kubectl run -it --rm test-vertex-ai \\"
    echo "    --image=google/cloud-sdk:slim \\"
    echo "    --serviceaccount=$K8S_SERVICE_ACCOUNT \\"
    echo "    --namespace=$K8S_NAMESPACE \\"
    echo "    -- gcloud auth list"
    echo ""
    log_info "Expected output: ${GCP_SERVICE_ACCOUNT}@${PROJECT_ID}.iam.gserviceaccount.com (active)"
}

print_summary() {
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    log_info "Vertex AI Workload Identity Setup Complete!"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "📋 Summary:"
    echo "  • Project: $PROJECT_ID"
    echo "  • Region: $REGION"
    echo "  • GCP Service Account: ${GCP_SERVICE_ACCOUNT}@${PROJECT_ID}.iam.gserviceaccount.com"
    echo "  • K8s Service Account: ${K8S_NAMESPACE}/${K8S_SERVICE_ACCOUNT}"
    echo ""
    echo "🔐 Granted Permissions:"
    echo "  ✓ roles/aiplatform.user (Vertex AI API access)"
    echo "  ✓ roles/aiplatform.developer (Model management)"
    echo "  ✓ roles/logging.logWriter (Cloud Logging)"
    echo "  ✓ roles/monitoring.metricWriter (Cloud Monitoring)"
    echo ""
    echo "🔗 Workload Identity:"
    echo "  ✓ Kubernetes → GCP service account binding configured"
    echo "  ✓ No service account keys required (keyless authentication)"
    echo ""
    echo "📝 Next Steps:"
    echo "  1. Update deployment configuration:"
    echo "     • Set VERTEX_PROJECT=$PROJECT_ID"
    echo "     • Set VERTEX_LOCATION=$REGION"
    echo "     • Set LLM_PROVIDER=google (or vertex_ai)"
    echo ""
    echo "  2. Apply the updated deployment:"
    echo "     kubectl apply -k deployments/overlays/staging-gke"
    echo ""
    echo "  3. Verify Vertex AI access:"
    echo "     kubectl exec -it <pod-name> -n $K8S_NAMESPACE -- gcloud auth list"
    echo ""
    echo "  4. Test with LiteLLM:"
    echo "     # From inside the pod"
    echo "     python3 -c 'from litellm import completion; print(completion(model=\"vertex_ai/gemini-2.5-flash\", messages=[{\"role\":\"user\",\"content\":\"Hello\"}], vertex_project=\"$PROJECT_ID\", vertex_location=\"$REGION\"))'"
    echo ""
    echo "📚 Documentation:"
    echo "  • See docs/deployment/vertex-ai-workload-identity.mdx for full guide"
    echo "  • See docs/guides/google-gemini.mdx for Vertex AI usage"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

# Main execution
main() {
    log_info "Starting Vertex AI Workload Identity Setup..."
    echo ""

    check_prerequisites
    enable_vertex_ai_api
    create_service_account
    grant_vertex_ai_permissions
    setup_workload_identity_binding
    annotate_kubernetes_service_account
    verify_configuration
    test_vertex_ai_access

    echo ""
    print_summary
}

# Run main function
main "$@"
