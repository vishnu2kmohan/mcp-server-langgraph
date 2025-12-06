#!/usr/bin/env bash

###############################################################################
# GKE Preview Environment - Teardown Script
#
# Single-command teardown of the complete GKE preview environment:
# - Kubernetes workloads
# - GKE Autopilot cluster
# - Cloud SQL PostgreSQL
# - Memorystore Redis
# - VPC networking
# - IAM resources
# - Secret Manager secrets
# - Orphaned resources (DNS zones, monitoring alerts, Artifact Registry)
#
# Features:
# - Uses Terraform for state-aware destruction
# - Comprehensive orphan cleanup
# - Verification of complete cleanup
# - Safe defaults (requires confirmation)
#
# Prerequisites:
# - gcloud CLI installed and authenticated
# - terraform >= 1.5.0 installed
# - kubectl installed
# - jq installed
#
# Usage:
#   ./scripts/gcp/gke-preview-down.sh [OPTIONS]
#
# Options:
#   --project PROJECT_ID   GCP project ID (default: vishnu-sandbox-20250310)
#   --region REGION        GCP region (default: us-central1)
#   --terraform-only       Only run Terraform destroy (skip orphan cleanup)
#   --orphans-only         Only cleanup orphans (skip Terraform)
#   --auto-approve         Skip confirmation prompts
#   --help                 Show help message
#
# Environment Variables:
#   GCP_PROJECT_ID         GCP project ID (alternative to --project)
#   GCP_REGION             GCP region (alternative to --region)
#
# Examples:
#   # Teardown with defaults (vishnu-sandbox-20250310)
#   ./scripts/gcp/gke-preview-down.sh
#
#   # Teardown your own project
#   ./scripts/gcp/gke-preview-down.sh --project my-project-id
#
#   # Non-interactive (for CI/CD)
#   ./scripts/gcp/gke-preview-down.sh --auto-approve
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

# Get project root (used for Terraform paths)
PROJECT_ROOT="$(get_project_root)"
export PROJECT_ROOT  # Used by Terraform commands

# Default values (can be overridden by flags or env vars)
PROJECT_ID="${GCP_PROJECT_ID:-$DEFAULT_PROJECT_ID}"
REGION="${GCP_REGION:-$DEFAULT_REGION}"
NAMESPACE="$DEFAULT_NAMESPACE"
export NAMESPACE  # Used for kubectl commands

# Resource names (match Terraform naming)
CLUSTER_NAME="preview-mcp-server-langgraph-gke"
SHORT_PREFIX="preview-mcp-slg"
CLOUD_SQL_INSTANCE="${SHORT_PREFIX}-postgres"
REDIS_INSTANCE="${SHORT_PREFIX}-redis"
VPC_NAME="${SHORT_PREFIX}-vpc"

# Flags
TERRAFORM_ONLY=false
ORPHANS_ONLY=false
AUTO_APPROVE=false

###############################################################################
# Help
###############################################################################

show_help() {
    cat << EOF
GKE Preview Environment - Teardown Script

Completely teardown the GKE preview environment with a single command.

USAGE:
    $(basename "$0") [OPTIONS]

OPTIONS:
    --project PROJECT_ID   GCP project ID (default: $DEFAULT_PROJECT_ID)
    --region REGION        GCP region (default: $DEFAULT_REGION)
    --terraform-only       Only run Terraform destroy (skip orphan cleanup)
    --orphans-only         Only cleanup orphans (skip Terraform)
    --auto-approve         Skip confirmation prompts
    --help                 Show this help message

ENVIRONMENT VARIABLES:
    GCP_PROJECT_ID         GCP project ID (alternative to --project)
    GCP_REGION             GCP region (alternative to --region)

EXAMPLES:
    # Teardown with defaults
    $(basename "$0")

    # Teardown your own project
    $(basename "$0") --project my-project-id

    # Non-interactive teardown (for CI/CD)
    $(basename "$0") --auto-approve

    # Only cleanup orphaned resources
    $(basename "$0") --orphans-only

WHAT THIS DELETES:
    - GKE Autopilot cluster and all workloads
    - Cloud SQL PostgreSQL instance
    - Memorystore Redis instance
    - VPC, subnets, Cloud NAT, firewall rules
    - IAM service accounts
    - Secret Manager secrets
    - DNS zones and records
    - Monitoring alert policies
    - Artifact Registry repository

ESTIMATED TIME:
    - Terraform destroy: 10-15 minutes
    - Orphan cleanup: 2-5 minutes
    - Total: ~15-20 minutes

WARNING:
    This action is IRREVERSIBLE. All data will be lost.
    Ensure you have backups if needed.

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
            --terraform-only)
                TERRAFORM_ONLY=true
                shift
                ;;
            --orphans-only)
                ORPHANS_ONLY=true
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
    check_gcp_auth || exit 1

    # Set project
    set_gcp_project "$PROJECT_ID" || exit 1

    log_success "Pre-flight checks passed"
}

