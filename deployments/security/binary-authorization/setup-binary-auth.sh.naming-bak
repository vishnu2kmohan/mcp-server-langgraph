#!/bin/bash
# ==============================================================================
# Binary Authorization Setup for GKE
# ==============================================================================
#
# This script sets up Binary Authorization for GKE clusters to enforce
# image signing policies before deployment.
#
# Prerequisites:
# - gcloud CLI authenticated
# - Project ID set in environment
# - Appropriate IAM permissions
#
# Usage:
#   ./setup-binary-auth.sh PROJECT_ID ENVIRONMENT
#
# Example:
#   ./setup-binary-auth.sh my-project-id production
#
# ==============================================================================

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Validate arguments
if [ $# -lt 2 ]; then
    log_error "Usage: $0 PROJECT_ID ENVIRONMENT"
    log_error "Example: $0 my-project-id production"
    exit 1
fi

PROJECT_ID="$1"
ENVIRONMENT="$2"

# Validate environment
if [[ ! "$ENVIRONMENT" =~ ^(development|staging|production)$ ]]; then
    log_error "Environment must be: development, staging, or production"
    exit 1
fi

log_info "Setting up Binary Authorization for $ENVIRONMENT environment"
log_info "Project: $PROJECT_ID"

# ==============================================================================
# 1. Enable APIs
# ==============================================================================

log_info "Enabling required APIs..."
gcloud services enable \
    binaryauthorization.googleapis.com \
    containeranalysis.googleapis.com \
    containerscanning.googleapis.com \
    --project="$PROJECT_ID"

log_info "✅ APIs enabled"

# ==============================================================================
# 2. Create KMS Key Ring and Key for Attestations
# ==============================================================================

REGION="us-central1"
KEYRING_NAME="${ENVIRONMENT}-binauthz"
KEY_NAME="attestor-key"

log_info "Creating KMS key ring: $KEYRING_NAME"

# Create key ring (idempotent)
gcloud kms keyrings create "$KEYRING_NAME" \
    --location="$REGION" \
    --project="$PROJECT_ID" \
    2>/dev/null || log_warn "Key ring already exists"

log_info "Creating KMS key: $KEY_NAME"

# Create key (idempotent)
gcloud kms keys create "$KEY_NAME" \
    --location="$REGION" \
    --keyring="$KEYRING_NAME" \
    --purpose=asymmetric-signing \
    --default-algorithm=rsa-sign-pkcs1-4096-sha512 \
    --project="$PROJECT_ID" \
    2>/dev/null || log_warn "Key already exists"

log_info "✅ KMS key created"

# ==============================================================================
# 3. Create Container Analysis Note
# ==============================================================================

NOTE_ID="${ENVIRONMENT}-attestor-note"
NOTE_PROJECT="$PROJECT_ID"

log_info "Creating Container Analysis note: $NOTE_ID"

cat > /tmp/note.json <<EOF
{
  "name": "projects/$NOTE_PROJECT/notes/$NOTE_ID",
  "attestation": {
    "hint": {
      "human_readable_name": "$ENVIRONMENT environment attestor note"
    }
  }
}
EOF

# Create note (check if exists first)
if ! gcloud container binauthz attestors describe "$NOTE_ID" --project="$PROJECT_ID" &>/dev/null; then
    curl -X POST \
        -H "Authorization: Bearer $(gcloud auth print-access-token)" \
        -H "Content-Type: application/json" \
        -d @/tmp/note.json \
        "https://containeranalysis.googleapis.com/v1/projects/$NOTE_PROJECT/notes/?noteId=$NOTE_ID"
    log_info "✅ Container Analysis note created"
else
    log_warn "Note already exists"
fi

# ==============================================================================
# 4. Create Attestor
# ==============================================================================

ATTESTOR_ID="${ENVIRONMENT}-attestor"

log_info "Creating Binary Authorization attestor: $ATTESTOR_ID"

gcloud container binauthz attestors create "$ATTESTOR_ID" \
    --attestation-authority-note="$NOTE_ID" \
    --attestation-authority-note-project="$NOTE_PROJECT" \
    --project="$PROJECT_ID" \
    2>/dev/null || log_warn "Attestor already exists"

# Add public key to attestor
log_info "Adding public key to attestor..."

gcloud container binauthz attestors public-keys add \
    --attestor="$ATTESTOR_ID" \
    --keyversion=1 \
    --keyversion-key="$KEY_NAME" \
    --keyversion-keyring="$KEYRING_NAME" \
    --keyversion-location="$REGION" \
    --keyversion-project="$PROJECT_ID" \
    --project="$PROJECT_ID" \
    2>/dev/null || log_warn "Public key already added"

log_info "✅ Attestor created with public key"

# ==============================================================================
# 5. Create Binary Authorization Policy
# ==============================================================================

log_info "Creating Binary Authorization policy for $ENVIRONMENT..."

case "$ENVIRONMENT" in
    production)
        # Production: Require attestations for all images
        cat > /tmp/policy.yaml <<EOF
