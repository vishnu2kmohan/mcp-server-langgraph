#!/bin/bash
# Version Bump Automation Script
# ================================
# Atomically updates version numbers across all deployment artifacts
#
# USAGE:
#   ./scripts/bump-version.sh <new-version> [--dry-run]
#
# EXAMPLES:
#   # Preview changes without modifying files
#   ./scripts/bump-version.sh 2.8.0 --dry-run
#
#   # Apply version update
#   ./scripts/bump-version.sh 2.8.0
#
# UPDATES:
#   - pyproject.toml (project version)
#   - Helm Chart.yaml (version and appVersion)
#   - Helm values.yaml (image tag)
#   - Kustomize base/kustomization.yaml (image tag)
#   - Kustomize overlays (production, staging)
#   - Package.json (if exists)
#
# VALIDATION:
#   - Checks version format (semver)
#   - Validates all files exist
#   - Performs dry-run by default if --dry-run specified
#   - Creates backup before modifications

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DRY_RUN=false
BACKUP_DIR="$PROJECT_ROOT/.version-backups"

# Files to update
PYPROJECT_FILE="$PROJECT_ROOT/pyproject.toml"
HELM_CHART_FILE="$PROJECT_ROOT/deployments/helm/mcp-server-langgraph/Chart.yaml"
HELM_VALUES_FILE="$PROJECT_ROOT/deployments/helm/mcp-server-langgraph/values.yaml"
KUSTOMIZE_BASE_FILE="$PROJECT_ROOT/deployments/kustomize/base/kustomization.yaml"
KUSTOMIZE_PROD_FILE="$PROJECT_ROOT/deployments/kustomize/overlays/production/kustomization.yaml"
KUSTOMIZE_STAGING_FILE="$PROJECT_ROOT/deployments/kustomize/overlays/staging/kustomization.yaml"
# KUSTOMIZE_DEV_FILE is reserved for future use (dev overlay uses dev-latest tag)
# shellcheck disable=SC2034
KUSTOMIZE_DEV_FILE="$PROJECT_ROOT/deployments/kustomize/overlays/dev/kustomization.yaml"

# ==============================================================================
# Helper Functions
# ==============================================================================

print_header() {
    echo -e "\n${BLUE}============================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}============================================================${NC}\n"
}

print_info() {
    echo -e "${CYAN}ℹ  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✓  $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠  $1${NC}"
}

print_error() {
    echo -e "${RED}✗  $1${NC}"
}

validate_semver() {
    local version=$1
    if [[ ! $version =~ ^[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9.]+)?(\+[a-zA-Z0-9.]+)?$ ]]; then
        print_error "Invalid version format: $version"
        print_info "Expected format: MAJOR.MINOR.PATCH (e.g., 2.8.0 or 2.8.0-beta.1)"
        return 1
    fi
    return 0
}

get_current_version() {
    if [[ -f "$PYPROJECT_FILE" ]]; then
        grep '^version = ' "$PYPROJECT_FILE" | cut -d'"' -f2
    else
        echo "unknown"
    fi
}

backup_file() {
    local file=$1
    local backup_file
    backup_file="$BACKUP_DIR/$(basename "$file").backup-$(date +%Y%m%d-%H%M%S)"

    if [[ ! -d "$BACKUP_DIR" ]]; then
        mkdir -p "$BACKUP_DIR"
    fi

    cp "$file" "$backup_file"
    print_info "Backed up $(basename "$file") to $backup_file"
}

update_file() {
    local file=$1
    local pattern=$2
    local replacement=$3
    local description=$4

    if [[ ! -f "$file" ]]; then
        print_warning "File not found: $file (skipping)"
        return 0
    fi

    if [[ "$DRY_RUN" == "true" ]]; then
        print_info "[DRY-RUN] Would update $description in $(basename "$file")"
        echo -e "  ${YELLOW}Pattern:${NC} $pattern"
        echo -e "  ${YELLOW}Replace:${NC} $replacement"

        # Show what would change
        if grep -q "$pattern" "$file"; then
            echo -e "  ${YELLOW}Current:${NC}"
            grep "$pattern" "$file" | sed 's/^/    /'
        fi
        return 0
    fi

    # Backup before modification
    backup_file "$file"

    # Perform replacement
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        sed -i '' "s|$pattern|$replacement|g" "$file"
    else
        # Linux
        sed -i "s|$pattern|$replacement|g" "$file"
    fi

    print_success "Updated $description in $(basename "$file")"
}

verify_update() {
    local file=$1
    local expected=$2
    local description=$3

    if [[ ! -f "$file" ]]; then
        print_warning "Cannot verify $description: file not found"
        return 0
    fi

    if grep -q "$expected" "$file"; then
        print_success "Verified $description: $expected"
        return 0
    else
        print_error "Verification failed for $description in $(basename "$file")"
        return 1
    fi
}

# ==============================================================================
# Main Logic
# ==============================================================================

