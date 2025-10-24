#!/bin/bash
#
# GCP Staging Infrastructure Setup Script
#
# This script creates a production-grade staging environment on GKE with:
# - Separate VPC for network isolation
# - GKE Autopilot cluster with security hardening
# - Workload Identity Federation for GitHub Actions (keyless)
# - Cloud SQL and Memorystore Redis
# - Secret Manager integration
#
# Prerequisites:
# - gcloud CLI installed and authenticated
# - Billing enabled on project
# - Required APIs enabled (see enable_apis function)
#
# Usage:
#   ./scripts/gcp/setup-staging-infrastructure.sh
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

# GitHub configuration (update these)
GITHUB_ORG="vishnu2kmohan"
GITHUB_REPO="mcp-server-langgraph"

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
}

enable_apis() {
    log_info "Enabling required GCP APIs..."

    gcloud services enable \
        container.googleapis.com \
        compute.googleapis.com \
        sql-component.googleapis.com \
        redis.googleapis.com \
        secretmanager.googleapis.com \
        cloudkms.googleapis.com \
        servicenetworking.googleapis.com \
        binaryauthorization.googleapis.com \
        iamcredentials.googleapis.com \
        sts.googleapis.com

    log_info "APIs enabled successfully"
}

create_vpc_network() {
    log_info "Creating staging VPC network..."

    # Check if VPC already exists
    if gcloud compute networks describe "$VPC_NAME" &> /dev/null; then
        log_warn "VPC $VPC_NAME already exists, skipping creation"
        return 0
    fi

    # Create VPC
    gcloud compute networks create "$VPC_NAME" \
        --subnet-mode=custom \
        --description="Staging VPC for MCP Server LangGraph"

    # Create subnet with secondary ranges for GKE
    gcloud compute networks subnets create "$SUBNET_NAME" \
        --network="$VPC_NAME" \
        --range=10.1.0.0/20 \
        --region="$REGION" \
        --secondary-range pods=10.2.0.0/16,services=10.3.0.0/16 \
        --enable-flow-logs \
        --enable-private-ip-google-access \
        --logging-aggregation-interval=interval-5-sec \
        --logging-flow-sampling=0.5 \
        --logging-metadata=include-all

    # Create firewall rules
    log_info "Creating firewall rules..."

    # Allow internal communication
    gcloud compute firewall-rules create "$VPC_NAME-allow-internal" \
        --network="$VPC_NAME" \
        --allow=tcp,udp,icmp \
        --source-ranges=10.1.0.0/20,10.2.0.0/16,10.3.0.0/16 \
        --description="Allow internal communication within staging VPC"

    # Allow SSH from IAP (for debugging)
    gcloud compute firewall-rules create "$VPC_NAME-allow-iap-ssh" \
        --network="$VPC_NAME" \
        --allow=tcp:22 \
        --source-ranges=35.235.240.0/20 \
        --description="Allow SSH from Identity-Aware Proxy"

    log_info "VPC network created successfully"
}

create_gke_cluster() {
    log_info "Creating GKE Autopilot cluster with security hardening..."

    # Check if cluster already exists
    if gcloud container clusters describe "$CLUSTER_NAME" --region="$REGION" &> /dev/null; then
        log_warn "Cluster $CLUSTER_NAME already exists, skipping creation"
        return 0
    fi

    # Create Autopilot cluster with security best practices
    gcloud container clusters create-auto "$CLUSTER_NAME" \
        --region="$REGION" \
        --network="$VPC_NAME" \
        --subnetwork="$SUBNET_NAME" \
        --cluster-secondary-range-name=pods \
        --services-secondary-range-name=services \
        --enable-private-nodes \
        --enable-private-endpoint=false \
        --master-ipv4-cidr=172.16.0.0/28 \
        --workload-pool="$PROJECT_ID.svc.id.goog" \
        --enable-shielded-nodes \
        --shielded-secure-boot \
        --shielded-integrity-monitoring \
        --binauthz-evaluation-mode=PROJECT_SINGLETON_POLICY_ENFORCE \
        --release-channel=regular \
        --enable-cloud-logging \
        --enable-cloud-monitoring \
        --enable-autorepair \
        --enable-autoupgrade \
        --disk-type=pd-balanced \
        --maintenance-window-start=2025-01-01T04:00:00Z \
        --maintenance-window-duration=4h \
        --maintenance-window-recurrence="FREQ=WEEKLY;BYDAY=SU"

    log_info "GKE cluster created successfully"
    log_info "Getting cluster credentials..."

    gcloud container clusters get-credentials "$CLUSTER_NAME" --region="$REGION"

    # Verify cluster access
    kubectl cluster-info
}

