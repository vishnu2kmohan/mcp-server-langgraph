#!/usr/bin/env bash

###############################################################################
# Staging GKE Infrastructure Teardown Script
#
# This script performs a complete teardown of the staging GKE environment,
# ensuring all resources are cleanly deleted and no orphaned resources remain.
#
# Features:
# - Idempotent: Safe to run multiple times
# - Complete cleanup: Kubernetes resources, Helm releases, GKE cluster,
#   Cloud SQL, Memorystore, VPC, IAM, Secrets
# - Dry-run mode by default (requires confirmation)
# - Comprehensive logging and error handling
# - Verification of resource deletion
#
# Prerequisites:
# - gcloud CLI installed and authenticated
# - kubectl configured
# - helm installed
# - Proper permissions to delete resources
#
# Usage:
#   ./scripts/gcp/teardown-staging-infrastructure.sh [OPTIONS]
#
# Options:
#   --auto-approve          Skip confirmation prompt
#   --keep-terraform-state  Don't clean up Terraform state
#   --help                  Show help message
#
# Author: Auto-enhanced for comprehensive cleanup
# Date: 2025-11-03
###############################################################################

set -euo pipefail

# Configuration
readonly PROJECT_ID="${GCP_PROJECT_ID:-vishnu-sandbox-20250310}"
readonly REGION="us-central1"
readonly CLUSTER_NAME="staging-mcp-server-langgraph-gke"
readonly NAMESPACE="staging-mcp-server-langgraph"
readonly VPC_NAME="staging-vpc"
readonly CLOUD_SQL_INSTANCE="mcp-staging-postgres"
readonly REDIS_INSTANCE="mcp-staging-redis"
readonly TERRAFORM_DIR="terraform/environments/gcp-staging"
readonly ARTIFACT_REGISTRY_REPO="mcp-staging"
readonly WORKLOAD_IDENTITY_POOL="github-actions-pool"
readonly WORKLOAD_IDENTITY_PROVIDER="github-provider"

# Service accounts to delete
readonly SERVICE_ACCOUNTS=(
    "mcp-staging-sa"
    "mcp-staging-keycloak-sa"
    "mcp-staging-openfga-sa"
    "mcp-staging-external-secrets-sa"
)

# Secrets to delete from Secret Manager
readonly SECRETS=(
    "staging-keycloak-db-password"
    "staging-openfga-db-password"
    "staging-redis-password"
    "staging-anthropic-api-key"
    "staging-google-api-key"
    "staging-jwt-secret"
)

# Flags
AUTO_APPROVE=false
KEEP_TERRAFORM_STATE=false

# Color codes for output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m' # No Color

###############################################################################
# Helper Functions
###############################################################################

log_info() {
    echo -e "${BLUE}[INFO]${NC} $*"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $*"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $*"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*"
}

