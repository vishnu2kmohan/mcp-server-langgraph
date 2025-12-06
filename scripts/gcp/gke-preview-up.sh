#!/usr/bin/env bash

###############################################################################
# GKE Preview Environment - Setup Script
#
# Single-command deployment of the complete GKE preview environment:
# - GKE Autopilot cluster
# - Cloud SQL PostgreSQL (HA)
# - Memorystore Redis (HA)
# - VPC networking
# - Kubernetes workloads
#
# Prerequisites:
# - gcloud CLI installed and authenticated
# - terraform >= 1.5.0 installed
# - kubectl installed
# - jq installed
#
# Usage:
#   ./scripts/gcp/gke-preview-up.sh [OPTIONS]
#
# Options:
#   --project PROJECT_ID   GCP project ID (default: vishnu-sandbox-20250310)
#   --region REGION        GCP region (default: us-central1)
#   --skip-k8s             Skip Kubernetes workload deployment
#   --skip-validation      Skip post-deployment validation
#   --auto-approve         Skip confirmation prompts
#   --help                 Show help message
#
# Environment Variables:
#   GCP_PROJECT_ID         GCP project ID (alternative to --project)
#   GCP_REGION             GCP region (alternative to --region)
#
# Examples:
#   # Deploy with defaults (vishnu-sandbox-20250310)
#   ./scripts/gcp/gke-preview-up.sh
#
#   # Deploy to your own project
#   ./scripts/gcp/gke-preview-up.sh --project my-project-id
#
#   # Or using environment variable
#   GCP_PROJECT_ID=my-project-id ./scripts/gcp/gke-preview-up.sh
#
# Author: MCP Server LangGraph Team
# Date: 2025-12-06
###############################################################################

set -euo pipefail

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Source common library
# shellcheck source=lib/common.sh
source "$SCRIPT_DIR/lib/common.sh"

###############################################################################
# Configuration
###############################################################################

# Get project root
PROJECT_ROOT="$(get_project_root)"

# Default values (can be overridden by flags or env vars)
PROJECT_ID="${GCP_PROJECT_ID:-$DEFAULT_PROJECT_ID}"
REGION="${GCP_REGION:-$DEFAULT_REGION}"
NAMESPACE="$DEFAULT_NAMESPACE"

# Resource names (match Terraform naming)
CLUSTER_NAME="preview-mcp-server-langgraph-gke"
SHORT_PREFIX="preview-mcp-slg"  # Used in derived names below
export SHORT_PREFIX  # Exported for potential use in sourced scripts

# Flags
SKIP_K8S=false
SKIP_VALIDATION=false
AUTO_APPROVE=false

###############################################################################
# Help
###############################################################################

show_help() {
    cat << EOF
GKE Preview Environment - Setup Script

Deploy the complete GKE preview environment with a single command.

USAGE:
    $(basename "$0") [OPTIONS]

OPTIONS:
    --project PROJECT_ID   GCP project ID (default: $DEFAULT_PROJECT_ID)
    --region REGION        GCP region (default: $DEFAULT_REGION)
    --skip-k8s             Skip Kubernetes workload deployment
    --skip-validation      Skip post-deployment validation
    --auto-approve         Skip confirmation prompts
    --help                 Show this help message

ENVIRONMENT VARIABLES:
    GCP_PROJECT_ID         GCP project ID (alternative to --project)
    GCP_REGION             GCP region (alternative to --region)

EXAMPLES:
    # Deploy with defaults
    $(basename "$0")

    # Deploy to your own project
    $(basename "$0") --project my-project-id

    # Using environment variable
    GCP_PROJECT_ID=my-project-id $(basename "$0")

    # Non-interactive deployment (for CI/CD)
    $(basename "$0") --auto-approve

WHAT THIS CREATES:
    - GKE Autopilot cluster (regional, us-central1)
    - Cloud SQL PostgreSQL 16 (HA, 2 vCPU, 7.5GB RAM)
    - Memorystore Redis 7.2 (HA, 5GB)
    - VPC with private subnets
    - Cloud NAT for egress
    - Workload Identity bindings
    - Kubernetes workloads (MCP Server, Keycloak, OpenFGA)

ESTIMATED TIME:
    - Infrastructure (Terraform): 15-20 minutes
    - Kubernetes workloads: 5-10 minutes
    - Total: ~25-30 minutes

ESTIMATED COST:
    - ~\$325/month (can vary based on usage)
    - GKE Autopilot scales down when idle

For more details, see: docs/deployment/kubernetes/gke-preview.mdx

EOF
}

