#!/usr/bin/env bash
set -euo pipefail

# ==============================================================================
# GCP Workload Identity Federation Setup for GitHub Actions
# ==============================================================================
#
# This script sets up Workload Identity Federation (WIF) for keyless
# authentication from GitHub Actions to Google Cloud Platform.
#
# Prerequisites:
# - gcloud CLI installed and authenticated
# - Project Owner or Security Admin role
# - GitHub repository: vishnu2kmohan/mcp-server-langgraph
#
# ==============================================================================

# Configuration
GCP_PROJECT_ID="${GCP_PROJECT_ID:-vishnu-sandbox-20250310}"
GCP_REGION="${GCP_REGION:-us-central1}"
GITHUB_REPO="vishnu2kmohan/mcp-server-langgraph"
POOL_ID="github-actions-pool"
PROVIDER_ID="github-actions-provider"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
log_info() {
    echo -e "${BLUE}ℹ ${NC}$1"
}

log_success() {
    echo -e "${GREEN}✓${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}⚠ ${NC}$1"
}

log_error() {
    echo -e "${RED}✗${NC} $1"
}

# ==============================================================================
# Step 1: Verify Prerequisites
# ==============================================================================

log_info "Verifying prerequisites..."

# Check gcloud is installed
if ! command -v gcloud &> /dev/null; then
    log_error "gcloud CLI not found. Please install: https://cloud.google.com/sdk/docs/install"
    exit 1
fi
log_success "gcloud CLI found"

# Check current project
CURRENT_PROJECT=$(gcloud config get-value project 2>/dev/null || echo "")
if [ "$CURRENT_PROJECT" != "$GCP_PROJECT_ID" ]; then
    log_warning "Current project is '$CURRENT_PROJECT', switching to '$GCP_PROJECT_ID'"
    gcloud config set project "$GCP_PROJECT_ID"
fi
log_success "Using GCP project: $GCP_PROJECT_ID"

# Get project number (needed for WIF provider path)
PROJECT_NUMBER=$(gcloud projects describe "$GCP_PROJECT_ID" --format="value(projectNumber)")
log_success "Project number: $PROJECT_NUMBER"

# ==============================================================================
# Step 2: Enable Required APIs
# ==============================================================================

log_info "Enabling required Google Cloud APIs..."

REQUIRED_APIS=(
    "iam.googleapis.com"
    "iamcredentials.googleapis.com"
    "cloudresourcemanager.googleapis.com"
    "sts.googleapis.com"
    "container.googleapis.com"
    "artifactregistry.googleapis.com"
)

for api in "${REQUIRED_APIS[@]}"; do
    if gcloud services list --enabled --filter="name:$api" --format="value(name)" | grep -q "$api"; then
        log_success "$api already enabled"
    else
        log_info "Enabling $api..."
        gcloud services enable "$api"
        log_success "$api enabled"
    fi
done

# ==============================================================================
# Step 3: Create Workload Identity Pool
# ==============================================================================

log_info "Creating Workload Identity Pool..."

if gcloud iam workload-identity-pools describe "$POOL_ID" \
    --location=global \
    --project="$GCP_PROJECT_ID" &>/dev/null; then
    log_warning "Workload Identity Pool '$POOL_ID' already exists"
else
    gcloud iam workload-identity-pools create "$POOL_ID" \
        --location=global \
        --display-name="GitHub Actions Pool" \
        --description="Workload Identity Pool for GitHub Actions authentication" \
        --project="$GCP_PROJECT_ID"
    log_success "Workload Identity Pool '$POOL_ID' created"
fi

# ==============================================================================
# Step 4: Create OIDC Provider
# ==============================================================================

log_info "Creating OIDC Provider for GitHub..."

if gcloud iam workload-identity-pools providers describe "$PROVIDER_ID" \
    --workload-identity-pool="$POOL_ID" \
    --location=global \
    --project="$GCP_PROJECT_ID" &>/dev/null; then
    log_warning "OIDC Provider '$PROVIDER_ID' already exists"
else
    gcloud iam workload-identity-pools providers create-oidc "$PROVIDER_ID" \
        --workload-identity-pool="$POOL_ID" \
        --location=global \
        --issuer-uri="https://token.actions.githubusercontent.com" \
        --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository,attribute.repository_owner=assertion.repository_owner" \
        --attribute-condition="assertion.repository_owner=='vishnu2kmohan'" \
        --project="$GCP_PROJECT_ID"
    log_success "OIDC Provider '$PROVIDER_ID' created"