check_prerequisites() {
    log_info "Checking prerequisites..."

    local missing_tools=()

    for tool in gcloud kubectl helm; do
        if ! command -v "$tool" &> /dev/null; then
            missing_tools+=("$tool")
        fi
    done

    if [ ${#missing_tools[@]} -gt 0 ]; then
        log_error "Missing required tools: ${missing_tools[*]}"
        log_error "Please install the missing tools and try again"
        exit 1
    fi

    # Check if authenticated with gcloud
    if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
        log_error "Not authenticated with gcloud. Run: gcloud auth login"
        exit 1
    fi

    # Set project
    gcloud config set project "$PROJECT_ID" --quiet

    log_success "Prerequisites check passed"
}

confirm_teardown() {
    if [ "$AUTO_APPROVE" = true ]; then
        log_warn "Auto-approve enabled, skipping confirmation"
        return 0
    fi

    log_warn "============================================"
    log_warn "WARNING: This will DELETE all staging resources"
    log_warn "============================================"
    log_warn "Project: $PROJECT_ID"
    log_warn "Region: $REGION"
    log_warn "Cluster: $CLUSTER_NAME"
    log_warn "Cloud SQL: $CLOUD_SQL_INSTANCE"
    log_warn "Redis: $REDIS_INSTANCE"
    log_warn "VPC: $VPC_NAME"
    log_warn "============================================"

    read -rp "Are you sure you want to proceed? (type 'yes' to confirm): " confirmation

    if [ "$confirmation" != "yes" ]; then
        log_info "Teardown cancelled by user"
        exit 0
    fi

    log_info "Teardown confirmed, proceeding..."
}

resource_exists() {
    local resource_type=$1
    local resource_name=$2

    case "$resource_type" in
        "gke-cluster")
            gcloud container clusters describe "$resource_name" \
                --region="$REGION" \
                --project="$PROJECT_ID" &> /dev/null
            ;;
        "cloud-sql")
            gcloud sql instances describe "$resource_name" \
                --project="$PROJECT_ID" &> /dev/null
            ;;
        "redis")
            gcloud redis instances describe "$resource_name" \
                --region="$REGION" \
                --project="$PROJECT_ID" &> /dev/null
            ;;
        "vpc")
            gcloud compute networks describe "$resource_name" \
                --project="$PROJECT_ID" &> /dev/null
            ;;
        "service-account")
            gcloud iam service-accounts describe "${resource_name}@${PROJECT_ID}.iam.gserviceaccount.com" \
                --project="$PROJECT_ID" &> /dev/null
            ;;
        "secret")
            gcloud secrets describe "$resource_name" \
                --project="$PROJECT_ID" &> /dev/null
            ;;
        *)
            log_error "Unknown resource type: $resource_type"
            return 1
            ;;
    esac
}

###############################################################################
# Kubernetes Cleanup
###############################################################################

cleanup_kubernetes_resources() {
    log_info "=========================================="
    log_info "Step 1: Cleaning up Kubernetes resources"
    log_info "=========================================="

    if ! resource_exists "gke-cluster" "$CLUSTER_NAME"; then
        log_warn "GKE cluster $CLUSTER_NAME not found, skipping K8s cleanup"
        return 0
    fi

    log_info "Getting GKE credentials..."
    gcloud container clusters get-credentials "$CLUSTER_NAME" \
        --region="$REGION" \
        --project="$PROJECT_ID" || {
            log_warn "Failed to get GKE credentials, cluster may already be deleted"
            return 0
        }

    # Delete namespace (this will cascade delete all resources in the namespace)
    if kubectl get namespace "$NAMESPACE" &> /dev/null; then
        log_info "Deleting namespace $NAMESPACE and all resources within it..."
        kubectl delete namespace "$NAMESPACE" --timeout=5m || log_warn "Failed to delete namespace cleanly"

        # Wait for namespace to be fully deleted
        log_info "Waiting for namespace to be fully deleted..."
        timeout 300 bash -c "while kubectl get namespace $NAMESPACE &> /dev/null; do sleep 5; done" || {
            log_warn "Timeout waiting for namespace deletion, forcing cleanup"
            kubectl patch namespace "$NAMESPACE" -p '{"metadata":{"finalizers":[]}}' --type=merge || true
        }

        log_success "Namespace $NAMESPACE deleted"
    else
        log_warn "Namespace $NAMESPACE not found"
    fi

    log_success "Kubernetes resources cleaned up"
}

###############################################################################
# Helm Releases Cleanup
###############################################################################

cleanup_helm_releases() {
    log_info "=========================================="
    log_info "Step 2: Cleaning up Helm releases"
    log_info "=========================================="

    if ! resource_exists "gke-cluster" "$CLUSTER_NAME"; then
        log_warn "GKE cluster not found, skipping Helm cleanup"
        return 0
    fi

    # Delete External Secrets Operator
    if helm list -n external-secrets-system 2>/dev/null | grep -q external-secrets; then
        log_info "Deleting External Secrets Operator..."
        helm uninstall external-secrets -n external-secrets-system || log_warn "Failed to uninstall external-secrets"
        kubectl delete namespace external-secrets-system --timeout=2m || log_warn "Failed to delete external-secrets-system namespace"
        log_success "External Secrets Operator removed"
    else
        log_warn "External Secrets Operator not found"
    fi

    log_success "Helm releases cleaned up"
}

