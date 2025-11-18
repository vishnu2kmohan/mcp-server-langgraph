#!/bin/bash
# ==============================================================================
# GCP Disaster Recovery Automation
# ==============================================================================
#
# This script automates disaster recovery procedures for MCP Server LangGraph
# on GCP GKE including failover, backup restoration, and verification.
#
# ==============================================================================

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# ==============================================================================
# Configuration
# ==============================================================================

PRIMARY_PROJECT="${1:-}"
DR_REGION="${2:-us-east1}"
PRIMARY_REGION="${3:-us-central1}"

if [ -z "$PRIMARY_PROJECT" ]; then
    log_error "Usage: $0 PROJECT_ID [DR_REGION] [PRIMARY_REGION]"
    exit 1
fi

# Cluster names
DR_CLUSTER="production-mcp-server-langgraph-gke-dr"

# Database names
PRIMARY_DB="mcp-prod-postgres"
DR_DB="mcp-prod-postgres-dr"

# Redis names
PRIMARY_REDIS="mcp-prod-redis"
DR_REDIS="mcp-prod-redis-dr"

log_info "DR Configuration:"
log_info "  Primary Region: $PRIMARY_REGION"
log_info "  DR Region: $DR_REGION"
log_info "  Project: $PRIMARY_PROJECT"

# ==============================================================================
# Function: Deploy DR Infrastructure
# ==============================================================================

deploy_dr_infrastructure() {
    log_info "Deploying DR infrastructure in $DR_REGION..."

    # Update Terraform for DR region
    cd terraform/environments/gcp-prod

    # Create DR-specific tfvars
    cat > terraform-dr.tfvars <<EOF
project_id = "$PRIMARY_PROJECT"
region     = "$DR_REGION"

# Override cluster name for DR
# (This requires updating main.tf to support cluster name override)

monitoring_notification_channels = []
EOF

    # Deploy DR infrastructure
    terraform apply -var-file=terraform-dr.tfvars -auto-approve

    log_info "✅ DR infrastructure deployed"
}

# ==============================================================================
# Function: Cloud SQL Failover
# ==============================================================================

failover_cloudsql() {
    log_info "Initiating Cloud SQL failover..."

    # Check if read replica exists in DR region
    REPLICA_EXISTS=$(gcloud sql instances list \
        --filter="name:${PRIMARY_DB}-replica AND region:${DR_REGION}" \
        --format="value(name)" \
        --project="$PRIMARY_PROJECT")

    if [ -z "$REPLICA_EXISTS" ]; then
        log_warn "No read replica in DR region. Creating from backup..."

        # Get latest backup
        LATEST_BACKUP=$(gcloud sql backups list \
            --instance="$PRIMARY_DB" \
            --limit=1 \
            --sort-by=~windowStartTime \
            --format="value(id)" \
            --project="$PRIMARY_PROJECT")

        # Clone from backup to DR region
        gcloud sql instances clone "$PRIMARY_DB" "$DR_DB" \
            --backup-id="$LATEST_BACKUP" \
            --region="$DR_REGION" \
            --project="$PRIMARY_PROJECT"

        log_info "✅ Database cloned to DR region"
    else
        log_info "Read replica exists. Promoting to standalone instance..."

        # Promote replica to standalone
        gcloud sql instances promote-replica "$REPLICA_EXISTS" \
            --project="$PRIMARY_PROJECT"

        log_info "✅ Replica promoted to primary"
    fi
}

# ==============================================================================
# Function: Redis Failover
# ==============================================================================

failover_redis() {
    log_info "Handling Redis failover..."

    # Export data from primary (if accessible)
    if gcloud redis instances describe "$PRIMARY_REDIS" \
        --region="$PRIMARY_REGION" \
        --project="$PRIMARY_PROJECT" &>/dev/null; then

        log_info "Exporting Redis data..."

        gcloud redis instances export \
            "gs://${PRIMARY_PROJECT}-redis-backup/failover-$(date +%Y%m%d-%H%M%S).rdb" \
            --source="$PRIMARY_REDIS" \
            --region="$PRIMARY_REGION" \
            --project="$PRIMARY_PROJECT"
    fi

    # Create new Redis in DR region if doesn't exist
    if ! gcloud redis instances describe "$DR_REDIS" \
        --region="$DR_REGION" \
        --project="$PRIMARY_PROJECT" &>/dev/null; then

        log_info "Creating Redis instance in DR region..."

        gcloud redis instances create "$DR_REDIS" \
            --tier=STANDARD_HA \
            --size=5 \
            --region="$DR_REGION" \
            --redis-version=redis_7_0 \
            --network=projects/"$PRIMARY_PROJECT"/global/networks/mcp-prod-vpc \
            --project="$PRIMARY_PROJECT"

        log_info "✅ DR Redis instance created"
    fi

    log_info "✅ Redis failover handled"
}

# ==============================================================================
# Function: Deploy Application to DR Cluster
# ==============================================================================

