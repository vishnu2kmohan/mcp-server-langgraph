#!/bin/bash
set -e

# Google Cloud Secret Manager Setup Script
# This script creates all required secrets for the MCP Server with LangGraph

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
PROJECT_ID="${GOOGLE_CLOUD_PROJECT:-}"
SERVICE_ACCOUNT="${SERVICE_ACCOUNT:-mcp-server-langgraph-sa}"

print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_prompt() {
    echo -e "${BLUE}[INPUT]${NC} $1"
}

check_prerequisites() {
    if [ -z "$PROJECT_ID" ]; then
        PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
        if [ -z "$PROJECT_ID" ]; then
            print_error "GOOGLE_CLOUD_PROJECT not set"
            exit 1
        fi
    fi
    print_info "Using project: $PROJECT_ID"
}

create_secret() {
    local secret_name=$1
    local description=$2
    local env_var=$3

    echo ""
    print_prompt "$description"

    # Check if secret exists in .env
    local secret_value=""
    if [ -f "../.env" ]; then
        secret_value=$(grep "^${env_var}=" ../.env | cut -d '=' -f2- | tr -d '"' | tr -d "'")
    fi

    if [ -n "$secret_value" ]; then
        print_info "Found value in .env file"
        read -p "Use value from .env? (y/n): " use_env
        if [[ "$use_env" != "y" ]]; then
            read -s -p "Enter value: " secret_value
            echo ""
        fi
    else
        read -s -p "Enter value: " secret_value
        echo ""
    fi

    if [ -z "$secret_value" ]; then
        print_warn "Empty value, skipping $secret_name"
        return
    fi

    # Check if secret already exists
    if gcloud secrets describe "$secret_name" --project="$PROJECT_ID" &>/dev/null; then
        print_warn "Secret $secret_name already exists"
        read -p "Update with new version? (y/n): " update
        if [[ "$update" == "y" ]]; then
            echo -n "$secret_value" | gcloud secrets versions add "$secret_name" \
                --data-file=- \
                --project="$PROJECT_ID"
            print_info "✓ Secret $secret_name updated"
        fi
    else
        echo -n "$secret_value" | gcloud secrets create "$secret_name" \
            --data-file=- \
            --replication-policy="automatic" \
            --project="$PROJECT_ID"
        print_info "✓ Secret $secret_name created"
    fi

    # Grant service account access
    gcloud secrets add-iam-policy-binding "$secret_name" \
        --member="serviceAccount:${SERVICE_ACCOUNT}@${PROJECT_ID}.iam.gserviceaccount.com" \
        --role="roles/secretmanager.secretAccessor" \
        --project="$PROJECT_ID" \
        --quiet 2>/dev/null || true
}

main() {
    echo "═══════════════════════════════════════════════════════════════"
    echo "  Secret Manager Setup - MCP Server with LangGraph"
    echo "═══════════════════════════════════════════════════════════════"
    echo ""

    check_prerequisites

    print_info "This script will create the following secrets:"
    echo "  1. jwt-secret-key - JWT signing secret"
    echo "  2. anthropic-api-key - Anthropic API key"
    echo "  3. openai-api-key - OpenAI API key"
    echo "  4. openfga-store-id - OpenFGA store ID (optional)"
    echo "  5. openfga-model-id - OpenFGA model ID (optional)"
    echo "  6. infisical-client-id - Infisical client ID (optional)"
    echo "  7. infisical-client-secret - Infisical client secret (optional)"
    echo ""

    read -p "Continue? (y/n): " confirm
    if [[ "$confirm" != "y" ]]; then
        print_warn "Aborted by user"
        exit 0
    fi

    # Required secrets
    create_secret "jwt-secret-key" \
        "JWT Secret Key (used for signing authentication tokens)" \
        "JWT_SECRET_KEY"

    create_secret "anthropic-api-key" \
        "Anthropic API Key (for Claude models)" \
        "ANTHROPIC_API_KEY"

    create_secret "openai-api-key" \
        "OpenAI API Key (for GPT models)" \
        "OPENAI_API_KEY"

    # Optional secrets
    echo ""
    print_info "Optional secrets (press Enter to skip):"

    create_secret "openfga-store-id" \
        "OpenFGA Store ID (for authorization)" \
        "OPENFGA_STORE_ID"

    create_secret "openfga-model-id" \
        "OpenFGA Model ID (for authorization)" \
        "OPENFGA_MODEL_ID"

    create_secret "infisical-client-id" \
        "Infisical Client ID (for secrets management)" \
        "INFISICAL_CLIENT_ID"

    create_secret "infisical-client-secret" \
        "Infisical Client Secret (for secrets management)" \
        "INFISICAL_CLIENT_SECRET"

    echo ""
    echo "═══════════════════════════════════════════════════════════════"
    print_info "✓ Secret setup complete!"
    echo "═══════════════════════════════════════════════════════════════"
    echo ""
    print_info "View secrets:"
    echo "  gcloud secrets list --project=$PROJECT_ID"
    echo ""
    print_info "Update a secret:"
    echo "  echo -n 'new-value' | gcloud secrets versions add SECRET_NAME --data-file=- --project=$PROJECT_ID"
    echo ""
    print_info "Next step: Deploy to Cloud Run"
    echo "  cd cloudrun && ./deploy.sh"
    echo ""
}

main "$@"