fi

# Get the full provider name
WORKLOAD_IDENTITY_PROVIDER="projects/$PROJECT_NUMBER/locations/global/workloadIdentityPools/$POOL_ID/providers/$PROVIDER_ID"
log_success "Workload Identity Provider: $WORKLOAD_IDENTITY_PROVIDER"

# ==============================================================================
# Step 5: Create Service Accounts
# ==============================================================================

log_info "Creating service accounts..."

# Preview deployment service account
SA_PREVIEW="github-actions-preview"
SA_PREVIEW_EMAIL="$SA_PREVIEW@$GCP_PROJECT_ID.iam.gserviceaccount.com"

if gcloud iam service-accounts describe "$SA_PREVIEW_EMAIL" --project="$GCP_PROJECT_ID" &>/dev/null; then
    log_warning "Service account '$SA_PREVIEW' already exists"
else
    gcloud iam service-accounts create "$SA_PREVIEW" \
        --display-name="GitHub Actions Preview Deployment" \
        --description="Service account for GitHub Actions preview deployments" \
        --project="$GCP_PROJECT_ID"
    log_success "Service account '$SA_PREVIEW' created"
fi

# Terraform service account
SA_TERRAFORM="github-actions-terraform"
SA_TERRAFORM_EMAIL="$SA_TERRAFORM@$GCP_PROJECT_ID.iam.gserviceaccount.com"

if gcloud iam service-accounts describe "$SA_TERRAFORM_EMAIL" --project="$GCP_PROJECT_ID" &>/dev/null; then
    log_warning "Service account '$SA_TERRAFORM' already exists"
else
    gcloud iam service-accounts create "$SA_TERRAFORM" \
        --display-name="GitHub Actions Terraform" \
        --description="Service account for GitHub Actions Terraform operations" \
        --project="$GCP_PROJECT_ID"
    log_success "Service account '$SA_TERRAFORM' created"
fi

# Production deployment service account (if needed)
SA_PRODUCTION="github-actions-production"
SA_PRODUCTION_EMAIL="$SA_PRODUCTION@$GCP_PROJECT_ID.iam.gserviceaccount.com"

if gcloud iam service-accounts describe "$SA_PRODUCTION_EMAIL" --project="$GCP_PROJECT_ID" &>/dev/null; then
    log_warning "Service account '$SA_PRODUCTION' already exists"
else
    gcloud iam service-accounts create "$SA_PRODUCTION" \
        --display-name="GitHub Actions Production Deployment" \
        --description="Service account for GitHub Actions production deployments" \
        --project="$GCP_PROJECT_ID"
    log_success "Service account '$SA_PRODUCTION' created"
fi

# ==============================================================================
# Step 6: Grant IAM Permissions to Service Accounts
# ==============================================================================

log_info "Granting IAM permissions..."

# Permissions for preview service account
PREVIEW_ROLES=(
    "roles/container.developer"           # GKE deployment
    "roles/artifactregistry.writer"       # Push Docker images
    "roles/logging.logWriter"            # Write logs
    "roles/monitoring.metricWriter"      # Write metrics
    "roles/storage.objectViewer"         # Read from buckets
)

for role in "${PREVIEW_ROLES[@]}"; do
    if gcloud projects get-iam-policy "$GCP_PROJECT_ID" \
        --flatten="bindings[].members" \
        --filter="bindings.members:serviceAccount:$SA_PREVIEW_EMAIL AND bindings.role:$role" \
        --format="value(bindings.role)" | grep -q "$role"; then
        log_success "$SA_PREVIEW already has $role"
    else
        gcloud projects add-iam-policy-binding "$GCP_PROJECT_ID" \
            --member="serviceAccount:$SA_PREVIEW_EMAIL" \
            --role="$role" \
            --condition=None \
            --no-user-output-enabled
        log_success "Granted $role to $SA_PREVIEW"
    fi
done

# Permissions for Terraform service account
TERRAFORM_ROLES=(
    "roles/compute.networkAdmin"         # Manage VPC/networks
    "roles/container.admin"              # Manage GKE clusters
    "roles/iam.serviceAccountAdmin"      # Manage service accounts
    "roles/resourcemanager.projectIamAdmin"  # Manage project IAM
    "roles/storage.admin"                # Manage buckets
)