setup_workload_identity() {
    log_info "Setting up Workload Identity for Kubernetes pods..."

    # Create Google Service Account
    if gcloud iam service-accounts describe "${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com" &> /dev/null; then
        log_warn "Service account ${SERVICE_ACCOUNT_NAME} already exists, skipping creation"
    else
        gcloud iam service-accounts create "$SERVICE_ACCOUNT_NAME" \
            --display-name="MCP Staging Service Account" \
            --description="Service account for MCP Server LangGraph staging environment"
    fi

    # Grant necessary permissions (least privilege)
    log_info "Granting IAM permissions..."

    # Secret Manager access
    gcloud projects add-iam-policy-binding "$PROJECT_ID" \
        --member="serviceAccount:${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com" \
        --role="roles/secretmanager.secretAccessor" \
        --condition=None

    # Cloud SQL client
    gcloud projects add-iam-policy-binding "$PROJECT_ID" \
        --member="serviceAccount:${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com" \
        --role="roles/cloudsql.client" \
        --condition=None

    # Logging writer
    gcloud projects add-iam-policy-binding "$PROJECT_ID" \
        --member="serviceAccount:${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com" \
        --role="roles/logging.logWriter" \
        --condition=None

    # Monitoring metric writer
    gcloud projects add-iam-policy-binding "$PROJECT_ID" \
        --member="serviceAccount:${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com" \
        --role="roles/monitoring.metricWriter" \
        --condition=None

    log_info "Workload Identity configured successfully"
}