###############################################################################
# Parse Arguments
###############################################################################

parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --project)
                PROJECT_ID="$2"
                shift 2
                ;;
            --region)
                REGION="$2"
                shift 2
                ;;
            --skip-k8s)
                SKIP_K8S=true
                shift
                ;;
            --skip-validation)
                SKIP_VALIDATION=true
                shift
                ;;
            --auto-approve)
                AUTO_APPROVE=true
                shift
                ;;
            --help|-h)
                show_help
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                echo ""
                echo "Run '$(basename "$0") --help' for usage information."
                exit 1
                ;;
        esac
    done
}

###############################################################################
# Pre-flight Checks
###############################################################################

preflight_checks() {
    log_step "Running pre-flight checks..."

    # Check prerequisites
    check_all_prerequisites || exit 1

    # Check GCP auth
    local active_account
    active_account=$(check_gcp_auth) || exit 1

    # Set project
    set_gcp_project "$PROJECT_ID" || exit 1

    # Show configuration summary
    echo ""
    echo "Configuration:"
    echo "  Project:   $PROJECT_ID"
    echo "  Region:    $REGION"
    echo "  Cluster:   $CLUSTER_NAME"
    echo "  Namespace: $NAMESPACE"
    echo "  Account:   $active_account"

    log_success "Pre-flight checks passed"
}

###############################################################################
# Cost Warning
###############################################################################

show_cost_warning() {
    if [ "$AUTO_APPROVE" = true ]; then
        log_info "Auto-approve enabled, skipping cost confirmation"
        return 0
    fi

    show_cost_estimate

    if ! confirm_action "Do you want to proceed with deployment?"; then
        log_info "Deployment cancelled"
        exit 0
    fi
}

###############################################################################
# Terraform Deployment
###############################################################################

deploy_infrastructure() {
    log_step "Deploying infrastructure with Terraform..."

    local tf_dir
    tf_dir=$(get_terraform_dir)

    # Initialize Terraform
    terraform_init_if_needed

    # Show what will be created
    log_substep "Planning infrastructure changes..."
    echo ""

    if [ "$AUTO_APPROVE" = true ]; then
        # Auto-approve mode
        terraform -chdir="$tf_dir" apply \
            -auto-approve \
            -var="project_id=$PROJECT_ID" \
            -var="region=$REGION" \
            -no-color
    else
        # Interactive mode - show plan first
        terraform -chdir="$tf_dir" plan \
            -var="project_id=$PROJECT_ID" \
            -var="region=$REGION" \
            -no-color

        echo ""
        if ! confirm_action "Apply this Terraform plan?"; then
            log_info "Terraform apply cancelled"
            exit 0
        fi

        terraform -chdir="$tf_dir" apply \
            -var="project_id=$PROJECT_ID" \
            -var="region=$REGION" \
            -no-color
    fi

    log_success "Infrastructure deployment complete"
}

###############################################################################
# Kubernetes Deployment
###############################################################################