###############################################################################
# Resource Listing
###############################################################################

list_resources() {
    log_step "Scanning for existing resources..."

    local found_resources=()

    # Check GKE cluster
    if check_resource_exists "gke-cluster" "$CLUSTER_NAME" "$PROJECT_ID" "$REGION"; then
        found_resources+=("GKE Cluster: $CLUSTER_NAME")
    fi

    # Check Cloud SQL
    if check_resource_exists "cloud-sql" "$CLOUD_SQL_INSTANCE" "$PROJECT_ID"; then
        found_resources+=("Cloud SQL: $CLOUD_SQL_INSTANCE")
    fi

    # Check Redis
    if check_resource_exists "redis" "$REDIS_INSTANCE" "$PROJECT_ID" "$REGION"; then
        found_resources+=("Memorystore Redis: $REDIS_INSTANCE")
    fi

    # Check VPC
    if check_resource_exists "vpc" "$VPC_NAME" "$PROJECT_ID"; then
        found_resources+=("VPC Network: $VPC_NAME")
    fi

    # Check Artifact Registry
    if gcloud artifacts repositories describe "mcp-preview" \
        --location="$REGION" --project="$PROJECT_ID" &> /dev/null; then
        found_resources+=("Artifact Registry: mcp-preview")
    fi

    # Check DNS Zone
    if gcloud dns managed-zones describe "preview-internal" \
        --project="$PROJECT_ID" &> /dev/null; then
        found_resources+=("DNS Zone: preview-internal")
    fi

    # Check monitoring alerts
    local alert_count
    alert_count=$(gcloud alpha monitoring policies list \
        --project="$PROJECT_ID" \
        --filter="displayName~preview" \
        --format="value(name)" 2>/dev/null | wc -l || echo "0")
    if [ "$alert_count" -gt 0 ]; then
        found_resources+=("Monitoring Alerts: $alert_count policies")
    fi

    if [ ${#found_resources[@]} -eq 0 ]; then
        log_warn "No preview resources found in project $PROJECT_ID"
        return 1
    fi

    echo ""
    echo "Resources to be deleted:"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    for resource in "${found_resources[@]}"; do
        echo "  • $resource"
    done
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""

    return 0
}

###############################################################################
# Confirmation
###############################################################################

confirm_teardown() {
    if [ "$AUTO_APPROVE" = true ]; then
        log_warn "Auto-approve enabled, skipping confirmation"
        return 0
    fi

    echo -e "${RED}${BOLD}"
    echo "╔════════════════════════════════════════════════════════════════╗"
    echo "║                     ⚠️  WARNING ⚠️                              ║"
    echo "║                                                                ║"
    echo "║  This will PERMANENTLY DELETE all preview environment         ║"
    echo "║  resources. This action CANNOT be undone.                     ║"
    echo "║                                                                ║"
    echo "║  Project: $PROJECT_ID"
    echo "║                                                                ║"
    echo "╚════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"

    echo ""
    echo -e "Type '${BOLD}yes${NC}' to confirm deletion: "
    read -r confirmation

    if [ "$confirmation" != "yes" ]; then
        log_info "Teardown cancelled"
        exit 0
    fi

    log_info "Teardown confirmed, proceeding..."
}

###############################################################################
# Terraform Destroy
###############################################################################

# Retry logic for Service Networking Connection deletion
# GCP Service Networking has eventual consistency - after CloudSQL/Redis deletion,
# the connection can take 2-5 minutes to fully release (Issue #3 in known issues doc)
SERVICE_NETWORKING_MAX_RETRIES=3
SERVICE_NETWORKING_RETRY_DELAY=120  # 2 minutes

cleanup_service_networking_with_gcloud() {
    log_warn "Attempting direct gcloud cleanup of service networking resources..."

    # Try to delete the VPC peering directly
    if gcloud compute networks peerings list \
        --network="$VPC_NAME" \
        --project="$PROJECT_ID" 2>/dev/null | grep -q "servicenetworking-googleapis-com"; then

        log_substep "Deleting VPC peering: servicenetworking-googleapis-com"
        if gcloud compute networks peerings delete servicenetworking-googleapis-com \
            --network="$VPC_NAME" \
            --project="$PROJECT_ID" \
            --quiet 2>/dev/null; then
            log_success "VPC peering deleted via gcloud"
            return 0
        else
            log_warn "Failed to delete VPC peering via gcloud"
        fi
    fi

    # Try the vpc-peerings delete command
    log_substep "Attempting service networking connection delete..."
    if gcloud services vpc-peerings delete \
        --network="$VPC_NAME" \
        --service=servicenetworking.googleapis.com \
        --project="$PROJECT_ID" \
        --quiet 2>/dev/null; then
        log_success "Service networking connection deleted via gcloud"
        return 0
    else
        log_warn "Failed to delete service networking connection via gcloud"
    fi

    return 1
}

remove_service_networking_from_state() {
    local tf_dir="$1"

    log_warn "Removing service networking resources from Terraform state..."

    # Remove service networking connection from state
    terraform -chdir="$tf_dir" state rm \
        'module.vpc.google_service_networking_connection.private_services[0]' 2>/dev/null || true

    # Remove peering routes config from state
    terraform -chdir="$tf_dir" state rm \
        'module.vpc.google_compute_network_peering_routes_config.private_services_dns[0]' 2>/dev/null || true

    # Remove global address from state
    terraform -chdir="$tf_dir" state rm \
        'module.vpc.google_compute_global_address.private_services[0]' 2>/dev/null || true

    log_info "Service networking resources removed from Terraform state"
}

terraform_destroy() {
    if [ "$ORPHANS_ONLY" = true ]; then
        log_warn "Skipping Terraform destroy (--orphans-only)"
        return 0
    fi

    log_step "Destroying infrastructure with Terraform..."

    local tf_dir
    tf_dir=$(get_terraform_dir)

    # Check if Terraform is initialized
    if ! check_terraform_state; then
        log_warn "Terraform state not found"
        log_info "Running legacy teardown script instead..."
        if [ -x "$SCRIPT_DIR/teardown-preview-infrastructure.sh" ]; then
            if [ "$AUTO_APPROVE" = true ]; then
                "$SCRIPT_DIR/teardown-preview-infrastructure.sh" --auto-approve
            else
                "$SCRIPT_DIR/teardown-preview-infrastructure.sh"
            fi
        else
            log_error "Legacy teardown script not found"
            return 1
        fi
        return 0
    fi

    # Initialize if needed
    terraform_init_if_needed

    # Run Terraform destroy with retry logic for service networking issues
    log_substep "Running terraform destroy..."

    local destroy_output
    local retry_count=0

    while [ $retry_count -lt $SERVICE_NETWORKING_MAX_RETRIES ]; do
        # Capture output for error detection
        destroy_output=$(mktemp)

        if [ "$AUTO_APPROVE" = true ]; then
            if terraform -chdir="$tf_dir" destroy \
                -auto-approve \
                -var="project_id=$PROJECT_ID" \
                -var="region=$REGION" \
                -no-color 2>&1 | tee "$destroy_output"; then
                rm -f "$destroy_output"
                log_success "Terraform destroy complete"
                return 0
            fi
        else
            if terraform -chdir="$tf_dir" destroy \
                -var="project_id=$PROJECT_ID" \
                -var="region=$REGION" \
                -no-color 2>&1 | tee "$destroy_output"; then
                rm -f "$destroy_output"
                log_success "Terraform destroy complete"
                return 0
            fi
        fi

        # Check if the failure was due to service networking connection
        if grep -q "Failed to delete connection\|Producer services.*still using this connection\|Error code 9" "$destroy_output" 2>/dev/null; then
            retry_count=$((retry_count + 1))

            if [ $retry_count -lt $SERVICE_NETWORKING_MAX_RETRIES ]; then
                log_warn "Service Networking Connection not ready for deletion (retry $retry_count/$SERVICE_NETWORKING_MAX_RETRIES)"
                log_info "GCP eventual consistency: waiting ${SERVICE_NETWORKING_RETRY_DELAY}s for connection to release..."
                sleep $SERVICE_NETWORKING_RETRY_DELAY
            else
                log_warn "Service Networking Connection deletion failed after $SERVICE_NETWORKING_MAX_RETRIES retries"

                # Fallback: Try gcloud direct cleanup
                log_info "Attempting fallback cleanup with gcloud..."

                # Remove problematic resources from state first
                remove_service_networking_from_state "$tf_dir"

                # Try gcloud cleanup
                cleanup_service_networking_with_gcloud || true

                # Try one more terraform destroy to clean up remaining resources
                log_substep "Running final terraform destroy for remaining resources..."
                if [ "$AUTO_APPROVE" = true ]; then
                    terraform -chdir="$tf_dir" destroy \
                        -auto-approve \
                        -var="project_id=$PROJECT_ID" \
                        -var="region=$REGION" \
                        -no-color || true
                else
                    terraform -chdir="$tf_dir" destroy \
                        -var="project_id=$PROJECT_ID" \
                        -var="region=$REGION" \
                        -no-color || true
                fi

                log_warn "Terraform destroy completed with warnings (service networking cleanup deferred)"
                rm -f "$destroy_output"
                return 0
            fi
        else
            # Different error - not retryable
            log_error "Terraform destroy failed with non-retryable error"
            cat "$destroy_output"
            rm -f "$destroy_output"
            return 1
        fi

        rm -f "$destroy_output"
    done

    log_success "Terraform destroy complete"
}

###############################################################################
# Orphan Cleanup
###############################################################################

cleanup_orphans() {
    if [ "$TERRAFORM_ONLY" = true ]; then
        log_warn "Skipping orphan cleanup (--terraform-only)"
        return 0
    fi

    log_step "Cleaning up orphaned resources..."

    # Cleanup Artifact Registry
    cleanup_artifact_registry

    # Cleanup DNS zones
    cleanup_dns_zones

    # Cleanup monitoring alerts
    cleanup_monitoring_alerts

    log_success "Orphan cleanup complete"
}

cleanup_artifact_registry() {
    log_substep "Checking Artifact Registry..."

    local repo_name="mcp-preview"

    if gcloud artifacts repositories describe "$repo_name" \
        --location="$REGION" --project="$PROJECT_ID" &> /dev/null; then

        log_substep "Deleting Artifact Registry: $repo_name"
        gcloud artifacts repositories delete "$repo_name" \
            --location="$REGION" \
            --project="$PROJECT_ID" \
            --quiet || log_warn "Failed to delete Artifact Registry"
        log_success "Artifact Registry deleted"
    else
        log_info "Artifact Registry not found (already deleted)"
    fi
}

cleanup_dns_zones() {
    log_substep "Checking DNS zones..."

    local dns_zone="preview-internal"

    if ! gcloud dns managed-zones describe "$dns_zone" \
        --project="$PROJECT_ID" &> /dev/null; then
        log_info "DNS zone not found (already deleted)"
        return 0
    fi

    log_substep "Deleting DNS zone: $dns_zone"

    # Must delete A records before deleting zone
    log_info "Deleting A records from DNS zone..."
    local a_records
    a_records=$(gcloud dns record-sets list --zone="$dns_zone" --project="$PROJECT_ID" \
        --filter="type=A" --format="value(name)" 2>/dev/null || echo "")

    if [ -n "$a_records" ]; then
        while IFS= read -r record_name; do
            if [ -n "$record_name" ]; then
                log_info "  Deleting A record: $record_name"
                gcloud dns record-sets delete "$record_name" \
                    --type=A \
                    --zone="$dns_zone" \
                    --project="$PROJECT_ID" \
                    --quiet || log_warn "Failed to delete A record: $record_name"
            fi
        done <<< "$a_records"
    fi

    # Delete the zone
    gcloud dns managed-zones delete "$dns_zone" \
        --project="$PROJECT_ID" \
        --quiet || log_warn "Failed to delete DNS zone"

    log_success "DNS zone deleted"
}

cleanup_monitoring_alerts() {
    log_substep "Checking monitoring alert policies..."

    local alert_policies
    alert_policies=$(gcloud alpha monitoring policies list \
        --project="$PROJECT_ID" \
        --filter="displayName~preview" \
        --format="value(name)" 2>/dev/null || echo "")

    if [ -z "$alert_policies" ]; then
        log_info "No monitoring alert policies found"
        return 0
    fi

    log_substep "Deleting monitoring alert policies..."

    local count=0
    while IFS= read -r policy_name; do
        if [ -n "$policy_name" ]; then
            local display_name
            display_name=$(gcloud alpha monitoring policies describe "$policy_name" \
                --project="$PROJECT_ID" --format="value(displayName)" 2>/dev/null || echo "unknown")
            log_info "  Deleting: $display_name"
            gcloud alpha monitoring policies delete "$policy_name" \
                --project="$PROJECT_ID" \
                --quiet || log_warn "Failed to delete policy: $display_name"
            count=$((count + 1))
        fi
    done <<< "$alert_policies"

    log_success "Deleted $count monitoring alert policies"
}

###############################################################################
# Verification
###############################################################################

verify_cleanup() {
    log_step "Verifying complete cleanup..."

    local remaining_resources=()

    # Check GKE cluster
    if check_resource_exists "gke-cluster" "$CLUSTER_NAME" "$PROJECT_ID" "$REGION"; then
        remaining_resources+=("GKE Cluster: $CLUSTER_NAME")
    fi

    # Check Cloud SQL
    if check_resource_exists "cloud-sql" "$CLOUD_SQL_INSTANCE" "$PROJECT_ID"; then
        remaining_resources+=("Cloud SQL: $CLOUD_SQL_INSTANCE")
    fi

    # Check Redis
    if check_resource_exists "redis" "$REDIS_INSTANCE" "$PROJECT_ID" "$REGION"; then
        remaining_resources+=("Memorystore Redis: $REDIS_INSTANCE")
    fi

    # Check VPC
    if check_resource_exists "vpc" "$VPC_NAME" "$PROJECT_ID"; then
        remaining_resources+=("VPC Network: $VPC_NAME")
    fi

    # Check Artifact Registry
    if gcloud artifacts repositories describe "mcp-preview" \
        --location="$REGION" --project="$PROJECT_ID" &> /dev/null; then
        remaining_resources+=("Artifact Registry: mcp-preview")
    fi

    # Check DNS Zone
    if gcloud dns managed-zones describe "preview-internal" \
        --project="$PROJECT_ID" &> /dev/null; then
        remaining_resources+=("DNS Zone: preview-internal")
    fi

    if [ ${#remaining_resources[@]} -gt 0 ]; then
        log_warn "Some resources may still exist:"
        for resource in "${remaining_resources[@]}"; do
            echo "  • $resource"
        done
        echo ""
        log_warn "You may need to manually delete these resources"
        return 1
    fi

    log_success "All resources have been successfully deleted"
    return 0
}

###############################################################################
# Success Message
###############################################################################

show_completion_message() {
    echo ""
    show_success_banner "GKE Preview Environment Teardown Complete!"

    echo ""
    echo "All preview environment resources have been deleted."
    echo ""
    echo "To recreate the environment:"
    echo "   ./scripts/gcp/gke-preview-up.sh"
    echo ""
    echo "Or using make:"
    echo "   make gke-preview-up"
    echo ""
}

###############################################################################
# Main
###############################################################################

main() {
    show_header "GKE Preview Environment Teardown" "Complete cleanup of preview infrastructure"

    # Parse command line arguments
    parse_args "$@"

    # Run pre-flight checks
    preflight_checks

    # List resources that will be deleted
    if ! list_resources; then
        show_success_banner "No resources to delete"
        exit 0
    fi

    # Confirm teardown
    confirm_teardown

    # Terraform destroy
    terraform_destroy

    # Cleanup orphans
    cleanup_orphans

    # Verify cleanup
    verify_cleanup || true

    # Show completion message
    show_completion_message

    log_success "Teardown complete!"
}

# Run main
main "$@"
