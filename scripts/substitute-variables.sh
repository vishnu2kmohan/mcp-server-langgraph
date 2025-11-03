#!/usr/bin/env bash
#
# Variable Substitution Script
#
# This script replaces placeholder values in Kubernetes manifests and Terraform configs
# with actual values from environment variables or .env file.
#
# Usage:
#   ./scripts/substitute-variables.sh [--validate-only]
#
# Options:
#   --validate-only    Only validate that all required variables are set, don't substitute
#   --dry-run          Show what would be changed without making changes
#
# Environment variables can be set via:
#   1. System environment variables
#   2. .env file in project root (recommended for development)
#   3. CI/CD environment (recommended for production)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Parse arguments
VALIDATE_ONLY=false
DRY_RUN=false

for arg in "$@"; do
    case $arg in
        --validate-only)
            VALIDATE_ONLY=true
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
    esac
done

# Load .env file if it exists
if [ -f "${PROJECT_ROOT}/.env" ]; then
    echo -e "${GREEN}Loading environment from .env file${NC}"
    set -a  # automatically export all variables
    source "${PROJECT_ROOT}/.env"
    set +a
else
    echo -e "${YELLOW}No .env file found at ${PROJECT_ROOT}/.env${NC}"
    echo -e "${YELLOW}Using system environment variables only${NC}"
fi

# Required variables
REQUIRED_VARS=(
    "AWS_ACCOUNT_ID"
    "ENVIRONMENT"
    "GCP_PROJECT_ID"
)

# Optional variables with defaults
: "${AWS_REGION:=us-west-2}"
: "${GCP_REGION:=us-central1}"
: "${APP_NAME:=mcp-server-langgraph}"

# Validate required variables
echo "Validating required environment variables..."
MISSING_VARS=()

for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var:-}" ]; then
        MISSING_VARS+=("$var")
        echo -e "${RED}✗ $var is not set${NC}"
    else
        # Don't print full values for security, just show they're set
        echo -e "${GREEN}✓ $var is set${NC}"
    fi
done

if [ ${#MISSING_VARS[@]} -gt 0 ]; then
    echo -e "\n${RED}ERROR: Missing required environment variables:${NC}"
    for var in "${MISSING_VARS[@]}"; do
        echo -e "${RED}  - $var${NC}"
    done
    echo -e "\n${YELLOW}Please set these variables in your environment or create a .env file${NC}"
    echo -e "${YELLOW}See .env.template for an example${NC}"
    exit 1
fi

if [ "$VALIDATE_ONLY" = true ]; then
    echo -e "\n${GREEN}✓ All required variables are set${NC}"
    exit 0
fi

# Function to substitute variables in a file
substitute_in_file() {
    local file="$1"
    local temp_file="${file}.tmp"

    if [ "$DRY_RUN" = true ]; then
        echo -e "${YELLOW}Would substitute variables in: $file${NC}"
        return
    fi

    # Create a temp file with substitutions
    cat "$file" | \
        sed "s/ACCOUNT_ID/${AWS_ACCOUNT_ID}/g" | \
        sed "s/PROJECT_ID/${GCP_PROJECT_ID}/g" | \
        sed "s/AZURE_CLIENT_ID/${AZURE_CLIENT_ID:-PLACEHOLDER}/g" | \
        sed "s/ENVIRONMENT/${ENVIRONMENT}/g" | \
        sed "s/YOUR_PROJECT_ID/${GCP_PROJECT_ID}/g" | \
        sed "s/YOUR_ACCOUNT_ID/${AWS_ACCOUNT_ID}/g" \
        > "$temp_file"

    # Only replace if substitutions were made
    if ! diff -q "$file" "$temp_file" > /dev/null 2>&1; then
        mv "$temp_file" "$file"
        echo -e "${GREEN}✓ Substituted variables in: $file${NC}"
    else
        rm "$temp_file"
    fi
}

# Substitute in Kubernetes overlays
echo -e "\n${GREEN}Substituting variables in Kubernetes manifests...${NC}"

# AWS overlay
if [ -f "${PROJECT_ROOT}/deployments/kubernetes/overlays/aws/serviceaccount-patch.yaml" ]; then
    substitute_in_file "${PROJECT_ROOT}/deployments/kubernetes/overlays/aws/serviceaccount-patch.yaml"
fi

if [ -f "${PROJECT_ROOT}/deployments/kubernetes/overlays/aws/external-secrets.yaml" ]; then
    substitute_in_file "${PROJECT_ROOT}/deployments/kubernetes/overlays/aws/external-secrets.yaml"
fi

# GCP overlay
if [ -f "${PROJECT_ROOT}/deployments/overlays/production-gke/serviceaccount-patch.yaml" ]; then
    substitute_in_file "${PROJECT_ROOT}/deployments/overlays/production-gke/serviceaccount-patch.yaml"
fi

if [ -f "${PROJECT_ROOT}/deployments/overlays/production-gke/external-secrets.yaml" ]; then
    substitute_in_file "${PROJECT_ROOT}/deployments/overlays/production-gke/external-secrets.yaml"
fi

# Base serviceaccount (remove placeholders - overlays will provide real values)
if [ -f "${PROJECT_ROOT}/deployments/base/serviceaccount.yaml" ]; then
    echo -e "${YELLOW}Note: Base ServiceAccount should use placeholders that overlays will replace${NC}"
fi

echo -e "\n${GREEN}✓ Variable substitution complete${NC}"
echo -e "${YELLOW}Note: Review changes before committing${NC}"