deploy_kubernetes() {
    if [ "$SKIP_K8S" = true ]; then
        log_warn "Skipping Kubernetes workload deployment (--skip-k8s)"
        return 0
    fi

    log_step "Deploying Kubernetes workloads..."

    # Get GKE credentials
    get_gke_credentials "$CLUSTER_NAME" "$REGION" "$PROJECT_ID" || {
        log_error "Failed to get GKE credentials"
        log_warn "Infrastructure was created, but K8s deployment failed"
        return 1
    }

    # Apply Kustomize manifests
    log_substep "Applying Kustomize manifests..."
    kubectl apply -k "$PROJECT_ROOT/deployments/overlays/preview-gke"

    # Wait for critical deployments
    log_substep "Waiting for deployments to become ready..."

    local deployments=(
        "preview-keycloak"
        "preview-openfga"
        "preview-mcp-server-langgraph"
    )

    local failed=false
    for deployment in "${deployments[@]}"; do
        if ! wait_for_rollout "$deployment" "$NAMESPACE" "10m"; then
            failed=true
        fi
    done

    if [ "$failed" = true ]; then
        log_warn "Some deployments did not become ready in time"
        log_info "You can check status with: kubectl get pods -n $NAMESPACE"
    else
        log_success "All deployments are ready"
    fi

    log_success "Kubernetes workload deployment complete"
}

###############################################################################
# Validation
###############################################################################

run_validation() {
    if [ "$SKIP_VALIDATION" = true ]; then
        log_warn "Skipping validation (--skip-validation)"
        return 0
    fi

    log_step "Running post-deployment validation..."

    # Run smoke tests
    if [ -x "$SCRIPT_DIR/preview-smoke-tests.sh" ]; then
        log_substep "Running smoke tests..."
        "$SCRIPT_DIR/preview-smoke-tests.sh" --skip-integration-tests || {
            log_warn "Some smoke tests failed"
        }
    fi

    # Run validation script
    if [ -x "$SCRIPT_DIR/validate-preview-deployment.sh" ]; then
        log_substep "Running deployment validation..."
        "$SCRIPT_DIR/validate-preview-deployment.sh" --skip-cost-check || {
            log_warn "Some validations reported issues"
        }
    fi

    log_success "Validation complete"
}

###############################################################################
# Access Instructions
###############################################################################

show_access_instructions() {
    echo ""
    show_success_banner "GKE Preview Environment Deployed Successfully!"

    echo ""
    echo "Access Instructions:"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "1. Get cluster credentials:"
    echo "   gcloud container clusters get-credentials $CLUSTER_NAME \\"
    echo "       --region=$REGION --project=$PROJECT_ID"
    echo ""
    echo "2. Check pod status:"
    echo "   kubectl get pods -n $NAMESPACE"
    echo ""
    echo "3. View logs:"
    echo "   kubectl logs -f deployment/preview-mcp-server-langgraph -n $NAMESPACE"
    echo ""
    echo "4. Port-forward to services:"
    echo "   kubectl port-forward svc/preview-mcp-server-langgraph 8000:8000 -n $NAMESPACE"
    echo "   kubectl port-forward svc/preview-keycloak 8082:8082 -n $NAMESPACE"
    echo "   kubectl port-forward svc/preview-openfga 8080:8080 -n $NAMESPACE"
    echo ""
    echo "5. View in GCP Console:"
    echo "   https://console.cloud.google.com/kubernetes/workload?project=$PROJECT_ID"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "To teardown this environment:"
    echo "   ./scripts/gcp/gke-preview-down.sh"
    echo ""
    echo "Or using make:"
    echo "   make gke-preview-down"
    echo ""
}

###############################################################################
# Main
###############################################################################

main() {
    show_header "GKE Preview Environment Setup" "Deploy complete preview infrastructure"

    # Parse command line arguments
    parse_args "$@"

    # Run pre-flight checks
    preflight_checks

    # Show cost warning and get confirmation
    show_cost_warning

    # Deploy infrastructure
    deploy_infrastructure

    # Deploy Kubernetes workloads
    deploy_kubernetes

    # Run validation
    run_validation

    # Show access instructions
    show_access_instructions

    log_success "GKE preview environment is ready!"
}

# Run main
main "$@"