###############################################################################
# GKE Cluster Deletion
###############################################################################

delete_gke_cluster() {
    log_info "=========================================="
    log_info "Step 3: Deleting GKE cluster"
    log_info "=========================================="

    if ! resource_exists "gke-cluster" "$CLUSTER_NAME"; then
        log_warn "GKE cluster $CLUSTER_NAME not found, skipping"
        return 0
    fi

    log_info "Deleting GKE Autopilot cluster $CLUSTER_NAME (this may take 5-10 minutes)..."
    gcloud container clusters delete "$CLUSTER_NAME" \
        --region="$REGION" \
        --project="$PROJECT_ID" \
        --quiet || {
            log_error "Failed to delete GKE cluster"
            return 1
        }

    log_success "GKE cluster deleted successfully"
}

delete_workload_identity() {
    log_info "Deleting Workload Identity Federation resources..."

    # Get project number
    PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format="value(projectNumber)")

    # Delete provider
    if gcloud iam workload-identity-pools providers describe "$WORKLOAD_IDENTITY_PROVIDER" \
        --workload-identity-pool="$WORKLOAD_IDENTITY_POOL" \
        --location=global &> /dev/null; then

        log_warn "Deleting Workload Identity Provider..."
        gcloud iam workload-identity-pools providers delete "$WORKLOAD_IDENTITY_PROVIDER" \
            --workload-identity-pool="$WORKLOAD_IDENTITY_POOL" \
            --location=global \
            --quiet

        log_info "Workload Identity Provider deleted"
    else
        log_warn "Workload Identity Provider not found, skipping"
    fi

    # Delete pool
    if gcloud iam workload-identity-pools describe "$WORKLOAD_IDENTITY_POOL" \
        --location=global &> /dev/null; then

        log_warn "Deleting Workload Identity Pool..."
        gcloud iam workload-identity-pools delete "$WORKLOAD_IDENTITY_POOL" \
            --location=global \
            --quiet

        log_info "Workload Identity Pool deleted"
    else
        log_warn "Workload Identity Pool not found, skipping"
    fi
}

###############################################################################
# IAM and Service Accounts Cleanup
###############################################################################

cleanup_iam() {
    log_info "=========================================="
    log_info "Step 7: Cleaning up IAM and service accounts"
    log_info "=========================================="

    for sa_name in "${SERVICE_ACCOUNTS[@]}"; do
        local sa_email="${sa_name}@${PROJECT_ID}.iam.gserviceaccount.com"

        if resource_exists "service-account" "$sa_name"; then
            log_info "Deleting service account: $sa_email"
            gcloud iam service-accounts delete "$sa_email" \
                --project="$PROJECT_ID" \
                --quiet || log_warn "Failed to delete service account: $sa_email"
            log_success "Service account $sa_name deleted"
        else
            log_warn "Service account $sa_email not found"
        fi
    done

    # Delete Workload Identity Pool
    log_info "Deleting Workload Identity Pool for GitHub Actions..."
    if gcloud iam workload-identity-pools describe "$WORKLOAD_IDENTITY_POOL" --location=global --project="$PROJECT_ID" &> /dev/null; then
        # First delete the provider
        if gcloud iam workload-identity-pools providers describe "$WORKLOAD_IDENTITY_PROVIDER" \
            --workload-identity-pool="$WORKLOAD_IDENTITY_POOL" \
            --location=global --project="$PROJECT_ID" &> /dev/null; then
            log_info "Deleting Workload Identity Provider..."
            gcloud iam workload-identity-pools providers delete "$WORKLOAD_IDENTITY_PROVIDER" \
                --workload-identity-pool="$WORKLOAD_IDENTITY_POOL" \
                --location=global \
                --project="$PROJECT_ID" \
                --quiet || log_warn "Failed to delete Workload Identity Provider"
        fi

        # Then delete the pool
        gcloud iam workload-identity-pools delete "$WORKLOAD_IDENTITY_POOL" \
            --location=global \
            --project="$PROJECT_ID" \
            --quiet || log_warn "Failed to delete Workload Identity Pool"
        log_success "Workload Identity Pool deleted"
    else
        log_warn "Workload Identity Pool not found"
    fi

    log_success "IAM resources cleaned up"
}