for role in "${TERRAFORM_ROLES[@]}"; do
    if gcloud projects get-iam-policy "$GCP_PROJECT_ID" \
        --flatten="bindings[].members" \
        --filter="bindings.members:serviceAccount:$SA_TERRAFORM_EMAIL AND bindings.role:$role" \
        --format="value(bindings.role)" | grep -q "$role"; then
        log_success "$SA_TERRAFORM already has $role"
    else
        gcloud projects add-iam-policy-binding "$GCP_PROJECT_ID" \
            --member="serviceAccount:$SA_TERRAFORM_EMAIL" \
            --role="$role" \
            --condition=None \
            --no-user-output-enabled
        log_success "Granted $role to $SA_TERRAFORM"
    fi
done

# Permissions for production service account
PRODUCTION_ROLES=(
    "roles/container.developer"          # GKE deployment
    "roles/artifactregistry.writer"      # Push Docker images
    "roles/logging.logWriter"           # Write logs
    "roles/monitoring.metricWriter"     # Write metrics
    "roles/cloudtrace.agent"            # Write traces
)

for role in "${PRODUCTION_ROLES[@]}"; do
    if gcloud projects get-iam-policy "$GCP_PROJECT_ID" \
        --flatten="bindings[].members" \
        --filter="bindings.members:serviceAccount:$SA_PRODUCTION_EMAIL AND bindings.role:$role" \
        --format="value(bindings.role)" | grep -q "$role"; then
        log_success "$SA_PRODUCTION already has $role"
    else
        gcloud projects add-iam-policy-binding "$GCP_PROJECT_ID" \
            --member="serviceAccount:$SA_PRODUCTION_EMAIL" \
            --role="$role" \
            --condition=None \
            --no-user-output-enabled
        log_success "Granted $role to $SA_PRODUCTION"
    fi
done

# ==============================================================================
# Step 7: Allow GitHub Actions to Impersonate Service Accounts
# ==============================================================================

log_info "Configuring Workload Identity Federation bindings..."

# Allow GitHub Actions from the specific repository to impersonate the preview SA
PREVIEW_BINDING_MEMBER="principalSet://iam.googleapis.com/$WORKLOAD_IDENTITY_PROVIDER/attribute.repository/$GITHUB_REPO"

if gcloud iam service-accounts get-iam-policy "$SA_PREVIEW_EMAIL" \
    --flatten="bindings[].members" \
    --filter="bindings.members:$PREVIEW_BINDING_MEMBER" \
    --format="value(bindings.role)" | grep -q "roles/iam.workloadIdentityUser"; then
    log_success "WIF binding already exists for $SA_PREVIEW"
else
    gcloud iam service-accounts add-iam-policy-binding "$SA_PREVIEW_EMAIL" \
        --member="$PREVIEW_BINDING_MEMBER" \
        --role="roles/iam.workloadIdentityUser" \
        --project="$GCP_PROJECT_ID"
    log_success "Added WIF binding for $SA_PREVIEW"
fi

# Allow GitHub Actions to impersonate the Terraform SA
TERRAFORM_BINDING_MEMBER="principalSet://iam.googleapis.com/$WORKLOAD_IDENTITY_PROVIDER/attribute.repository/$GITHUB_REPO"

if gcloud iam service-accounts get-iam-policy "$SA_TERRAFORM_EMAIL" \
    --flatten="bindings[].members" \
    --filter="bindings.members:$TERRAFORM_BINDING_MEMBER" \
    --format="value(bindings.role)" | grep -q "roles/iam.workloadIdentityUser"; then
    log_success "WIF binding already exists for $SA_TERRAFORM"
else
    gcloud iam service-accounts add-iam-policy-binding "$SA_TERRAFORM_EMAIL" \
        --member="$TERRAFORM_BINDING_MEMBER" \
        --role="roles/iam.workloadIdentityUser" \
        --project="$GCP_PROJECT_ID"
    log_success "Added WIF binding for $SA_TERRAFORM"
fi

# Allow GitHub Actions to impersonate the production SA
PRODUCTION_BINDING_MEMBER="principalSet://iam.googleapis.com/$WORKLOAD_IDENTITY_PROVIDER/attribute.repository/$GITHUB_REPO"

