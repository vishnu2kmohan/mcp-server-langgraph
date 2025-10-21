#!/usr/bin/env bash
# ==============================================================================
# Migrate to Consolidated Kustomize Structure
# ==============================================================================
#
# This script consolidates the deployment manifests from 3 different locations
# into a single Kustomize-based structure.
#
# BEFORE:
#   deployments/kubernetes/base/    (15 manifests)
#   deployments/kustomize/base/     (15 duplicate manifests)
#   deployments/helm/               (12 templates)
#
# AFTER:
#   deployments/base/               (15 manifests - single source of truth)
#   deployments/overlays/           (environment-specific patches)
#   deployments/helm/               (wrapper around Kustomize)
#   deployments/DEPRECATED/         (old structure for rollback)
#
# USAGE:
#   ./scripts/migrate-to-consolidated-kustomize.sh [--dry-run] [--no-backup]
#
# OPTIONS:
#   --dry-run      Show what would be done without making changes
#   --no-backup    Skip creating backup in DEPRECATED directory
#
# ==============================================================================

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default options
DRY_RUN=false
NO_BACKUP=false

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --dry-run)
      DRY_RUN=true
      shift
      ;;
    --no-backup)
      NO_BACKUP=true
      shift
      ;;
    *)
      echo "Unknown option: $1"
      echo "Usage: $0 [--dry-run] [--no-backup]"
      exit 1
      ;;
  esac
done

