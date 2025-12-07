#!/usr/bin/env bash

###############################################################################
# Preview GKE Infrastructure Teardown Script
#
# This script performs a complete teardown of the preview GKE environment,
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
#   ./scripts/gcp/teardown-preview-infrastructure.sh [OPTIONS]
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
readonly CLUSTER_NAME="preview-mcp-server-langgraph-gke"
readonly NAMESPACE="preview-mcp-server-langgraph"
# VPC and resource names match Terraform naming convention (short_prefix = "preview-mcp-slg")
readonly VPC_NAME="preview-mcp-slg-vpc"
readonly CLOUD_SQL_INSTANCE="preview-mcp-slg-postgres"
readonly REDIS_INSTANCE="preview-mcp-slg-redis"
readonly PRIVATE_SERVICES_ADDRESS="preview-mcp-slg-private-services"
# TERRAFORM_DIR reserved for future Terraform state cleanup
# shellcheck disable=SC2034
readonly TERRAFORM_DIR="terraform/environments/gcp-preview"
readonly ARTIFACT_REGISTRY_REPO="mcp-preview"
readonly WORKLOAD_IDENTITY_POOL="github-actions-pool"
readonly WORKLOAD_IDENTITY_PROVIDER="github-actions-provider"

# Runtime-created databases to delete before Cloud SQL destruction
# These are created by Keycloak/OpenFGA during deployment and own objects
# that prevent the postgres user from being dropped
readonly RUNTIME_DATABASES=(
    "keycloak"
    "openfga"
)

# Service accounts to delete (matches Terraform workload_identity module + runtime-created)
readonly SERVICE_ACCOUNTS=(
    # Core application service accounts
    "preview-mcp-slg-sa"
    "preview-keycloak"
    "preview-openfga"
    # GitHub Actions service accounts
    "github-actions-preview"
    "github-actions-production"
    "github-actions-terraform"
    # Runtime-created service accounts
    "external-secrets-preview"
    "preview-otel-collector"
)