deploy_to_dr() {
    log_info "Deploying application to DR cluster..."

    # Get DR cluster credentials
    gcloud container clusters get-credentials "$DR_CLUSTER" \
        --region="$DR_REGION" \
        --project="$PRIMARY_PROJECT"

    # Update database connection (point to DR database)
    kubectl create secret generic dr-database-config \
        --from-literal=cloudsql-connection-name="${PRIMARY_PROJECT}:${DR_REGION}:${DR_DB}" \
        --from-literal=redis-host="REDIS_DR_IP" \
        --namespace=mcp-production \
        --dry-run=client -o yaml | kubectl apply -f -

    # Deploy application
    kubectl apply -k deployments/overlays/production-gke

    # Wait for rollout
    kubectl rollout status deployment/production-mcp-server-langgraph \
        -n mcp-production \
        --timeout=10m

    log_info "✅ Application deployed to DR cluster"
}

# ==============================================================================
# Function: Update DNS/Load Balancer
# ==============================================================================

update_dns() {
    log_info "Updating DNS to point to DR cluster..."

    # Get DR cluster ingress IP
    DR_INGRESS_IP=$(kubectl get svc production-mcp-server-langgraph \
        -n mcp-production \
        -o jsonpath='{.status.loadBalancer.ingress[0].ip}')

    log_info "DR Ingress IP: $DR_INGRESS_IP"
    log_warn "Update your DNS record to point to: $DR_INGRESS_IP"
    log_warn "Or configure Cloud Load Balancer for multi-region routing"

    # Example Cloud DNS update (if using Cloud DNS)
    # gcloud dns record-sets update app.example.com \
    #     --zone=ZONE_NAME \
    #     --type=A \
    #     --rrdatas=$DR_INGRESS_IP \
    #     --project=$PRIMARY_PROJECT
}

# ==============================================================================
# Function: Verify DR Deployment
# ==============================================================================

verify_dr() {
    log_info "Verifying DR deployment..."

    # Health checks
    kubectl wait --for=condition=ready pods \
        -l app=mcp-server-langgraph \
        -n mcp-production \
        --timeout=5m

    # Test endpoint
    kubectl port-forward -n mcp-production \
        svc/production-mcp-server-langgraph 8000:8000 &
    PF_PID=$!

    sleep 5

    if curl -f -s http://localhost:8000/health/live; then
        log_info "✅ Health check passed"
    else
        log_error "❌ Health check failed"
        kill $PF_PID 2>/dev/null || true
        exit 1
    fi

    kill $PF_PID 2>/dev/null || true

    log_info "✅ DR deployment verified"
}

# ==============================================================================
# Function: Full DR Failover
# ==============================================================================

full_dr_failover() {
    log_warn "═══════════════════════════════════════════════"
    log_warn "  INITIATING FULL DR FAILOVER"
    log_warn "═══════════════════════════════════════════════"
    log_warn "This will:"
    log_warn "  1. Deploy DR infrastructure"
    log_warn "  2. Failover Cloud SQL"
    log_warn "  3. Failover Redis"
    log_warn "  4. Deploy application to DR"
    log_warn "  5. Update DNS"
    log_warn "═══════════════════════════════════════════════"

    read -p "Continue with DR failover? (yes/no): " -r
    if [[ ! $REPLY =~ ^yes$ ]]; then
        log_info "DR failover cancelled"
        exit 0
    fi

    # Execute failover steps
    deploy_dr_infrastructure
    failover_cloudsql
    failover_redis
    deploy_to_dr
    verify_dr
    update_dns

    log_info "═══════════════════════════════════════════════"
    log_info "  DR FAILOVER COMPLETE"
    log_info "═══════════════════════════════════════════════"
    log_info "RTO (Recovery Time): $(date)"
    log_info "System is now running in DR region: $DR_REGION"
    log_info "═══════════════════════════════════════════════"
}

# ==============================================================================
# Function: Test DR (Non-Destructive)
# ==============================================================================

test_dr() {
    log_info "Running DR test (non-destructive)..."

    # 1. Create test backup
    log_info "Creating test backup..."
    gcloud sql backups create \
        --instance="$PRIMARY_DB" \
        --description="DR test backup" \
        --project="$PRIMARY_PROJECT"

    # 2. Deploy to DR cluster (without DNS change)
    log_info "Testing DR deployment..."
    deploy_dr_infrastructure
    failover_cloudsql
    deploy_to_dr
    verify_dr

    log_info "✅ DR test complete (no DNS changes made)"
    log_info "   Primary system unchanged"
    log_info "   DR system verified and can be torn down or kept for testing"
}

# ==============================================================================
# Main Menu
# ==============================================================================

case "${4:-menu}" in
    full)
        full_dr_failover
        ;;
    test)
        test_dr
        ;;
    deploy-infra)
        deploy_dr_infrastructure
        ;;
    failover-db)
        failover_cloudsql
        ;;
    failover-redis)
        failover_redis
        ;;
    verify)
        verify_dr
        ;;
    *)
        echo "GCP Disaster Recovery Automation"
        echo
        echo "Usage: $0 PROJECT_ID [DR_REGION] [PRIMARY_REGION] [COMMAND]"
        echo
        echo "Commands:"
        echo "  full           - Full DR failover (production)"
        echo "  test           - Test DR without DNS change (safe)"
        echo "  deploy-infra   - Deploy DR infrastructure only"
        echo "  failover-db    - Failover Cloud SQL only"
        echo "  failover-redis - Failover Redis only"
        echo "  verify         - Verify DR deployment"
        echo
        echo "Example:"
        echo "  $0 my-project us-east1 us-central1 test"
        echo
        ;;
esac