if gcloud iam service-accounts get-iam-policy "$SA_PRODUCTION_EMAIL" \
    --flatten="bindings[].members" \
    --filter="bindings.members:$PRODUCTION_BINDING_MEMBER" \
    --format="value(bindings.role)" | grep -q "roles/iam.workloadIdentityUser"; then
    log_success "WIF binding already exists for $SA_PRODUCTION"
else
    gcloud iam service-accounts add-iam-policy-binding "$SA_PRODUCTION_EMAIL" \
        --member="$PRODUCTION_BINDING_MEMBER" \
        --role="roles/iam.workloadIdentityUser" \
        --project="$GCP_PROJECT_ID"
    log_success "Added WIF binding for $SA_PRODUCTION"
fi

# ==============================================================================
# Step 8: Create Artifact Registry Repository (if needed)
# ==============================================================================

log_info "Setting up Artifact Registry..."

REPO_NAME="mcp-preview"
REPO_LOCATION="$GCP_REGION"

if gcloud artifacts repositories describe "$REPO_NAME" \
    --location="$REPO_LOCATION" \
    --project="$GCP_PROJECT_ID" &>/dev/null; then
    log_success "Artifact Registry repository '$REPO_NAME' already exists"
else
    gcloud artifacts repositories create "$REPO_NAME" \
        --repository-format=docker \
        --location="$REPO_LOCATION" \
        --description="Docker images for MCP preview environment" \
        --project="$GCP_PROJECT_ID"
    log_success "Artifact Registry repository '$REPO_NAME' created"
fi

# ==============================================================================
# Step 9: Output GitHub Secrets
# ==============================================================================

echo ""
echo "================================================================================"
echo -e "${GREEN}Setup Complete!${NC}"
echo "================================================================================"
echo ""
echo "Add these secrets to your GitHub repository:"
echo "  Repository: https://github.com/$GITHUB_REPO/settings/secrets/actions"
echo ""
echo "-------------------------------------------------------------------------------"
echo -e "${BLUE}GCP_WIF_PROVIDER${NC}"
echo "$WORKLOAD_IDENTITY_PROVIDER"
echo ""
echo "-------------------------------------------------------------------------------"
echo -e "${BLUE}GCP_STAGING_SA_EMAIL${NC}"
echo "$SA_STAGING_EMAIL"
echo ""
echo "-------------------------------------------------------------------------------"
echo -e "${BLUE}GCP_TERRAFORM_SA_EMAIL${NC}"
echo "$SA_TERRAFORM_EMAIL"
echo ""
echo "-------------------------------------------------------------------------------"
echo -e "${BLUE}GCP_PRODUCTION_SA_EMAIL${NC} (optional)"
echo "$SA_PRODUCTION_EMAIL"
echo ""
echo "================================================================================"
echo ""
echo "Next Steps:"
echo "1. Go to: https://github.com/$GITHUB_REPO/settings/secrets/actions/new"
echo "2. Add each secret above (name and value)"
echo "3. Test the deployment workflow"
echo ""
echo "================================================================================"
echo ""

# Save to file for easy reference
OUTPUT_FILE="/tmp/gcp-wif-setup-secrets.txt"
cat > "$OUTPUT_FILE" <<EOF
GCP Workload Identity Federation Setup - GitHub Secrets
========================================================

Repository: https://github.com/$GITHUB_REPO/settings/secrets/actions

Secrets to Add:
---------------

Name: GCP_WIF_PROVIDER
Value: $WORKLOAD_IDENTITY_PROVIDER

Name: GCP_STAGING_SA_EMAIL
Value: $SA_STAGING_EMAIL

Name: GCP_TERRAFORM_SA_EMAIL
Value: $SA_TERRAFORM_EMAIL

Name: GCP_PRODUCTION_SA_EMAIL (optional)
Value: $SA_PRODUCTION_EMAIL

Additional Configuration:
------------------------

Project ID: $GCP_PROJECT_ID
Project Number: $PROJECT_NUMBER
Region: $GCP_REGION

Artifact Registry:
- Repository: $REPO_NAME
- Location: $REPO_LOCATION
- URL: $REPO_LOCATION-docker.pkg.dev/$GCP_PROJECT_ID/$REPO_NAME

Service Accounts Created:
- Staging: $SA_STAGING_EMAIL
- Terraform: $SA_TERRAFORM_EMAIL
- Production: $SA_PRODUCTION_EMAIL

Setup completed: $(date)
EOF

log_success "Secrets saved to: $OUTPUT_FILE"
echo ""