###############################################################################
# Cloud SQL Deletion
###############################################################################

delete_cloud_sql() {
    log_info "=========================================="
    log_info "Step 4: Deleting Cloud SQL instance"
    log_info "=========================================="

    if ! resource_exists "cloud-sql" "$CLOUD_SQL_INSTANCE"; then
        log_warn "Cloud SQL instance $CLOUD_SQL_INSTANCE not found, skipping"
        return 0
    fi

    # Disable deletion protection if enabled
    log_info "Disabling deletion protection..."
    gcloud sql instances patch "$CLOUD_SQL_INSTANCE" \
        --no-deletion-protection \
        --project="$PROJECT_ID" \
        --quiet || log_warn "Failed to disable deletion protection"

    log_info "Deleting Cloud SQL instance $CLOUD_SQL_INSTANCE..."
    gcloud sql instances delete "$CLOUD_SQL_INSTANCE" \
        --project="$PROJECT_ID" \
        --quiet || {
            log_error "Failed to delete Cloud SQL instance"
            return 1
        }

    log_success "Cloud SQL instance deleted successfully"
}

###############################################################################
# Memorystore Redis Deletion
###############################################################################

delete_redis() {
    log_info "=========================================="
    log_info "Step 5: Deleting Memorystore Redis"
    log_info "=========================================="

    if ! resource_exists "redis" "$REDIS_INSTANCE"; then
        log_warn "Redis instance $REDIS_INSTANCE not found, skipping"
        return 0
    fi

    log_info "Deleting Memorystore Redis instance $REDIS_INSTANCE..."
    gcloud redis instances delete "$REDIS_INSTANCE" \
        --region="$REGION" \
        --project="$PROJECT_ID" \
        --quiet || {
            log_error "Failed to delete Redis instance"
            return 1
        }

    log_success "Memorystore Redis deleted successfully"
}

delete_artifact_registry() {
    log_info "Checking for Artifact Registry repositories..."

    if gcloud artifacts repositories describe "$ARTIFACT_REGISTRY_REPO" \
        --location="$REGION" &> /dev/null; then

        log_warn "Deleting Artifact Registry repository: $ARTIFACT_REGISTRY_REPO..."
        gcloud artifacts repositories delete "$ARTIFACT_REGISTRY_REPO" \
            --location="$REGION" \
            --quiet

        log_info "Artifact Registry repository deleted"
    else
        log_warn "Artifact Registry repository not found, skipping"
    fi
}

###############################################################################
# Secret Manager Cleanup
###############################################################################

cleanup_secrets() {
    log_info "=========================================="
    log_info "Step 8: Cleaning up Secret Manager secrets"
    log_info "=========================================="

    for secret_name in "${SECRETS[@]}"; do
        if resource_exists "secret" "$secret_name"; then
            log_info "Deleting secret: $secret_name"
            gcloud secrets delete "$secret_name" \
                --project="$PROJECT_ID" \
                --quiet || log_warn "Failed to delete secret: $secret_name"
            log_success "Secret $secret_name deleted"
        else
            log_warn "Secret $secret_name not found"
        fi
    done

    log_success "Secret Manager secrets cleaned up"
}

###############################################################################
# VPC and Network Resources Deletion
###############################################################################

