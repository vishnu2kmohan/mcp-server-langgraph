#!/bin/bash
# Setup Cloud DNS for Staging Environment
# This script creates Cloud DNS zone and records for staging GKE deployment
#
# Usage:
#   ./scripts/setup-cloud-dns-staging.sh
#
# Prerequisites:
#   - gcloud CLI installed and authenticated
#   - Project set: gcloud config set project YOUR_PROJECT_ID
#   - Required APIs enabled: dns.googleapis.com

set -euo pipefail

# Configuration
PROJECT_ID="${GCP_PROJECT_ID:-$(gcloud config get-value project)}"
REGION="${GCP_REGION:-us-central1}"
VPC_NETWORK="${VPC_NETWORK:-default}"
DNS_ZONE_NAME="staging-internal"
DNS_ZONE_DOMAIN="staging.internal"

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

check_prerequisites() {
    log_info "Checking prerequisites..."

    # Check gcloud is installed
    if ! command -v gcloud &> /dev/null; then
        log_error "gcloud CLI not found. Install from: https://cloud.google.com/sdk/docs/install"
        exit 1
    fi

    # Check project is set
    if [ -z "$PROJECT_ID" ]; then
        log_error "GCP_PROJECT_ID not set. Run: gcloud config set project YOUR_PROJECT_ID"
        exit 1
    fi

    log_info "Using GCP Project: $PROJECT_ID"
    log_info "Using Region: $REGION"

    # Check DNS API is enabled
    if ! gcloud services list --enabled --project="$PROJECT_ID" | grep -q "dns.googleapis.com"; then
        log_warn "Cloud DNS API not enabled. Enabling..."
        gcloud services enable dns.googleapis.com --project="$PROJECT_ID"
    fi
}

get_resource_ips() {
    log_info "Fetching IP addresses from GCP resources..."

    # Get Cloud SQL private IP
    CLOUD_SQL_IP=$(gcloud sql instances describe staging-postgres \
        --project="$PROJECT_ID" \
        --format='get(ipAddresses[?type="PRIVATE"].ipAddress)' 2>/dev/null || echo "")

    if [ -z "$CLOUD_SQL_IP" ]; then
        log_error "Cloud SQL instance 'staging-postgres' not found or has no private IP"
        log_info "Create Cloud SQL instance first or set CLOUD_SQL_IP environment variable"
        exit 1
    fi

    log_info "Cloud SQL IP: $CLOUD_SQL_IP"

    # Get Memorystore Redis (primary) IP
    REDIS_IP=$(gcloud redis instances describe staging-redis \
        --region="$REGION" \
        --project="$PROJECT_ID" \
        --format='get(host)' 2>/dev/null || echo "")

    if [ -z "$REDIS_IP" ]; then
        log_error "Memorystore Redis instance 'staging-redis' not found"
        log_info "Create Redis instance first or set REDIS_IP environment variable"
        exit 1
    fi

    log_info "Redis IP: $REDIS_IP"

    # Get Memorystore Redis (session) IP
    REDIS_SESSION_IP=$(gcloud redis instances describe staging-redis-session \
        --region="$REGION" \
        --project="$PROJECT_ID" \
        --format='get(host)' 2>/dev/null || echo "")

    if [ -z "$REDIS_SESSION_IP" ]; then
        log_error "Memorystore Redis instance 'staging-redis-session' not found"
        log_info "Create Redis instance first or set REDIS_SESSION_IP environment variable"
        exit 1
    fi

    log_info "Redis Session IP: $REDIS_SESSION_IP"
}

create_dns_zone() {
    log_info "Creating private DNS zone: $DNS_ZONE_NAME"

    # Check if zone already exists
    if gcloud dns managed-zones describe "$DNS_ZONE_NAME" \
        --project="$PROJECT_ID" &>/dev/null; then
        log_warn "DNS zone '$DNS_ZONE_NAME' already exists. Skipping zone creation."
        return 0
    fi

    # Create private DNS zone
    gcloud dns managed-zones create "$DNS_ZONE_NAME" \
        --description="Private DNS for staging environment - Cloud SQL and Memorystore" \
        --dns-name="${DNS_ZONE_DOMAIN}." \
        --networks="$VPC_NETWORK" \
        --visibility="private" \
        --project="$PROJECT_ID"

    log_info "DNS zone created successfully"
}

create_dns_records() {
    log_info "Creating DNS records..."

    # Helper function to create or update DNS record
    create_or_update_record() {
        local record_name=$1
        local record_ip=$2

        # Check if record exists
        if gcloud dns record-sets describe "${record_name}." \
            --zone="$DNS_ZONE_NAME" \
            --type="A" \
            --project="$PROJECT_ID" &>/dev/null; then

            log_warn "DNS record '${record_name}' already exists. Updating..."

            # Delete old record first
            gcloud dns record-sets delete "${record_name}." \
                --zone="$DNS_ZONE_NAME" \
                --type="A" \
                --project="$PROJECT_ID" \
                --quiet
        fi

        # Create new record
        gcloud dns record-sets create "${record_name}." \
            --zone="$DNS_ZONE_NAME" \
            --type="A" \
            --ttl="300" \
            --rrdatas="$record_ip" \
            --project="$PROJECT_ID"

        log_info "Created DNS record: ${record_name} -> $record_ip"
    }

    # Create DNS records
    create_or_update_record "cloudsql-staging.internal" "$CLOUD_SQL_IP"
    create_or_update_record "redis-staging.internal" "$REDIS_IP"
    create_or_update_record "redis-session-staging.internal" "$REDIS_SESSION_IP"
}

verify_dns() {
    log_info "Verifying DNS configuration..."

    # List all DNS records
    log_info "DNS records in $DNS_ZONE_NAME:"
    gcloud dns record-sets list \
        --zone="$DNS_ZONE_NAME" \
        --project="$PROJECT_ID"

    # Provide verification command
    echo ""
    log_info "To verify DNS resolution from within GKE cluster, run:"
    echo ""
    echo "kubectl run -it --rm dns-test \\"
    echo "  --image=gcr.io/google.com/cloudsdktool/cloud-sdk:slim \\"
    echo "  --namespace=staging-mcp-server-langgraph \\"
    echo "  --restart=Never \\"
    echo "  -- bash -c 'nslookup cloudsql-staging.internal && nslookup redis-staging.internal && nslookup redis-session-staging.internal'"
    echo ""
}

main() {
    log_info "Starting Cloud DNS setup for staging environment"
    echo ""

    check_prerequisites
    get_resource_ips
    create_dns_zone
    create_dns_records
    verify_dns

    echo ""
    log_info "Cloud DNS setup complete!"
    log_info "Next steps:"
    echo "  1. Deploy to staging: kubectl apply -k deployments/overlays/staging-gke"
    echo "  2. Verify DNS from pods (see command above)"
    echo "  3. Check pod logs: kubectl logs -n staging-mcp-server-langgraph -l app=staging-mcp-server-langgraph"
}

# Run main function
main "$@"