admissionWhitelistPatterns:
- namePattern: gcr.io/google_containers/*
- namePattern: gcr.io/google-containers/*
- namePattern: k8s.gcr.io/*
- namePattern: gke.gcr.io/*

globalPolicyEvaluationMode: ENABLE

defaultAdmissionRule:
  evaluationMode: REQUIRE_ATTESTATION
  enforcementMode: ENFORCED_BLOCK_AND_AUDIT_LOG
  requireAttestationsBy:
  - projects/$PROJECT_ID/attestors/$ATTESTOR_ID

clusterAdmissionRules:
  us-central1.mcp-prod-gke:
    evaluationMode: REQUIRE_ATTESTATION
    enforcementMode: ENFORCED_BLOCK_AND_AUDIT_LOG
    requireAttestationsBy:
    - projects/$PROJECT_ID/attestors/$ATTESTOR_ID
EOF
        ;;

    staging)
        # Staging: Require attestations but allow override
        cat > /tmp/policy.yaml <<EOF
admissionWhitelistPatterns:
- namePattern: gcr.io/google_containers/*
- namePattern: gcr.io/google-containers/*
- namePattern: k8s.gcr.io/*
- namePattern: gke.gcr.io/*

globalPolicyEvaluationMode: ENABLE

defaultAdmissionRule:
  evaluationMode: REQUIRE_ATTESTATION
  enforcementMode: DRYRUN_AUDIT_LOG_ONLY
  requireAttestationsBy:
  - projects/$PROJECT_ID/attestors/$ATTESTOR_ID
EOF
        ;;

    development)
        # Development: Audit only (no enforcement)
        cat > /tmp/policy.yaml <<EOF
admissionWhitelistPatterns:
- namePattern: '*'

globalPolicyEvaluationMode: ENABLE

defaultAdmissionRule:
  evaluationMode: ALWAYS_ALLOW
  enforcementMode: DRYRUN_AUDIT_LOG_ONLY
EOF
        ;;
esac

# Import policy
gcloud container binauthz policy import /tmp/policy.yaml \
    --project="$PROJECT_ID"

log_info "✅ Binary Authorization policy imported"

# ==============================================================================
# 6. Grant IAM Permissions
# ==============================================================================

log_info "Granting IAM permissions for Binary Authorization..."

# Get the project number
PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format="value(projectNumber)")

# Grant service account permissions
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:service-${PROJECT_NUMBER}@gcp-sa-binaryauthorization.iam.gserviceaccount.com" \
    --role="roles/binaryauthorization.attestorsViewer" \
    2>/dev/null || log_warn "Permission already granted"

log_info "✅ IAM permissions granted"

# ==============================================================================
# 7. Display Configuration Summary
# ==============================================================================

log_info "Binary Authorization setup complete!"
echo
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Configuration Summary"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo
echo "Project:      $PROJECT_ID"
echo "Environment:  $ENVIRONMENT"
echo "Region:       $REGION"
echo
echo "KMS Key Ring: $KEYRING_NAME"
echo "KMS Key:      $KEY_NAME"
echo "Note:         $NOTE_ID"
echo "Attestor:     $ATTESTOR_ID"
echo
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Next Steps"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo
echo "1. Sign container images during CI/CD:"
echo
echo "   # In your CI/CD pipeline (GitHub Actions, Cloud Build, etc.)"
echo "   gcloud container binauthz attestations sign-and-create \\"
echo "     --artifact-url=\${ARTIFACT_REGISTRY}/\${IMAGE}:\${TAG} \\"
echo "     --attestor=$ATTESTOR_ID \\"
echo "     --attestor-project=$PROJECT_ID \\"
echo "     --keyversion-project=$PROJECT_ID \\"
echo "     --keyversion-location=$REGION \\"
echo "     --keyversion-keyring=$KEYRING_NAME \\"
echo "     --keyversion-key=$KEY_NAME \\"
echo "     --keyversion=1"
echo
echo "2. Enable Binary Authorization in GKE cluster:"
echo
echo "   # Already configured in Terraform module"
echo "   # Set enable_binary_authorization = true in terraform.tfvars"
echo
echo "3. Test policy enforcement:"
echo
echo "   # Try deploying unsigned image (should be blocked in production)"
echo "   kubectl run test --image=nginx:latest --namespace=$ENVIRONMENT"
echo
echo "4. View attestations:"
echo
echo "   gcloud container binauthz attestations list \\"
echo "     --attestor=$ATTESTOR_ID \\"
echo "     --project=$PROJECT_ID"
echo
echo "5. View policy:"
echo
echo "   gcloud container binauthz policy export --project=$PROJECT_ID"
echo
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Cleanup
rm -f /tmp/policy.yaml /tmp/note.json