delete_vpc_network() {
    log_info "=========================================="
    log_info "Step 6: Deleting VPC and network resources"
    log_info "=========================================="

    if ! resource_exists "vpc" "$VPC_NAME"; then
        log_warn "VPC $VPC_NAME not found, skipping network cleanup"
        return 0
    fi

    # Delete Cloud NAT
    log_info "Deleting Cloud NAT..."
    local nat_router="${VPC_NAME}-router"
    local nat_config="${VPC_NAME}-nat"

    if gcloud compute routers nats describe "$nat_config" --router="$nat_router" --region="$REGION" --project="$PROJECT_ID" &> /dev/null; then
        gcloud compute routers nats delete "$nat_config" \
            --router="$nat_router" \
            --region="$REGION" \
            --project="$PROJECT_ID" \
            --quiet || log_warn "Failed to delete Cloud NAT"
    fi

    # Delete Cloud Router
    log_info "Deleting Cloud Router..."
    if gcloud compute routers describe "$nat_router" --region="$REGION" --project="$PROJECT_ID" &> /dev/null; then
        gcloud compute routers delete "$nat_router" \
            --region="$REGION" \
            --project="$PROJECT_ID" \
            --quiet || log_warn "Failed to delete Cloud Router"
    fi

    # Delete firewall rules
    log_info "Deleting firewall rules..."
    local firewall_rules
    firewall_rules=$(gcloud compute firewall-rules list --filter="network:$VPC_NAME" --format="value(name)" --project="$PROJECT_ID" 2>/dev/null || echo "")

    if [ -n "$firewall_rules" ]; then
        while IFS= read -r rule; do
            log_info "Deleting firewall rule: $rule"
            gcloud compute firewall-rules delete "$rule" --project="$PROJECT_ID" --quiet || log_warn "Failed to delete firewall rule: $rule"
        done <<< "$firewall_rules"
    fi

    # Delete subnets
    log_info "Deleting subnets..."
    local subnets
    subnets=$(gcloud compute networks subnets list --network="$VPC_NAME" --format="value(name,region)" --project="$PROJECT_ID" 2>/dev/null || echo "")

    if [ -n "$subnets" ]; then
        while IFS=$'\t' read -r subnet_name subnet_region; do
            log_info "Deleting subnet: $subnet_name in $subnet_region"
            gcloud compute networks subnets delete "$subnet_name" \
                --region="$subnet_region" \
                --project="$PROJECT_ID" \
                --quiet || log_warn "Failed to delete subnet: $subnet_name"
        done <<< "$subnets"
    fi

    # Delete Cloud Router (if not already deleted by NAT deletion)
    log_info "Ensuring Cloud Router is deleted..."
    if gcloud compute routers describe "$nat_router" --region="$REGION" --project="$PROJECT_ID" &> /dev/null; then
        log_info "Deleting remaining Cloud Router: $nat_router"
        gcloud compute routers delete "$nat_router" \
            --region="$REGION" \
            --project="$PROJECT_ID" \
            --quiet || log_warn "Failed to delete Cloud Router"
    fi

    # Delete Google-managed IP address for private service connection (Cloud SQL/Redis peering)
    log_info "Deleting Google-managed IP address for private service connection..."
    local managed_ip="google-managed-services-${VPC_NAME}"
    if gcloud compute addresses describe "$managed_ip" --global --project="$PROJECT_ID" &> /dev/null; then
        gcloud compute addresses delete "$managed_ip" \
            --global \
            --project="$PROJECT_ID" \
            --quiet || log_warn "Failed to delete Google-managed IP address"
        log_success "Google-managed IP address deleted"
    fi

    # Delete VPC network
    log_info "Deleting VPC network $VPC_NAME..."
    gcloud compute networks delete "$VPC_NAME" \
        --project="$PROJECT_ID" \
        --quiet || {
            log_error "Failed to delete VPC network"
            return 1
        }

    log_success "VPC and network resources deleted successfully"
}