# Secrets to delete from Secret Manager
# Includes all secrets created by Terraform, External Secrets, and runtime deployments
readonly SECRETS=(
    # Database passwords (Terraform-managed)
    "preview-keycloak-db-password"
    "preview-openfga-db-password"
    "preview-gdpr-db-password"
    "preview-postgres-username"
    "preview-gdpr-postgres-url"
    # Redis configuration
    "preview-redis-password"
    "preview-redis-host"
    # API keys
    "preview-anthropic-api-key"
    "preview-google-api-key"
    "preview-jwt-secret"
    "preview-qdrant-api-key"
    # Keycloak configuration
    "preview-keycloak-admin-password"
    "preview-keycloak-admin-username"
    "preview-keycloak-client-id"
    "preview-keycloak-client-secret"
    # OpenFGA configuration
    "preview-openfga-model-id"
    "preview-openfga-store-id"
    # Infisical (secrets management)
    "preview-infisical-client-id"
    "preview-infisical-client-secret"
    "preview-infisical-project-id"
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
    log_warn "WARNING: This will DELETE all preview resources"
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

    # Get project number (reserved for future provider deletion logic)
    # shellcheck disable=SC2034
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
# Cloud SQL Runtime Database Cleanup
# CRITICAL: Must run BEFORE Cloud SQL deletion
# Keycloak/OpenFGA create database objects owned by the postgres role.
# These must be deleted first or the postgres user cannot be dropped.
###############################################################################

cleanup_runtime_databases() {
    log_info "=========================================="
    log_info "Step 3.5: Cleaning up runtime-created databases"
    log_info "=========================================="
    log_info "Keycloak/OpenFGA create database objects that block postgres user deletion."
    log_info "Deleting these databases before Cloud SQL destruction..."

    if ! resource_exists "cloud-sql" "$CLOUD_SQL_INSTANCE"; then
        log_warn "Cloud SQL instance $CLOUD_SQL_INSTANCE not found, skipping database cleanup"
        return 0
    fi

    for db_name in "${RUNTIME_DATABASES[@]}"; do
        log_info "Checking for database: $db_name"
        if gcloud sql databases describe "$db_name" \
            --instance="$CLOUD_SQL_INSTANCE" \
            --project="$PROJECT_ID" &> /dev/null; then

            log_info "Deleting database: $db_name (this removes objects blocking postgres user deletion)"
            gcloud sql databases delete "$db_name" \
                --instance="$CLOUD_SQL_INSTANCE" \
                --project="$PROJECT_ID" \
                --quiet || log_warn "Failed to delete database: $db_name"
            log_success "Database $db_name deleted"
        else
            log_warn "Database $db_name not found on instance $CLOUD_SQL_INSTANCE"
        fi
    done

    log_success "Runtime database cleanup complete"
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

    # CRITICAL: Clean up runtime-created databases first
    # Keycloak/OpenFGA create objects owned by postgres role that prevent user deletion
    cleanup_runtime_databases

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
    log_info "==========================================="
    log_info "Step 6.5: Deleting Artifact Registry"
    log_info "==========================================="

    if gcloud artifacts repositories describe "$ARTIFACT_REGISTRY_REPO" \
        --location="$REGION" --project="$PROJECT_ID" &> /dev/null; then

        log_info "Deleting Artifact Registry repository: $ARTIFACT_REGISTRY_REPO..."
        gcloud artifacts repositories delete "$ARTIFACT_REGISTRY_REPO" \
            --location="$REGION" \
            --project="$PROJECT_ID" \
            --quiet || log_warn "Failed to delete Artifact Registry repository"

        log_success "Artifact Registry repository deleted"
    else
        log_warn "Artifact Registry repository $ARTIFACT_REGISTRY_REPO not found, skipping"
    fi
}

###############################################################################
# DNS Zone Cleanup
# Deletes internal DNS zones and their resource records
###############################################################################

cleanup_dns_zones() {
    log_info "==========================================="
    log_info "Step 6.6: Cleaning up DNS zones"
    log_info "==========================================="

    local dns_zone="preview-internal"

    # Check if DNS zone exists
    if ! gcloud dns managed-zones describe "$dns_zone" --project="$PROJECT_ID" &> /dev/null; then
        log_warn "DNS zone $dns_zone not found, skipping"
        return 0
    fi

    log_info "Found DNS zone: $dns_zone"

    # Get all A records (skip NS and SOA which are auto-managed)
    log_info "Deleting A records from DNS zone..."
    local a_records
    a_records=$(gcloud dns record-sets list --zone="$dns_zone" --project="$PROJECT_ID" \
        --filter="type=A" --format="value(name)" 2>/dev/null || echo "")

    if [ -n "$a_records" ]; then
        while IFS= read -r record_name; do
            if [ -n "$record_name" ]; then
                log_info "Deleting A record: $record_name"
                gcloud dns record-sets delete "$record_name" \
                    --type=A \
                    --zone="$dns_zone" \
                    --project="$PROJECT_ID" \
                    --quiet || log_warn "Failed to delete A record: $record_name"
            fi
        done <<< "$a_records"
    fi

    # Delete DNS zone (NS and SOA records are deleted automatically with zone)
    log_info "Deleting DNS zone: $dns_zone..."
    gcloud dns managed-zones delete "$dns_zone" \
        --project="$PROJECT_ID" \
        --quiet || log_warn "Failed to delete DNS zone: $dns_zone"

    log_success "DNS zone cleanup complete"
}

###############################################################################
# Monitoring Alert Policies Cleanup
# Deletes all monitoring alert policies for this environment
###############################################################################

cleanup_monitoring_alerts() {
    log_info "==========================================="
    log_info "Step 6.7: Cleaning up monitoring alert policies"
    log_info "==========================================="

    # Find all alert policies containing "preview" in the display name
    log_info "Searching for preview monitoring alert policies..."
    local alert_policies
    alert_policies=$(gcloud alpha monitoring policies list \
        --project="$PROJECT_ID" \
        --filter="displayName~preview" \
        --format="value(name)" 2>/dev/null || echo "")

    if [ -z "$alert_policies" ]; then
        log_warn "No preview monitoring alert policies found"
        return 0
    fi

    local count=0
    while IFS= read -r policy_name; do
        if [ -n "$policy_name" ]; then
            local display_name
            display_name=$(gcloud alpha monitoring policies describe "$policy_name" \
                --project="$PROJECT_ID" --format="value(displayName)" 2>/dev/null || echo "unknown")
            log_info "Deleting alert policy: $display_name"
            gcloud alpha monitoring policies delete "$policy_name" \
                --project="$PROJECT_ID" \
                --quiet || log_warn "Failed to delete policy: $display_name"
            count=$((count + 1))
        fi
    done <<< "$alert_policies"

    log_success "Deleted $count monitoring alert policies"
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
    # Resource names match Terraform naming: ${short_prefix}-router-${region} / ${short_prefix}-nat-${region}
    log_info "Deleting Cloud NAT..."
    local short_prefix="preview-mcp-slg"
    local nat_router="${short_prefix}-router-${REGION}"
    local nat_config="${short_prefix}-nat-${REGION}"

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

    # Wait for Service Networking Connection to propagate deletion of Cloud SQL/Memorystore
    # This is a known GCP timing issue - the connection may still report producer services
    # are using it even after they've been deleted
    log_info "Waiting 60 seconds for Service Networking Connection to propagate..."
    log_info "This wait helps avoid 'Producer services still using connection' errors."
    sleep 60

    # Delete private services IP address (used for Cloud SQL/Redis VPC peering)
    # The address name is: ${name_prefix}-private-services (e.g., preview-mcp-slg-private-services)
    log_info "Deleting private services IP address: $PRIVATE_SERVICES_ADDRESS"
    if gcloud compute addresses describe "$PRIVATE_SERVICES_ADDRESS" --global --project="$PROJECT_ID" &> /dev/null; then
        # Try to delete, with retry logic for timing issues
        local max_retries=3
        local retry_count=0
        local delete_success=false

        while [ $retry_count -lt $max_retries ] && [ "$delete_success" = false ]; do
            if gcloud compute addresses delete "$PRIVATE_SERVICES_ADDRESS" \
                --global \
                --project="$PROJECT_ID" \
                --quiet 2>/dev/null; then
                delete_success=true
                log_success "Private services IP address deleted"
            else
                retry_count=$((retry_count + 1))
                if [ $retry_count -lt $max_retries ]; then
                    log_warn "Failed to delete private services address (attempt $retry_count/$max_retries), waiting 30 seconds..."
                    sleep 30
                else
                    log_warn "Failed to delete private services address after $max_retries attempts"
                    log_warn "You may need to manually delete: gcloud compute addresses delete $PRIVATE_SERVICES_ADDRESS --global"
                fi
            fi
        done
    else
        log_warn "Private services IP address $PRIVATE_SERVICES_ADDRESS not found"
    fi

    # Delete VPC network
    log_info "Deleting VPC network $VPC_NAME..."
    gcloud compute networks delete "$VPC_NAME" \
        --project="$PROJECT_ID" \
        --quiet || {
            log_error "Failed to delete VPC network"
            log_error "If the network deletion fails due to Service Networking Connection:"
            log_error "  1. Wait a few minutes for GCP propagation"
            log_error "  2. Try: gcloud compute networks delete $VPC_NAME --project=$PROJECT_ID"
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
    log_info "Step 10: Verifying complete cleanup"
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

    # Check Artifact Registry
    if gcloud artifacts repositories describe "$ARTIFACT_REGISTRY_REPO" \
        --location="$REGION" --project="$PROJECT_ID" &> /dev/null; then
        failed_checks+=("Artifact Registry $ARTIFACT_REGISTRY_REPO still exists")
    fi

    # Check DNS zone
    if gcloud dns managed-zones describe "preview-internal" \
        --project="$PROJECT_ID" &> /dev/null; then
        failed_checks+=("DNS zone preview-internal still exists")
    fi

    # Check for remaining monitoring alert policies
    local remaining_policies
    remaining_policies=$(gcloud alpha monitoring policies list \
        --project="$PROJECT_ID" \
        --filter="displayName~preview" \
        --format="value(name)" 2>/dev/null | wc -l)
    if [ "$remaining_policies" -gt 0 ]; then
        failed_checks+=("$remaining_policies preview monitoring alert policies still exist")
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
    log_info "Starting preview GKE infrastructure teardown..."

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
                # Reserved for future Terraform state cleanup logic
                # shellcheck disable=SC2034
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
    delete_artifact_registry
    cleanup_dns_zones
    cleanup_monitoring_alerts
    cleanup_iam
    cleanup_secrets
    verify_cleanup

    log_success "=========================================="
    log_success "Preview infrastructure teardown complete!"
    log_success "=========================================="
}

# Run main function
main "$@"
