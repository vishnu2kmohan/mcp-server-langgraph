#!/bin/bash
#
# GCP IAM Permissions Validation Script
#
# This script validates that the service account has all required IAM roles
# for successful CI/CD deployments to GKE.
#
# Usage:
#   ./scripts/validation/validate-gcp-permissions.sh
#
# Exit codes:
#   0 - All permissions valid
#   1 - Missing required permissions
#

set -euo pipefail

# Configuration
PROJECT_ID="${GCP_PROJECT_ID:-vishnu-sandbox-20250310}"
SERVICE_ACCOUNT="${GCP_SERVICE_ACCOUNT:-mcp-staging-sa@${PROJECT_ID}.iam.gserviceaccount.com}"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Required roles for CI/CD deployment
REQUIRED_ROLES=(
  "roles/artifactregistry.writer"
  "roles/container.developer"
  "roles/logging.logWriter"
  "roles/monitoring.metricWriter"
  "roles/secretmanager.secretAccessor"
)

# Optional roles (warn if missing but don't fail)
OPTIONAL_ROLES=(
  "roles/cloudsql.client"
)

echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  GCP IAM Permissions Validation${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "Project: $PROJECT_ID"
echo "Service Account: $SERVICE_ACCOUNT"
echo ""

# Check if service account exists
echo "Checking if service account exists..."
if ! gcloud iam service-accounts describe "$SERVICE_ACCOUNT" --project="$PROJECT_ID" &> /dev/null; then
  echo -e "${RED}✗ Service account does not exist${NC}"
  echo ""
  echo "Create it with:"
  echo "  gcloud iam service-accounts create mcp-staging-sa \\"
  echo "    --display-name='MCP Staging Service Account' \\"
  echo "    --project=$PROJECT_ID"
  exit 1
fi
echo -e "${GREEN}✓ Service account exists${NC}"
echo ""

# Get all granted roles
echo "Fetching granted IAM roles..."
GRANTED_ROLES=$(gcloud projects get-iam-policy "$PROJECT_ID" \
  --flatten="bindings[].members" \
  --filter="bindings.members:${SERVICE_ACCOUNT}" \
  --format="value(bindings.role)" || echo "")

if [ -z "$GRANTED_ROLES" ]; then
  echo -e "${RED}✗ No IAM roles granted to service account${NC}"
  exit 1
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Required Roles:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

MISSING_COUNT=0

for role in "${REQUIRED_ROLES[@]}"; do
  if echo "$GRANTED_ROLES" | grep -q "^${role}$"; then
    echo -e "${GREEN}✓${NC} $role"
  else
    echo -e "${RED}✗${NC} $role (MISSING - REQUIRED)"
    MISSING_COUNT=$((MISSING_COUNT + 1))
  fi
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Optional Roles:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

for role in "${OPTIONAL_ROLES[@]}"; do
  if echo "$GRANTED_ROLES" | grep -q "^${role}$"; then
    echo -e "${GREEN}✓${NC} $role"
  else
    echo -e "${YELLOW}⚠${NC} $role (missing - optional)"
  fi
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ $MISSING_COUNT -gt 0 ]; then
  echo -e "${RED}✗ Validation FAILED: $MISSING_COUNT required role(s) missing${NC}"
  echo ""
  echo "Grant missing roles with:"
  echo ""
  for role in "${REQUIRED_ROLES[@]}"; do
    if ! echo "$GRANTED_ROLES" | grep -q "^${role}$"; then
      echo "  gcloud projects add-iam-policy-binding $PROJECT_ID \\"
      echo "    --member='serviceAccount:${SERVICE_ACCOUNT}' \\"
      echo "    --role='$role'"
      echo ""
    fi
  done
  exit 1
else
  echo -e "${GREEN}✓ Validation PASSED: All required IAM roles present${NC}"
  echo ""
  echo "Service account is properly configured for CI/CD deployments."
fi

# Check Workload Identity binding
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Workload Identity Binding:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

WI_BINDINGS=$(gcloud iam service-accounts get-iam-policy "$SERVICE_ACCOUNT" \
  --format="value(bindings.role)" 2>/dev/null || echo "")

if echo "$WI_BINDINGS" | grep -q "roles/iam.workloadIdentityUser"; then
  echo -e "${GREEN}✓ Workload Identity User binding present${NC}"
  echo ""
  echo "GitHub Actions can impersonate this service account via Workload Identity Federation."
else
  echo -e "${YELLOW}⚠ Workload Identity User binding missing${NC}"
  echo ""
  echo "If using GitHub Actions, grant impersonation rights:"
  echo "  gcloud iam service-accounts add-iam-policy-binding \\"
  echo "    '${SERVICE_ACCOUNT}' \\"
  echo "    --role='roles/iam.workloadIdentityUser' \\"
  echo "    --member='principalSet://iam.googleapis.com/projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/github-actions-pool/attribute.repository/GITHUB_REPO'"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${GREEN}✓ GCP permissions validation complete${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