# Helper functions
log_info() {
  echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
  echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warn() {
  echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
  echo -e "${RED}[ERROR]${NC} $1"
}

execute() {
  if [ "$DRY_RUN" = true ]; then
    echo -e "${YELLOW}[DRY-RUN]${NC} $1"
  else
    eval "$1"
  fi
}

# ==============================================================================
# Pre-flight Checks
# ==============================================================================

log_info "Starting migration to consolidated Kustomize structure..."

# Check if we're in the project root
if [ ! -f "pyproject.toml" ]; then
  log_error "Must be run from project root (where pyproject.toml is located)"
  exit 1
fi

# Check if deployments directory exists
if [ ! -d "deployments" ]; then
  log_error "deployments/ directory not found"
  exit 1
fi

# Check if source directories exist
if [ ! -d "deployments/kustomize/base" ]; then
  log_error "deployments/kustomize/base/ not found - nothing to migrate"
  exit 1
fi

log_success "Pre-flight checks passed"

# ==============================================================================
# Step 1: Create Backup (if enabled)
# ==============================================================================

if [ "$NO_BACKUP" = false ]; then
  log_info "Creating backup of existing deployment files..."

  execute "mkdir -p deployments/DEPRECATED"

  if [ -d "deployments/kubernetes" ]; then
    execute "cp -r deployments/kubernetes deployments/DEPRECATED/kubernetes-$(date +%Y%m%d-%H%M%S)"
    log_success "Backed up deployments/kubernetes/"
  fi

  if [ -d "deployments/kustomize" ]; then
    execute "cp -r deployments/kustomize deployments/DEPRECATED/kustomize-$(date +%Y%m%d-%H%M%S)"
    log_success "Backed up deployments/kustomize/"
  fi
else
  log_warn "Skipping backup (--no-backup specified)"
fi

# ==============================================================================
# Step 2: Create New Structure
# ==============================================================================

log_info "Creating consolidated structure..."

# Move kustomize/base to deployments/base
if [ -d "deployments/kustomize/base" ]; then
  execute "mv deployments/kustomize/base deployments/base"
  log_success "Moved deployments/kustomize/base/ → deployments/base/"
else
  log_warn "deployments/kustomize/base/ not found, skipping"
fi

# Move kustomize/overlays to deployments/overlays
if [ -d "deployments/kustomize/overlays" ]; then
  execute "mv deployments/kustomize/overlays deployments/overlays"
  log_success "Moved deployments/kustomize/overlays/ → deployments/overlays/"
else
  log_warn "deployments/kustomize/overlays/ not found, skipping"
fi

# ==============================================================================
# Step 3: Update Kustomization References
# ==============================================================================

log_info "Updating kustomization.yaml references..."

# Update overlay kustomization files to point to new base
if [ -d "deployments/overlays" ]; then
  for overlay in deployments/overlays/*/kustomization.yaml; do
    if [ -f "$overlay" ]; then
      log_info "Updating $overlay"
      execute "sed -i.bak 's|../../base|../../base|g' \"$overlay\""
      execute "sed -i.bak 's|../../../kustomize/base|../../base|g' \"$overlay\""
      execute "rm -f \"$overlay.bak\""
    fi
  done
  log_success "Updated overlay kustomization files"
fi

# ==============================================================================
# Step 4: Remove Old Directories
# ==============================================================================

log_info "Removing old directory structure..."

if [ -d "deployments/kubernetes/base" ]; then
  execute "rm -rf deployments/kubernetes/base"
  log_success "Removed deployments/kubernetes/base/ (duplicate)"
fi

if [ -d "deployments/kustomize" ] && [ -z "$(ls -A deployments/kustomize)" ]; then
  execute "rm -rf deployments/kustomize"
  log_success "Removed empty deployments/kustomize/"
fi

# ==============================================================================
# Step 5: Update Helm Charts
# ==============================================================================

log_info "Updating Helm charts to reference new base..."

# Create Helm template that wraps Kustomize
HELM_KUSTOMIZATION="deployments/helm/mcp-server-langgraph/templates/kustomization.yaml"
if [ -f "$HELM_KUSTOMIZATION" ]; then
  execute "sed -i.bak 's|../../../kustomize/base|../../../base|g' \"$HELM_KUSTOMIZATION\""
  execute "rm -f \"$HELM_KUSTOMIZATION.bak\""
  log_success "Updated Helm kustomization reference"
fi

# ==============================================================================
# Step 6: Create README in New Structure
# ==============================================================================

log_info "Creating documentation..."

cat > deployments/base/README.md << 'EOF'
# Kubernetes Base Manifests

This directory contains the base Kubernetes manifests for the MCP Server LangGraph deployment.

## Structure

```
base/
├── kustomization.yaml          # Base kustomization
├── deployment.yaml             # Main application deployment
├── service.yaml                # Kubernetes service
├── configmap.yaml              # Configuration
├── secret.yaml                 # Secrets template
├── serviceaccount.yaml         # Service account
├── hpa.yaml                    # Horizontal Pod Autoscaler
├── pdb.yaml                    # Pod Disruption Budget
├── networkpolicy.yaml          # Network policies
├── postgres-statefulset.yaml  # PostgreSQL database
├── postgres-service.yaml       # PostgreSQL service
├── openfga-deployment.yaml    # OpenFGA authorization
├── openfga-service.yaml        # OpenFGA service
├── keycloak-deployment.yaml   # Keycloak SSO
├── keycloak-service.yaml       # Keycloak service
├── redis-session-deployment.yaml  # Redis session store
├── redis-session-service.yaml     # Redis session service
├── qdrant-deployment.yaml     # Qdrant vector database
└── qdrant-service.yaml         # Qdrant service
```

## Usage

### Direct Application

```bash
kubectl apply -k deployments/base
```

### With Overlays (Recommended)

```bash
# Development
kubectl apply -k deployments/overlays/dev

# Staging
kubectl apply -k deployments/overlays/staging

# Production
kubectl apply -k deployments/overlays/production
```

### With Helm

```bash
helm install mcp-server-langgraph deployments/helm/mcp-server-langgraph
```

## Customization

Do not modify these base manifests directly. Instead:

1. Create an overlay in `deployments/overlays/<env>/`
2. Use Kustomize patches to customize
3. Reference the base in your overlay's `kustomization.yaml`

Example overlay structure:

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

bases:
  - ../../base

patches:
  - path: deployment-patch.yaml
    target:
      kind: Deployment
      name: mcp-server-langgraph
```

## Migration

This structure was created by consolidating:
- `deployments/kubernetes/base/` (removed)
- `deployments/kustomize/base/` (moved here)

Old backups are available in `deployments/DEPRECATED/` if needed.
EOF

if [ "$DRY_RUN" = false ]; then
  log_success "Created deployments/base/README.md"
fi

# ==============================================================================
# Step 7: Validation
# ==============================================================================

log_info "Validating new structure..."

# Check if kubectl is available
if command -v kubectl &> /dev/null; then
  if [ -f "deployments/base/kustomization.yaml" ]; then
    if [ "$DRY_RUN" = false ]; then
      if kubectl kustomize deployments/base > /dev/null 2>&1; then
        log_success "Kustomize build validation passed"
      else
        log_warn "Kustomize build validation failed - manual review needed"
      fi
    fi
  fi
else
  log_warn "kubectl not found - skipping validation"
fi

# ==============================================================================
# Summary
# ==============================================================================

echo ""
echo "=================================="
log_success "Migration Complete!"
echo "=================================="
echo ""
echo "New structure:"
echo "  deployments/base/           - Single source of truth (15 manifests)"
echo "  deployments/overlays/       - Environment-specific patches"
echo "  deployments/helm/           - Helm wrapper"
echo ""
if [ "$NO_BACKUP" = false ]; then
  echo "Backups:"
  echo "  deployments/DEPRECATED/     - Old structure (for rollback)"
  echo ""
fi
echo "Next steps:"
echo "  1. Review the new structure: ls -la deployments/base/"
echo "  2. Test deployment: kubectl kustomize deployments/base"
echo "  3. Update CI/CD to use new paths"
echo "  4. Delete DEPRECATED/ after confirming everything works"
echo ""

if [ "$DRY_RUN" = true ]; then
  log_warn "This was a DRY RUN - no changes were made"
  echo "Run without --dry-run to apply changes"
fi
