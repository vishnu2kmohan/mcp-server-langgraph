#!/bin/bash
#
# GCP Staging Infrastructure Teardown Script
#
# This script safely and thoroughly tears down the staging GKE environment including:
# - GKE Autopilot cluster
# - Workload Identity pool and providers
# - Service accounts and IAM bindings
# - VPC network and subnets
# - Cloud SQL instances
# - Memorystore Redis instances
# - Artifact Registry repositories
# - Secrets in Secret Manager
#
# Prerequisites:
# - gcloud CLI installed and authenticated
# - Proper permissions to delete resources
#
# Usage:
#   ./scripts/gcp/teardown-staging-infrastructure.sh [--skip-confirmation]
#

set -euo pipefail

# Configuration
PROJECT_ID="${GCP_PROJECT_ID:-vishnu-sandbox-20250310}"
REGION="us-central1"
ZONE="us-central1-a"
CLUSTER_NAME="mcp-staging-cluster"
VPC_NAME="staging-vpc"
SUBNET_NAME="staging-gke-subnet"
SERVICE_ACCOUNT_NAME="mcp-staging-sa"
WORKLOAD_IDENTITY_POOL="github-actions-pool"
WORKLOAD_IDENTITY_PROVIDER="github-provider"
ARTIFACT_REGISTRY_REPO="mcp-staging"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
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

confirm_teardown() {
    if [[ "${1:-}" == "--skip-confirmation" ]]; then
        return 0
    fi

    log_warn "⚠️  WARNING: This will delete all staging infrastructure!"
    log_warn "The following resources will be PERMANENTLY DELETED:"
    echo ""
    echo "  - GKE Cluster: $CLUSTER_NAME"
    echo "  - VPC Network: $VPC_NAME"
    echo "  - Service Account: $SERVICE_ACCOUNT_NAME"
    echo "  - Workload Identity Pool: $WORKLOAD_IDENTITY_POOL"
    echo "  - Artifact Registry: $ARTIFACT_REGISTRY_REPO"
    echo "  - Any associated Cloud SQL, Redis, and Secret Manager resources"
    echo ""
    read -p "Are you sure you want to continue? (type 'yes' to confirm): " confirmation

    if [[ "$confirmation" != "yes" ]]; then
        log_info "Teardown cancelled."
        exit 0
    fi
}

delete_gke_cluster() {
    log_info "Deleting GKE cluster..."

    if gcloud container clusters describe "$CLUSTER_NAME" --region="$REGION" &> /dev/null; then
        log_warn "Deleting cluster $CLUSTER_NAME (this may take 5-10 minutes)..."
        gcloud container clusters delete "$CLUSTER_NAME" \
            --region="$REGION" \
            --quiet

        log_info "GKE cluster deleted successfully"
    else
        log_warn "Cluster $CLUSTER_NAME not found, skipping"
    fi
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

delete_service_accounts() {
    log_info "Deleting service accounts..."

    SERVICE_ACCOUNT_EMAIL="${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

    if gcloud iam service-accounts describe "$SERVICE_ACCOUNT_EMAIL" &> /dev/null; then
        log_warn "Deleting service account $SERVICE_ACCOUNT_EMAIL..."
        gcloud iam service-accounts delete "$SERVICE_ACCOUNT_EMAIL" --quiet
        log_info "Service account deleted"
    else
        log_warn "Service account not found, skipping"
    fi
}

delete_cloud_sql() {
    log_info "Checking for Cloud SQL instances..."

    INSTANCES=$(gcloud sql instances list --filter="name~staging" --format="value(name)" 2>/dev/null || true)

    if [[ -n "$INSTANCES" ]]; then
        for instance in $INSTANCES; do
            log_warn "Deleting Cloud SQL instance: $instance..."
            gcloud sql instances delete "$instance" --quiet
            log_info "Cloud SQL instance $instance deleted"
        done
    else
        log_warn "No Cloud SQL instances found, skipping"
    fi
}

delete_redis() {
    log_info "Checking for Redis instances..."

    INSTANCES=$(gcloud redis instances list --region="$REGION" --filter="name~staging" --format="value(name)" 2>/dev/null || true)

    if [[ -n "$INSTANCES" ]]; then
        for instance in $INSTANCES; do
            log_warn "Deleting Redis instance: $instance..."
            gcloud redis instances delete "$instance" --region="$REGION" --quiet
            log_info "Redis instance $instance deleted"
        done
    else
        log_warn "No Redis instances found, skipping"
    fi
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

delete_secrets() {
    log_info "Checking for secrets in Secret Manager..."

    SECRETS=$(gcloud secrets list --filter="name~staging OR name~mcp" --format="value(name)" 2>/dev/null || true)

    if [[ -n "$SECRETS" ]]; then
        log_warn "Found secrets. Please review and delete manually if needed:"
        for secret in $SECRETS; do
            echo "  - $secret"
        done
        log_warn "Skipping automatic deletion to prevent accidental data loss"
    else
        log_info "No staging secrets found"
    fi
}

delete_vpc_network() {
    log_info "Deleting VPC network and subnets..."

    # Delete firewall rules first
    log_warn "Deleting firewall rules..."
    FIREWALL_RULES=$(gcloud compute firewall-rules list --filter="network:$VPC_NAME" --format="value(name)" 2>/dev/null || true)

    if [[ -n "$FIREWALL_RULES" ]]; then
        for rule in $FIREWALL_RULES; do
            log_info "Deleting firewall rule: $rule..."
            gcloud compute firewall-rules delete "$rule" --quiet
        done
    fi

    # Delete all subnets in the VPC
    log_warn "Deleting subnets..."
    SUBNETS=$(gcloud compute networks subnets list --filter="network:$VPC_NAME" --format="value(name,region)" 2>/dev/null || true)

    if [[ -n "$SUBNETS" ]]; then
        while IFS=$'\t' read -r subnet_name subnet_region; do
            log_info "Deleting subnet: $subnet_name in $subnet_region..."
            gcloud compute networks subnets delete "$subnet_name" --region="$subnet_region" --quiet
        done <<< "$SUBNETS"
    fi

    # Delete VPC network
    if gcloud compute networks describe "$VPC_NAME" &> /dev/null; then
        log_warn "Deleting VPC network: $VPC_NAME..."
        gcloud compute networks delete "$VPC_NAME" --quiet
        log_info "VPC network deleted"
    else
        log_warn "VPC network not found, skipping"
    fi
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

# Main execution
main() {
    log_info "Starting GCP Staging Infrastructure Teardown..."
    log_info "Project: $PROJECT_ID"
    log_info "Region: $REGION"

    # Set project
    gcloud config set project "$PROJECT_ID"

    # Confirm teardown
    confirm_teardown "$@"

    # Delete resources in order (dependencies first)
    delete_gke_cluster
    cleanup_gke_auto_resources
    delete_workload_identity
    delete_service_accounts
    delete_cloud_sql
    delete_redis
    delete_artifact_registry
    delete_secrets
    delete_vpc_network

    log_info "✅ Teardown completed successfully!"
    log_info ""
    log_info "Summary:"
    log_info "  - GKE cluster and auto-created resources removed"
    log_info "  - Workload Identity resources removed"
    log_info "  - Service accounts removed"
    log_info "  - VPC network and subnets removed"
    log_info "  - Cloud SQL and Redis instances removed (if any)"
    log_info "  - Artifact Registry repositories removed (if any)"
    log_info ""
    log_warn "Note: Secrets in Secret Manager were not deleted automatically."
    log_warn "Please review and delete manually if needed."
}

# Run main function
main "$@"
