#!/bin/bash
# ==============================================================================
# Sign Container Image for Binary Authorization
# ==============================================================================
#
# This script signs a container image and creates an attestation for
# Binary Authorization.
#
# Usage:
#   ./sign-image.sh PROJECT_ID ENVIRONMENT IMAGE_URL
#
# Example:
#   ./sign-image.sh my-project production us-central1-docker.pkg.dev/my-project/mcp-production/app:v1.0.0
#
# ==============================================================================

set -euo pipefail

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Validate arguments
if [ $# -lt 3 ]; then
    log_error "Usage: $0 PROJECT_ID ENVIRONMENT IMAGE_URL"
    log_error "Example: $0 my-project production us-central1-docker.pkg.dev/my-project/mcp-production/app:v1.0.0"
    exit 1
fi

PROJECT_ID="$1"
ENVIRONMENT="$2"
IMAGE_URL="$3"

# Validate environment
if [[ ! "$ENVIRONMENT" =~ ^(development|staging|production)$ ]]; then
    log_error "Environment must be: development, staging, or production"
    exit 1
fi

# Configuration
REGION="us-central1"
KEYRING_NAME="${ENVIRONMENT}-binauthz"
KEY_NAME="attestor-key"
ATTESTOR_ID="${ENVIRONMENT}-attestor"

log_info "Signing image: $IMAGE_URL"
log_info "Environment: $ENVIRONMENT"
log_info "Attestor: $ATTESTOR_ID"

# ==============================================================================
# Verify Image Exists
# ==============================================================================

log_info "Verifying image exists..."

if ! gcloud container images describe "$IMAGE_URL" --project="$PROJECT_ID" &>/dev/null; then
    log_error "Image not found: $IMAGE_URL"
    log_error "Please build and push the image first"
    exit 1
fi

log_info "✅ Image verified"

# ==============================================================================
# Check for Existing Attestation
# ==============================================================================

log_info "Checking for existing attestations..."

EXISTING_ATTESTATIONS=$(gcloud container binauthz attestations list \
    --attestor="$ATTESTOR_ID" \
    --project="$PROJECT_ID" \
    --filter="resourceUri:\"$IMAGE_URL\"" \
    --format="value(name)" | wc -l)

if [ "$EXISTING_ATTESTATIONS" -gt 0 ]; then
    log_warn "Image already has attestations ($EXISTING_ATTESTATIONS found)"
    read -p "Sign anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Skipping signing"
        exit 0
    fi
fi

# ==============================================================================
# Create Attestation
# ==============================================================================

log_info "Creating attestation (this may take a moment)..."

gcloud container binauthz attestations sign-and-create \
    --project="$PROJECT_ID" \
    --artifact-url="$IMAGE_URL" \
    --attestor="$ATTESTOR_ID" \
    --attestor-project="$PROJECT_ID" \
    --keyversion-project="$PROJECT_ID" \
    --keyversion-location="$REGION" \
    --keyversion-keyring="$KEYRING_NAME" \
    --keyversion-key="$KEY_NAME" \
    --keyversion=1

log_info "✅ Image signed successfully"

# ==============================================================================
# Verify Attestation
# ==============================================================================

log_info "Verifying attestation..."

ATTESTATION_COUNT=$(gcloud container binauthz attestations list \
    --attestor="$ATTESTOR_ID" \
    --project="$PROJECT_ID" \
    --filter="resourceUri:\"$IMAGE_URL\"" \
    --format="value(name)" | wc -l)

if [ "$ATTESTATION_COUNT" -lt 1 ]; then
    log_error "Attestation creation failed (no attestations found)"
    exit 1
fi

log_info "✅ Attestation verified ($ATTESTATION_COUNT attestations)"

# ==============================================================================
# Display Summary
# ==============================================================================

echo
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Image Signing Summary"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo
echo "Image:       $IMAGE_URL"
echo "Attestor:    $ATTESTOR_ID"
echo "Environment: $ENVIRONMENT"
echo "Status:      ✅ SIGNED"
echo
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Verification"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo
echo "View attestations:"
echo "  gcloud container binauthz attestations list \\"
echo "    --attestor=$ATTESTOR_ID \\"
echo "    --project=$PROJECT_ID \\"
echo "    --filter='resourceUri:\"$IMAGE_URL\"'"
echo
echo "Test deployment:"
echo "  kubectl run test-signed --image=$IMAGE_URL --namespace=mcp-$ENVIRONMENT"
echo
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