main() {
    print_header "Version Bump Automation"

    # Parse arguments
    if [[ $# -lt 1 ]]; then
        print_error "Missing version argument"
        echo ""
        echo "Usage: $0 <new-version> [--dry-run]"
        echo ""
        echo "Examples:"
        echo "  $0 2.8.0           # Apply version update"
        echo "  $0 2.8.0 --dry-run # Preview changes"
        exit 1
    fi

    NEW_VERSION=$1
    shift

    # Check for --dry-run flag
    while [[ $# -gt 0 ]]; do
        case $1 in
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            *)
                print_error "Unknown option: $1"
                exit 1
                ;;
        esac
    done

    # Validate version format
    print_info "Validating version format..."
    if ! validate_semver "$NEW_VERSION"; then
        exit 1
    fi
    print_success "Version format is valid: $NEW_VERSION"

    # Get current version
    CURRENT_VERSION=$(get_current_version)
    print_info "Current version: $CURRENT_VERSION"
    print_info "New version: $NEW_VERSION"

    if [[ "$CURRENT_VERSION" == "$NEW_VERSION" ]]; then
        print_warning "New version matches current version. No changes needed."
        exit 0
    fi

    if [[ "$DRY_RUN" == "true" ]]; then
        print_warning "DRY-RUN MODE: No files will be modified"
    fi

    echo ""
    print_header "Updating Version Numbers"

    # Update pyproject.toml
    update_file "$PYPROJECT_FILE" \
        "version = \".*\"" \
        "version = \"$NEW_VERSION\"" \
        "project version"

    # Update Helm Chart.yaml (version and appVersion)
    update_file "$HELM_CHART_FILE" \
        "^version: .*" \
        "version: $NEW_VERSION" \
        "Helm chart version"

    update_file "$HELM_CHART_FILE" \
        "^appVersion: \".*\"" \
        "appVersion: \"$NEW_VERSION\"" \
        "Helm app version"

    # Update Helm values.yaml (image tag)
    update_file "$HELM_VALUES_FILE" \
        "tag: \".*\"" \
        "tag: \"$NEW_VERSION\"" \
        "Helm image tag"

    # Update Kustomize base
    update_file "$KUSTOMIZE_BASE_FILE" \
        "newTag: .*" \
        "newTag: $NEW_VERSION" \
        "Kustomize base image tag"

    # Update Kustomize production overlay
    update_file "$KUSTOMIZE_PROD_FILE" \
        "newTag: v.*" \
        "newTag: v$NEW_VERSION" \
        "Kustomize production image tag"

    # Update Kustomize staging overlay
    update_file "$KUSTOMIZE_STAGING_FILE" \
        "newTag: staging-.*" \
        "newTag: staging-$NEW_VERSION" \
        "Kustomize staging image tag"

    # Note: Dev overlay uses 'dev-latest', not versioned

    if [[ "$DRY_RUN" == "true" ]]; then
        echo ""
        print_header "Dry-Run Summary"
        print_info "No files were modified (dry-run mode)"
        print_info "Run without --dry-run to apply changes:"
        echo ""
        echo "  ./scripts/bump-version.sh $NEW_VERSION"
        echo ""
        exit 0
    fi

    # Verification phase
    echo ""
    print_header "Verifying Updates"

    VERIFICATION_FAILED=false

    verify_update "$PYPROJECT_FILE" "version = \"$NEW_VERSION\"" "pyproject.toml version" || VERIFICATION_FAILED=true
    verify_update "$HELM_CHART_FILE" "version: $NEW_VERSION" "Helm chart version" || VERIFICATION_FAILED=true
    verify_update "$HELM_CHART_FILE" "appVersion: \"$NEW_VERSION\"" "Helm app version" || VERIFICATION_FAILED=true
    verify_update "$HELM_VALUES_FILE" "tag: \"$NEW_VERSION\"" "Helm image tag" || VERIFICATION_FAILED=true
    verify_update "$KUSTOMIZE_BASE_FILE" "newTag: $NEW_VERSION" "Kustomize base tag" || VERIFICATION_FAILED=true
    verify_update "$KUSTOMIZE_PROD_FILE" "newTag: v$NEW_VERSION" "Kustomize production tag" || VERIFICATION_FAILED=true
    verify_update "$KUSTOMIZE_STAGING_FILE" "newTag: staging-$NEW_VERSION" "Kustomize staging tag" || VERIFICATION_FAILED=true

    echo ""

    if [[ "$VERIFICATION_FAILED" == "true" ]]; then
        print_header "Update Failed"
        print_error "Some verifications failed. Please check the files manually."
        print_info "Backups are available in: $BACKUP_DIR"
        exit 1
    fi

    print_header "Update Complete"
    print_success "All files updated to version $NEW_VERSION"
    print_info "Backups saved to: $BACKUP_DIR"

    echo ""
    print_info "Next steps:"
    echo "  1. Review changes: git diff"
    echo "  2. Validate deployments: make validate-all"
    echo "  3. Commit changes: git add . && git commit -m 'chore: bump version to $NEW_VERSION'"
    echo "  4. Create release tag: git tag v$NEW_VERSION"
    echo ""
}

# Run main function
main "$@"