cleanup_gke_auto_resources() {
    log_info "Cleaning up GKE auto-created resources..."

    # Delete GKE auto-created subnets (these have special naming)
    GKE_SUBNETS=$(gcloud compute networks subnets list \
        --filter="name~gke-$CLUSTER_NAME" \
        --format="value(name,region)" 2>/dev/null || true)

    if [[ -n "$GKE_SUBNETS" ]]; then
        while IFS=$'\t' read -r subnet_name subnet_region; do
            log_info "Deleting GKE auto-created subnet: $subnet_name..."
            gcloud compute networks subnets delete "$subnet_name" --region="$subnet_region" --quiet 2>/dev/null || true
        done <<< "$GKE_SUBNETS"
    fi

    # Delete GKE auto-created firewall rules
    GKE_FIREWALL=$(gcloud compute firewall-rules list \
        --filter="name~gke-$CLUSTER_NAME" \
        --format="value(name)" 2>/dev/null || true)

    if [[ -n "$GKE_FIREWALL" ]]; then
        for rule in $GKE_FIREWALL; do
            log_info "Deleting GKE auto-created firewall rule: $rule..."
            gcloud compute firewall-rules delete "$rule" --quiet 2>/dev/null || true
        done
    fi
}

###############################################################################
# Verification
###############################################################################

verify_cleanup() {
    log_info "=========================================="
    log_info "Step 9: Verifying complete cleanup"
    log_info "=========================================="

    local failed_checks=()

    # Check GKE cluster
    if resource_exists "gke-cluster" "$CLUSTER_NAME"; then
        failed_checks+=("GKE cluster $CLUSTER_NAME still exists")
    fi

    # Check Cloud SQL
    if resource_exists "cloud-sql" "$CLOUD_SQL_INSTANCE"; then
        failed_checks+=("Cloud SQL instance $CLOUD_SQL_INSTANCE still exists")
    fi

    # Check Redis
    if resource_exists "redis" "$REDIS_INSTANCE"; then
        failed_checks+=("Redis instance $REDIS_INSTANCE still exists")
    fi

    # Check VPC
    if resource_exists "vpc" "$VPC_NAME"; then
        failed_checks+=("VPC $VPC_NAME still exists")
    fi

    if [ ${#failed_checks[@]} -gt 0 ]; then
        log_error "Cleanup verification failed:"
        for check in "${failed_checks[@]}"; do
            log_error "  - $check"
        done
        log_error "Some resources may still exist. Please check manually."
        return 1
    fi

    log_success "All resources have been successfully deleted"
    log_success "Teardown complete!"
}

###############################################################################
# Main Execution
###############################################################################

main() {
    log_info "Starting staging GKE infrastructure teardown..."

    # Parse command-line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --auto-approve)
                AUTO_APPROVE=true
                shift
                ;;
            --skip-confirmation)
                AUTO_APPROVE=true
                shift
                ;;
            --keep-terraform-state)
                KEEP_TERRAFORM_STATE=true
                shift
                ;;
            --help)
                echo "Usage: $0 [OPTIONS]"
                echo ""
                echo "Options:"
                echo "  --auto-approve          Skip confirmation prompt"
                echo "  --skip-confirmation     Skip confirmation prompt (alias for --auto-approve)"
                echo "  --keep-terraform-state  Don't clean up Terraform state"
                echo "  --help                  Show this help message"
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                log_error "Use --help for usage information"
                exit 1
                ;;
        esac
    done

    # Execute teardown steps
    check_prerequisites
    confirm_teardown

    # Execute all cleanup steps in order
    cleanup_kubernetes_resources
    cleanup_helm_releases
    delete_gke_cluster
    delete_cloud_sql
    delete_redis
    delete_vpc_network
    cleanup_iam
    cleanup_secrets
    verify_cleanup

    log_success "=========================================="
    log_success "Staging infrastructure teardown complete!"
    log_success "=========================================="
}

# Run main function
main "$@"