setup_github_workload_identity() {
    log_info "Setting up Workload Identity Federation for GitHub Actions (keyless authentication)..."

    # Create Workload Identity Pool
    if gcloud iam workload-identity-pools describe "github-actions-pool" \
        --location="global" &> /dev/null; then
        log_warn "Workload Identity Pool already exists, skipping creation"
    else
        gcloud iam workload-identity-pools create "github-actions-pool" \
            --location="global" \
            --display-name="GitHub Actions Pool" \
            --description="Workload Identity Pool for GitHub Actions deployments"
    fi

    # Create OIDC Provider
    if gcloud iam workload-identity-pools providers describe "github-provider" \
        --location="global" \
        --workload-identity-pool="github-actions-pool" &> /dev/null; then
        log_warn "GitHub provider already exists, skipping creation"
    else
        gcloud iam workload-identity-pools providers create-oidc "github-provider" \
            --location="global" \
            --workload-identity-pool="github-actions-pool" \
            --issuer-uri="https://token.actions.githubusercontent.com" \
            --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository,attribute.repository_owner=assertion.repository_owner" \
            --attribute-condition="assertion.repository_owner=='${GITHUB_ORG}'"
    fi

    # Grant GitHub Actions permission to impersonate service account
    log_info "Granting GitHub Actions impersonation rights..."

    gcloud iam service-accounts add-iam-policy-binding \
        "${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com" \
        --role="roles/iam.workloadIdentityUser" \
        --member="principalSet://iam.googleapis.com/projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/github-actions-pool/attribute.repository/${GITHUB_ORG}/${GITHUB_REPO}"

    # Get Workload Identity Provider resource name
    WI_PROVIDER=$(gcloud iam workload-identity-pools providers describe github-provider \
        --location=global \
        --workload-identity-pool=github-actions-pool \
        --format='value(name)')

    log_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    log_info "GitHub Actions Configuration:"
    log_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "Add these to your GitHub Actions workflow:"
    echo ""
    echo "  workload_identity_provider: '$WI_PROVIDER'"
    echo "  service_account: '${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com'"
    echo ""
    log_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

create_cloud_sql() {
    log_info "Creating Cloud SQL PostgreSQL instance for staging..."

    INSTANCE_NAME="mcp-staging-postgres"

    # Check if instance already exists
    if gcloud sql instances describe "$INSTANCE_NAME" &> /dev/null; then
        log_warn "Cloud SQL instance $INSTANCE_NAME already exists, skipping creation"
        return 0
    fi

    # Create instance (smaller tier for staging)
    gcloud sql instances create "$INSTANCE_NAME" \
        --database-version=POSTGRES_15 \
        --tier=db-custom-1-4096 \
        --region="$REGION" \
        --network="projects/${PROJECT_ID}/global/networks/${VPC_NAME}" \
        --no-assign-ip \
        --enable-google-private-path \
        --backup-start-time=04:00 \
        --backup-location=us \
        --maintenance-window-day=SUN \
        --maintenance-window-hour=4 \
        --database-flags=max_connections=100,shared_buffers=256MB \
        --deletion-protection

    # Create databases
    log_info "Creating databases..."

    gcloud sql databases create keycloak --instance="$INSTANCE_NAME"
    gcloud sql databases create openfga --instance="$INSTANCE_NAME"

    # Generate secure passwords
    KEYCLOAK_PASSWORD=$(openssl rand -base64 32)
    OPENFGA_PASSWORD=$(openssl rand -base64 32)

    # Create users
    gcloud sql users create keycloak \
        --instance="$INSTANCE_NAME" \
        --password="$KEYCLOAK_PASSWORD"

    gcloud sql users create openfga \
        --instance="$INSTANCE_NAME" \
        --password="$OPENFGA_PASSWORD"

    # Store passwords in Secret Manager
    echo -n "$KEYCLOAK_PASSWORD" | gcloud secrets create staging-keycloak-db-password \
        --data-file=- \
        --replication-policy=automatic || true

    echo -n "$OPENFGA_PASSWORD" | gcloud secrets create staging-openfga-db-password \
        --data-file=- \
        --replication-policy=automatic || true

    # Get connection name
    CONNECTION_NAME=$(gcloud sql instances describe "$INSTANCE_NAME" --format='value(connectionName)')

    log_info "Cloud SQL instance created: $CONNECTION_NAME"
}

create_memorystore_redis() {
    log_info "Creating Memorystore Redis instance for staging..."

    INSTANCE_NAME="mcp-staging-redis"

    # Check if instance already exists
    if gcloud redis instances describe "$INSTANCE_NAME" --region="$REGION" &> /dev/null; then
        log_warn "Redis instance $INSTANCE_NAME already exists, skipping creation"
        return 0
    fi

    # Create Redis instance
    gcloud redis instances create "$INSTANCE_NAME" \
        --size=2 \
        --region="$REGION" \
        --tier=standard \
        --redis-version=redis_7_0 \
        --network="projects/${PROJECT_ID}/global/networks/${VPC_NAME}" \
        --connect-mode=private-service-access \
        --enable-auth \
        --maintenance-window-day=sunday \
        --maintenance-window-hour=4

    # Get Redis details
    REDIS_HOST=$(gcloud redis instances describe "$INSTANCE_NAME" \
        --region="$REGION" \
        --format='value(host)')

    REDIS_PORT=$(gcloud redis instances describe "$INSTANCE_NAME" \
        --region="$REGION" \
        --format='value(port)')

    REDIS_AUTH=$(gcloud redis instances get-auth-string "$INSTANCE_NAME" \
        --region="$REGION")

    # Store in Secret Manager
    echo -n "$REDIS_HOST" | gcloud secrets create staging-redis-host \
        --data-file=- \
        --replication-policy=automatic || true

    echo -n "$REDIS_AUTH" | gcloud secrets create staging-redis-password \
        --data-file=- \
        --replication-policy=automatic || true

    log_info "Redis instance created: $REDIS_HOST:$REDIS_PORT"
}

create_secrets() {
    log_info "Creating application secrets in Secret Manager..."

    # JWT secret
    JWT_SECRET=$(openssl rand -base64 64)
    echo -n "$JWT_SECRET" | gcloud secrets create staging-jwt-secret \
        --data-file=- \
        --replication-policy=automatic || log_warn "staging-jwt-secret already exists"

    # Placeholder for API keys (user should update these)
    echo -n "sk-ant-REPLACE_WITH_ACTUAL_KEY" | gcloud secrets create staging-anthropic-api-key \
        --data-file=- \
        --replication-policy=automatic || log_warn "staging-anthropic-api-key already exists"

    echo -n "REPLACE_WITH_ACTUAL_KEY" | gcloud secrets create staging-google-api-key \
        --data-file=- \
        --replication-policy=automatic || log_warn "staging-google-api-key already exists"

    log_warn "⚠️  Update these secrets with actual API keys:"
    log_warn "   gcloud secrets versions add staging-anthropic-api-key --data-file=<(echo -n 'sk-ant-...')"
    log_warn "   gcloud secrets versions add staging-google-api-key --data-file=<(echo -n 'your-key')"
}

setup_artifact_registry() {
    log_info "Setting up Artifact Registry for Docker images..."

    REPO_NAME="mcp-staging"

    # Check if repository already exists
    if gcloud artifacts repositories describe "$REPO_NAME" \
        --location="$REGION" &> /dev/null; then
        log_warn "Artifact Registry repository $REPO_NAME already exists, skipping creation"
        return 0
    fi

    # Create repository
    gcloud artifacts repositories create "$REPO_NAME" \
        --repository-format=docker \
        --location="$REGION" \
        --description="Docker images for MCP Server LangGraph staging environment"

    log_info "Artifact Registry repository created: ${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}"
    log_info "Configure Docker authentication:"
    log_info "  gcloud auth configure-docker ${REGION}-docker.pkg.dev"
}

print_summary() {
    log_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    log_info "Staging Infrastructure Setup Complete!"
    log_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "📋 Summary:"
    echo "  • Project: $PROJECT_ID"
    echo "  • Region: $REGION"
    echo "  • VPC: $VPC_NAME"
    echo "  • GKE Cluster: $CLUSTER_NAME"
    echo "  • Service Account: ${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
    echo ""
    echo "🔐 Security Features Enabled:"
    echo "  ✓ Private GKE nodes"
    echo "  ✓ Shielded nodes with secure boot"
    echo "  ✓ Binary authorization"
    echo "  ✓ Workload Identity"
    echo "  ✓ Network isolation (separate VPC)"
    echo "  ✓ Audit logging"
    echo ""
    echo "☁️ Managed Services:"
    echo "  • Cloud SQL PostgreSQL: mcp-staging-postgres"
    echo "  • Memorystore Redis: mcp-staging-redis"
    echo "  • Artifact Registry: ${REGION}-docker.pkg.dev/${PROJECT_ID}/mcp-staging"
    echo ""
    echo "📝 Next Steps:"
    echo "  1. Update API keys in Secret Manager (see warnings above)"
    echo "  2. Deploy application: kubectl apply -k deployments/overlays/staging-gke"
    echo "  3. Configure GitHub Actions workflow with Workload Identity values"
    echo "  4. Set up monitoring and alerts in Cloud Console"
    echo ""
    log_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

# Main execution
main() {
    log_info "Starting GCP Staging Infrastructure Setup..."
    echo ""

    check_prerequisites
    enable_apis
    create_vpc_network
    create_gke_cluster
    setup_workload_identity
    setup_github_workload_identity
    create_cloud_sql
    create_memorystore_redis
    create_secrets
    setup_artifact_registry

    echo ""
    print_summary
}

# Run main function
main "$@"
