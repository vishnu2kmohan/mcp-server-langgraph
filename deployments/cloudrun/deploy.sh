#!/bin/bash
set -e

# Google Cloud Run Deployment Script
# This script builds and deploys the MCP Server with LangGraph to Cloud Run

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ID="${GOOGLE_CLOUD_PROJECT:-}"
REGION="${REGION:-us-central1}"
SERVICE_NAME="mcp-server-langgraph"
SERVICE_ACCOUNT="${SERVICE_ACCOUNT:-mcp-server-langgraph-sa}"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

# Functions
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_prerequisites() {
    print_info "Checking prerequisites..."

    # Check if gcloud is installed
    if ! command -v gcloud &> /dev/null; then
        print_error "gcloud CLI not found. Install from: https://cloud.google.com/sdk/docs/install"
        exit 1
    fi

    # Check if project ID is set
    if [ -z "$PROJECT_ID" ]; then
        PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
        if [ -z "$PROJECT_ID" ]; then
            print_error "GOOGLE_CLOUD_PROJECT not set and no default project found"
            print_error "Set project: gcloud config set project YOUR_PROJECT_ID"
            exit 1
        fi
    fi

    print_info "Using project: $PROJECT_ID"
    print_info "Using region: $REGION"
}

enable_apis() {
    print_info "Enabling required APIs..."

    gcloud services enable \
        run.googleapis.com \
        cloudbuild.googleapis.com \
        secretmanager.googleapis.com \
        --project="$PROJECT_ID" \
        --quiet

    print_info "APIs enabled successfully"
}

create_service_account() {
    print_info "Creating service account..."

    # Check if service account exists
    if gcloud iam service-accounts describe "${SERVICE_ACCOUNT}@${PROJECT_ID}.iam.gserviceaccount.com" \
        --project="$PROJECT_ID" &>/dev/null; then
        print_warn "Service account already exists, skipping creation"
    else
        gcloud iam service-accounts create "$SERVICE_ACCOUNT" \
            --display-name="MCP Server with LangGraph Service Account" \
            --project="$PROJECT_ID"

        print_info "Service account created: ${SERVICE_ACCOUNT}@${PROJECT_ID}.iam.gserviceaccount.com"
    fi

    # Grant necessary permissions
    print_info "Granting permissions to service account..."

    gcloud projects add-iam-policy-binding "$PROJECT_ID" \
        --member="serviceAccount:${SERVICE_ACCOUNT}@${PROJECT_ID}.iam.gserviceaccount.com" \
        --role="roles/secretmanager.secretAccessor" \
        --quiet

    print_info "Service account configured"
}

create_secrets() {
    print_info "Setting up secrets in Secret Manager..."

    # Check if .env exists for local secrets
    if [ ! -f "../.env" ]; then
        print_warn ".env file not found, skipping secret creation"
        print_warn "You'll need to create secrets manually or provide a .env file"
        return
    fi

    # Array of required secrets
    declare -a secrets=(
        "jwt-secret-key:JWT_SECRET_KEY"
        "anthropic-api-key:ANTHROPIC_API_KEY"
        "openai-api-key:OPENAI_API_KEY"
    )

    for secret_pair in "${secrets[@]}"; do
        IFS=':' read -r secret_name env_var <<< "$secret_pair"

        # Get value from .env
        secret_value=$(grep "^${env_var}=" ../.env | cut -d '=' -f2- | tr -d '"' | tr -d "'")

        if [ -z "$secret_value" ]; then
            print_warn "Secret $env_var not found in .env, skipping"
            continue
        fi

        # Check if secret exists
        if gcloud secrets describe "$secret_name" --project="$PROJECT_ID" &>/dev/null; then
            print_warn "Secret $secret_name already exists, adding new version"
            echo -n "$secret_value" | gcloud secrets versions add "$secret_name" \
                --data-file=- \
                --project="$PROJECT_ID"
        else
            print_info "Creating secret: $secret_name"
            echo -n "$secret_value" | gcloud secrets create "$secret_name" \
                --data-file=- \
                --replication-policy="automatic" \
                --project="$PROJECT_ID"
        fi
    done

    print_info "Secrets configured"
}

build_image() {
    print_info "Building Docker image with Cloud Build..."

    # Build using Cloud Build
    gcloud builds submit \
        --tag "$IMAGE_NAME:latest" \
        --project="$PROJECT_ID" \
        ..

    print_info "Image built: $IMAGE_NAME:latest"
}

update_service_yaml() {
    print_info "Updating service.yaml with project-specific values..."

    # Create a temporary service.yaml with substitutions
    sed -e "s/PROJECT_ID/$PROJECT_ID/g" \
        -e "s/REGION/$REGION/g" \
        service.yaml > service.tmp.yaml

    print_info "Service configuration updated"
}

deploy_service() {
    print_info "Deploying to Cloud Run..."

    gcloud run services replace service.tmp.yaml \
        --region="$REGION" \
        --project="$PROJECT_ID"

    # Clean up temporary file
    rm -f service.tmp.yaml

    print_info "Service deployed successfully"
}

get_service_url() {
    print_info "Getting service URL..."

    SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" \
        --region="$REGION" \
        --project="$PROJECT_ID" \
        --format="value(status.url)")

    echo ""
    echo "═══════════════════════════════════════════════════════════════"
    echo -e "${GREEN}✓ Deployment Complete!${NC}"
    echo "═══════════════════════════════════════════════════════════════"
    echo ""
    echo "Service URL: $SERVICE_URL"
    echo ""
    echo "Test your deployment:"
    echo "  curl $SERVICE_URL/health/live"
    echo "  curl $SERVICE_URL/health/ready"
    echo ""
    echo "View logs:"
    echo "  gcloud run services logs read $SERVICE_NAME --region=$REGION --project=$PROJECT_ID"
    echo ""
    echo "Update service:"
    echo "  ./deploy.sh"
    echo ""
    echo "═══════════════════════════════════════════════════════════════"
}

# Main deployment flow
main() {
    echo "═══════════════════════════════════════════════════════════════"
    echo "  MCP Server with LangGraph - Cloud Run Deployment"
    echo "═══════════════════════════════════════════════════════════════"
    echo ""

    check_prerequisites

    # Check for --setup flag
    if [[ "$1" == "--setup" ]]; then
        print_info "Running initial setup..."
        enable_apis
        create_service_account
        create_secrets
    fi

    build_image
    update_service_yaml
    deploy_service
    get_service_url
}

# Run main function
main "$@"
